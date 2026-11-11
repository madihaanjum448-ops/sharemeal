
from fastapi import APIRouter, HTTPException

from app.auth.schemas import SendOTPRequest, VerifyOTPRequest
from app.core.auth_client import auth_supabase
from app.core.supabase_client import get_supabase

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/send-otp")
def send_otp(request: SendOTPRequest):
    email = request.email.strip().lower()

    try:
        response = auth_supabase.auth.sign_in_with_otp({
            "email": email,
            "options": {
                "should_create_user": True,
            },
        })

        print("OTP request response:", response)

        return {
            "message": "Verification code sent. Please check your email."
        }

    except Exception as error:
        print("SUPABASE OTP ERROR:", repr(error))

        raise HTTPException(
            status_code=400,
            detail="Could not send OTP. Check the server terminal.",
        )


@router.post("/verify-otp")
def verify_otp(request: VerifyOTPRequest):
    email = request.email.strip().lower()

    try:
        verification = auth_supabase.auth.verify_otp({
            "email": email,
            "token": request.token,
            "type": "email",
        })

        user = verification.user
        session = verification.session

        if not user or not session:
            raise HTTPException(
                status_code=401,
                detail="OTP verification failed.",
            )

        client = get_supabase()

        existing = (
            client.table("user_profiles")
            .select("id, full_name, role, organization_name, is_verified")
            .eq("id", user.id)
            .limit(1)
            .execute()
        )

        if existing.data:
            profile = existing.data[0]

        else:
            profile_data = {
                "id": user.id,
                "full_name": request.full_name.strip(),
                "role": request.role,
                "organization_name": (
                    request.organization_name.strip()
                    if request.organization_name
                    else None
                ),
            }

            created = (
                client.table("user_profiles")
                .insert(profile_data)
                .execute()
            )

            if not created.data:
                raise HTTPException(
                    status_code=500,
                    detail="Account verified, but profile creation failed.",
                )

            profile = created.data[0]

        return {
            "message": "Email verified and login successful.",
            "user": {
                "id": user.id,
                "email": user.email,
            },
            "profile": profile,
            "session": {
                "access_token": session.access_token,
                "refresh_token": session.refresh_token,
                "token_type": session.token_type,
                "expires_in": session.expires_in,
            },
        }

    except HTTPException:
        raise

    except Exception as error:
        print("SUPABASE VERIFY OTP ERROR:", repr(error))

        raise HTTPException(
            status_code=400,
            detail="OTP verification or account setup failed. Check the server terminal.",
        )
