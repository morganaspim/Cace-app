from __future__ import annotations

from dataclasses import MISSING, dataclass, fields, is_dataclass
from enum import Enum
from collections.abc import Mapping as ABCMapping
import types
from typing import Any, Callable, Generic, Literal, Mapping, Protocol, TypeVar, Union, get_args, get_origin, get_type_hints


class Capability(str, Enum):
    UNKNOWN = "unknown"
    READ_CATALOG = "read_catalog"
    READ_RUNTIME = "read_runtime"
    READ_EXPERIMENT = "read_experiment"
    RUN_SCIENCE = "run_science"
    RUN_CHECKER = "run_checker"
    CANVAS_MUTATE = "canvas_mutate"
    WORKSPACE_WRITE = "workspace_write"
    TOOL_PROPOSE = "tool_propose"
    NETWORK = "network"
    SHELL = "shell"
    PACKAGE_INSTALL = "package_install"
    SELF_MODIFY = "self_modify"
    PROOF_WRITE = "proof_write"
    CLAIM_PROMOTION = "claim_promotion"
    SECRET_ACCESS = "secret_access"
    WALLET_KEY_ACCESS = "wallet_key_access"


ZERO_CONTACT_HARD_DENY = frozenset(
    {
        Capability.NETWORK,
        Capability.SHELL,
        Capability.PACKAGE_INSTALL,
        Capability.SELF_MODIFY,
        Capability.PROOF_WRITE,
        Capability.CLAIM_PROMOTION,
        Capability.SECRET_ACCESS,
        Capability.WALLET_KEY_ACCESS,
    }
)


@dataclass(frozen=True)
class CapabilityPolicy:
    """Fail-closed capability policy for one Tool Bus instance.

    ``denied`` always wins. Approval-required capabilities are unavailable when
    no approval callback is installed.
    """

    allowed: frozenset[Capability]
    approval_required: frozenset[Capability] = frozenset()
    denied: frozenset[Capability] = frozenset()

    def __post_init__(self) -> None:
        overlap = (self.allowed & self.denied) | (self.approval_required & self.denied)
        if overlap:
            raise ValueError(f"capabilities cannot be both enabled and denied: {sorted(x.value for x in overlap)}")

    @classmethod
    def zero_contact(cls) -> "CapabilityPolicy":
        return cls(
            allowed=frozenset(
                {
                    Capability.READ_CATALOG,
                    Capability.READ_RUNTIME,
                    Capability.READ_EXPERIMENT,
                    Capability.RUN_SCIENCE,
                    Capability.RUN_CHECKER,
                }
            ),
            approval_required=frozenset(
                {
                    Capability.CANVAS_MUTATE,
                    Capability.WORKSPACE_WRITE,
                    Capability.TOOL_PROPOSE,
                }
            ),
            denied=ZERO_CONTACT_HARD_DENY,
        )

    def decision(self, capability: Capability) -> Literal["allow", "approval", "deny"]:
        if capability in self.denied:
            return "deny"
        if capability in self.approval_required:
            return "approval"
        if capability in self.allowed:
            return "allow"
        return "deny"


class ToolStatus(str, Enum):
    OK = "ok"
    DENIED = "denied"
    INVALID_REQUEST = "invalid_request"
    INVALID_RESPONSE = "invalid_response"
    ERROR = "error"
    RECOVERY_BLOCKED = "recovery_blocked"


@dataclass(frozen=True)
class ToolCall:
    call_id: str
    tool_name: str
    arguments: Mapping[str, Any]
    run_id: str = ""
    operation_id: str | None = None
    lease_id: str = ""
    lease_generation: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.call_id, str) or not self.call_id.strip():
            raise ValueError("tool call_id must be a non-empty string")
        if not isinstance(self.tool_name, str) or not self.tool_name.strip():
            raise ValueError("tool name must be a non-empty string")
        if not isinstance(self.arguments, Mapping):
            raise TypeError("tool arguments must be a mapping")
        if not isinstance(self.run_id, str):
            raise TypeError("tool run_id must be a string")
        if self.operation_id is not None:
            if not isinstance(self.operation_id, str) or not self.operation_id:
                raise ValueError("tool operation_id must be non-empty when supplied")
            if len(self.operation_id) > 128 or any(
                ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
                for ch in self.operation_id
            ):
                raise ValueError("tool operation_id contains unsupported characters")
        if not isinstance(self.lease_id, str):
            raise TypeError("tool lease_id must be a string")
        if (
            not isinstance(self.lease_generation, int)
            or isinstance(self.lease_generation, bool)
            or self.lease_generation < 0
        ):
            raise ValueError("tool lease_generation must be a non-negative integer")


