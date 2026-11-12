from __future__ import annotations

import json
from typing import Any
from urllib.request import Request, urlopen

MCP_ENDPOINT = "http://127.0.0.1:8765/mcp"
MCP_PROTOCOL_VERSION = "2025-03-26"
MAX_RESPONSE_BYTES = 1024 * 1024

READ_ONLY_TOOLS = (
    "get_control_capabilities",
    "get_cace_runtime_status",
    "get_github_runner_status",
)


def _decode_message(body: bytes, content_type: str) -> dict[str, Any]:
    if len(body) > MAX_RESPONSE_BYTES:
        raise RuntimeError("MCP response exceeded the 1 MiB limit")
    text = body.decode("utf-8", errors="strict")
    if "text/event-stream" not in content_type:
        message = json.loads(text)
        if not isinstance(message, dict):
            raise RuntimeError("MCP response was not a JSON-RPC object")
        return message

    blocks: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        if line.startswith("data:"):
            current.append(line[5:].lstrip())
        elif not line and current:
            blocks.append("\n".join(current))
            current = []
    if current:
        blocks.append("\n".join(current))
    messages = [json.loads(block) for block in blocks if block and block != "[DONE]"]
    if not messages or not isinstance(messages[-1], dict):
        raise RuntimeError("MCP SSE response contained no JSON-RPC object")
    return messages[-1]


def probe_local_mcp() -> dict[str, Any]:
    """Initialize the loopback MCP service and call only fixed read-only tools."""
    session_id: str | None = None
    protocol_version = MCP_PROTOCOL_VERSION

    def rpc(method: str, request_id: int | None, params: dict[str, Any] | None = None) -> dict[str, Any]:
        nonlocal session_id
        payload: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if request_id is not None:
            payload["id"] = request_id
        if params is not None:
            payload["params"] = params
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": protocol_version,
        }
        if session_id:
            headers["Mcp-Session-Id"] = session_id
        request = Request(
            MCP_ENDPOINT,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=8) as response:
                body = response.read(MAX_RESPONSE_BYTES + 1)
                content_type = response.headers.get("Content-Type", "")
                session_id = response.headers.get("Mcp-Session-Id", session_id)
        except Exception as exc:
            raise RuntimeError(f"MCP HTTP request failed: {type(exc).__name__}") from None
        if not body:
            return {}
        message = _decode_message(body, content_type)
        if message.get("error"):
            raise RuntimeError("MCP JSON-RPC returned an error")
        return message

    initialized = rpc(
        "initialize",
        1,
        {
            "protocolVersion": protocol_version,
            "capabilities": {},
            "clientInfo": {"name": "merlin-oci-health-probe", "version": "1.0.0"},
        },
    )
    initialize_result = initialized.get("result") or {}
    negotiated_version = initialize_result.get("protocolVersion")
    if not isinstance(negotiated_version, str) or not negotiated_version:
        raise RuntimeError("MCP initialize response omitted protocolVersion")
    protocol_version = negotiated_version

    rpc("notifications/initialized", None)
    listed = rpc("tools/list", 2, {})
    tools = (listed.get("result") or {}).get("tools") or []
    tool_names = sorted(
        tool["name"]
        for tool in tools
        if isinstance(tool, dict) and isinstance(tool.get("name"), str)
    )

    tool_results: dict[str, dict[str, Any]] = {}
    for request_id, tool_name in enumerate(READ_ONLY_TOOLS, start=3):
        if tool_name not in tool_names:
            tool_results[tool_name] = {"available": False}
            continue
        response = rpc(
            "tools/call",
            request_id,
            {"name": tool_name, "arguments": {}},
        )
        result = response.get("result") or {}
        tool_results[tool_name] = {
            "available": True,
            "is_error": bool(result.get("isError", False)),
            "structured_content": result.get("structuredContent"),
            "content": result.get("content", []),
        }

    required_tools_ok = all(
        tool_results.get(name, {}).get("available") and not tool_results.get(name, {}).get("is_error")
        for name in ("get_control_capabilities", "get_cace_runtime_status")
    )
    return {
        "status": "succeeded" if required_tools_ok else "partial",
        "endpoint": MCP_ENDPOINT,
        "protocol_version": protocol_version,
        "server_info": initialize_result.get("serverInfo"),
        "tool_names": tool_names,
        "read_only_tool_results": tool_results,
    }
