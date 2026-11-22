#!/usr/bin/env python3
"""One-shot, rootless user+network namespaced GGUF inference from an extracted ZIP.

Never uses the installed host model provider, changes a system unit, installs a
package, exports weights, signs a release or asserts general model quality.
Frozen positive/negative controls are in test_packaged_model_inference.py.
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
import stat
import struct
import subprocess
import sys
import time

MODEL_PORT = 18777
MODEL_ALIAS = "merlin-private-zip-smoke"
BIN_SHA = "af4c10f1f4a1e7f0878dc9b3896bb742f65170861276ef04ddecdf2a9be3cd82"
MODEL_SHA = "cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046"
BIN_SIZE = 14614984
MODEL_SIZE = 1117320768
SAFE_ENV = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
            "PYTHONDONTWRITEBYTECODE": "1", "OMP_NUM_THREADS": "2",
            "OPENBLAS_NUM_THREADS": "2"}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def _pinned_regular(path, expected_size, expected_sha, *, executable):
    file = Path(path)
    before = file.lstat()
    expected_mode = 0o755 if executable else 0o644
    if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
            or stat.S_IMODE(before.st_mode) != expected_mode
            or before.st_size != expected_size
            or not isinstance(expected_sha, str)
            or re.fullmatch(r"[0-9a-f]{64}", expected_sha) is None):
        raise ValueError("packaged model/binary type, mode or size differs")
    fd = os.open(file, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    count = 0
    hashval = hashlib.sha256()
    start = time.monotonic()
    try:
        opened = os.fstat(fd)
        if (opened.st_dev,opened.st_ino,opened.st_size) != (before.st_dev,before.st_ino,before.st_size):
            raise ValueError("packaged file changed before hashing")
        while True:
            if time.monotonic()-start > 110:
                raise ValueError("packaged file digest time budget exceeded")
            data = os.read(fd, 4*1024*1024)
            if not data:
                break
            hashval.update(data)
            count += len(data)
            if count > expected_size:
                raise ValueError("packaged model file grew during hashing")
        after = os.fstat(fd)
        if (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns) != (
                opened.st_dev,opened.st_ino,opened.st_size,opened.st_mtime_ns,opened.st_ctime_ns):
            raise ValueError("packaged file changed during hashing")
        if hashval.hexdigest() != expected_sha or count != expected_size:
            raise ValueError("packaged file content digest differs")
        os.lseek(fd, 0, os.SEEK_SET)
        return os.read(fd,20)
    finally:
        os.close(fd)


def verify_packaged_assets(*,root,binary_sha,model_sha,binary_size,model_size):
    root = Path(root)
    if root.name != "Merlin_Studio" or not root.is_dir() or root.is_symlink():
        raise ValueError("exact private extracted archive root required")
    binary = root / "bin/llama-server"
    model = root / "models/merlin-local.gguf"
    header = _pinned_regular(binary,binary_size,binary_sha,executable=True)
    if (len(header) != 20 or header[:6] != b"\x7fELF\x02\x01"
            or struct.unpack("<H",header[18:20])[0] != 183):
        raise ValueError("packaged inference executable not Linux aarch64 ELF64")
    model_header = _pinned_regular(model,model_size,model_sha,executable=False)
    if model_header[:4] != b"GGUF":
        raise ValueError("packaged model is not GGUF")
    return {
        "binary": {"sha256":binary_sha,"bytes":binary_size},
        "model": {"sha256":model_sha,"bytes":model_size},
        "model_inference_executed": False,
        "production_qualified": False,
    }


def model_argv(root):
    root = Path(root)
    if root.name != "Merlin_Studio":
        raise ValueError("invalid extracted archive root")
    return [str(root / "bin/llama-server"),
            "--model",str(root / "models/merlin-local.gguf"),
            "--alias",MODEL_ALIAS,"--host","127.0.0.1",
            "--port",str(MODEL_PORT),"--ctx-size","1024",
            "--parallel","1","--threads","2","--threads-batch","2",
            "--threads-http","2","--n-gpu-layers","0","--offline","--no-webui"]


def no_default_route(raw):
    if not isinstance(raw,str):
        return False
    lines = raw.splitlines()
    if len(lines) < 2 or not lines[0].lstrip().startswith("Iface"):
        return False
    for line in lines[1:]:
        columns = line.split()
        if len(columns) < 2:
            return False
        if columns[1] == "00000000" and columns[0] != "lo":
            return False
    return True


def _unique_json(pairs):
    row = {}
    for k,v in pairs:
        if k in row:
            raise ValueError("duplicate model JSON key")
        row[k] = v
    return row


def assess_model_reply(message):
    if not isinstance(message,dict):
        raise ValueError("model JSON response not an object")
    choices = message.get("choices")
    if not isinstance(choices,list) or len(choices) != 1 or not isinstance(choices[0],dict):
        raise ValueError("model JSON response missing exact single choice")
    item = choices[0].get("message")
    value = item.get("content") if isinstance(item,dict) else None
    if not isinstance(value,str) or not 1 <= len(value.strip()) <= 1024:
        raise ValueError("empty, oversized or malformed real model answer")
    exact = value.strip() == "42"
    return {
        "model_inference_executed": True,
        "answer_exact_42": exact,
        "answer_sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
        "answer_length_chars": len(value),
        "general_model_quality_qualified": False,
        "production_qualified": False,
    }


def _request(method, path, body=None, *, seconds):
    if (method,path) not in {
        ("GET","/health"),("GET","/v1/models"),
        ("POST","/v1/chat/completions")}:
        raise ValueError("model probe endpoint not allowed")
    data = None if body is None else json.dumps(body,sort_keys=True,allow_nan=False).encode()
    if data is not None and len(data) > 2048:
        raise ValueError("model probe request oversized")
    conn = http.client.HTTPConnection("127.0.0.1",MODEL_PORT,timeout=seconds)
    try:
        conn.request(method,path,body=data,
                     headers={"Connection":"close","Content-Type":"application/json"})
        response = conn.getresponse()
        if response.status != 200:
            raise RuntimeError("model HTTP response not successful")
        raw = response.read(65537)
        if not 0 < len(raw) <= 65536:
            raise ValueError("bounded model response required")
        return json.loads(raw,object_pairs_hook=_unique_json)
    finally:
        conn.close()


def _namespace(parent):
    if os.geteuid() != 1000:
        raise RuntimeError("isolated package inference UID must be 1000")
    if os.stat("/proc/self/ns/net").st_ino == parent:
        raise RuntimeError("model retained host network namespace")
    if Path("/proc/self/uid_map").read_text().split() != ["1000","1000","1"]:
        raise RuntimeError("private user namespace mapping differs")
    if sorted(name for _,name in socket.if_nameindex()) != ["lo"]:
        raise RuntimeError("non-loopback network interface in private model namespace")
    if not no_default_route(Path("/proc/net/route").read_text()):
        raise RuntimeError("model namespace exposes default route")
    return os.stat("/proc/self/ns/net").st_ino


def _enable_private_loopback():
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sk:
        rq = struct.pack("16sH14s",b"lo",0,b"")
        name,flags,pad = struct.unpack("16sH14s",fcntl.ioctl(sk.fileno(),0x8913,rq))
        if name.rstrip(b"\0") != b"lo":
            raise RuntimeError("private loopback identifier changed")
        if not flags & 1:
            fcntl.ioctl(sk.fileno(),0x8914,
                        struct.pack("16sH14s",b"lo",flags|1,pad))


def _status(pid):
    result = {}
    for line in Path("/proc/%d/status"%pid).read_text().splitlines():
        key,sep,val=line.partition(":")
        if sep and key in ("CapEff","NoNewPrivs","Uid"):
            result[key] = val.strip()
    return result


def _limits():
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    resource.setrlimit(resource.RLIMIT_NOFILE,(128,128))
    resource.setrlimit(resource.RLIMIT_CPU,(210,210))
    resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3))


def _stop(process):
    if process is None:
        return True
    if process.poll() is None:
        try:
            os.killpg(process.pid,signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=5)
    return process.poll() is not None


def _run(root, scratch, parent):
    _namespace(parent)
    privilege = _status(os.getpid())
    if privilege.get("CapEff") != "0000000000000000" or privilege.get("NoNewPrivs") != "1":
        raise RuntimeError("model child retained ambient capabilities")
    pinned = verify_packaged_assets(root=root,binary_sha=BIN_SHA,model_sha=MODEL_SHA,
                                   binary_size=BIN_SIZE,model_size=MODEL_SIZE)
    scratch=Path(scratch)
    out=scratch/"packaged-model.stdout"
    err=scratch/"packaged-model.stderr"
    state={
        "schema":"merlin-private-extracted-gguf-smoke/1",
        "status":"blocked","model_inference_executed":False,
        "packaged_model_sha256":MODEL_SHA,"packaged_server_sha256":BIN_SHA,
        "external_network_allowed":False,"host_mutations":0,
        "model_weights_exported":False,"production_qualified":False,
        "source_pins_verified":True,
    }
    process=None
    try:
        clean=dict(SAFE_ENV)
        clean.update(HOME=str(scratch),XDG_CACHE_HOME=str(scratch),
                     XDG_CONFIG_HOME=str(scratch),TMPDIR=str(scratch))
        with out.open("wb") as stdout, err.open("wb") as stderr:
            process=subprocess.Popen(model_argv(root),cwd=str(root),env=clean,
                                     stdin=subprocess.DEVNULL,stdout=stdout,
                                     stderr=stderr,start_new_session=True,preexec_fn=_limits)
        if process.pid <= 0:
            raise RuntimeError("packaged inference process not created")
        before=_status(process.pid)
        if before.get("CapEff")!="0000000000000000" or before.get("NoNewPrivs")!="1":
            raise RuntimeError("packaged inference process retained capabilities")
        ready=False
        started=time.monotonic()
        while time.monotonic()-started < 150:
            if process.poll() is not None:
                raise RuntimeError("packaged inference exited before health check")
            try:
                health=_request("GET","/health",seconds=2)
                if health.get("status")=="ok":
                    ready=True;break
            except (OSError,ValueError,RuntimeError,http.client.HTTPException):
                pass
            time.sleep(.35)
        if not ready:
            raise RuntimeError("packaged model did not reach loopback health")
        models=_request("GET","/v1/models",seconds=5)
        listed=[x.get("id") for x in models.get("data",[])
                if isinstance(x,dict)] if isinstance(models,dict) else []
        if MODEL_ALIAS not in listed:
            raise RuntimeError("packaged model alias differs")
        body={
            "model":MODEL_ALIAS,"messages":[{"role":"user",
                "content":"Compute 6 times 7. Reply with only the number."}],
            "stream":False,"max_tokens":32,"temperature":0.0,
        }
        answer=_request("POST","/v1/chat/completions",body,seconds=95)
        measured=assess_model_reply(answer)
        state.update(measured)
        state.update(status="private_extracted_model_transport_passed",
                     packaged_model_ready=True,
                     model_provider_independent=True,
                     namespace_loopback_only=True,
                     no_new_privileges=True,
                     request_count=1,
                     elapsed_seconds=round(time.monotonic()-started,3))
    finally:
        state["model_process_terminated"]=_stop(process)
        state["scratch_model_log_bytes"]=(
            out.stat().st_size+err.stat().st_size if out.exists() and err.exists() else 0)
        if state["scratch_model_log_bytes"] > 2*1024*1024:
            state["status"]="blocked"
            state["log_budget_exceeded"]=True
        (scratch/"packaged-model-smoke.json").write_text(
            json.dumps(state,sort_keys=True,indent=2)+"\n")
    if state["status"]!="private_extracted_model_transport_passed":
        raise RuntimeError("private packaged inference incomplete")
    print(json.dumps(state,sort_keys=True))
    return 0


def _setup(root,scratch,parent):
    _namespace(parent)
    _enable_private_loopback()
    self_script=Path(__file__).resolve(strict=True)
    argv=["/usr/bin/setpriv","--no-new-privs","--bounding-set=-all",
          "--inh-caps=-all","/usr/bin/python3","-I","-B",
          str(self_script),"run",str(root),str(scratch),str(parent)]
    env=dict(SAFE_ENV)
    env["HOME"]=str(scratch)
    child=subprocess.run(argv,cwd="/",env=env,stdin=subprocess.DEVNULL,
                         capture_output=True,timeout=320)
    if len(child.stdout)>32768 or len(child.stderr)>32768:
        raise RuntimeError("packaged model child output exceeded limit")
    if child.returncode:
        raise RuntimeError("isolated packaged model child exit "+str(child.returncode))
    print(child.stdout.decode("utf-8",errors="strict").strip())
    return 0


def invoke(root,scratch):
    """Invoke only on OCI runner after verified complete source-only package extraction."""
    root=Path(root)
    scratch=Path(scratch)
    verify_packaged_assets(root=root,binary_sha=BIN_SHA,model_sha=MODEL_SHA,
                           binary_size=BIN_SIZE,model_size=MODEL_SIZE)
    if scratch.is_symlink() or not scratch.is_dir():
        raise ValueError("private model scratch directory unavailable")
    script=Path(__file__).resolve(strict=True)
    parent_ns=os.stat("/proc/self/ns/net").st_ino
    env=dict(SAFE_ENV)
    env["HOME"]=str(scratch)
    command=["/usr/bin/unshare","--user","--map-current-user","--net",
             "--fork","/usr/bin/python3","-I","-B",
             str(script),"setup",str(root),str(scratch),str(parent_ns)]
    proc=subprocess.run(command,cwd="/",env=env,stdin=subprocess.DEVNULL,
                        capture_output=True,timeout=370)
    if (len(proc.stdout)>32768 or len(proc.stderr)>32768
            or proc.returncode != 0):
        raise RuntimeError("isolated private packaged model transport failed")
    try:
        report=json.loads(proc.stdout.decode("utf-8").strip(),object_pairs_hook=_unique_json)
    except (ValueError,UnicodeDecodeError) as exc:
        raise ValueError("packaged model transport receipt invalid") from exc
    if (report.get("status")!="private_extracted_model_transport_passed"
            or report.get("model_inference_executed") is not True
            or report.get("model_process_terminated") is not True
            or report.get("host_mutations") != 0):
        raise ValueError("packaged model inference evidence unqualified")
    return report


def main(argv):
    if len(argv)!=5 or argv[1] not in ("setup","run"):
        raise ValueError("fixed private packaged model phase and inputs required")
    phase,root,scratch,parent=argv[1:]
    root=Path(root)
    scratch=Path(scratch)
    parent=int(parent)
    if phase=="setup":
        return _setup(root,scratch,parent)
    return _run(root,scratch,parent)


if __name__=="__main__":
    try:
        raise SystemExit(main(sys.argv))
    except BaseException as exc:
        if isinstance(exc,SystemExit):
            raise
        print(json.dumps({"status":"blocked","error_type":type(exc).__name__,
                          "reason":str(exc)[:200],"production_qualified":False}),file=sys.stderr)
        raise SystemExit(2)
