-- Day 4 Task 1: persistent, idempotent timeout-strike processing.
-- Depends on: 202611120003 (claims/listings lifecycle), 202611120006 (pickup_handshakes).
-- Safe to re-run: every statement is IF NOT EXISTS / OR REPLACE / idempotent GRANT.
BEGIN;

-- =========================================================
-- 1. Append-only strike event log
-- =========================================================
CREATE TABLE IF NOT EXISTS public.strike_events (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    receiver_id uuid NOT NULL,
    claim_id    uuid REFERENCES public.claims(id) ON DELETE RESTRICT,
    event_type  text NOT NULL CHECK (event_type IN ('timeout', 'admin_clear')),
    reason      text NOT NULL,
    -- When the event happened (for a timeout: the moment the claim's 15-minute timer ended).
    created_at  timestamptz NOT NULL,
    -- When this row was written (audit; differs from created_at if the worker was late).
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT strike_events_timeout_needs_claim
        CHECK (event_type <> 'timeout' OR claim_id IS NOT NULL)
);

-- Idempotency guarantee: a claim can produce AT MOST ONE timeout strike, enforced by the database.
CREATE UNIQUE INDEX IF NOT EXISTS uq_strike_events_one_timeout_per_claim
    ON public.strike_events (claim_id)
    WHERE event_type = 'timeout';

CREATE INDEX IF NOT EXISTS ix_strike_events_receiver_time
    ON public.strike_events (receiver_id, created_at);

ALTER TABLE public.strike_events ENABLE ROW LEVEL SECURITY;

-- service_role is revoked too: Supabase default privileges grant it ALL on new tables, which would
-- otherwise leave UPDATE / DELETE / TRUNCATE in place and defeat the append-only audit log.
REVOKE ALL ON TABLE public.strike_events FROM PUBLIC, anon, authenticated, service_role;
-- Append-only: the backend role may read and add events, never rewrite or erase them.
GRANT SELECT, INSERT ON TABLE public.strike_events TO service_role;


-- =========================================================
-- 2. apply_timeout_strikes(): derive strikes from persisted claim state
-- =========================================================
-- A strike is recorded for a claim that satisfies ALL of:
--   * status = 'expired'                      (so never for cancelled / completed / active claims)
--   * expires_at < listing.safe_until         (the 15-minute timer ended while the food was still
--                                              safe; food-safety expiry wins when safe_until came first)
--   * no verified pickup handshake            (the receiver did not actually show up)
--   * expires_at within the lookback window   (bounded scan; no unbounded retroactive punishment)
-- Eligibility is read from rows, not from the sweep's counters, so timeouts reconciled inline by
-- claim_food_listing() or by a late cancel_food_claim() are covered too.
CREATE OR REPLACE FUNCTION public.apply_timeout_strikes(
    p_lookback interval DEFAULT interval '48 hours'
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_now   timestamptz := clock_timestamp();
    v_added integer := 0;
BEGIN
    IF p_lookback IS NULL OR p_lookback <= interval '0' THEN
        RAISE EXCEPTION 'p_lookback must be a positive interval';
    END IF;

    INSERT INTO public.strike_events (receiver_id, claim_id, event_type, reason, created_at)
    SELECT c.receiver_id, c.id, 'timeout', 'claim timed out', c.expires_at
    FROM public.claims c
    JOIN public.food_listings l ON l.id = c.listing_id
    WHERE c.status = 'expired'
      AND c.expires_at <= v_now
      AND c.expires_at >= v_now - p_lookback
      AND c.expires_at < l.safe_until
      AND NOT EXISTS (
            SELECT 1 FROM public.pickup_handshakes h
            WHERE h.claim_id = c.id AND h.verified_at IS NOT NULL)
    -- Deterministic order => concurrent workers acquire unique-index entries in the same order.
    ORDER BY c.expires_at, c.id
    ON CONFLICT (claim_id) WHERE event_type = 'timeout' DO NOTHING;

    GET DIAGNOSTICS v_added = ROW_COUNT;
    RETURN jsonb_build_object('strikes_added', v_added);
END;
$$;

REVOKE ALL ON FUNCTION public.apply_timeout_strikes(interval) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.apply_timeout_strikes(interval) TO service_role;

COMMIT;
