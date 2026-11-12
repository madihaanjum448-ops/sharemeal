-- All lifecycle transitions use listing -> claim lock order to reduce deadlocks.
CREATE OR REPLACE FUNCTION public.claim_food_listing(p_listing_id uuid, p_receiver_id uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=public AS $$
DECLARE v_listing public.food_listings%ROWTYPE; v_claim public.claims%ROWTYPE; v_now timestamptz;
BEGIN
  SELECT * INTO v_listing FROM public.food_listings WHERE id=p_listing_id FOR UPDATE;
  IF NOT FOUND THEN RETURN jsonb_build_object('success',false,'code','NOT_FOUND','message','Listing not found'); END IF;
  v_now := clock_timestamp(); -- read after acquiring the listing lock
  IF v_listing.safe_until <= v_now THEN
    UPDATE public.claims SET status='expired'
      WHERE listing_id=p_listing_id AND status='active';
    UPDATE public.food_listings SET status='expired', updated_at=v_now
      WHERE id=p_listing_id AND status IN ('available','claimed');
    RETURN jsonb_build_object('success',false,'code','EXPIRED','message','Listing expired');
  END IF;
  -- Scheduler is cleanup, not the correctness guard: reconcile a stale timed-out claim inline.
  IF v_listing.status='claimed' THEN
    UPDATE public.claims SET status='expired'
      WHERE listing_id=p_listing_id AND status='active' AND expires_at <= v_now;
    IF FOUND THEN
      UPDATE public.food_listings SET status='available', updated_at=v_now
        WHERE id=p_listing_id AND status='claimed' AND safe_until > v_now;
      v_listing.status := 'available';
    END IF;
  END IF;
  IF v_listing.status <> 'available' THEN
    RETURN jsonb_build_object('success',false,'code','CONFLICT','message','Listing already claimed or unavailable');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM public.user_profiles WHERE id=p_receiver_id AND role='receiver' AND is_verified=true) THEN
    RETURN jsonb_build_object('success',false,'code','FORBIDDEN','message','Verified receiver required');
  END IF;
  IF EXISTS (SELECT 1 FROM public.claims WHERE listing_id=p_listing_id AND status='active') THEN
    RETURN jsonb_build_object('success',false,'code','CONFLICT','message','Active claim already exists');
  END IF;
  INSERT INTO public.claims(listing_id,receiver_id,status,claimed_at,expires_at)
    VALUES(p_listing_id,p_receiver_id,'active',v_now,v_now + interval '15 minutes') RETURNING * INTO v_claim;
  UPDATE public.food_listings SET status='claimed', updated_at=v_now WHERE id=p_listing_id;
  RETURN jsonb_build_object('success',true,'claim_id',v_claim.id,'listing_id',p_listing_id,
    'receiver_id',p_receiver_id,'status',v_claim.status,'claimed_at',v_claim.claimed_at,'expires_at',v_claim.expires_at);
EXCEPTION WHEN unique_violation THEN
  RETURN jsonb_build_object('success',false,'code','CONFLICT','message','Active claim already exists');
END; $$;

