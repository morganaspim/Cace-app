from __future__ import annotations
import importlib.util
from pathlib import Path
MODULE_PATH=Path(__file__).parents[1]/"scripts"/"verify_collaboration_records.py";spec=importlib.util.spec_from_file_location("verify_collaboration_records",MODULE_PATH);assert spec and spec.loader;mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
HEAD="a"*40
def record(**updates):
 v={"schema_version":"cace-collaboration-v1","record_id":"task:00000001","record_type":"TASK_LEASE","sender":"chatgpt","target":"gemini","head_sha":HEAD,"evidence_class":"AI_PROPOSAL","created_at":"2026-09-17T00:00:00Z","payload":{"task":"review"},"content_sha256":"0"*64};v.update(updates);v["content_sha256"]=mod.digest(v);return v
def test_valid_record():assert mod.validate(record(),expected_head=HEAD)==[]
def test_hash_detects_mutation():
 v=record();v["payload"]["task"]="changed";assert "content_sha256 mismatch" in mod.validate(v)
def test_stale_head_rejected():assert any(x.startswith("stale head:") for x in mod.validate(record(),expected_head="b"*40))
def test_proved_requires_evidence_reference():assert "PROVED requires at least one evidence_ref" in mod.validate(record(evidence_class="PROVED"))
def test_proved_with_evidence_reference_is_structurally_valid():assert mod.validate(record(evidence_class="PROVED",evidence_refs=["qualification/run-44/kernel-audit"]),expected_head=HEAD)==[]
def test_unknown_field_rejected():
 v=record();v["unexpected"]=True;v["content_sha256"]=mod.digest(v);assert any(x.startswith("unknown fields:") for x in mod.validate(v))
def test_null_payload_rejected():assert "payload must be an object" in mod.validate(record(payload=None))
def test_numeric_sender_rejected():assert any("sender must" in x for x in mod.validate(record(sender=7)))
def test_short_record_id_rejected():assert "record_id violates schema" in mod.validate(record(record_id="x"))
def test_duplicate_evidence_refs_rejected():assert "evidence_refs must be unique nonempty strings" in mod.validate(record(evidence_refs=["x","x"]))
def test_naive_timestamp_rejected():assert "created_at must be timezone-aware ISO-8601 date-time" in mod.validate(record(created_at="2026-09-17T00:00:00"))
