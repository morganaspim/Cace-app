#!/usr/bin/env python3
"""Actual Merlin Studio -> separately spawned private GGUF model, two turns.

Single-use test only. Fresh rootless user+network namespace, loopback only.
Temporary CAP_NET_ADMIN turns on only private lo, then setpriv drops all caps
before loading the pinned model or starting Studio. No external model service,
installation, public browser, desktop, Python tool, or user data is accessed.
"""
from __future__ import annotations
import fcntl
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import signal
import socket
import struct
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_private_model as base

STUDIO_PORT = 18771
MODEL_PORT = base.PORT
TESTS = (
    ("Compute 6 times 7. Reply with only the number.", "42"),
    ("Compute 19 plus 23. Reply with only the number.", "42"),
)


def request(method, path, token=None, body=None, timeout=5):
    if method == "GET":
        base.require(path in ("/api/health","/api/status","/api/conversations")
                     or re.fullmatch(r"/api/conversations/[0-9a-f]{32}",path)
                     or re.fullmatch(r"/api/runs/[0-9a-f]{32}",path),
                     "Studio GET not allowlisted")
    else:
        base.require((method,path) in {("POST","/api/settings"),
          ("POST","/api/conversations"),("POST","/api/chat")},
          "Studio mutation not allowlisted")
    data = None if body is None else json.dumps(body,allow_nan=False).encode()
    base.require(data is None or len(data)<=4096,"Studio request too long")
    con=http.client.HTTPConnection("127.0.0.1",STUDIO_PORT,timeout=timeout)
    try:
        headers={"Host":"127.0.0.1:%d"%STUDIO_PORT,
                 "Content-Type":"application/json","Connection":"close"}
        if token:headers["X-Merlin-Token"]=token
        con.request(method,path,body=data,headers=headers)
        response=con.getresponse()
        raw=response.read(128*1024+1)
        base.require(len(raw)<=128*1024,"Studio JSON exceeds bound")
        return response.status,json.loads(raw)
    finally:con.close()


def await_healthy(process, port, expected, deadline=20):
    stop=time.monotonic()+deadline
    while time.monotonic()<stop:
        base.require(process.poll() is None,expected+" process exited early")
        try:
            if port==MODEL_PORT:
                status=base.json_local("GET","/health",seconds=2)
                if status.get("status")=="ok": return True
            else:
                code,value=request("GET","/api/health",timeout=2)
                if code==200 and value.get("ready") is True:
                    return True
        except (OSError,ValueError,RuntimeError,http.client.HTTPException):
            pass
        time.sleep(.15)
    raise RuntimeError(expected+" did not become ready within budget")


def terminate(process, label,ev):
    if process is None:return
    if process.poll() is None:
        try:os.killpg(process.pid,signal.SIGTERM)
        except ProcessLookupError:pass
    try:process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        try:os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        process.wait(timeout=5)
    base.require(process.poll() is not None,label+" process survived cleanup")


