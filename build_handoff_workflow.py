"""Prepare pinned handoff sources; emit a workflow only for an accepted install.

The build inputs are retained native API/artifact evidence. No placeholder host
pins, browser acquisition, installation, provider or GitHub mutation is performed.
"""
import argparse
import ast
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import zipfile

ROOT=Path(__file__).resolve().parent
OPS=ROOT/'ops/merlin_research'
sys.path.insert(0,str(OPS))
import handoff_request as controller

SOURCE_FILES=('handoff_support.py','handoff_request.py','test_handoff_request.py','handoff_product_pins.json')
SOURCE_COMMIT='bc8a9b64638323791b761d26d1b7093203405626'


def identity(raw):
    return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
            'git_blob':hashlib.sha1(('blob %d\0'%len(raw)).encode()+raw).hexdigest()}


def prepare_bundle(product_source,program_path):
    product=controller.decode((OPS/'handoff_product_pins.json').read_bytes());controller.validate_product(product)
    controller.require(product['source_commit']==SOURCE_COMMIT,'reviewed published product commit required')
    files={}
    for key,name in controller.SOURCE_NAMES.items():
        path=Path(program_path) if key=='program' else Path(product_source)/product[key]['path']
        raw=path.read_bytes();controller.check_bytes(raw,product[key]);files[name]=raw
    manifest={'schema':'merlin-browser-handoff-transport/1','repository':product['repository'],
              'source_commit':product['source_commit'],'files':{name:identity(raw) for name,raw in sorted(files.items())}}
    files['manifest.json']=controller.canonical(manifest)
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,raw in sorted(files.items()):
            info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.create_system=3;info.external_attr=0o100644<<16
            info.compress_type=zipfile.ZIP_DEFLATED;archive.writestr(info,raw)
    raw=buffer.getvalue();target=ROOT/'merlin/browser-handoff-source.zip';target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists(): controller.require(target.read_bytes()==raw,'immutable prepared source bundle differs')
    else: target.write_bytes(raw)
    pin={'path':'merlin/browser-handoff-source.zip',**identity(raw),'manifest':manifest}
    (ROOT/'source-bundle-pin.json').write_text(json.dumps(pin,sort_keys=True,indent=2)+'\n')
    return product,pin


