"""Fixed zero-inference retained-response assessment; preserve both failed generations."""
import ast
from dataclasses import asdict
from datetime import datetime,timezone
import hashlib
import io
import json
import os
from pathlib import Path,PurePosixPath
import pwd
import re
import socket
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time
import zipfile
PINS={'native_validation_sha256':'782ba06ac293a86abdda480d73f4a017cc0c42690069cceedc05e70f6d786420','oracle_sha256':'73ad01b8443ab3e72ee3d54c43a75ff55104b75a3d4125cc17599cced87e9abb','retained_inputs_bytes':24509,'retained_inputs_sha256':'8f7a13740d46e2bb0150ffc365e7485ae463a1a158d2bb0221d60e424c1642f2','retained_records_sha256':'4f6655bcc146fe0ab4e8b93349c45332d674e04bf30f3f0609561c6f65822213','root_decision_sha256':'d799c4e916176b2245a76752a0984cc2ab0a6f636a98837dcdb9e74cd56dd5f7','source_commit':'761756025fb88f7e722c799ca91964e3ad24c53a','source_file_count':130,'source_map_sha256':'548194d9fddd5a587feeb5384bf6b71f9fe7cee4976dab519725251fb2ca3654','source_notes_sha256':'ad412f724f95df30077a6fb21503a5f291478a0048f762e2c16bddefdbfb7192','source_package_sha256':'31afbda693cfcbe75bdfa56a3b47571271c7a6e817fd1264a56d6f23930da4ad','worker_sha256':'7f0947df45c3239cce48dd7e112886f4ccff98dd097673d0275844d227caf8f6'}
HOST_SOURCE_LIMIT=48*1024
SESSION="merlin-exact-assessment-20261121"
PROJECT="dot-production-docs"
STATE=Path("/var/lib/merlin-dot-private/state")
CONFIG=Path("/etc/merlin-dot-private/config.json")
SOCKET=Path("/run/merlin-dot-private/tools.sock")
PROVIDER=Path("/etc/merlin-model-provider")
HOST_PREFIX="local-research/"+SESSION+"/host/"
SOLVER_PREFIX="local-solver/"+SESSION+"/"
BRANCH_PREFIX="branch-research/"+SESSION+"/"
REPORT_SOURCE_ID=SESSION+":assessment-report"
ENV={"PATH":"/usr/sbin:/usr/bin:/sbin:/bin","LANG":"C.UTF-8","PYTHONDONTWRITEBYTECODE":"1","PYTHONNOUSERSITE":"1"}
MODEL_SHA="cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046"
RUNTIME_COMMIT="2a4daf0e08d6a9b6993ee0d4a9a3cfc35a6f405c"
MODEL_BYTES=1117320768
BASELINE_SHA="72ba14b8f8b98475c3c25f885bc2edd88e05bd1d36422ab6b5e3ee20c2799798"
PROVIDER_MANIFEST_SHA="35cf7ea56185126587e7dc10bb400ec53df51057407f9920d0ab03aff4299203"
PROVIDER_BOOTSTRAP_SHA="7b7489297414d8304f12e8c0e28aec8ddd806704889f8b17986eac8ada0cba57"
NO_AUTH={"qualification":False,"promotion_authority":False}
PHASE_TIMEOUTS={"selection":90,"final":90,"replay":30}
def canonical(value):
 return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
def sha(raw):
 return hashlib.sha256(raw).hexdigest()
def unique(pairs):
 value={}
 for key,item in pairs:
  if key in value:
   raise ValueError("duplicate JSON key")
  value[key]=item
 return value
def read_regular(path,maximum,*,root_owned=False):
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC)
 try:
  before=os.fstat(fd)
  if not stat.S_ISREG(before.st_mode)or before.st_size>maximum:
   raise ValueError("bounded regular file required")
  if root_owned and(before.st_uid!=0 or before.st_mode&0o022):
   raise PermissionError("root-owned immutable host file required")
  with os.fdopen(fd,"rb",closefd=False)as stream:
   data=stream.read(maximum+1)
  after=os.fstat(fd)
  identity=lambda item:(item.st_dev,item.st_ino,item.st_size,item.st_mtime_ns,item.st_ctime_ns)
  if len(data)>maximum or identity(before)!=identity(after):
   raise ValueError("file changed while reading")
  return data
 finally:
  os.close(fd)
def hash_large(path,expected_bytes):
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC)
 try:
  before=os.fstat(fd)
  if(not stat.S_ISREG(before.st_mode)or before.st_uid!=0 or before.st_mode&0o022 or before.st_size!=expected_bytes):
   raise ValueError("fixed root-owned model size/ownership differs")
  digest=hashlib.sha256()
  with os.fdopen(fd,"rb",closefd=False)as stream:
   for chunk in iter(lambda:stream.read(256*1024),b""):
    digest.update(chunk)
  after=os.fstat(fd)
  fields=("st_dev","st_ino","st_size","st_mtime_ns","st_ctime_ns")
  if any(getattr(before,name)!=getattr(after,name)for name in fields):
   raise ValueError("model changed while hashing")
  return digest.hexdigest()
 finally:
  os.close(fd)
def service(name):
 if name not in{"merlin-model-provider.service","merlin-dot-private.service"}:
  raise ValueError("fixed unit required")
 command=["/usr/bin/systemctl","show",name,"--property=ActiveState,SubState,MainPID,User,Group,PrivateNetwork,RestrictAddressFamilies,MemoryMax,MemorySwapMax,CPUQuotaPerSecUSec,TasksMax"]
 result=subprocess.run(command,env=ENV,cwd="/",capture_output=True,timeout=8)
 if result.returncode or len(result.stdout)>8192:
  raise RuntimeError("bounded service observation failed")
 return dict(line.split("=",1)for line in result.stdout.decode().splitlines()if "=" in line)
