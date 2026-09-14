from __future__ import annotations
import argparse, json
from pathlib import Path
from .core.prager_synge_mesh_exact import check_artifact

def main(argv=None):
    p=argparse.ArgumentParser(description="CACE v3.21 exact mesh-admissibility -> orthogonality checker")
    p.add_argument("--artifact",required=True)
    ns=p.parse_args(argv)
    try:
        a=json.loads(Path(ns.artifact).read_text())
        out=check_artifact(a)
    except Exception as exc:
        out={"passed":False,"errors":[str(exc)]}
    print(json.dumps(out,sort_keys=True))
    return 0 if out.get("passed") else 1

if __name__=="__main__":
    raise SystemExit(main())
