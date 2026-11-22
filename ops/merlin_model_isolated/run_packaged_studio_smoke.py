#!/usr/bin/env python3
"""Exact-source, non-deploying extracted-Merlin-Studio UI and restart smoke.

Runs in a rootless user+network namespace with loopback only. Tests the actual
Python interpreter and application restored from a verified model-containing ZIP.
Does not access external networks, start GGUF inference, modify host services, or
grant production status.
"""
from __future__ import annotations

import fcntl
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import resource
import signal
import socket
import struct
import subprocess
import sys
import time

PORT = 18793
SCHEMA = "merlin-packaged-studio-ui-restart/1"
ENV = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
       "PYTHONDONTWRITEBYTECODE": "1"}


def require(ok, why):
    if not ok:
        raise RuntimeError(why)


def no_external_route(raw):
    if not isinstance(raw, str):
        return False
    rows = raw.splitlines()
    if not rows or rows[0].split()[:3] != ["Iface", "Destination", "Gateway"]:
        return False
    for row in rows[1:]:
        columns = row.split()
        if len(columns) < 3 or columns[0] != "lo":
            return False
    return True


def namespace(parent):
    require(os.geteuid() == 1000, "expected unprivileged UID1000")
    require(Path("/proc/self/uid_map").read_text().split() == ["1000", "1000", "1"],
            "user namespace mapping differs")
    require(os.stat("/proc/self/ns/net").st_ino != parent, "host network namespace exposed")
    require(sorted(n for _, n in socket.if_nameindex()) == ["lo"],
            "private namespace has another network interface")
    require(no_external_route(Path("/proc/net/route").read_text()),
            "external routing was observed")
    return os.stat("/proc/self/ns/net").st_ino


def enable_private_loopback():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        raw = struct.pack("16sH14s", b"lo", 0, b"")
        name, flags, padding = struct.unpack("16sH14s",
                                              fcntl.ioctl(s.fileno(), 0x8913, raw))
        require(name.rstrip(b"\0") == b"lo", "private interface name differs")
        if not flags & 1:
            fcntl.ioctl(s.fileno(), 0x8914,
                        struct.pack("16sH14s", b"lo", flags | 1, padding))


