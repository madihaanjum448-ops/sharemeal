from datetime import datetime, timezone
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator


class FoodListingCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=120)
    description: Optional[str] = None
    food_category: Literal["human", "animal"]
    quantity: str = Field(..., min_length=1, max_length=100)
    servings: Optional[int] = Field(default=None, gt=0)
    pickup_address: str = Field(..., min_length=5)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    safe_until: datetime

    @field_validator("safe_until")
    @classmethod
    def validate_safe_until(cls, value):
        if value.tzinfo is None:
            raise ValueError("safe_until must include a timezone")
        if value <= datetime.now(timezone.utc):
            raise ValueError("safe_until must be in the future")
        return value


class FoodListingPublic(BaseModel):
    id: str
    title: str
    description: Optional[str]
    food_category: str
    quantity: str
    servings: Optional[int]
    safe_until: datetime
    status: str
    created_at: datetime
    