import pytest
from fastapi import HTTPException
from app.core.rate_limit import enforce_otp_send_limit


def test_rate_limiter_blocks_after_limit():
    key = "test-rate-limit-case"
    enforce_otp_send_limit(key, 1, 300)
    with pytest.raises(HTTPException) as exc:
        enforce_otp_send_limit(key, 1, 300)
    assert exc.value.status_code == 429
