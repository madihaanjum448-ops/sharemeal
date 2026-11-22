"""
Integration tests for 202611190001_timeout_strikes.sql against a REAL PostgreSQL, driving the real
lifecycle functions from 202611120003 / 202611120006 (claim -> timeout / cancel / safety expiry -> sweep).

SAFETY - these tests DROP and recreate schema `public`. They therefore refuse to run unless ALL hold:
  * SHAREMEAL_TEST_PG_DSN is set and points at a LOCAL host (unix socket, localhost, 127.0.0.1)
  * the database name contains 'test', 'qa' or 'scratch'
  * SHAREMEAL_TEST_PG_ALLOW_RESET=yes
They are never able to target Supabase. Without the DSN they are skipped with an explicit reason.

  createdb sharemeal_qa_scratch
  SHAREMEAL_TEST_PG_DSN="host=/var/run/postgresql dbname=sharemeal_qa_scratch user=postgres" \
  SHAREMEAL_TEST_PG_ALLOW_RESET=yes python -m pytest tests/sql -v

Optional: SHAREMEAL_MIGRATIONS_DIR (default supabase/migrations), SHAREMEAL_TEST_SCRATCH_BASE=0 to skip the
inferred base schema when your migrations directory already contains the real base DDL.
"""
import ipaddress
import os
import pathlib
import shlex
import threading
import urllib.parse
import uuid
from datetime import timedelta

import pytest

try:
    import psycopg
    from psycopg import errors as pgerr
    from psycopg.conninfo import conninfo_to_dict
except ImportError:
    psycopg = None
    class _DummyPgErr:
        class RaiseException(Exception): pass
        class UniqueViolation(Exception): pass
        class CheckViolation(Exception): pass
        class ForeignKeyViolation(Exception): pass
        class InsufficientPrivilege(Exception): pass
    pgerr = _DummyPgErr
    conninfo_to_dict = None

DSN = os.getenv("SHAREMEAL_TEST_PG_DSN")
ROOT = pathlib.Path(__file__).resolve().parents[2]
MIG_DIR = pathlib.Path(os.getenv("SHAREMEAL_MIGRATIONS_DIR", ROOT / "supabase" / "migrations"))
NEW_MIGRATION = "202611190001_timeout_strikes.sql"
HASH = "a" * 64


def _parse_dsn(dsn: str) -> dict:
    if not isinstance(dsn, str) or not dsn.strip():
        raise RuntimeError("REFUSING: empty or invalid DSN")

    # If psycopg's conninfo_to_dict is available, validate syntax through it
    if conninfo_to_dict is not None:
        try:
            conninfo_to_dict(dsn)
        except Exception as exc:
            raise RuntimeError(f"REFUSING: invalid DSN format: {exc}") from exc

    info = {}
    dsn_clean = dsn.strip()
    if dsn_clean.startswith("postgresql://") or dsn_clean.startswith("postgres://"):
        try:
            parsed = urllib.parse.urlparse(dsn_clean)
        except Exception as e:
            raise RuntimeError(f"REFUSING: unparseable URI DSN: {e}") from e
        if parsed.hostname:
            info["host"] = parsed.hostname
        if parsed.port:
            info["port"] = str(parsed.port)
        if parsed.username:
            info["user"] = parsed.username
        if parsed.path and parsed.path != "/":
            info["dbname"] = parsed.path.lstrip("/")
        if parsed.query:
            qs = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
            for k, v in qs.items():
                if len(v) > 1:
                    raise RuntimeError(f"REFUSING: ambiguous repeated parameter {k!r} in DSN query string")
                info[k] = v[0]
    else:
        try:
            tokens = shlex.split(dsn_clean)
        except Exception as e:
            raise RuntimeError(f"REFUSING: unparseable key-value DSN: {e}") from e
        if not tokens:
            raise RuntimeError("REFUSING: empty DSN tokens")
        for token in tokens:
            if "=" not in token:
                raise RuntimeError(f"REFUSING: invalid DSN token without '=': {token!r}")
            k, v = token.split("=", 1)
            k, v = k.strip(), v.strip()
            if not k:
                raise RuntimeError("REFUSING: invalid empty key in DSN")
            if k in info:
                raise RuntimeError(f"REFUSING: ambiguous duplicate key {k!r} in DSN")
            info[k] = v
    return info


