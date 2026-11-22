from typing import Any, Dict

from fastapi import APIRouter, Body, Depends, HTTPException, Response

from app.core.auth import get_current_user
from app.core.supabase_client import get_supabase
from app.receivers.service import LocationError, read_location, save_location

router = APIRouter(prefix="/receivers", tags=["Receivers"])

NO_STORE = {"Cache-Control": "no-store"}


@router.put("/me/location")
def put_my_location(
    response: Response,
    payload: Dict[str, Any] = Body(...),
    user=Depends(get_current_user),
):
    """Create or update the logged-in receiver's location. The id comes from the token."""
    response.headers["Cache-Control"] = "no-store"
    try:
        return save_location(get_supabase(), user, payload)
    except LocationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail, headers=NO_STORE)


@router.get("/me/location")
def get_my_location(
    response: Response,
    user=Depends(get_current_user),
):
    """Return the logged-in receiver's own saved location."""
    response.headers["Cache-Control"] = "no-store"
    try:
        return read_location(get_supabase(), user)
    except LocationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail, headers=NO_STORE)
