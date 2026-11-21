"""Exact EGM-inspired context integration on the approved OCI host; no deployment.

The source snapshot is an explicitly recorded overlay on a published anchor,
not a claim that the anchor contains the overlay. Only synthetic context is used.
"""
import base64
import hashlib
import io
import json
import lzma
import os
from pathlib import Path, PurePosixPath
import platform
import stat
import subprocess
import sys
import urllib.parse
import urllib.request
import zipfile

ANCHOR = '47874bc1ded7b59b167c0052564e8d6ff31daae2'
BASE_ARTIFACT = 14686982334
BASE_ARCHIVE_SHA = '26c0b9f8bbd4b76060e0697ca89533588bc6207c06cfab1fd26e65d73bd3ae46'
BASE_SOURCE_SHA = 'b1fc65bb1fa33df23a0fa54a97e5f220b2e888a6232e062a99f9fd70bd27d39f'
BASE_MAP = 'fc7560266244d6cf72a395bf7a16cfdd3a9f1e05adca5fe99741471232282935'
OVERLAY_BLOB = '5f812bd2cd21c1d46ac6a85ba128944e7763370c'
OVERLAY_SHA = '67e0bd83a5c1d33421a1d0d9f0389de65938f39ec21be72f577c4ca57283723e'
SOURCE_MAP = '15a7a2aa22675d76a9c3be6f5880dae831bf45a09d5aa959fddd21c186195384'
CHANGES = {'python/merlin/review_context.py', 'python/merlin/packet_process.py',
           'tests/test_review_context.py', 'tests/test_packet_process.py',
           'scripts/merlin/oci_review_context_drill.py'}
ENV = {'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C.UTF-8'}


def sha(raw): return hashlib.sha256(raw).hexdigest()
def git(raw): return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
def canonical(value): return json.dumps(value,sort_keys=True,separators=(',',':')).encode()

def unique(items):
    result={}
    for key,value in items:
        if key in result: raise ValueError('duplicate JSON field')
        result[key]=value
    return result


def zip_members(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        infos=z.infolist();names=[x.filename for x in infos]
        if len(names)!=len(set(names)) or len(names)>200 or sum(x.file_size for x in infos)>4*1024*1024:
            raise ValueError('archive bounds')
        result={}
        for info in infos:
            name=info.filename
            if (PurePosixPath(name).is_absolute() or any(x in ('','.','..') for x in name.split('/'))
                    or '\\' in name or info.is_dir() or info.flag_bits&1
                    or stat.S_IFMT(info.external_attr>>16) not in (0,stat.S_IFREG)):
                raise ValueError('unsafe archive member')
            result[name]=z.read(info)
        return result


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed=urllib.parse.urlparse(newurl)
        if parsed.scheme!='https': raise ValueError('non-HTTPS artifact redirect')
        result=super().redirect_request(req,fp,code,msg,headers,newurl)
        if parsed.netloc!='api.github.com':
            result.remove_header('Authorization')
        return result


def download_baseline():
    url='https://api.github.com/repos/morganaspim/Cace-app/actions/artifacts/'+str(BASE_ARTIFACT)+'/zip'
    req=urllib.request.Request(url,headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],
                                          'Accept':'application/vnd.github+json'})
    with urllib.request.build_opener(SafeRedirect()).open(req,timeout=20) as response:
        raw=response.read(600001)
    if len(raw)!=419330 or sha(raw)!=BASE_ARCHIVE_SHA: raise ValueError('baseline artifact identity differs')
    return raw


def assemble(api, output):
    raw=download_baseline();(output/'baseline-44854470610.zip').write_bytes(raw)
    artifact=zip_members(raw);source=artifact['tested-source.zip']
    if sha(source)!=BASE_SOURCE_SHA: raise ValueError('baseline source identity differs')
    members=zip_members(source);manifest=json.loads(members.pop('manifest.json'),object_pairs_hook=unique)
    if set(members)!=set(manifest['files']) or len(members)!=111: raise ValueError('baseline file set differs')
    for name,body in members.items():
        if sha(body)!=manifest['files'][name] or git(body)!=manifest['git_blobs'][name]: raise ValueError('baseline file differs')
    if sha(canonical({n:sha(b) for n,b in sorted(members.items())}))!=BASE_MAP: raise ValueError('baseline map differs')
    obj=api('git/blobs/'+OVERLAY_BLOB)
    encoded=base64.b64decode(''.join(obj['content'].split()),validate=True)
    if len(encoded)!=16781 or git(encoded)!=OVERLAY_BLOB: raise ValueError('overlay transport differs')
    packed=base64.b64decode(encoded.strip(),validate=True)
    if len(packed)!=12584 or sha(packed)!=OVERLAY_SHA: raise ValueError('overlay archive differs')
    decoder=lzma.LZMADecompressor(memlimit=128*1024*1024)
    raw=decoder.decompress(packed,max_length=51416)
    if len(raw)!=51415 or not decoder.eof or decoder.unused_data: raise ValueError('overlay expansion differs')
    overlay=json.loads(raw,object_pairs_hook=unique)
    if (set(overlay)!={'schema','parent_source','files'} or overlay['schema']!='merlin-egm-overlay/1'
            or overlay['parent_source']!=ANCHOR or set(overlay['files'])!=CHANGES): raise ValueError('overlay scope differs')
    files={**members,**{n:t.encode('utf-8') for n,t in overlay['files'].items()}}
    if len(files)!=116 or sha(canonical({n:sha(b) for n,b in sorted(files.items())}))!=SOURCE_MAP: raise ValueError('complete source map differs')
    return files


