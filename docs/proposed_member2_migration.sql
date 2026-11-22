-- PROPOSED migration v2 (Member 2), revised after Member 1 review.
-- Do NOT apply before review. Verify names against the live schema first.
-- Backward compatible: every new column is nullable or defaulted.

BEGIN;

-- 1. user_profiles ---------------------------------------------------------
ALTER TABLE public.user_profiles
  ADD COLUMN IF NOT EXISTS accepts_food_category text,
  ADD COLUMN IF NOT EXISTS is_flagged boolean NOT NULL DEFAULT FALSE;

ALTER TABLE public.user_profiles
  DROP CONSTRAINT IF EXISTS user_profiles_accepts_food_category_check;
ALTER TABLE public.user_profiles
  ADD CONSTRAINT user_profiles_accepts_food_category_check
  CHECK (accepts_food_category IS NULL
         OR accepts_food_category IN ('human', 'animal', 'both'));

UPDATE public.user_profiles
   SET accepts_food_category = 'both'
 WHERE role = 'receiver' AND approval_status = 'approved'
   AND accepts_food_category IS NULL;   -- pending receivers must choose

CREATE INDEX IF NOT EXISTS idx_user_profiles_matchable_receivers
  ON public.user_profiles (accepts_food_category)
  WHERE role = 'receiver' AND approval_status = 'approved'
    AND is_verified = TRUE AND is_flagged = FALSE;

-- 2. claims: handshake fields (service-role access only, see grants below) --
ALTER TABLE public.claims
  ADD COLUMN IF NOT EXISTS handshake_code_hash            text,
  ADD COLUMN IF NOT EXISTS handshake_expires_at           timestamptz,
  ADD COLUMN IF NOT EXISTS handshake_attempts             integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS handshake_locked_at            timestamptz,
  ADD COLUMN IF NOT EXISTS handshake_verified_at          timestamptz,
  ADD COLUMN IF NOT EXISTS handshake_review_required      boolean NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS handshake_review_resolved_at   timestamptz,
  ADD COLUMN IF NOT EXISTS handshake_review_resolved_by   uuid REFERENCES public.user_profiles(id);

ALTER TABLE public.claims DROP CONSTRAINT IF EXISTS claims_handshake_hash_format;
ALTER TABLE public.claims ADD CONSTRAINT claims_handshake_hash_format
  CHECK (handshake_code_hash IS NULL
         OR handshake_code_hash ~ '^[0-9a-f]{64}$');      -- HMAC-SHA256 hex; plain codes rejected

-- CHANGE 1: attempts limited to 0-5
ALTER TABLE public.claims DROP CONSTRAINT IF EXISTS claims_handshake_attempts_check;
ALTER TABLE public.claims ADD CONSTRAINT claims_handshake_attempts_check
  CHECK (handshake_attempts BETWEEN 0 AND 5);

ALTER TABLE public.claims DROP CONSTRAINT IF EXISTS claims_handshake_expiry_required;
ALTER TABLE public.claims ADD CONSTRAINT claims_handshake_expiry_required
  CHECK (handshake_code_hash IS NULL OR handshake_expires_at IS NOT NULL);

-- CHANGE 5: handshake expiry always equals the existing claim expiry
ALTER TABLE public.claims DROP CONSTRAINT IF EXISTS claims_handshake_expiry_matches_claim;
ALTER TABLE public.claims ADD CONSTRAINT claims_handshake_expiry_matches_claim
  CHECK (handshake_expires_at IS NULL OR handshake_expires_at = expires_at);

ALTER TABLE public.claims DROP CONSTRAINT IF EXISTS claims_handshake_verified_needs_hash;
ALTER TABLE public.claims ADD CONSTRAINT claims_handshake_verified_needs_hash
  CHECK (handshake_verified_at IS NULL OR handshake_code_hash IS NOT NULL);

-- CHANGE 3: persistent review flag, only valid on a locked claim
ALTER TABLE public.claims DROP CONSTRAINT IF EXISTS claims_handshake_review_needs_lock;
ALTER TABLE public.claims ADD CONSTRAINT claims_handshake_review_needs_lock
  CHECK (NOT handshake_review_required OR handshake_locked_at IS NOT NULL);

