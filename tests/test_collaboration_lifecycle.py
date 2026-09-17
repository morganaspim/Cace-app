from __future__ import annotations
import importlib.util
from pathlib import Path
P=Path(__file__).parents[1]/"scripts"/"validate_collaboration_lifecycle.py";s=importlib.util.spec_from_file_location("lifecycle",P);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
H="a"*40
def r(i,t,sender="chatgpt",head=H,**x):
 v={"record_id":i,"record_type":t,"sender":sender,"head_sha":head};v.update(x);return v
def test_single_lease_valid():assert m.validate([r("task:1","TASK_LEASE")])==[]
def test_conflicting_owners_rejected():assert any("conflicting live lease owners" in x for x in m.validate([r("task:1","TASK_LEASE"),r("task:2","TASK_LEASE",sender="gemini")]))
def test_valid_supersession_allows_owner_change():assert m.validate([r("task:1","TASK_LEASE"),r("task:2","TASK_LEASE",sender="gemini",supersedes="task:1")])==[]
def test_review_cannot_hide_conflicting_lease():
 e=m.validate([r("task:1","TASK_LEASE"),r("review:1","REVIEW",supersedes="task:1"),r("task:2","TASK_LEASE",sender="gemini")]);assert any("only TASK_LEASE/HANDOFF" in x for x in e) and any("conflicting live lease owners" in x for x in e)
def test_cross_head_supersession_rejected():assert any("cross-head supersession forbidden" in x for x in m.validate([r("task:1","TASK_LEASE"),r("task:2","TASK_LEASE",head="b"*40,supersedes="task:1")]))
def test_unknown_supersession_rejected():assert any("supersedes unknown" in x for x in m.validate([r("task:2","TASK_LEASE",supersedes="missing")]))
def test_decision_without_lease_rejected():assert any("DECISION requires an earlier lease" in x for x in m.validate([r("decision:1","DECISION")]))
def test_close_without_decision_rejected():assert any("CLOSED requires an earlier DECISION" in x for x in m.validate([r("task:1","TASK_LEASE"),r("closed:1","CLOSED")]))
def test_valid_lifecycle():assert m.validate([r("task:1","TASK_LEASE"),r("proposal:1","PROPOSAL"),r("review:1","REVIEW"),r("decision:1","DECISION"),r("closed:1","CLOSED")])==[]
def test_reference_shape_rejected():assert any("evidence_refs must" in x for x in m.validate([r("task:1","TASK_LEASE",evidence_refs=[""]) ]))