def test(ev, product, scratch, parent, python):
    base.namespace_identity(parent)
    flags=base.status(os.getpid())
    base.require(flags.get("CapEff")=="0000000000000000"
                 and flags.get("NoNewPrivs")=="1",
                 "Studio/model controller still has effective capabilities")
    base.require(product.is_dir() and not product.is_symlink(),
                 "pinned product source unavailable")
    base.require(python.is_file() and not python.is_symlink()
                 and python.stat().st_size==56723673
                 and python.name=="python3.11" and python.parent.name=="bin",
                 "privately staged CPython3.11 identity missing")
    studio_dir=product/"portable/merlin_studio"
    for name in ("server.py","engine.py","model.py","storage.py","tools.py","worker.py"):
        base.require((studio_dir/name).is_file() and not (studio_dir/name).is_symlink(),
                     "pinned Merlin Studio module missing")
    model_home=scratch/"model-home";model_home.mkdir(mode=0o700,exist_ok=False)
    data=scratch/"studio-state";data.mkdir(mode=0o700,exist_ok=False)
    env={"PATH":"/usr/bin:/bin","LANG":"C.UTF-8","LC_ALL":"C.UTF-8",
         "HOME":str(model_home),"XDG_CACHE_HOME":str(model_home),
         "XDG_CONFIG_HOME":str(model_home),"TMPDIR":str(scratch),
         "PYTHONDONTWRITEBYTECODE":"1","OMP_NUM_THREADS":"2",
         "OPENBLAS_NUM_THREADS":"2","GGML_N_THREADS":"2"}
    result={"schema":"merlin-oci-studio-real-model/1","status":"blocked",
      "model_generation_calls":0,"source_pinned":True,"host_installed":False,
      "root_used":False,"existing_provider_mutated":False,
      "network_namespace_only_loopback":True,"production_qualified":False}
    model=None;studio=None;start=time.monotonic()
    try:
        source=base.files()
        base.COMMAND=base.COMMAND+["--jinja"]
        with (ev/"private-model.stdout").open("wb") as out, \
             (ev/"private-model.stderr").open("wb") as err:
            model=subprocess.Popen(base.COMMAND,cwd="/",env=env,
                stdin=subprocess.DEVNULL,stdout=out,stderr=err,
                start_new_session=True,preexec_fn=base.restricted_limits)
        await_healthy(model,MODEL_PORT,"private GGUF",deadline=145)
        process_before=base.check_process(model.pid,source,parent)
        model_list=base.json_local("GET","/v1/models",seconds=5)
        base.require(base.ALIAS in [x.get("id") for x in model_list.get("data",[])
                     if isinstance(x,dict)],"live private model alias differs")
        # The exact app code and its actual HTTP worker are both exercised.
        studio_env=dict(env)
        studio_env.update(MERLIN_MODEL_URL="http://127.0.0.1:%d/v1/chat/completions"%MODEL_PORT,
                          MERLIN_MODEL_ID=base.ALIAS)
        bootstrap=("import sys;sys.path.insert(0,%r);sys.path.insert(0,%r);"
                   "from server import main;main()"%
                   (str(studio_dir),str(product/"python")))
        argv=[str(python),"-I","-B","-S","-c",bootstrap,
              "--port",str(STUDIO_PORT),"--data-dir",str(data)]
        def launch_studio():
            return subprocess.Popen(argv,cwd="/",env=studio_env,
                stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,start_new_session=True)
        studio=launch_studio()
        await_healthy(studio,STUDIO_PORT,"Merlin Studio",deadline=17)
        code,status=request("GET","/api/status")
        base.require(code==200 and status.get("version")=="0.2.0"
                     and status.get("model",{}).get("configured") is True
                     and status["model"]["model_id"]==base.ALIAS
                     and status["model"]["endpoint"]==studio_env["MERLIN_MODEL_URL"],
                     "real-model Studio configuration differed")
        token=status["session_token"]
        base.require(isinstance(token,str) and len(token)>=32,
                     "Studio authorization token not present")
        settings={"model_url":studio_env["MERLIN_MODEL_URL"],
                  "model_id":base.ALIAS,"network_enabled":False,
                  "python_enabled":False,"desktop_enabled":False,"max_steps":1}
        code,saved=request("POST","/api/settings",token,settings,timeout=5)
        base.require(code==200,"Studio restricted model settings refused")
        code,stable=request("GET","/api/status")
        base.require(code==200 and
                    all(stable.get("capabilities",{}).get(key) is False
                        for key in ("network","python","desktop")),
                    "non-model tools remain enabled")
        code,created=request("POST","/api/conversations",token,
                             {"title":"OCI genuine local model two turns"})
        base.require(code==201 and isinstance(created.get("conversation"),dict),
                     "real Studio conversation create failed")
        cid=created["conversation"]["id"]
        base.require(re.fullmatch(r"[0-9a-f]{32}",cid) is not None,
                     "Studio storage identity must be a 32-character lowercase hex ID")
        turns=[]
        for question,expected in TESTS:
            code,reply=request("POST","/api/chat",token,
                               {"conversation_id":cid,"message":question})
            base.require(code==202 and
                         re.fullmatch(r"[0-9a-f]{32}",reply.get("run_id","")),
                         "real Studio model run submission failed")
            run_id=reply["run_id"]
            cutoff=time.monotonic()+100
            run=None;actual=None
            while time.monotonic()<cutoff:
                code,info=request("GET","/api/runs/"+run_id)
                base.require(code==200,"Studio model run lookup failed")
                run=info["run"]
                if run["status"] in ("completed","failed","cancelled","interrupted"):
                    messages=info["conversation"].get("messages",[])
                    actual=messages[-1] if messages else None
                    break
                time.sleep(.25)
            if run is not None:
                result["last_run_status"] = str(run.get("status", ""))[:40]
                result["last_run_error"] = str(run.get("error", ""))[:180]
            base.require(run is not None and run.get("status")=="completed",
                         "Studio real model generation did not complete")
            base.require(actual and actual.get("role")=="assistant"
                         and isinstance(actual.get("content"),str),
                         "Studio real model assistant response missing")
            answer=actual["content"]
            passed=answer.strip().strip(".").strip()==expected
            turns.append({"prompt_sha256":hashlib.sha256(question.encode()).hexdigest(),
                          "assistant_sha256":hashlib.sha256(answer.encode()).hexdigest(),
                          "answer_excerpt":answer[:160],"expected":expected,
                          "correct":passed,"run_status":run["status"]})
            result["model_generation_calls"]+=1
        base.require(all(x["correct"] for x in turns),
                     "Studio model answer failed independent arithmetic reference")
        code,before=request("GET","/api/conversations/"+cid)
        base.require(code==200 and len(before["conversation"]["messages"])==4,
                     "expected two genuine persisted user/assistant exchanges")
        # Shut down Studio, NOT the model. Check actual process lifecycle,
        # per-launch token rotation, and persisted model-produced messages.
        terminate(studio,"first Studio",ev)
        studio=None
        studio=launch_studio()
        await_healthy(studio,STUDIO_PORT,"restarted Merlin Studio",deadline=17)
        code,newstatus=request("GET","/api/status")
        base.require(code==200 and newstatus["session_token"]!=token,
                     "Studio restart reused old mutation credential")
        stale_code,stale_reply=request("POST","/api/conversations",token,
                              {"title":"stale token must reject"})
        base.require(stale_code==403,"expired Studio token accepted")
        code,after=request("GET","/api/conversations/"+cid)
        base.require(code==200
                     and before["conversation"]["messages"]==
                         after["conversation"]["messages"],
                     "model-generated conversation changed across backend restart")
        after_worker=base.check_process(model.pid,source,parent)
        base.require(process_before==after_worker,
                     "private GGUF process identity changed across Studio restart")
        result.update(status="passed",correct_answers=2,turns=turns,
          persisted_messages=4,restart_restored=True,stale_token_rejected=True,
          model_worker=process_before,studio_model_alias=base.ALIAS,
          model_file_sha256=source["model"]["sha256"],
          model_binary_sha256=source["binary"]["sha256"])
        return True
    except BaseException as exc:
        result.update(error_type=type(exc).__name__,error_reason=str(exc)[:200])
        return False
    finally:
        if studio is not None:
            # Do not store service stdout that could include authorization data.
            terminate(studio,"Studio",ev)
            if studio.stdout:studio.stdout.close()
            if studio.stderr:studio.stderr.close()
        if model is not None:terminate(model,"private GGUF",ev)
        result["model_process_terminated"]=model is None or model.poll() is not None
        result["studio_process_terminated"]=studio is None or studio.poll() is not None
        result["elapsed_seconds"]=round(time.monotonic()-start,3)
        (ev/"studio-model-result.json").write_text(
            json.dumps(result,sort_keys=True,indent=2))
        print(json.dumps({"status":result["status"],"model_generation_calls":
                          result["model_generation_calls"],
                          "restart_restored":result.get("restart_restored",False),
                          "model_terminated":result["model_process_terminated"],
                          "studio_terminated":result["studio_process_terminated"],
                          "production_qualified":False},sort_keys=True))


