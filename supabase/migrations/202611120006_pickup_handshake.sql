BEGIN;

-- =========================================================
-- 1. Store pickup handshake state (never store plaintext code)
-- =========================================================

CREATE TABLE IF NOT EXISTS public.pickup_handshakes (
    claim_id uuid PRIMARY KEY
        REFERENCES public.claims(id) ON DELETE CASCADE,

    code_hash text NOT NULL
        CHECK (code_hash ~ '^[0-9a-f]{64}$'),

    attempts integer NOT NULL DEFAULT 0
        CHECK (attempts BETWEEN 0 AND 5),

    verified_at timestamptz,
    invalidated_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS idx_pickup_handshakes_claim_verified
    ON public.pickup_handshakes (claim_id, verified_at);

ALTER TABLE public.pickup_handshakes ENABLE ROW LEVEL SECURITY;

REVOKE ALL PRIVILEGES ON TABLE public.pickup_handshakes
    FROM PUBLIC, anon, authenticated;

GRANT SELECT, INSERT, UPDATE
    ON TABLE public.pickup_handshakes
    TO service_role;

-- Explicit RLS policies ensuring service_role access across all core tables
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'pickup_handshakes'
          AND policyname = 'service_role_manage_pickup_handshakes'
    ) THEN
        CREATE POLICY service_role_manage_pickup_handshakes
            ON public.pickup_handshakes
            FOR ALL
            TO service_role
            USING (true)
            WITH CHECK (true);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'claims'
          AND policyname = 'service_role_manage_claims'
    ) THEN
        CREATE POLICY service_role_manage_claims
            ON public.claims
            FOR ALL
            TO service_role
            USING (true)
            WITH CHECK (true);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'food_listings'
          AND policyname = 'service_role_manage_food_listings'
    ) THEN
        CREATE POLICY service_role_manage_food_listings
            ON public.food_listings
            FOR ALL
            TO service_role
            USING (true)
            WITH CHECK (true);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'user_profiles'
          AND policyname = 'service_role_manage_user_profiles'
    ) THEN
        CREATE POLICY service_role_manage_user_profiles
            ON public.user_profiles
            FOR ALL
            TO service_role
            USING (true)
            WITH CHECK (true);
    END IF;
END $$;


-- =========================================================
-- 2. Automatically invalidate cancelled/expired handshakes
-- =========================================================

CREATE OR REPLACE FUNCTION public.invalidate_pickup_handshake()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    IF NEW.status IN ('cancelled', 'expired')
       AND OLD.status IS DISTINCT FROM NEW.status THEN

        UPDATE public.pickup_handshakes
        SET invalidated_at = COALESCE(invalidated_at, clock_timestamp())
        WHERE claim_id = NEW.id;
    END IF;

    RETURN NEW;
END;
$$;

REVOKE ALL ON FUNCTION public.invalidate_pickup_handshake()
    FROM PUBLIC, anon, authenticated;

DROP TRIGGER IF EXISTS trg_invalidate_pickup_handshake
    ON public.claims;

CREATE TRIGGER trg_invalidate_pickup_handshake
AFTER UPDATE OF status ON public.claims
FOR EACH ROW
EXECUTE FUNCTION public.invalidate_pickup_handshake();


-- =========================================================
-- 3. Replace the old claim RPC with handshake-aware version
-- =========================================================