@dataclass(frozen=True)
class ToolDescriptor:
    name: str
    description: str
    capability: Capability
    request_schema: Mapping[str, Any]
    response_schema: Mapping[str, Any]
    requires_approval: bool
    idempotency_required: bool = False
    proof_effect: str = "none"
    promotion_authority: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "capability": self.capability.value,
            "request_schema": dict(self.request_schema),
            "response_schema": dict(self.response_schema),
            "requires_approval": self.requires_approval,
            "idempotency_required": self.idempotency_required,
            "proof_effect": self.proof_effect,
            "promotion_authority": self.promotion_authority,
        }


@dataclass(frozen=True)
class ToolResult:
    call_id: str
    tool_name: str
    status: ToolStatus
    output: Mapping[str, Any] | None = None
    error: str = ""
    proof_effect: str = "none"
    promotion_authority: bool = False

    @property
    def ok(self) -> bool:
        return self.status is ToolStatus.OK

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_result_schema": 1,
            "call_id": self.call_id,
            "tool_name": self.tool_name,
            "status": self.status.value,
            "output": dict(self.output) if self.output is not None else None,
            "error": self.error,
            "proof_effect": self.proof_effect,
            "promotion_authority": self.promotion_authority,
        }


@dataclass(frozen=True)
class ToolAuditRecord:
    sequence: int
    call_id: str
    tool_name: str
    capability: Capability
    status: ToolStatus
    approved: bool
    input_sha256: str
    output_sha256: str | None
    error: str
    proof_effect: str = "none"
    promotion_authority: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_audit_schema": 1,
            "sequence": self.sequence,
            "call_id": self.call_id,
            "tool_name": self.tool_name,
            "capability": self.capability.value,
            "status": self.status.value,
            "approved": self.approved,
            "input_sha256": self.input_sha256,
            "output_sha256": self.output_sha256,
            "error": self.error,
            "proof_effect": self.proof_effect,
            "promotion_authority": self.promotion_authority,
        }


@dataclass(frozen=True)
class ToolContext:
    sequence: int
    call_id: str
    tool_name: str
    capability: Capability
    run_id: str = ""
    operation_id: str | None = None
    lease_id: str = ""
    lease_generation: int = 0


RequestT = TypeVar("RequestT")
ResponseT = TypeVar("ResponseT")


class ToolHandler(Protocol[RequestT, ResponseT]):
    def __call__(self, request: RequestT, context: ToolContext) -> ResponseT:
        ...


@dataclass(frozen=True)
class TypedTool(Generic[RequestT, ResponseT]):
    name: str
    description: str
    capability: Capability
    request_type: type[RequestT]
    response_type: type[ResponseT]
    handler: ToolHandler[RequestT, ResponseT]
    idempotency_required: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("tool name must be non-empty")
        if self.name != self.name.strip() or self.name.lower() != self.name:
            raise ValueError("tool name must be lowercase canonical text")
        if any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789._-" for ch in self.name):
            raise ValueError("tool name contains unsupported characters")
        if not self.description.strip():
            raise ValueError("tool description must be non-empty")
        if not isinstance(self.capability, Capability):
            raise TypeError("tool capability must be a Capability")
        if not is_dataclass(self.request_type) or not isinstance(self.request_type, type):
            raise TypeError("tool request_type must be a dataclass type")
        if not is_dataclass(self.response_type) or not isinstance(self.response_type, type):
            raise TypeError("tool response_type must be a dataclass type")
        if not callable(self.handler):
            raise TypeError("tool handler must be callable")
        if not isinstance(self.idempotency_required, bool):
            raise TypeError("tool idempotency_required must be boolean")


class ToolValidationError(ValueError):
    pass


class ToolPreconditionError(ValueError):
    """Safe fail-closed rejection raised before a tool performs side effects."""

    pass


def _annotation_name(annotation: Any) -> str:
    origin = get_origin(annotation)
    args = get_args(annotation)
    if annotation is Any:
        return "any"
    if origin in (Union, types.UnionType):
        return " | ".join(_annotation_name(arg) for arg in args)
    if origin is Literal:
        return "literal[" + ",".join(repr(arg) for arg in args) + "]"
    if origin is list:
        return f"list[{_annotation_name(args[0]) if args else 'any'}]"
    if origin is tuple:
        if len(args) == 2 and args[1] is Ellipsis:
            return f"tuple[{_annotation_name(args[0])}, ...]"
        return "tuple[" + ",".join(_annotation_name(arg) for arg in args) + "]"
    if origin in (dict, ABCMapping):
        key = _annotation_name(args[0]) if args else "any"
        value = _annotation_name(args[1]) if len(args) > 1 else "any"
        return f"mapping[{key},{value}]"
    if isinstance(annotation, type):
        return annotation.__name__
    return str(annotation)