def limits():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
    resource.setrlimit(resource.RLIMIT_FSIZE, (8*1024*1024, 8*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU, (80, 80))
    resource.setrlimit(resource.RLIMIT_AS, (3*1024**3, 3*1024**3))


def request(method, path, payload=None, token=None):
    allowed = {( "GET", "/api/health"), ("GET", "/api/status"),
               ("GET", "/studio/"), ("POST", "/api/conversations")}
    if (method, path) not in allowed and not (
            method == "GET" and re.fullmatch(r"/api/conversations/[0-9a-f]{32}", path)):
        raise ValueError("unapproved offline Studio endpoint")
    raw = None if payload is None else json.dumps(
        payload, ensure_ascii=False, allow_nan=False).encode()
    require(raw is None or len(raw) <= 2048, "offline request too large")
    headers = {"Host": f"127.0.0.1:{PORT}", "Connection": "close"}
    if method == "POST":
        require(isinstance(token,str) and len(token) >= 32, "mutation token missing")
        headers.update({"X-Merlin-Token": token,
                        "Content-Type": "application/json"})
    con = http.client.HTTPConnection("127.0.0.1", PORT, timeout=4)
    try:
        con.request(method, path, body=raw, headers=headers)
        res = con.getresponse()
        data = res.read(1024*1024+1)
        require(len(data) <= 1024*1024, "offline Studio response over budget")
        if path == "/studio/" and res.status == 200:
            require("text/html" in res.getheader("Content-Type",""),
                    "offline Studio UI content type differs")
            return res.status, data
        obj = json.loads(data)
        require(isinstance(obj,dict), "offline API returned non-object")
        return res.status, obj
    finally:
        con.close()


def stop(proc):
    if proc is None:
        return True
    if proc.poll() is None:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    try:
        proc.wait(timeout=6)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid,signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait(timeout=5)
    return proc.poll() is not None


def run(root, scratch, evidence, parent):
    namespace(parent)
    state = Path("/proc/self/status").read_text().splitlines()
    fields = {key:val.strip() for key,sep,val in
              (line.partition(":") for line in state) if sep}
    require(fields.get("CapEff") == "0000000000000000"
            and fields.get("NoNewPrivs") == "1",
            "offline Studio verifier has effective capabilities")
    source = root / "Merlin_Studio"
    require(source.is_dir() and not source.is_symlink(),
            "verified extract root unavailable")
    require(all((source/p).is_file() and not (source/p).is_symlink()
                for p in ("server.py", "engine.py", "model.py",
                          "storage.py", "tools.py", "web/index.html")),
            "verified Studio source absent")
    py = source / "runtime/python/bin/python3"
    require(py.is_file() and py.resolve(strict=True).is_relative_to(source.resolve(strict=True))
            and py.resolve(strict=True).name == "python3.11",
            "verified packaged Python unavailable")
    home = scratch / "private-ui-home"
    data = scratch / "private-ui-state"
    home.mkdir(mode=0o700,exist_ok=False)
    data.mkdir(mode=0o700,exist_ok=False)
    env={**ENV,"HOME":str(home),"TMPDIR":str(home),
         "XDG_CACHE_HOME":str(home),"XDG_CONFIG_HOME":str(home)}
    bootstrap=("import sys;sys.path.insert(0,%r);"
               "from server import create_server;"
               "s=create_server(port=%d,data_dir=%r,start_bundled=False);"
               "s.serve_forever(poll_interval=0.2)"
               % (str(source), PORT, data))
    cmd=[str(py),"-I","-B","-S","-c",bootstrap]
    report={"schema":SCHEMA,"status":"blocked","production_qualified":False,
            "model_inference_executed":False,"host_mutations":0,
            "external_network_available":False,"packaged_python_started":False,
            "studio_ui_served":False,"conversation_restored":False,
            "stale_token_rejected":False,"studio_workers_terminated":False}
    worker=None
    start=time.monotonic()

    def launch(n):
        out=evidence/("studio-%d.stdout"%n)
        err=evidence/("studio-%d.stderr"%n)
        with out.open("wb") as stdout,err.open("wb") as stderr:
            proc=subprocess.Popen(cmd,cwd="/",env=env,stdin=subprocess.DEVNULL,
                stdout=stdout,stderr=stderr,start_new_session=True,preexec_fn=limits)
        deadline=time.monotonic()+25
        while time.monotonic()<deadline:
            require(proc.poll() is None, "packaged Studio exited before healthy")
            try:
                code,health=request("GET","/api/health")
                if code==200 and health.get("ready") is True:
                    return proc
            except (OSError,ValueError,RuntimeError,http.client.HTTPException):
                pass
            time.sleep(.15)
        stop(proc)
        raise RuntimeError("packaged Studio health timeout")

    try:
        worker=launch(1)
        report["packaged_python_started"]=True
        code,html=request("GET","/studio/")
        require(code==200 and b"Merlin" in html and len(html)>1000,
                "packaged chat UI not served")
        report["studio_ui_served"]=True
        report["ui_sha256"]=hashlib.sha256(html).hexdigest()
        code,first=request("GET","/api/status")
        require(code==200 and first.get("ready") is True
                and first.get("version")=="0.2.0",
                "Studio status differs")
        token=first.get("session_token")
        require(isinstance(token,str) and len(token)>=32, "first session token missing")
        caps=first.get("capabilities",{})
        require(isinstance(caps,dict) and all(
                caps.get(name) is False for name in ("network","python","desktop")),
                "offline host capabilities unexpectedly active")
        code,created=request("POST","/api/conversations",
                             {"title":"OCI packaged restart smoke"},token)
        require(code==201 and isinstance(created.get("conversation"),dict),
                "packaged conversation not created")
        cid=created["conversation"].get("id")
        require(isinstance(cid,str) and re.fullmatch(r"[0-9a-f]{32}",cid),
                "unexpected conversation identity")
        require(stop(worker), "first packaged Studio stop failed")
        worker=None
        worker=launch(2)
        code,after=request("GET","/api/status")
        require(code==200 and after.get("session_token")!=token,
                "Studio reused old session token after restart")
        code,restored=request("GET","/api/conversations/"+cid)
        require(code==200 and restored.get("conversation",{}).get("id")==cid
                and restored["conversation"].get("title")=="OCI packaged restart smoke",
                "persisted offline conversation not recovered")
        report["conversation_restored"]=True
        code,denied=request("POST","/api/conversations",
                             {"title":"stale token must fail"},token)
        require(code==403,"stale mutation token accepted after restart")
        report["stale_token_rejected"]=True
        report["conversation_sha256"]=hashlib.sha256(cid.encode()).hexdigest()
        report["status"]="packaged_ui_and_restart_passed"
        return True
    except BaseException as exc:
        report["error_type"]=type(exc).__name__
        report["error_reason"]=str(exc)[:170]
        return False
    finally:
        report["studio_workers_terminated"]=stop(worker)
        report["elapsed_seconds"]=round(time.monotonic()-start,3)
        (evidence/"packaged-studio-ui.json").write_text(
            json.dumps(report,sort_keys=True,indent=2)+"\n")
        print(json.dumps({k:report.get(k) for k in (
            "status","studio_ui_served","conversation_restored",
            "stale_token_rejected","studio_workers_terminated",
            "production_qualified")},sort_keys=True))


def setup(root,scratch,evidence,parent):
    namespace(parent)
    enable_private_loopback()
    args=["/usr/bin/setpriv","--no-new-privs","--bounding-set=-all",
          "--inh-caps=-all","/usr/bin/python3","-I","-B",
          str(Path(__file__).resolve(strict=True)),"run",
          str(root),str(scratch),str(evidence),str(parent)]
    child=subprocess.run(args,cwd="/",env={**ENV,"HOME":str(scratch)},
                         stdin=subprocess.DEVNULL,capture_output=True,timeout=130)
    (evidence/"studio-wrapper.stdout").write_bytes(child.stdout[:8192])
    (evidence/"studio-wrapper.stderr").write_bytes(child.stderr[:8192])
    require(len(child.stdout)<=8192 and len(child.stderr)<=8192,
            "packaged UI wrapper output over budget")
    return child.returncode==0


def invoke(root,scratch):
    root=Path(root)
    scratch=Path(scratch)
    require(root.is_dir() and not root.is_symlink() and
            scratch.is_dir() and not scratch.is_symlink(),
            "isolated packaged UI inputs unavailable")
    evidence=scratch/"ui-evidence"
    evidence.mkdir(mode=0o700,exist_ok=False)
    parent=os.stat("/proc/self/ns/net").st_ino
    args=["/usr/bin/unshare","--user","--map-current-user","--net",
          "--fork","/usr/bin/python3","-I","-B",
          str(Path(__file__).resolve(strict=True)),"setup",
          str(root),str(scratch),str(evidence),str(parent)]
    proc=subprocess.run(args,cwd="/",env={**ENV,"HOME":str(scratch)},
                        stdin=subprocess.DEVNULL,capture_output=True,timeout=150)
    require(len(proc.stdout)<=8192 and len(proc.stderr)<=8192,
            "packaged UI subprocess output over budget")
    report=evidence/"packaged-studio-ui.json"
    require(report.is_file() and not report.is_symlink()
            and report.stat().st_size<=8192,
            "packaged Studio UI proof missing")
    result=json.loads(report.read_text())
    require(proc.returncode==0 and result.get("status")=="packaged_ui_and_restart_passed"
            and result.get("studio_ui_served") is True
            and result.get("conversation_restored") is True
            and result.get("stale_token_rejected") is True
            and result.get("studio_workers_terminated") is True
            and result.get("production_qualified") is False,
            "packaged Studio UI/restart acceptance failed")
    return result


def main(argv):
    require(len(argv)==6 and argv[1] in ("setup","run"),
            "fixed packaged UI phase arguments required")
    phase,raw_root,raw_scratch,raw_evidence,raw_parent=argv[1:]
    root,scratch,evidence=Path(raw_root),Path(raw_scratch),Path(raw_evidence)
    require(all(x.is_dir() and not x.is_symlink() for x in (root,scratch,evidence)),
            "private source/staging/evidence directory missing")
    return (setup(root,scratch,evidence,int(raw_parent)) if phase=="setup"
            else run(root,scratch,evidence,int(raw_parent)))


if __name__=="__main__":
    try:
        raise SystemExit(0 if main(sys.argv) else 2)
    except BaseException as exc:
        if isinstance(exc,SystemExit):
            raise
        print(json.dumps({"status":"blocked","error_type":type(exc).__name__,
                          "reason":str(exc)[:170],"production_qualified":False}),
              file=sys.stderr)
        raise SystemExit(2)
