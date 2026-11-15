from datetime import datetime, timezone

from app.admin.service import (
    ALREADY_DECIDED, APPROVE, INVALID_DECISION, NOT_ADMIN, NOT_RECEIVER, OK,
    REASON_REQUIRED, REJECT, SUMMARY_FIELDS, decide_receiver,
    pending_applications,
)

NOW = datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)
ADMIN = {"id": "admin-1", "role": "admin"}


def profile(pid, role="receiver", status="pending", created="2026-11-10"):
    return {
        "id": pid, "role": role, "approval_status": status,
        "is_verified": False, "full_name": "Name " + pid,
        "organization_name": "Org " + pid, "phone": "9990001111",
        "registration_photo": "photos/" + pid + ".jpg", "created_at": created,
        "accepts_food_category": "both",
    }


def test_pending_list_only_pending_receivers():
    profiles = [
        profile("a"), profile("b", status="approved"),
        profile("c", status="rejected"), profile("d", role="donor"),
    ]
    assert [p["id"] for p in pending_applications(profiles)] == ["a"]


def test_pending_list_treats_missing_status_as_pending():
    p = profile("a")
    p["approval_status"] = None
    assert [x["id"] for x in pending_applications([p])] == ["a"]


def test_pending_list_oldest_first():
    profiles = [profile("new", created="2026-11-14"), profile("old", created="2026-11-01")]
    assert [p["id"] for p in pending_applications(profiles)] == ["old", "new"]


def test_pending_list_hides_private_fields():
    summary = pending_applications([profile("a")])[0]
    assert set(summary.keys()) == set(SUMMARY_FIELDS)
    assert "phone" not in summary


def test_approve_sets_status_and_verified():
    updated, audit, result = decide_receiver(profile("a"), APPROVE, ADMIN, NOW)
    assert result == OK
    assert updated["approval_status"] == "approved" and updated["is_verified"] is True


def test_reject_requires_reason():
    original = profile("a")
    updated, audit, result = decide_receiver(original, REJECT, ADMIN, NOW)
    assert result == REASON_REQUIRED and audit is None and updated == original


def test_reject_with_reason():
    updated, audit, result = decide_receiver(
        profile("a"), REJECT, ADMIN, NOW, reason="documents unclear")
    assert result == OK
    assert updated["approval_status"] == "rejected" and updated["is_verified"] is False


def test_non_admin_cannot_decide():
    donor = {"id": "u1", "role": "donor"}
    _, audit, result = decide_receiver(profile("a"), APPROVE, donor, NOW)
    assert result == NOT_ADMIN and audit is None


def test_cannot_decide_on_non_receiver():
    _, _, result = decide_receiver(profile("d", role="donor"), APPROVE, ADMIN, NOW)
    assert result == NOT_RECEIVER


def test_already_decided_is_rejected():
    _, _, result = decide_receiver(profile("a", status="approved"), REJECT, ADMIN, NOW, reason="x")
    assert result == ALREADY_DECIDED


def test_invalid_decision_rejected():
    _, _, result = decide_receiver(profile("a"), "maybe", ADMIN, NOW)
    assert result == INVALID_DECISION


def test_audit_record_has_actor_and_timestamp():
    _, audit, _ = decide_receiver(profile("a"), APPROVE, ADMIN, NOW)
    assert audit["actor_id"] == "admin-1"
    assert audit["decided_at"] == NOW
    assert audit["receiver_id"] == "a" and audit["decision"] == APPROVE


def test_input_profile_not_modified():
    original = profile("a")
    snapshot = dict(original)
    decide_receiver(original, APPROVE, ADMIN, NOW)
    assert original == snapshot


def test_approve_requires_food_category():
    from app.admin.service import CATEGORY_REQUIRED
    p = profile("a")
    p["accepts_food_category"] = None
    updated, audit, result = decide_receiver(p, APPROVE, ADMIN, NOW)
    assert result == CATEGORY_REQUIRED and audit is None and updated == p


def test_reject_does_not_need_food_category():
    p = profile("a")
    p["accepts_food_category"] = None
    _, _, result = decide_receiver(p, REJECT, ADMIN, NOW, reason="documents unclear")
    assert result == OK


def test_pending_list_shows_chosen_category():
    summary = pending_applications([profile("a")])[0]
    assert summary["accepts_food_category"] == "both"
