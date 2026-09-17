#!/usr/bin/env python3
"""Verify CACE collaboration records without granting them proof authority."""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess, sys
from datetime import datetime
from pathlib import Path
from typing import Any
SHA40=re.compile(r"^[0-9a-f]{40}$"); SHA256=re.compile(r"^[0-9a-f]{64}$"); RID=re.compile(r"^[A-Za-z0-9._:-]{8,160}$")
RECORD_TYPES={"TASK_LEASE","PROPOSAL","REVIEW","DECISION","HANDOFF","CLOSED"}; EVIDENCE_CLASSES={"AI_PROPOSAL","ENGINEERING_VERIFIED","CERTIFIED_NUMERICAL","PROVED"}
REQUIRED={"schema_version","record_id","record_type","sender","target","head_sha","evidence_class","created_at","payload","content_sha256"}; OPTIONAL={"supersedes","discovery_refs","evidence_refs"}
def canonical_bytes(r:dict[str,Any])->bytes:
 return json.dumps({k:v for k,v in r.items() if k!="content_sha256"},sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
def digest(r): return hashlib.sha256(canonical_bytes(r)).hexdigest()
def git_head(repo): return subprocess.check_output(["git","rev-parse","HEAD"],cwd=repo,text=True).strip()
def validate(r:dict[str,Any],expected_head=None)->list[str]:
 e=[]; keys=set(r); missing=REQUIRED-keys; extra=keys-REQUIRED-OPTIONAL
 if missing:e.append("missing fields: "+", ".join(sorted(missing)))
 if extra:e.append("unknown fields: "+", ".join(sorted(extra)))
 if r.get("schema_version")!="cace-collaboration-v1":e.append("unsupported schema_version")
 rid=r.get("record_id")
 if not isinstance(rid,str) or not RID.fullmatch(rid):e.append("record_id violates schema")
 for f in ("sender","target"):
  v=r.get(f)
  if not isinstance(v,str) or not 1<=len(v)<=120:e.append(f+" must be a nonempty string <=120 chars")
 if r.get("record_type") not in RECORD_TYPES:e.append("invalid record_type")
 if r.get("evidence_class") not in EVIDENCE_CLASSES:e.append("invalid evidence_class")
 h=r.get("head_sha")
 if not isinstance(h,str) or not SHA40.fullmatch(h):e.append("head_sha must be lowercase 40-hex")
 elif expected_head is not None and h!=expected_head:e.append(f"stale head: record={h} expected={expected_head}")
 stamp=r.get("created_at")
 try:
  if not isinstance(stamp,str):raise ValueError
  dt=datetime.fromisoformat(stamp.replace("Z","+00:00"))
  if dt.tzinfo is None:raise ValueError
 except ValueError:e.append("created_at must be timezone-aware ISO-8601 date-time")
 if not isinstance(r.get("payload"),dict):e.append("payload must be an object")
 sup=r.get("supersedes")
 if sup is not None and not isinstance(sup,str):e.append("supersedes must be string or null")
 for f in ("discovery_refs","evidence_refs"):
  if f in r:
   v=r[f]
   if not isinstance(v,list) or not all(isinstance(x,str) and x for x in v) or len(v)!=len(set(v)):e.append(f+" must be unique nonempty strings")
 supplied=r.get("content_sha256")
 if not isinstance(supplied,str) or not SHA256.fullmatch(supplied):e.append("content_sha256 must be lowercase 64-hex")
 elif supplied!=digest(r):e.append("content_sha256 mismatch")
 if r.get("evidence_class") in {"PROVED","CERTIFIED_NUMERICAL"} and not r.get("evidence_refs"):e.append(r.get("evidence_class")+" requires at least one evidence_ref")
 return e
def main():
 p=argparse.ArgumentParser();p.add_argument("paths",nargs="*",type=Path);p.add_argument("--repo",type=Path,default=Path.cwd());p.add_argument("--require-current-head",action="store_true");a=p.parse_args();paths=a.paths or sorted((a.repo/"collaboration"/"records").glob("*.json"));expected=git_head(a.repo) if a.require_current_head else None;fail=0;seen=set()
 for path in paths:
  try:
   r=json.loads(path.read_text());
   if not isinstance(r,dict):raise ValueError("top level must be object")
   errors=validate(r,expected);rid=r.get("record_id")
   if isinstance(rid,str) and rid in seen:errors.append("duplicate record_id")
   if isinstance(rid,str):seen.add(rid)
  except Exception as x:errors=[f"parse/validation exception: {x}"]
  print(("FAIL " if errors else "OK   ")+str(path));[print("  - "+x) for x in errors];fail+=bool(errors)
 print(json.dumps({"records_checked":len(paths),"failures":fail},sort_keys=True));return 1 if fail else 0
if __name__=="__main__":sys.exit(main())
