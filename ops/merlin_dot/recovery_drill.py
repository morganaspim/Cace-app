"""Fixed, isolated recovery drill for the two-document private Merlin demo.

Only a hash-pinned root controller may supply the helper namespace and recovery
source. No operation stops/restarts production, changes its link/config/unit,
or opens production state for writing. A new workspace preserves the snapshot,
negative fixtures and receipt. This measures a demo-registry recovery only.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile

ROOT_UID = 0
SERVICE_UID = 982
SOURCE = Path('/opt/merlin-dot-private')
STATE = Path('/var/lib/merlin-dot-private/state')
CONFIG = Path('/etc/merlin-dot-private/config.json')
UNIT = Path('/etc/systemd/system/merlin-dot-private.service')
WORKSPACE = Path('/var/lib/merlin-dot-private-recovery-drills')
RELEASE_SHA = 'efe57bada5cd86f45118cac0036faf497f9aa60972508e036aed09f7b8cf04db'
MANIFEST_SHA = '68ef80c37a0368b09b67d01b5bf563ea4ab8bbb014bfd6184a93f3b19e2f01b9'
CONFIG_SHA = 'a25921442e2d3e463ccd685de6c67d824140b8c1592ab4fe942fb50c5d3b22e8'
UNIT_SHA = 'f22462e9c91eedab99d4bd16d9e3bb14eb52fedbc1e9e3b9110bb3307a11e543'
ENV = {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C.UTF-8'}


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _error(exc):
    def tail(value):
        if isinstance(value, bytes): value = value.decode('utf-8', 'replace')
        return str(value or '')[-16000:]
    return {'class': type(exc).__name__, 'message': str(exc)[:1000], 'returncode': getattr(exc, 'returncode', None),
            'stdout': tail(getattr(exc, 'stdout', None)), 'stderr': tail(getattr(exc, 'stderr', None))}


def _state_digest(root):
    """Bounded read-only byte+path+permission identity; rejects links/sidecars."""
    files = {}; total = 0
    for directory, children, names in os.walk(root, followlinks=False):
        for path in [Path(directory)] + [Path(directory) / name for name in children]:
            info = path.lstat()
            if not stat.S_ISDIR(info.st_mode) or info.st_uid != SERVICE_UID or info.st_mode & 0o022:
                raise RuntimeError('unexpected canonical state directory identity')
        for name in sorted(names):
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            if relative != 'merlin.sqlite3' and not re.fullmatch(r'blobs/sha256/[0-9a-f]{2}/[0-9a-f]{62}', relative):
                raise RuntimeError('unexpected file in published demo registry')
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
            try:
                info = os.fstat(fd)
                if (not stat.S_ISREG(info.st_mode) or info.st_uid != SERVICE_UID or info.st_mode & 0o022
                        or info.st_nlink != 1 or info.st_size > 4 * 1024 * 1024):
                    raise RuntimeError('unsafe canonical state file')
                raw = os.read(fd, info.st_size + 1)
                if len(raw) != info.st_size: raise RuntimeError('canonical file changed during read')
            finally:
                os.close(fd)
            total += len(raw)
            if len(files) >= 32 or total > 16 * 1024 * 1024: raise RuntimeError('demo state exceeds fixed drill bounds')
            if relative == 'merlin.sqlite3' and (raw[:16] != b'SQLite format 3\0' or raw[18:20] != b'\x01\x01'):
                raise RuntimeError('published non-WAL canonical database required')
            files[relative] = {'sha256': _sha(raw), 'size': len(raw), 'mode': stat.S_IMODE(info.st_mode), 'uid': info.st_uid}
    if 'merlin.sqlite3' not in files: raise RuntimeError('canonical database missing')
    return {'sha256': _sha(_json(files)), 'files': len(files), 'bytes': total}


PRODUCTION_PROBE = """import sys,json,time
sys.path.insert(0,sys.argv[1])
from dot_ai_os.private_runtime import call_socket
out={}
for tool in ('health','context_status'):
 q={'schema':'merlin-private-call/1','request_id':'recovery-baseline-'+tool,'tool':tool,'arguments':{}}
 for attempt in range(20):
  try:
   r=call_socket('/run/merlin-dot-private/tools.sock',q,expected_server_uid=982,timeout_seconds=5);break
  except (FileNotFoundError,ConnectionRefusedError):
   if attempt==19:raise
   time.sleep(.2)
 if r.get('ok') is not True or r.get('qualification') is not False or r.get('promotion_authority') is not False:raise RuntimeError('production read probe failed')
 if tool=='context_status' and (r['result']['record_count']!=2 or r['result']['by_namespace']!={'merlin':2}):raise RuntimeError('not the fixed two-document demo')
 if tool=='health' and (r['result']['transport']!='unix' or r['result']['public_listener'] is not False):raise RuntimeError('unexpected production transport')
 out[tool]=r
