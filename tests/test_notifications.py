from app.notifications.service import (
    MAX_BODY_LENGTH, build_alert_payload, deliver_to_receiver,
    dispatch_alerts, listing_deep_link,
)

LISTING = {
    "id": "L1", "title": "Veg biryani", "servings": 20, "food_category": "human",
    "pickup_address": "12 Secret Street, Indiranagar",
    "latitude": 12.9716, "longitude": 77.5946,
}
RECEIVER = {"id": "r1"}


def recorder(result=True, raises=None):
    calls = []

    def sender(receiver, payload):
        calls.append(receiver["id"])
        if raises:
            raise raises
        return result

    sender.calls = calls
    return sender


def test_deep_link_format():
    assert listing_deep_link("abc") == "/receiver/listings/abc"
    assert listing_deep_link("abc", "/x/") == "/x/abc"


def test_payload_has_link_and_tag():
    payload = build_alert_payload(LISTING)
    assert payload["url"] == "/receiver/listings/L1"
    assert payload["tag"] == "listing-L1"


def test_payload_never_contains_address_or_coordinates():
    text = str(build_alert_payload(LISTING))
    assert "Secret Street" not in text
    assert "12.9716" not in text and "77.5946" not in text


def test_long_title_is_truncated():
    payload = build_alert_payload(dict(LISTING, title="x" * 500))
    assert len(payload["body"]) <= MAX_BODY_LENGTH


def test_push_success_skips_telegram():
    push, telegram = recorder(True), recorder(True)
    result = deliver_to_receiver(RECEIVER, {}, [("push", push), ("telegram", telegram)])
    assert result.delivered and result.channel == "push"
    assert telegram.calls == []


def test_push_returning_false_falls_back_to_telegram():
    push, telegram = recorder(False), recorder(True)
    result = deliver_to_receiver(RECEIVER, {}, [("push", push), ("telegram", telegram)])
    assert result.delivered and result.channel == "telegram"


def test_push_exception_falls_back_and_hides_message():
    push = recorder(raises=RuntimeError("token=SECRET123"))
    telegram = recorder(True)
    result = deliver_to_receiver(RECEIVER, {}, [("push", push), ("telegram", telegram)])
    assert result.delivered and result.channel == "telegram"
    assert "SECRET123" not in str(result.errors)
    assert "RuntimeError" in str(result.errors)


def test_all_channels_failing_does_not_raise():
    push = recorder(raises=ValueError("x"))
    telegram = recorder(False)
    result = deliver_to_receiver(RECEIVER, {}, [("push", push), ("telegram", telegram)])
    assert result.delivered is False and result.channel is None


def test_dispatch_returns_only_reached_receivers_and_counts_failures():
    def sender(receiver, payload):
        return receiver["id"] != "bad"

    outcome = dispatch_alerts(LISTING, [{"id": "ok"}, {"id": "bad"}], [("push", sender)])
    assert outcome.delivered_ids == ["ok"]
    assert outcome.attempts == {"bad": 1}


def test_one_failing_receiver_does_not_stop_the_others():
    def sender(receiver, payload):
        if receiver["id"] == "a":
            raise RuntimeError("boom")
        return True

    receivers = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    outcome = dispatch_alerts(LISTING, receivers, [("push", sender)])
    assert outcome.delivered_ids == ["b", "c"]


def test_dispatch_gives_up_after_max_attempts():
    sender = recorder(False)
    outcome = dispatch_alerts(
        LISTING, [{"id": "r1"}], [("push", sender)], attempts={"r1": 3}, max_attempts=3)
    assert sender.calls == [] and outcome.delivered_ids == []


def test_dispatch_does_not_modify_attempts_input():
    attempts = {"r1": 1}
    dispatch_alerts(LISTING, [{"id": "r1"}], [("push", recorder(False))], attempts=attempts)
    assert attempts == {"r1": 1}
