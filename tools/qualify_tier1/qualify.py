#!/usr/bin/env python3
"""Tier-1 static conformance check for a CACE-shaped repo. Stdlib only.

Usage: qualify.py --repo PATH [--contract-index 0] [--json]
Exit: 0 PASS, 1 FAIL, 2 REFUSED (cannot certify what was asked).
"""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess, sys
from pathlib import Path

class Result:
    def __init__(self):
        self.rows = []
    def add(self, cid, status, detail, loc=""):
        self.rows.append({"check": cid, "status": status, "detail": detail, "where": loc})
    def status(self):
        s = {r["status"] for r in self.rows}
        if "FAIL" in s: return "FAIL"
        if "REFUSED" in s and s <= {"PASS", "REFUSED"}: return "REFUSED"
        return "PASS"

def load_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8")), None
    except Exception as e:
        return None, f"{p.name}: {type(e).__name__}: {e}"

def sha256(p: Path):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def git_head(repo: Path):
    try:
        out = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                             capture_output=True, text=True, timeout=20)
        return out.stdout.strip() if out.returncode == 0 else None
    except Exception:
        return None

def find_pin_mathlib(manifest):
    for name, deps in (manifest.get("packages", {}) or {}).items():
        if isinstance(deps, list):
            for d in deps:
                if isinstance(d, dict) and d.get("name") == "mathlib":
                    return d.get("rev")
    for name, deps in (manifest.get("packages") or {}).items():
        if name == "mathlib" and isinstance(deps, dict):
            return deps.get("rev")
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=Path("."))
    ap.add_argument("--contract-index", type=int, default=0)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    repo = a.repo.resolve()
    R = Result()

    cpath = repo / "cace_studio/data/proof_contracts.json"
    data, err = load_json(cpath)
    if err:
        R.add("contract.load", "FAIL", err, "cace_studio/data/proof_contracts.json:1")
        return emit(R, a.json)
    contracts = data.get("contracts") if isinstance(data, dict) else data
    if not isinstance(contracts, list) or not contracts:
        R.add("contract.shape", "FAIL", "no contracts array", "cace_studio/data/proof_contracts.json:1")
        return emit(R, a.json)
    if a.contract_index >= len(contracts):
        R.add("contract.index", "FAIL", f"index {a.contract_index} out of range ({len(contracts)})", "")
        return emit(R, a.json)
    c = contracts[a.contract_index]
    cid = c.get("contract_id", f"#{a.contract_index}")

    eps = c.get("endpoint_theorems") or []
    if len(eps) != len(set(eps)):
        dup = sorted({x for x in eps if eps.count(x) > 1})
        R.add("endpoints.unique", "FAIL", f"{len(eps)-len(set(eps))} duplicate endpoint(s): {dup[:3]}", f"{cid}.endpoint_theorems")
    elif not eps:
        R.add("endpoints.nonempty", "FAIL", "endpoint_theorem set empty", f"{cid}.endpoint_theorems")
    else:
        R.add("endpoints", "PASS", f"{len(eps)} endpoints, unique", f"{cid}.endpoint_theorems")

    bad_ax = [x for x in (c.get("allowed_axioms") or []) if x not in {"Classical.choice", "Quot.sound", "propext"}]
    R.add("axioms.allowed", "FAIL" if bad_ax else "PASS",
          f"unexpected axiom(s): {bad_ax}" if bad_ax else "axioms subset of std3", f"{cid}.allowed_axioms")

    tf = c.get("toolchain_file", "lean-toolchain")
    base = (repo / tf).parent
    tp = repo / tf
    if not tp.exists():
        R.add("toolchain.file", "FAIL", f"missing {tf}", tf)
    else:
        raw = tp.read_text().strip()
        parts = raw.split(":")
        ok = raw.startswith("leanprover/lean4:v") and len(parts[-1].split(".")) == 3
        R.add("toolchain.pin", "PASS" if ok else "FAIL", f"pin={raw}" if ok else f"unparseable pin: {raw!r}", f"{tf}:1")

    mpath = base / "lake-manifest.json"
    lock, lerr = load_json(base / "TOOLCHAIN_LOCK.json")
    man, merr = load_json(mpath)
    pins = c.get("dependency_pins") or []
    want = None
    for p in pins:
        if isinstance(p, dict) and "mathlib" in str(p.get("name", "")).lower():
            want = p.get("rev") or p.get("commit")
    if not merr:
        rev = find_pin_mathlib(man)
        ok = bool(rev) and (want is None or rev.startswith(str(want)[:10]) or str(want).startswith(rev[:10]))
        R.add("manifest.mathlib", "PASS" if ok else "FAIL",
              f"mathlib rev={rev} (contract wants {want})" if not ok else f"mathlib rev={rev} matches contract",
              "lake-manifest.json")
    elif lock and lock.get("lake_manifest_status") == "NOT_GENERATED":
        R.add("manifest.mathlib", "REFUSED",
              f"lake-manifest not generated ({lock.get('reason','')[:60]}); lock says mathlib {lock.get('mathlib_release')}",
              "TOOLCHAIN_LOCK.json:1")
    else:
        R.add("manifest.load", "FAIL", merr, "lake-manifest.json:1")

    missing = [f for f in (c.get("audited_source_files") or []) if not (base / f).exists()]
    R.add("sources.exist", "FAIL" if missing else "PASS",
          f"{len(missing)} missing: {missing[:3]}" if missing else f"{len(c.get('audited_source_files') or [])} audited files present", f"{cid}.audited_source_files")

    # endpoint declarations must exist in the audited Lean sources
    lean_text = []
    for f in (c.get("audited_source_files") or []):
        fp = base / f
        if fp.exists():
            try:
                for i, line in enumerate(fp.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                    lean_text.append((f, i, line))
            except Exception:
                pass
    blob = "\n".join(t[2] for t in lean_text)
    absent = []
    for name in eps:
        short = name.split(".")[-1]
        pat = r"(?:theorem|lemma|def|abbrev)\s+(?:[A-Za-z0-9_'.]+\.)?" + re.escape(short) + r"\b"
        if not re.search(pat, blob):
            absent.append(name)
    if eps:
        R.add("endpoints.declared", "FAIL" if absent else "PASS",
              f"{len(absent)} endpoint(s) with no declaration in audited sources: {absent[:3]}" if absent
              else f"{len(eps)} endpoints found in audited sources",
              f"{cid}.endpoint_theorems")

    bs = c.get("executable_bindings") or []
    bmiss = []
    for b in bs:
        f = b.get("path") or b.get("file") if isinstance(b, dict) else b
        if f and not (repo / f).exists() and not (base / f).exists():
            bmiss.append(f)
    if bs:
        R.add("bindings.exist", "FAIL" if bmiss else "PASS",
              f"missing: {bmiss[:3]}" if bmiss else f"{len(bs)} executable bindings present", f"{cid}.executable_bindings")

    ev = [p for p in [base / "v330_lean_environment_metadata.json", repo / "v330_lean_environment_metadata.json",
                      repo / "cace_continuum_qualification_attestation.json"]]
    present = [p for p in ev if p.exists()]
    if not present:
        R.add("evidence.bundle", "REFUSED", "no qualification evidence bundle; cannot certify axiom closure", str(repo))
    else:
        meta, merr2 = load_json(present[0])
        if merr2:
            R.add("evidence.load", "FAIL", merr2, present[0].name)
        else:
            st = json.dumps(meta)
            R.add("evidence.present", "PASS", f"{len(present)} evidence file(s) parsed", present[0].name)

    head = git_head(repo)
    audit = None
    for cand in ["cace_full-5.py", "scripts/audit_v330_axioms.py"]:
        if (repo / cand).exists():
            audit = cand
            break
    R.add("audit.script", "PASS" if audit else "FAIL", f"found {audit}" if audit else "no axiom audit script", str(repo))
    if head:
        R.add("git.head", "PASS", head[:12], ".git")

    return emit(R, a.json)

def emit(R, as_json):
    st = R.status()
    if as_json:
        print(json.dumps({"status": st, "checks": R.rows}, indent=2, sort_keys=True))
    else:
        for r in R.rows:
            print(f"[{r['status']:7}] {r['check']:20} {r['detail']}  <- {r['where']}")
        print(f"\nRESULT: {st}")
    return {"PASS": 0, "FAIL": 1, "REFUSED": 2}[st]

if __name__ == "__main__":
    sys.exit(main())