def _guard(dsn: str):
    if not dsn or not isinstance(dsn, str) or not dsn.strip():
        raise RuntimeError("REFUSING: DSN is empty or not a string")

    if "supabase" in dsn.lower():
        raise RuntimeError("REFUSING: DSN contains 'supabase'")

    info = _parse_dsn(dsn)

    # 1. Database name check
    name = (info.get("dbname") or "").lower()
    if not name or not any(t in name for t in ("test", "qa", "scratch")):
        raise RuntimeError(f"REFUSING: database name {name!r} must contain 'test', 'qa' or 'scratch'")

    # 2. Reset permission environment variable check
    if os.getenv("SHAREMEAL_TEST_PG_ALLOW_RESET", "").lower() != "yes":
        raise RuntimeError("REFUSING: set SHAREMEAL_TEST_PG_ALLOW_RESET=yes (this test drops schema public)")

    # 3. Host and hostaddr validation
    raw_host = info.get("host")
    host = (raw_host or "").strip()
    raw_hostaddr = info.get("hostaddr")
    hostaddr = (raw_hostaddr or "").strip()

    # Reject ambiguous multiple hosts or hostaddrs
    if "," in host:
        raise RuntimeError(f"REFUSING: ambiguous multiple hosts in DSN: {host!r}")
    if "," in hostaddr:
        raise RuntimeError(f"REFUSING: ambiguous multiple hostaddrs in DSN: {hostaddr!r}")

    # Validate hostaddr if specified
    addr_ip = None
    if hostaddr:
        try:
            addr_ip = ipaddress.ip_address(hostaddr)
        except ValueError:
            raise RuntimeError(f"REFUSING: DSN hostaddr {hostaddr!r} is not a valid IP address")
        if not addr_ip.is_loopback:
            raise RuntimeError(f"REFUSING: DSN hostaddr {hostaddr!r} is not a loopback address")

    # Validate host if specified
    if host.startswith("/"):
        # Local Unix domain socket directory (e.g. /var/run/postgresql, /tmp)
        if hostaddr:
            raise RuntimeError(
                f"REFUSING: ambiguous configuration specifying both Unix socket host {host!r} and hostaddr {hostaddr!r}"
            )
    elif host == "" or host.lower() == "localhost":
        # Empty host (libpq defaults to local socket/localhost) or "localhost"
        pass
    else:
        # Host must be a valid loopback IP address
        try:
            host_ip = ipaddress.ip_address(host)
        except ValueError:
            raise RuntimeError(f"REFUSING: DSN host {host!r} is not a local scratch server")

        if not host_ip.is_loopback:
            raise RuntimeError(f"REFUSING: DSN host IP {host!r} is not a loopback address")

        if addr_ip is not None and host_ip != addr_ip:
            raise RuntimeError(
                f"REFUSING: ambiguous conflicting host IP {host!r} and hostaddr {hostaddr!r}"
            )


@pytest.fixture(scope="module")
def conn():
    if not psycopg:
        pytest.skip("NOT RUN: psycopg missing (pip install 'psycopg[binary]')")
    if not DSN:
        pytest.skip("NOT RUN: set SHAREMEAL_TEST_PG_DSN (+ SHAREMEAL_TEST_PG_ALLOW_RESET=yes) to a LOCAL scratch Postgres")
    _guard(DSN)
    c = psycopg.connect(DSN, autocommit=True)
    c.execute("DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;")
    if os.getenv("SHAREMEAL_TEST_SCRATCH_BASE", "1") != "0":
        c.execute((pathlib.Path(__file__).parent / "scratch_base_schema.sql").read_text())
    files = sorted(MIG_DIR.glob("*.sql"))
    assert any(f.name == NEW_MIGRATION for f in files), f"{NEW_MIGRATION} not found in {MIG_DIR}"
    for f in files:
        c.execute(f.read_text())
    yield c
    c.close()