def accepted_installation(installed,api,archive_raw):
    """Bind actual successful native producer bytes to its retained API identity."""
    controller.validate_installed(installed)
    controller.require(len(archive_raw)<=128*1024*1024,'bounded native acceptance archive required')
    run=api.get('run');jobs=api.get('jobs');artifacts=api.get('artifacts')
    controller.require(type(run) is dict and run.get('id')==installed['bootstrap_run_id']
        and run.get('head_sha')==installed['bootstrap_workflow_commit']
        and run.get('status')=='completed' and run.get('conclusion')=='success'
        and run.get('repository',{}).get('full_name')=='morganaspim/Cace-app',
        'completed successful native installation run required')
    controller.require(type(jobs) is dict and jobs.get('total_count')==len(jobs.get('jobs',[]))
        and 1<=len(jobs['jobs'])<=8 and all(job.get('run_id')==run['id'] and job.get('status')=='completed'
        and job.get('conclusion')=='success' for job in jobs['jobs']), 'complete successful native jobs required')
    controller.require(type(artifacts) is dict and artifacts.get('total_count')==len(artifacts.get('artifacts',[])),
                       'complete native artifact metadata required')
    candidates=[row for row in artifacts['artifacts'] if row.get('digest')=='sha256:'+controller.digest(archive_raw)
        and row.get('size_in_bytes')==len(archive_raw) and row.get('expired') is False
        and row.get('workflow_run',{}).get('id')==run['id']]
    controller.require(len(candidates)==1,'one exact retained native acceptance artifact required')
    with zipfile.ZipFile(io.BytesIO(archive_raw)) as archive:
        names=archive.namelist()
        controller.require(len(names)==len(set(names)) and len(names)<=4096
            and sum(item.file_size for item in archive.infolist())<=256*1024*1024,'bounded unique native archive required')
        members=[name for name in names if name=='bootstrap-evidence/operation-receipt.json'
                 or name.endswith('/bootstrap-evidence/operation-receipt.json')]
        controller.require(len(members)==1 and archive.getinfo(members[0]).file_size<=4*1024*1024,
                           'one full native bootstrap receipt required')
        raw=archive.read(members[0]);receipt=controller.decode(raw)
        runtime_members=[name for name in names if name=='runtime.zip' or name.endswith('/runtime.zip')]
        controller.require(len(runtime_members)==1 and archive.getinfo(runtime_members[0]).file_size<=4*1024*1024,
                           'one bounded exact native runtime archive required')
        runtime_raw=archive.read(runtime_members[0])
    runtime_pin=receipt.get('runtime_pin')
    controller.require(type(runtime_pin) is dict and runtime_pin.get('sha256')==installed['runtime_sha256'],
                       'actual native runtime archive binding differs')
    controller.check_bytes(runtime_raw,runtime_pin)
    with zipfile.ZipFile(io.BytesIO(runtime_raw)) as runtime:
        controller.require(len(runtime.namelist())==len(set(runtime.namelist()))
            and len(runtime.namelist())<=65 and 'manifest.json' in runtime.namelist()
            and runtime.getinfo('manifest.json').file_size<=1048576,'bounded unique installed runtime manifest required')
        manifest_raw=runtime.read('manifest.json');manifest=controller.decode(manifest_raw)
    manifest_sha=controller.digest(manifest_raw)
    controller.require(manifest_sha==installed['runtime_manifest_sha256']
        and manifest.get('schema')=='merlin-browser-runtime/1'
        and manifest.get('expert_source_commit')==installed['expert_source_commit'],
        'actual installed runtime manifest pin differs')
    executable=receipt.get('native_executable',{})
    controller.require(executable.get('path')=='/usr/lib64/chromium-browser/headless_shell'
        and type(executable.get('bytes')) is int and 0<executable['bytes']<=512*1024*1024,
        'actual fixed native executable identity required')
    controller.hash_value(executable.get('sha256'))
    host={'schema':'merlin-browser-host/1','release':'/opt/merlin-public-browser/releases/'+installed['runtime_sha256'],
          'browser_uid':installed['browser_uid'],'browser_gid':installed['browser_gid'],
          'executable':executable['path'],'executable_sha256':executable['sha256'],'runtime_manifest_sha256':manifest_sha}
    controller.require(controller.digest(controller.canonical(host))==installed['host_config_sha256'],
                       'actual installed host configuration pin differs')
    controller.require(receipt.get('schema')=='merlin-browser-bootstrap/1'
        and receipt.get('status')=='installed_native_passed'
        and receipt.get('public_episode_acceptance')=='passed'
        and receipt.get('native_acceptance',{}).get('status')=='passed'
        and receipt.get('fixture',{}).get('status')=='succeeded'
        and receipt.get('fixture',{}).get('all_workers_stopped') is True,
        'actual installed native browser and public-source acceptance required')
    native=receipt['native_acceptance'];cases=native.get('public_cases')
    controller.require(native.get('schema')=='merlin-browser-native-acceptance/1'
        and native.get('caller_uid')==982 and native.get('caller_gid')==installed['opc_gid']
        and native.get('max_public_episodes')==3 and native.get('parallel_episodes')==1
        and native.get('model_calls')==0 and native.get('external_spend_usd')==0
        and native.get('unauthorized_peer')=={'uid':1000,'status':'denied'}
        and native.get('post_restart_read',{}).get('unchanged') is True
        and native.get('post_restart_read',{}).get('new_acquisition') is False
        and isinstance(cases,list) and len(cases)==3
        and {case.get('id') for case in cases}=={'database-arxiv','news-nasa','repository-openmdao'}
        and all(case.get('acceptance') is True and case.get('submit_status')=='completed'
                and type(case.get('document_status')) is int and 200<=case['document_status']<300 for case in cases),
        'actual caller, all three public sources and retained restart readback required')
    fixture=receipt.get('fixture_observation',{})
    controller.require(fixture.get('status')=='succeeded' and fixture.get('playwright')=='1.60.0'
        and isinstance(fixture.get('chromium'),str) and fixture['chromium'].startswith('156.0.8078.79')
        and fixture.get('chromium_sandbox') is True and receipt['fixture'].get('scratch_unmounted') is True,
        'actual native rendered fixture and sandbox acceptance required')
    controller.require(receipt.get('runtime_pin',{}).get('sha256')==installed['runtime_sha256']
        and receipt.get('runtime_pin',{}).get('expert_source_commit')==installed['expert_source_commit']
        and receipt.get('execution',{}).get('run_id')==run['id']
        and receipt.get('execution',{}).get('workflow_commit')==run['head_sha']
        and receipt.get('service_config_sha256')==installed['service_config_sha256']
        and receipt.get('unit_sha256')==installed['unit_sha256'], 'installed pins do not bind actual native receipt')
    for name in ('browser_uid','browser_gid','opc_gid'):
        controller.require(receipt.get('accounts',{}).get(name)==installed[name], 'actual installed account pin differs')
    controller.require(type(receipt.get('before')) is dict and bool(receipt['before'])
        and receipt['before']==receipt.get('after') and receipt.get('model_calls')==0
        and receipt.get('external_model_cost_usd')==0 and receipt.get('qualification') is False
        and receipt.get('promotion_authority') is False,'native acceptance authority or preservation differs')
    return {'run_id':run['id'],'run_attempt':run.get('run_attempt'),'workflow_commit':run['head_sha'],
            'artifact_id':candidates[0]['id'],'artifact_bytes':len(archive_raw),'artifact_sha256':controller.digest(archive_raw),
            'receipt_member':members[0],'receipt_sha256':controller.digest(raw),'status':'accepted_native_producer_tuple',
            'runtime_member':runtime_members[0],'runtime_sha256':controller.digest(runtime_raw),
            'runtime_manifest_sha256':manifest_sha,'host_config_sha256':controller.digest(controller.canonical(host)),
            'host_config_evidence':'canonical fixed producer construction from bound receipt fields and exact runtime manifest',
            'api_scope':'retained API responses supplied by coordinating agent; no independent API call by this generator'}


