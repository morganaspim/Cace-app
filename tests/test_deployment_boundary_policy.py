from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.check_deployment_boundary import (
    DeploymentBoundaryError,
    load_policy,
    validate_policy,
)


ROOT = Path(__file__).resolve().parents[1]


def _policy():
    return load_policy(ROOT / "CACE_DEPLOYMENT_BOUNDARY.json")


def test_production_policy_is_valid():
    validate_policy(_policy())


def test_browser_can_only_reach_gateway():
    policy = _policy()
    assert policy["browser_contract"]["allowed_network_destinations"] == ["web_gateway"]
    assert policy["browser_contract"]["direct_localhost_service_access"] is False
    assert policy["browser_contract"]["direct_private_service_access"] is False


def test_all_protected_services_are_non_public():
    policy = _policy()
    assert policy["private_services"]
    assert all(item["public_listener"] is False for item in policy["private_services"])


def test_making_wallet_or_proof_runner_public_fails_closed():
    for target in ("monero_wallet_broker", "formal_qualification_runner"):
        policy = deepcopy(_policy())
        for item in policy["private_services"]:
            if item["service_id"] == target:
                item["public_listener"] = True
        with pytest.raises(DeploymentBoundaryError, match="public listener"):
            validate_policy(policy)


def test_browser_direct_model_access_fails_closed():
    policy = deepcopy(_policy())
    policy["browser_contract"]["allowed_network_destinations"] = [
        "web_gateway",
        "local_ai_broker",
    ]
    with pytest.raises(DeploymentBoundaryError, match="only to web_gateway"):
        validate_policy(policy)


def test_policy_has_no_embedded_private_wallet_material():
    raw = json.dumps(_policy()).casefold()
    forbidden = (
        "mnemonic",
        "private_spend_key",
        "private_view_key",
        "wallet_seed",
        "wallet_rpc_password",
    )
    assert all(term not in raw for term in forbidden)