class _DbTest:
    """Base class for database tests ensuring table cleanup runs only for database test cases."""
    @pytest.fixture(autouse=True)
    def clean(self, conn):
        conn.execute("TRUNCATE public.strike_events, public.pickup_handshakes, public.claims, "
                     "public.food_listings, public.user_profiles CASCADE")


class D:
    """Tiny helper around the connection."""
    def __init__(self, conn):
        self.c = conn

    def all(self, sql, *params):
        return self.c.execute(sql, params or None).fetchall()

    def val(self, sql, *params):
        return self.c.execute(sql, params or None).fetchone()[0]

    def receiver(self, verified=True):
        rid = uuid.uuid4()
        self.c.execute(
            "INSERT INTO public.user_profiles(id, role, is_verified, approval_status) "
            "VALUES (%s, 'receiver', %s, 'approved')",
            (rid, verified),
        )
        return rid

    def listing(self, safe_for=timedelta(hours=3)):
        lid = uuid.uuid4()
        self.c.execute("INSERT INTO public.food_listings(id, donor_id, safe_until) "
                       "VALUES (%s,%s, clock_timestamp() + %s)", (lid, uuid.uuid4(), safe_for))
        return lid

    def claim(self, lid, rid):
        cid = uuid.uuid4()
        res = self.val("SELECT public.claim_food_listing(%s,%s,%s,%s)", lid, rid, cid, HASH)
        assert res["success"] is True, res
        return cid

    def try_claim(self, lid, rid):
        return self.val("SELECT public.claim_food_listing(%s,%s,%s,%s)", lid, rid, uuid.uuid4(), HASH)

    def cancel(self, cid, rid):
        return self.val("SELECT public.cancel_food_claim(%s,%s)", cid, rid)

    def timer(self, cid, expires_in):
        """Fast-forward / rewind a claim's 15-minute timer (scratch DB only)."""
        self.c.execute("UPDATE public.claims SET expires_at = clock_timestamp() + %s, "
                       "claimed_at = clock_timestamp() + %s - interval '15 minutes' WHERE id=%s",
                       (expires_in, expires_in, cid))

    def safe_until(self, lid, delta):
        self.c.execute("UPDATE public.food_listings SET safe_until = clock_timestamp() + %s WHERE id=%s", (delta, lid))

    def sweep(self):
        return self.val("SELECT public.process_expired_claims_and_listings()")

    def strikes(self, lookback=None):
        if lookback is None:
            return self.val("SELECT public.apply_timeout_strikes()")
        return self.val("SELECT public.apply_timeout_strikes(%s)", lookback)

    def cycle(self):
        """What the worker does: sweep, then strikes."""
        return self.sweep(), self.strikes()

    def claim_status(self, cid):
        return self.val("SELECT status FROM public.claims WHERE id=%s", cid)

    def listing_status(self, lid):
        return self.val("SELECT status FROM public.food_listings WHERE id=%s", lid)

    def events(self, rid=None):
        if rid is None:
            return self.all("SELECT receiver_id, claim_id, event_type, reason FROM public.strike_events ORDER BY created_at")
        return self.all("SELECT receiver_id, claim_id, event_type, reason FROM public.strike_events "
                        "WHERE receiver_id=%s", rid)

    def n_events(self):
        return self.val("SELECT count(*) FROM public.strike_events")


@pytest.fixture
def d(conn):
    return D(conn)


