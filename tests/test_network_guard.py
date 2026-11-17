import httpx
import pytest


def test_sync_httpx_requests_are_blocked():
    transport = httpx.HTTPTransport()
    request = httpx.Request("GET", "https://example.com")

    with pytest.raises(RuntimeError, match="Blocked outbound HTTP request"):
        transport.handle_request(request)


@pytest.mark.anyio
async def test_async_httpx_requests_are_blocked():
    transport = httpx.AsyncHTTPTransport()
    request = httpx.Request("GET", "https://example.com")

    with pytest.raises(RuntimeError, match="Blocked outbound HTTP request"):
        await transport.handle_async_request(request)
