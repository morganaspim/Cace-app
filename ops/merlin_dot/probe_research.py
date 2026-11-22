"""Root-only fixed read probe reproducing the upgrade's v1 child invocation."""
import os
from pathlib import Path
import subprocess

OLD = Path("/opt/merlin-dot-private/releases/95e4985f5cf4af7b31bbb183047f6e2e4c4488034ec2d880e54f260feedb0b10")
SAFE_ENV = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C.UTF-8"}


def probe():
    if os.geteuid() != 0:
        raise PermissionError("fixed private-service probe requires root")
    code = """import sys,os
sys.path.insert(0,sys.argv[1])
import json
print('PROBE_IDENTITY='+json.dumps({'uid':os.getuid(),'gid':os.getgid(),'groups':os.getgroups(),'python':sys.version,'path':sys.path}),flush=True)
from dot_ai_os.private_runtime import call_socket
tools=['health'];receipts={}
for tool in tools:
 q={'schema':'merlin-private-call/1','request_id':'upgrade-'+tool,'tool':tool,'arguments':{}}
 r=call_socket('/run/merlin-dot-private/tools.sock',q,expected_server_uid=982,timeout_seconds=5)
 print('PROBE_REPLY='+json.dumps(r),flush=True)
 if r.get('ok') is not True or r.get('qualification') is not False or r.get('promotion_authority') is not False: raise RuntimeError('fixed read tool failed')
 if tool=='health' and (r['result'].get('transport')!='unix' or r['result'].get('public_listener') is not False): raise RuntimeError('private route changed')
 receipts[tool]={'ok':True}
q={'schema':'merlin-private-call/1','request_id':'upgrade-write-denial','tool':'job_submit','arguments':{}}
r=call_socket('/run/merlin-dot-private/tools.sock',q,expected_server_uid=982,timeout_seconds=5)
print('PROBE_REPLY='+json.dumps(r),flush=True)
if r.get('ok') is not False or r.get('error',{}).get('code')!='tool_not_allowed': raise RuntimeError('write denial failed')
print(json.dumps({'tools':receipts,'job_submit':'tool_not_allowed'}))
"""
    command = ["/usr/bin/python3", "-I", "-B", "-c", code, str(OLD / "python")]
    try:
        result = subprocess.run(command, user=1000, group=1000, extra_groups=[],
                                cwd=str(OLD), env=SAFE_ENV, capture_output=True,
                                text=True, timeout=30, check=False)
        return {"schema": "merlin-dot-fixed-v1-peer-probe/1", "read_only": True,
                "release": str(OLD), "expected_server_uid": 982,
                "child_uid": 1000, "child_gid": 1000, "child_extra_groups": [],
                "returncode": result.returncode, "stdout": result.stdout[-16384:],
                "stderr": result.stderr[-8192:], "stdout_characters": len(result.stdout),
                "stderr_characters": len(result.stderr), "host_mutations": False}
    except subprocess.TimeoutExpired as exc:
        return {"schema": "merlin-dot-fixed-v1-peer-probe/1", "read_only": True,
                "returncode": None, "error_class": "TimeoutExpired",
                "stdout": (exc.stdout or b"")[-16384:].decode("utf-8", "replace"),
                "stderr": (exc.stderr or b"")[-8192:].decode("utf-8", "replace"),
                "host_mutations": False}
    except OSError as exc:
        return {"schema": "merlin-dot-fixed-v1-peer-probe/1", "read_only": True,
                "returncode": None, "error_class": type(exc).__name__, "errno": exc.errno,
                "host_mutations": False}
