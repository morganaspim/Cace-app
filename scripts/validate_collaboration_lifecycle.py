#!/usr/bin/env python3
"""Cross-record lifecycle checks. Coordination structure is not proof authority."""
from __future__ import annotations
import argparse,json,sys
from collections import defaultdict
from pathlib import Path

def load_records(d):
 out=[]
 for p in sorted(d.glob("*.json")):
  r=json.loads(p.read_text());r["__path"]=str(p);out.append(r)
 return out

def validate(records):
 errors=[];by={};index={}
 for i,r in enumerate(records):
  rid=r.get("record_id")
  if not isinstance(rid,str):errors.append(f"{r.get('__path')}: missing record_id");continue
  if rid in by:errors.append(f"duplicate record_id: {rid}")
  by[rid]=r;index[rid]=i
 # Validate supersession before it can affect lease liveness.
 valid_superseders={}
 for r in records:
  rid=r.get("record_id"); prior=r.get("supersedes")
  if prior is None:continue
  if prior==rid:errors.append(f"{rid}: cannot supersede itself");continue
  old=by.get(prior)
  if old is None:errors.append(f"{rid}: supersedes unknown record {prior}");continue
  if index.get(prior,10**9)>=index.get(rid,-1):errors.append(f"{rid}: supersedes must reference an earlier record");continue
  if r.get("head_sha")!=old.get("head_sha"):errors.append(f"{rid}: cross-head supersession forbidden");continue
  if r.get("record_type") not in {"TASK_LEASE","HANDOFF"} or old.get("record_type") not in {"TASK_LEASE","HANDOFF"}:
   errors.append(f"{rid}: only TASK_LEASE/HANDOFF may supersede a lease/handoff");continue
  valid_superseders[prior]=rid
 # one live owner per exact head
 leases=defaultdict(list)
 for r in records:
  if r.get("record_type") in {"TASK_LEASE","HANDOFF"}:leases[r.get("head_sha")].append(r)
 for head,rs in leases.items():
  live=[r for r in rs if r.get("record_id") not in valid_superseders]
  owners={r.get("sender") for r in live}
  if len(owners)>1:errors.append(f"conflicting live lease owners at {head}: {', '.join(sorted(map(str,owners)))}")
 # Per-head documented lifecycle: lease -> proposal/review -> decision -> closed.
 for head,rs in defaultdict(list, {h:[r for r in records if r.get('head_sha')==h] for h in {r.get('head_sha') for r in records}}).items():
  types=[r.get("record_type") for r in rs]
  lease_positions=[i for i,t in enumerate(types) if t in {"TASK_LEASE","HANDOFF"}]
  for i,t in enumerate(types):
   if t in {"PROPOSAL","REVIEW","DECISION","CLOSED"} and not any(j<i for j in lease_positions):errors.append(f"{rs[i].get('record_id')}: {t} requires an earlier lease on the same head")
   if t=="CLOSED" and "DECISION" not in types[:i]:errors.append(f"{rs[i].get('record_id')}: CLOSED requires an earlier DECISION on the same head")
 # Handoff must supersede prior lease/handoff and change/identify target owner explicitly.
 for r in records:
  if r.get("record_type")=="HANDOFF":
   rid=r.get("record_id");prior=r.get("supersedes")
   if prior not in valid_superseders:errors.append(f"{rid}: invalid HANDOFF supersession")
 for r in records:
  for f in ("discovery_refs","evidence_refs"):
   v=r.get(f,[])
   if not isinstance(v,list) or not all(isinstance(x,str) and x for x in v):errors.append(f"{r.get('record_id')}: {f} must be a list of nonempty strings")
 return errors

def main():
 p=argparse.ArgumentParser();p.add_argument("--records",type=Path,default=Path("collaboration/records"));a=p.parse_args();rs=load_records(a.records);e=validate(rs);print(json.dumps({"schema":"cace-collaboration-lifecycle-v1","records_checked":len(rs),"errors":e},indent=2,sort_keys=True));return 1 if e else 0
if __name__=="__main__":sys.exit(main())
