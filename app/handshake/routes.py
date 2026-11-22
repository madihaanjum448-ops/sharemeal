from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Response

from app.core.auth import get_current_donor, get_current_verified_receiver
from app.core.supabase_client import get_supabase
from app.handshake.rpc import HandshakeError, confirm_pickup, donor_handshake_code

claims_router = APIRouter(prefix="/claims", tags=["Handshake"])
donor_router = APIRouter(prefix="/donor", tags=["Handshake"])

NO_STORE = {"Cache-Control": "no-store"}


@claims_router.post("/{claim_id}/confirm-pickup")
def confirm_pickup_route(
    claim_id: UUID,
    response: Response,
    payload: Dict[str, Any] = Body(...),
    user=Depends(get_current_verified_receiver),
):
    """The receiver types the code the donor gives them at pickup."""
    response.headers["Cache-Control"] = "no-store"
    try:
        return confirm_pickup(get_supabase(), str(claim_id), user, payload.get("code"))
    except HandshakeError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail, headers=NO_STORE)


@donor_router.get("/claims/{claim_id}/handshake-code")
def donor_handshake_code_route(
    claim_id: UUID,
    response: Response,
    user=Depends(get_current_donor),
):
    """The owning donor reads the pickup code while the claim is active."""
    response.headers["Cache-Control"] = "no-store"
    try:
        return donor_handshake_code(get_supabase(), str(claim_id), user)
    except HandshakeError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail, headers=NO_STORE)