def service():
    r=subprocess.run(['/usr/bin/systemctl','show','merlin-dot-private.service',
        '--property=ActiveState,SubState,MainPID,UnitFileState'],env=ENV,cwd='/',capture_output=True,text=True,timeout=5)
    if r.returncode: raise RuntimeError('production metadata inspection failed')
    return dict(line.split('=',1) for line in r.stdout.splitlines() if '=' in line)


# Every byte is checked against the fixed complete source map before a privileged
# import. Runner-writable files and cwd are never imported by the privileged host.
ROOT_BOOTSTRAP = '''import base64,hashlib,importlib.abc,importlib.util,json,os,sys,tempfile
from pathlib import Path
if os.geteuid()!=0: raise RuntimeError('existing approved host privilege required')
raw=sys.stdin.buffer.read(4*1024*1024+1)
if len(raw)>4*1024*1024: raise ValueError('fixed source input ceiling')
obj=json.loads(raw);files={n:base64.b64decode(b,validate=True) for n,b in obj.items()}
mapping={n:hashlib.sha256(b).hexdigest() for n,b in sorted(files.items())}
checksum=hashlib.sha256(json.dumps(mapping,sort_keys=True,separators=(',',':')).encode()).hexdigest()
if len(files)!=116 or checksum!='15a7a2aa22675d76a9c3be6f5880dae831bf45a09d5aa959fddd21c186195384': raise ValueError('privileged complete source pin differs')
os.environ.clear();os.environ.update({'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C.UTF-8'})
modules={}
for path,body in files.items():
 if path.startswith(('python/merlin/','python/dot_ai_os/')) and path.endswith('.py'):
  name=path[len('python/'):-3].replace('/','.')
  package=name.endswith('.__init__');name=name[:-len('.__init__')] if package else name
  modules[name]=(path,body,package)
for name,path in [('merlin_cgroup_drill','scripts/merlin/oci_cgroup_drill.py'),('merlin_context_drill','scripts/merlin/oci_review_context_drill.py')]: modules[name]=(path,files[path],False)
class Loader(importlib.abc.MetaPathFinder,importlib.abc.Loader):
 def find_spec(self,fullname,path=None,target=None):
  if fullname in modules: return importlib.util.spec_from_loader(fullname,self,is_package=modules[fullname][2])
 def create_module(self,spec): return None
 def exec_module(self,module):
  path,body,package=modules[module.__name__];module.__file__='verified-memory:'+path
  if package:module.__path__=[]
  exec(compile(body,module.__file__,'exec'),module.__dict__)
sys.meta_path.insert(0,Loader())
import merlin_cgroup_drill,merlin_context_drill
with tempfile.TemporaryDirectory(prefix='merlin-egm-results-',dir='/run') as temp:
 kernel=merlin_cgroup_drill.run(str(Path(temp)/'kernel'))
 context=merlin_context_drill.run(str(Path(temp)/'context'),source_commit='47874bc1ded7b59b167c0052564e8d6ff31daae2')
 report={'kernel':kernel,'context':context,'fixture_frame_source_anchor':'47874bc1ded7b59b167c0052564e8d6ff31daae2','tested_source_map_sha256':checksum}
 print('EGM_LIVE_REPORT='+json.dumps(report,sort_keys=True),flush=True)
sys.exit(0 if kernel['status']=='succeeded' and context['status']=='succeeded' else 1)
'''