CREATE OR REPLACE FUNCTION public.claim_food_listing(
    p_listing_id uuid,
    p_receiver_id uuid,
    p_claim_id uuid,
    p_handshake_code_hash text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_listing public.food_listings%ROWTYPE;
    v_claim public.claims%ROWTYPE;
    v_now timestamptz;
BEGIN
    -- Validate backend-generated handshake inputs.
    IF p_claim_id IS NULL
       OR p_handshake_code_hash IS NULL
       OR p_handshake_code_hash !~ '^[0-9a-f]{64}$' THEN

        RETURN jsonb_build_object(
            'success', false,
            'code', 'INVALID_HANDSHAKE'
        );
    END IF;

    -- Preserve the existing listing -> claim lock order.
    SELECT *
    INTO v_listing
    FROM public.food_listings
    WHERE id = p_listing_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'success', false,
            'code', 'NOT_FOUND',
            'message', 'Listing not found'
        );
    END IF;

    v_now := clock_timestamp();

    -- Food safety expiry takes precedence.
    IF v_listing.safe_until <= v_now THEN

        UPDATE public.claims
        SET status = 'expired'
        WHERE listing_id = p_listing_id
          AND status = 'active';

        UPDATE public.food_listings
        SET status = 'expired',
            updated_at = v_now
        WHERE id = p_listing_id
          AND status IN ('available', 'claimed');

        RETURN jsonb_build_object(
            'success', false,
            'code', 'EXPIRED',
            'message', 'Listing expired'
        );
    END IF;

    -- Reconcile an old timed-out claim while holding the listing lock.
    IF v_listing.status = 'claimed' THEN

        UPDATE public.claims
        SET status = 'expired'
        WHERE listing_id = p_listing_id
          AND status = 'active'
          AND expires_at <= v_now;

        IF FOUND THEN
            UPDATE public.food_listings
            SET status = 'available',
                updated_at = v_now
            WHERE id = p_listing_id
              AND status = 'claimed'
              AND safe_until > v_now;

            v_listing.status := 'available';
        END IF;
    END IF;

    IF v_listing.status <> 'available' THEN
        RETURN jsonb_build_object(
            'success', false,
            'code', 'CONFLICT',
            'message', 'Listing already claimed or unavailable'
        );
    END IF;

    -- Verify receiver role, approval status and verification.
    IF NOT EXISTS (
        SELECT 1
        FROM public.user_profiles
        WHERE id = p_receiver_id
          AND role = 'receiver'
          AND approval_status = 'approved'
          AND is_verified = TRUE
    ) THEN
        RETURN jsonb_build_object(
            'success', false,
            'code', 'FORBIDDEN',
            'message', 'Approved receiver required'
        );
    END IF;

    IF EXISTS (
        SELECT 1
        FROM public.claims
        WHERE listing_id = p_listing_id
          AND status = 'active'
    ) THEN
        RETURN jsonb_build_object(
            'success', false,
            'code', 'CONFLICT',
            'message', 'Active claim already exists'
        );
    END IF;

    -- Insert claim using the UUID generated by the backend.
    INSERT INTO public.claims (
        id,
        listing_id,
        receiver_id,
        status,
        claimed_at,
        expires_at
    )
    VALUES (
        p_claim_id,
        p_listing_id,
        p_receiver_id,
        'active',
        v_now,
        v_now + interval '15 minutes'
    )
    RETURNING * INTO v_claim;

    -- Insert handshake in the SAME transaction.
    -- If this insert fails, the claim insert also rolls back.
    INSERT INTO public.pickup_handshakes (
        claim_id,
        code_hash,
        created_at
    )
    VALUES (
        p_claim_id,
        p_handshake_code_hash,
        v_now
    );

    UPDATE public.food_listings
    SET status = 'claimed',
        updated_at = v_now
    WHERE id = p_listing_id;

    RETURN jsonb_build_object(
        'success', true,
        'claim_id', v_claim.id,
        'listing_id', p_listing_id,
        'receiver_id', p_receiver_id,
        'status', v_claim.status,
        'claimed_at', v_claim.claimed_at,
        'expires_at', v_claim.expires_at
    );

EXCEPTION
    WHEN unique_violation THEN
        RETURN jsonb_build_object(
            'success', false,
            'code', 'CONFLICT',
            'message', 'Active claim already exists'
        );
END;
$$;


-- =========================================================
-- 4. Remove old RPC so claims cannot bypass handshake creation
-- =========================================================

REVOKE ALL ON FUNCTION public.claim_food_listing(uuid, uuid)
    FROM PUBLIC, anon, authenticated, service_role;

DROP FUNCTION IF EXISTS public.claim_food_listing(uuid, uuid);


-- =========================================================
-- 5. Restrict claim RPC to backend service role
-- =========================================================

REVOKE ALL ON FUNCTION public.claim_food_listing(
    uuid, uuid, uuid, text
) FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION public.claim_food_listing(
    uuid, uuid, uuid, text
) TO service_role;


-- =========================================================
-- 6. Atomic pickup verification RPC
-- =========================================================

