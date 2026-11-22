import httpx
import pytest


def test_sync_httpx_requests_are_blocked():
    transport = httpx.HTTPTransport()
    request = httpx.Request("GET", "https://example.com")

    with pytest.raises(RuntimeError, match="Blocked outbound HTTP request"):
        transport.handle_request(request)


def test_async_httpx_requests_are_blocked():
    transport = httpx.AsyncHTTPTransport()
    request = httpx.Request("GET", "https://example.com")

    with pytest.raises(RuntimeError, match="Blocked outbound HTTP request"):
        coro = transport.handle_async_request(request)
        try:
            coro.send(None)
        finally:
            coro.close()