# ============================================================ guard security tests
class TestGuard:
    """Unit tests verifying that _guard() strictly enforces local-only scratch database connections."""

    @pytest.fixture(autouse=True)
    def allow_reset(self, monkeypatch):
        monkeypatch.setenv("SHAREMEAL_TEST_PG_ALLOW_RESET", "yes")

    # --- Localhost and loopback IP acceptance ---
    @pytest.mark.parametrize("dsn", [
        "host=localhost dbname=sharemeal_test user=postgres",
        "host=localhost port=5432 dbname=sharemeal_qa",
        "host=127.0.0.1 dbname=sharemeal_scratch",
        "host=127.0.0.2 dbname=sharemeal_test",
        "host=::1 dbname=sharemeal_test",
        "host=localhost hostaddr=127.0.0.1 dbname=sharemeal_test",
        "host=localhost hostaddr=::1 dbname=sharemeal_qa",
        "hostaddr=127.0.0.1 dbname=sharemeal_scratch",
        "dbname=sharemeal_test",
        "postgresql://localhost/sharemeal_test",
        "postgresql://127.0.0.1/sharemeal_qa",
        "postgresql://user:pass@localhost:5432/sharemeal_scratch?hostaddr=127.0.0.1",
    ])
    def test_guard_accepts_localhost_and_loopback(self, dsn):
        _guard(dsn)

    # --- Unix socket acceptance ---
    @pytest.mark.parametrize("dsn", [
        "host=/var/run/postgresql dbname=sharemeal_qa_scratch user=postgres",
        "host=/tmp dbname=sharemeal_test",
        "host='/var/run/postgresql' dbname='my_test_db'",
    ])
    def test_guard_accepts_unix_sockets(self, dsn):
        _guard(dsn)

    # --- Remote hostaddr rejection ---
    @pytest.mark.parametrize("dsn", [
        "host=localhost hostaddr=192.168.1.5 dbname=sharemeal_test",
        "host=localhost hostaddr=10.0.0.1 dbname=sharemeal_qa",
        "host=localhost hostaddr=8.8.8.8 dbname=sharemeal_scratch",
        "host=localhost hostaddr=172.16.0.50 dbname=sharemeal_test",
        "hostaddr=192.168.1.100 dbname=sharemeal_test",
        "hostaddr=203.0.113.195 dbname=sharemeal_test",
        "postgresql://localhost/sharemeal_test?hostaddr=192.168.1.5",
        "postgresql://localhost/sharemeal_test?hostaddr=10.0.0.1",
    ])
    def test_guard_rejects_remote_hostaddr(self, dsn):
        with pytest.raises(RuntimeError, match="REFUSING: DSN hostaddr .* is not a loopback address"):
            _guard(dsn)

    # --- Non-loopback IP rejection (both host and hostaddr) ---
    @pytest.mark.parametrize("dsn,match", [
        ("host=0.0.0.0 dbname=sharemeal_test", "not a loopback address"),
        ("host=localhost hostaddr=0.0.0.0 dbname=sharemeal_test", "not a loopback address"),
        ("host=192.168.1.1 dbname=sharemeal_test", "not a loopback address"),
        ("host=10.0.0.1 dbname=sharemeal_test", "not a loopback address"),
    ])
    def test_guard_rejects_non_loopback_ips(self, dsn, match):
        with pytest.raises(RuntimeError, match=match):
            _guard(dsn)

    # --- Remote host rejection ---
    @pytest.mark.parametrize("dsn", [
        "host=db.remote.com dbname=sharemeal_test",
        "host=example.com dbname=sharemeal_qa",
        "host=localhost.evil.com dbname=sharemeal_scratch",
        "postgresql://db.remote.com/sharemeal_test",
    ])
    def test_guard_rejects_remote_hosts(self, dsn):
        with pytest.raises(RuntimeError, match="REFUSING: DSN host .* is not a local scratch server"):
            _guard(dsn)

    # --- Ambiguous remote connection configurations ---
    @pytest.mark.parametrize("dsn,match", [
        ("host=/var/run/postgresql hostaddr=127.0.0.1 dbname=sharemeal_test", "both Unix socket host .* and hostaddr"),
        ("host=/tmp hostaddr=192.168.1.1 dbname=sharemeal_test", "is not a loopback address"),
        ("host=localhost,remotehost dbname=sharemeal_test", "ambiguous multiple hosts"),
        ("host=127.0.0.1,192.168.1.1 dbname=sharemeal_test", "ambiguous multiple hosts"),
        ("host=localhost hostaddr=127.0.0.1,192.168.1.1 dbname=sharemeal_test", "ambiguous multiple hostaddrs"),
        ("host=127.0.0.1 hostaddr=127.0.0.2 dbname=sharemeal_test", "conflicting host IP .* and hostaddr"),
        ("host=localhost host=remotehost dbname=sharemeal_test", "ambiguous duplicate key"),
        ("postgresql://localhost/sharemeal_test?hostaddr=127.0.0.1&hostaddr=10.0.0.1", "ambiguous repeated parameter"),
    ])
    def test_guard_rejects_ambiguous_configurations(self, dsn, match):
        with pytest.raises(RuntimeError, match=match):
            _guard(dsn)

    # --- Invalid DSNs ---
    @pytest.mark.parametrize("dsn,match", [
        ("", "empty or not a string"),
        ("   ", "empty or not a string"),
        ("not_a_valid_dsn_no_equals", "invalid DSN format"),
        ("host=localhost hostaddr=not_an_ip dbname=sharemeal_test", "not a valid IP address"),
        ("host=localhost dbname=production", "must contain 'test', 'qa' or 'scratch'"),
        ("host=localhost dbname=my_db", "must contain 'test', 'qa' or 'scratch'"),
        ("host=localhost dbname=sharemeal_test_supabase", "contains 'supabase'"),
        ("postgresql://user:pass@mydb.supabase.co:5432/sharemeal_test", "contains 'supabase'"),
    ])
    def test_guard_rejects_invalid_dsns(self, dsn, match):
        with pytest.raises(RuntimeError, match=match):
            _guard(dsn)

    def test_guard_rejects_missing_allow_reset(self, monkeypatch):
        monkeypatch.delenv("SHAREMEAL_TEST_PG_ALLOW_RESET", raising=False)
        with pytest.raises(RuntimeError, match="SHAREMEAL_TEST_PG_ALLOW_RESET=yes"):
            _guard("host=localhost dbname=sharemeal_test")


