
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class SendOTPRequest(BaseModel):
    email: EmailStr


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    token: str = Field(..., pattern=r"^\d{8}$")
    full_name: str = Field(..., min_length=2, max_length=100)
    role: Literal["donor", "receiver"]
    organization_name: Optional[str] = None