def require_provider():
 manifest_raw=read_regular(PROVIDER/"manifest.json",16384,root_owned=True)
 bootstrap_raw=read_regular(PROVIDER/"bootstrap-receipt.json",65536,root_owned=True)
 manifest=json.loads(manifest_raw,object_pairs_hook=unique)
 bootstrap=json.loads(bootstrap_raw,object_pairs_hook=unique)
 if(manifest.get("schema")!="merlin-local-model-provider/1" or manifest.get("status")!="ready" or manifest.get("endpoint")!="http://127.0.0.1:8080/v1/chat/completions" or manifest.get("model")!="merlin-qwen-coder-1.5b-q4" or manifest.get("bootstrap_receipt_sha256")!=sha(bootstrap_raw)or manifest.get("qualification")is not False or manifest.get("promotion_authority")is not False or bootstrap.get("schema")!="merlin-local-model-bootstrap-receipt/1" or bootstrap.get("smoke",{}).get("passed")is not True):
  raise ValueError("actual accepted provider bootstrap evidence required")
 model,runtime=manifest["model_artifact"],manifest["runtime"]
 if(model.get("sha256")!=MODEL_SHA or model.get("size_bytes")!=MODEL_BYTES or runtime.get("source_commit")!=RUNTIME_COMMIT or runtime.get("source_tree_sha")!="445f2b6c9555e93c2e2c526d68497d8f47d97a1d" or runtime.get("source_archive_sha256")!="fd484b0ba95d74e0cd76ff7793f220fa3bb64bf85c9638962783d1085ee8bd28"):
  raise ValueError("provider model/runtime identity differs")
 for path in(model["path"],runtime["binary_path"]):
  if not str(Path(path).resolve()).startswith("/opt/merlin-model-provider/releases/"):
   raise ValueError("fixed versioned provider path required")
 if hash_large(model["path"],MODEL_BYTES)!=MODEL_SHA:
  raise ValueError("actual model bytes differ")
 binary_sha=sha(read_regular(runtime["binary_path"],128*1024*1024,root_owned=True))
 if binary_sha!=runtime["binary_sha256"]:
  raise ValueError("actual model runtime binary differs")
 revision="gguf:"+MODEL_SHA+";llama:"+RUNTIME_COMMIT+";bin:"+binary_sha
 if manifest["revision"]!=revision:
  raise ValueError("actual provider revision differs")
 unit=read_regular("/etc/systemd/system/merlin-model-provider.service",16384,root_owned=True)
 if sha(unit)!=manifest["service"]["unit_sha256"]:
  raise ValueError("provider unit identity differs")
 observed=service("merlin-model-provider.service")
 if(observed.get("ActiveState")!="active" or observed.get("SubState")!="running" or observed.get("MainPID")!=str(manifest["service"]["main_pid"])or observed.get("MemoryMax")!="3221225472" or observed.get("MemorySwapMax")!="0"):
  raise ValueError("provider service no longer matches actual bootstrap")
 return manifest_raw,bootstrap_raw,manifest,observed
def unzip_source(raw):
 if sha(raw)!=PINS["source_package_sha256"]:
  raise ValueError("accepted source package differs")
 files={}
 with zipfile.ZipFile(io.BytesIO(raw))as archive:
  if len(archive.infolist())!=PINS["source_file_count"]+1:
   raise ValueError("source membership count differs")
  total=0
  for item in archive.infolist():
   path=PurePosixPath(item.filename)
   mode=item.external_attr>>16
   if(item.filename in files or path.is_absolute()or ".." in path.parts or "\\" in item.filename or item.is_dir()or stat.S_ISLNK(mode)or item.compress_type not in{zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED}):
    raise ValueError("invalid source archive entry")
   total+=item.file_size
   if item.file_size>4*1024*1024 or total>4*1024*1024:
    raise ValueError("source expansion ceiling")
   files[item.filename]=archive.read(item)
 manifest=json.loads(files.pop("manifest.json"),object_pairs_hook=unique)
 actual={name:sha(body)for name,body in sorted(files.items())}
 if(actual!=manifest["files"]or sha(canonical(actual))!=PINS["source_map_sha256"]or manifest["source_commit"]!=PINS["source_commit"]or set(files)!=set(manifest["git_blobs"])):
  raise ValueError("accepted source manifest differs")
 for name,body in files.items():
  if hashlib.sha1(b"blob "+str(len(body)).encode()+b"\0"+body).hexdigest()!=manifest["git_blobs"][name]:
   raise ValueError("source Git blob differs")
 return files
def put_once(store,path,raw,media_type="application/json"):
 history=store.artifact_history(PROJECT,path)
 if history:
  if len(history)!=1:
   raise ValueError("immutable host record has multiple versions")
  ref=store.artifact_ref(PROJECT,path,version=1)
  if store.read_artifact_ref(ref,max_bytes=2*1024*1024)["content"]!=raw:
   raise ValueError("immutable host record content differs")
  return ref
 store.put_artifact(PROJECT,path,raw,media_type)
 return store.artifact_ref(PROJECT,path,version=1)
def owned_registry(owner):
 """Keep each newly written CAS object readable even if a later stage fails."""
 from merlin.project_registry import MerlinRegistry
 class HostRegistry(MerlinRegistry):
  def put_artifact(self,project_id,logical_path,content,media_type="application/octet-stream",**kwargs):
   if project_id!=PROJECT or not isinstance(content,bytes):
    raise ValueError("fixed project and immutable bytes required")
   digest=sha(content)
   path=self.blobs/digest[:2]/digest[2:]
   new_parent,new_file=not path.parent.exists(),not path.exists()
   try:
    return super().put_artifact(project_id,logical_path,content,media_type,**kwargs)
   finally:
    for target,created in((path.parent,new_parent),(path,new_file)):
     if created and target.exists():
      item=target.lstat()
      if stat.S_ISLNK(item.st_mode)or item.st_uid not in{0,owner.pw_uid}:
       raise PermissionError("new CAS custody differs")
      if target==path and sha(read_regular(path,2*1024*1024))!=digest:
       raise ValueError("new CAS object digest differs")
      if item.st_uid==0:
       os.chown(target,owner.pw_uid,owner.pw_gid,follow_symlinks=False)
 return HostRegistry(STATE)
def inventory_rows(store):
 rows=store.inventory(PROJECT)["artifacts"]
 if len(rows)>4096:
  raise ValueError("fixed registry inventory ceiling")
 return{row["logical_path"]:{key:row[key]for key in("digest","version","size_bytes")}for row in rows}
def fixed_record(store,name,digest):
 history=store.artifact_history(PROJECT,name)
 if len(history)!=1 or type(history[0]["version"])is not int or history[0]["version"]!=1:
  raise ValueError("fixed recovery record history differs")
 ref={"schema":"merlin-artifact-ref/1","project_id":PROJECT,"logical_path":name,"version":1,"sha256":digest}
 if store.artifact_ref(PROJECT,name)!=ref:
  raise ValueError("fixed recovery current reference differs")
 raw=store.read_artifact_ref(ref,max_bytes=2*1024*1024)["content"]
 if sha(raw)!=digest:
  raise ValueError("fixed recovery bytes differ")
 return raw,ref