# ============================================================ eligible: genuine receiver timeout
class TestEligibleTimeout(_DbTest):
    def test_timed_out_claim_gets_exactly_one_persisted_strike(self, d):
        r, l = d.receiver(), d.listing()
        c = d.claim(l, r)
        d.timer(c, timedelta(minutes=-2))
        swept, struck = d.cycle()
        assert swept == {"expired_claims": 1, "reopened_listings": 1, "expired_listings": 0}
        assert struck == {"strikes_added": 1}
        assert d.claim_status(c) == "expired" and d.listing_status(l) == "available"
        assert d.events() == [(r, c, "timeout", "claim timed out")]

    def test_event_time_is_the_timeout_moment_and_recorded_at_is_audit_time(self, d):
        r, l = d.receiver(), d.listing()
        c = d.claim(l, r)
        d.timer(c, timedelta(minutes=-2))
        d.cycle()
        created, recorded, expires = d.all(
            "SELECT s.created_at, s.recorded_at, c.expires_at FROM public.strike_events s JOIN public.claims c ON c.id=s.claim_id")[0]
        assert created == expires and recorded >= created

    def test_timeout_reconciled_inline_by_a_new_claim_still_gets_a_strike(self, d):
        """The sweep never ran: claim_food_listing expired A's stale claim itself. Strikes must still catch it."""
        r1, r2, l = d.receiver(), d.receiver(), d.listing()
        a = d.claim(l, r1)
        d.timer(a, timedelta(minutes=-1))
        b = d.try_claim(l, r2)
        assert b["success"] is True
        assert d.claim_status(a) == "expired"
        assert d.strikes() == {"strikes_added": 1}
        assert [e[0] for e in d.events()] == [r1]          # only the receiver who timed out
        assert d.events(r2) == []

    def test_late_cancel_after_timer_is_a_timeout_decision_D2(self, d):
        """DECISION D-2: cancelling AFTER the 15-minute timer already ended counts as a timeout."""
        r, l = d.receiver(), d.listing()
        c = d.claim(l, r)
        d.timer(c, timedelta(minutes=-1))
        res = d.cancel(c, r)
        assert res["code"] == "EXPIRED" and d.claim_status(c) == "expired"
        assert d.strikes() == {"strikes_added": 1}

    def test_strikes_are_attributed_per_receiver_and_per_claim(self, d):
        r1, r2 = d.receiver(), d.receiver()
        for _ in range(3):
            l = d.listing(); c = d.claim(l, r1); d.timer(c, timedelta(minutes=-1))
        l = d.listing(); c = d.claim(l, r2); d.timer(c, timedelta(minutes=-1))
        d.cycle()
        assert len(d.events(r1)) == 3 and len(d.events(r2)) == 1   # 3 == pure-service FLAG_THRESHOLD


