BEGIN;

-- =========================================================
-- 1. Atomic pickup verification
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
    v_verified_at timestamptz;
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

        -- This status change fires migration 006's invalidation trigger.
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
-- 2. Restrict execution to the backend service role
-- =========================================================

REVOKE ALL ON FUNCTION public.verify_pickup_handshake(
    uuid, uuid, text
) FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION public.verify_pickup_handshake(
    uuid, uuid, text
) TO service_role;

COMMIT;
