"""Read-only classifier for one previously failed Merlin browser installation.

Consumes the canonical fixed inspector's JSON receipt. It never opens a host
socket, changes a service, removes a file or grants permission to do so.
The output is a candidate for a separately authorized host-locked reinspection,
not a reconciliation or deployment certificate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SCHEMA = "merlin-browser-state-inspection/1"
OPERATION = "inspect-state-44956695079"
SOCKET = "/run/merlin-public-browser/browser.sock"
EXPECTED_PATHS = (
    "/var/lib/merlin-browser-bootstrap/3eadad53-ba62-4a35-9578-eebe65420f76",
    "/var/lib/merlin-browser-bootstrap/ledger-successor-from-18106dfc-0a56-4b68-9d30-5d334d7d6a69.json",
    "/opt/merlin-public-browser/releases/ebdca90a42bbb243ac04872bdf3f1210ea20583cce9b4c34c7867af1873cb959",
    "/opt/merlin-public-browser/current",
    SOCKET,
    "/var/lib/merlin-public-browser/episodes/recovered-arxiv-18106dfc-0a56-4b68-9d30-5d334d7d6a69",
)
MAX_RECEIPT_BYTES = 256 * 1024


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate field in inspection JSON")
        result[key] = value
    return result


def assess(receipt, *, expected_run_id, expected_workflow_commit):
    """Classify an observed snapshot; authority remains false under every result."""
    reasons = []
    def require(ok, message):
        if ok is not True:
            reasons.append(message)

    require(type(expected_run_id) is int and expected_run_id > 0, "expected run ID invalid")
    require(isinstance(expected_workflow_commit, str)
            and len(expected_workflow_commit) == 40
            and all(ch in "0123456789abcdef" for ch in expected_workflow_commit),
            "expected workflow commit invalid")
    require(isinstance(receipt, dict), "inspection receipt must be an object")
    if not isinstance(receipt, dict):
        receipt = {}
    require(receipt.get("schema") == SCHEMA, "inspection schema differs")
    require(receipt.get("operation") == OPERATION, "inspection operation differs")
    require(receipt.get("complete") is True and receipt.get("status") == "inspection_complete",
            "inspection was incomplete")
    require(receipt.get("acceptance_allowed") is False
            and receipt.get("qualification") is False, "inspection authority flags differ")
    for key in ("application_mutations", "connections", "acquisitions", "model_calls"):
        require(type(receipt.get(key)) is int and receipt[key] == 0,
                "inspection side-effect counter differs: " + key)
    execution = receipt.get("execution")
    require(isinstance(execution, dict), "missing execution identity")
    if not isinstance(execution, dict):
        execution = {}
    require(execution.get("run_id") == expected_run_id
            and type(execution.get("run_id")) is int, "source run identity differs")
    require(execution.get("workflow_commit") == expected_workflow_commit,
            "workflow source identity differs")
    require(execution.get("repository") == "morganaspim/Cace-app"
            and execution.get("runner") == "cace-oci-a1"
            and execution.get("run_attempt") == 1,
            "expected runner identity differs")

    paths = receipt.get("paths")
    require(isinstance(paths, list) and len(paths) == len(EXPECTED_PATHS),
            "fixed path inventory incomplete")
    by_path = {}
    if isinstance(paths, list):
        for item in paths:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                reasons.append("path entry malformed")
                continue
            if item["path"] in by_path:
                reasons.append("duplicate path entry")
            by_path[item["path"]] = item
        require(set(by_path) == set(EXPECTED_PATHS),
                "fixed path inventory substituted")
    for path in EXPECTED_PATHS:
        item = by_path.get(path)
        if not isinstance(item, dict):
            reasons.append("fixed path missing: " + path)
            continue
        require(item.get("follows_symlinks") is False, "symlink following not excluded: " + path)
        if path != SOCKET:
            require(item.get("status") == "absent" and item.get("exists") is False,
                    "release/ledger state not absent: " + path)
        else:
            metadata = item.get("metadata")
            require(item.get("status") == "present" and item.get("exists") is True
                    and isinstance(metadata, dict), "socket inode not observed")
            if isinstance(metadata, dict):
                require(metadata.get("type") == "socket" and metadata.get("uid") == 0
                        and metadata.get("gid") == 1000
                        and metadata.get("mode") == "0o660"
                        and type(metadata.get("inode")) is int
                        and metadata["inode"] > 0
                        and metadata.get("nlink") == 1,
                        "socket inode metadata unexpected")
    require(receipt.get("all_six_absent_snapshot") is False,
            "observed snapshot shape unexpectedly changed")

    marker = receipt.get("successor_marker")
    require(isinstance(marker, dict) and marker.get("status") == "absent"
            and marker.get("verified") is False, "successor marker is not absent")
    supervisor = receipt.get("supervisor")
    require(isinstance(supervisor, dict) and supervisor.get("status") == "observed",
            "service observation unavailable")
    if not isinstance(supervisor, dict):
        supervisor = {}
    properties = supervisor.get("properties")
    require(isinstance(properties, dict), "service properties unavailable")
    if isinstance(properties, dict):
        require(properties.get("ActiveState") == "inactive"
                and properties.get("SubState") == "dead"
                and properties.get("UnitFileState") == "disabled"
                and properties.get("MainPID") == "0"
                and properties.get("User") == "root",
                "service appears active or changed")
    sockets = receipt.get("unix_socket_table")
    require(isinstance(sockets, dict) and sockets.get("status") == "observed"
            and sockets.get("matching_path") == SOCKET
            and sockets.get("matches") == 0
            and sockets.get("rows") == [],
            "socket has a listener or table observation is incomplete")

    return {
        "schema": "merlin-browser-reconciliation-preflight/1",
        "status": "candidate_for_separate_locked_reinspection" if not reasons else "blocked",
        "reasons": sorted(set(reasons)),
        "source_run_id": expected_run_id,
        "source_workflow_commit": expected_workflow_commit,
        "authority_granted": False,
        "may_unlink_socket": False,
        "host_mutations": 0,
        "native_browser_qualified": False,
        "next_gate": (
            "Independent authorized root-side recheck of the exact socket inode,"
            " service state, active Unix listeners, and prior ledger under operation.lock;"
            " only then propose one bounded recovery action with rollback"
        ),
    }


def from_json_bytes(raw, *, expected_run_id, expected_workflow_commit):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_RECEIPT_BYTES:
        raise ValueError("inspection JSON size outside bounded range")
    receipt = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_keys)
    result = assess(receipt, expected_run_id=expected_run_id,
                    expected_workflow_commit=expected_workflow_commit)
    result["source_receipt_sha256"] = hashlib.sha256(raw).hexdigest()
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only browser reconciliation preflight")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-run-id", type=int, required=True)
    parser.add_argument("--expected-workflow-commit", required=True)
    args = parser.parse_args(argv)
    if args.input.is_symlink() or not args.input.is_file():
        parser.error("input must be a regular file, not a symlink")
    with args.input.open("rb") as stream:
        raw = stream.read(MAX_RECEIPT_BYTES + 1)
    output = from_json_bytes(raw, expected_run_id=args.expected_run_id,
                             expected_workflow_commit=args.expected_workflow_commit)
    # The caller owns the destination. This does not operate on root/browser paths.
    args.output.write_text(json.dumps(output, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": output["status"], "reason_count": len(output["reasons"]),
                      "authority_granted": False}, sort_keys=True))
    return 0 if output["status"] != "blocked" else 2


if __name__ == "__main__":
    raise SystemExit(main())
