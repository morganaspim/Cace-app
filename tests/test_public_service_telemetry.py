from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from cace_studio.telemetry_contract import (
    TelemetryContractError,
    TelemetryEvent,
    essential_heartbeat,
    proof_status_summary,
    validate_telemetry_event,
)
from scripts.check_public_service_telemetry_policy import (
    PublicServicePolicyError,
    _load,
    validate_access_policy,
    validate_telemetry_policy,
)


ROOT = Path(__file__).resolve().parents[1]


def test_access_policy_blocks_requested_country_codes():
    policy = _load(ROOT / "CACE_PUBLIC_SERVICE_POLICY.json")
    validate_access_policy(policy)
    assert set(policy["public_access"]["blocked_country_codes"]) == {"CN", "KP"}


def test_removing_country_block_fails_closed():
    policy = deepcopy(_load(ROOT / "CACE_PUBLIC_SERVICE_POLICY.json"))
    policy["public_access"]["blocked_country_codes"] = ["KP"]
    with pytest.raises(PublicServicePolicyError, match="CN and KP"):
        validate_access_policy(policy)


def test_telemetry_policy_keeps_proof_content_opt_in():
    policy = _load(ROOT / "CACE_TELEMETRY_PRIVACY_POLICY.json")
    validate_telemetry_policy(policy)
    lanes = {item["id"]: item for item in policy["lanes"]}
    assert lanes["proof_research_contribution"]["default"] == "off"


def test_essential_heartbeat_contains_only_safe_metadata():
    event = essential_heartbeat(
        release="v-test",
        health="ok",
        online=True,
        resource_bucket="cpu-low",
        job_count=2,
        feature_heartbeat_counts={"canvas": 3},
    )
    assert event.lane == "essential_operations"
    validate_telemetry_event(event)


def test_proof_status_summary_is_counts_not_proof_text():
    event = proof_status_summary(passed=4, failed=1, not_run=2, release="v-test")
    assert "proof_text" not in event.payload
    validate_telemetry_event(event)


def test_essential_telemetry_rejects_proof_text():
    event = TelemetryEvent(
        lane="essential_operations",
        event_type="proof.status_summary",
        payload={"release": "x", "proof_text": "secret theorem body"},
    )
    with pytest.raises(TelemetryContractError, match="forbidden"):
        validate_telemetry_event(event)


def test_product_analytics_rejects_raw_filename():
    event = TelemetryEvent(
        lane="product_analytics",
        event_type="feature.usage",
        payload={"feature_id": "canvas", "filename": "private-project.cace"},
    )
    with pytest.raises(TelemetryContractError, match="forbidden"):
        validate_telemetry_event(event)


def test_actual_proof_contribution_uses_separate_contract():
    event = TelemetryEvent(
        lane="proof_research_contribution",
        event_type="proof.upload",
        payload={"count": 1},
    )
    with pytest.raises(TelemetryContractError, match="separate explicit-consent"):
        validate_telemetry_event(event)
