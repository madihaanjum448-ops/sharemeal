
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

ALTER TABLE public.pickup_handshakes ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.pickup_handshakes
    FROM PUBLIC, anon, authenticated;

GRANT SELECT, INSERT, UPDATE
    ON TABLE public.pickup_handshakes
    TO service_role;


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

    IF NOT EXISTS (
        SELECT 1
        FROM public.user_profiles
        WHERE id = p_receiver_id
          AND role = 'receiver'
          AND is_verified = true
    ) THEN
        RETURN jsonb_build_object(
            'success', false,
            'code', 'FORBIDDEN',
            'message', 'Verified receiver required'
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

DROP FUNCTION public.claim_food_listing(uuid, uuid);


-- =========================================================
-- 5. Restrict new RPC to backend service role
-- =========================================================

REVOKE ALL ON FUNCTION public.claim_food_listing(
    uuid, uuid, uuid, text
) FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION public.claim_food_listing(
    uuid, uuid, uuid, text
) TO service_role;

COMMIT;
