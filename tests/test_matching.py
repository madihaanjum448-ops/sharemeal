from app.matching.matching import match_receivers

LISTING = {"latitude": 12.9716, "longitude": 77.5946, "food_category": "human"}


def make(rid, offset_deg, **overrides):
    """Receiver roughly offset_deg * 111 km north of the listing."""
    base = {
        "id": rid,
        "latitude": 12.9716 + offset_deg,
        "longitude": 77.5946,
        "approval_status": "approved",
        "is_verified": True,
        "is_flagged": False,
        "accepts_food_category": "human",
    }
    base.update(overrides)
    return base


def ids(result):
    return [r["id"] for r in result]


def test_unapproved_receiver_excluded():
    r = make("a", 0.01, approval_status="pending")
    assert match_receivers(LISTING, [r], 0) == []


def test_unverified_receiver_excluded():
    r = make("a", 0.01, is_verified=False)
    assert match_receivers(LISTING, [r], 0) == []


def test_flagged_receiver_excluded():
    r = make("a", 0.01, is_flagged=True)
    assert match_receivers(LISTING, [r], 0) == []


def test_category_mismatch_excluded_and_both_accepted():
    animal_only = make("animal", 0.01, accepts_food_category="animal")
    both = make("both", 0.02, accepts_food_category="both")
    assert ids(match_receivers(LISTING, [animal_only, both], 0)) == ["both"]


def test_minute_zero_returns_nearest_five_within_3km():
    near = [make("r%d" % i, 0.002 * i) for i in range(1, 8)]  # 7 within ~1.6 km
    far = make("far", 0.05)  # ~5.5 km
    result = match_receivers(LISTING, near + [far], 0)
    assert ids(result) == ["r1", "r2", "r3", "r4", "r5"]


def test_minute_five_widens_to_8km():
    mid = make("mid", 0.05)    # ~5.5 km
    far = make("far", 0.10)    # ~11 km
    assert ids(match_receivers(LISTING, [mid, far], 4)) == []
    assert ids(match_receivers(LISTING, [mid, far], 5)) == ["mid"]


def test_minute_ten_returns_all_compatible():
    mid = make("mid", 0.05)
    far = make("far", 0.10)
    assert ids(match_receivers(LISTING, [far, mid], 10)) == ["mid", "far"]


def test_results_sorted_nearest_first():
    a = make("a", 0.02)
    b = make("b", 0.01)
    c = make("c", 0.015)
    assert ids(match_receivers(LISTING, [a, b, c], 0)) == ["b", "c", "a"]


def test_empty_receiver_list():
    assert match_receivers(LISTING, [], 0) == []


def test_inputs_are_not_modified():
    r = make("a", 0.01)
    snapshot = dict(r)
    match_receivers(LISTING, [r], 0)
    assert r == snapshot


def test_malformed_coordinates_skipped():
    bad = make("bad", 0.01)
    del bad["latitude"]
    good = make("good", 0.02)
    assert ids(match_receivers(LISTING, [bad, good], 0)) == ["good"]
