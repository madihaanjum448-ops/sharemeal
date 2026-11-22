import re
import uuid
from unittest.mock import patch

from app.claims.routes import ClaimRequest, create_claim
from app.core.config import settings
from app.handshake.service import derive_code, hash_code


def test_claim_creation_uses_handshake_aware_rpc_without_exposing_code():
    listing_id = uuid.uuid4()
    receiver_id = str(uuid.uuid4())

    user = {
        "id": receiver_id,
        "role": "receiver",
        "is_verified": True,
        "approval_status": "approved",
    }

    response_data = {
        "success": True,
        "claim_id": str(uuid.uuid4()),
        "listing_id": str(listing_id),
        "status": "active",
    }

    with patch("app.claims.routes.get_supabase") as mock_db:
        mock_db.return_value.rpc.return_value.execute.return_value.data = response_data

        result = create_claim(
            ClaimRequest(listing_id=listing_id),
            user=user,
        )

    rpc_args, _ = mock_db.return_value.rpc.call_args

    assert rpc_args[0] == "claim_food_listing"

    params = rpc_args[1]

    assert set(params.keys()) == {
        "p_listing_id",
        "p_receiver_id",
        "p_claim_id",
        "p_handshake_code_hash",
    }

    assert params["p_listing_id"] == str(listing_id)
    assert params["p_receiver_id"] == receiver_id

    claim_id = params["p_claim_id"]
    uuid.UUID(claim_id)

    pickup_code = derive_code(claim_id, settings.HANDSHAKE_SECRET)
    expected_hash = hash_code(
        pickup_code,
        claim_id,
        settings.HANDSHAKE_SECRET,
    )

    assert params["p_handshake_code_hash"] == expected_hash
    assert re.fullmatch(r"[0-9a-f]{64}", params["p_handshake_code_hash"])

    assert "pickup_code" not in result
    assert pickup_code not in str(result)
