#!/usr/bin/env python3
"""Validate a CACE AI rigorous-tool submission packet.

This validator checks coordination structure only. Passing does not create
scientific or formal evidence.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys

HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
SEMANTIC_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{2,159}$")
TRACKS = set("ABCDEFGHI")
PROOF_STATES = {"NOT_STARTED","DRAFT","QUARANTINED","PREFLIGHT_ONLY","QUALIFICATION_REQUIRED"}
NEXT_GATES = {"ENGINEERING_REVIEW","LEAN_DRAFT","LEAN_QUARANTINE","EXACT_PIN_PREFLIGHT","AUDITED_PROMOTION","CANONICAL_QUALIFICATION"}
TARGET_EVIDENCE = {"ENGINEERING","NUMERICAL","EXACT","INTERVAL","FORMAL"}

REQUIRED = {
    "schema_version","submission_id","head_sha","agent","track","tool","cpp",
    "formal","verification","unresolved_obligations","recommended_next_gate",
    "promotion_authority","packet_sha256"
}

def canonical_digest(packet: dict) -> str:
    body = {k: v for k, v in packet.items() if k != "packet_sha256"}
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()

def _strings(value, field: str, errors: list[str], *, unique: bool = False) -> None:
    if not isinstance(value, list) or any(not isinstance(x, str) or not x for x in value):
        errors.append(f"{field} must be an array of nonempty strings")
        return
    if unique and len(value) != len(set(value)):
        errors.append(f"{field} must contain unique strings")

def validate(packet: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(packet, dict):
        return ["packet must be an object"]
    unknown = sorted(set(packet) - REQUIRED)
    missing = sorted(REQUIRED - set(packet))
    if unknown:
        errors.append("unknown fields: " + ", ".join(unknown))
    if missing:
        errors.append("missing fields: " + ", ".join(missing))
    if packet.get("schema_version") != "cace-ai-tool-submission-v1":
        errors.append("schema_version mismatch")
    if not isinstance(packet.get("submission_id"), str) or len(packet.get("submission_id","")) < 8:
        errors.append("submission_id invalid")
    if not isinstance(packet.get("head_sha"), str) or not HEX40.fullmatch(packet["head_sha"]):
        errors.append("head_sha must be lowercase 40-hex")
    if not isinstance(packet.get("agent"), str) or not packet["agent"]:
        errors.append("agent must be nonempty")
    if packet.get("track") not in TRACKS:
        errors.append("track must be A-I")
    if packet.get("promotion_authority") is not False:
        errors.append("promotion_authority must be false")
    if packet.get("recommended_next_gate") not in NEXT_GATES:
        errors.append("recommended_next_gate invalid")

    tool = packet.get("tool")
    if not isinstance(tool, dict):
        errors.append("tool must be an object")
    else:
        if not isinstance(tool.get("semantic_id"), str) or not SEMANTIC_ID.fullmatch(tool["semantic_id"]):
            errors.append("tool.semantic_id invalid")
        if tool.get("target_evidence") not in TARGET_EVIDENCE:
            errors.append("tool.target_evidence invalid")
        _strings(tool.get("assumptions"), "tool.assumptions", errors)
        _strings(tool.get("failure_modes"), "tool.failure_modes", errors)

    cpp = packet.get("cpp")
    if not isinstance(cpp, dict):
        errors.append("cpp must be an object")
    else:
        for key in ("headers","sources","tests","bindings"):
            _strings(cpp.get(key), f"cpp.{key}", errors, unique=True)

    formal = packet.get("formal")
    if not isinstance(formal, dict):
        errors.append("formal must be an object")
    else:
        if formal.get("proof_state") not in PROOF_STATES:
            errors.append("formal.proof_state invalid; FORMAL/PASS is intentionally not legal here")
        _strings(formal.get("lean_files"), "formal.lean_files", errors, unique=True)
        _strings(formal.get("theorem_names"), "formal.theorem_names", errors, unique=True)
        _strings(formal.get("source_to_formal_refs"), "formal.source_to_formal_refs", errors, unique=True)

    verification = packet.get("verification")
    if not isinstance(verification, dict):
        errors.append("verification must be an object")
    else:
        for key in ("unit_tests","property_tests","adversarial_tests","exact_or_certificate_checks"):
            _strings(verification.get(key), f"verification.{key}", errors, unique=True)

    _strings(packet.get("unresolved_obligations"), "unresolved_obligations", errors)

    digest = packet.get("packet_sha256")
    if not isinstance(digest, str) or not HEX64.fullmatch(digest):
        errors.append("packet_sha256 must be lowercase 64-hex")
    elif digest != canonical_digest(packet):
        errors.append("packet_sha256 mismatch")
    return errors

def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: validate_ai_tool_submission.py SUBMISSION.json", file=sys.stderr)
        return 2
    path = Path(argv[1])
    packet = json.loads(path.read_text(encoding="utf-8"))
    errors = validate(packet)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("CACE_AI_TOOL_SUBMISSION_VALID")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
