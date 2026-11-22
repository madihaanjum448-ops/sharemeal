from app.matching.fetch import fetch_flagged_receiver_ids


class Res:
    def __init__(self, data):
        self.data = data


class Query:
    def __init__(self, rows):
        self.rows = list(rows)

    def select(self, columns="*"):
        return self

    def in_(self, column, values):
        self.rows = [r for r in self.rows if r[column] in values]
        return self

    def order(self, column, desc=False):
        self.rows = sorted(self.rows, key=lambda r: r[column], reverse=desc)
        return self

    def execute(self):
        return Res(self.rows)


class Client:
    def __init__(self, rows=(), broken=False):
        self.rows, self.broken = list(rows), broken

    def table(self, name):
        if self.broken:
            raise RuntimeError("database down")
        assert name == "strike_events"
        return Query(self.rows)


def ev(receiver, kind, minute):
    return {
        "receiver_id": receiver,
        "claim_id": "c%d" % minute if kind == "timeout" else None,
        "event_type": kind,
        "reason": "test",
        "created_at": "2026-11-20T10:%02d:00+00:00" % minute,
    }


def timeouts(receiver, minutes):
    return [ev(receiver, "timeout", m) for m in minutes]


def test_three_timeouts_flag_the_receiver():
    assert fetch_flagged_receiver_ids(Client(timeouts("r1", [1, 2, 3]))) == {"r1"}


def test_two_timeouts_do_not_flag():
    assert fetch_flagged_receiver_ids(Client(timeouts("r1", [1, 2]))) == set()


def test_admin_clear_removes_the_flag():
    rows = timeouts("r1", [1, 2, 3]) + [ev("r1", "admin_clear", 4)]
    assert fetch_flagged_receiver_ids(Client(rows)) == set()


def test_strikes_after_a_clear_count_from_zero_and_can_flag_again():
    base = timeouts("r1", [1, 2, 3]) + [ev("r1", "admin_clear", 4)]
    assert fetch_flagged_receiver_ids(Client(base + timeouts("r1", [5, 6]))) == set()
    assert fetch_flagged_receiver_ids(Client(base + timeouts("r1", [5, 6, 7]))) == {"r1"}


def test_receivers_are_counted_separately():
    rows = timeouts("r1", [1, 2, 3]) + timeouts("r2", [4, 5])
    assert fetch_flagged_receiver_ids(Client(rows)) == {"r1"}


def test_a_database_failure_never_raises():
    assert fetch_flagged_receiver_ids(Client(broken=True)) == set()
