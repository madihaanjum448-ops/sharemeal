CREATE INDEX IF NOT EXISTS idx_food_listings_available_safe_until
  ON public.food_listings(status, safe_until) WHERE status='available';
CREATE INDEX IF NOT EXISTS idx_food_listings_donor_created
  ON public.food_listings(donor_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_claims_receiver_claimed
  ON public.claims(receiver_id, claimed_at DESC);
CREATE INDEX IF NOT EXISTS idx_claims_active_expiry
  ON public.claims(expires_at) WHERE status='active';
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM public.claims WHERE status='active' GROUP BY listing_id HAVING COUNT(*) > 1) THEN
    RAISE EXCEPTION 'Cannot create one_active_claim_per_listing: duplicate active claims exist. Review and reconcile these rows first.';
  END IF;
END $$;
CREATE UNIQUE INDEX IF NOT EXISTS one_active_claim_per_listing
  ON public.claims(listing_id) WHERE status='active';