WRAPPER=r'''import ast,base64,hashlib,io,json,os,re,selectors,signal,subprocess,sys,time,urllib.request,zipfile
from pathlib import Path
repo=os.environ['GITHUB_REPOSITORY'];commit=os.environ['GITHUB_SHA']
if (repo!='morganaspim/Cace-app' or os.environ['GITHUB_REF']!='refs/heads/merlin/browser-operations-20261121'
    or os.environ.get('RUNNER_NAME')!='cace-oci-a1' or os.geteuid()!=1000
    or sys.version_info[:2]!=(3,9) or not re.fullmatch('[0-9a-f]{40}',commit)):
    raise RuntimeError('fixed native handoff workflow identity required')
run_id=int(os.environ['GITHUB_RUN_ID']);attempt=int(os.environ['GITHUB_RUN_ATTEMPT'])
if run_id<=0 or attempt<=0: raise RuntimeError('positive native invocation identity required')
source_pins=@@SOURCE_PINS@@
product=@@PRODUCT@@
installed=@@INSTALLED@@
bundle_pin=@@BUNDLE@@
installation_acceptance=@@ACCEPTANCE@@
clean={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C.UTF-8','LC_ALL':'C.UTF-8','HOME':'/var/empty','PYTHONDONTWRITEBYTECODE':'1'}
def unique(pairs):
    value={}
    for key,item in pairs:
        if key in value: raise ValueError('duplicate JSON field')
        value[key]=item
    return value
def decode(raw): return json.loads(raw,object_pairs_hook=unique,parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
def blob(raw): return hashlib.sha1(('blob %d\0'%len(raw)).encode()+raw).hexdigest()
def api(path):
    request=urllib.request.Request('https://api.github.com/repos/'+repo+'/'+path,
        headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(request,timeout=20) as response: raw=response.read(4*1024*1024+1)
    if len(raw)>4*1024*1024: raise RuntimeError('bounded GitHub response exceeded')
    return decode(raw)
def fetch(path):
    value=api('contents/'+path+'?ref='+commit)
    raw=base64.b64decode(''.join(value['content'].split()),validate=True)
    if blob(raw)!=value['sha']: raise RuntimeError('Git content identity differs')
    return raw,value['sha']
def check(raw,pin):
    if len(raw)!=pin['bytes'] or hashlib.sha256(raw).hexdigest()!=pin['sha256'] or blob(raw)!=pin['git_blob']:
        raise RuntimeError('pinned handoff source identity differs')
out=Path(os.environ['RUNNER_TEMP'])/('merlin-browser-handoff-%d-%d'%(run_id,attempt));out.mkdir(mode=0o700,exist_ok=False)
def fixed(argv,name,seconds,maximum=8*1024*1024):
    process=subprocess.Popen(argv,cwd='/',env=clean,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
    selector=selectors.DefaultSelector();selector.register(process.stdout,selectors.EVENT_READ)
    started=time.monotonic();deadline=started+seconds;total=0;error=None
    try:
        with (out/name).open('xb') as log:
            while selector.get_map():
                left=deadline-time.monotonic()
                if left<=0: raise TimeoutError('handoff wrapper absolute deadline')
                for key,_ in selector.select(min(.2,left)):
                    raw=os.read(key.fd,65536)
                    if not raw: selector.unregister(key.fileobj);continue
                    if total+len(raw)>maximum: raise RuntimeError('handoff output ceiling')
                    log.write(raw);log.flush();total+=len(raw)
            code=process.wait(timeout=max(.01,deadline-time.monotonic()))
            if code: raise RuntimeError('fixed handoff child exit '+str(code))
    except BaseException as exc:
        error=exc
        try: os.killpg(process.pid,signal.SIGTERM)
        except (PermissionError,ProcessLookupError): pass
        if process.poll() is None:
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: pass
        try: os.killpg(process.pid,signal.SIGKILL)
        except (PermissionError,ProcessLookupError): pass
        raise
    finally:
        selector.close();process.stdout.close()
        (out/(name+'.json')).write_text(json.dumps({'returncode':process.returncode,'elapsed_seconds':time.monotonic()-started,
            'absolute_deadline_seconds':seconds,'output_bytes':total,'error_type':type(error).__name__ if error else None},sort_keys=True,indent=2))
try:
    changed=api('commits/'+commit)['files']
    if len(changed)!=1 or changed[0]['status']!='added': raise RuntimeError('one additive handoff request required')
    path=changed[0]['filename']
    if not re.fullmatch(r'merlin/browser-handoff-requests/[0-9a-f-]{36}\.json',path): raise RuntimeError('fixed handoff request path required')
    raw,request_blob=fetch(path)
    if len(raw)>16384: raise RuntimeError('handoff request byte ceiling')
    request=decode(raw)
    if path!='merlin/browser-handoff-requests/'+request.get('request_id','')+'.json': raise RuntimeError('request filename identity differs')
    (out/'request.json').write_bytes(raw)
    for name,pin in source_pins.items():
        body,_=fetch('ops/merlin_research/'+name);check(body,pin)
        if name.endswith('.py'): ast.parse(body,feature_version=(3,9))
        (out/name).write_bytes(body)
    packed,_=fetch(bundle_pin['path']);check(packed,bundle_pin);(out/'handoff-source.zip').write_bytes(packed)
    source_dir=out/'sources';source_dir.mkdir(mode=0o700)
    with zipfile.ZipFile(io.BytesIO(packed)) as archive:
        expected={'browser_research_handoff.py','test_browser_research_handoff.py','program.json','manifest.json'}
        if len(archive.namelist())!=4 or set(archive.namelist())!=expected: raise RuntimeError('fixed source bundle inventory differs')
        manifest=decode(archive.read('manifest.json'))
        if manifest!=bundle_pin['manifest']: raise RuntimeError('fixed source bundle manifest differs')
        for name,pin in manifest['files'].items():
            if archive.getinfo(name).file_size!=pin['bytes']: raise RuntimeError('source ZIP size differs')
            body=archive.read(name);check(body,pin);(source_dir/name).write_bytes(body)
    workflow,workflow_blob=fetch('.github/workflows/merlin-browser-handoff.yml');(out/'workflow-definition.yml').write_bytes(workflow)
    (out/'source-identities.json').write_text(json.dumps({'sources':source_pins,'product':product,'installed':installed,
        'installation_acceptance':installation_acceptance,'bundle':bundle_pin,'request_git_blob':request_blob,
        'workflow_git_blob':workflow_blob,'workflow_sha256':hashlib.sha256(workflow).hexdigest()},sort_keys=True,indent=2))
    execution={'repository':repo,'ref':os.environ['GITHUB_REF'],'runner':os.environ['RUNNER_NAME'],
        'workflow_commit':commit,'run_id':run_id,'run_attempt':attempt,'python':sys.version}
    (out/'identity.json').write_text(json.dumps(execution,sort_keys=True,indent=2))
    test_code="import sys,unittest,json;sys.path.insert(0,sys.argv[1]);s=unittest.defaultTestLoader.discover(sys.argv[1],pattern='test_handoff_request.py');r=unittest.TextTestRunner(verbosity=2).run(s);print(json.dumps({'tests':r.testsRun,'errors':len(r.errors),'failures':len(r.failures),'skips':len(r.skipped)}));sys.exit(0 if r.wasSuccessful() and not r.skipped and r.testsRun==@@TEST_COUNT@@ else 1)"
    fixed(['/usr/bin/python3','-I','-B','-c',test_code,str(out)],'native-coordinator-controls.txt',40)
    support=(out/'handoff_support.py').read_bytes();source=(out/'handoff_request.py').read_bytes()
    check(support,source_pins['handoff_support.py']);check(source,source_pins['handoff_request.py'])
    root_code='import hashlib,json,signal,sys,types;support='+repr(support)+';source='+repr(source)+'\n'
    root_code+='assert hashlib.sha256(support).hexdigest()=='+repr(source_pins['handoff_support.py']['sha256'])+'\n'
    root_code+='assert hashlib.sha256(source).hexdigest()=='+repr(source_pins['handoff_request.py']['sha256'])+'\n'
    root_code+='m=types.ModuleType("handoff_support");sys.modules["handoff_support"]=m;exec(compile(support,"pinned-handoff-support","exec"),m.__dict__)\n'
    root_code+='n={"__name__":"pinned_handoff_controller"};exec(compile(source,"pinned-handoff-controller","exec"),n)\n'
    root_code+='def expire(signum,frame): raise n["OperationError"]("handoff controller absolute deadline")\nsignal.signal(signal.SIGALRM,expire);signal.alarm(130)\n'
    root_code+='answer=n["run"]('+','.join(repr(value) for value in (request,execution,installed,product,str(source_dir),str(out/'operation')))+');signal.alarm(0);print(json.dumps(answer,sort_keys=True))\n'
    if len(root_code.encode())>115000: raise RuntimeError('root handoff source argument ceiling')
    unit='merlin-browser-handoff-%d-%d.service'%(run_id,attempt)
    launch=['/usr/bin/sudo','-n','/usr/bin/systemd-run','--unit='+unit,'--quiet','--wait','--service-type=exec',
        '--property=RuntimeMaxSec=150','--property=TimeoutStopSec=15','--property=KillMode=control-group',
        '--property=MemoryMax=512M','--property=MemorySwapMax=0','--property=CPUQuota=50%','--property=TasksMax=64',
        '--property=PrivateNetwork=yes','--property=NoNewPrivileges=yes','--property=RestrictAddressFamilies=AF_UNIX',
        '--property=UMask=0022','--property=StandardOutput=journal','--property=StandardError=journal','--',
        '/usr/bin/env','-i','PATH=/usr/sbin:/usr/bin:/sbin:/bin','LANG=C.UTF-8','LC_ALL=C.UTF-8','HOME=/var/empty',
        '/usr/bin/python3','-I','-B','-c',root_code]
    (out/'root-launch-input-identity.json').write_text(json.dumps({'unit':unit,'root_code_bytes':len(root_code.encode()),
        'root_code_sha256':hashlib.sha256(root_code.encode()).hexdigest(),'maximum_argument_bytes':max(len(x.encode()) for x in launch),
        'stdio_transport':'journal; no caller descriptors forwarded through system bus'},sort_keys=True,indent=2))
    started=time.time();launch_error=None
    try: fixed(launch,'root-handoff-launch.txt',170)
    except BaseException as exc: launch_error=exc;raise
    finally:
        journal=['/usr/bin/sudo','-n','/usr/bin/timeout','--signal=TERM','--kill-after=5s','20s',
            '/usr/bin/env','-i','PATH=/usr/sbin:/usr/bin:/sbin:/bin','LANG=C.UTF-8','LC_ALL=C.UTF-8','HOME=/var/empty',
            '/usr/bin/journalctl','--no-pager','--all','--output=json',
            '--output-fields=__REALTIME_TIMESTAMP,__MONOTONIC_TIMESTAMP,_BOOT_ID,_SYSTEMD_UNIT,_PID,_COMM,MESSAGE',
            '--unit='+unit,'--since='+time.strftime('%Y-%m-%d %H:%M:%S UTC',time.gmtime(started-2)),
            '--until='+time.strftime('%Y-%m-%d %H:%M:%S UTC',time.gmtime(time.time()+2)),'--lines=4096']
        try: fixed(journal,'root-unit-journal.jsonl',30)
        except BaseException as exc:
            (out/'journal-error.json').write_text(json.dumps({'status':'failed','type':type(exc).__name__,
                'message':str(exc)[:1000],'launch_already_failed':launch_error is not None},indent=2))
            if launch_error is None: raise
    print(json.dumps({'status':'native_handoff_completed','run_id':run_id,'request_id':request['request_id'],
        'operation':request['operation'],'new_browser_calls':0,'model_calls':0,'domain_execution':'not_run'},sort_keys=True))
except BaseException as exc:
    (out/'operation-error.json').write_text(json.dumps({'status':'failed','type':type(exc).__name__,
        'message':str(exc)[:2000],'run_id':run_id,'run_attempt':attempt,'workflow_commit':commit},sort_keys=True,indent=2))
    raise
'''