def repair_new_objects(store,before,owner):
 after=inventory_rows(store)
 for name,old in before.items():
  if after.get(name)!=old:
   raise ValueError("pre-existing canonical artifact changed")
 changed=[]
 for name in sorted(set(after)-set(before)):
  if not(name.startswith("context/merlin/")or name.startswith("local-research/"+SESSION+"/")or name.startswith("local-solver/"+SESSION+"/")or name.startswith("branch-research/"+SESSION+"/")or name=="handoffs/"+SESSION+".json"):
   raise ValueError("unexpected canonical write scope")
  digest=after[name]["digest"]
  path=store.blobs/digest[:2]/digest[2:]
  raw=read_regular(path,2*1024*1024)
  if sha(raw)!=digest:
   raise ValueError("new canonical bytes differ")
  old_digests={row["digest"]for row in before.values()}
  old_prefixes={value[:2]for value in old_digests}
  for target in(path.parent,path):
   item=target.lstat()
   if stat.S_ISLNK(item.st_mode):
    raise ValueError("new canonical path is a symlink")
   if item.st_uid==0:
    if(target==path and digest in old_digests)or(target==path.parent and digest[:2]in old_prefixes):
     raise PermissionError("pre-existing canonical ownership is outside repair scope")
    os.chown(target,owner.pw_uid,owner.pw_gid,follow_symlinks=False)
   elif item.st_uid!=owner.pw_uid:
    raise PermissionError("unexpected new canonical ownership")
  changed.append(store.artifact_ref(PROJECT,name))
 lock=store.root/"dot-dual-coder.lock"
 if lock.exists()and lock.lstat().st_uid==0:
  if not stat.S_ISREG(lock.lstat().st_mode):
   raise ValueError("workflow lock type differs")
  os.chown(lock,owner.pw_uid,owner.pw_gid,follow_symlinks=False)
 return{"new_refs":changed,"preexisting_artifacts_unchanged":True,"owner_uid":owner.pw_uid,"new_objects":len(changed)}
def decode(raw):
 return json.loads(raw,object_pairs_hook=unique,parse_constant=lambda _:(_ for _ in()).throw(ValueError("nonfinite JSON")))
def retained_inputs(raw):
 from dot_ai_os.research_protocol import _validated_plan
 if len(raw)!=PINS["retained_inputs_bytes"]or sha(raw)!=PINS["retained_inputs_sha256"]:
  raise ValueError("retained data differs")
 data=decode(raw)
 if(data.get("schema")!="merlin-retained-assessment-inputs/2" or data.get("session_id")!=SESSION or data.get("project_id")!=PROJECT or type(data.get("required_version"))is not int or data["required_version"]!=1 or len(data.get("records",{}))!=39 or sha(canonical(data["records"]))!=data["records_sha256"]or data["records_sha256"]!=PINS["retained_records_sha256"]or sha(data["root_decision_utf8"].encode())!=PINS["root_decision_sha256"]or data["root_decision_sha256"]!=PINS["root_decision_sha256"]or data.get("qualification")is not False or data.get("promotion_authority")is not False):
  raise ValueError("assessment decision differs")
 if(sha(canonical(data["admission_static"]["native_validation"]))!=PINS["native_validation_sha256"]or data["receipt_static"]["native_validation"]!=data["admission_static"]["native_validation"]):
  raise ValueError("native data pins differ")
 plan=_validated_plan(data["research_plan"])
 if plan["source_commit"]!=PINS["source_commit"]or plan["plan_id"]!=SESSION:
  raise ValueError("assessment frame differs")
 return data
def checked_ref(store,ref,maximum=2*1024*1024):
 if(not isinstance(ref,dict)or set(ref)!={"schema","project_id","logical_path","version","sha256"}or ref["schema"]!="merlin-artifact-ref/1" or ref["project_id"]!=PROJECT or type(ref["version"])is not int or ref["version"]!=1):
  raise ValueError("invalid assessment reference")
 raw,actual=fixed_record(store,ref["logical_path"],ref["sha256"])
 alias=inventory_rows(store).get(ref["logical_path"])
 if actual!=ref or len(raw)>maximum or alias!={"digest":ref["sha256"],"version":1,"size_bytes":len(raw)}:
  raise ValueError("artifact alias or size differs")
 return raw
def preserved_records(store,data):
 rows=inventory_rows(store)
 expected=data["records"]
 old_paths={name for name in rows if any(name.startswith(prefix+sid+"/")for sid in data["generation_sessions"]for prefix in("dual-coder/","local-research/","local-solver/","branch-research/"))or name in{"handoffs/"+sid+".json" for sid in data["generation_sessions"]}}
 if old_paths!=set(expected):
  raise ValueError("unexpected or missing historical session record")
 observations={}
 for name,digest in sorted(expected.items()):
  raw,ref=fixed_record(store,name,digest)
  alias={"digest":digest,"version":1,"size_bytes":len(raw)}
  history=store.artifact_history(PROJECT,name)
  if(rows[name]!=alias or history[0]["digest"]!=digest or history[0]["size_bytes"]!=len(raw)or history[0]["previous_digest"]is not None):
   raise ValueError("historical metadata differs")
  observations[name]={"ref":ref,"size_bytes":len(raw),"current_alias":alias,"history":[{key:history[0][key]for key in("version","digest","size_bytes","previous_digest")}]}
 return{"schema":"merlin-retained-assessment-preservation/1","project_id":PROJECT,"session_id":SESSION,"records_sha256":data["records_sha256"],"records":observations,**NO_AUTH}
def report_context_base():
 return "context/merlin/"+sha(REPORT_SOURCE_ID.encode())+"/"
def fresh_assessment(store):
 if any(name.startswith(prefix)or name=="handoffs/"+SESSION+".json" for name in inventory_rows(store)for prefix in(HOST_PREFIX.rsplit("host/",1)[0],SOLVER_PREFIX,BRANCH_PREFIX,"dual-coder/"+SESSION+"/",report_context_base())):
  raise ValueError("existing assessment fences retry")
def retained_proposals(store,data):
 from dot_ai_os.local_research import _function_source
 baseline=_function_source()
 result=decode(checked_ref(store,data["a_result_ref"],32000))
 candidate=result["payload"]["candidate"]
 if(candidate!=baseline or sha(candidate.encode())!=BASELINE_SHA or len(candidate.encode())!=1281 or result.get("schema")!="dot-dual-coder-result/1"):
  raise ValueError("retained A differs from baseline")
 observed=decode(checked_ref(store,data["b_observation_ref"],64000))["observation"]
 response_raw=observed["response_utf8"].encode()
 response=decode(response_raw)
 if(response!=observed["response"]or sha(response_raw)!=observed["response_sha256"]or observed.get("inference_attempted")is not True or observed.get("inference_requests")!=1 or len(response["choices"])!=1 or response["choices"][0]["finish_reason"]!="length" or response["usage"]["completion_tokens"]!=900):
  raise ValueError("retained B evidence differs")
 rejection=dict(data["rejection_static"])
 rejection.update({"observation_ref":data["b_observation_ref"],"response_sha256":observed["response_sha256"]})
 return{"baseline":baseline,"coder_a":candidate},rejection
