from datetime import datetime, timedelta, timezone
import pytest
from app.listings.schemas import FoodListingCreate


def test_safe_until_future_validation():
    valid_time = datetime.now(timezone.utc) + timedelta(hours=2)
    payload = {
        "title": "Surplus Rice",
        "food_category": "human",
        "quantity": "10 kg",
        "pickup_address": "123 Main Street, Bangalore",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "safe_until": valid_time,
    }
    model = FoodListingCreate(**payload)
    assert model.safe_until == valid_time


def test_safe_until_past_rejection():
    past_time = datetime.now(timezone.utc) - timedelta(hours=1)
    payload = {
        "title": "Surplus Rice",
        "food_category": "human",
        "quantity": "10 kg",
        "pickup_address": "123 Main Street, Bangalore",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "safe_until": past_time,
    }
    with pytest.raises(ValueError, match="strictly in the future"):
        FoodListingCreate(**payload)


def test_safe_until_naive_datetime_rejection():
    naive_time = datetime.now() + timedelta(hours=2)
    payload = {
        "title": "Surplus Rice",
        "food_category": "human",
        "quantity": "10 kg",
        "pickup_address": "123 Main Street, Bangalore",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "safe_until": naive_time,
    }
    with pytest.raises(ValueError, match="include UTC timezone offset"):
        FoodListingCreate(**payload)