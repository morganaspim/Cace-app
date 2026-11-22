"""Fail-closed reference check for one model-selected local file-read episode.

No inference, filesystem access, or network calls here. The controller supplies
unpredictable fixture identity and inspects *actual* Studio event records.
"""
from __future__ import annotations
import hashlib
import re

ID32 = re.compile(r"[0-9a-f]{32}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class ToolEvidenceError(ValueError):
    pass


def require(ok, detail):
    if not ok:
        raise ToolEvidenceError(detail)


def assess(events, *, expected_path, fixture_sha256, marker, answer):
    require(isinstance(events, list) and 3 <= len(events) <= 100, "bounded real events required")
    require(isinstance(expected_path, str) and 0 < len(expected_path) <= 80
            and re.fullmatch(r"[A-Za-z0-9_.-]+", expected_path) is not None,
            "fixture path must be a basename")
    require(isinstance(fixture_sha256, str) and HEX64.fullmatch(fixture_sha256),
            "exact fixture SHA256 required")
    require(isinstance(marker, str) and re.fullmatch(r"MERLIN_TOOL_[0-9a-f]{32}", marker),
            "unpredictable reference marker shape invalid")
    require(isinstance(answer, str) and answer.count(marker) == 1,
            "model final message did not reproduce file-only marker exactly once")
    for event in events:
        require(isinstance(event, dict) and isinstance(event.get("type"), str),
                "malformed Studio event")
    request_indexes = [i for i, event in enumerate(events) if event["type"] == "model_request"]
    require(2 <= len(request_indexes) <= 3, "model must choose tools and then answer in bounded steps")
    forbidden = {"tool_error", "tool_denied", "interrupted"}
    require(not any(event["type"] in forbidden for event in events),
            "tool failed, denied, or was interrupted")
    started = [(i, event) for i, event in enumerate(events) if event["type"] == "tool_started"]
    results = [(i, event) for i, event in enumerate(events) if event["type"] == "tool_result"]
    require(1 <= len(started) <= 2 and len(started) == len(results),
            "one or two real tool executions and matching results required")
    allowed = {"list_files", "read_file"}
    require(all(event.get("tool") in allowed for _, event in started + results),
            "unsafe or unrequested model-selected tool observed")
    for (start_i, start), (result_i, result) in zip(started, results):
        require(start_i < result_i and start.get("tool") == result.get("tool"),
                "tool start/result event ordering or name changed")
    reads = [(i, event) for i, event in started if event.get("tool") == "read_file"]
    read_results = [(i, event) for i, event in results if event.get("tool") == "read_file"]
    require(len(reads) == 1 and len(read_results) == 1,
            "one successful model-selected read_file invocation required")
    read_i, started_read = reads[0]
    return_i, finished_read = read_results[0]
    require(started_read.get("arguments") == {"path": expected_path},
            "model read an unexpected path")
    payload = finished_read.get("result")
    require(isinstance(payload, dict) and
            payload.get("sha256") == fixture_sha256 and
            payload.get("path") == expected_path and
            isinstance(payload.get("content"), str),
            "tool result did not match the fixture bytes and path")
    require(hashlib.sha256(payload["content"].encode("utf-8")).hexdigest() == fixture_sha256,
            "tool result content digest inconsistent with fixture")
    require(payload["content"].count(marker) == 1,
            "actual tool result did not contain the single file-only marker")
    require(request_indexes[0] < read_i < return_i < request_indexes[-1],
            "tool evidence must precede a later model answer request")
    require(len([event for event in events if event["type"] == "tool_started"
                 and event.get("tool") == "list_files"]) <= 1,
            "unexpected repeated directory listing")
    return {"model_request_events": len(request_indexes),
            "tool_started_events": len(started),
            "verified_read_file": True,
            "unsafe_tools_selected": 0,
            "fixture_sha256": fixture_sha256,
            "marker_sha256": hashlib.sha256(marker.encode()).hexdigest()}


if __name__ == "__main__":
    raise SystemExit("Import this reference checker; it is not a standalone model test.")
