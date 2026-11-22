from unittest.mock import MagicMock, call, patch

import pytest

from app.jobs.expiry_worker import run_expiry_and_timeout_sweep


def test_expiry_worker_calls_correct_rpc_and_returns_result():
    expected = {
        "expired_claims": 2,
        "reopened_listings": 1,
        "expired_listings": 0,
    }
    sweep_response = MagicMock()
    sweep_response.data = expected
    strike_response = MagicMock()
    strike_response.data = {"strikes_added": 2}

    mock_db = MagicMock()
    mock_db.rpc.return_value.execute.side_effect = [sweep_response, strike_response]

    with patch("app.jobs.expiry_worker.get_supabase", return_value=mock_db):
        result = run_expiry_and_timeout_sweep()

    # Sweep first, then timeout strikes; the returned value is still the sweep result, unchanged.
    assert mock_db.rpc.call_args_list == [
        call("process_expired_claims_and_listings", {}),
        call("apply_timeout_strikes", {}),
    ]
    assert result == expected


def test_expiry_worker_propagates_rpc_error():
    mock_db = MagicMock()
    mock_db.rpc.return_value.execute.side_effect = RuntimeError("DB unavailable")

    with patch("app.jobs.expiry_worker.get_supabase", return_value=mock_db):
        with pytest.raises(RuntimeError, match="DB unavailable"):
            run_expiry_and_timeout_sweep()


def test_expiry_worker_rejects_non_dict_response():
    mock_response = MagicMock()
    mock_response.data = ["unexpected", "response"]

    mock_db = MagicMock()
    mock_db.rpc.return_value.execute.return_value = mock_response

    with patch("app.jobs.expiry_worker.get_supabase", return_value=mock_db):
        with pytest.raises(RuntimeError, match="unexpected response"):
            run_expiry_and_timeout_sweep()