# ============================================================ ineligible: must never strike
class TestIneligibleExpiry(_DbTest):
    @pytest.mark.parametrize("safe_until_in,timer_in", [
        (timedelta(minutes=-1), timedelta(minutes=10)),    # food unsafe before the timer even ended
        (timedelta(minutes=-5), timedelta(minutes=-1)),    # both elapsed, food-safety deadline came first
    ])
    def test_food_safety_expiry_gives_no_strike(self, d, safe_until_in, timer_in):
        r, l = d.receiver(), d.listing()
        c = d.claim(l, r)
        d.safe_until(l, safe_until_in)
        d.timer(c, timer_in)
        swept, struck = d.cycle()
        assert swept["expired_listings"] == 1 and d.claim_status(c) == "expired"
        assert d.listing_status(l) == "expired"
        assert struck == {"strikes_added": 0} and d.n_events() == 0

    def test_cancelled_claim_gives_no_strike_even_after_its_timer_passes(self, d):
        r, l = d.receiver(), d.listing()
        c = d.claim(l, r)
        res = d.cancel(c, r)
        assert res["success"] is True and d.claim_status(c) == "cancelled"
        d.timer(c, timedelta(minutes=-30))
        d.cycle()
        assert d.claim_status(c) == "cancelled" and d.n_events() == 0

    @pytest.mark.parametrize("status", ["completed", "picked_up"])
    def test_finished_pickup_gives_no_strike(self, d, status):
        r, l = d.receiver(), d.listing()
        c = d.claim(l, r)
        d.c.execute("UPDATE public.claims SET status=%s WHERE id=%s", (status, c))
        d.timer(c, timedelta(minutes=-30))
        d.cycle()
        assert d.n_events() == 0

    def test_active_unexpired_claim_gives_no_strike(self, d):
        r, l = d.receiver(), d.listing()
        c = d.claim(l, r)
        assert d.cycle()[1] == {"strikes_added": 0}
        assert d.claim_status(c) == "active" and d.n_events() == 0

    def test_receiver_who_verified_pickup_handshake_is_not_struck(self, d):
        r, l = d.receiver(), d.listing()
        c = d.claim(l, r)
        d.c.execute("UPDATE public.pickup_handshakes SET verified_at = clock_timestamp() WHERE claim_id=%s", (c,))
        d.timer(c, timedelta(minutes=-1))
        d.cycle()
        assert d.claim_status(c) == "expired" and d.n_events() == 0

    def test_claim_expired_before_lookback_window_is_not_retroactively_struck_D4(self, d):
        """DECISION D-4: default 48h lookback, so deploying cannot mass-punish old history."""
        r, l = d.receiver(), d.listing(timedelta(days=10))
        c = d.claim(l, r)
        d.c.execute("UPDATE public.claims SET status='expired', expires_at = clock_timestamp() - interval '3 days', "
                    "claimed_at = clock_timestamp() - interval '3 days 15 minutes' WHERE id=%s", (c,))
        assert d.strikes() == {"strikes_added": 0}
        assert d.strikes(timedelta(days=7)) == {"strikes_added": 1}      # explicit backfill is possible

    @pytest.mark.parametrize("bad", [timedelta(0), timedelta(hours=-1)])
    def test_non_positive_lookback_is_rejected(self, d, bad):
        with pytest.raises(pgerr.RaiseException):
            d.strikes(bad)


