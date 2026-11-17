from unittest.mock import MagicMock, patch

import pytest

from app.jobs.expiry_worker import run_expiry_and_timeout_sweep


def test_expiry_worker_calls_correct_rpc_and_returns_result():
    expected = {
        "expired_claims": 2,
        "reopened_listings": 1,
        "expired_listings": 0,
    }
    mock_response = MagicMock()
    mock_response.data = expected

    mock_db = MagicMock()
    mock_db.rpc.return_value.execute.return_value = mock_response

    with patch("app.jobs.expiry_worker.get_supabase", return_value=mock_db):
        result = run_expiry_and_timeout_sweep()

    mock_db.rpc.assert_called_once_with(
        "process_expired_claims_and_listings", {}
    )
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
