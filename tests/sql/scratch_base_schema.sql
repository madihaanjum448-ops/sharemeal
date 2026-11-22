-- ============================================================================================
-- SCRATCH BASE SCHEMA - FOR THROWAWAY LOCAL TEST DATABASES ONLY. NEVER RUN AGAINST SUPABASE.
-- This is a minimal throwaway base schema for local PostgreSQL tests only. The test fixture
-- applies every repository migration afterward, including migration 005 which adds and populates
-- user_profiles.approval_status before the tests insert verified receiver profiles.
-- Columns below are inferred only for the core tables; use a disposable local database. Assumptions:
--   * claims has a partial UNIQUE index on (listing_id) WHERE status='active'
--     (claim_food_listing handles unique_violation, implying one exists)
--   * statuses are plain text; id columns are uuid primary keys
-- When you have a clone with your real migrations applied, set SHAREMEAL_TEST_SCRATCH_BASE=0.
-- ============================================================================================
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='anon')          THEN CREATE ROLE anon NOLOGIN; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN CREATE ROLE authenticated NOLOGIN; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='service_role')  THEN CREATE ROLE service_role NOLOGIN BYPASSRLS; END IF;
END $$;

GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;
-- Supabase grants everything on new public objects to these roles by default; mirror that so the
-- migrations' REVOKE statements are meaningfully tested.
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO anon, authenticated, service_role;

CREATE TABLE public.user_profiles (
  id uuid PRIMARY KEY, role text NOT NULL, is_verified boolean NOT NULL DEFAULT false, full_name text);

CREATE TABLE public.food_listings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), donor_id uuid, title text NOT NULL DEFAULT 'scratch',
  description text, food_category text DEFAULT 'human', quantity text DEFAULT '1', servings integer,
  pickup_address text DEFAULT 'scratch addr', latitude double precision DEFAULT 0, longitude double precision DEFAULT 0,
  safe_until timestamptz NOT NULL, status text NOT NULL DEFAULT 'available',
  created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE public.claims (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  listing_id uuid NOT NULL REFERENCES public.food_listings(id),
  receiver_id uuid NOT NULL REFERENCES public.user_profiles(id),
  status text NOT NULL DEFAULT 'active', claimed_at timestamptz NOT NULL DEFAULT now(), expires_at timestamptz NOT NULL);

CREATE UNIQUE INDEX uq_claims_one_active_per_listing ON public.claims (listing_id) WHERE status = 'active';