def assessment_authority(store,cap,check):
 check()
 data=retained_inputs(checked_ref(store,cap["retained_inputs_ref"],32000))
 preserved_records(store,data)
 for ref in cap["admitted_refs"]:
  checked_ref(store,ref,128*1024)
 admission=decode(checked_ref(store,cap["admission_ref"],32000))
 if(admission["invocation"]!=cap["invocation"]or admission["session_id"]!=SESSION or admission["host_source_sha256"]!=cap["host_source_sha256"]or admission["source_commit"]!=PINS["source_commit"]or sha(canonical(admission["native_validation"]))!=PINS["native_validation_sha256"]or admission["budget"]!=data["admission_static"]["budget"]):
  raise PermissionError("assessment admission differs")
 check()
 return data
def native_policy_allowed(policy):
 from merlin.hermes_systemd import _properties
 from dot_ai_os.local_research import WORKER_LIMITS
 return(isinstance(policy,dict)and set(policy)=={"program_sha256","unit","limits","tasks_max","isolation","compute_budget_units_enforced"}and policy["program_sha256"]==PINS["worker_sha256"]and isinstance(policy["unit"],str)and re.fullmatch(r"merlin-fixed-[0-9a-f]{32}\.service",policy["unit"])is not None and policy["limits"]==_properties(WORKER_LIMITS,8)and type(policy["tasks_max"])is int and policy["tasks_max"]==8 and policy["isolation"]=="systemd_cgroup_v2" and policy["compute_budget_units_enforced"]is False)
def branch_session(store,cap,check):
 from merlin.branch_registry import RegistryBranchSession
 from merlin.branch_research import Branch
 from dot_ai_os.research_protocol import _validated_plan
 def allowed(spec):
  assessment_authority(store,cap,check)
  return spec["executor"]["sha256"]==cap["host_source_sha256"]
 return RegistryBranchSession(store,project_id=PROJECT,session_id=SESSION,branches=(Branch("selection","Record selection measurement integrity",2),Branch("final","Record separate final measurement integrity",1,("selection",))),source_commit=PINS["source_commit"],research_plan_ref=cap["research_plan_ref"],principal="fixed-retained-assessment-host",executor_id="retained-assessment-host-v1",executor_sha256=cap["host_source_sha256"],frame_validator=_validated_plan,approval=allowed,lease=allowed)
def measure_partition(store,cap,phase,programs,process,context,check,effects):
 from dot_ai_os.local_research import WORKER_LIMITS,_oracle,_checked_outcomes
 from merlin.scientific_loop import Observation,Prediction,compare_observation
 oracle=decode(checked_ref(store,cap["oracle_ref"],32000))
 _oracle(oracle)
 cases=[case for case in oracle["cases"]if(case["split"]=="final")==(phase=="final")]
 if phase not in{"selection","final"}or len(cases)!=(12 if phase=="selection" else 6):
  raise ValueError("invalid partition")
 variants={}
 for name in("baseline","coder_a"):
  assessment_authority(store,cap,check)
  if type(process.tasks_max)is not int or process.tasks_max!=8 or effects["native_process_launches"]>=2:
   raise PermissionError("fixed two-worker phase budget required")
  payload={"schema":"merlin-solver-worker-input/1","program":programs[name],"cases":[{key:case[key]for key in("case_id","matrix","right")}for case in cases]}
  raw=canonical(payload)
  if len(raw)>65536:
   raise ValueError("worker input ceiling")
  base=SOLVER_PREFIX+phase+"/"+name+"/"
  if store.artifact_history(PROJECT,base+"input.json"):
   raise ValueError("existing worker input fences a repeated effect")
  input_ref=put_once(store,base+"input.json",raw)
  def gate(policy):
   assessment_authority(store,cap,check)
   if checked_ref(store,input_ref,65536)!=raw or process.tasks_max!=8:
    return False
   return native_policy_allowed(policy)
  assessment_authority(store,cap,check)
  try:
   receipt=process.run(raw,limits=WORKER_LIMITS,context=context,authorize=gate)
  except BaseException:
   effects["native_process_launches"]=None
   raise
  effects["native_process_launches"]+=1
  if(not isinstance(receipt,dict)or receipt.get("schema")!="merlin-systemd-process-result/1" or receipt.get("program_sha256")!=PINS["worker_sha256"]or receipt.get("input_sha256")!=sha(raw)or receipt.get("qualification")is not False or receipt.get("promotion_authority")is not False or len(canonical(receipt))>128*1024):
   raise ValueError("invalid process evidence")
  if receipt.get("status")=="completed":
   setup=receipt.get("kernel_setup")
   if(not isinstance(setup,dict)or type(setup.get("uid"))is not int or setup["uid"]<=0 or setup.get("program_sha256")!=PINS["worker_sha256"]):
    raise ValueError("actual nonroot fixed-worker setup required")
  process_ref=put_once(store,base+"process.json",canonical(receipt))
  assessment_authority(store,cap,check)
  variants[name]={"input_ref":input_ref,"process_ref":process_ref,"cases":_checked_outcomes(receipt,cases)}
 measurement={"schema":"merlin-local-solver-measurement/1","partition":phase,"oracle_ref":cap["oracle_ref"],"variants":variants,"measurement_scope":"finite_original_task_checks_and_untrusted_worker_cpu_observations",**NO_AUTH}
 measurement_ref=put_once(store,SOLVER_PREFIX+phase+"/measurement.json",canonical(measurement))
 observations={}
 for name,variant in variants.items():
  count=sum(row["passed"]is True for row in variant["cases"])
  metric=phase+"_passed"
  observation=Observation(observation_id=SESSION+":"+phase+":"+name,question="Does this exact retained program satisfy the finite original-task reference?",method="Unchanged isolated worker, exact expected Fraction outputs and equation residuals, input preservation and singular contract.",measurements={metric:count},units={metric:"cases"},uncertainty={metric:0},conditions={"partition":phase,"variant":name,"scope":"Finite cases only; no speed, memory or universal correctness claim."},source_refs=(measurement_ref["sha256"],variant["process_ref"]["sha256"],cap["oracle_ref"]["sha256"]),observed_at=datetime.now(timezone.utc).isoformat(),artifact_sha256=measurement_ref["sha256"])
  observations[name]={"observation":asdict(observation),"assessment":compare_observation(observation,[Prediction(metric,len(cases),0,"cases")])}
 observation_ref=put_once(store,SOLVER_PREFIX+phase+"/observation.json",canonical({"schema":"merlin-retained-assessment-observations/1","partition":phase,"measurement_ref":measurement_ref,"variants":observations,**NO_AUTH}))
 assessment_authority(store,cap,check)
 return measurement_ref,observation_ref