# ============================================================ duplicate execution / idempotency
class TestIdempotency(_DbTest):
    def test_repeated_worker_cycles_never_double_count(self, d):
        r, l = d.receiver(), d.listing()
        c = d.claim(l, r)
        d.timer(c, timedelta(minutes=-1))
        first = d.cycle()
        second = d.cycle()
        third = d.cycle()
        assert first[1] == {"strikes_added": 1}
        assert second[1] == third[1] == {"strikes_added": 0}
        assert d.n_events() == 1

    def test_calling_strikes_repeatedly_without_sweep_is_idempotent(self, d):
        r, l = d.receiver(), d.listing()
        c = d.claim(l, r)
        d.timer(c, timedelta(minutes=-1))
        d.sweep()
        assert [d.strikes()["strikes_added"] for _ in range(5)] == [1, 0, 0, 0, 0]
        assert d.n_events() == 1

    def test_reopened_listing_reclaimed_and_timed_out_again_gives_a_second_strike_for_the_new_claim(self, d):
        r, l = d.receiver(), d.listing()
        c1 = d.claim(l, r); d.timer(c1, timedelta(minutes=-1)); d.cycle()
        c2 = d.claim(l, r); d.timer(c2, timedelta(minutes=-1)); d.cycle()
        assert d.n_events() == 2 and c1 != c2

    def test_database_enforces_one_timeout_per_claim_even_for_direct_inserts(self, d):
        r, l = d.receiver(), d.listing()
        c = d.claim(l, r)
        ins = ("INSERT INTO public.strike_events(receiver_id, claim_id, event_type, reason, created_at) "
               "VALUES (%s,%s,'timeout','x', now())")
        d.c.execute(ins, (r, c))
        with pytest.raises(pgerr.UniqueViolation):
            d.c.execute(ins, (r, c))

    def test_concurrent_workers_produce_exactly_one_strike_per_claim(self, conn, d):
        r = d.receiver()
        for _ in range(20):
            l = d.listing(); c = d.claim(l, r); d.timer(c, timedelta(minutes=-1))
        d.sweep()
        barrier, results, errors = threading.Barrier(8), [], []

        def worker():
            try:
                with psycopg.connect(DSN, autocommit=True) as c2:
                    barrier.wait(timeout=20)
                    results.append(c2.execute("SELECT public.apply_timeout_strikes()").fetchone()[0]["strikes_added"])
            except Exception as exc:       # noqa: BLE001 - surfaced by the assertion below
                errors.append(repr(exc))
        ts = [threading.Thread(target=worker) for _ in range(8)]
        [t.start() for t in ts]
        [t.join(timeout=60) for t in ts]
        assert errors == [], errors
        assert sum(results) == 20 and d.n_events() == 20

    def test_concurrent_full_sweeps_and_strikes_do_not_deadlock_or_duplicate(self, d):
        r = d.receiver()
        for _ in range(10):
            l = d.listing(); c = d.claim(l, r); d.timer(c, timedelta(minutes=-1))
        barrier, errors = threading.Barrier(6), []

        def worker():
            try:
                with psycopg.connect(DSN, autocommit=True) as c2:
                    barrier.wait(timeout=20)
                    c2.execute("SELECT public.process_expired_claims_and_listings()").fetchone()
                    c2.execute("SELECT public.apply_timeout_strikes()").fetchone()
            except Exception as exc:       # noqa: BLE001
                errors.append(repr(exc))
        ts = [threading.Thread(target=worker) for _ in range(6)]
        [t.start() for t in ts]
        [t.join(timeout=60) for t in ts]
        assert errors == [], errors
        d.cycle()   # catch anything a racing sweep had not yet committed
        assert d.n_events() == 10


