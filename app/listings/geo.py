from math import radians, sin, cos, asin, sqrt


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance using the Haversine formula."""
    values = (lat1, lon1, lat2, lon2)
    if not (-90 <= lat1 <= 90 and -90 <= lat2 <= 90 and -180 <= lon1 <= 180 and -180 <= lon2 <= 180):
        raise ValueError("Coordinates are outside valid latitude/longitude ranges")
    a1, o1, a2, o2 = map(radians, values)
    dlat, dlon = a2 - a1, o2 - o1
    a = sin(dlat / 2) ** 2 + cos(a1) * cos(a2) * sin(dlon / 2) ** 2
    return 6371.0088 * 2 * asin(sqrt(min(1.0, a)))
