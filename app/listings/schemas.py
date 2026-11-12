from datetime import datetime, timezone
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class FoodListingCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=120)
    description: Optional[str] = None
    food_category: Literal["human", "animal"]
    quantity: str = Field(..., min_length=1, max_length=100)
    servings: Optional[int] = Field(default=None, gt=0)
    pickup_address: str = Field(..., min_length=5)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    safe_until: datetime

    @field_validator("safe_until")
    @classmethod
    def validate_safe_until(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("safe_until timestamp must include UTC timezone offset")
        
        now = datetime.now(timezone.utc)
        if value <= now:
            raise ValueError("safe_until timestamp must be strictly in the future")
        return value


class FoodListingPublicResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    food_category: str
    quantity: str
    servings: Optional[int] = None
    safe_until: datetime
    status: str
    created_at: datetime


class FoodListingDetailResponse(FoodListingPublicResponse):
    pickup_address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class FoodListingUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=120)
    description: Optional[str] = None
    food_category: Optional[Literal["human", "animal"]] = None
    quantity: Optional[str] = Field(default=None, min_length=1, max_length=100)
    servings: Optional[int] = Field(default=None, gt=0)
    pickup_address: Optional[str] = Field(default=None, min_length=5)
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    safe_until: Optional[datetime] = None

    @field_validator(
        "title",
        "food_category",
        "quantity",
        "pickup_address",
        "latitude",
        "longitude",
        "safe_until",
        mode="before",
    )
    @classmethod
    def reject_null_required_fields(cls, value):
        if value is None:
            raise ValueError("This field cannot be null")
        return value

    @field_validator("safe_until")
    @classmethod
    def validate_optional_safe_until(cls, value):
        if value is not None:
            if value.tzinfo is None:
                raise ValueError(
                    "safe_until timestamp must include timezone information"
                )
            if value <= datetime.now(timezone.utc):
                raise ValueError(
                    "safe_until timestamp must be strictly in the future"
                )
        return value

    @model_validator(mode="after")
    def validate_coordinates_together(self):
        latitude_provided = "latitude" in self.model_fields_set
        longitude_provided = "longitude" in self.model_fields_set

        if latitude_provided != longitude_provided:
            raise ValueError(
                "Latitude and longitude must be updated together"
            )

        return self
