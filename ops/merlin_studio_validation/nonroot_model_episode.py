#!/usr/bin/env python3
"""Exactly two bounded real local Qwen/llama.cpp generations in private netns.

This is a rootless process owned by this test. It never controls or attests the
separate host-root model provider; no host network, credentials or service
mutations. Two held-out integer questions establish only this scoped model use.
"""
from __future__ import annotations
import hashlib
import http.client
import json
import os
from pathlib import Path
import platform
import re
import resource
import signal
import socket
import stat
import subprocess
import sys
import time

MODEL_SHA = "cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046"
MODEL_BYTES = 1117320768
MANIFEST_SHA = "35cf7ea56185126587e7dc10bb400ec53df51057407f9920d0ab03aff4299203"
MODEL_ALIAS = "merlin-qwen-coder-1.5b-q4"
SOURCE_COMMIT = "2a4daf0e08d6a9b6993ee0d4a9a3cfc35a6f405c"
MODEL_REVISION = "f86cb2c1fa58255f8052cc32aeede1b7482d4361"
RELEASES = Path("/opt/merlin-model-provider/releases")
MANIFEST = Path("/etc/merlin-model-provider/manifest.json")
PORT = 8080
QUESTIONS = (
    ("Compute 17 + 25. Reply with the integer only.", "42"),
    ("Compute 9 multiplied by 7. Reply with the integer only.", "63"),
)


def require(ok, why):
    if not ok:
        raise RuntimeError(why)


def pairs_unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def file_digest(path, size, expected, uid=65534):
    """Strict read of non-symlink root-owned file remapped to overflow UID."""
    require(re.fullmatch(r"[a-f0-9]{64}", expected), "invalid pinned digest")
    before = os.lstat(path)
    require(stat.S_ISREG(before.st_mode) and before.st_uid == uid
            and not (stat.S_IMODE(before.st_mode) & 0o022)
            and before.st_size == size, "rootless model source file identity differs")
    fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW)
    start = time.monotonic()
    done = 0
    sha = hashlib.sha256()
    try:
        opened = os.fstat(fd)
        require((opened.st_dev, opened.st_ino, opened.st_size) ==
                (before.st_dev, before.st_ino, before.st_size),
                "model file changed while opening")
        while done < size:
            require(time.monotonic() - start < 100, "model verification time budget")
            data = os.read(fd, min(1024 * 1024, size - done))
            require(data, "model source truncated while hashing")
            done += len(data)
            sha.update(data)
        after = os.fstat(fd)
        require((before.st_dev, before.st_ino, before.st_size,
                 before.st_mtime_ns, before.st_ctime_ns) ==
                (after.st_dev, after.st_ino, after.st_size,
                 after.st_mtime_ns, after.st_ctime_ns), "model file changed during hash")
        require(done == size and sha.hexdigest() == expected,
                "model source bytes do not match pinned SHA-256")
        return {"bytes": done, "sha256": sha.hexdigest(),
                "elapsed_seconds": round(time.monotonic()-start, 3),
                "owner_uid_inside_namespace": before.st_uid}
    finally:
        os.close(fd)


