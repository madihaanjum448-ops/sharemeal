-- PROPOSED migration PART 2 (Member 2). Run AFTER part 1. Do NOT apply before review.
-- Adds: shared admin audit log, receiver approve/reject, flag clearing,
-- and an audited version of resolve_handshake_review.

BEGIN;

-- 1. One append-only audit log for every admin action ------------------------
CREATE TABLE IF NOT EXISTS public.admin_audit_log (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_id    uuid NOT NULL REFERENCES public.user_profiles(id),
  action      text NOT NULL CHECK (action IN
              ('receiver_approved', 'receiver_rejected', 'flag_cleared',
               'handshake_review_resolved')),
  target_type text NOT NULL CHECK (target_type IN ('receiver', 'claim')),
  target_id   uuid NOT NULL,
  reason      text,
  created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_admin_audit_target
  ON public.admin_audit_log (target_type, target_id, created_at);

ALTER TABLE public.admin_audit_log ENABLE ROW LEVEL SECURITY;   -- no policies
REVOKE ALL ON TABLE public.admin_audit_log FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT ON TABLE public.admin_audit_log TO service_role;  -- no UPDATE/DELETE

-- 2. Approve or reject a receiver application --------------------------------
CREATE OR REPLACE FUNCTION public.decide_receiver_application(
  p_receiver_id uuid, p_admin_id uuid, p_decision text, p_reason text DEFAULT NULL
) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE r public.user_profiles%ROWTYPE;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM public.user_profiles
                  WHERE id = p_admin_id AND role = 'admin') THEN
    RETURN 'not_admin';
  END IF;
  IF p_decision NOT IN ('approve', 'reject') THEN RETURN 'invalid_decision'; END IF;

  SELECT * INTO r FROM public.user_profiles WHERE id = p_receiver_id FOR UPDATE;
  IF NOT FOUND OR r.role <> 'receiver' THEN RETURN 'not_receiver'; END IF;
  IF r.approval_status IS NOT NULL AND r.approval_status <> 'pending' THEN
    RETURN 'already_decided';
  END IF;
  IF p_decision = 'reject' AND (p_reason IS NULL OR btrim(p_reason) = '') THEN
    RETURN 'reason_required';
  END IF;
  -- cannot approve a receiver who never said what food they accept
  IF p_decision = 'approve' AND r.accepts_food_category IS NULL THEN
    RETURN 'category_required';
  END IF;

  UPDATE public.user_profiles
     SET approval_status = CASE WHEN p_decision = 'approve' THEN 'approved' ELSE 'rejected' END,
         is_verified     = (p_decision = 'approve')       -- both fields change together
   WHERE id = p_receiver_id;

  INSERT INTO public.admin_audit_log (actor_id, action, target_type, target_id, reason)
  VALUES (p_admin_id,
          CASE WHEN p_decision = 'approve' THEN 'receiver_approved' ELSE 'receiver_rejected' END,
          'receiver', p_receiver_id, p_reason);
  RETURN 'ok';
END $$;

-- 3. Clear a flagged receiver after admin review ------------------------------
-- Adds an 'admin_clear' event (history is kept) so apply_timeout_strikes()
-- counts strikes only from this point on, and lifts the flag.
CREATE OR REPLACE FUNCTION public.clear_receiver_flag(
  p_receiver_id uuid, p_admin_id uuid, p_reason text
) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_flagged boolean;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM public.user_profiles
                  WHERE id = p_admin_id AND role = 'admin') THEN
    RETURN 'not_admin';
  END IF;
  IF p_reason IS NULL OR btrim(p_reason) = '' THEN RETURN 'reason_required'; END IF;

  SELECT is_flagged INTO v_flagged FROM public.user_profiles
   WHERE id = p_receiver_id AND role = 'receiver' FOR UPDATE;
  IF NOT FOUND THEN RETURN 'not_receiver'; END IF;
  IF NOT v_flagged THEN RETURN 'not_flagged'; END IF;

  INSERT INTO public.receiver_strike_events
         (receiver_id, claim_id, event_type, reason, actor_id)
  VALUES (p_receiver_id, NULL, 'admin_clear', p_reason, p_admin_id);
  UPDATE public.user_profiles SET is_flagged = FALSE WHERE id = p_receiver_id;

  INSERT INTO public.admin_audit_log (actor_id, action, target_type, target_id, reason)
  VALUES (p_admin_id, 'flag_cleared', 'receiver', p_receiver_id, p_reason);
  RETURN 'ok';
END $$;

-- 4. Replace resolve_handshake_review with an audited version -----------------
DROP FUNCTION IF EXISTS public.resolve_handshake_review(uuid, uuid);

CREATE OR REPLACE FUNCTION public.resolve_handshake_review(
  p_claim_id uuid, p_admin_id uuid, p_note text
) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_done integer;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM public.user_profiles
                  WHERE id = p_admin_id AND role = 'admin') THEN
    RETURN 'not_admin';
  END IF;
  IF p_note IS NULL OR btrim(p_note) = '' THEN RETURN 'reason_required'; END IF;

  UPDATE public.claims
     SET handshake_review_resolved_at = now(),
         handshake_review_resolved_by = p_admin_id
   WHERE id = p_claim_id
     AND handshake_review_required
     AND handshake_review_resolved_at IS NULL;
  GET DIAGNOSTICS v_done = ROW_COUNT;
  IF v_done <> 1 THEN RETURN 'not_found'; END IF;

  INSERT INTO public.admin_audit_log (actor_id, action, target_type, target_id, reason)
  VALUES (p_admin_id, 'handshake_review_resolved', 'claim', p_claim_id, p_note);
  RETURN 'ok';
END $$;

-- 5. Grants: service role only ---------------------------------------------------
REVOKE ALL ON FUNCTION public.decide_receiver_application(uuid, uuid, text, text)
  FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.clear_receiver_flag(uuid, uuid, text)
  FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.resolve_handshake_review(uuid, uuid, text)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.decide_receiver_application(uuid, uuid, text, text) TO service_role;
GRANT EXECUTE ON FUNCTION public.clear_receiver_flag(uuid, uuid, text) TO service_role;
GRANT EXECUTE ON FUNCTION public.resolve_handshake_review(uuid, uuid, text) TO service_role;

COMMIT;

-- ROLLBACK (manual): drop the three functions and admin_audit_log.
