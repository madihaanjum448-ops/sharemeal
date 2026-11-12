
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import get_current_admin
from app.core.supabase_client import get_supabase


router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/receivers/pending")
def get_pending_receivers(
    _admin=Depends(get_current_admin),
):
    """List receiver accounts awaiting administrator approval."""
    try:
        response = (
            get_supabase()
            .table("user_profiles")
            .select(
                "id, full_name, phone, organization_name, "
                "approval_status, is_verified, created_at"
            )
            .eq("role", "receiver")
            .eq("approval_status", "pending")
            .order("created_at", desc=False)
            .execute()
        )

        receivers = response.data or []

        return {
            "count": len(receivers),
            "receivers": receivers,
        }

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not retrieve pending receiver applications",
        )


@router.get("/receivers/{receiver_id}")
def get_receiver_details(
    receiver_id: UUID,
    _admin=Depends(get_current_admin),
):
    """View a receiver application."""
    try:
        response = (
            get_supabase()
            .table("user_profiles")
            .select(
                "id, full_name, phone, role, organization_name, "
                "approval_status, is_verified, created_at"
            )
            .eq("id", str(receiver_id))
            .eq("role", "receiver")
            .limit(1)
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Receiver application not found",
            )

        return {"receiver": response.data[0]}

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not retrieve receiver application",
        )


@router.patch("/receivers/{receiver_id}/approve")
def approve_receiver(
    receiver_id: UUID,
    _admin=Depends(get_current_admin),
):
    """Approve a pending receiver account."""
    try:
        client = get_supabase()

        updated = (
            client.table("user_profiles")
            .update({
                "approval_status": "approved",
                "is_verified": True,
            })
            .eq("id", str(receiver_id))
            .eq("role", "receiver")
            .eq("approval_status", "pending")
            .select(
                "id, full_name, role, organization_name, "
                "approval_status, is_verified, created_at"
            )
            .execute()
        )

        if not updated.data:
            existing = (
                client.table("user_profiles")
                .select("id")
                .eq("id", str(receiver_id))
                .eq("role", "receiver")
                .eq("approval_status", "pending")
                .limit(1)
                .execute()
            )

            if not existing.data:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Receiver application not found, or it is no longer pending",
                )

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Application status changed. Refresh and try again.",
            )

        return {
            "message": "Receiver approved successfully",
            "receiver": updated.data[0],
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not approve receiver application",
        )


@router.patch("/receivers/{receiver_id}/reject")
def reject_receiver(
    receiver_id: UUID,
    _admin=Depends(get_current_admin),
):
    """Reject a pending receiver account."""
    try:
        client = get_supabase()

        updated = (
            client.table("user_profiles")
            .update({
                "approval_status": "rejected",
                "is_verified": False,
            })
            .eq("id", str(receiver_id))
            .eq("role", "receiver")
            .eq("approval_status", "pending")
            .select(
                "id, full_name, role, organization_name, "
                "approval_status, is_verified, created_at"
            )
            .execute()
        )

        if not updated.data:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Receiver application not found, or it is no longer pending",
            )

        return {
            "message": "Receiver rejected successfully",
            "receiver": updated.data[0],
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not reject receiver application",
        )
