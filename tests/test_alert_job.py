from datetime import datetime, timedelta, timezone

from fastapi import Response

import app.alerts.routes as aroutes
from app.alerts.job import parse_time, run_alert_cycle
from app.notifications import telegram as tg
from app.notifications.service import build_alert_payload

NOW = datetime(2026, 11, 22, 12, 0, tzinfo=timezone.utc)
LISTING_ID = "22222222-2222-4222-8222-222222222222"


class Res:
    def __init__(self, data):
        self.data = data


class Q:
    def __init__(self, client, name):
        self.client, self.name, self.filters, self.rows, self.key = client, name, [], None, None

    def select(self, columns="*"):
        return self

    def eq(self, column, value):
        self.filters.append(("eq", column, value))
        return self

    def in_(self, column, values):
        self.filters.append(("in", column, list(values)))
        return self

    def limit(self, n):
        return self

    def upsert(self, rows, on_conflict=None):
        self.rows, self.key = rows, on_conflict
        return self

    def execute(self):
        table = self.client.tables.setdefault(self.name, [])
        if self.rows is not None:
            keys = self.key.split(",")
            for row in self.rows:
                same = [r for r in table if all(r.get(k) == row.get(k) for k in keys)]
                if same:
                    same[0].update(row)
                else:
                    table.append(dict(row))
            return Res(self.rows)
        found = []
        for row in table:
            ok = True
            for op, column, value in self.filters:
                ok = ok and (row.get(column) == value if op == "eq" else row.get(column) in value)
            if ok:
                found.append(dict(row))
        return Res(found)


class FakeClient:
    def __init__(self, tables=None):
        self.tables = tables or {}

    def table(self, name):
        return Q(self, name)


class BrokenClient:
    def table(self, name):
        raise RuntimeError("database down")


def listing_row(created=NOW):
    return {"id": LISTING_ID, "title": "Rice", "servings": 10, "food_category": "human",
            "status": "available", "latitude": 12.9716, "longitude": 77.5946,
            "created_at": created.isoformat(), "safe_until": (NOW + timedelta(hours=4)).isoformat()}


def receiver(name, km, **overrides):
    row = {"id": name, "latitude": 12.9716 + km / 111.0, "longitude": 77.5946,
           "approval_status": "approved", "is_verified": True, "is_flagged": False,
           "accepts_food_category": "human"}
    row.update(overrides)
    return row


def delivered(client):
    return {r["receiver_id"] for r in client.tables.get("alert_deliveries", [])}


def in_app_only():
    return [("in_app", tg.in_app_sender)]


def test_cycle_records_alerts_for_the_nearest_eligible_receivers():
    client = FakeClient({"food_listings": [listing_row()]})
    people = [receiver("a", 1), receiver("b", 2), receiver("bad", 1, approval_status="pending")]
    assert run_alert_cycle(client, NOW, in_app_only(), people) == 2
    assert delivered(client) == {"a", "b"}
    assert {r["channel"] for r in client.tables["alert_deliveries"]} == {"in_app"}


def test_running_again_sends_nothing_new():
    client = FakeClient({"food_listings": [listing_row()]})
    people = [receiver("a", 1)]
    assert run_alert_cycle(client, NOW, in_app_only(), people) == 1
    assert run_alert_cycle(client, NOW, in_app_only(), people) == 0
    assert len(client.tables["alert_deliveries"]) == 1


def test_tiers_widen_over_time():
    client = FakeClient({"food_listings": [listing_row()]})
    people = [receiver("near", 1), receiver("mid", 5)]
    run_alert_cycle(client, NOW, in_app_only(), people)
    assert delivered(client) == {"near"}
    run_alert_cycle(client, NOW + timedelta(minutes=6), in_app_only(), people)
    assert delivered(client) == {"near", "mid"}


def test_failing_telegram_falls_back_to_in_app():
    def boom(rcv, payload):
        raise RuntimeError("token=SECRET")

    client = FakeClient({"food_listings": [listing_row()]})
    channels = [("telegram", boom), ("in_app", tg.in_app_sender)]
    assert run_alert_cycle(client, NOW, channels, [receiver("a", 1)]) == 1
    assert client.tables["alert_deliveries"][0]["channel"] == "in_app"


def test_cycle_never_raises_when_the_database_is_down():
    assert run_alert_cycle(BrokenClient(), NOW, in_app_only(), []) == 0


def test_parse_time_handles_database_formats():
    assert parse_time("2026-11-22T12:00:00Z") == NOW
    assert parse_time("2026-11-22T12:00:00.12345+00:00").microsecond == 123450
    assert parse_time("garbage") is None
    assert parse_time(None) is None


def test_telegram_sender_needs_a_linked_chat():
    sender = tg.make_telegram_sender(FakeClient(), "SECRET-TOKEN")
    assert sender({"id": "r1"}, build_alert_payload(listing_row())) is False


def test_telegram_sender_posts_without_leaking_the_token(monkeypatch):
    sent = {}

    class Resp:
        status_code = 200

    def fake_post(url, json=None, timeout=None):
        sent.update(url=url, json=json)
        return Resp()

    monkeypatch.setattr(tg.httpx, "post", fake_post)
    client = FakeClient({"receiver_telegram_links": [{"receiver_id": "r1", "chat_id": "999"}]})
    sender = tg.make_telegram_sender(client, "SECRET-TOKEN", "https://app.example")
    assert sender({"id": "r1"}, build_alert_payload(listing_row())) is True
    assert sent["json"]["chat_id"] == "999"
    assert "SECRET-TOKEN" not in sent["json"]["text"]
    assert "https://app.example/receiver/listings/" in sent["json"]["text"]


def test_channels_include_telegram_only_when_the_token_is_set(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    assert [name for name, _ in tg.build_channels(FakeClient())] == ["in_app"]
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "x" * 20)
    assert [name for name, _ in tg.build_channels(FakeClient())] == ["telegram", "in_app"]


def test_my_alerts_lists_only_available_listings_for_this_receiver(monkeypatch):
    other = "99999999-9999-4999-8999-999999999999"
    client = FakeClient({
        "alert_deliveries": [
            {"listing_id": LISTING_ID, "receiver_id": "r1", "created_at": "2026-11-22T12:00:00+00:00"},
            {"listing_id": other, "receiver_id": "r1", "created_at": "2026-11-22T11:00:00+00:00"},
            {"listing_id": LISTING_ID, "receiver_id": "r2", "created_at": "2026-11-22T12:00:00+00:00"},
        ],
        "food_listings": [{"id": LISTING_ID, "status": "available"}, {"id": other, "status": "picked_up"}],
    })
    monkeypatch.setattr(aroutes, "get_supabase", lambda: client)
    response = Response()
    result = aroutes.my_alerts(response=response, user={"id": "r1"})
    assert [a["listing_id"] for a in result["alerts"]] == [LISTING_ID]
    assert result["alerts"][0]["url"] == "/receiver/listings/" + LISTING_ID
    assert response.headers.get("Cache-Control") == "no-store"
