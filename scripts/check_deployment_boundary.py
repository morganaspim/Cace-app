from __future__ import annotations

import json
from pathlib import Path


class DeploymentBoundaryError(ValueError):
    pass


PROTECTED_SERVICE_IDS = {
    "local_orchestrator",
    "scientific_runtime",
    "local_ai_broker",
    "account_store",
    "network_pairing_broker",
    "math_coin_broker",
    "monero_wallet_broker",
    "durable_storage",
    "native_worker",
    "formal_qualification_runner",
}


def load_policy(path: str | Path = "CACE_DEPLOYMENT_BOUNDARY.json") -> dict:
    target = Path(path)
    raw = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise DeploymentBoundaryError("deployment boundary policy must be a JSON object")
    return raw


def validate_policy(policy: dict) -> None:
    if policy.get("schema") != "cace.deployment-boundary.v1":
        raise DeploymentBoundaryError("unexpected deployment-boundary schema")

    public = policy.get("public_surface")
    if not isinstance(public, dict):
        raise DeploymentBoundaryError("public_surface is required")
    if public.get("service_id") != "web_gateway":
        raise DeploymentBoundaryError("web_gateway must be the only public application surface")
    if public.get("internet_exposed") is not True:
        raise DeploymentBoundaryError("web_gateway must be explicitly marked internet_exposed")

    browser = policy.get("browser_contract")
    if not isinstance(browser, dict):
        raise DeploymentBoundaryError("browser_contract is required")
    if browser.get("allowed_network_destinations") != ["web_gateway"]:
        raise DeploymentBoundaryError("browser may connect only to web_gateway")
    if browser.get("same_origin_api_only") is not True:
        raise DeploymentBoundaryError("same-origin API requirement must remain enabled")
    for field in (
        "direct_localhost_service_access",
        "direct_private_service_access",
        "executable_third_party_runtime_dependencies",
        "secrets_in_client_bundle",
    ):
        if browser.get(field) is not False:
            raise DeploymentBoundaryError(f"{field} must remain false")

    services = policy.get("private_services")
    if not isinstance(services, list) or not services:
        raise DeploymentBoundaryError("private_services must be a non-empty list")
    by_id = {}
    for service in services:
        if not isinstance(service, dict):
            raise DeploymentBoundaryError("private service entries must be objects")
        service_id = str(service.get("service_id", ""))
        if not service_id or service_id in by_id:
            raise DeploymentBoundaryError("private service IDs must be non-empty and unique")
        by_id[service_id] = service
        if service.get("public_listener") is not False:
            raise DeploymentBoundaryError(
                f"protected service {service_id} must not have a public listener"
            )

    missing = sorted(PROTECTED_SERVICE_IDS - set(by_id))
    if missing:
        raise DeploymentBoundaryError(
            f"deployment boundary missing protected services: {missing}"
        )

    hardening = policy.get("local_hardening")
    if not isinstance(hardening, dict):
        raise DeploymentBoundaryError("local_hardening is required")
    bind_policy = str(hardening.get("bind_policy", "")).lower()
    if "never 0.0.0.0" not in bind_policy or "public interface" not in bind_policy:
        raise DeploymentBoundaryError(
            "bind policy must explicitly forbid protected public listeners"
        )

    rules = policy.get("server_mediation_rules")
    if not isinstance(rules, list) or len(rules) < 5:
        raise DeploymentBoundaryError("server_mediation_rules are incomplete")

    acceptance = policy.get("production_acceptance")
    if not isinstance(acceptance, list) or len(acceptance) < 5:
        raise DeploymentBoundaryError("production_acceptance is incomplete")


def main() -> int:
    policy = load_policy()
    validate_policy(policy)
    print("CACE_DEPLOYMENT_BOUNDARY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
