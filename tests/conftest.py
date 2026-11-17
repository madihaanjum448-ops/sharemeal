"""
Shared pytest configuration for ShareMeal.

Provides dummy credentials before application modules are imported.
Blocks outbound HTTPX requests during tests.
These values and guards are test-only.
"""

import os

import httpx
import pytest

# Set test-only credentials before importing application modules.
os.environ["SUPABASE_URL"] = "https://example.supabase.co"
os.environ["SUPABASE_KEY"] = "test-service-role-key"
os.environ["SUPABASE_ANON_KEY"] = "test-anon-key"
os.environ["HANDSHAKE_SECRET"] = "test-only-handshake-secret"
os.environ["EXPIRY_SWEEP_INTERVAL_SECONDS"] = "60"
os.environ["APP_ENV"] = "test"


@pytest.fixture(autouse=True)
def block_outbound_httpx(monkeypatch):
    """Prevent tests from making real outbound HTTP requests."""

    def blocked_sync_request(self, request):
        raise RuntimeError(
            f"Blocked outbound HTTP request during tests: {request.method} {request.url}"
        )

    async def blocked_async_request(self, request):
        raise RuntimeError(
            f"Blocked outbound HTTP request during tests: {request.method} {request.url}"
        )

    monkeypatch.setattr(
        httpx.HTTPTransport,
        "handle_request",
        blocked_sync_request,
    )
    monkeypatch.setattr(
        httpx.AsyncHTTPTransport,
        "handle_async_request",
        blocked_async_request,
    )
