from __future__ import annotations
import json,subprocess,sys,tempfile
from pathlib import Path
from typing import Any
from .formal_kernel_v14 import KERNEL_NAME,KERNEL_VERSION

def invoke_fem_checker(artifact:dict[str,Any],timeout:float=10.0)->dict[str,Any]:
    with tempfile.TemporaryDirectory(prefix='cace-fem-proof-') as td:
        p=Path(td)/'artifact.json'; p.write_text(json.dumps(artifact,sort_keys=True,indent=2),encoding='utf-8')
        proc=subprocess.run([sys.executable,'-m','cace_studio.formal_checker_v14','--artifact',str(p)],capture_output=True,text=True,timeout=timeout,check=False)
        try: out=json.loads(proc.stdout.strip())
        except Exception: out={'passed':False,'errors':['checker did not emit valid JSON']}
        out.update({'process_returncode':proc.returncode,'invocation':'subprocess','expected_checker':KERNEL_NAME,'expected_checker_version':KERNEL_VERSION,'stderr':proc.stderr})
        return out
