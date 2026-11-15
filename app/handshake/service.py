"""Pickup handshake logic (Member 2). Pure functions, no database.

Only a keyed hash of the code is stored, never the code itself.
MAX_ATTEMPTS and the code lifetime are placeholders pending team sign-off.
"""
import hashlib
import hmac
import secrets
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Optional, Tuple

MAX_ATTEMPTS = 5

OK = "ok"
WRONG = "wrong_code"
LOCKED = "locked"
EXPIRED = "expired"
ALREADY_USED = "already_used"


@dataclass(frozen=True)
class Handshake:
    claim_id: str
    code_hash: str
    expires_at: datetime
    attempts: int = 0
    verified_at: Optional[datetime] = None


def generate_code() -> str:
    return "%04d" % secrets.randbelow(10000)


def hash_code(code: str, claim_id: str, secret: str) -> str:
    message = ("%s:%s" % (claim_id, code)).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def start_handshake(
    claim_id: str, secret: str, expires_at: datetime, code: Optional[str] = None
) -> Tuple[Handshake, str]:
    """Return (record to store, plain code to show the donor once)."""
    code = code or derive_code(claim_id, secret)
    record = Handshake(claim_id, hash_code(code, claim_id, secret), expires_at)
    return record, code


def verify_handshake(
    handshake: Handshake, submitted: str, secret: str, now: datetime
) -> Tuple[Handshake, str]:
    """Return (updated record, result). Never modifies the input record."""
    if handshake.verified_at is not None:
        return handshake, ALREADY_USED
    if now >= handshake.expires_at:
        return handshake, EXPIRED
    if handshake.attempts >= MAX_ATTEMPTS:
        return handshake, LOCKED
    candidate = hash_code(str(submitted), handshake.claim_id, secret)
    if hmac.compare_digest(candidate, handshake.code_hash):
        return replace(handshake, verified_at=now), OK
    return replace(handshake, attempts=handshake.attempts + 1), WRONG


def derive_code(claim_id: str, secret: str) -> str:
    """Recompute a claim's 4-digit code from the server secret.

    Lets the backend show the code again to the authorised donor without
    storing it. Needs HANDSHAKE_SECRET kept private, same as the hash.
    """
    message = ("code:%s" % claim_id).encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()
    return "%04d" % (int.from_bytes(digest[:4], "big") % 10000)