CREATE OR REPLACE FUNCTION public.cancel_food_claim(p_claim_id uuid, p_receiver_id uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=public AS $$
DECLARE v_listing_id uuid; v_listing public.food_listings%ROWTYPE; v_claim public.claims%ROWTYPE; v_now timestamptz;
BEGIN
  SELECT listing_id INTO v_listing_id FROM public.claims WHERE id=p_claim_id;
  IF NOT FOUND THEN RETURN jsonb_build_object('success',false,'code','NOT_FOUND','message','Claim not found'); END IF;
  SELECT * INTO v_listing FROM public.food_listings WHERE id=v_listing_id FOR UPDATE;
  IF NOT FOUND THEN RETURN jsonb_build_object('success',false,'code','NOT_FOUND','message','Listing not found'); END IF;
  SELECT * INTO v_claim FROM public.claims WHERE id=p_claim_id FOR UPDATE;
  v_now := clock_timestamp();
  IF v_claim.receiver_id <> p_receiver_id THEN RETURN jsonb_build_object('success',false,'code','FORBIDDEN','message','Claim owner required'); END IF;
  IF v_claim.status <> 'active' THEN RETURN jsonb_build_object('success',false,'code','CONFLICT','claim_status',v_claim.status); END IF;
  IF v_claim.expires_at <= v_now OR v_listing.safe_until <= v_now THEN
    UPDATE public.claims SET status='expired' WHERE id=p_claim_id AND status='active';
    UPDATE public.food_listings SET status=CASE WHEN safe_until > v_now THEN 'available' ELSE 'expired' END,
      updated_at=v_now WHERE id=v_listing_id AND status='claimed';
    RETURN jsonb_build_object('success',false,'code','EXPIRED','claim_status','expired');
  END IF;
  UPDATE public.claims SET status='cancelled' WHERE id=p_claim_id;
  IF v_listing.safe_until > v_now THEN
    UPDATE public.food_listings SET status='available', updated_at=v_now WHERE id=v_listing_id AND status='claimed';
  ELSE
    UPDATE public.food_listings SET status='expired', updated_at=v_now WHERE id=v_listing_id AND status='claimed';
  END IF;
  RETURN jsonb_build_object('success',true,'claim_status','cancelled','listing_status',
    CASE WHEN v_listing.safe_until > v_now THEN 'available' ELSE 'expired' END);
END; $$;

CREATE OR REPLACE FUNCTION public.process_expired_claims_and_listings()
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=public AS $$
DECLARE r record; v_now timestamptz := clock_timestamp(); v_claims int:=0; v_reopened int:=0; v_expired int:=0; v_rows int:=0;
BEGIN
  -- Food safety expiry takes precedence even if the 15-minute claim timer has not elapsed.
  FOR r IN SELECT l.id, c.id AS claim_id
    FROM public.food_listings l LEFT JOIN public.claims c ON c.listing_id=l.id AND c.status='active'
    WHERE l.status IN ('available','claimed') AND l.safe_until <= v_now
    ORDER BY l.id FOR UPDATE OF l SKIP LOCKED
  LOOP
    IF r.claim_id IS NOT NULL THEN
      UPDATE public.claims SET status='expired' WHERE id=r.claim_id AND status='active';
      IF FOUND THEN v_claims := v_claims + 1; END IF;
    END IF;
    UPDATE public.food_listings SET status='expired', updated_at=v_now
      WHERE id=r.id AND status IN ('available','claimed');
    IF FOUND THEN v_expired := v_expired + 1; END IF;
  END LOOP;

  -- Timeout only claims whose food remains safe; listing is reopened under the same row lock.
  FOR r IN SELECT l.id, c.id AS claim_id
    FROM public.food_listings l JOIN public.claims c ON c.listing_id=l.id
    WHERE l.status='claimed' AND c.status='active' AND c.expires_at <= v_now AND l.safe_until > v_now
    ORDER BY l.id FOR UPDATE OF l SKIP LOCKED
  LOOP
    UPDATE public.claims SET status='expired' WHERE id=r.claim_id AND status='active' AND expires_at <= v_now;
    IF FOUND THEN
      v_claims := v_claims + 1;
      UPDATE public.food_listings SET status='available', updated_at=v_now
        WHERE id=r.id AND status='claimed' AND safe_until > v_now;
      IF FOUND THEN v_reopened := v_reopened + 1; END IF;
    END IF;
  END LOOP;
  RETURN jsonb_build_object('expired_claims',v_claims,'reopened_listings',v_reopened,'expired_listings',v_expired);
END; $$;

-- Atomic donor edit; active claims and non-available states cannot be modified.
CREATE OR REPLACE FUNCTION public.update_food_listing(p_listing_id uuid, p_donor_id uuid, p_changes jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=public AS $$
DECLARE v_listing public.food_listings%ROWTYPE; v_safe_until timestamptz;
BEGIN
  SELECT * INTO v_listing FROM public.food_listings WHERE id=p_listing_id FOR UPDATE;
  IF NOT FOUND OR v_listing.donor_id <> p_donor_id THEN
    RETURN jsonb_build_object('success',false,'code','NOT_FOUND');
  END IF;
  IF v_listing.status <> 'available' OR EXISTS (SELECT 1 FROM public.claims WHERE listing_id=p_listing_id AND status='active') THEN
    RETURN jsonb_build_object('success',false,'code','CONFLICT');
  END IF;
  IF p_changes ? 'safe_until' THEN
    v_safe_until := (p_changes->>'safe_until')::timestamptz;
    IF v_safe_until <= clock_timestamp() THEN RETURN jsonb_build_object('success',false,'code','INVALID_SAFE_UNTIL'); END IF;
  END IF;
  UPDATE public.food_listings SET
    title=COALESCE(p_changes->>'title',title),
    description=CASE WHEN p_changes ? 'description' THEN p_changes->>'description' ELSE description END,
    food_category=COALESCE(p_changes->>'food_category',food_category),
    quantity=COALESCE(p_changes->>'quantity',quantity),
    servings=CASE WHEN p_changes ? 'servings' THEN NULLIF(p_changes->>'servings','')::integer ELSE servings END,
    pickup_address=COALESCE(p_changes->>'pickup_address',pickup_address),
    latitude=COALESCE((p_changes->>'latitude')::double precision,latitude),
    longitude=COALESCE((p_changes->>'longitude')::double precision,longitude),
    safe_until=COALESCE(v_safe_until,safe_until), updated_at=clock_timestamp()
  WHERE id=p_listing_id RETURNING * INTO v_listing;
  RETURN jsonb_build_object('success',true,'listing_id',v_listing.id,'status',v_listing.status);
END; $$;

CREATE OR REPLACE FUNCTION public.cancel_donor_listing(p_listing_id uuid, p_donor_id uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=public AS $$
DECLARE v_listing public.food_listings%ROWTYPE;
BEGIN
  SELECT * INTO v_listing FROM public.food_listings WHERE id=p_listing_id FOR UPDATE;
  IF NOT FOUND OR v_listing.donor_id <> p_donor_id THEN RETURN jsonb_build_object('success',false,'code','NOT_FOUND'); END IF;
  IF v_listing.status <> 'available' OR EXISTS (SELECT 1 FROM public.claims WHERE listing_id=p_listing_id AND status='active') THEN
    RETURN jsonb_build_object('success',false,'code','CONFLICT');
  END IF;
  UPDATE public.food_listings SET status='cancelled',updated_at=clock_timestamp() WHERE id=p_listing_id;
  RETURN jsonb_build_object('success',true,'listing_id',p_listing_id,'status','cancelled');
END; $$;

REVOKE ALL ON FUNCTION public.claim_food_listing(uuid,uuid) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.cancel_food_claim(uuid,uuid) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.process_expired_claims_and_listings() FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.update_food_listing(uuid,uuid,jsonb) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.cancel_donor_listing(uuid,uuid) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.claim_food_listing(uuid,uuid) TO service_role;
GRANT EXECUTE ON FUNCTION public.cancel_food_claim(uuid,uuid) TO service_role;
GRANT EXECUTE ON FUNCTION public.process_expired_claims_and_listings() TO service_role;
GRANT EXECUTE ON FUNCTION public.update_food_listing(uuid,uuid,jsonb) TO service_role;
GRANT EXECUTE ON FUNCTION public.cancel_donor_listing(uuid,uuid) TO service_role;