def bound_source():
    raw = MANIFEST.read_bytes()
    require(len(raw) <= 16384 and hashlib.sha256(raw).hexdigest() == MANIFEST_SHA,
            "manifest digest differs")
    # Reopen with no-follow. The host root file was validated before entering
    # this user namespace; no manifest bytes are sent to the model.
    meta = os.lstat(MANIFEST)
    require(stat.S_ISREG(meta.st_mode) and meta.st_uid == 65534
            and not (stat.S_IMODE(meta.st_mode) & 0o022),
            "root manifest type or owner differs inside mapped user namespace")
    fd = os.open(str(MANIFEST), os.O_RDONLY | os.O_NOFOLLOW)
    try:
        current = os.read(fd, 16385)
        post = os.fstat(fd)
    finally:
        os.close(fd)
    require(current == raw and post.st_size == meta.st_size
            and post.st_ino == meta.st_ino and post.st_dev == meta.st_dev,
            "root manifest replaced during read")
    manifest = json.loads(current, object_pairs_hook=pairs_unique)
    model = manifest.get("model_artifact", {})
    runtime = manifest.get("runtime", {})
    require(manifest.get("schema") == "merlin-local-model-provider/1"
            and manifest.get("status") == "ready"
            and manifest.get("model") == MODEL_ALIAS
            and manifest.get("qualification") is False
            and isinstance(model, dict) and isinstance(runtime, dict)
            and model.get("sha256") == MODEL_SHA
            and model.get("size_bytes") == MODEL_BYTES
            and model.get("repository_revision") == MODEL_REVISION
            and runtime.get("source_commit") == SOURCE_COMMIT,
            "manifest model role and upstream version differ")
    bsha = runtime.get("binary_sha256")
    binary, weights = runtime.get("binary_path"), model.get("path")
    require(isinstance(binary, str) and isinstance(weights, str)
            and isinstance(bsha, str) and re.fullmatch(r"[a-f0-9]{64}", bsha),
            "model runtime source identity absent")
    bp, wp = Path(binary), Path(weights)
    require(bp.name == "llama-server" and
            wp.name == "qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"
            and bp.parent == wp.parent
            and bp.parent.parent == RELEASES
            and re.fullmatch(r"[a-f0-9]{64}", bp.parent.name),
            "unreviewed model source paths")
    for parent in (RELEASES, bp.parent):
        st = os.lstat(parent)
        require(stat.S_ISDIR(st.st_mode) and st.st_uid == 65534
                and not (stat.S_IMODE(st.st_mode) & 0o022),
                "release directory is mutable or symlinked")
    binary_size = os.stat(bp).st_size
    require(0 < binary_size <= 256 * 1024**2 and os.access(bp, os.X_OK),
            "local model executable bounds fail")
    return bp, wp, bsha, binary_size


def network_identity():
    require(os.geteuid() == 1000 and platform.machine() == "aarch64",
            "fixed nonroot ARM64 identity required")
    require(Path("/proc/self/uid_map").read_text().split() == ["1000","1000","1"],
            "user namespace UID map differs")
    parent = int(os.environ["MERLIN_PARENT_NETNS_INODE"])
    own = os.stat("/proc/self/ns/net").st_ino
    require(parent != own, "process still in host network namespace")
    require([name for _, name in socket.if_nameindex()] == ["lo"],
            "private netns has unexpected network links")
    flags = dict(line.split(":",1) for line in
                 Path("/proc/self/status").read_text().splitlines() if ":" in line)
    require(flags.get("CapEff","").strip() == "0000000000000000"
            and flags.get("NoNewPrivs","").strip() == "1",
            "zero-cap/no-new-privileges boundary differs")
    routes = Path("/proc/net/route").read_text().splitlines()[1:]
    require(not any(len(f) > 2 and f[1] == "00000000" for f in
                    (line.split() for line in routes)),
            "default IPv4 route found in private netns")
    return own


def http_json(method, path, payload=None, timeout=20, allowed=(200,)):
    require((method,path) in {
        ("GET","/health"), ("GET","/v1/models"),
        ("POST","/v1/chat/completions")}, "nonallowlisted model endpoint")
    body = None
    if payload is not None:
        require(method == "POST", "payload on unapproved method")
        body = json.dumps(payload,sort_keys=True,separators=(",",":")).encode()
        require(len(body)<=4096, "fixed request exceeds context cap")
    connection = http.client.HTTPConnection("127.0.0.1", PORT, timeout=timeout)
    try:
        connection.request(method,path,body=body,
                           headers={"Content-Type":"application/json"} if body is not None else {})
        resp = connection.getresponse()
        data = resp.read(65537)
        require(len(data)<=65536,"model response exceeds bounded receipt")
        require(resp.status in allowed,"unexpected model HTTP status "+str(resp.status))
        return resp.status, json.loads(data,object_pairs_hook=pairs_unique)
    finally:
        connection.close()


def heldout_request(question):
    require(question in [p[0] for p in QUESTIONS],"new prompt not allowlisted")
    return {"model":MODEL_ALIAS,"temperature":0,"stream":False,"max_tokens":32,
            "messages":[{"role":"system","content":"Answer only the integer, no words, no punctuation."},
                        {"role":"user","content":question}]}


