"""Pinned OCI recovery suite and bounded actual cgroup drill; no deployment."""
import base64
import hashlib
import json
import lzma
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import subprocess
import sys
import zipfile

PARENT = 'b66f2d72cd755a8aa6b4d74da35f24620f71cebb'
OLD = '4983b4a2d503e843bb18fc4209087f06e8bf1d9d'
PARTS = ('30dfc57c3949330161102647bb76d52f758a5c49', '5bacca6482ade06bbb6a22572267b68d36d159dc',
         'e1a1badfe61d7455ee703c1f8ed58921164b77b3', '6628be1146ee059b47a4c158a1877b4b9374cb30')
DELTA = '73936e6f17431563591da6550ada31e39d3bd2e1e62ba9b60fd16bbcdcb95529'
MAP = '9ae2a27181563bacaa57092a81d66a6866c1eb7e4c5508713b274da588841e5c'
ROOT_FILES = {
 'python/merlin/hermes_process.py': 'e89c80659172b22f6db73dbe00abc880aa80bf4e4895801c5501a59b7fbd08b3',
 'python/merlin/hermes_systemd.py': '8fbf73d563745aea28f227f14fec9fa78d5c03a46bc0a4889cacbf333a211cf0',
 'scripts/merlin/oci_cgroup_drill.py': '578fbba1e8ac8dc081e8a9a7734310be6e85bcc7278c1bf92c9fa6a2794367b3'}
ENV = {'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C.UTF-8'}


def sha(raw): return hashlib.sha256(raw).hexdigest()
def git(raw): return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()


def unique(pairs):
    result={}
    for key,value in pairs:
        if key in result: raise ValueError('duplicate JSON field')
        result[key]=value
    return result


def blob(api, identity, limit=1024*1024):
    obj=api('git/blobs/'+identity)
    if obj.get('sha')!=identity or obj.get('encoding')!='base64' or type(obj.get('size')) is not int or not 0<=obj['size']<=limit:
        raise ValueError('bounded exact blob required')
    raw=base64.b64decode(''.join(obj['content'].split()),validate=True)
    if len(raw)!=obj['size'] or git(raw)!=identity: raise ValueError('blob bytes differ')
    return raw


def apply(files,packed):
    if len(packed)!=16216 or sha(packed)!=DELTA: raise ValueError('fixed delta identity differs')
    decoder=lzma.LZMADecompressor(memlimit=128*1024*1024)
    raw=decoder.decompress(packed,max_length=67076)
    if len(raw)!=67075 or not decoder.eof or decoder.unused_data: raise ValueError('delta expansion differs')
    delta=json.loads(raw,object_pairs_hook=unique)
    if set(delta)!={'schema','parent_source','changes'} or delta['schema']!='merlin-fixed-recovery-lines/1' or delta['parent_source']!=PARENT or len(delta['changes'])!=12:
        raise ValueError('delta schema or scope differs')
    files=dict(files)
    for name,change in delta['changes'].items():
        path=PurePosixPath(name)
        if path.is_absolute() or any(x in ('','.','..') for x in name.split('/')) or '\\' in name: raise ValueError('unsafe source path')
        if set(change)!={'before','after','git_blob','line_edits'}: raise ValueError('delta record differs')
        before=files.get(name,b'')
        if sha(before)!=change['before']: raise ValueError('preimage differs')
        lines=before.decode().splitlines(keepends=True);last=0
        for edit in change['line_edits']:
            if not isinstance(edit,list) or len(edit)!=3 or type(edit[0]) is not int or type(edit[1]) is not int or not isinstance(edit[2],str) or not last<=edit[0]<=edit[1]<=len(lines): raise ValueError('invalid line edit')
            last=edit[1]
        for start,end,text in reversed(change['line_edits']): lines[start:end]=text.splitlines(keepends=True)
        body=''.join(lines).encode()
        if sha(body)!=change['after'] or git(body)!=change['git_blob']: raise ValueError('postimage differs')
        files[name]=body
    mapping={name:sha(body) for name,body in sorted(files.items())}
    if len(files)!=109 or sha(json.dumps(mapping,sort_keys=True,separators=(',',':')).encode())!=MAP:
        raise ValueError('complete source map differs')
    return files


def service():
    r=subprocess.run(['/usr/bin/systemctl','show','merlin-dot-private.service',
        '--property=ActiveState,SubState,MainPID,UnitFileState'],env=ENV,cwd='/',capture_output=True,text=True,timeout=5)
    if r.returncode: raise RuntimeError('production metadata inspection failed')
    return dict(line.split('=',1) for line in r.stdout.splitlines() if '=' in line)