def run(api, output):
    report={'schema':'merlin-egm-oci-validation/1','source_anchor_commit':ANCHOR,
        'source_kind':'exact_overlay_on_published_anchor','source_map_sha256':SOURCE_MAP,
        'run_id':os.environ['GITHUB_RUN_ID'],'workflow_commit':os.environ['GITHUB_SHA'],
        'runner':os.environ['RUNNER_NAME'],'python':sys.version,'architecture':platform.machine(),
        'actual_native_model_review_performed':False,'private_context_used':False,
        'production_service_modified':False,'permissions_modified':False,'avrea_used':False,
        'qualification':False,'promotion_authority':False}
    protocol={'question':'Exact source-bound chat continuity and minimized reviewer packet through actual Hermes and OCI process',
        'software_tests':340,'kernel_cases':8,'context_worker_cases':5,'synthetic_only':True,
        'source_commit_semantics':'Research fixture binds the published anchor; the tested overlay is identified by source_map_sha256, not falsely attributed to that anchor.',
        'model_review':'Blocked until native fresh-context runtime and authenticated complete trace exist',
        'maximum_corrective_runs':2,'deployment':False}
    (output/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    try:
        files=assemble(api,output)
        root=output/'source';root.mkdir(mode=0o700)
        for name,body in files.items():
            dest=root/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(body)
        manifest={'schema':'merlin-egm-source/1','source_anchor_commit':ANCHOR,'source_kind':report['source_kind'],
            'files':{n:sha(b) for n,b in sorted(files.items())},'git_blobs':{n:git(b) for n,b in sorted(files.items())},
            'source_map_sha256':SOURCE_MAP,'qualification':False,'promotion_authority':False}
        encoded=(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode();(output/'source-manifest.json').write_bytes(encoded)
        with zipfile.ZipFile(output/'tested-source.zip','w',zipfile.ZIP_DEFLATED) as archive:
            for name,body in sorted({**files,'manifest.json':encoded}.items()):
                info=zipfile.ZipInfo(name,(2026,11,20,0,0,0));info.external_attr=0o100644<<16;info.compress_type=zipfile.ZIP_DEFLATED;archive.writestr(info,body)
        report['source_package_sha256']=sha((output/'tested-source.zip').read_bytes())
        code="import sys,json,unittest;from pathlib import Path;p=Path(sys.argv[1]);sys.path[:0]=[str(p/'python'),str(p),str(p/'tests')];s=unittest.defaultTestLoader.discover(str(p/'tests'),pattern='test_*.py');r=unittest.TextTestRunner(verbosity=2).run(s);v={'tests':r.testsRun,'errors':len(r.errors),'failures':len(r.failures),'skipped':len(r.skipped),'passed':r.wasSuccessful() and not r.skipped and r.testsRun==340};print('RESULT='+json.dumps(v,sort_keys=True));sys.exit(0 if v['passed'] else 1)"
        result=subprocess.run(['/usr/bin/python3','-I','-B','-c',code,str(root)],cwd=root,env=ENV,capture_output=True,text=True,timeout=210)
        (output/'tests.txt').write_text(result.stdout+result.stderr)
        lines=[x[7:] for x in result.stdout.splitlines() if x.startswith('RESULT=')]
        report['tests']=json.loads(lines[-1]) if lines else {'passed':False}
        if result.returncode or report['tests'].get('passed') is not True: raise RuntimeError('software suite not accepted')
        report['service_before']=service()
        if report['service_before'].get('ActiveState')!='active':raise RuntimeError('production service not active before drill')
        payload=canonical({n:base64.b64encode(b).decode() for n,b in sorted(files.items())})
        if len(payload)>4*1024*1024:raise ValueError('privileged source payload ceiling')
        try:
            result=subprocess.run(['/usr/bin/sudo','-n','/usr/bin/python3','-I','-B','-S','-c',ROOT_BOOTSTRAP],input=payload,
                env=ENV,cwd='/',capture_output=True,timeout=100)
            (output/'live-execution.txt').write_bytes(result.stdout+b'\nSTDERR\n'+result.stderr)
            lines=[x[len('EGM_LIVE_REPORT='):] for x in result.stdout.decode(errors='replace').splitlines() if x.startswith('EGM_LIVE_REPORT=')]
            live=json.loads(lines[-1]) if lines else {'status':'failed','reason':'missing live receipt','returncode':result.returncode}
            (output/'live-report.json').write_text(json.dumps(live,indent=2,sort_keys=True)+'\n')
            report['kernel']={k:v for k,v in live.get('kernel',{}).items() if k!='cases'}
            report['context']={k:v for k,v in live.get('context',{}).items() if k!='cases'}
        finally:
            report['service_after']=service()
        report['service_unchanged']=report['service_before']==report['service_after']
        if not report['service_unchanged']:raise RuntimeError('production service metadata changed')
        if (result.returncode or report['kernel'].get('passed')!=8 or report['kernel'].get('status')!='succeeded'
                or report['context'].get('passed')!=5 or report['context'].get('status')!='succeeded'):
            raise RuntimeError('actual kernel/context integration not accepted')
        report['status']='succeeded'
    except Exception as exc:
        report.update(status='failed',error_class=type(exc).__name__,message=str(exc)[:1500])
    (output/'report.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps(report,indent=2,sort_keys=True))
    if report['status']!='succeeded':raise RuntimeError('EGM integration acceptance failed')
    return report
