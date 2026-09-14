from __future__ import annotations
import json, os, subprocess, sys, tempfile
from pathlib import Path
from typing import Any

def invoke_mesh_orthogonality_checker(artifact: dict[str,Any], timeout: float=10.0) -> dict[str,Any]:
    project_root=Path(__file__).resolve().parents[2]
    env=os.environ.copy()
    old=env.get("PYTHONPATH","")
    env["PYTHONPATH"]=str(project_root)+(os.pathsep+old if old else "")
    with tempfile.TemporaryDirectory(prefix="cace-mesh-orth-") as td:
        p=Path(td)/"artifact.json"
        p.write_text(json.dumps(artifact,indent=2,sort_keys=True)+"\n\n")
        proc=subprocess.run(
            [sys.executable,"-m","cace_studio.formal_checker_mesh_orthogonality","--artifact",str(p)],
            cwd=str(project_root), env=env, capture_output=True, text=True,
            timeout=timeout, check=False,
        )
        try:
            out=json.loads(proc.stdout.strip())
        except Exception:
            out={"passed":False,"errors":["checker did not emit valid JSON"],"stdout":proc.stdout}
        out["process_returncode"]=proc.returncode
        out["invocation"]="independent-subprocess"
        out["cwd_independent"]=True
        out["stderr"]=proc.stderr
        return out
