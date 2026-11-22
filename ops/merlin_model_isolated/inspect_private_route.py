#!/usr/bin/env python3
"""One-shot non-deploying rootless network-namespace mapping comparison.

Collect only capabilities/route-table SHAPE; never read routes, host IPs,
credentials, model bytes or unrelated host files. No installed service changes.
"""
from __future__ import annotations
import fcntl
import hashlib
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


def observation(mode,stage,host_netns,loopback_errno=None):
    data=Path("/proc/net/route").read_text()
    lines=data.splitlines()
    rows=[line.split() for line in lines[1:]]
    status=Path("/proc/self/status").read_text().splitlines()
    fields={k:v.strip() for k,sep,v in (row.partition(":") for row in status) if sep}
    cap=int(fields.get("CapEff","0"),16)
    uidmap=Path("/proc/self/uid_map").read_text().split()
    return {
        "schema":"merlin-oci-rootless-route-sample/2",
        "mode":mode,"stage":stage,"private_netns":os.stat("/proc/self/ns/net").st_ino != host_netns,
        "effective_uid":os.geteuid(),
        "uid_map_is_host_uid1000":uidmap in (["1000","1000","1"],["0","1000","1"]),
        "uid_map_inside_root":uidmap==["0","1000","1"],
        "cap_net_admin_inside_namespace":bool(cap & (1<<12)),
        "no_new_privs":fields.get("NoNewPrivs","unknown")=="1",
        "only_loopback_interfaces":sorted(n for _,n in socket.if_nameindex())==["lo"],
        "route_header_columns":lines[0].split() if lines else [],
        "route_lines":len(lines),
        "route_row_column_counts":[len(row) for row in rows[:8]],
        "route_interface_is_lo":[bool(row and row[0]=="lo") for row in rows[:8]],
        "default_destination_rows":sum(len(row)>1 and row[1]=="00000000" for row in rows),
        "nonlo_rows":sum(bool(row and row[0]!="lo") for row in rows),
        "original_predicate_allows":no_default_route(data),
        "loopback_setup_errno":loopback_errno,
        "no_host_route_values_collected":True,
        "host_mutations":0,"model_inference_executed":False,"production_qualified":False,
    }


def child(mode,host_netns):
    print(json.dumps(observation(mode,"before_loopback",host_netns),sort_keys=True),flush=True)
    failure=None
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
        try:
            rq=struct.pack("16sH14s",b"lo",0,b"")
            name,flags,padding=struct.unpack("16sH14s",fcntl.ioctl(s.fileno(),0x8913,rq))
            if name.rstrip(b"\0")!=b"lo":
                raise RuntimeError("unexpected loopback interface name")
            if not flags & 1:
                fcntl.ioctl(s.fileno(),0x8914,
                            struct.pack("16sH14s",b"lo",flags|1,padding))
        except OSError as exc:
            failure=exc.errno if type(exc.errno) is int else -1
    print(json.dumps(observation(mode,"after_loopback_attempt",host_netns,failure),
                     sort_keys=True),flush=True)


def main():
    if len(sys.argv)==4 and sys.argv[1]=="child":
        if sys.argv[2] not in ("same-uid","namespace-root"):
            raise SystemExit("unapproved child mapping")
        child(sys.argv[2],int(sys.argv[3]))
        return
    if len(sys.argv)!=1 or os.geteuid()!=1000:
        raise SystemExit("must run only on UID1000 OCI read-only probe")
    host_netns=os.stat("/proc/self/ns/net").st_ino
    all_observations=[]
    statuses=[]
    for label,flag in (("same-uid","--map-current-user"),
                       ("namespace-root","--map-root-user")):
        args=["/usr/bin/unshare","--user",flag,"--net","--fork",
              "/usr/bin/python3","-I","-B",str(Path(__file__).resolve(strict=True)),
              "child",label,str(host_netns)]
        response=subprocess.run(args,cwd="/",stdin=subprocess.DEVNULL,
            capture_output=True,timeout=25,
            env={"PATH":"/usr/bin:/bin","LANG":"C.UTF-8"})
        parsed=[]
        for row in response.stdout.decode("utf-8","replace").splitlines()[:3]:
            try:
                item=json.loads(row)
                if item.get("schema")=="merlin-oci-rootless-route-sample/2":
                    parsed.append(item)
            except (ValueError,AttributeError):
                pass
        stderr=response.stderr[:8192]
        markers=[("permission_denied",b"Operation not permitted"),
                 ("missing_path",b"No such file"),
                 ("import_failure",b"ImportError"),
                 ("runtime_error",b"RuntimeError")]
        category=next((name for name,needle in markers if needle in stderr),
                      "none" if response.returncode==0 else "other_failure")
        all_observations.extend(parsed)
        statuses.append({"mapping":label,"returncode":response.returncode,
                         "observed_steps":len(parsed),"error_class":category,
                         "stderr_sha256":hashlib.sha256(stderr).hexdigest()})
    report={
        "schema":"merlin-oci-private-route-mapping-comparison/1",
        "status":"observed_unqualified",
        "modes":statuses,"observations":all_observations,
        "host_mutations":0,"model_inference_executed":False,
        "production_qualified":False,
    }
    Path("private-route-result.json").write_text(
        json.dumps(report,sort_keys=True,indent=2)+"\n")
    if any(row.get("host_mutations")!=0 or row.get("nonlo_rows")!=0
           or row.get("only_loopback_interfaces") is not True
           or row.get("private_netns") is not True
           or row.get("uid_map_is_host_uid1000") is not True
           for row in all_observations):
        raise RuntimeError("unexpected route, interface or namespace identity")
    print(json.dumps({"status":"observed_unqualified",
        "modes":statuses,"observation_count":len(all_observations),
        "host_mutations":0,"production_qualified":False},sort_keys=True))


if __name__=="__main__":
    main()