# Only the three reviewed module hashes below may execute with host privilege.
# Bytes arrive over stdin, are fully checked, then loaded from memory. No runner
# working directory or runner-writable package is ever imported as root.
ROOT_BOOTSTRAP = '''import base64,hashlib,json,os,sys,tempfile,types
from pathlib import Path
if os.geteuid()!=0: raise RuntimeError('existing host privilege required')
raw=sys.stdin.buffer.read(65537)
if len(raw)>65536: raise ValueError('fixed source input ceiling')
files=json.loads(raw)
pins={"python/merlin/hermes_process.py":"e89c80659172b22f6db73dbe00abc880aa80bf4e4895801c5501a59b7fbd08b3","python/merlin/hermes_systemd.py":"8fbf73d563745aea28f227f14fec9fa78d5c03a46bc0a4889cacbf333a211cf0","scripts/merlin/oci_cgroup_drill.py":"578fbba1e8ac8dc081e8a9a7734310be6e85bcc7278c1bf92c9fa6a2794367b3"}
if set(files)!=set(pins): raise ValueError('fixed source keys differ')
verified={}
for path,expected in pins.items():
 body=base64.b64decode(files[path],validate=True)
 if hashlib.sha256(body).hexdigest()!=expected: raise ValueError('privileged source pin differs')
 verified[path]=body
os.environ.clear();os.environ.update({'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C.UTF-8'})
pkg=types.ModuleType('merlin');pkg.__path__=[];sys.modules['merlin']=pkg
for name,path in [('merlin.hermes_process','python/merlin/hermes_process.py'),('merlin.hermes_systemd','python/merlin/hermes_systemd.py'),('merlin_cgroup_drill','scripts/merlin/oci_cgroup_drill.py')]:
 mod=types.ModuleType(name);mod.__file__='verified-memory:'+path;mod.__package__=name.rpartition('.')[0];sys.modules[name]=mod
 exec(compile(verified[path],mod.__file__,'exec'),mod.__dict__)
with tempfile.TemporaryDirectory(prefix='merlin-cgroup-results-',dir='/run') as temp:
 report=sys.modules['merlin_cgroup_drill'].run(temp)
 print('CGROUP_REPORT='+json.dumps(report,sort_keys=True),flush=True)
sys.exit(0 if report['status']=='succeeded' else 1)
'''


