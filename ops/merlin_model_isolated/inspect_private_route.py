#!/usr/bin/env python3
"""Rootless OCI-only route table metadata, never routes/addresses or model bytes."""
from __future__ import annotations
import fcntl
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from run_packaged_model_from_zip import no_default_route


def observation(stage):
    data=Path("/proc/net/route").read_text()
    lines=data.splitlines()
    rows=[line.split() for line in lines[1:]]
    header=lines[0].split() if lines else []
    return {
        "schema":"merlin-oci-rootless-route-sample/1",
        "stage":stage,
        "inside_private_uid1000":os.geteuid()==1000
            and Path("/proc/self/uid_map").read_text().split()==["1000","1000","1"],
        "only_loopback_interfaces": sorted(n for _,n in socket.if_nameindex())==["lo"],
        "route_header_columns":header,
        "route_lines":len(lines),
        "route_row_column_counts":[len(row) for row in rows[:8]],
        "route_interface_is_lo":[bool(row and row[0]=="lo") for row in rows[:8]],
        "default_destination_rows":sum(len(row)>1 and row[1]=="00000000" for row in rows),
        "nonlo_rows":sum(bool(row and row[0]!="lo") for row in rows),
        "predicate_allows":no_default_route(data),
        "no_host_route_values_collected":True,
        "host_mutations":0,"model_inference_executed":False,
        "production_qualified":False
    }


def child():
    print(json.dumps(observation("before_private_lo"),sort_keys=True),flush=True)
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
        req=struct.pack("16sH14s",b"lo",0,b"")
        name,flags,padding=struct.unpack("16sH14s",fcntl.ioctl(s.fileno(),0x8913,req))
        if name.rstrip(b"\0")!=b"lo":
            raise RuntimeError("loopback ioctl looked up unexpected interface")
        if not flags&1:
            fcntl.ioctl(s.fileno(),0x8914,struct.pack("16sH14s",b"lo",flags|1,padding))
    print(json.dumps(observation("after_private_lo"),sort_keys=True),flush=True)


def main():
    if len(sys.argv)==2 and sys.argv[1]=="child":
        child();return
    if len(sys.argv)!=1:
        raise SystemExit("fixed inspection mode only")
    if os.geteuid()!=1000:
        raise SystemExit("unprivileged UID1000 runner required")
    original=os.stat("/proc/self/ns/net").st_ino
    args=["/usr/bin/unshare","--user","--map-current-user","--net","--fork",
          "/usr/bin/python3","-I","-B",str(Path(__file__).resolve()),"child"]
    child_result=subprocess.run(args,cwd="/",stdin=subprocess.DEVNULL,
                    capture_output=True,timeout=25,
                    env={"PATH":"/usr/bin:/bin","LANG":"C.UTF-8"})
    if child_result.returncode:
        import hashlib
        stderr = child_result.stderr[:16384]
        stdout = child_result.stdout[:16384]
        markers = [
            ("permission_denied", b"Operation not permitted"),
            ("missing_path", b"No such file or directory"),
            ("module_missing", b"ModuleNotFoundError"),
            ("capability_io_error", b"PermissionError"),
            ("unexpected_interface", b"loopback ioctl"),
            ("route_exception", b"route"),
        ]
        category = next((name for name,part in markers if part in stderr), "unknown_child_failure")
        partial=[]
        for line in stdout.decode("utf-8","replace").splitlines()[:3]:
            try:
                item=json.loads(line)
                if item.get("schema") == "merlin-oci-rootless-route-sample/1":
                    partial.append(item)
            except (ValueError,AttributeError):
                pass
        report={"schema":"merlin-oci-private-route-probe/1","status":"blocked",
                "failure_category":category,"child_returncode":child_result.returncode,
                "child_stderr_sha256":hashlib.sha256(stderr).hexdigest(),
                "observations":partial,"host_mutations":0,
                "model_inference_executed":False,"production_qualified":False}
        Path("private-route-result.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\\n")
        raise RuntimeError("bounded private namespace probe failed: "+category)
    results=[json.loads(x) for x in child_result.stdout.decode("utf-8").splitlines()]
    if len(results)!=2 or any(x.get("nonlo_rows")!=0
                            or x.get("only_loopback_interfaces") is not True
                            or x.get("inside_private_uid1000") is not True for x in results):
        raise RuntimeError("private namespace identity failed")
    report={"schema":"merlin-oci-private-route-probe/1",
            "namespace_separate":True,"observations":results,
            "no_network_access":True,"host_mutations":0,
            "production_qualified":False}
    Path("private-route-result.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"status":"observed","route_predicates":[x["predicate_allows"]
          for x in results],"model_inference_executed":False,
          "host_mutations":0},sort_keys=True))


if __name__=="__main__":
    main()
