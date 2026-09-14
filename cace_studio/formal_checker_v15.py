from __future__ import annotations
import argparse,json
from pathlib import Path
from .core.formal_kernel_v15 import check_artifact

def main(argv=None):
    p=argparse.ArgumentParser(description='CACE v0.15 exact assembly proof checker'); p.add_argument('--artifact',required=True); ns=p.parse_args(argv)
    try: out=check_artifact(json.loads(Path(ns.artifact).read_text(encoding='utf-8')))
    except Exception as exc: out={'passed':False,'errors':[str(exc)]}
    print(json.dumps(out,sort_keys=True,separators=(',',':'))); return 0 if out.get('passed') else 2
if __name__=='__main__': raise SystemExit(main())
