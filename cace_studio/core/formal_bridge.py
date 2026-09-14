from __future__ import annotations
import json, subprocess, sys, tempfile
from pathlib import Path
from typing import Any
from .formal_kernel import KERNEL_NAME, KERNEL_VERSION


def invoke_formal_checker(artifact: dict[str, Any], timeout: float = 10.0) -> dict[str, Any]:
    """Invoke the formal checker as an independent Python process."""
    with tempfile.TemporaryDirectory(prefix='cace-proof-') as td:
        p=Path(td)/'artifact.json'; p.write_text(json.dumps(artifact,sort_keys=True,indent=2),encoding='utf-8')
        cmd=[sys.executable,'-m','cace_studio.formal_checker','--artifact',str(p)]
        proc=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout,check=False)
        try: payload=json.loads(proc.stdout.strip())
        except Exception: payload={'passed':False,'errors':['checker did not emit valid JSON'],'stdout':proc.stdout,'stderr':proc.stderr}
        payload['process_returncode']=proc.returncode
        payload['invocation']='subprocess'
        payload['expected_checker']=KERNEL_NAME
        payload['expected_checker_version']=KERNEL_VERSION
        payload['stderr']=proc.stderr
        return payload
