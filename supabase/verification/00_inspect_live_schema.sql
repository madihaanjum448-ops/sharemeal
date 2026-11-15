-- Read-only inspection. Run before and after migrations; does not change data.
SELECT 'TABLE' AS item_type, tablename AS item_name
FROM pg_tables WHERE schemaname='public' AND tablename IN ('user_profiles','food_listings','claims')
UNION ALL
SELECT 'INDEX', tablename || ' -> ' || indexname
FROM pg_indexes WHERE schemaname='public' AND tablename IN ('user_profiles','food_listings','claims')
UNION ALL
SELECT 'FUNCTION', p.proname || '(' || pg_get_function_identity_arguments(p.oid) || ')'
FROM pg_proc p WHERE p.pronamespace='public'::regnamespace
  AND p.proname IN ('claim_food_listing','cancel_food_claim','process_expired_claims_and_listings')
UNION ALL
SELECT 'RLS', c.relname || ' enabled=' || c.relrowsecurity
FROM pg_class c WHERE c.relnamespace='public'::regnamespace AND c.relname IN ('user_profiles','food_listings','claims') AND c.relkind='r'
ORDER BY item_type, item_name;
