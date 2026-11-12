from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from ops.oci_mcp.policy import (
    MANAGED_RULE_PREFIX,
    ManagedIngressRequest,
    is_managed_rule_description,
    select_managed_rule_ids,
    validate_log_lines,
    validate_source_cidr,
    validate_web_port,
)


def test_web_ingress_policy_is_fail_closed():
    assert validate_web_port(80) == 80
    assert validate_web_port(443) == 443
    for port in (22, 8000, 8765, 0, 65535):
        with pytest.raises(ValueError):
            validate_web_port(port)


def test_source_cidr_requires_canonical_network():
    assert validate_source_cidr("0.0.0.0/0") == "0.0.0.0/0"
    assert validate_source_cidr("203.0.113.0/24") == "203.0.113.0/24"
    with pytest.raises(ValueError):
        validate_source_cidr("203.0.113.4/24")
    with pytest.raises(ValueError):
        validate_source_cidr("not-a-cidr")


def test_managed_rules_are_identifiable_and_removal_is_scoped():
    request = ManagedIngressRequest("203.0.113.0/24", 443)
    assert request.description.startswith(MANAGED_RULE_PREFIX)
    assert is_managed_rule_description(request.description)
    assert not is_managed_rule_description("manual admin rule")

    rules = [
        SimpleNamespace(id="a", description=request.description),
        SimpleNamespace(id="b", description="manual admin rule"),
        SimpleNamespace(id="c", description=f"{MANAGED_RULE_PREFIX} tcp/80 from 0.0.0.0/0"),
    ]
    assert select_managed_rule_ids(rules) == ("a", "c")


def test_log_read_bound_is_small():
    assert validate_log_lines(1) == 1
    assert validate_log_lines(200) == 200
    for count in (0, 201, 10_000):
        with pytest.raises(ValueError):
            validate_log_lines(count)


def test_server_and_service_do_not_enable_broad_control_by_default():
    server = Path("ops/oci_mcp/server.py").read_text(encoding="utf-8")
    service = Path("ops/oci_mcp/cace-oci-mcp.service").read_text(encoding="utf-8")
    sudoers = Path("ops/oci_mcp/cace-oci-mcp.sudoers").read_text(encoding="utf-8")

    assert "CACE_OCI_MCP_ALLOW_SERVICE_RESTART=false" in service
    assert "CACE_OCI_MCP_ALLOW_NETWORK_WRITE=false" in service
    assert "CACE_OCI_MCP_HOST=127.0.0.1" in service
    assert "terminate_instance" not in server
    assert "delete_network_security_group" not in server
    assert "shell=True" not in server

    lines = [
        line.strip()
        for line in sudoers.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert lines == [
        "cace-mcp ALL=(root) NOPASSWD: /usr/bin/systemctl restart cace-web"
    ]


def test_merlin_rsi_signing_is_fail_closed_and_all_signing_tools_use_gate():
    from ops.oci_mcp.policy import require_merlin_rsi_signing

    with pytest.raises(PermissionError):
        require_merlin_rsi_signing(False)
    require_merlin_rsi_signing(True)

    import ast
    server = ast.parse(Path("ops/oci_mcp/server.py").read_text(encoding="utf-8"))
    functions = {
        node.name: node for node in ast.walk(server)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    for name in (
        "initialize_merlin_rsi_attestor",
        "attest_merlin_rsi_reproduction",
        "attest_merlin_rsi_bundle",
    ):
        calls = [
            node for node in ast.walk(functions[name])
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "require_merlin_rsi_signing"
        ]
        assert len(calls) == 1, f"{name} must enforce the explicit signing gate"
