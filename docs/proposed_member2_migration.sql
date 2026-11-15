-- PROPOSED migration for review (Member 2). Do NOT apply before review.
-- Verify table/column/status names against the real schema first.
-- Idempotent and backward compatible: every new column is nullable or defaulted.

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

-- Existing receivers keep today's behaviour (they could see every listing).
UPDATE public.user_profiles
   SET accepts_food_category = 'both'
 WHERE role = 'receiver' AND accepts_food_category IS NULL;

-- Serves the matching query: approved, unflagged receivers only.
CREATE INDEX IF NOT EXISTS idx_user_profiles_matchable_receivers
  ON public.user_profiles (accepts_food_category)
  WHERE role = 'receiver'
    AND approval_status = 'approved'
    AND is_verified = TRUE
    AND is_flagged = FALSE;

-- 2. claims: handshake fields ------------------------------------------------
ALTER TABLE public.claims
  ADD COLUMN IF NOT EXISTS handshake_code_hash   text,
  ADD COLUMN IF NOT EXISTS handshake_expires_at  timestamptz,
  ADD COLUMN IF NOT EXISTS handshake_attempts    integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS handshake_locked_at   timestamptz,
  ADD COLUMN IF NOT EXISTS handshake_verified_at timestamptz;

ALTER TABLE public.claims DROP CONSTRAINT IF EXISTS claims_handshake_hash_format;
ALTER TABLE public.claims
  ADD CONSTRAINT claims_handshake_hash_format
  CHECK (handshake_code_hash IS NULL
         OR handshake_code_hash ~ '^[0-9a-f]{64}$');   -- HMAC-SHA256 hex; a plain 4-digit code is rejected

ALTER TABLE public.claims DROP CONSTRAINT IF EXISTS claims_handshake_attempts_check;
ALTER TABLE public.claims
  ADD CONSTRAINT claims_handshake_attempts_check CHECK (handshake_attempts >= 0);

ALTER TABLE public.claims DROP CONSTRAINT IF EXISTS claims_handshake_expiry_required;
ALTER TABLE public.claims
  ADD CONSTRAINT claims_handshake_expiry_required
  CHECK (handshake_code_hash IS NULL OR handshake_expires_at IS NOT NULL);

ALTER TABLE public.claims DROP CONSTRAINT IF EXISTS claims_handshake_verified_needs_hash;
ALTER TABLE public.claims
  ADD CONSTRAINT claims_handshake_verified_needs_hash
  CHECK (handshake_verified_at IS NULL OR handshake_code_hash IS NOT NULL);

-- No extra claims index: every handshake lookup is by primary key.

-- 3. Start the handshake (called by the backend right after a claim is created)
CREATE OR REPLACE FUNCTION public.start_claim_handshake(
  p_claim_id uuid, p_code_hash text
) RETURNS timestamptz
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_expires timestamptz;
BEGIN
  UPDATE public.claims
     SET handshake_code_hash  = p_code_hash,
         handshake_expires_at = expires_at,     -- same lifetime as the claim lock
         handshake_attempts   = 0,
         handshake_locked_at  = NULL
   WHERE id = p_claim_id
     AND status = 'active'
     AND handshake_code_hash IS NULL
  RETURNING handshake_expires_at INTO v_expires;
  RETURN v_expires;                              -- NULL = nothing started
END $$;

-- 4. Confirm pickup: one atomic transition, safe against races and replays
CREATE OR REPLACE FUNCTION public.confirm_claim_pickup(
  p_claim_id uuid, p_actor_id uuid, p_candidate_hash text,
  p_max_attempts integer DEFAULT 5
) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE c public.claims%ROWTYPE;
BEGIN
  SELECT * INTO c FROM public.claims WHERE id = p_claim_id FOR UPDATE;
  IF NOT FOUND OR c.receiver_id <> p_actor_id THEN RETURN 'not_found'; END IF;
  IF c.handshake_verified_at IS NOT NULL OR c.status = 'completed' THEN
    RETURN 'already_used';
  END IF;
  IF c.status <> 'active' THEN RETURN 'claim_not_active'; END IF;
  IF c.handshake_code_hash IS NULL THEN RETURN 'no_handshake'; END IF;
  -- Server clock only. Works even if the expiry sweep has not run yet.
  IF now() >= LEAST(c.expires_at, c.handshake_expires_at) THEN
    RETURN 'expired';
  END IF;
  IF c.handshake_locked_at IS NOT NULL OR c.handshake_attempts >= p_max_attempts THEN
    RETURN 'locked';
  END IF;

  IF c.handshake_code_hash = p_candidate_hash THEN
    UPDATE public.claims
       SET status = 'completed', handshake_verified_at = now()
     WHERE id = c.id;
    UPDATE public.food_listings SET status = 'picked_up' WHERE id = c.listing_id;
    RETURN 'ok';
  END IF;

  UPDATE public.claims
     SET handshake_attempts = c.handshake_attempts + 1,
         handshake_locked_at = CASE
           WHEN c.handshake_attempts + 1 >= p_max_attempts THEN now() END
   WHERE id = c.id;
  RETURN 'wrong_code';                           -- returns, never raises, so the count persists
END $$;

REVOKE ALL ON FUNCTION public.start_claim_handshake(uuid, text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.confirm_claim_pickup(uuid, uuid, text, integer) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.start_claim_handshake(uuid, text) TO service_role;
GRANT EXECUTE ON FUNCTION public.confirm_claim_pickup(uuid, uuid, text, integer) TO service_role;

COMMIT;

-- ROLLBACK (manual): drop both functions, the five handshake columns on claims,
-- the index, and the two user_profiles columns.