def assessment_refs(store,suffixes):
 refs={}
 for key,path in suffixes.items():
  ref=store.artifact_ref(PROJECT,path)
  checked_ref(store,ref,128*1024)
  refs[key]=ref
 return refs
def publish_report(store,cap,data,state,measurement_refs,observation_refs,check):
 from dot_ai_os.bridge import DotContextBridge
 programs,rejected=retained_proposals(store,data)
 counts,processes={},[]
 for partition,ref in measurement_refs.items():
  measurement=decode(checked_ref(store,ref,128*1024))
  counts[partition]={name:{"passed":sum(row["passed"]is True for row in entry["cases"]),"cases":len(entry["cases"])}for name,entry in measurement["variants"].items()}
  processes.extend(entry["process_ref"]for entry in measurement["variants"].values())
 passed=all(row["passed"]==row["cases"]for part in counts.values()for row in part.values())
 report=dict(data['report_static'])
 report.update({"ops_executor_sha256":cap["host_source_sha256"],"invocation":cap["invocation"],"retained_inputs_ref":cap["retained_inputs_ref"],"research_plan_ref":cap["research_plan_ref"],"proposal_a":{"status":"same_as_baseline","result_ref":data["a_result_ref"],"program_sha256":sha(programs["coder_a"].encode()),"bytes":len(programs["coder_a"].encode()),"distinct_improvement":False},"proposal_b":rejected,"measurements":counts,"measurement_refs":measurement_refs,"scientific_observation_refs":observation_refs,"process_receipt_refs":processes,"branch_state":state,"recommendation":"retain_baseline" if passed else "block_release_reference_failed"})
 raw=canonical(report)
 if len(raw)>16000:
  raise ValueError("report exceeds16000bytes")
 assessment_authority(store,cap,check)
 ref=put_once(store,SOLVER_PREFIX+"report.json",raw)
 bridge=DotContextBridge(store,project_id=PROJECT,namespaces=["merlin","expert-robot"])
 if any(path.startswith(report_context_base())or path=="handoffs/"+SESSION+".json" for path in inventory_rows(store)):
  raise ValueError("existing context fences publication")
 assessment_authority(store,cap,check)
 source=bridge.ingest(namespace="merlin",source_id=REPORT_SOURCE_ID,title=data["publication_static"]["title"],content=raw,source_url="https://github.com/Mannyspiro/expert-robot/commit/"+PINS["source_commit"],source_version=sha(raw),epistemic="local_observation",captured_at=datetime.now(timezone.utc).isoformat())
 assessment_authority(store,cap,check)
 handoff=bridge.save_handoff(SESSION,summary=data["publication_static"]["summary"],next_action=data["publication_static"]["next_action"],source_refs=[source["source_ref"]])
 checked_ref(store,source["source_ref"],16000)
 checked_ref(store,handoff["handoff_ref"],16000)
 assessment_authority(store,cap,check)
 return ref,source["source_ref"],handoff["handoff_ref"]
def execute_phase(store,cap,phase,process,context,check):
 if phase not in PHASE_TIMEOUTS:
  raise ValueError("fixed assessment phase required")
 effects={"inference_attempts":0,"inference_responses":0,"metadata_requests":0,"native_process_launches":0}
 data=assessment_authority(store,cap,check)
 programs,rejected=retained_proposals(store,data)
 session=branch_session(store,cap,check)
 state=session.status()
 expected={"selection":0,"final":1,"replay":2}[phase]
 if state["completed"]!=expected or state["reconciliation_required"]is not None:
  raise ValueError("phase state fences replay")
 if phase!="replay":
  def evaluate(branch,intent):
   if branch!=phase:
    raise ValueError("only the fixed phase branch may execute")
   mref,oref=measure_partition(store,cap,phase,programs,process,context,check,effects)
   return{"passed":True,"detail":"Complete bounded measurement evidence recorded; this integrity result is not solver improvement or qualification.","artifact_refs":[mref,oref]}
  state=session.step(evaluate,check_cancelled=check,budget=1)
  if state["completed"]!=expected+1 or effects["native_process_launches"]!=2:
   raise ValueError("expected two process receipts")
 else:
  if process is not None:
   raise ValueError("read-only replay must not receive a process adapter")
 parts=("selection",)if phase=="selection" else("selection","final")
 measurement_refs=assessment_refs(store,{p:SOLVER_PREFIX+p+"/measurement.json" for p in parts})
 observation_refs=assessment_refs(store,{p:SOLVER_PREFIX+p+"/observation.json" for p in parts})
 report_ref=source_ref=handoff_ref=None
 if phase=="final":
  report_ref,source_ref,handoff_ref=publish_report(store,cap,data,state,measurement_refs,observation_refs,check)
 elif phase=="replay":
  refs=assessment_refs(store,{"report":SOLVER_PREFIX+"report.json","source":report_context_base()+"source.txt","handoff":"handoffs/"+SESSION+".json"})
  report_ref,source_ref,handoff_ref=refs["report"],refs["source"],refs["handoff"]
  report=decode(checked_ref(store,report_ref,16000))
  if(report["branch_state"]!=state or report["measurement_refs"]!=measurement_refs or report["scientific_observation_refs"]!=observation_refs or checked_ref(store,source_ref,16000)!=canonical(report)):
   raise ValueError("report replay lineage differs")
 assessment_authority(store,cap,check)
 return{"schema":"merlin-retained-assessment-phase-result/1","session_id":SESSION,"status":"selection_recorded" if phase=="selection" else "completed_research_only","branch_state":state,"measurement_refs":measurement_refs,"observation_refs":observation_refs,"report_ref":report_ref,"report_source_ref":source_ref,"handoff_ref":handoff_ref,"effects_this_call":effects,**NO_AUTH}
