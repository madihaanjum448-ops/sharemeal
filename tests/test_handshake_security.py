import pytest
from pydantic import ValidationError

from app.handshake.routes import VerifyCodeRequest


@pytest.mark.parametrize("code", ["1234", "0000", "9999"])
def test_accepts_exactly_four_ascii_digits(code):
    assert VerifyCodeRequest(code=code).code == code


@pytest.mark.parametrize(
    "code",
    ["١٢٣٤", "１２３４", "123", "12345", "12 4", "1234\n", " 1234", "abcd", ""],
)
def test_rejects_everything_else(code):
    with pytest.raises(ValidationError):
        VerifyCodeRequest(code=code)
