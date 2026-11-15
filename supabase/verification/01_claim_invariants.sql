-- Read-only checks for the atomic claim invariant and RPC presence.
SELECT indexname, indexdef FROM pg_indexes
WHERE schemaname='public' AND tablename='claims'
  AND indexname='one_active_claim_per_listing';
SELECT proname, pg_get_function_identity_arguments(oid) AS arguments,
       pg_get_function_result(oid) AS result_type
FROM pg_proc WHERE pronamespace='public'::regnamespace
  AND proname IN ('claim_food_listing','cancel_food_claim','process_expired_claims_and_listings',
                  'update_food_listing','cancel_donor_listing')
ORDER BY proname;
SELECT listing_id, COUNT(*) AS active_claims
FROM public.claims WHERE status='active'
GROUP BY listing_id HAVING COUNT(*) > 1;
