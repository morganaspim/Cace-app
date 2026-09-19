from __future__ import annotations

import json
from pathlib import Path


class PublicServicePolicyError(ValueError):
    pass


def _load(path: str | Path) -> dict:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise PublicServicePolicyError(f"{path} must contain an object")
    return raw


def validate_access_policy(policy: dict) -> None:
    if policy.get("schema") != "cace.public-service-access.v1":
        raise PublicServicePolicyError("unexpected public-service schema")
    access = policy.get("public_access")
    if not isinstance(access, dict):
        raise PublicServicePolicyError("public_access is required")
    if access.get("default") != "allow":
        raise PublicServicePolicyError("public service default must remain allow")
    blocked = set(access.get("blocked_country_codes", []))
    if blocked != {"CN", "KP"}:
        raise PublicServicePolicyError(
            "country access policy must block exactly CN and KP unless explicitly revised"
        )
    enforcement = set(access.get("enforcement_points", []))
    required = {
        "CDN/edge or reverse proxy before application routing",
        "signup/account creation",
        "session renewal and high-risk privileged actions",
        "local-agent broker registration",
    }
    if not required.issubset(enforcement):
        raise PublicServicePolicyError("country block enforcement points are incomplete")
    signup = policy.get("signup")
    if not isinstance(signup, dict) or signup.get("enabled") is not True:
        raise PublicServicePolicyError("public signup must remain enabled")
    if signup.get("creates_logical_tenant_instance") is not True:
        raise PublicServicePolicyError("signup must provision/restore a logical tenant instance")


def validate_telemetry_policy(policy: dict) -> None:
    if policy.get("schema") != "cace.telemetry-privacy.v1":
        raise PublicServicePolicyError("unexpected telemetry policy schema")
    lanes = policy.get("lanes")
    if not isinstance(lanes, list):
        raise PublicServicePolicyError("telemetry lanes are required")
    by_id = {str(item.get("id")): item for item in lanes if isinstance(item, dict)}
    required = {
        "essential_operations",
        "product_analytics",
        "proof_research_contribution",
    }
    if set(by_id) != required:
        raise PublicServicePolicyError("telemetry lane set is incomplete")
    if by_id["essential_operations"].get("default") != "on":
        raise PublicServicePolicyError("essential operational telemetry must remain on for hosted service")
    if by_id["product_analytics"].get("default") != "off_until_clear_consent_or_approved_legal_basis":
        raise PublicServicePolicyError("product analytics privacy default changed")
    if by_id["proof_research_contribution"].get("default") != "off":
        raise PublicServicePolicyError("proof contribution must be explicit opt-in")
    heartbeat = policy.get("heartbeat_reporting")
    if not isinstance(heartbeat, dict):
        raise PublicServicePolicyError("heartbeat_reporting is required")
    if heartbeat.get("all_hosted_instances_send_essential_heartbeat") is not True:
        raise PublicServicePolicyError("hosted essential heartbeat requirement changed")


def main() -> int:
    validate_access_policy(_load("CACE_PUBLIC_SERVICE_POLICY.json"))
    validate_telemetry_policy(_load("CACE_TELEMETRY_PRIVACY_POLICY.json"))
    print("CACE_PUBLIC_SERVICE_TELEMETRY_POLICY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
