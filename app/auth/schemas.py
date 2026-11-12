
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class SendOTPRequest(BaseModel):
    email: EmailStr


class VerifyOTPRequest(BaseModel):
    email: EmailStr

    token: str = Field(
        ...,
        min_length=6,
        max_length=8,
        pattern=r"^\d{6,8}$",
        description="Supabase email OTP containing 6 to 8 digits",
    )

    full_name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    role: Optional[Literal["donor", "receiver"]] = None

    organization_name: Optional[str] = Field(
        default=None,
        max_length=160,
    )