CREATE OR REPLACE FUNCTION public.verify_pickup_handshake(
    p_claim_id uuid,
    p_receiver_id uuid,
    p_candidate_hash text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_listing_id uuid;
    v_listing public.food_listings%ROWTYPE;
    v_claim public.claims%ROWTYPE;
    v_handshake public.pickup_handshakes%ROWTYPE;
    v_now timestamptz;
BEGIN
    -- Validate the backend-generated candidate hash.
    IF p_claim_id IS NULL
       OR p_receiver_id IS NULL
       OR p_candidate_hash IS NULL
       OR p_candidate_hash !~ '^[0-9a-f]{64}$' THEN
        RETURN jsonb_build_object(
            'success', false,
            'code', 'INVALID_HANDSHAKE'
        );
    END IF;

    -- Initial lookup only to discover the listing.
    -- Actual locking follows listing -> claim -> handshake.
    SELECT listing_id
    INTO v_listing_id
    FROM public.claims
    WHERE id = p_claim_id;

    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'success', false,
            'code', 'NOT_FOUND'
        );
    END IF;

    -- Lock the listing first, matching existing lifecycle functions.
    SELECT *
    INTO v_listing
    FROM public.food_listings
    WHERE id = v_listing_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'success', false,
            'code', 'NOT_FOUND'
        );
    END IF;

    -- Lock and re-read the claim after obtaining the listing lock.
    SELECT *
    INTO v_claim
    FROM public.claims
    WHERE id = p_claim_id
      AND listing_id = v_listing_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'success', false,
            'code', 'NOT_FOUND'
        );
    END IF;

    -- A receiver must never verify another receiver's claim.
    IF v_claim.receiver_id <> p_receiver_id THEN
        RETURN jsonb_build_object(
            'success', false,
            'code', 'FORBIDDEN'
        );
    END IF;

    -- Lock the handshake after the listing and claim.
    SELECT *
    INTO v_handshake
    FROM public.pickup_handshakes
    WHERE claim_id = p_claim_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'success', false,
            'code', 'NO_HANDSHAKE'
        );
    END IF;

    v_now := clock_timestamp();

    -- Prevent replay of a previously successful code.
    IF v_handshake.verified_at IS NOT NULL THEN
        RETURN jsonb_build_object(
            'success', false,
            'code', 'ALREADY_USED'
        );
    END IF;

    -- Reject handshakes invalidated by cancellation or expiry.
    IF v_handshake.invalidated_at IS NOT NULL THEN
        RETURN jsonb_build_object(
            'success', false,
            'code', 'INVALIDATED'
        );
    END IF;

    -- Reject claims that are no longer active.
    IF v_claim.status <> 'active' THEN
        RETURN jsonb_build_object(
            'success', false,
            'code', 'CONFLICT',
            'claim_status', v_claim.status
        );
    END IF;

    -- Check both claim expiry and food safety expiry.
    IF v_claim.expires_at <= v_now
       OR v_listing.safe_until <= v_now THEN

        -- This status change fires the invalidation trigger.
        UPDATE public.claims
        SET status = 'expired'
        WHERE id = p_claim_id
          AND status = 'active';

        -- Reopen the listing only if the food is still safe.
        UPDATE public.food_listings
        SET status = CASE
                WHEN safe_until > v_now THEN 'available'
                ELSE 'expired'
            END,
            updated_at = v_now
        WHERE id = v_listing_id
          AND status = 'claimed';

        RETURN jsonb_build_object(
            'success', false,
            'code', 'EXPIRED'
        );
    END IF;

    -- Enforce the five-attempt limit.
    IF v_handshake.attempts >= 5 THEN
        RETURN jsonb_build_object(
            'success', false,
            'code', 'LOCKED',
            'attempts', v_handshake.attempts
        );
    END IF;

    -- Do not complete a claim if its listing is not currently claimed.
    IF v_listing.status <> 'claimed' THEN
        RETURN jsonb_build_object(
            'success', false,
            'code', 'CONFLICT'
        );
    END IF;

    -- Incorrect code: persist the attempt while holding the row lock.
    IF v_handshake.code_hash <> p_candidate_hash THEN
        UPDATE public.pickup_handshakes
        SET attempts = attempts + 1
        WHERE claim_id = p_claim_id;

        RETURN jsonb_build_object(
            'success', false,
            'code', 'WRONG_CODE',
            'attempts', v_handshake.attempts + 1,
            'remaining_attempts', 5 - (v_handshake.attempts + 1)
        );
    END IF;

    -- Correct code: all three updates occur in this transaction.
    UPDATE public.pickup_handshakes
    SET verified_at = v_now
    WHERE claim_id = p_claim_id;

    UPDATE public.claims
    SET status = 'completed'
    WHERE id = p_claim_id;

    UPDATE public.food_listings
    SET status = 'picked_up',
        updated_at = v_now
    WHERE id = v_listing_id;

    RETURN jsonb_build_object(
        'success', true,
        'code', 'OK',
        'claim_id', p_claim_id,
        'listing_id', v_listing_id,
        'claim_status', 'completed',
        'listing_status', 'picked_up',
        'verified_at', v_now
    );
END;
$$;


-- =========================================================
-- 7. Restrict verification RPC to backend service role
-- =========================================================

REVOKE ALL ON FUNCTION public.verify_pickup_handshake(
    uuid, uuid, text
) FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION public.verify_pickup_handshake(
    uuid, uuid, text
) TO service_role;

COMMIT;
