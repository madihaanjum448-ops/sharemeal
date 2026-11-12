-- Idempotent baseline definitions. Existing rows/tables are preserved.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE TABLE IF NOT EXISTS public.user_profiles (
  id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  full_name text NOT NULL,
  phone text UNIQUE,
  role text NOT NULL CHECK (role IN ('donor','receiver','admin')),
  organization_name text,
  is_verified boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS public.food_listings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  donor_id uuid NOT NULL REFERENCES public.user_profiles(id),
  title text NOT NULL,
  description text,
  food_category text NOT NULL CHECK (food_category IN ('human','animal')),
  quantity text NOT NULL,
  servings integer CHECK (servings IS NULL OR servings > 0),
  pickup_address text NOT NULL,
  latitude double precision NOT NULL CHECK (latitude BETWEEN -90 AND 90),
  longitude double precision NOT NULL CHECK (longitude BETWEEN -180 AND 180),
  safe_until timestamptz NOT NULL,
  status text NOT NULL DEFAULT 'available' CHECK (status IN ('available','claimed','picked_up','cancelled','expired')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (safe_until > created_at)
);
CREATE TABLE IF NOT EXISTS public.claims (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  listing_id uuid NOT NULL REFERENCES public.food_listings(id),
  receiver_id uuid NOT NULL REFERENCES public.user_profiles(id),
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','completed','cancelled','expired')),
  claimed_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- ShareMeal additive baseline. Run against a backed-up project after reviewing existing columns.
-- Assumes public.user_profiles, public.food_listings and public.claims already exist.
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='food_listings_safe_until_after_created') THEN
    ALTER TABLE public.food_listings ADD CONSTRAINT food_listings_safe_until_after_created
      CHECK (safe_until > created_at) NOT VALID;
  END IF;
END $$;
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='food_listings_latitude_range') THEN
    ALTER TABLE public.food_listings ADD CONSTRAINT food_listings_latitude_range CHECK (latitude BETWEEN -90 AND 90) NOT VALID;
  END IF;
END $$;
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='food_listings_longitude_range') THEN
    ALTER TABLE public.food_listings ADD CONSTRAINT food_listings_longitude_range CHECK (longitude BETWEEN -180 AND 180) NOT VALID;
  END IF;
END $$;
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='claims_status_valid') THEN
    ALTER TABLE public.claims ADD CONSTRAINT claims_status_valid
      CHECK (status IN ('active','completed','cancelled','expired')) NOT VALID;
  END IF;
END $$;
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='food_listings_status_valid') THEN
    ALTER TABLE public.food_listings ADD CONSTRAINT food_listings_status_valid
      CHECK (status IN ('available','claimed','picked_up','cancelled','expired')) NOT VALID;
  END IF;
END $$;
