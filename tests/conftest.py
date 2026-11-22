import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _no_handshake_secret(monkeypatch):
    """Keep tests independent of a local .env: the handshake is off unless a test turns it on."""
    monkeypatch.delenv("HANDSHAKE_SECRET", raising=False)
