from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import subprocess
from typing import Any
from urllib.request import Request, urlopen

from mcp.server.mcpserver import MCPServer
import oci

from .policy import (
    ManagedIngressRequest,
    is_managed_rule_description,
    select_managed_rule_ids,
    validate_log_lines,
    validate_source_cidr,
    require_merlin_rsi_signing,
)
from .runner_inventory import collect_runner_status

mcp = MCPServer(
    "CACE OCI Control Plane",
    instructions=(
        "Narrow operational control plane for one CACE OCI VM. "
        "Never claim a write succeeded unless the tool response says it did. "
        "Network changes are restricted to attached NSGs and TCP 80/443. "
        "No generic shell, IAM mutation, secret access, instance termination, "
        "or arbitrary OCI API execution is exposed."
    ),
)

MCP_HOST = os.getenv("CACE_OCI_MCP_HOST", "127.0.0.1")
MCP_PORT = int(os.getenv("CACE_OCI_MCP_PORT", "8765"))
ALLOW_SERVICE_RESTART = os.getenv("CACE_OCI_MCP_ALLOW_SERVICE_RESTART", "").lower() == "true"
ALLOW_NETWORK_WRITE = os.getenv("CACE_OCI_MCP_ALLOW_NETWORK_WRITE", "").lower() == "true"
ALLOW_MERLIN_RSI_SIGNING = os.getenv("CACE_OCI_MCP_ALLOW_MERLIN_RSI_SIGNING", "").lower() == "true"
MERLIN_RSI_SIGNING_KEY = Path("/var/lib/cace-oci-mcp/keys/merlin-rsi-attestor-ed25519.pem")
CACE_SERVICE = "cace-web"
ALLOW_MERLIN_ARTIFACT_REF = os.getenv("CACE_OCI_MCP_ALLOW_MERLIN_ARTIFACT_REF", "").lower() == "true"
MERLIN_ARTIFACT_REF_SIGNING_KEY = Path("/var/lib/cace-oci-mcp/keys/merlin-artifact-ref-attestor-ed25519.pem")