def verify_answer(response, expected):
    require(isinstance(response,dict) and response.get("model")==MODEL_ALIAS
            and isinstance(response.get("choices"),list) and len(response["choices"])==1,
            "unexpected model response envelope")
    choice = response["choices"][0]
    text = choice.get("message",{}).get("content")
    require(isinstance(text,str) and len(text) <= 1024,
            "actual response content missing or oversized")
    usage=response.get("usage",{})
    require(isinstance(usage,dict)
            and type(usage.get("prompt_tokens")) is int and usage["prompt_tokens"] > 0
            and type(usage.get("completion_tokens")) is int
            and 0 < usage["completion_tokens"] <= 32
            and type(usage.get("total_tokens")) is int
            and usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"],
            "local inference token accounting invalid")
    return {"expected":expected,"content":text[:256],
            "matches_exact_reference":bool(re.fullmatch(r"\s*"+re.escape(expected)+r"\s*",text)),
            "prompt_tokens":usage["prompt_tokens"],
            "completion_tokens":usage["completion_tokens"],
            "finish_reason":choice.get("finish_reason")}


def child_process_identity(child, binary, net_inode):
    require(child.poll() is None,"model child stopped unexpectedly")
    pid=child.pid
    root=Path("/proc") / str(pid)
    exe=os.stat(root/"exe")
    owned=os.stat(binary)
    require((exe.st_dev,exe.st_ino)==(owned.st_dev,owned.st_ino),
            "model executable PID inode identity differs")
    require(os.stat(root/"ns/net").st_ino==net_inode,
            "model escaped its private network namespace")
    raw=(root/"cmdline").read_bytes()
    require(raw.startswith(os.fsencode(str(binary))+b"\0"),
            "model process argv does not match pinned executable")
    text=(root/"stat").read_text()
    tail=text.rsplit(") ",1)
    require(len(tail)==2 and len(tail[1].split()) > 19, "model PID start tick unavailable")
    ticks=tail[1].split()[19]
    require(ticks.isdigit(),"model PID start tick is invalid")
    return {"pid":pid,"start_ticks":ticks,"binary_dev":owned.st_dev,
            "binary_inode":owned.st_ino,"network_namespace_inode":net_inode,
            "executable_identity_bound":True}


