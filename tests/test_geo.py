import pytest
from app.listings.geo import distance_km


def test_same_coordinate_distance_is_zero():
    assert distance_km(12.9716, 77.5946, 12.9716, 77.5946) == pytest.approx(0)


def test_known_bengaluru_distance_is_reasonable():
    distance = distance_km(12.9716, 77.5946, 12.9352, 77.6245)
    assert 4.0 < distance < 5.5


def test_invalid_coordinate_rejected():
    with pytest.raises(ValueError):
        distance_km(91, 0, 0, 0)
