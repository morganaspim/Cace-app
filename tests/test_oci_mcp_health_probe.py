import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from ops.oci_mcp.health_probe import (
    MCP_ENDPOINT,
    _decode_message,
    probe_local_mcp,
)


class FakeResponse:
    def __init__(self, payload=b"", headers=None):
        self.payload = payload
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, limit=-1):
        return self.payload[:limit]


def json_response(message, headers=None):
    return FakeResponse(
        json.dumps(message).encode("utf-8"),
        {"Content-Type": "application/json", **(headers or {})},
    )


def test_probe_initializes_lists_tools_and_calls_only_fixed_read_only_tools():
    responses = [
        json_response(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "protocolVersion": "2025-03-26",
                    "serverInfo": {"name": "cace-oci-mcp", "version": "1"},
                },
            },
            {"Mcp-Session-Id": "session-test"},
        ),
        FakeResponse(b"", {"Content-Type": "application/json"}),
        json_response(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "result": {
                    "tools": [
                        {"name": "get_control_capabilities"},
                        {"name": "get_cace_runtime_status"},
                        {"name": "get_github_runner_status"},
                        {"name": "arbitrary_shell"},
                    ]
                },
            }
        ),
        json_response({"jsonrpc": "2.0", "id": 3, "result": {"structuredContent": {"ok": True}, "content": []}}),
        json_response({"jsonrpc": "2.0", "id": 4, "result": {"structuredContent": {"healthy": True}, "content": []}}),
        json_response({"jsonrpc": "2.0", "id": 5, "result": {"structuredContent": {"runner": "oci"}, "content": []}}),
    ]
    requests = []

    def fake_urlopen(request, timeout):
        requests.append(request)
        assert request.full_url == MCP_ENDPOINT
        assert timeout == 8
        return responses.pop(0)

    with patch("ops.oci_mcp.health_probe.urlopen", side_effect=fake_urlopen):
        result = probe_local_mcp()

    assert result["status"] == "succeeded"
    assert result["protocol_version"] == "2025-03-26"
    assert result["server_info"]["name"] == "cace-oci-mcp"
    assert "arbitrary_shell" in result["tool_names"]
    assert set(result["read_only_tool_results"]) == {
        "get_control_capabilities",
        "get_cace_runtime_status",
        "get_github_runner_status",
    }
    assert result["read_only_tool_results"]["get_control_capabilities"]["structured_content"] == {"ok": True}
    assert len(requests) == 6
    payloads = [json.loads(request.data.decode("utf-8")) for request in requests]
    assert payloads[0]["method"] == "initialize"
    assert payloads[1]["method"] == "notifications/initialized"
    assert payloads[2]["method"] == "tools/list"
    assert [item["params"]["name"] for item in payloads[3:]] == [
        "get_control_capabilities",
        "get_cace_runtime_status",
        "get_github_runner_status",
    ]
    assert all(request.get_header("Mcp-session-id") == "session-test" for request in requests[1:])


def test_probe_reports_missing_optional_tool_without_calling_other_tools():
    responses = [
        json_response({"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2025-03-26"}}),
        FakeResponse(b"", {"Content-Type": "application/json"}),
        json_response({"jsonrpc": "2.0", "id": 2, "result": {"tools": [{"name": "get_control_capabilities"}]}}),
        json_response({"jsonrpc": "2.0", "id": 3, "result": {"content": []}}),
    ]
    requests = []

    def fake_urlopen(request, timeout):
        requests.append(request)
        return responses.pop(0)

    with patch("ops.oci_mcp.health_probe.urlopen", side_effect=fake_urlopen):
        result = probe_local_mcp()

    assert result["read_only_tool_results"]["get_github_runner_status"] == {"available": False}
    called = [json.loads(request.data.decode("utf-8")) for request in requests]
    assert [item["method"] for item in called] == [
        "initialize",
        "notifications/initialized",
        "tools/list",
        "tools/call",
    ]


def test_decode_message_supports_streamable_http_sse():
    body = b'event: message\ndata: {"jsonrpc":"2.0","id":2,"result":{"tools":[]}}\n\n'
    assert _decode_message(body, "text/event-stream") == {
        "jsonrpc": "2.0",
        "id": 2,
        "result": {"tools": []},
    }


def test_decode_message_rejects_oversized_and_non_object_responses():
    with pytest.raises(RuntimeError, match="1 MiB"):
        _decode_message(b"x" * (1024 * 1024 + 1), "application/json")
    with pytest.raises(RuntimeError, match="JSON-RPC object"):
        _decode_message(b"[]", "application/json")


def test_probe_fails_closed_when_local_service_is_unreachable():
    with patch("ops.oci_mcp.health_probe.urlopen", side_effect=OSError("private details")):
        with pytest.raises(RuntimeError, match="MCP HTTP request failed: OSError"):
            probe_local_mcp()
