BEGIN;

CREATE TABLE IF NOT EXISTS public.receiver_locations (
    receiver_id uuid PRIMARY KEY
        REFERENCES public.user_profiles(id) ON DELETE CASCADE,

    latitude numeric(9,6) NOT NULL,
    longitude numeric(9,6) NOT NULL,

    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),

    CONSTRAINT receiver_locations_latitude_check
        CHECK (latitude BETWEEN -90 AND 90),

    CONSTRAINT receiver_locations_longitude_check
        CHECK (longitude BETWEEN -180 AND 180)
);

ALTER TABLE public.receiver_locations ENABLE ROW LEVEL SECURITY;

REVOKE ALL PRIVILEGES
ON TABLE public.receiver_locations
FROM PUBLIC, anon, authenticated;

GRANT SELECT, INSERT, UPDATE, DELETE
ON TABLE public.receiver_locations
TO service_role;

COMMIT;
