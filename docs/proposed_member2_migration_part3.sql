-- PROPOSED part 3 (Member 2): alert tables. FOR REVIEW, NOT APPLIED.
-- Apply after receiver_locations, part 1 and part 2.
-- Tables only, no functions. Service-role access only, no RLS policies.
BEGIN;

CREATE TABLE IF NOT EXISTS public.alert_deliveries (
  listing_id uuid NOT NULL REFERENCES public.food_listings(id) ON DELETE CASCADE,
  receiver_id uuid NOT NULL REFERENCES public.user_profiles(id) ON DELETE CASCADE,
  channel text NOT NULL CHECK (channel IN ('telegram', 'web_push', 'in_app')),
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (listing_id, receiver_id)          -- one alert per receiver per listing
);
CREATE INDEX IF NOT EXISTS alert_deliveries_receiver_idx
  ON public.alert_deliveries (receiver_id, created_at DESC);

CREATE TABLE IF NOT EXISTS public.alert_attempts (
  listing_id uuid NOT NULL REFERENCES public.food_listings(id) ON DELETE CASCADE,
  receiver_id uuid NOT NULL REFERENCES public.user_profiles(id) ON DELETE CASCADE,
  attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (listing_id, receiver_id)
);

CREATE TABLE IF NOT EXISTS public.receiver_telegram_links (
  receiver_id uuid PRIMARY KEY REFERENCES public.user_profiles(id) ON DELETE CASCADE,
  chat_id text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.alert_deliveries ENABLE ROW LEVEL SECURITY;          -- no policies
ALTER TABLE public.alert_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.receiver_telegram_links ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.alert_deliveries, public.alert_attempts,
  public.receiver_telegram_links FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.alert_deliveries,
  public.alert_attempts, public.receiver_telegram_links TO service_role;

COMMIT;
-- ROLLBACK (manual): DROP TABLE public.alert_deliveries, public.alert_attempts,
--   public.receiver_telegram_links;