ALTER TABLE public.claims DROP CONSTRAINT IF EXISTS claims_handshake_resolved_needs_review;
ALTER TABLE public.claims ADD CONSTRAINT claims_handshake_resolved_needs_review
  CHECK (handshake_review_resolved_at IS NULL OR handshake_review_required);

-- Admin review queue: locked claims nobody has resolved yet
CREATE INDEX IF NOT EXISTS idx_claims_handshake_review_queue
  ON public.claims (handshake_locked_at)
  WHERE handshake_review_required AND handshake_review_resolved_at IS NULL;

-- 3. Strike events (append-only, auditable, idempotent per claim) -----------
CREATE TABLE IF NOT EXISTS public.receiver_strike_events (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  receiver_id uuid NOT NULL REFERENCES public.user_profiles(id),
  claim_id    uuid REFERENCES public.claims(id),
  event_type  text NOT NULL CHECK (event_type IN ('timeout', 'admin_clear')),
  reason      text,
  actor_id    uuid REFERENCES public.user_profiles(id),
  created_at  timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT receiver_strike_events_one_per_claim UNIQUE (claim_id, event_type),
  CONSTRAINT receiver_strike_events_timeout_needs_claim
    CHECK (event_type <> 'timeout' OR claim_id IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS idx_strike_events_receiver
  ON public.receiver_strike_events (receiver_id, event_type, created_at);

ALTER TABLE public.receiver_strike_events ENABLE ROW LEVEL SECURITY;  -- no policies = service role only
REVOKE ALL ON TABLE public.receiver_strike_events FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT ON TABLE public.receiver_strike_events TO service_role;

-- 4. Handshake functions ------------------------------------------------------
DROP FUNCTION IF EXISTS public.confirm_claim_pickup(uuid, uuid, text, integer);

-- CHANGE 2: starts only for an ACTIVE, UNEXPIRED claim without a code yet
CREATE OR REPLACE FUNCTION public.start_claim_handshake(
  p_claim_id uuid, p_code_hash text
) RETURNS timestamptz
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_expires timestamptz;
BEGIN
  UPDATE public.claims
     SET handshake_code_hash  = p_code_hash,
         handshake_expires_at = expires_at,            -- CHANGE 5: same 15-minute lifetime
         handshake_attempts   = 0,
         handshake_locked_at  = NULL
   WHERE id = p_claim_id
     AND status = 'active'
     AND expires_at > now()
     AND handshake_code_hash IS NULL
  RETURNING handshake_expires_at INTO v_expires;
  RETURN v_expires;                                    -- NULL means nothing was started
END $$;

CREATE OR REPLACE FUNCTION public.confirm_claim_pickup(
  p_claim_id uuid, p_actor_id uuid, p_candidate_hash text
) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
  c public.claims%ROWTYPE;
  v_listing public.food_listings%ROWTYPE;
  v_max CONSTANT integer := 5;                         -- must match the 0-5 check above
  v_attempts integer;
BEGIN
  -- Lock order matches Member 1's functions (listing first, then claim) to avoid deadlocks.
  SELECT * INTO c FROM public.claims WHERE id = p_claim_id;
  IF NOT FOUND THEN RETURN 'not_found'; END IF;
  SELECT * INTO v_listing FROM public.food_listings WHERE id = c.listing_id FOR UPDATE;
  SELECT * INTO c FROM public.claims WHERE id = p_claim_id FOR UPDATE;
  IF NOT FOUND OR c.receiver_id <> p_actor_id THEN RETURN 'not_found'; END IF;
  IF c.handshake_verified_at IS NOT NULL OR c.status = 'completed' THEN
    RETURN 'already_used';
  END IF;
  IF c.status <> 'active' THEN RETURN 'claim_not_active'; END IF;
  IF c.handshake_code_hash IS NULL THEN RETURN 'no_handshake'; END IF;
  -- Server clock only. The food-safety window also blocks pickup, even if the sweep has not run yet.
  IF now() >= LEAST(c.expires_at, c.handshake_expires_at)
     OR v_listing.safe_until <= now() THEN
    RETURN 'expired';
  END IF;
  IF c.handshake_locked_at IS NOT NULL OR c.handshake_attempts >= v_max THEN
    RETURN 'locked';
  END IF;

  IF c.handshake_code_hash = p_candidate_hash THEN
    UPDATE public.claims
       SET status = 'completed', handshake_verified_at = now()
     WHERE id = c.id;
    UPDATE public.food_listings SET status = 'picked_up', updated_at = clock_timestamp()
     WHERE id = c.listing_id AND status = 'claimed';
    RETURN 'ok';
  END IF;

  v_attempts := c.handshake_attempts + 1;
  UPDATE public.claims
     SET handshake_attempts = v_attempts,
         handshake_locked_at = CASE WHEN v_attempts >= v_max THEN now()
                                    ELSE handshake_locked_at END,
         -- CHANGE 3: five wrong attempts send the claim to admin review
         handshake_review_required = (handshake_review_required OR v_attempts >= v_max)
   WHERE id = c.id;
  RETURN CASE WHEN v_attempts >= v_max THEN 'locked' ELSE 'wrong_code' END;
END $$;

-- CHANGE 4: timeout strikes, skipping claims locked for admin review.
-- The expiry worker calls this right AFTER expire_claims. Idempotent: the
-- UNIQUE (claim_id, event_type) constraint blocks a second strike per claim.
-- Only claims that had a handshake are struck, so old expired claims get none.
CREATE OR REPLACE FUNCTION public.apply_timeout_strikes() RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_added integer;
BEGIN
  WITH ins AS (
    INSERT INTO public.receiver_strike_events (receiver_id, claim_id, event_type, reason)
    SELECT c.receiver_id, c.id, 'timeout', 'claim timed out without pickup'
      FROM public.claims c
      JOIN public.food_listings l ON l.id = c.listing_id
     WHERE c.status = 'expired'
       AND l.safe_until > c.expires_at                -- food-safety expiry is not the receiver's fault
       AND c.handshake_code_hash IS NOT NULL
       AND c.handshake_verified_at IS NULL
       AND NOT c.handshake_review_required            -- locked claims: no automatic strike
    ON CONFLICT (claim_id, event_type) DO NOTHING
    RETURNING 1
  )
  SELECT count(*) INTO v_added FROM ins;

  -- flag receivers with 3 or more timeout strikes since their last admin clear
  UPDATE public.user_profiles p
     SET is_flagged = TRUE
   WHERE p.role = 'receiver' AND NOT p.is_flagged
     AND (SELECT count(*) FROM public.receiver_strike_events e
           WHERE e.receiver_id = p.id AND e.event_type = 'timeout'
             AND e.created_at > COALESCE(
                   (SELECT max(a.created_at) FROM public.receiver_strike_events a
                     WHERE a.receiver_id = p.id AND a.event_type = 'admin_clear'),
                   '-infinity'::timestamptz)) >= 3;
  RETURN v_added;
END $$;

-- Admin closes a handshake review. The flag stays TRUE (persistent), so the
-- claim never receives an automatic strike afterwards.
CREATE OR REPLACE FUNCTION public.resolve_handshake_review(
  p_claim_id uuid, p_admin_id uuid
) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_done integer;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM public.user_profiles
                  WHERE id = p_admin_id AND role = 'admin') THEN
    RETURN 'not_admin';
  END IF;
  UPDATE public.claims
     SET handshake_review_resolved_at = now(),
         handshake_review_resolved_by = p_admin_id
   WHERE id = p_claim_id
     AND handshake_review_required
     AND handshake_review_resolved_at IS NULL;
  GET DIAGNOSTICS v_done = ROW_COUNT;
  RETURN CASE WHEN v_done = 1 THEN 'ok' ELSE 'not_found' END;
END $$;

-- 5. Grants: service role only -------------------------------------------------
REVOKE ALL ON FUNCTION public.start_claim_handshake(uuid, text)
  FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.confirm_claim_pickup(uuid, uuid, text)
  FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.apply_timeout_strikes()
  FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.resolve_handshake_review(uuid, uuid)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.start_claim_handshake(uuid, text) TO service_role;
GRANT EXECUTE ON FUNCTION public.confirm_claim_pickup(uuid, uuid, text) TO service_role;
GRANT EXECUTE ON FUNCTION public.apply_timeout_strikes() TO service_role;
GRANT EXECUTE ON FUNCTION public.resolve_handshake_review(uuid, uuid) TO service_role;

COMMIT;

-- ROLLBACK (manual): drop the four functions, receiver_strike_events, the eight
-- handshake columns on claims, the two indexes, and the two user_profiles columns.