def render_workflow(product,bundle,installed,acceptance):
    controller.validate_product(product)
    controller.require(controller.decode((OPS/'handoff_product_pins.json').read_bytes())==product,
                       'embedded product pins differ from pinned native source file')
    pins={}
    for name in SOURCE_FILES:
        raw=(OPS/name).read_bytes()
        if name.endswith('.py'): ast.parse(raw,feature_version=(3,9))
        pins[name]=identity(raw)
    count=sum(isinstance(node,ast.FunctionDef) and node.name.startswith('test_')
              for node in ast.walk(ast.parse((OPS/'test_handoff_request.py').read_bytes())))
    body=WRAPPER
    for name,value in {'SOURCE_PINS':pins,'PRODUCT':product,'BUNDLE':bundle,'INSTALLED':installed,
                       'ACCEPTANCE':acceptance,'TEST_COUNT':count}.items():
        body=body.replace('@@'+name+'@@',repr(value))
    controller.require('@@' not in body,'unresolved workflow field');ast.parse(body,feature_version=(3,9))
    workflow='''name: Merlin fixed retained-source research handoff

"on":
  push:
    branches: ["merlin/browser-operations-20261121"]
    paths: ["merlin/browser-handoff-requests/**"]

permissions:
  contents: read

concurrency:
  group: merlin-dot-oci-operations
  cancel-in-progress: false

jobs:
  retained-source-handoff:
    runs-on: [self-hosted, cace, oci, aarch64]
    timeout-minutes: 8
    steps:
      - name: Verify retained source admission and record typed research intake
        shell: bash
        env:
          GITHUB_TOKEN: ${{ github.token }}
        run: |
          set -euo pipefail
          python3 - <<'PYCODE'
'''+''.join('          '+line+'\n' for line in body.splitlines())+'''          PYCODE
      - name: Preserve full source, test and handoff operation evidence
        if: always()
        uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02
        with:
          name: merlin-browser-handoff-${{ github.run_id }}-${{ github.run_attempt }}
          path: ${{ runner.temp }}/merlin-browser-handoff-${{ github.run_id }}-${{ github.run_attempt }}/
          include-hidden-files: true
          retention-days: 30
          if-no-files-found: warn
'''
    return workflow,pins,count


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--product-source',type=Path,required=True)
    parser.add_argument('--program',type=Path,required=True)
    parser.add_argument('--prepare-only',action='store_true')
    parser.add_argument('--installed-pins',type=Path)
    parser.add_argument('--acceptance-artifact',type=Path)
    parser.add_argument('--acceptance-api',type=Path)
    args=parser.parse_args()
    if not args.prepare_only:
        controller.require(all((args.installed_pins,args.acceptance_artifact,args.acceptance_api)),
                           'actual accepted installation pins, primary ZIP and API evidence are required before workflow generation')
        installed=controller.decode(args.installed_pins.read_bytes())
        acceptance=accepted_installation(installed,controller.decode(args.acceptance_api.read_bytes()),args.acceptance_artifact.read_bytes())
    product,bundle=prepare_bundle(args.product_source,args.program)
    if args.prepare_only:
        print(json.dumps({'status':'source_prepared_only','workflow_emitted':False,'bundle':bundle},sort_keys=True,indent=2));return
    workflow,pins,count=render_workflow(product,bundle,installed,acceptance)
    destination=ROOT/'.github/workflows/merlin-browser-handoff.yml';destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(workflow)
    manifest={'schema':'merlin-native-handoff-workflow-publication/1','sources':pins,'product':product,
        'source_bundle':bundle,'installed':installed,'installation_acceptance':acceptance,
        'workflow':{'path':'.github/workflows/merlin-browser-handoff.yml',**identity(destination.read_bytes())},
        'native_coordinator_test_count':count,'native_handoff_test_count':23,
        'source_commit':SOURCE_COMMIT,'new_browser_calls':0,'model_calls':0,'software_installation':False,
        'request_path':'merlin/browser-handoff-requests/<UUID>.json','branch':'merlin/browser-operations-20261121',
        'root_limits':{'runtime_seconds':150,'stop_grace_seconds':15,'memory_bytes':536870912,'tasks':64,
                       'cpu_percent':50,'private_network':True,'address_families':['AF_UNIX']}}
    (ROOT/'workflow-publication-manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'status':'workflow_prepared_from_accepted_installation','workflow':manifest['workflow'],
                      'native_coordinator_tests':count,'native_handoff_tests':23},sort_keys=True,indent=2))


if __name__=='__main__': main()