def run(py, manifest_arg, scratch, evidence):
    scratch,evidence=Path(scratch),Path(evidence)
    require(str(py)=="/usr/bin/python3" and str(manifest_arg)==str(MANIFEST),
            "fixed model episode authority/input differs")
    require(scratch.is_dir() and evidence.is_dir()
            and not scratch.is_symlink() and not evidence.is_symlink(),
            "private scratch folders required")
    receipt={"schema":"merlin-oci-rootless-local-inference/1","status":"blocked",
             "generation_calls":0,"requested_generation_calls":2,
             "external_model_spend_usd":0,"host_service_mutations":False,
             "root_execution":False,"system_installation":False,
             "production_qualified":False,"model_quality_generalized":False}
    stage="network-identity"
    child=None
    log_path=scratch/"owned-llama-server.log"
    try:
        net_inode=network_identity()
        receipt["private_network_namespace_verified"]=True
        receipt["effective_capabilities_zero"]=True
        stage="verify-source"
        binary, weights, binary_hash, bsize=bound_source()
        receipt["binary_identity"]=file_digest(binary,bsize,binary_hash)
        receipt["model_identity"]=file_digest(weights,MODEL_BYTES,MODEL_SHA)
        stage="spawn-private-model"
        profile=scratch/"local-model-home";profile.mkdir(mode=0o700,exist_ok=False)
        env={"PATH":"/usr/bin:/bin","LANG":"C.UTF-8","LC_ALL":"C.UTF-8",
             "HOME":str(profile),"XDG_CACHE_HOME":str(profile),
             "XDG_CONFIG_HOME":str(profile),"XDG_DATA_HOME":str(profile),
             "TMPDIR":str(profile),"PYTHONDONTWRITEBYTECODE":"1"}
        argv=[str(binary),"--model",str(weights),"--alias",MODEL_ALIAS,
              "--host","127.0.0.1","--port",str(PORT),
              "--ctx-size","4096","--parallel","1","--threads","2",
              "--threads-batch","2","--threads-http","2","--n-gpu-layers","0",
              "--offline","--no-webui"]
        require(not any(any(flag in arg for flag in ("0.0.0.0","--public","--no-sandbox"))
                        for arg in argv), "nonlocal/insecure model argument")
        def limits():
            resource.setrlimit(resource.RLIMIT_CPU,(210,210))
            resource.setrlimit(resource.RLIMIT_FSIZE,(1024*1024,1024*1024))
            resource.setrlimit(resource.RLIMIT_NOFILE,(128,128))
            resource.setrlimit(resource.RLIMIT_AS,(6*1024**3,6*1024**3))
        with log_path.open("wb") as log:
            child=subprocess.Popen(argv,cwd="/",env=env,stdin=subprocess.DEVNULL,
                     stdout=log,stderr=subprocess.STDOUT,start_new_session=True,
                     preexec_fn=limits)
        first_identity=child_process_identity(child,binary,net_inode)
        receipt["model_process_before"]=first_identity
        stage="wait-local-health"
        deadline=time.monotonic()+82
        ready=False
        while time.monotonic()<deadline:
            require(child.poll() is None,"model stopped before healthy")
            try:
                _, health=http_json("GET","/health",timeout=3)
                if isinstance(health,dict) and health.get("status")=="ok":
                    ready=True
                    break
            except (OSError,ValueError,RuntimeError,json.JSONDecodeError):
                pass
            time.sleep(0.5)
        require(ready,"private model did not become healthy before deadline")
        _, listing=http_json("GET","/v1/models",timeout=4)
        ids=[row.get("id") for row in listing.get("data",[]) if isinstance(row,dict)]
        require(ids==[MODEL_ALIAS],"new local server alias differs")
        receipt["local_health_ready"]=True
        receipt["model_alias_verified"]=True
        stage="two-fixed-inference-requests"
        answers=[]
        for i,(question,expected) in enumerate(QUESTIONS):
            request=heldout_request(question)
            receipt["generation_calls"]=i+1
            started=time.monotonic()
            _, reply=http_json("POST","/v1/chat/completions",request,timeout=57)
            answer=verify_answer(reply,expected)
            answer["index"]=i+1
            answer["duration_seconds"]=round(time.monotonic()-started,3)
            answers.append(answer)
            receipt["answers"]=answers
            (evidence/"inference-partial.json").write_text(json.dumps(receipt,sort_keys=True,indent=2))
            require(answer["matches_exact_reference"],
                    "local model answer differs from independent fixed reference")
            require(child.poll() is None,"model stopped during bounded inference")
        stage="process-recheck"
        after=child_process_identity(child,binary,net_inode)
        require(after==first_identity,"owned inference process changed before/after")
        receipt["model_process_after"]=after
        receipt["model_file_unchanged_after"]=(
            file_digest(weights,MODEL_BYTES,MODEL_SHA)["sha256"]==MODEL_SHA)
        receipt["binary_unchanged_after"]=(
            file_digest(binary,bsize,binary_hash)["sha256"]==binary_hash)
        receipt["two_reference_checks_passed"]=True
        receipt["status"]="two_live_local_model_turns_verified_in_private_netns"
        return 0
    except BaseException as exc:
        receipt["blocked_stage"]=stage
        receipt["error_type"]=type(exc).__name__
        receipt["error"]=str(exc)[:350]
        return 2
    finally:
        if child is not None:
            if child.poll() is None:
                try: os.killpg(child.pid,signal.SIGTERM)
                except ProcessLookupError: pass
            try: child.wait(timeout=7)
            except subprocess.TimeoutExpired:
                try: os.killpg(child.pid,signal.SIGKILL)
                except ProcessLookupError: pass
                child.wait(timeout=5)
            receipt["owned_process_stopped"]=child.poll() is not None
            receipt["model_child_returncode"]=child.returncode
        else: receipt["owned_process_stopped"]=True
        if log_path.is_file():
            with log_path.open("rb") as f:
                raw=f.read(128*1024)
            (evidence/"owned-llama-server-log-prefix.txt").write_bytes(raw)
            receipt["log_prefix_bytes"]=len(raw)
        receipt["private_endpoint_removed_with_process"]=bool(receipt["owned_process_stopped"])
        (evidence/"model-episode-result.json").write_text(json.dumps(receipt,sort_keys=True,indent=2))
        print(json.dumps({"status":receipt["status"],
            "generation_calls":receipt["generation_calls"],
            "answers_checked":len(receipt.get("answers",[])),
            "owned_process_stopped":receipt.get("owned_process_stopped"),
            "external_model_spend_usd":0,
            "production_qualified":False},sort_keys=True))


if __name__=="__main__":
    if len(sys.argv)!=5:
        raise SystemExit("fixed interpreter, manifest, scratch, evidence required")
    raise SystemExit(run(*sys.argv[1:]))