def _merlin_artifact_resolver(artifact_ref: dict[str, Any]) -> dict[str, Any]:
    """Authenticated read-only transport; endpoint and bearer token are runtime secrets."""
    import urllib.error
    import urllib.request
    from urllib.parse import urlsplit

    endpoint = os.getenv("MERLIN_ARTIFACT_RESOLVER_URL", "").strip()
    token = os.getenv("MERLIN_ARTIFACT_RESOLVER_TOKEN", "")
    parsed = urlsplit(endpoint)
    if (
        parsed.scheme != "https" or not parsed.hostname
        or parsed.username is not None or parsed.password is not None
        or parsed.query or parsed.fragment
        or not parsed.path.rstrip("/").endswith("/api/artifacts/resolve")
        or not token
    ):
        raise RuntimeError("authenticated Merlin ArtifactRef resolver endpoint is invalid or unconfigured")
    body = json.dumps({
        "schema": "merlin-artifact-resolution-request/1",
        "artifact_ref": artifact_ref,
    }, separators=(",", ":"), sort_keys=True).encode("utf-8")
    request = Request(endpoint, data=body, method="POST", headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "CACE-Merlin-ArtifactRef-Verifier/1",
    })
    try:
        class _RejectRedirects(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                raise urllib.error.HTTPError(req.full_url, code, "resolver redirects are forbidden", headers, fp)

        opener = urllib.request.build_opener(_RejectRedirects)
        with opener.open(request, timeout=15) as response:
            raw = response.read(14_000_001)
    except Exception as exc:
        raise RuntimeError(f"authenticated Merlin artifact resolution failed: {type(exc).__name__}") from None
    if len(raw) > 14_000_000:
        raise RuntimeError("Merlin resolver response exceeded the accepted size")
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("Merlin resolver response must be an object")
    return payload


def _merlin_artifact_ref_trust_root_provider() -> dict[str, Any]:
    """Read the trust anchor from separately administered protected deployment config."""
    from cace_studio.core.attestation import public_key_id

    public_pem = os.getenv("CACE_MERLIN_ARTIFACT_REF_TRUST_ROOT_PUBLIC_KEY_PEM", "")
    authority_id = os.getenv("CACE_MERLIN_ARTIFACT_REF_TRUST_ROOT_AUTHORITY_ID", "")
    provisioning_identity = os.getenv("CACE_MERLIN_ARTIFACT_REF_TRUST_ROOT_PROVISIONING_IDENTITY", "")
    version_text = os.getenv("CACE_MERLIN_ARTIFACT_REF_TRUST_ROOT_VERSION", "")
    if not all((public_pem, authority_id, provisioning_identity, version_text)):
        raise RuntimeError("independently provisioned ArtifactRef trust root is unavailable")
    try:
        version = int(version_text)
    except ValueError as exc:
        raise RuntimeError("independent ArtifactRef trust-root version is invalid") from exc
    if version < 1:
        raise RuntimeError("independent ArtifactRef trust-root version is invalid")
    pem_bytes = public_pem.encode("ascii")
    return {
        "schema": "merlin-independent-trust-root-v1",
        "authority_id": authority_id,
        "version": version,
        "key_id": public_key_id(pem_bytes),
        "public_key_pem": public_pem,
        "source_authority": "protected-deployment-config:CACE_MERLIN_ARTIFACT_REF_TRUST_ROOT_PUBLIC_KEY_PEM",
        "provisioning_identity": provisioning_identity,
    }


def _merlin_artifact_ref_trust_store_provider() -> dict[str, Any]:
    """Retrieve the signed trust-store receipt from OCI Vault using instance identity."""
    secret_ocid = os.getenv("CACE_MERLIN_ARTIFACT_REF_TRUST_STORE_SECRET_OCID", "")
    if not secret_ocid.startswith("ocid1.vaultsecret."):
        raise RuntimeError("ArtifactRef signed trust-store Vault secret is unavailable")
    client = oci.secrets.SecretsClient(config={}, signer=_signer())
    bundle = client.get_secret_bundle(secret_id=secret_ocid).data
    content = getattr(bundle, "secret_bundle_content", None)
    if content is None or getattr(content, "content_type", None) != "BASE64":
        raise RuntimeError("ArtifactRef trust-store Vault secret has an unsupported content type")
    try:
        raw = base64.b64decode(content.content.encode("ascii"), validate=True)
        payload = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise RuntimeError("ArtifactRef signed trust-store Vault secret is malformed") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("ArtifactRef signed trust-store Vault secret must be an object")
    metadata = _metadata()
    instance_id = metadata.get("id")
    if not isinstance(instance_id, str) or not instance_id:
        raise RuntimeError("OCI instance identity is unavailable for trust-store retrieval")
    return {
        **payload,
        "source_authority": f"oci-vault-secret:{secret_ocid}",
        "retrieval_identity": f"oci-instance-principal:{instance_id}",
    }


@mcp.tool()
def get_merlin_artifact_ref_capability() -> dict[str, Any]:
    """Report readiness without exposing resolver credentials or trust material."""
    endpoint = os.getenv("MERLIN_ARTIFACT_RESOLVER_URL", "").strip()
    token_configured = bool(os.getenv("MERLIN_ARTIFACT_RESOLVER_TOKEN", ""))
    key_ready = MERLIN_ARTIFACT_REF_SIGNING_KEY.is_file() and not MERLIN_ARTIFACT_REF_SIGNING_KEY.is_symlink()
    root_ready = all(os.getenv(name, "") for name in (
        "CACE_MERLIN_ARTIFACT_REF_TRUST_ROOT_PUBLIC_KEY_PEM",
        "CACE_MERLIN_ARTIFACT_REF_TRUST_ROOT_AUTHORITY_ID",
        "CACE_MERLIN_ARTIFACT_REF_TRUST_ROOT_PROVISIONING_IDENTITY",
        "CACE_MERLIN_ARTIFACT_REF_TRUST_ROOT_VERSION",
    ))
    trust_store_ready = os.getenv(
        "CACE_MERLIN_ARTIFACT_REF_TRUST_STORE_SECRET_OCID", ""
    ).startswith("ocid1.vaultsecret.")
    resolver_ready = endpoint.startswith("https://") and endpoint.rstrip("/").endswith("/api/artifacts/resolve") and token_configured
    configured = ALLOW_MERLIN_ARTIFACT_REF and resolver_ready and key_ready and root_ready and trust_store_ready
    return {
        "schema": "cace-capability-status-v1",
        "capability_id": "merlin.artifact_ref.attestation",
        "status": "unqualified" if configured else "unavailable",
        "configuration": "configured" if configured else "incomplete",
        "checks": {
            "feature_flag_enabled": ALLOW_MERLIN_ARTIFACT_REF,
            "https_resolver_and_token_configured": resolver_ready,
            "separate_signing_key_present": key_ready,
            "independently_provisioned_trust_root_present": root_ready,
            "signed_trust_store_vault_secret_configured": trust_store_ready,
            "independent_protected_qualification_receipt": False,
        },
        "authority": "verification-only",
        "proof_effect": "none",
    }


@mcp.tool()
def initialize_merlin_artifact_ref_attestor() -> dict[str, Any]:
    """Create a distinct ArtifactRef Ed25519 key once; never overwrite an existing key."""
    if not ALLOW_MERLIN_ARTIFACT_REF:
        raise PermissionError("Merlin ArtifactRef capability is disabled")
    from .merlin_artifact_ref import initialize_merlin_artifact_ref_attestor as initialize
    return initialize(
        private_key_path=MERLIN_ARTIFACT_REF_SIGNING_KEY,
        cace_app_root=os.getenv("CACE_APP_ROOT", "/opt/cace-web/current"),
    )


@mcp.tool()
def attest_merlin_artifact_ref(
    bundle_payload: dict[str, Any],
    artifact_ref: dict[str, Any],
    source_repo: str,
    source_commit: str,
    artifact_id: str,
    artifact_kind: str,
    artifact_schema: str,
) -> dict[str, Any]:
    """Resolve exact historical Merlin bytes independently and sign ArtifactRef identity.

    Separate opt-in capability; integrity only, proof_effect=none, no promotion authority.
    """
    if not ALLOW_MERLIN_ARTIFACT_REF:
        raise PermissionError("Merlin ArtifactRef attestation is unavailable; its separate capability is disabled")
    from .merlin_artifact_ref import attest_merlin_artifact_ref as attest
    key_path = MERLIN_ARTIFACT_REF_SIGNING_KEY
    if not key_path.is_file() or key_path.is_symlink():
        raise PermissionError("CACE ArtifactRef signing key is not provisioned")
    return attest(
        bundle_payload=bundle_payload, artifact_ref=artifact_ref,
        source_repo=source_repo, source_commit=source_commit,
        artifact_id=artifact_id, artifact_kind=artifact_kind,
        artifact_schema=artifact_schema, resolver=_merlin_artifact_resolver,
        private_key_pem=key_path.read_bytes(),
        cace_app_root=os.getenv("CACE_APP_ROOT", "/opt/cace-web/current"),
    )


@mcp.tool()
def verify_merlin_artifact_ref(
    bundle_payload: dict[str, Any],
    attestation_payload: dict[str, Any],
    artifact_ref: dict[str, Any],
    source_repo: str,
    source_commit: str,
    artifact_id: str,
    artifact_kind: str,
    artifact_schema: str,
) -> dict[str, Any]:
    """Re-resolve historical bytes and verify the signed ArtifactRef against pinned trust."""
    from .merlin_artifact_ref import verify_merlin_artifact_ref as verify
    return verify(
        bundle_payload=bundle_payload, attestation_payload=attestation_payload,
        artifact_ref=artifact_ref, source_repo=source_repo,
        source_commit=source_commit, artifact_id=artifact_id,
        artifact_kind=artifact_kind, artifact_schema=artifact_schema,
        resolver=_merlin_artifact_resolver,
        trust_root_provider=_merlin_artifact_ref_trust_root_provider,
        trust_store_provider=_merlin_artifact_ref_trust_store_provider,
        cace_app_root=os.getenv("CACE_APP_ROOT", "/opt/cace-web/current"),
    )


IMDS_INSTANCE = "http://169.254.169.254/opc/v2/instance/"
IMDS_VNICS = "http://169.254.169.254/opc/v2/vnics/"
MANAGED_RULE_PREFIX = "CACE-MCP-MANAGED"




def _imds_json(url: str) -> Any:
    request = Request(url, headers={"Authorization": "Bearer Oracle"})
    with urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def _metadata() -> dict[str, Any]:
    payload = _imds_json(IMDS_INSTANCE)
    if not isinstance(payload, dict):
        raise RuntimeError("unexpected OCI instance metadata response")
    return payload


def _signer():
    return oci.auth.signers.InstancePrincipalsSecurityTokenSigner()


def _clients():
    signer = _signer()
    return (
        oci.core.ComputeClient(config={}, signer=signer),
        oci.core.VirtualNetworkClient(config={}, signer=signer),
    )


def _attached_vnics(network_client) -> list[dict[str, Any]]:
    payload = _imds_json(IMDS_VNICS)
    if not isinstance(payload, list):
        raise RuntimeError("unexpected OCI VNIC metadata response")
    result: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        vnic_id = item.get("vnicId")
        if not isinstance(vnic_id, str) or not vnic_id:
            continue
        vnic = network_client.get_vnic(vnic_id).data
        result.append(
            {
                "id": vnic.id,
                "display_name": vnic.display_name,
                "is_primary": bool(vnic.is_primary),
                "private_ip": vnic.private_ip,
                "public_ip": vnic.public_ip,
                "subnet_id": vnic.subnet_id,
                "nsg_ids": list(vnic.nsg_ids or ()),
            }
        )
    result.sort(key=lambda item: (not item["is_primary"], item["id"]))
    return result


def _attached_nsg_ids(network_client) -> set[str]:
    return {
        nsg_id
        for vnic in _attached_vnics(network_client)
        for nsg_id in vnic["nsg_ids"]
        if isinstance(nsg_id, str) and nsg_id
    }


def _require_attached_nsg(network_client, nsg_id: str) -> str:
    if not isinstance(nsg_id, str) or not nsg_id.strip():
        raise ValueError("nsg_id must be a non-empty OCID")
    candidate = nsg_id.strip()
    attached = _attached_nsg_ids(network_client)
    if candidate not in attached:
        raise PermissionError(
            "refusing network write: requested NSG is not attached to this CACE VM"
        )
    return candidate


def _run_command(argv: list[str], *, timeout: int = 20) -> dict[str, Any]:
    completed = subprocess.run(
        argv,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return {
        "argv": argv,
        "returncode": completed.returncode,
        "stdout": completed.stdout[-16000:],
        "stderr": completed.stderr[-16000:],
    }


def _service_active() -> bool:
    result = _run_command(["/usr/bin/systemctl", "is-active", "--quiet", CACE_SERVICE])
    return result["returncode"] == 0


def _health_probe() -> dict[str, Any]:
    try:
        with urlopen("http://127.0.0.1:8000/api/health", timeout=3) as response:
            body = response.read().decode("utf-8")
        payload = json.loads(body)
        return {
            "reachable": True,
            "status_code": 200,
            "payload": payload,
        }
    except Exception as exc:
        return {
            "reachable": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


@mcp.tool()
def get_github_runner_status() -> dict[str, Any]:
    """Read local GitHub Actions runner metadata without reading credentials or contacting GitHub."""
    return collect_runner_status()


@mcp.tool()
def initialize_merlin_rsi_attestor() -> dict[str, Any]:
    """Create the CACE Merlin RSI Ed25519 signing identity once, without overwriting it."""
    require_merlin_rsi_signing(ALLOW_MERLIN_RSI_SIGNING)
    from .merlin_rsi_verifier import initialize_merlin_rsi_attestor as initialize

    return initialize(
        private_key_path=MERLIN_RSI_SIGNING_KEY,
        cace_app_root=os.getenv("CACE_APP_ROOT", "/opt/cace-web/current"),
    )


@mcp.tool()
def attest_merlin_rsi_reproduction(
    bundle_payload: dict[str, Any],
    expected_claim_id: str,
    expected_bindings: dict[str, Any],
    artifact_bytes_b64: dict[str, str],
    github_run_id: int,
) -> dict[str, Any]:
    """Verify exact CACE OCI run provenance and sign an independent-reproduction attestation.

    Requires a successful fixed-profile run on cace-oci-a1, exact pinned source
    commit, frozen 25-case held-out suite, retained job artifact, and exact
    EvidenceBundle bytes. This attestation still has proof_effect=none and
    cannot promote a candidate.
    """
    require_merlin_rsi_signing(ALLOW_MERLIN_RSI_SIGNING)
    from .merlin_rsi_verifier import attest_merlin_rsi_reproduction as attest

    key_path = os.getenv(
        "CACE_MERLIN_RSI_SIGNING_KEY_PATH",
        "/var/lib/cace-oci-mcp/keys/merlin-rsi-attestor-ed25519.pem",
    )
    return attest(
        bundle_payload=bundle_payload,
        expected_claim_id=expected_claim_id,
        expected_bindings=expected_bindings,
        artifact_bytes_b64=artifact_bytes_b64,
        github_run_id=github_run_id,
        private_key_path=key_path,
        cace_app_root=os.getenv("CACE_APP_ROOT", "/opt/cace-web/current"),
    )


@mcp.tool()
def attest_merlin_rsi_bundle(
    bundle_payload: dict[str, Any],
    expected_claim_id: str,
    expected_bindings: dict[str, Any],
    artifact_bytes_b64: dict[str, str],
) -> dict[str, Any]:
    """Verify exact EvidenceBundle artifact bytes and sign a CACE artifact-integrity attestation.

    This is provenance/integrity only (proof_effect=none). It does not run
    candidate code, prove a theorem, or authorize promotion.
    """
    require_merlin_rsi_signing(ALLOW_MERLIN_RSI_SIGNING)
    from .merlin_rsi_verifier import attest_merlin_rsi_bundle as attest

    return attest(
        bundle_payload=bundle_payload,
        expected_claim_id=expected_claim_id,
        expected_bindings=expected_bindings,
        artifact_bytes_b64=artifact_bytes_b64,
        private_key_path=MERLIN_RSI_SIGNING_KEY,
        cace_app_root=os.getenv("CACE_APP_ROOT", "/opt/cace-web/current"),
    )


@mcp.tool()
def verify_merlin_rsi_attestation(
    bundle_payload: dict[str, Any],
    attestation_payload: dict[str, Any],
    expected_claim_id: str,
    expected_bindings: dict[str, Any],
    artifact_bytes_b64: dict[str, str],
) -> dict[str, Any]:
    """Verify a Merlin RSI EvidenceBundle and CACE-signed independent-reproduction attestation.

    The verifier key allowlist is loaded only from the service's digest-pinned
    environment trust store. Callers cannot supply or override trusted keys.
    This operation is read-only and never upgrades proof or promotion state.
    """
    from .merlin_rsi_verifier import verify_merlin_rsi_attestation as verify

    return verify(
        bundle_payload=bundle_payload,
        attestation_payload=attestation_payload,
        expected_claim_id=expected_claim_id,
        expected_bindings=expected_bindings,
        artifact_bytes_b64=artifact_bytes_b64,
        trust_store_json=os.getenv("CACE_MERLIN_RSI_TRUST_STORE_JSON", ""),
        trust_store_sha256=os.getenv("CACE_MERLIN_RSI_TRUST_STORE_SHA256", ""),
        cace_app_root=os.getenv("CACE_APP_ROOT", "/opt/cace-web/current"),
    )


@mcp.tool()
def get_control_capabilities() -> dict[str, Any]:
    """Return the narrow capability switches for this OCI MCP server."""
    return {
        "service_restart_enabled": ALLOW_SERVICE_RESTART,
        "network_write_enabled": ALLOW_NETWORK_WRITE,
        "network_write_scope": "attached NSGs only; TCP 80/443 only",
        "generic_shell_exposed": False,
        "iam_mutation_exposed": False,
        "secret_access_exposed": False,
        "instance_termination_exposed": False,
        "merlin_rsi_signing_enabled": ALLOW_MERLIN_RSI_SIGNING,
        "merlin_artifact_ref_attestation": "configured" if ALLOW_MERLIN_ARTIFACT_REF and os.getenv("MERLIN_ARTIFACT_RESOLVER_URL", "").startswith("https://") and bool(os.getenv("MERLIN_ARTIFACT_RESOLVER_TOKEN")) and MERLIN_ARTIFACT_REF_SIGNING_KEY.is_file() else "unavailable",
        "private_signing_key_read_enabled": ALLOW_MERLIN_RSI_SIGNING,
        "merlin_rsi_attestation": "independent-reproduction verification; separate opt-in artifact-integrity attestor; no proof or promotion authority",
        "mcp_listen": f"{MCP_HOST}:{MCP_PORT}",
    }


@mcp.tool()
def get_cace_runtime_status() -> dict[str, Any]:
    """Read CACE service state and localhost health without changing anything."""
    current = Path("/opt/cace-web/current")
    target = None
    if current.is_symlink():
        try:
            target = str(current.resolve(strict=False))
        except OSError:
            target = None
    return {
        "service": CACE_SERVICE,
        "active": _service_active(),
        "health": _health_probe(),
        "current_release": target,
    }


@mcp.tool()
def get_cace_logs(lines: int = 80) -> dict[str, Any]:
    """Read the last 1-200 journal lines for the CACE web service."""
    count = validate_log_lines(lines)
    result = _run_command(
        [
            "/usr/bin/journalctl",
            "-u",
            CACE_SERVICE,
            "-n",
            str(count),
            "--no-pager",
            "--output=short-iso",
        ]
    )
    return {
        "lines_requested": count,
        "ok": result["returncode"] == 0,
        "output": result["stdout"],
        "error": result["stderr"],
    }


@mcp.tool()
def get_oci_instance_summary() -> dict[str, Any]:
    """Inspect this VM and its VNIC/NSG attachments using an OCI instance principal."""
    metadata = _metadata()
    compute_client, network_client = _clients()
    instance_id = str(metadata["id"])
    instance = compute_client.get_instance(instance_id).data
    return {
        "instance": {
            "id": instance.id,
            "display_name": instance.display_name,
            "compartment_id": instance.compartment_id,
            "availability_domain": instance.availability_domain,
            "fault_domain": instance.fault_domain,
            "region": metadata.get("region"),
            "shape": instance.shape,
            "lifecycle_state": instance.lifecycle_state,
            "time_created": str(instance.time_created),
        },
        "vnics": _attached_vnics(network_client),
    }


@mcp.tool()
def get_attached_nsg_rules() -> dict[str, Any]:
    """List security rules for NSGs attached to this VM. Security lists are not modified."""
    _, network_client = _clients()
    result: list[dict[str, Any]] = []
    for nsg_id in sorted(_attached_nsg_ids(network_client)):
        nsg = network_client.get_network_security_group(nsg_id).data
        rules = network_client.list_network_security_group_security_rules(nsg_id).data
        result.append(
            {
                "nsg_id": nsg_id,
                "display_name": nsg.display_name,
                "rules": [
                    {
                        "id": rule.id,
                        "direction": rule.direction,
                        "protocol": rule.protocol,
                        "source": rule.source,
                        "source_type": rule.source_type,
                        "destination": rule.destination,
                        "destination_type": rule.destination_type,
                        "description": rule.description,
                        "is_stateless": bool(rule.is_stateless),
                        "tcp_options": (
                            {
                                "destination_port_range": (
                                    {
                                        "min": rule.tcp_options.destination_port_range.min,
                                        "max": rule.tcp_options.destination_port_range.max,
                                    }
                                    if rule.tcp_options
                                    and rule.tcp_options.destination_port_range
                                    else None
                                )
                            }
                            if rule.tcp_options
                            else None
                        ),
                        "managed_by_cace_mcp": is_managed_rule_description(rule.description),
                    }
                    for rule in rules
                ],
            }
        )
    return {
        "attached_nsg_count": len(result),
        "network_security_groups": result,
        "note": (
            "This tool intentionally does not mutate subnet security lists. "
            "Oracle recommends NSGs for resource-specific rules."
        ),
    }


@mcp.tool()
def restart_cace_web() -> dict[str, Any]:
    """Restart only the cace-web systemd service when the restart capability is enabled."""
    if not ALLOW_SERVICE_RESTART:
        raise PermissionError(
            "service restart is disabled; set CACE_OCI_MCP_ALLOW_SERVICE_RESTART=true "
            "and install the narrow sudoers rule to enable it"
        )
    before = _service_active()
    restart = _run_command(
        ["/usr/bin/sudo", "-n", "/usr/bin/systemctl", "restart", CACE_SERVICE],
        timeout=30,
    )
    after = _service_active()
    health = _health_probe()
    return {
        "before_active": before,
        "restart_returncode": restart["returncode"],
        "restart_stderr": restart["stderr"],
        "after_active": after,
        "health": health,
        "success": restart["returncode"] == 0 and after and health.get("reachable") is True,
    }


@mcp.tool()
def ensure_web_ingress(
    nsg_id: str,
    source_cidr: str,
    enable_http: bool = True,
    enable_https: bool = True,
) -> dict[str, Any]:
    """Add missing MCP-managed TCP 80/443 ingress rules to an attached NSG only."""
    if not ALLOW_NETWORK_WRITE:
        raise PermissionError(
            "network writes are disabled; set CACE_OCI_MCP_ALLOW_NETWORK_WRITE=true "
            "after granting the instance principal a narrowly scoped NSG policy"
        )
    source = validate_source_cidr(source_cidr)
    requested_ports = [
        port
        for port, enabled in ((80, enable_http), (443, enable_https))
        if enabled
    ]
    if not requested_ports:
        raise ValueError("at least one of enable_http or enable_https must be true")

    _, network_client = _clients()
    attached_nsg_id = _require_attached_nsg(network_client, nsg_id)
    existing = network_client.list_network_security_group_security_rules(attached_nsg_id).data

    present: set[tuple[str, int]] = set()
    for rule in existing:
        if (
            rule.direction == "INGRESS"
            and rule.protocol == "6"
            and rule.source == source
            and rule.tcp_options
            and rule.tcp_options.destination_port_range
            and rule.tcp_options.destination_port_range.min
            == rule.tcp_options.destination_port_range.max
        ):
            present.add(
                (source, int(rule.tcp_options.destination_port_range.min))
            )

    missing = [
        ManagedIngressRequest(source, port)
        for port in requested_ports
        if (source, port) not in present
    ]
    if not missing:
        return {
            "success": True,
            "changed": False,
            "nsg_id": attached_nsg_id,
            "source_cidr": source,
            "ports": requested_ports,
            "message": "matching ingress rules already exist",
        }

    details = oci.core.models.AddNetworkSecurityGroupSecurityRulesDetails(
        security_rules=[
            oci.core.models.AddSecurityRuleDetails(
                direction="INGRESS",
                protocol="6",
                description=request.description,
                is_stateless=False,
                source=request.source_cidr,
                source_type="CIDR_BLOCK",
                tcp_options=oci.core.models.TcpOptions(
                    destination_port_range=oci.core.models.PortRange(
                        min=request.port,
                        max=request.port,
                    )
                ),
            )
            for request in missing
        ]
    )
    response = network_client.add_network_security_group_security_rules(
        attached_nsg_id,
        details,
    )
    return {
        "success": True,
        "changed": True,
        "nsg_id": attached_nsg_id,
        "source_cidr": source,
        "ports_added": [request.port for request in missing],
        "rule_ids": [rule.id for rule in response.data.security_rules],
        "description_prefix": MANAGED_RULE_PREFIX,
    }


@mcp.tool()
def remove_mcp_managed_web_ingress(nsg_id: str) -> dict[str, Any]:
    """Remove only CACE-MCP-MANAGED rules from an NSG attached to this VM."""
    if not ALLOW_NETWORK_WRITE:
        raise PermissionError(
            "network writes are disabled; set CACE_OCI_MCP_ALLOW_NETWORK_WRITE=true "
            "after granting the instance principal a narrowly scoped NSG policy"
        )
    _, network_client = _clients()
    attached_nsg_id = _require_attached_nsg(network_client, nsg_id)
    rules = network_client.list_network_security_group_security_rules(attached_nsg_id).data
    managed_ids = select_managed_rule_ids(rules)
    if not managed_ids:
        return {
            "success": True,
            "changed": False,
            "nsg_id": attached_nsg_id,
            "message": "no MCP-managed rules were present",
        }

    details = oci.core.models.RemoveNetworkSecurityGroupSecurityRulesDetails(
        security_rule_ids=list(managed_ids)
    )
    network_client.remove_network_security_group_security_rules(
        attached_nsg_id,
        details,
    )
    return {
        "success": True,
        "changed": True,
        "nsg_id": attached_nsg_id,
        "removed_rule_ids": list(managed_ids),
    }


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host=MCP_HOST,
        port=MCP_PORT,
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
    )