def phase_main(stage,phase):
 if os.geteuid()!=0 or phase not in PHASE_TIMEOUTS:
  raise PermissionError("fixed privileged phase required")
 stage=Path(stage).resolve(strict=True)
 if not str(stage).startswith("/run/merlin-research-")or stage.stat().st_uid!=0:
  raise PermissionError("root-owned operation stage required")
 capsule_raw=read_regular(stage/"capsule.json",32000,root_owned=True)
 cap=decode(capsule_raw)
 if(cap["source_commit"]!=PINS["source_commit"]or cap["session_id"]!=SESSION or sha(read_regular(stage/"host.py",HOST_SOURCE_LIMIT,root_owned=True))!=cap["host_source_sha256"]):
  raise ValueError("phase controller differs")
 sys.path.insert(0,str(stage/"source/python"))
 from merlin.hermes_systemd import SystemdFixedPythonProcess
 from merlin.hermes_worker import TaskExecutionContext
 from dot_ai_os.private_runtime import PrivateReadOnlyRegistry
 def check():
  if(time.time()>=cap["deadline_epoch"]or read_regular(stage/"capsule.json",32000,root_owned=True)!=capsule_raw or sha(read_regular(CONFIG,16000,root_owned=True))!=cap["config_sha256"]or sha(read_regular(PROVIDER/"manifest.json",16384,root_owned=True))!=PROVIDER_MANIFEST_SHA or sha(read_regular(PROVIDER/"bootstrap-receipt.json",65536,root_owned=True))!=PROVIDER_BOOTSTRAP_SHA):
   raise InterruptedError("lease or host binding changed")
 check()
 store=PrivateReadOnlyRegistry(STATE)if phase=="replay" else owned_registry(pwd.getpwnam("merlin-dot"))
 before=inventory_rows(store)
 db_before=sha(read_regular(store.db_path,16*1024*1024))
 context=TaskExecutionContext(task_id=SESSION,hypothesis_id="retained-exact-solver-assessment",resource_budget={"cpu_cores":2,"memory_bytes":4*1024**3,"max_wall_seconds":240,"compute_budget_units":1},approval_ref=cap["admission_ref"]["sha256"],lease_ref=sha(canonical(cap["invocation"])),artifact_refs=tuple(cap["admitted_refs"]),idempotency_key=SESSION,deadline_epoch=cap["deadline_epoch"],emit_progress=lambda*args:None,emit_tool_event=lambda*args:None,heartbeat=check,check_cancelled=check)
 process=None if phase=="replay" else SystemdFixedPythonProcess(stage/"source/python/dot_ai_os/fixed_solver_worker.py",PINS["worker_sha256"],tasks_max=8)
 started=time.monotonic()
 result=execute_phase(store,cap,phase,process,context,check)
 after=inventory_rows(store)
 observation={"before_inventory_sha256":sha(canonical(before)),"after_inventory_sha256":sha(canonical(after)),"database_before_sha256":db_before,"database_after_sha256":sha(read_regular(store.db_path,16*1024*1024)),"new_artifact_refs":[store.artifact_ref(PROJECT,name)for name in sorted(set(after)-set(before))]}
 if phase=="replay" and(before!=after or observation["database_after_sha256"]!=db_before):
  raise ValueError("read-only replay changed canonical state")
 (stage/(phase+".json")).write_bytes(canonical({"schema":"merlin-retained-assessment-phase/1","phase":phase,"pid":os.getpid(),"elapsed_seconds":time.monotonic()-started,"registry_observation":observation,"result":result}))
def private_call(source_root,tool,arguments):
 if tool not in{"rsi_status","context_fetch","session_handoff"}:
  raise ValueError("fixed private read required")
 request={"schema":"merlin-private-call/1","request_id":"assessment-read","tool":tool,"arguments":arguments}
 code=("import sys,json;sys.path.insert(0,sys.argv[1]);from dot_ai_os.private_runtime import call_socket;" "r=call_socket('/run/merlin-dot-private/tools.sock',json.loads(sys.argv[3])," "expected_server_uid=int(sys.argv[2]));print(json.dumps(r,sort_keys=True))")
 owner,caller=pwd.getpwnam("merlin-dot"),pwd.getpwnam("opc")
 result=subprocess.run(["/usr/sbin/runuser","-u","opc","--","/usr/bin/python3","-I","-B","-S","-c",code,str(source_root/"python"),str(owner.pw_uid),canonical(request).decode()],env=ENV,cwd="/",capture_output=True,timeout=30)
 if result.returncode or len(result.stdout)>65536:
  raise RuntimeError("bounded private read failed")
 value=decode(result.stdout)
 if value.get("ok")is not True:
  raise RuntimeError("actual private read rejected: "+str(value.get("error")))
 return{"caller_uid":caller.pw_uid,"server_uid":owner.pw_uid,"transport":"SO_PEERCRED Unix socket","tool":tool,"arguments":arguments,"result":value["result"],"result_sha256":sha(canonical(value["result"]))}
def old_statuses(source_root,data):
 rows={sid:private_call(source_root,"rsi_status",{"session_id":sid})for sid in data["generation_sessions"]}
 if any(row["result"].get("status")!="incomplete" or row["result_sha256"]!=data["old_status_sha256"][sid]for sid,row in rows.items()):
  raise ValueError("historical generation statuses changed")
 return rows
def report_reads(store,source_root,result):
 from dot_ai_os.bridge import DotContextBridge
 raw=checked_ref(store,result["report_ref"],16000)
 source_ref=result["report_source_ref"]
 if checked_ref(store,source_ref,16000)!=raw:
  raise ValueError("complete report source bytes differ")
 bridge=DotContextBridge(store,project_id=PROJECT,namespaces=["merlin","expert-robot"])
 arguments={"source_ref":source_ref,"start_byte":0,"length_bytes":16000}
 fetched=private_call(source_root,"context_fetch",arguments)
 handed=private_call(source_root,"session_handoff",{"session_id":SESSION})
 page=fetched["result"]
 if(page!=bridge.fetch(**arguments)or page["next_start_byte"]is not None or page["text"].encode()!=raw or page["excerpt_sha256"]!=sha(raw)or handed["result"]!=bridge.load_handoff(SESSION)or handed["result"]["handoff_ref"]!=result["handoff_ref"]or handed["result"]["handoff"]["source_refs"]!=[source_ref]):
  raise ValueError("private context/handoff differs")
 return{"context_fetch":fetched,"session_handoff":handed}
def validate_phase_outcomes(phases,private_reads):
 if set(phases)!=set(PHASE_TIMEOUTS)or set(private_reads)!={"final","replay"}:
  raise ValueError("missing assessment phase or read")
 if len({row["pid"]for row in phases.values()})!=3:
  raise ValueError("phase PIDs must differ")
 for phase,launches in(("selection",2),("final",2),("replay",0)):
  result=phases[phase]["result"]
  if result["effects_this_call"]!={"native_process_launches":launches,"inference_attempts":0,"inference_responses":0,"metadata_requests":0}:
   raise ValueError("assessment effects differ")
 final,replay=(phases[key]["result"]for key in("final","replay"))
 if({key:value for key,value in final.items()if key!="effects_this_call"}!={key:value for key,value in replay.items()if key!="effects_this_call"}or private_reads["final"]!=private_reads["replay"]):
  raise ValueError("replay result differs")
 observed=phases["replay"]["registry_observation"]
 if(observed["new_artifact_refs"]!=[]or observed["before_inventory_sha256"]!=observed["after_inventory_sha256"]or observed["database_before_sha256"]!=observed["database_after_sha256"]):
  raise ValueError("replay canonical writes were observed")
