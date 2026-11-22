from pathlib import Path

import app.receivers.routes as routes
from app.matching.fetch import fetch_matching_candidates
from app.matching.matching import match_receivers
from app.receivers.service import LocationError, read_location, save_location
from fastapi import HTTPException, Response


# ---- a tiny in-memory stand-in for the Supabase client ------------------------
class FakeResult:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, client, name):
        self.client, self.name = client, name
        self.filters, self.limit_n, self.upsert_args = [], None, None

    def select(self, columns="*"):
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def limit(self, n):
        self.limit_n = n
        return self

    def upsert(self, row, on_conflict=None):
        self.upsert_args = (dict(row), on_conflict)
        return self

    def execute(self):
        if self.client.fail:
            raise RuntimeError("database down, secret=XYZ")
        rows = self.client.tables.setdefault(self.name, [])
        if self.upsert_args:
            row, key = self.upsert_args
            for i, existing in enumerate(rows):
                if existing.get(key) == row.get(key):
                    rows[i] = row
                    break
            else:
                rows.append(row)
            return FakeResult([row])
        found = [dict(r) for r in rows if all(r.get(c) == v for c, v in self.filters)]
        if self.limit_n is not None:
            found = found[: self.limit_n]
        return FakeResult(found)


class FakeClient:
    def __init__(self, fail=False):
        self.tables, self.fail = {}, fail

    def table(self, name):
        return FakeQuery(self, name)


def receiver(uid="r1", **overrides):
    base = {"id": uid, "role": "receiver", "is_verified": True, "approval_status": "approved"}
    base.update(overrides)
    return base


def rows(client):
    return client.tables.get("receiver_locations", [])