def run(api,output):
    report={'schema':'merlin-recovery-validation/1','parent_source_commit':PARENT,
        'source_map_sha256':MAP,'run_id':os.environ['GITHUB_RUN_ID'],'workflow_commit':os.environ['GITHUB_SHA'],
        'runner':os.environ['RUNNER_NAME'],'python':sys.version,'architecture':platform.machine(),
        'production_service_modified':False,'private_state_accessed':False,'grants_modified':False,
        'avrea_used':False,'qualification':False,'promotion_authority':False}
    try:
        prior={};exec(compile(blob(api,OLD,32000),'pinned-parent-controller','exec'),prior)
        assembly={};exec(compile(blob(api,prior['PRIOR'],32000),'pinned-original-assembly','exec'),assembly)
        baseline,_=assembly['assemble']({n:blob(api,i) for n,(i,_) in assembly['PINS'].items()})
        parent=prior['apply_delta'](baseline,b''.join(blob(api,i,4500) for i in prior['PARTS']))
        files=apply(parent,b''.join(blob(api,i,4500) for i in PARTS))
        name='scripts/merlin/oci_cgroup_drill.py'
        old=files[name]
        if sha(old)!='962c6bbbf6a524e62671a77b58549ad152ffa5c9eecfb0d077dc79618d75608b': raise ValueError('drill preimage differs')
        files[name]=old.replace(b"['/usr/bin/systemd','--version']",b"['/usr/bin/systemctl','--version']")
        if sha(files[name])!='578fbba1e8ac8dc081e8a9a7734310be6e85bcc7278c1bf92c9fa6a2794367b3': raise ValueError('drill path repair postimage differs')
        final_map=sha(json.dumps({n:sha(b) for n,b in sorted(files.items())},sort_keys=True,separators=(',',':')).encode())
        if final_map!='2bcc937d57e8bc95da422cf204284d359e1ddfa20f830a5e6021cfba8a8b4779': raise ValueError('repaired full source map differs')
        report['source_map_sha256']=final_map
        root=output/'source';root.mkdir(mode=0o700)
        for name,body in files.items():
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True)
            with path.open('xb') as stream:stream.write(body)
        manifest={'schema':'merlin-recovery-source/1','parent_source_commit':PARENT,
            'files':{n:sha(b) for n,b in sorted(files.items())},'git_blobs':{n:git(b) for n,b in sorted(files.items())},
            'source_map_sha256':final_map,'qualification':False,'promotion_authority':False}
        encoded=(json.dumps(manifest,sort_keys=True,indent=2)+'\n').encode()
        (output/'source-manifest.json').write_bytes(encoded)
        with zipfile.ZipFile(output/'tested-source.zip','w',zipfile.ZIP_DEFLATED) as z:
            for name,body in sorted({**files,'manifest.json':encoded}.items()):
                info=zipfile.ZipInfo(name,(2026,11,20,0,0,0));info.external_attr=0o100644<<16;info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,body)
        report['source_package_sha256']=sha((output/'tested-source.zip').read_bytes())
        code="import sys,json,unittest;from pathlib import Path;p=Path(sys.argv[1]);sys.path[:0]=[str(p/'python'),str(p),str(p/'tests')];s=unittest.defaultTestLoader.discover(str(p/'tests'),pattern='test_*.py');r=unittest.TextTestRunner(verbosity=2).run(s);v={'tests':r.testsRun,'errors':len(r.errors),'failures':len(r.failures),'skipped':len(r.skipped),'passed':r.wasSuccessful() and not r.skipped and r.testsRun==281};print('RESULT='+json.dumps(v,sort_keys=True));sys.exit(0 if v['passed'] else 1)"
        result=subprocess.run(['/usr/bin/python3','-I','-B','-c',code,str(root)],cwd=root,env=ENV,capture_output=True,text=True,timeout=210)
        (output/'tests.txt').write_text(result.stdout+result.stderr)
        lines=[s[7:] for s in result.stdout.splitlines() if s.startswith('RESULT=')]
        report['tests']=json.loads(lines[-1]) if lines else {'passed':False}
        if result.returncode or report['tests'].get('passed') is not True:raise RuntimeError('recovery suite failed')
        negative=output/'negative';shutil.copytree(root,negative)
        for name in ('python/merlin/branch_registry.py','python/merlin/hermes_worker.py','python/merlin/hypothesis_ledger.py'):
            (negative/name).write_bytes(parent[name])
        code="import sys,json,unittest;p=sys.argv[1];sys.path[:0]=[p+'/python',p,p+'/tests'];s=unittest.defaultTestLoader.loadTestsFromNames(['test_production_runtime_boundaries.LedgerConnectionLifetimeTests','test_production_runtime_boundaries.WorkerBoundaryTests']);r=unittest.TextTestRunner(verbosity=2).run(s);v={'tests':r.testsRun,'errors':len(r.errors),'failures':len(r.failures),'skipped':len(r.skipped)};print('NEGATIVE='+json.dumps(v,sort_keys=True));sys.exit(0 if v=={'tests':5,'failures':5,'errors':0,'skipped':0} else 1)"
        result=subprocess.run(['/usr/bin/python3','-I','-B','-c',code,str(negative)],cwd=negative,env=ENV,capture_output=True,text=True,timeout=30)
        (output/'negative-controls.txt').write_text(result.stdout+result.stderr)
        report['original_code_controls_passed']=result.returncode==0
        if result.returncode:raise RuntimeError('original-code controls did not reproduce expected defects')
        report['service_before']=service()
        if report['service_before'].get('ActiveState')!='active':raise RuntimeError('existing production service not active before drill')
        payload=json.dumps({n:base64.b64encode(files[n]).decode() for n in ROOT_FILES}).encode()
        if len(payload)>65536:raise ValueError('privileged payload ceiling')
        try:
            result=subprocess.run(['/usr/bin/sudo','-n','/usr/bin/python3','-I','-B','-S','-c',ROOT_BOOTSTRAP],
                input=payload,cwd='/',env=ENV,capture_output=True,timeout=90)
            text=result.stdout.decode('utf-8',errors='replace')
            (output/'cgroup-execution.txt').write_bytes(result.stdout+b'\nSTDERR\n'+result.stderr)
            lines=[s[len('CGROUP_REPORT='):] for s in text.splitlines() if s.startswith('CGROUP_REPORT=')]
            drill=json.loads(lines[-1]) if lines else {'status':'failed','reason':'no kernel drill receipt','returncode':result.returncode}
            (output/'cgroup-report.json').write_text(json.dumps(drill,indent=2,sort_keys=True)+'\n')
            report['cgroup_drill']={k:v for k,v in drill.items() if k!='cases'}
        finally:
            report['service_after']=service()
        report['service_unchanged']=report['service_before']==report['service_after']
        if not report['service_unchanged']:raise RuntimeError('production service metadata changed during drill')
        if result.returncode or drill.get('status')!='succeeded' or drill.get('tests')!=8:raise RuntimeError('live kernel drill not accepted')
        report['status']='succeeded'
    except Exception as exc:
        report.update(status='failed',error_class=type(exc).__name__,message=str(exc)[:1500])
    (output/'report.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps(report,indent=2,sort_keys=True))
    if report['status']!='succeeded':raise RuntimeError('fixed production-recovery acceptance failed')
    return report
