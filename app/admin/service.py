"""Receiver approval logic (Member 2). Pure functions, no database.

Approval sets BOTH approval_status and is_verified so the two fields can
never disagree. Every decision returns an audit record (actor + timestamp).
"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

APPROVE = "approve"
REJECT = "reject"

OK = "ok"
NOT_ADMIN = "not_admin"
NOT_RECEIVER = "not_receiver"
ALREADY_DECIDED = "already_decided"
INVALID_DECISION = "invalid_decision"
REASON_REQUIRED = "reason_required"
CATEGORY_REQUIRED = "category_required"

# Only these fields are shown in the pending list (no phone, no address).
SUMMARY_FIELDS = (
    "id", "full_name", "organization_name", "registration_photo",
    "accepts_food_category", "created_at",
)


def _is_pending(profile: Dict[str, Any]) -> bool:
    return profile.get("role") == "receiver" and profile.get("approval_status") in (
        None, "pending",
    )


def pending_applications(profiles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Pending receivers, oldest first, with a limited set of fields."""
    pending = [p for p in profiles if _is_pending(p)]
    pending.sort(key=lambda p: str(p.get("created_at") or ""))
    return [{key: p.get(key) for key in SUMMARY_FIELDS} for p in pending]


def decide_receiver(
    profile: Dict[str, Any],
    decision: str,
    admin: Dict[str, Any],
    now: datetime,
    reason: Optional[str] = None,
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]], str]:
    """Return (profile, audit_record, result). Inputs are never modified.

    On any failure the original profile is returned with no audit record.
    """
    if admin.get("role") != "admin":
        return profile, None, NOT_ADMIN
    if profile.get("role") != "receiver":
        return profile, None, NOT_RECEIVER
    if decision not in (APPROVE, REJECT):
        return profile, None, INVALID_DECISION
    if not _is_pending(profile):
        return profile, None, ALREADY_DECIDED
    if decision == REJECT and not (reason and reason.strip()):
        return profile, None, REASON_REQUIRED
    if decision == APPROVE and not profile.get("accepts_food_category"):
        return profile, None, CATEGORY_REQUIRED

    approved = decision == APPROVE
    updated = dict(profile)
    updated["approval_status"] = "approved" if approved else "rejected"
    updated["is_verified"] = approved
    audit = {
        "receiver_id": profile.get("id"),
        "decision": decision,
        "actor_id": admin.get("id"),
        "reason": reason,
        "decided_at": now,
    }
    return updated, audit, OK