def error_of(fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except LocationError as exc:
        return exc.status_code, exc.detail
    return None


# ---- saving a location ----------------------------------------------------------
def test_save_creates_a_row_for_the_logged_in_user():
    client = FakeClient()
    result = save_location(client, receiver("r1"), {"latitude": 12.97, "longitude": 77.59})
    assert rows(client)[0]["receiver_id"] == "r1"
    assert result["latitude"] == 12.97 and result["longitude"] == 77.59
    assert result["updated_at"].endswith("Z")


def test_second_save_updates_the_same_row():
    client = FakeClient()
    save_location(client, receiver("r1"), {"latitude": 12.97, "longitude": 77.59})
    save_location(client, receiver("r1"), {"latitude": 13.01, "longitude": 77.60})
    assert len(rows(client)) == 1
    assert rows(client)[0]["latitude"] == 13.01


def test_receiver_id_in_the_body_is_ignored():
    client = FakeClient()
    body = {"latitude": 12.97, "longitude": 77.59, "receiver_id": "someone-else"}
    save_location(client, receiver("r1"), body)
    assert [r["receiver_id"] for r in rows(client)] == ["r1"]


def test_coordinates_are_rounded_to_six_decimals():
    client = FakeClient()
    result = save_location(client, receiver(), {"latitude": 12.97159876, "longitude": 77.59456789})
    assert result["latitude"] == 12.971599 and rows(client)[0]["longitude"] == 77.594568


def test_bad_coordinates_are_rejected_and_nothing_is_written():
    client = FakeClient()
    cases = [
        ({"latitude": 12.9}, "missing_coordinates"),
        ({"longitude": 77.5}, "missing_coordinates"),
        ({"latitude": "12.9", "longitude": "77.5"}, "invalid_coordinates"),
        ({"latitude": 91, "longitude": 77.5}, "out_of_range"),
        ({"latitude": 12.9, "longitude": 181}, "out_of_range"),
        ("not an object", "invalid_coordinates"),
    ]
    for body, code in cases:
        assert error_of(save_location, client, receiver(), body) == (422, code)
    assert rows(client) == []


def test_donor_and_pending_receiver_are_refused():
    client = FakeClient()
    body = {"latitude": 12.9, "longitude": 77.5}
    assert error_of(save_location, client, receiver(role="donor"), body) == (403, "not_receiver")
    assert error_of(save_location, client, receiver(approval_status="pending"), body) == (403, "not_approved")
    assert error_of(save_location, client, receiver(is_verified=False), body) == (403, "not_approved")
    assert rows(client) == []


def test_database_failure_gives_503_without_leaking_details():
    client = FakeClient(fail=True)
    status, detail = error_of(save_location, client, receiver(), {"latitude": 12.9, "longitude": 77.5})
    assert status == 503 and detail == "location_service_unavailable"
    assert "XYZ" not in detail


# ---- reading a location -----------------------------------------------------------
def test_read_before_saving_gives_404():
    assert error_of(read_location, FakeClient(), receiver()) == (404, "location_not_set")


def test_read_returns_only_the_owners_location():
    client = FakeClient()
    save_location(client, receiver("r1"), {"latitude": 12.97, "longitude": 77.59})
    save_location(client, receiver("r2"), {"latitude": 13.50, "longitude": 77.10})
    mine = read_location(client, receiver("r1"))
    assert mine["latitude"] == 12.97 and mine["longitude"] == 77.59


def test_read_response_has_only_the_expected_keys():
    client = FakeClient()
    save_location(client, receiver("r1"), {"latitude": 12.97, "longitude": 77.59})
    assert set(read_location(client, receiver("r1")).keys()) == {"latitude", "longitude", "updated_at"}


def test_read_refuses_non_receivers():
    client = FakeClient()
    assert error_of(read_location, client, receiver(role="donor")) == (403, "not_receiver")
    assert error_of(read_location, client, receiver(approval_status="pending")) == (403, "not_approved")


def test_corrupt_stored_values_read_as_not_set():
    client = FakeClient()
    client.tables["receiver_locations"] = [{"receiver_id": "r1", "latitude": "abc", "longitude": 77.5}]
    assert error_of(read_location, client, receiver("r1")) == (404, "location_not_set")


# ---- candidates for matching ------------------------------------------------------------
def seed_candidates(client):
    profiles = [
        {"id": "ok", "role": "receiver", "approval_status": "approved", "is_verified": True,
         "is_flagged": False, "accepts_food_category": "human"},
        {"id": "no-location", "role": "receiver", "approval_status": "approved", "is_verified": True,
         "is_flagged": False, "accepts_food_category": "human"},
        {"id": "a-donor", "role": "donor"},
    ]
    client.tables["user_profiles"] = profiles
    client.tables["receiver_locations"] = [
        {"receiver_id": "ok", "latitude": 12.98, "longitude": 77.59},
        {"receiver_id": "a-donor", "latitude": 12.98, "longitude": 77.59},
    ]


def test_receivers_without_a_location_are_left_out():
    client = FakeClient()
    seed_candidates(client)
    assert [c["id"] for c in fetch_matching_candidates(client)] == ["ok"]


def test_fetched_candidates_work_with_match_receivers():
    client = FakeClient()
    seed_candidates(client)
    listing = {"latitude": 12.9716, "longitude": 77.5946, "food_category": "human"}
    matched = match_receivers(listing, fetch_matching_candidates(client), 0)
    assert [r["id"] for r in matched] == ["ok"]


# ---- privacy: only the location modules may touch receiver_locations ----------------------
def test_only_location_modules_touch_the_receiver_locations_table():
    app_dir = Path(__file__).resolve().parents[1] / "app"
    allowed = {
        "receivers/service.py",
        "matching/fetch.py",
        "matching/candidates.py",
    }
    users = set()
    for path in app_dir.rglob("*.py"):
        if "receiver_locations" in path.read_text(encoding="utf-8"):
            users.add(path.relative_to(app_dir).as_posix())
    assert users <= allowed, "unexpected modules use receiver_locations: %s" % sorted(users - allowed)


# ---- the route functions ----------------------------------------------------------------------
def test_put_route_saves_and_sets_no_store(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(routes, "get_supabase", lambda: client)
    response = Response()
    result = routes.put_my_location(
        response=response, payload={"latitude": 12.97, "longitude": 77.59}, user=receiver("r1"))
    assert result["latitude"] == 12.97
    assert response.headers.get("Cache-Control") == "no-store"
    assert rows(client)[0]["receiver_id"] == "r1"


def test_put_route_turns_errors_into_http_exceptions(monkeypatch):
    monkeypatch.setattr(routes, "get_supabase", lambda: FakeClient())
    try:
        routes.put_my_location(response=Response(), payload={"latitude": 95, "longitude": 10}, user=receiver())
    except HTTPException as exc:
        assert exc.status_code == 422 and exc.detail == "out_of_range"
    else:
        raise AssertionError("expected HTTPException")


def test_get_route_returns_404_until_a_location_is_saved(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(routes, "get_supabase", lambda: client)
    try:
        routes.get_my_location(response=Response(), user=receiver("r1"))
    except HTTPException as exc:
        assert exc.status_code == 404 and exc.detail == "location_not_set"
    else:
        raise AssertionError("expected HTTPException")
    save_location(client, receiver("r1"), {"latitude": 12.97, "longitude": 77.59})
    assert routes.get_my_location(response=Response(), user=receiver("r1"))["latitude"] == 12.97
