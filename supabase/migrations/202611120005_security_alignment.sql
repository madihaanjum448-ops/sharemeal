
-- ShareMeal security and migration alignment.
-- Preserve existing account data and lifecycle function logic.

BEGIN;

-- 1. Ensure approval_status exists for fresh installations.
ALTER TABLE public.user_profiles
ADD COLUMN IF NOT EXISTS approval_status text;

-- Preserve existing approval statuses.
UPDATE public.user_profiles
SET approval_status = CASE
    WHEN is_verified = TRUE THEN 'approved'
    ELSE 'pending'
END
WHERE role = 'receiver'
  AND approval_status IS NULL;

UPDATE public.user_profiles
SET approval_status = NULL
WHERE role <> 'receiver'
  AND approval_status IS NOT NULL;

-- 2. Add approval constraint only if missing.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'public.user_profiles'::regclass
          AND conname = 'user_profiles_approval_status_check'
    ) THEN
        ALTER TABLE public.user_profiles
        ADD CONSTRAINT user_profiles_approval_status_check
        CHECK (
            (
                role = 'receiver'
                AND approval_status IN ('pending', 'approved', 'rejected')
            )
            OR
            (
                role <> 'receiver'
                AND approval_status IS NULL
            )
        ) NOT VALID;
    END IF;
END
$$;

ALTER TABLE public.user_profiles
VALIDATE CONSTRAINT user_profiles_approval_status_check;

-- 3. Remove direct table privileges from client roles.
REVOKE ALL PRIVILEGES
ON TABLE public.user_profiles, public.food_listings, public.claims
FROM anon, authenticated;

-- 4. Restrict lifecycle functions to backend service_role.
REVOKE ALL ON FUNCTION public.claim_food_listing(uuid, uuid)
FROM PUBLIC, anon, authenticated;

REVOKE ALL ON FUNCTION public.cancel_food_claim(uuid, uuid)
FROM PUBLIC, anon, authenticated;

REVOKE ALL ON FUNCTION public.process_expired_claims_and_listings()
FROM PUBLIC, anon, authenticated;

REVOKE ALL ON FUNCTION public.update_food_listing(uuid, uuid, jsonb)
FROM PUBLIC, anon, authenticated;

REVOKE ALL ON FUNCTION public.cancel_donor_listing(uuid, uuid)
FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION public.claim_food_listing(uuid, uuid)
TO service_role;

GRANT EXECUTE ON FUNCTION public.cancel_food_claim(uuid, uuid)
TO service_role;

GRANT EXECUTE ON FUNCTION public.process_expired_claims_and_listings()
TO service_role;

GRANT EXECUTE ON FUNCTION public.update_food_listing(uuid, uuid, jsonb)
TO service_role;

GRANT EXECUTE ON FUNCTION public.cancel_donor_listing(uuid, uuid)
TO service_role;

-- 5. Secure search_path for SECURITY DEFINER functions.
ALTER FUNCTION public.claim_food_listing(uuid, uuid)
SET search_path = public, pg_temp;

ALTER FUNCTION public.cancel_food_claim(uuid, uuid)
SET search_path = public, pg_temp;

ALTER FUNCTION public.process_expired_claims_and_listings()
SET search_path = public, pg_temp;

ALTER FUNCTION public.update_food_listing(uuid, uuid, jsonb)
SET search_path = public, pg_temp;

ALTER FUNCTION public.cancel_donor_listing(uuid, uuid)
SET search_path = public, pg_temp;

COMMIT;