def export_episode(store,before,output):
 exported,total={},0
 for name in sorted(set(inventory_rows(store))-set(before)):
  if not(name.startswith(HOST_PREFIX)or name.startswith(SOLVER_PREFIX)or name.startswith(BRANCH_PREFIX)or name.startswith(report_context_base())or name=="handoffs/"+SESSION+".json"):
   raise ValueError("unexpected assessment export path")
  ref=store.artifact_ref(PROJECT,name)
  raw=checked_ref(store,ref)
  total+=len(raw)
  if total>4*1024*1024 or len(exported)>=256:
   raise ValueError("bounded exact assessment export required")
  exported[name]={"ref":ref,"content":raw.decode()}
 (output/"episode-artifacts.json").write_bytes(canonical({"schema":"merlin-exact-episode-export/1","project_id":PROJECT,"session_id":SESSION,"artifacts":exported}))
def finish_assessment(store,before,owner,output,data):
 original,failures=sys.exc_info()[1],{}
 def retain_preservation():
  (output/"preservation-after.json").write_bytes(canonical(preserved_records(store,data)))
 for name,action in(("preservation",retain_preservation),("custody",lambda:repair_new_objects(store,before,owner)),("export",lambda:export_episode(store,before,output))):
  try:
   action()
  except Exception as error:
   failures[name]={"type":type(error).__name__,"message":str(error)[:500]}
 if failures:
  raw=canonical({"original_error":None if original is None else{"type":type(original).__name__,"message":str(original)[:500]},"cleanup_errors":failures})
  try:
   (output/"cleanup-errors.json").write_bytes(raw)
  except Exception:
   if original is None:
    raise
   sys.stderr.write(raw.decode()+"\n")
  if original is None:
   raise RuntimeError("assessment cleanup failed")
def root_run(incoming,output):
 previous_umask=os.umask(0o022)
 try:
  return _root_run(incoming,output)
 finally:
  os.umask(previous_umask)
