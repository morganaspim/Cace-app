from __future__ import annotations

from typing import Callable

from cace_studio.core.reproducibility import sha256_identity

from .contracts import (
    Capability,
    CapabilityPolicy,
    ToolAuditRecord,
    ToolCall,
    ToolContext,
    ToolDescriptor,
    ToolResult,
    ToolStatus,
    ToolValidationError,
    TypedTool,
    dataclass_schema,
    decode_dataclass,
    to_plain,
)

ApprovalCallback = Callable[[ToolCall, ToolDescriptor], bool]


class ToolBus:
    """Typed, capability-scoped execution boundary for local agents.

    The bus is deliberately outside CACE's proof/evidence authority. A successful
    tool call can report observations or execute existing canonical operations,
    but it cannot itself create PASS/FORMAL status or promote proof-ledger state.
    """

    def __init__(
        self,
        *,
        policy: CapabilityPolicy | None = None,
        approval_callback: ApprovalCallback | None = None,
    ) -> None:
        self.policy = policy or CapabilityPolicy.zero_contact()
        self.approval_callback = approval_callback
        self._tools: dict[str, TypedTool] = {}
        self._audit: list[ToolAuditRecord] = []
        self._sequence = 0

    def register(self, tool: TypedTool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"duplicate tool name: {tool.name}")
        self._tools[tool.name] = tool

    def contains(self, name: str) -> bool:
        return name in self._tools

    def descriptor(self, name: str) -> ToolDescriptor:
        try:
            tool = self._tools[name]
        except KeyError as exc:
            raise KeyError(f"unknown tool: {name}") from exc
        decision = self.policy.decision(tool.capability)
        return ToolDescriptor(
            name=tool.name,
            description=tool.description,
            capability=tool.capability,
            request_schema=dataclass_schema(tool.request_type),
            response_schema=dataclass_schema(tool.response_type),
            requires_approval=decision == "approval",
        )

    def descriptors(self, *, include_denied: bool = False) -> tuple[ToolDescriptor, ...]:
        items = []
        for name in sorted(self._tools):
            tool = self._tools[name]
            decision = self.policy.decision(tool.capability)
            if decision == "deny" and not include_denied:
                continue
            items.append(self.descriptor(name))
        return tuple(items)

    @property
    def audit_records(self) -> tuple[ToolAuditRecord, ...]:
        return tuple(self._audit)

    def _record(
        self,
        *,
        call: ToolCall,
        tool: TypedTool,
        status: ToolStatus,
        approved: bool,
        input_sha256: str,
        output_sha256: str | None,
        error: str,
    ) -> ToolResult:
        record = ToolAuditRecord(
            sequence=self._sequence,
            call_id=call.call_id,
            tool_name=tool.name,
            capability=tool.capability,
            status=status,
            approved=approved,
            input_sha256=input_sha256,
            output_sha256=output_sha256,
            error=error,
        )
        self._audit.append(record)
        return ToolResult(
            call_id=call.call_id,
            tool_name=tool.name,
            status=status,
            output=None,
            error=error,
        )

    def invoke(self, call: ToolCall) -> ToolResult:
        self._sequence += 1

        tool = self._tools.get(call.tool_name)
        if tool is None:
            try:
                input_sha256 = sha256_identity(dict(call.arguments))
            except (TypeError, ValueError):
                input_sha256 = sha256_identity({"invalid_request": "non-canonical arguments"})
            self._audit.append(
                ToolAuditRecord(
                    sequence=self._sequence,
                    call_id=call.call_id,
                    tool_name=call.tool_name,
                    capability=Capability.UNKNOWN,
                    status=ToolStatus.DENIED,
                    approved=False,
                    input_sha256=input_sha256,
                    output_sha256=None,
                    error="unknown or unavailable tool",
                )
            )
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                status=ToolStatus.DENIED,
                error="unknown or unavailable tool",
            )

        try:
            input_sha256 = sha256_identity(dict(call.arguments))
        except (TypeError, ValueError) as exc:
            input_sha256 = sha256_identity({"invalid_request": "non-canonical arguments"})
            return self._record(
                call=call,
                tool=tool,
                status=ToolStatus.INVALID_REQUEST,
                approved=False,
                input_sha256=input_sha256,
                output_sha256=None,
                error=f"request is not canonical JSON-compatible data: {exc}",
            )

        decision = self.policy.decision(tool.capability)
        approved = decision == "allow"

        if decision == "deny":
            return self._record(
                call=call,
                tool=tool,
                status=ToolStatus.DENIED,
                approved=False,
                input_sha256=input_sha256,
                output_sha256=None,
                error=f"capability denied: {tool.capability.value}",
            )

        if decision == "approval":
            if self.approval_callback is None:
                return self._record(
                    call=call,
                    tool=tool,
                    status=ToolStatus.DENIED,
                    approved=False,
                    input_sha256=input_sha256,
                    output_sha256=None,
                    error=f"human approval required: {tool.capability.value}",
                )
            descriptor = self.descriptor(tool.name)
            try:
                approved = bool(self.approval_callback(call, descriptor))
            except Exception as exc:
                return self._record(
                    call=call,
                    tool=tool,
                    status=ToolStatus.ERROR,
                    approved=False,
                    input_sha256=input_sha256,
                    output_sha256=None,
                    error=f"approval callback failed: {type(exc).__name__}: {exc}",
                )
            if not approved:
                return self._record(
                    call=call,
                    tool=tool,
                    status=ToolStatus.DENIED,
                    approved=False,
                    input_sha256=input_sha256,
                    output_sha256=None,
                    error=f"human approval denied: {tool.capability.value}",
                )

        try:
            request = decode_dataclass(tool.request_type, call.arguments)
        except ToolValidationError as exc:
            return self._record(
                call=call,
                tool=tool,
                status=ToolStatus.INVALID_REQUEST,
                approved=approved,
                input_sha256=input_sha256,
                output_sha256=None,
                error=str(exc),
            )

        context = ToolContext(
            sequence=self._sequence,
            call_id=call.call_id,
            tool_name=tool.name,
            capability=tool.capability,
        )
        try:
            response = tool.handler(request, context)
        except Exception as exc:
            return self._record(
                call=call,
                tool=tool,
                status=ToolStatus.ERROR,
                approved=approved,
                input_sha256=input_sha256,
                output_sha256=None,
                error=f"{type(exc).__name__}: {exc}",
            )

        if not isinstance(response, tool.response_type):
            return self._record(
                call=call,
                tool=tool,
                status=ToolStatus.INVALID_RESPONSE,
                approved=approved,
                input_sha256=input_sha256,
                output_sha256=None,
                error=(
                    f"handler returned {type(response).__name__}; "
                    f"expected {tool.response_type.__name__}"
                ),
            )

        try:
            output = to_plain(response)
            if not isinstance(output, dict):
                raise TypeError("dataclass response did not encode to an object")
            output_sha256 = sha256_identity(output)
        except (TypeError, ValueError) as exc:
            return self._record(
                call=call,
                tool=tool,
                status=ToolStatus.INVALID_RESPONSE,
                approved=approved,
                input_sha256=input_sha256,
                output_sha256=None,
                error=f"response is not a canonical tool payload: {exc}",
            )

        self._audit.append(
            ToolAuditRecord(
                sequence=self._sequence,
                call_id=call.call_id,
                tool_name=tool.name,
                capability=tool.capability,
                status=ToolStatus.OK,
                approved=approved,
                input_sha256=input_sha256,
                output_sha256=output_sha256,
                error="",
            )
        )
        return ToolResult(
            call_id=call.call_id,
            tool_name=tool.name,
            status=ToolStatus.OK,
            output=output,
            error="",
        )
