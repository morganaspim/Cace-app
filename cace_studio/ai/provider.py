from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import ipaddress
from typing import Mapping, Sequence
from urllib.parse import unquote, urlsplit, urlunsplit

from .capability_gate import AICapabilityManifest, CapabilityTier


class LocalAIError(RuntimeError):
    """Raised when an optional local-AI provider cannot complete a request."""


@dataclass(frozen=True)
class ProviderHealth:
    provider_id: str
    name: str
    endpoint: str
    healthy: bool
    models: tuple[str, ...] = ()
    detail: str = ""


def _validate_local_path(path: str) -> str:
    """Reject path encodings that could alter authority or escape the local origin."""

    if not path or path == "/":
        return ""
    if not path.startswith("/"):
        raise LocalAIError("local AI endpoint path must be absolute")
    if "\\" in path:
        raise LocalAIError("local AI endpoint path must not contain backslashes")
    for segment in path.split("/"):
        decoded = segment
        for _ in range(2):
            decoded = unquote(decoded)
            if decoded in {".", ".."} or "/" in decoded or "\\" in decoded:
                raise LocalAIError("local AI endpoint path contains unsafe traversal or separators")
            if any(ord(char) < 32 or ord(char) == 127 for char in decoded):
                raise LocalAIError("local AI endpoint path contains control characters")
    return path.rstrip("/")


def validate_local_endpoint(endpoint: str) -> str:
    """Validate and normalize a loopback-only local AI HTTP(S) endpoint.

    The local-AI feature is deliberately unable to contact arbitrary network
    hosts. Only the exact special-use hostname ``localhost`` or a literal
    loopback IP address is accepted. Credentials, query strings, fragments and
    ambiguous path encodings are rejected fail-closed.
    """

    candidate = endpoint.strip()
    if not candidate:
        raise LocalAIError("local AI endpoint cannot be empty")
    if "\\" in candidate or any(ord(char) < 32 or ord(char) == 127 for char in candidate):
        raise LocalAIError("local AI endpoint contains unsafe characters")

    parsed = urlsplit(candidate)
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        raise LocalAIError("local AI endpoint must use http or https")
    if not parsed.netloc or parsed.hostname is None:
        raise LocalAIError("local AI endpoint must include a host")
    if parsed.username is not None or parsed.password is not None:
        raise LocalAIError("local AI endpoint must not contain credentials")
    if parsed.query or parsed.fragment:
        raise LocalAIError("local AI endpoint must not contain a query string or fragment")

    try:
        port = parsed.port
    except ValueError as exc:
        raise LocalAIError("local AI endpoint contains an invalid port") from exc

    hostname = parsed.hostname
    if hostname.lower() == "localhost":
        normalized_host = "localhost"
    else:
        try:
            address = ipaddress.ip_address(hostname)
        except ValueError as exc:
            raise LocalAIError(
                "local AI endpoint host must be localhost or a literal loopback IP address"
            ) from exc
        if not address.is_loopback:
            raise LocalAIError("local AI endpoint IP address must be loopback")
        normalized_host = (
            f"[{address.compressed}]" if address.version == 6 else address.compressed
        )

    path = _validate_local_path(parsed.path)
    netloc = normalized_host + (f":{port}" if port is not None else "")
    return urlunsplit((scheme, netloc, path, "", ""))


class AIProvider(ABC):
    """Narrow assistant-only provider interface.

    Implementations must not mutate CACE verification records, certificates,
    claim status, or proof-ledger state.
    """

    provider_id: str
    display_name: str

    def __init__(self, endpoint: str, model: str = "", timeout: float = 30.0) -> None:
        self.endpoint = validate_local_endpoint(endpoint)
        self.model = model
        self.timeout = timeout

    def capability_manifest(self) -> AICapabilityManifest:
        """Declared provider capabilities used by CACE admission policy."""
        return AICapabilityManifest(
            provider_id=self.provider_id,
            model_id=self.model,
            tier=CapabilityTier.BOUNDED,
            requested_compute_credits=0.0,
            hidden_layers_exposed=False,
        )

    @abstractmethod
    def health(self) -> ProviderHealth:
        raise NotImplementedError

    @abstractmethod
    def list_models(self) -> tuple[str, ...]:
        raise NotImplementedError

    @abstractmethod
    def chat(self, messages: Sequence[Mapping[str, str]], *, temperature: float = 0.2) -> str:
        raise NotImplementedError
