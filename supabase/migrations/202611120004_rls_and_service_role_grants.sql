-- FastAPI uses the backend-only service_role key. Never expose this key to clients.
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.food_listings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.claims ENABLE ROW LEVEL SECURITY;
GRANT USAGE ON SCHEMA public TO service_role;
GRANT SELECT, INSERT, UPDATE ON public.user_profiles TO service_role;
GRANT SELECT, INSERT, UPDATE ON public.food_listings TO service_role;
GRANT SELECT, INSERT, UPDATE ON public.claims TO service_role;
-- No anon/authenticated table policies are created here: clients must use the API.
