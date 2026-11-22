from app.matching.candidates import (
    INVALID_COORDINATES, MISSING_COORDINATES, NOT_APPROVED, NOT_RECEIVER, OK,
    OUT_OF_RANGE, build_candidates, check_location_authorization,
    validate_location,
)
from app.matching.matching import match_receivers

LISTING = {"latitude": 12.9716, "longitude": 77.5946, "food_category": "human"}


def profile(pid, **overrides):
    base = {
        "id": pid, "role": "receiver", "approval_status": "approved",
        "is_verified": True, "is_flagged": False, "accepts_food_category": "human",
    }
    base.update(overrides)
    return base


def loc(pid, lat, lng):
    return {"receiver_id": pid, "latitude": lat, "longitude": lng}


# ---- coordinate validation -------------------------------------------------
def test_valid_coordinates_are_rounded_to_six_decimals():
    clean, status = validate_location(12.97159876, 77.59456789)
    assert status == OK
    assert clean == {"latitude": 12.971599, "longitude": 77.594568}


def test_integers_and_boundary_values_are_accepted():
    assert validate_location(90, 180)[1] == OK
    assert validate_location(-90, -180)[1] == OK
    assert validate_location(0, 0)[1] == OK


def test_out_of_range_rejected():
    assert validate_location(90.0001, 10)[1] == OUT_OF_RANGE
    assert validate_location(10, 180.5)[1] == OUT_OF_RANGE
    assert validate_location(-91, 0)[1] == OUT_OF_RANGE


def test_both_coordinates_are_required():
    assert validate_location(None, 77.5)[1] == MISSING_COORDINATES
    assert validate_location(12.9, None)[1] == MISSING_COORDINATES
    assert validate_location(None, None)[1] == MISSING_COORDINATES


def test_non_numbers_rejected():
    assert validate_location("12.9", "77.5")[1] == INVALID_COORDINATES
    assert validate_location(True, 77.5)[1] == INVALID_COORDINATES
    assert validate_location([1], 77.5)[1] == INVALID_COORDINATES


def test_nan_and_infinity_rejected():
    assert validate_location(float("nan"), 77.5)[1] == INVALID_COORDINATES
    assert validate_location(12.9, float("inf"))[1] == INVALID_COORDINATES


# ---- authorization ----------------------------------------------------------
def test_approved_verified_receiver_may_save_location():
    assert check_location_authorization(profile("r1")) == OK


def test_pending_or_unverified_receiver_may_not():
    assert check_location_authorization(profile("r1", approval_status="pending")) == NOT_APPROVED
    assert check_location_authorization(profile("r1", is_verified=False)) == NOT_APPROVED
    assert check_location_authorization(profile("r1", approval_status="rejected")) == NOT_APPROVED


def test_donor_admin_or_unknown_user_may_not():
    assert check_location_authorization(profile("d1", role="donor")) == NOT_RECEIVER
    assert check_location_authorization(profile("a1", role="admin")) == NOT_RECEIVER
    assert check_location_authorization(None) == NOT_RECEIVER


# ---- building matching candidates ------------------------------------------------
def test_candidate_gets_coordinates_from_location_row():
    result = build_candidates([profile("r1")], [loc("r1", 12.98, 77.59)])
    assert result[0]["latitude"] == 12.98 and result[0]["longitude"] == 77.59


def test_receiver_without_location_is_excluded():
    result = build_candidates([profile("r1"), profile("r2")], [loc("r2", 12.98, 77.59)])
    assert [c["id"] for c in result] == ["r2"]


def test_invalid_stored_location_is_excluded():
    rows = [loc("r1", 200, 77.59), loc("r2", None, 77.59), loc("r3", "abc", 77.59)]
    profiles = [profile("r1"), profile("r2"), profile("r3")]
    assert build_candidates(profiles, rows) == []


def test_non_receivers_are_excluded():
    result = build_candidates([profile("d1", role="donor")], [loc("d1", 12.98, 77.59)])
    assert result == []


def test_numeric_strings_from_the_database_are_accepted():
    result = build_candidates([profile("r1")], [loc("r1", "12.980000", "77.590000")])
    assert result[0]["latitude"] == 12.98


def test_embedded_location_shapes_are_supported():
    as_object = dict(profile("r1"), receiver_locations={"latitude": 12.98, "longitude": 77.59})
    as_list = dict(profile("r2"), receiver_locations=[{"latitude": 12.99, "longitude": 77.59}])
    result = build_candidates([as_object, as_list])
    assert [c["id"] for c in result] == ["r1", "r2"]
    assert all("receiver_locations" not in c for c in result)


def test_inputs_are_not_modified():
    p = profile("r1")
    rows = [loc("r1", 12.98, 77.59)]
    build_candidates([p], rows)
    assert "latitude" not in p and rows == [loc("r1", 12.98, 77.59)]


# ---- matching eligibility with locations ------------------------------------------
def test_receiver_without_location_is_never_matched():
    candidates = build_candidates([profile("r1")], [])
    assert match_receivers(LISTING, candidates, 10) == []


def test_matching_still_applies_approval_flag_and_category_rules():
    profiles = [
        profile("ok"),
        profile("pending", approval_status="pending"),
        profile("flagged", is_flagged=True),
        profile("animal", accepts_food_category="animal"),
        profile("unverified", is_verified=False),
    ]
    rows = [loc(p["id"], 12.98, 77.59) for p in profiles]
    matched = match_receivers(LISTING, build_candidates(profiles, rows), 0)
    assert [r["id"] for r in matched] == ["ok"]


def test_matching_uses_the_location_distance():
    profiles = [profile("near"), profile("far")]
    rows = [loc("near", 12.98, 77.59), loc("far", 13.40, 77.59)]   # far is ~47 km away
    candidates = build_candidates(profiles, rows)
    assert [r["id"] for r in match_receivers(LISTING, candidates, 0)] == ["near"]
    assert [r["id"] for r in match_receivers(LISTING, candidates, 10)] == ["near", "far"]
