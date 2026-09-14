from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from .core.prager_synge_exact import check_artifact

def main():
    p=argparse.ArgumentParser(); p.add_argument('--artifact',required=True); ns=p.parse_args()
    a=json.loads(Path(ns.artifact).read_text())
    out=check_artifact(a); print(json.dumps(out,sort_keys=True))
    return 0 if out['passed'] else 1
if __name__=='__main__': raise SystemExit(main())
