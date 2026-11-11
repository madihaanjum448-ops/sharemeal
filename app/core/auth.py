
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.auth_client import auth_supabase
from app.core.supabase_client import get_supabase

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials

    try:
        # Validate the user's access token using the Auth client.
        response = auth_supabase.auth.get_user(token)
        user = response.user

        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired authentication token",
            )

        # Use the backend client for the protected profile lookup.
        client = get_supabase()

        profile_response = (
            client.table("user_profiles")
            .select("id, role, is_verified")
            .eq("id", user.id)
            .single()
            .execute()
        )

        profile = profile_response.data

        if not profile:
            raise HTTPException(
                status_code=403,
                detail="User profile not found",
            )

        return {
            "id": user.id,
            "role": profile["role"],
            "is_verified": profile["is_verified"],
        }

    except HTTPException:
        raise

    except Exception as error:
        print("AUTHENTICATION DEBUG:", repr(error))
        raise HTTPException(
            status_code=401,
            detail="Authentication failed",
        )


def get_current_donor(user=Depends(get_current_user)):
    if user["role"] != "donor":
        raise HTTPException(
            status_code=403,
            detail="Only donors can create food listings",
        )

    return user
