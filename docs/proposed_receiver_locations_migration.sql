-- PROPOSED receiver_locations migration (Member 2), FOR COMPARISON ONLY.
-- Member 1's local migration is the source of truth. This is the schema the
-- Member 2 code was written against (PUT/GET /receivers/me/location).
BEGIN;

CREATE TABLE IF NOT EXISTS public.receiver_locations (
  receiver_id uuid PRIMARY KEY REFERENCES public.user_profiles(id) ON DELETE CASCADE,
  latitude    numeric(9,6) NOT NULL,
  longitude   numeric(9,6) NOT NULL,
  updated_at  timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT receiver_locations_latitude_range  CHECK (latitude  BETWEEN -90  AND 90),
  CONSTRAINT receiver_locations_longitude_range CHECK (longitude BETWEEN -180 AND 180)
);

ALTER TABLE public.receiver_locations ENABLE ROW LEVEL SECURITY;   -- no policies
REVOKE ALL ON TABLE public.receiver_locations FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.receiver_locations TO service_role;

COMMIT;
-- ROLLBACK (manual): DROP TABLE public.receiver_locations;