# ============================================================ existing behaviour unchanged
class TestCompatibility(_DbTest):
    def test_sweep_response_shape_is_unchanged(self, d):
        assert set(d.sweep()) == {"expired_claims", "reopened_listings", "expired_listings"}

    def test_new_migration_is_rerunnable(self, conn, d):
        r, l = d.receiver(), d.listing()
        c = d.claim(l, r); d.timer(c, timedelta(minutes=-1)); d.cycle()
        conn.execute((MIG_DIR / NEW_MIGRATION).read_text())
        conn.execute((MIG_DIR / NEW_MIGRATION).read_text())
        assert d.n_events() == 1 and d.strikes() == {"strikes_added": 0}


# ============================================================ constraints & privileges
class TestConstraintsAndPrivileges(_DbTest):
    def test_timeout_event_requires_a_claim(self, d):
        r = d.receiver()
        with pytest.raises(pgerr.CheckViolation):
            d.c.execute("INSERT INTO public.strike_events(receiver_id, claim_id, event_type, reason, created_at) "
                        "VALUES (%s, NULL, 'timeout', 'x', now())", (r,))

    def test_admin_clear_event_may_have_no_claim_and_unknown_types_are_rejected(self, d):
        r = d.receiver()
        d.c.execute("INSERT INTO public.strike_events(receiver_id, claim_id, event_type, reason, created_at) "
                    "VALUES (%s, NULL, 'admin_clear', 'review', now())", (r,))
        with pytest.raises(pgerr.CheckViolation):
            d.c.execute("INSERT INTO public.strike_events(receiver_id, claim_id, event_type, reason, created_at) "
                        "VALUES (%s, NULL, 'banned', 'x', now())", (r,))

    def test_claim_with_a_strike_cannot_be_deleted_D3(self, d):
        """DECISION D-3: ON DELETE RESTRICT keeps the audit trail intact."""
        r, l = d.receiver(), d.listing()
        c = d.claim(l, r); d.timer(c, timedelta(minutes=-1)); d.cycle()
        with pytest.raises(pgerr.ForeignKeyViolation):
            d.c.execute("DELETE FROM public.claims WHERE id=%s", (c,))

    @pytest.mark.parametrize("role", ["anon", "authenticated"])
    def test_public_roles_cannot_run_the_function_or_read_the_table(self, conn, role):
        for stmt in ("SELECT public.apply_timeout_strikes()", "SELECT * FROM public.strike_events"):
            with pytest.raises(pgerr.InsufficientPrivilege):
                with conn.transaction():
                    conn.execute(f"SET LOCAL ROLE {role}")
                    conn.execute(stmt)

    def test_service_role_can_run_and_read_but_log_is_append_only(self, conn, d):
        r, l = d.receiver(), d.listing()
        c = d.claim(l, r); d.timer(c, timedelta(minutes=-1)); d.sweep()
        with conn.transaction():
            conn.execute("SET LOCAL ROLE service_role")
            assert conn.execute("SELECT public.apply_timeout_strikes()").fetchone()[0] == {"strikes_added": 1}
            assert conn.execute("SELECT count(*) FROM public.strike_events").fetchone()[0] == 1
        for stmt in ("UPDATE public.strike_events SET reason='tampered'", "DELETE FROM public.strike_events",
                     "TRUNCATE public.strike_events"):
            with pytest.raises(pgerr.InsufficientPrivilege):
                with conn.transaction():
                    conn.execute("SET LOCAL ROLE service_role")
                    conn.execute(stmt)