def dataclass_schema(cls: type[Any]) -> dict[str, Any]:
    hints = get_type_hints(cls)
    properties: dict[str, Any] = {}
    required: list[str] = []
    for field in fields(cls):
        annotation = hints.get(field.name, Any)
        entry: dict[str, Any] = {"type": _annotation_name(annotation)}
        if field.default is not MISSING:
            entry["default"] = to_plain(field.default)
        elif field.default_factory is not MISSING:  # type: ignore[comparison-overlap]
            entry["default_factory"] = True
        else:
            required.append(field.name)
        properties[field.name] = entry
    return {
        "kind": "cace-python-dataclass-v1",
        "name": cls.__name__,
        "properties": properties,
        "required": required,
        "additional_properties": False,
    }


def _coerce(annotation: Any, value: Any, path: str) -> Any:
    if annotation is Any:
        return value

    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin in (Union, types.UnionType):
        errors = []
        for option in args:
            try:
                return _coerce(option, value, path)
            except ToolValidationError as exc:
                errors.append(str(exc))
        raise ToolValidationError(f"{path}: value does not match any allowed type")

    if origin is Literal:
        if value not in args:
            raise ToolValidationError(f"{path}: expected one of {args!r}")
        return value

    if isinstance(annotation, type) and issubclass(annotation, Enum):
        try:
            return annotation(value)
        except (ValueError, TypeError) as exc:
            raise ToolValidationError(f"{path}: invalid {annotation.__name__}") from exc

    if isinstance(annotation, type) and is_dataclass(annotation):
        if not isinstance(value, Mapping):
            raise ToolValidationError(f"{path}: expected object")
        return decode_dataclass(annotation, value, path=path)

    if origin is list:
        if not isinstance(value, list):
            raise ToolValidationError(f"{path}: expected array")
        item_type = args[0] if args else Any
        return [_coerce(item_type, item, f"{path}[{index}]") for index, item in enumerate(value)]

    if origin is tuple:
        if not isinstance(value, (list, tuple)):
            raise ToolValidationError(f"{path}: expected array")
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(_coerce(args[0], item, f"{path}[{index}]") for index, item in enumerate(value))
        if args and len(value) != len(args):
            raise ToolValidationError(f"{path}: expected {len(args)} items")
        return tuple(
            _coerce(args[index] if args else Any, item, f"{path}[{index}]")
            for index, item in enumerate(value)
        )

    if origin in (dict, ABCMapping):
        if not isinstance(value, Mapping):
            raise ToolValidationError(f"{path}: expected object")
        key_type = args[0] if args else Any
        value_type = args[1] if len(args) > 1 else Any
        out = {}
        for key, item in value.items():
            coerced_key = _coerce(key_type, key, f"{path}.<key>")
            out[coerced_key] = _coerce(value_type, item, f"{path}.{key}")
        return out

    if annotation is str:
        if not isinstance(value, str):
            raise ToolValidationError(f"{path}: expected string")
        return value
    if annotation is bool:
        if not isinstance(value, bool):
            raise ToolValidationError(f"{path}: expected boolean")
        return value
    if annotation is int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ToolValidationError(f"{path}: expected integer")
        return value
    if annotation is float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ToolValidationError(f"{path}: expected number")
        return float(value)
    if annotation is type(None):
        if value is not None:
            raise ToolValidationError(f"{path}: expected null")
        return None

    if isinstance(annotation, type):
        if not isinstance(value, annotation):
            raise ToolValidationError(f"{path}: expected {annotation.__name__}")
        return value

    return value


def decode_dataclass(cls: type[RequestT], payload: Mapping[str, Any], *, path: str = "request") -> RequestT:
    if not isinstance(payload, Mapping):
        raise ToolValidationError(f"{path}: expected object")
    allowed = {field.name for field in fields(cls)}
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise ToolValidationError(f"{path}: unknown fields {unknown}")
    hints = get_type_hints(cls)
    kwargs = {}
    for field in fields(cls):
        if field.name in payload:
            kwargs[field.name] = _coerce(hints.get(field.name, Any), payload[field.name], f"{path}.{field.name}")
        elif field.default is MISSING and field.default_factory is MISSING:  # type: ignore[comparison-overlap]
            raise ToolValidationError(f"{path}: missing required field {field.name!r}")
    try:
        return cls(**kwargs)
    except (TypeError, ValueError) as exc:
        raise ToolValidationError(f"{path}: {exc}") from exc


def to_plain(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return to_plain(value.value)
    if is_dataclass(value):
        return {field.name: to_plain(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping):
        out = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("tool output mappings require string keys")
            out[key] = to_plain(item)
        return out
    if isinstance(value, (list, tuple)):
        return [to_plain(item) for item in value]
    raise TypeError(f"unsupported tool payload type: {type(value).__name__}")