def _root_run(incoming,output):
 """One fixed operation; source and assets arrive through the pinned runner loader."""
 if os.geteuid()!=0 or socket.gethostname()!="cace-oci-a1":
  raise PermissionError("intended privileged host supervisor required")
 incoming,output=Path(incoming).resolve(strict=True),Path(output).resolve(strict=True)
 runner=pwd.getpwnam("opc")
 if incoming!=output or incoming.stat().st_uid!=runner.pw_uid:
  raise PermissionError("one runner-owned operation output directory required")
 native_raw=read_regular(incoming/"tested-source.zip",4*1024*1024)
 files=unzip_source(native_raw)
 oracle_raw=read_regular(incoming/"oracle.json",32000)
 notes_raw=read_regular(incoming/"source-notes.json",32000)
 if sha(oracle_raw)!=PINS["oracle_sha256"]or sha(notes_raw)!=PINS["source_notes_sha256"]:
  raise ValueError("independent reference/source notes differ")
 invocation_raw=read_regular(incoming/"invocation.json",4096)
 invocation=json.loads(invocation_raw,object_pairs_hook=unique)
 if(set(invocation)!={"request_id","run_id","run_attempt","workflow_commit"}or not re.fullmatch(r"[0-9a-f-]{36}",invocation["request_id"])or type(invocation["run_id"])is not int or invocation["run_attempt"]!=1 or not re.fullmatch(r"[0-9a-f]{40}",invocation["workflow_commit"])):
  raise ValueError("fixed one-attempt operation identity required")
 manifest_raw,bootstrap_raw,provider,provider_live=require_provider()
 if sha(manifest_raw)!=PROVIDER_MANIFEST_SHA or sha(bootstrap_raw)!=PROVIDER_BOOTSTRAP_SHA:
  raise ValueError("exact accepted provider files differ")
 config_raw=read_regular(CONFIG,16000,root_owned=True)
 if sha(config_raw)!="a25921442e2d3e463ccd685de6c67d824140b8c1592ab4fe942fb50c5d3b22e8":
  raise ValueError("existing project and access configuration changed")
 config=json.loads(config_raw,object_pairs_hook=unique)
 if(config["project_id"]!=PROJECT or config["namespaces"]!=["merlin","expert-robot"]or len(config["grants"])!=1 or config["grants"][0]["uid"]!=runner.pw_uid or config["grants"][0]["principal"]!="local-runner-opc" or not{"rsi_status","context_fetch","session_handoff"}<=set(config["grants"][0]["tools"])):
  raise ValueError("canonical host binding differs")
 private_before=service("merlin-dot-private.service")
 if(private_before.get("ActiveState")!="active" or private_before.get("SubState")!="running" or private_before.get("PrivateNetwork")!="yes" or private_before.get("RestrictAddressFamilies")!="AF_UNIX"):
  raise ValueError("existing private service profile differs")
 owner=pwd.getpwnam("merlin-dot")
 if STATE.is_symlink()or STATE.stat().st_uid!=owner.pw_uid:
  raise ValueError("existing canonical state ownership differs")
 db_path=STATE/"merlin.sqlite3"
 header=read_regular(db_path,16*1024*1024)[:100]
 if header[:16]!=b"SQLite format 3\x00" or header[18:20]!=b"\x01\x01":
  raise ValueError("existing non-WAL registry required")
 backups=STATE.parent/"backups"
 backups.mkdir(mode=0o700,exist_ok=True)
 if backups.is_symlink()or backups.stat().st_uid!=0:
  raise ValueError("root-owned backup directory required")
 backup_path=backups/("before-research-"+invocation["request_id"]+".sqlite3")
 if backup_path.exists():
  raise ValueError("operation already has a preserved pre-write snapshot")
 began=time.monotonic()
 with sqlite3.connect(db_path.as_uri()+"?mode=ro",uri=True,timeout=2)as source:
  with sqlite3.connect(backup_path)as target:
   def backup_progress(status,remaining,total):
    if time.monotonic()-began>10:
     raise TimeoutError("bounded pre-write backup timed out")
   source.backup(target,pages=64,progress=backup_progress)
 backup_path.chmod(0o600)
 backup_sha=sha(read_regular(backup_path,16*1024*1024,root_owned=True))
 (output/"intent.json").write_bytes(canonical({"schema":"merlin-retained-assessment-intent/1","session_id":SESSION,"invocation":invocation,"source_commit":PINS["source_commit"],"source_map_sha256":PINS["source_map_sha256"],"backup_sha256":backup_sha,"external_model_budget_usd":0,"provider_manifest_sha256":sha(manifest_raw),"oracle_sha256":sha(oracle_raw),"no_automatic_retry_after_ambiguous_intent":True}))
 with tempfile.TemporaryDirectory(prefix="merlin-research-",dir="/run")as temporary:
  stage=Path(temporary);stage.chmod(0o755)
  source_root=stage/"source"
  for name,body in files.items():
   path=source_root/name
   path.parent.mkdir(parents=True,exist_ok=True)
   path.write_bytes(body);path.chmod(0o444)
  script=read_regular(incoming/"research_episode_host.py",HOST_SOURCE_LIMIT)
  if sha(script)!=_HOST_SOURCE_SHA256:
   raise ValueError("privileged host source differs")
  (stage/"host.py").write_bytes(script);(stage/"host.py").chmod(0o444)
  sys.path.insert(0,str(source_root/"python"))
  store=owned_registry(owner)
  input_raw=read_regular(incoming/"retained-inputs.json",32000)
  data=retained_inputs(input_raw)
  fresh_assessment(store)
  preserved_before=preserved_records(store,data)
  old_before=old_statuses(source_root,data)
  before=inventory_rows(store)
  try:
   (output/"preservation-before.json").write_bytes(canonical(preserved_before))
   (output/"old-generation-status-before.json").write_bytes(canonical(old_before))
   refs={}
   for key,filename,raw in(("retained_inputs_ref","retained-inputs.json",input_raw),("research_plan_ref","research-plan.json",canonical(data["research_plan"])),("oracle_ref","oracle.json",oracle_raw),("source_notes_ref","source-notes.json",notes_raw),("provider_manifest_ref","provider-manifest.json",manifest_raw),("provider_bootstrap_ref","provider-bootstrap.json",bootstrap_raw)):
    refs[key]=put_once(store,HOST_PREFIX+filename,raw)
   admission=dict(data['admission_static'])
   admission.update({"invocation":invocation,"host_source_sha256":_HOST_SOURCE_SHA256,"artifact_refs":list(refs.values()),"root_decision_sha256":data["root_decision_sha256"]})
   admission_ref=put_once(store,HOST_PREFIX+"admission.json",canonical(admission))
   cap={"source_commit":PINS["source_commit"],"session_id":SESSION,"invocation":invocation,"host_source_sha256":_HOST_SOURCE_SHA256,**refs,"admission_ref":admission_ref,"admitted_refs":list(refs.values())+[admission_ref],"config_sha256":sha(config_raw),"deadline_epoch":time.time()+240}
   (stage/"capsule.json").write_bytes(canonical(cap));(stage/"capsule.json").chmod(0o600)
   repair_new_objects(store,before,owner)
   phases,reads={},{}
   for phase,timeout in PHASE_TIMEOUTS.items():
    prior=inventory_rows(store)
    try:
     child=subprocess.run(["/usr/bin/python3","-I","-B","-S",str(stage/"host.py"),"--phase",str(stage),phase],env=ENV,cwd="/",capture_output=True,timeout=timeout)
     if len(child.stdout)+len(child.stderr)>65536:
      raise ValueError("phase diagnostics ceiling")
     (output/(phase+"-process.txt")).write_bytes(child.stdout+child.stderr)
     if child.returncode:
      raise RuntimeError("fixed assessment phase failed: "+phase)
     raw=read_regular(stage/(phase+".json"),128*1024,root_owned=True)
     phases[phase]=decode(raw)
     (output/(phase+".json")).write_bytes(raw)
    finally:
     repair_new_objects(store,prior,owner)
    if phase!="selection":
     reads[phase]=report_reads(store,source_root,phases[phase]["result"])
     (output/(phase+"-private-reads.json")).write_bytes(canonical(reads[phase]))
   validate_phase_outcomes(phases,reads)
   old_after=old_statuses(source_root,data)
   preserved_after=preserved_records(store,data)
   if old_before!=old_after or preserved_before!=preserved_after:
    raise ValueError("historical records or statuses changed")
   (output/"preservation-after.json").write_bytes(canonical(preserved_after))
   (output/"old-generation-status-after.json").write_bytes(canonical(old_after))
   private_after=service("merlin-dot-private.service")
   final_manifest,final_bootstrap,_,provider_after=require_provider()
   if(private_after!=private_before or provider_after!=provider_live or final_manifest!=manifest_raw or final_bootstrap!=bootstrap_raw or read_regular(CONFIG,16000,root_owned=True)!=config_raw):
    raise ValueError("provider/service/config changed")
   final=phases["replay"]["result"]
   report_raw=checked_ref(store,final["report_ref"],16000)
   report=decode(report_raw)
   for filename,value in(("assessment-report-ref.json",final["report_ref"]),("report-source-ref.json",final["report_source_ref"]),("handoff-ref.json",final["handoff_ref"])):
    (output/filename).write_bytes(canonical(value))
   for filename,raw in(("assessment-report.json",report_raw),("provider-manifest.json",manifest_raw),("provider-bootstrap.json",bootstrap_raw)):
    (output/filename).write_bytes(raw)
   if report["recommendation"]!="retain_baseline":
    raise ValueError("reference failed; release blocked")
   receipt=dict(data['receipt_static'])
   receipt.update({"invocation":invocation,"retained_inputs_ref":refs["retained_inputs_ref"],"research_plan_ref":refs["research_plan_ref"],"phases":phases,"assessment_report_ref":final["report_ref"],"report_source_ref":final["report_source_ref"],"report_sha256":sha(report_raw),"report_bytes":len(report_raw),"handoff_ref":final["handoff_ref"],"private_reads":reads,"expected_context_fetch_sha256":reads["replay"]["context_fetch"]["result_sha256"],"expected_handoff_result_sha256":reads["replay"]["session_handoff"]["result_sha256"],"old_generation_status_before":old_before,"old_generation_status_after":old_after,"provider_manifest_ref":refs["provider_manifest_ref"],"provider_bootstrap_ref":refs["provider_bootstrap_ref"],"provider_revision":provider["revision"],"private_service_before":private_before,"private_service_after":private_after,"provider_service_before":provider_live,"provider_service_after":provider_after,"preservation_before_sha256":sha(canonical(preserved_before)),"preservation_after_sha256":sha(canonical(preserved_after)),"prewrite_backup_sha256":backup_sha})
   receipt_raw=canonical(receipt)
   receipt_ref=put_once(store,HOST_PREFIX+"receipt.json",receipt_raw)
   (output/"host-receipt.json").write_bytes(receipt_raw)
   (output/"host-receipt-ref.json").write_bytes(canonical(receipt_ref))
  finally:
   finish_assessment(store,before,owner,output,data)
if __name__=="__main__":
 if len(sys.argv)!=4 or sys.argv[1]!="--phase":
  raise SystemExit("fixed phase supervisor invocation required")
 phase_main(sys.argv[2],sys.argv[3])