import hashlib
print(json.dumps({'record_count':2,'sha256':hashlib.sha256(json.dumps(out,sort_keys=True,separators=(',',':')).encode()).hexdigest()}))
"""


def _profile(b):
    release = SOURCE / 'releases' / RELEASE_SHA
    for path in (SOURCE, SOURCE / 'releases', CONFIG.parent, UNIT.parent): b['_root_directory'](path)
    b['_current'](release)
    b['_verify_release'](release, MANIFEST_SHA)
    b['_regular'](CONFIG, expected=CONFIG_SHA, maximum=16000)
    b['_regular'](UNIT, expected=UNIT_SHA, maximum=16000)
    if b['pwd'].getpwnam('merlin-dot').pw_uid != 982 or b['pwd'].getpwnam('opc').pw_uid != 1000:
        raise RuntimeError('fixed service/runner UID changed')
    properties = b['_active']()
    pid = subprocess.run(['/usr/bin/systemctl', 'show', 'merlin-dot-private.service', '--property=MainPID', '--value'],
        env=ENV, cwd='/', capture_output=True, text=True, timeout=10, check=True).stdout.strip()
    if not pid.isdigit() or int(pid) <= 1: raise RuntimeError('running private-service PID required')
    response = subprocess.run(['/usr/bin/python3', '-I', '-B', '-c', PRODUCTION_PROBE, str(release / 'python')],
        user=1000, group=1000, extra_groups=[], cwd=str(release), env=ENV,
        capture_output=True, text=True, timeout=25, check=True)
    health = json.loads(response.stdout)
    if set(health) != {'record_count', 'sha256'} or health['record_count'] != 2:
        raise RuntimeError('invalid compact production probe')
    return {'release_sha256': RELEASE_SHA, 'manifest_sha256': MANIFEST_SHA,
        'config_sha256': CONFIG_SHA, 'unit_sha256': UNIT_SHA, 'pid': int(pid),
        'service_properties': properties, 'state': _state_digest(STATE), 'health': health}


SERVER_START = """import sys,os,ctypes,signal
parent=int(sys.argv[1])
if os.getppid()!=parent:raise RuntimeError('worker parent identity mismatch')
if ctypes.CDLL(None).prctl(1,signal.SIGTERM)!=0:raise RuntimeError('parent-death guard failed')
if os.getppid()!=parent:raise RuntimeError('worker already exited')
sys.path.insert(0,sys.argv[2])
from dot_ai_os.private_runtime import main
sys.argv=[sys.argv[0]]+sys.argv[3:]
raise SystemExit(main())
"""


WORKER = 'SERVER_START = '+repr(SERVER_START)+'\n'+r'''import sys,json,hashlib,types,sqlite3,shutil,subprocess,time,os
from pathlib import Path
os.umask(0o077)
release,source,work,recovery_file=map(Path,sys.argv[1:5])
sys.path.insert(0,str(release/'python'))
from dot_ai_os.private_runtime import PrivateReadOnlyRegistry,call_socket
from dot_ai_os.bridge import DotContextBridge,canonical
recovery=types.ModuleType('recovery_drill_impl');sys.modules[recovery.__name__]=recovery
exec(compile(recovery_file.read_text(),'pinned-recovery-source','exec'),recovery.__dict__)
bounds=recovery.SnapshotBounds(max_db_bytes=4*1024*1024,max_blob_bytes=4*1024*1024,max_total_bytes=16*1024*1024,
 max_blobs=32,max_rows=1024,max_manifest_bytes=65536,max_seconds=5)
def digest(value):return hashlib.sha256(canonical(value)).hexdigest()
def inspect(root):
 r=PrivateReadOnlyRegistry(root);b=DotContextBridge(r,project_id='dot-production-docs',namespaces=('merlin','expert-robot'))
 records=b._records();seeds=json.loads((release/'seed-documents.json').read_text())
 if len(records)!=2 or len(seeds)!=2:raise RuntimeError('not fixed synthetic source')
 expected={d['source_id']:d for d in seeds};refs=[]
 for record in records:
  d=expected[record['source_id']]
  for key in ('namespace','title','source_url','source_version','epistemic','captured_at'):
   if record[key]!=d[key]:raise RuntimeError('synthetic source metadata changed')
  value=r.read_artifact_ref(record['source_ref'],max_bytes=16000)['content']
  if value!=d['content'].encode():raise RuntimeError('synthetic source bytes changed')
  b.fetch(record['source_ref'],length_bytes=16000);refs.append(record['source_ref'])
 with r._connect() as db:
  history=[dict(x) for x in db.execute('SELECT * FROM artifact_versions ORDER BY project_id,logical_path,version')]
  provenance=[dict(x) for x in db.execute('SELECT * FROM artifact_version_provenance ORDER BY project_id,logical_path,version')]
  projects=[x[0] for x in db.execute('SELECT project_id FROM projects ORDER BY project_id')]
 if projects!=['dot-production-docs']:raise RuntimeError('unexpected project in demo registry')
 return {'inventory_sha256':digest(r.inventory('dot-production-docs')),'history_sha256':digest(history),
  'provenance_sha256':digest(provenance),'history_rows':len(history),'provenance_rows':len(provenance),
  'source_refs_sha256':digest(sorted(refs,key=lambda x:x['logical_path'])),'record_count':2},refs
def read_call(sock,tool,args):
 q={'schema':'merlin-private-call/1','request_id':'recovery-'+tool,'tool':tool,'arguments':args}
 for attempt in range(20):
  try:return call_socket(sock,q,expected_server_uid=os.geteuid(),timeout_seconds=5)
  except (FileNotFoundError,ConnectionRefusedError):
   if attempt==19:raise
   time.sleep(.2)
def run():
 original,refs=inspect(source)
 snapshot=work/'snapshot';restored=work/'restored'
 made=recovery.create_snapshot(source,snapshot,bounds=bounds);pin=made['manifest_sha256']
 checked=recovery.verify_snapshot(snapshot,pin,bounds=bounds)
 restored_receipt=recovery.restore_snapshot(snapshot,restored,pin,bounds=bounds)
 recovered,restored_refs=inspect(restored)
 if original!=recovered or refs!=restored_refs:raise RuntimeError('historical identity changed during restore')
 negative={}
 for kind in ('corrupt_blob','missing_blob'):
  damaged=work/kind;shutil.copytree(snapshot,damaged)
  blob=next(p for p in (damaged/'registry'/'blobs'/'sha256').rglob('*') if p.is_file())
  if kind=='missing_blob':blob.unlink()
  else:blob.write_bytes(blob.read_bytes()+b'corrupt')
  destination=work/(kind+'-must-not-publish')
  try:recovery.restore_snapshot(damaged,destination,pin,bounds=bounds)
  except (ValueError,RuntimeError) as exc:negative[kind]={'rejected':True,'class':type(exc).__name__}
  else:raise RuntimeError('damaged snapshot accepted')
  if destination.exists():raise RuntimeError('damaged restore was published')
 if recovery.verify_snapshot(snapshot,pin,bounds=bounds)['inventory_sha256']!=checked['inventory_sha256']:raise RuntimeError('original snapshot changed')
 tools=['health','context_status','context_search','context_fetch','mathematical_lenses_demo','research_contract','research_episode_demo']
 cfg={'schema':'merlin-private-host/1','project_id':'dot-production-docs','namespaces':['merlin','expert-robot'],
  'grants':[{'uid':os.geteuid(),'principal':'isolated-recovery-drill','tools':tools}]}
 config=work/'isolated-config.json';config.write_text(json.dumps(cfg));config.chmod(0o600)
 sockets=work/'socket';sockets.mkdir(mode=0o700);sock=sockets/'tools.sock'
 # Linux parent-death signal prevents an orphan server if the bounded worker
 # itself is terminated. Only this separately spawned child is affected.
 out=(work/'server.stdout').open('wb');err=(work/'server.stderr').open('wb')
 child=subprocess.Popen(['/usr/bin/python3','-I','-B','-c',SERVER_START,str(os.getpid()),str(release/'python'),'serve','--root',str(restored),
  '--socket',str(sock),'--config',str(config),'--simulation-demo'],cwd=str(release),env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'},stdout=out,stderr=err)
 reports={}
 try:
  for tool in tools+['job_submit']:
   args={'query':'engineering','budget_bytes':8000} if tool=='context_search' else ({'source_ref':refs[0],'length_bytes':16000} if tool=='context_fetch' else {})
   reply=read_call(sock,tool,args)
   if tool=='job_submit':
    if reply.get('ok') is not False or reply.get('error',{}).get('code')!='tool_not_allowed':raise RuntimeError('isolated write denial failed')
   else:
    if reply.get('ok') is not True or reply.get('qualification') is not False or reply.get('promotion_authority') is not False:raise RuntimeError('isolated tool failed: '+tool)
    if tool=='context_status' and reply['result']['record_count']!=2:raise RuntimeError('isolated context count changed')
   reports[tool]={'checked':True,'reply_sha256':digest(reply)}
 finally:
  if child.poll() is None:child.terminate()
  try:child.wait(timeout=5)
  except subprocess.TimeoutExpired:child.kill();child.wait(timeout=5)
  out.close();err.close()
 if inspect(source)[0]!=original or inspect(restored)[0]!=original:raise RuntimeError('source/restoration mutated by reads')
 return {'status':'passed','manifest_sha256':pin,'inventory_sha256':checked['inventory_sha256'],
  'snapshot_receipt_sha256':digest(made),'restore_receipt_sha256':digest(restored_receipt),
  'canonical_identity':original,'negative_controls':negative,'isolated_tools':reports,
  'isolated_server_stopped':child.poll() is not None,'qualification':False,'promotion_authority':False}
try:print(json.dumps(run(),sort_keys=True))
except Exception as exc:
 log=work/'server.stderr'
 detail=log.read_bytes()[-8000:].decode('utf-8','replace') if log.is_file() else ''
 print(json.dumps({'status':'failed','error_class':type(exc).__name__,'message':str(exc)[:1000],
  'isolated_server_stderr':detail}));raise
'''


def drill(upgrade_namespace, recovery_source):
    """Run one unique isolated drill; supplied source is controller hash-pinned."""
    b = upgrade_namespace
    if os.geteuid() != ROOT_UID: raise PermissionError('fixed recovery drill requires root')
    if (b['ROOT_UID'] != ROOT_UID or b['SOURCE'] != SOURCE or b['CONFIG'] != CONFIG or b['UNIT'] != UNIT
            or not isinstance(recovery_source, str) or not 100 <= len(recovery_source.encode()) <= 100000):
        raise ValueError('fixed trusted helper namespace and bounded pinned recovery source required')
    before = _profile(b)
    if WORKSPACE.exists() or WORKSPACE.is_symlink(): b['_root_directory'](WORKSPACE)
    else:
        WORKSPACE.mkdir(mode=0o755);WORKSPACE.chmod(0o755)
    run = Path(tempfile.mkdtemp(prefix='drill-', dir=str(WORKSPACE)));run.chmod(0o755)
    work = run/'work';work.mkdir(mode=0o700);work.chmod(0o700);os.chown(work,SERVICE_UID,1000)
    b['_new_file'](run/'recovery_source.py',recovery_source.encode(),mode=0o644)
    b['_new_file'](run/'worker.py',WORKER.encode(),mode=0o644)
    identity = {'schema':'merlin-private-recovery-drill/1','workspace':str(run),'service_uid':982,
        'release_sha256':RELEASE_SHA,'recovery_source_sha256':_sha(recovery_source.encode()),
        'production_seed_changed':False,'production_service_restarted':False,
        'qualification':False,'promotion_authority':False}
    b['_new_file'](run/'intent.json',_json({**identity,'before':before}))
    failure = None;result = None
    try:
        process = subprocess.run(['/usr/bin/python3','-I','-B',str(run/'worker.py'),
            str(SOURCE/'releases'/RELEASE_SHA),str(STATE),str(work),str(run/'recovery_source.py')],
            user=SERVICE_UID,group=1000,extra_groups=[],cwd=str(run),env=ENV,
            capture_output=True,text=True,timeout=100,check=True)
        result=json.loads(process.stdout)
        if result.get('status')!='passed' or result.get('qualification') is not False or result.get('promotion_authority') is not False:
            raise RuntimeError('invalid isolated recovery result')
    except Exception as exc: failure=_error(exc)
    try:
        after=_profile(b)
        unchanged=after==before
    except Exception as exc:
        after={'error':_error(exc)};unchanged=False
    receipt={**identity,'status':'passed' if failure is None and unchanged else 'failed',
        'production_unchanged':unchanged,'before':before,'after':after,'isolated':result,'error':failure}
    b['_new_file'](run/'receipt.json',_json(receipt))
    return receipt
