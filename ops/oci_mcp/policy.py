from __future__ import annotations

from dataclasses import dataclass
from ipaddress import ip_network
from typing import Iterable

MANAGED_RULE_PREFIX = "CACE-MCP-MANAGED"
ALLOWED_WEB_PORTS = frozenset({80, 443})
MAX_LOG_LINES = 200


@dataclass(frozen=True)
class ManagedIngressRequest:
    source_cidr: str
    port: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_cidr", validate_source_cidr(self.source_cidr))
        object.__setattr__(self, "port", validate_web_port(self.port))

    @property
    def description(self) -> str:
        return f"{MANAGED_RULE_PREFIX} tcp/{self.port} from {self.source_cidr}"


def validate_source_cidr(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("source_cidr must be a non-empty CIDR string")
    try:
        network = ip_network(value.strip(), strict=True)
    except ValueError as exc:
        raise ValueError("source_cidr must be a canonical CIDR network") from exc
    return str(network)


def validate_web_port(value: int) -> int:
    try:
        port = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("port must be 80 or 443") from exc
    if port not in ALLOWED_WEB_PORTS:
        raise ValueError("only TCP ports 80 and 443 are allowed")
    return port


def validate_log_lines(value: int) -> int:
    try:
        lines = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("lines must be an integer") from exc
    if not 1 <= lines <= MAX_LOG_LINES:
        raise ValueError(f"lines must be between 1 and {MAX_LOG_LINES}")
    return lines


def is_managed_rule_description(description: str | None) -> bool:
    return isinstance(description, str) and description.startswith(MANAGED_RULE_PREFIX)


def select_managed_rule_ids(rules: Iterable[object]) -> tuple[str, ...]:
    selected: list[str] = []
    for rule in rules:
        description = getattr(rule, "description", None)
        rule_id = getattr(rule, "id", None)
        if is_managed_rule_description(description) and isinstance(rule_id, str) and rule_id:
            selected.append(rule_id)
    return tuple(sorted(set(selected)))


def require_merlin_rsi_signing(enabled: bool) -> None:
    """Fail closed unless the operator explicitly enabled persistent RSI signing."""
    if enabled is not True:
        raise PermissionError(
            "Merlin RSI signing is disabled; review persistent key custody before enabling it"
        )