def setup(ev,product,scratch,parent,python):
    base.require(os.geteuid()==1000 and
       os.stat("/proc/self/ns/net").st_ino!=parent and
       Path("/proc/self/uid_map").read_text().split()==["1000","1000","1"],
       "rootless Studio namespace setup identity failed")
    base.require(sorted(name for _,name in socket.if_nameindex())==["lo"],
                 "unexpected private namespace interface")
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sk:
        req=struct.pack("16sH14s",b"lo",0,b"")
        name,flags,pad=struct.unpack("16sH14s",fcntl.ioctl(sk.fileno(),0x8913,req))
        base.require(name.rstrip(b"\0")==b"lo","private lo identity differs")
        if not flags&1:
            fcntl.ioctl(sk.fileno(),0x8914,
                        struct.pack("16sH14s",b"lo",flags|1,pad))
    base.namespace_identity(parent)
    args=["/usr/bin/setpriv","--no-new-privs","--bounding-set=-all",
          "--inh-caps=-all","/usr/bin/python3","-I","-B",
          str(Path(__file__).resolve()),"test",str(ev),
          str(product),str(scratch),str(parent),str(python)]
    child=subprocess.run(args,env={"PATH":"/usr/bin:/bin","LANG":"C.UTF-8",
       "HOME":str(scratch),"PYTHONDONTWRITEBYTECODE":"1"},
       cwd="/",stdin=subprocess.DEVNULL,capture_output=True,timeout=340)
    (ev/"studio-model-wrapper.stdout").write_bytes(child.stdout[:32768])
    (ev/"studio-model-wrapper.stderr").write_bytes(child.stderr[:32768])
    base.require(len(child.stdout)<=32768 and len(child.stderr)<=32768,
                 "Studio model controller output over ceiling")
    return child.returncode==0


def main():
    if len(sys.argv)!=7 or sys.argv[1] not in ("setup","test"):
        raise SystemExit("fixed mode, evidence, product, scratch, parent, private interpreter")
    phase,ev,p,scratch,par,py=sys.argv[1:]
    ev,product,scratch,parent,python=Path(ev),Path(p),Path(scratch),int(par),Path(py)
    try:
        base.require(all(x.is_dir() and not x.is_symlink()
                         for x in (ev,product,scratch)),
                     "fixed private folders missing")
        good=(setup(ev,product,scratch,parent,python) if phase=="setup"
              else test(ev,product,scratch,parent,python))
        return 0 if good else 2
    except BaseException as exc:
        (ev/"studio-model-error.json").write_text(
          json.dumps({"status":"blocked","error_type":type(exc).__name__,
              "reason":str(exc)[:220],"production_qualified":False},sort_keys=True))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
