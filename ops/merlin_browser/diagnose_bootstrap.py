"""Fixed read-only supervisor inspection for native runtime run44945790158.

No installation, service transition, unit creation, policy change, model call,
or browser episode is supported. All inspected paths and commands are fixed.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import platform
import pwd
import re
import selectors
import stat
import subprocess
import sys
import time
import uuid

TARGET_RUN=44945790158
TARGET_ATTEMPT=1
TARGET_REQUEST='4e9b1d59-f966-44ed-a2c1-329aa77aa22e'
TARGET_COMMIT='230b06056b74a998e47e5d8646aa70ec484d811a'
TARGET_UNIT='merlin-browser-bootstrap-44945790158-1.service'
OPERATION='inspect-supervisor-44945790158'
PRIOR_INTENT_SHA256='203c362c00fb7af0b6f02ac7b923d0894b7f09553eb031299822f62e35a1d305'
PRIOR_RESULT_SHA256='8170ddc15aaf4630fc32440eb353da649c1c8bdfcf9a52cda1e8d7f2a0c30557'
SUCCESSOR_INTENT_SHA256='3cf066c08574d06f59fa3620413ecb72d58af655776a4f0ae5967cfcc3848e36'
SUCCESSOR_RESULT_SHA256='58bb11466d426164070ec07b476adcf919934491b7d6f5099e8266f845e31a37'
SUCCESSOR_LINEAGE_SHA256='5da96d5381d98981450f50e6c9a209d73c357f37d6bf6a0aaf4a2f3f83121d65'
FIXTURE_RECEIPT_SHA256='3c54b1df854e33ae11573ddd3280a91b908b289d587025cf26536952af8b4b98'
STAGED=Path('/var/lib/merlin-browser-bootstrap')/TARGET_REQUEST
BEFORE_SHA256='498f3ea85fe0dfcebbd2871c5029e1f1216ea2a6031f4ef20bd0eefaa69d79fd'
BEFORE_COUNT=971
FIXTURE_RESULT_SHA256='bfa954af712061844777bb1859d6925e41cc97fd24911650c2054c757fdc110e'
RELEASE=Path('/opt/merlin-public-browser/releases/5b967b6364bb8d3213c357e148c43073c309ab45d13338fe577d13565f8d0e9d')
RUNTIME_MANIFEST_SHA256='ea5ea521f055273cd6d82c8a164f6e713172ecf0db51bddefc915a3548ff1ef6'
EXPECTED_HOST_SHA256='728199723582985bc21357e72059fab26a0220e01a6d109f36288b39ecbd8600'
FIXTURE=Path('/var/lib/merlin-public-browser/episodes')/('bootstrap-fixture-'+TARGET_REQUEST)
FIXTURE_UNIT='merlin-browser-fixture-bootstrap-fixture-'+TARGET_REQUEST+'.service'
SUPERVISOR='merlin-public-browser.service'
START='2026-11-21 20:20:40 UTC'
END='2026-11-21 20:21:45 UTC'
ENV={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C.UTF-8','LC_ALL':'C.UTF-8',
     'HOME':'/var/empty','SYSTEMD_PAGER':'','SYSTEMD_COLORS':'0'}
RPM_FORMAT='%{NAME}\t%{EPOCHNUM}\t%{VERSION}\t%{RELEASE}\t%{ARCH}\n'
UNIT_FIELDS=('LoadState','ActiveState','SubState','Result','MainPID','ExecMainPID',
             'ExecMainCode','ExecMainStatus','InvocationID','ControlGroup','RuntimeMaxUSec',
             'TimeoutStopUSec','KillMode','MemoryMax','MemorySwapMax','CPUQuotaPerSecUSec','TasksMax')


class ProbeError(RuntimeError): pass


def canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()


def digest(raw): return hashlib.sha256(raw).hexdigest()


def validate_request(request,execution):
    if (not isinstance(request,dict) or set(request)!={'schema','request_id','operation','created_at'}
        or request['schema']!='merlin-browser-diagnostic-request/1'
        or request['operation']!=OPERATION
        or not isinstance(request['request_id'],str) or str(uuid.UUID(request['request_id']))!=request['request_id']
        or not isinstance(request['created_at'],str)
        or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ',request['created_at'])):
        raise ProbeError('exact fixed reconciliation request required')
    if (execution.get('repository')!='morganaspim/Cace-app'
        or execution.get('ref')!='refs/heads/merlin/browser-operations-20261121'
        or execution.get('runner')!='cace-oci-a1' or type(execution.get('run_id')) is not int
        or execution['run_id']<=0 or execution.get('run_attempt')!=1
        or not re.fullmatch('[0-9a-f]{40}',execution.get('workflow_commit',''))):
        raise ProbeError('fixed diagnostic workflow identity required')


def directory_fd(path):
    path=Path(path)
    if not path.is_absolute() or '..' in path.parts: raise ProbeError('absolute fixed ancestry required')
    descriptor=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        for part in path.parts[1:]:
            child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=descriptor)
            os.close(descriptor);descriptor=child
        return descriptor
    except BaseException:
        os.close(descriptor);raise


def read_safe(path,maximum,root_owned=False):
    path=Path(path);parent=directory_fd(path.parent)
    try: descriptor=os.open(path.name,os.O_RDONLY|os.O_NONBLOCK|os.O_NOFOLLOW,dir_fd=parent)
    finally: os.close(parent)
    try:
        before=os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size>maximum:
            raise ProbeError('bounded regular diagnostic input required')
        if root_owned and (before.st_uid!=0 or before.st_mode&0o022):
            raise ProbeError('root-owned operation artifact required')
        raw=bytearray()
        while True:
            value=os.read(descriptor,min(65536,maximum+1-len(raw)))
            if not value: break
            raw.extend(value)
            if len(raw)>maximum: raise ProbeError('diagnostic input byte ceiling')
        after=os.fstat(descriptor)
        if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns):
            raise ProbeError('diagnostic input changed while read')
        return bytes(raw)
    finally: os.close(descriptor)


def describe(path,content=False,root_owned=False,maximum=4*1024*1024):
    result={'path':str(path),'content_scope':'fixed browser operation only'}
    try:
        path=Path(path);parent=directory_fd(path.parent)
        try:
            info=os.stat(path.name,dir_fd=parent,follow_symlinks=False)
            result.update(exists=True,mode=oct(stat.S_IMODE(info.st_mode)),uid=info.st_uid,gid=info.st_gid,bytes=info.st_size)
            if stat.S_ISLNK(info.st_mode): result['symlink_target']=os.readlink(path.name,dir_fd=parent)
        finally: os.close(parent)
        if content:
            raw=read_safe(path,maximum,root_owned);result['sha256']=digest(raw)
            try: result.update(encoding='utf-8',content=raw.decode())
            except UnicodeDecodeError: result.update(encoding='base64',content=base64.b64encode(raw).decode())
    except FileNotFoundError: result['exists']=False
    except BaseException as exc: result['observation_error']={'type':type(exc).__name__,'message':str(exc)[:300]}
    return result


def command(argv,seconds=8,maximum=1024*1024):
    # No detached descendants: the workflow supplies an independent root
    # timeout process group around this entire read-only probe.
    process=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,env=ENV,cwd='/')
    selector=selectors.DefaultSelector();selector.register(process.stdout,selectors.EVENT_READ)
    raw=bytearray();started=time.monotonic();error=None
    try:
        while selector.get_map():
            remaining=seconds-(time.monotonic()-started)
            if remaining<=0: raise ProbeError('read-only command deadline')
            for key,_ in selector.select(min(.2,remaining)):
                value=os.read(key.fd,65536)
                if not value: selector.unregister(key.fileobj);continue
                if len(raw)+len(value)>maximum: raise ProbeError('read-only command output ceiling')
                raw.extend(value)
        process.wait(timeout=max(.01,seconds-(time.monotonic()-started)))
    except BaseException as exc: error={'type':type(exc).__name__,'message':str(exc)[:300]}
    finally:
        selector.close()
        if process.poll() is None: process.kill();process.wait(timeout=3)
        process.stdout.close()
    result={'argv':argv,'returncode':process.returncode,'elapsed_seconds':round(time.monotonic()-started,6),
            'bytes':len(raw),'sha256':digest(raw),'complete':error is None,'error':error}
    try: result.update(encoding='utf-8',output=raw.decode())
    except UnicodeDecodeError: result.update(encoding='base64',output=base64.b64encode(raw).decode())
    return result


def fixed_commands():
    journal=['/usr/bin/journalctl','--no-pager','--all','--output=json',
             '--output-fields=__REALTIME_TIMESTAMP,__MONOTONIC_TIMESTAMP,_BOOT_ID,_SYSTEMD_UNIT,_PID,_COMM,MESSAGE',
             '--since='+START,'--until='+END,'--lines=512']
    result={
      'failed_unit':['/usr/bin/systemctl','show',TARGET_UNIT,'--no-pager']+['--property='+key for key in UNIT_FIELDS],
      'private_unit':['/usr/bin/systemctl','show','merlin-dot-private.service','--no-pager']+['--property='+key for key in UNIT_FIELDS],
      'model_unit':['/usr/bin/systemctl','show','merlin-model-provider.service','--no-pager']+['--property='+key for key in UNIT_FIELDS],
      'zvbi_unit':['/usr/bin/systemctl','show','zvbid.service','--no-pager','--property=LoadState',
                   '--property=ActiveState','--property=SubState','--property=MainPID','--property=FragmentPath'],
      'installed_packages':['/usr/bin/rpm','-qa','--qf',RPM_FORMAT],
      'unit_journal':journal+['--unit='+TARGET_UNIT],
      'fixture_unit':['/usr/bin/systemctl','show',FIXTURE_UNIT,'--no-pager']+['--property='+key for key in UNIT_FIELDS],
      'zvbi_file_states':['/usr/bin/rpm','-q','--qf','[%{FILENAMES}\t%{FILESTATES}\n]','zvbi']}
    result['supervisor_unit']=['/usr/bin/systemctl','show',SUPERVISOR,'--no-pager']+['--property='+key for key in UNIT_FIELDS+('FragmentPath','UnitFileState','ExecStart','Restart','NRestarts','User','Group','UMask','RestrictAddressFamilies','PrivateTmp','ProtectHome','WorkingDirectory','RuntimeDirectory','RuntimeDirectoryMode')]
    result['supervisor_journal']=journal+['--unit='+SUPERVISOR]
    return result


def run(request,execution,runner_temporary):
    validate_request(request,execution)
    if os.geteuid()!=0 or platform.machine()!='aarch64' or sys.version_info[:2]!=(3,9):
        raise ProbeError('actual native root inspection required')
    temporary=Path(runner_temporary)
    if not temporary.is_absolute() or '..' in temporary.parts: raise ProbeError('observed absolute runner temporary path required')
    state=Path('/var/lib/merlin-browser-bootstrap')
    if (digest(read_safe(state/'bootstrap-intent.json',65536,root_owned=True))!=PRIOR_INTENT_SHA256
        or digest(read_safe(state/'bootstrap-result.json',4*1024*1024,root_owned=True))!=PRIOR_RESULT_SHA256):
        raise ProbeError('exact retained failed operation lineage differs')
    expected={STAGED/'bootstrap-intent.json':SUCCESSOR_INTENT_SHA256,
      STAGED/'bootstrap-result.json':SUCCESSOR_RESULT_SHA256,STAGED/'operation-receipt.json':SUCCESSOR_RESULT_SHA256,
      STAGED/'successor-lineage.json':SUCCESSOR_LINEAGE_SHA256,
      state/'runtime-successor-from-04d38719-4c94-4059-988b-9081375fd209.json':SUCCESSOR_LINEAGE_SHA256,
      FIXTURE/'result/fixture.json':FIXTURE_RESULT_SHA256,
      FIXTURE/'launch-receipt.json':FIXTURE_RECEIPT_SHA256,RELEASE/'manifest.json':RUNTIME_MANIFEST_SHA256,
      Path('/etc/merlin-public-browser/host.json'):EXPECTED_HOST_SHA256}
    observed_pins=[]
    for path,wanted in expected.items():
        raw=read_safe(path,4*1024*1024,root_owned=True);actual=digest(raw)
        observed_pins.append({'path':str(path),'sha256':actual,'bytes':len(raw),'matches_expected':actual==wanted})
        if actual!=wanted: raise ProbeError('exact retained successor/runtime identity differs: '+str(path))
    result={'schema':'merlin-browser-bootstrap-reconciliation/1','status':'observations_collected',
       'request':request,'execution':execution,'target':{'run_id':TARGET_RUN,'run_attempt':TARGET_ATTEMPT,
       'workflow_commit':TARGET_COMMIT,'request_id':TARGET_REQUEST,'unit':TARGET_UNIT,
       'successful_fixture_result_sha256':FIXTURE_RESULT_SHA256},'model_calls':0,'browser_episodes':0,
       'software_installation':False,'service_transitions':False,'policy_changes':False,
       'automatic_retry':False,'observed_at_unix':time.time(),'uid':os.geteuid(),'commands':{}}
    result['prior_lineage']={'intent_sha256':PRIOR_INTENT_SHA256,'failed_result_sha256':PRIOR_RESULT_SHA256,
                             'actual_files_matched':True}
    result['successor_identity_observations']=observed_pins
    result['host_expected_pin_origin']='actual prior observed host hash and runtime receipt confirm rollback to that exact file'
    for name,argv in fixed_commands().items():
        observed=command(argv,seconds=8 if name.endswith('journal') else 5,
                         maximum=4*1024*1024 if name.endswith('journal') else 1024*1024)
        result['commands'][name]=observed
    package_command=result['commands']['installed_packages']
    if package_command['returncode']==0 and package_command['complete'] and package_command['encoding']=='utf-8':
        rows=[]
        for line in package_command['output'].splitlines():
            fields=line.split('\t')
            if len(fields)!=5: raise ProbeError('current RPM inventory format differs')
            rows.append(dict(zip(('name','epoch','version','release','arch'),fields)))
        rows.sort(key=lambda row:tuple(row[key] for key in ('name','epoch','version','release','arch')))
        result['package_reconciliation']={'count':len(rows),'sha256':digest(canonical(rows)),
             'retained_after_count':BEFORE_COUNT,'retained_after_sha256':BEFORE_SHA256,
             'equals_retained_after':len(rows)==BEFORE_COUNT and digest(canonical(rows))==BEFORE_SHA256}
    paths=[state/'bootstrap-intent.json',state/'bootstrap-result.json',
           STAGED/'bootstrap-intent.json',STAGED/'bootstrap-result.json',STAGED/'operation-receipt.json',
           STAGED/'host-replacement-intent.json',STAGED/'successor-lineage.json',FIXTURE/'launch-receipt.json',FIXTURE/'result/fixture.json']
    result['retained_operation_artifacts']=[describe(path,content=True,root_owned=True) for path in paths]
    result['browser_state']=[describe(path,content=True,root_owned=True,maximum=65536) for path in
       (Path('/etc/merlin-public-browser/host.json'),Path('/etc/merlin-public-browser/service.json'),
        Path('/etc/systemd/system/merlin-public-browser.service'))]
    result['browser_path_metadata']=[describe(path) for path in
       (Path('/opt/merlin-public-browser/current'),Path('/etc/merlin-public-browser'),
        Path('/run/merlin-public-browser'),Path('/run/merlin-public-browser/browser.sock'),
        Path('/var/lib/merlin-public-browser'),Path('/var/lib/merlin-public-browser/episodes'),
        Path('/var/lib/merlin-public-browser/registry'),Path('/var/lib/merlin-public-browser/registry/merlin.sqlite3'),
        Path('/var/lib/merlin-public-browser/registry/merlin.sqlite3-wal'),
        Path('/var/lib/merlin-public-browser/registry/merlin.sqlite3-shm'),
        Path('/var/lib/merlin-public-browser/registry/blobs'),RELEASE,RELEASE/'venv',RELEASE/'venv/bin',
        RELEASE/'venv/bin/python',RELEASE/'python',RELEASE/'python/merlin',RELEASE/'bin',
        RELEASE/'bin/launch-episode')]
    result['public_episode_paths']=[describe(Path('/var/lib/merlin-public-browser/episodes')/(prefix+'-'+TARGET_REQUEST))
        for prefix in ('database-arxiv','news-nasa','repository-openmdao')]
    try:
        account=pwd.getpwnam('merlin-browser')
        result['dedicated_browser_account']={'exists':True,'uid':account.pw_uid,'gid':account.pw_gid,
            'home':account.pw_dir,'shell':account.pw_shell}
    except KeyError: result['dedicated_browser_account']={'exists':False}
    result['existing_private_hashes']=[]
    for path in ('/etc/merlin-dot-private/config.json','/etc/systemd/system/merlin-dot-private.service',
                 '/etc/merlin-model-provider/manifest.json','/etc/systemd/system/merlin-model-provider.service'):
        # Match the existing snapshot's read-only hash contract; do not invent
        # a new ownership requirement for already admitted private services.
        raw=read_safe(path,1048576)
        result['existing_private_hashes'].append({'path':path,'sha256':digest(raw),'bytes':len(raw),'content_exported':False})
    result['daemon_paths']=[describe(path) for path in ('/usr/lib/systemd/system/zvbid.service',
      '/etc/systemd/system/zvbid.service','/run/systemd/system/zvbid.service','/usr/sbin/zvbid')]
    result['venv_configuration']=describe(RELEASE/'venv/pyvenv.cfg',content=True,root_owned=True,maximum=65536)
    result['existing_private_current']=describe(Path('/opt/merlin-dot-private/current'))
    manifest=json.loads(read_safe(RELEASE/'manifest.json',1048576,root_owned=True));result['runtime_file_identities']=[]
    for item in manifest['files']:
        name=item['path']
        if not re.fullmatch(r'(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+',name) or '..' in Path(name).parts:
            raise ProbeError('frozen runtime member path differs')
        raw=read_safe(RELEASE/name,2*1024*1024,root_owned=True)
        result['runtime_file_identities'].append({'path':name,'bytes':len(raw),'sha256':digest(raw),
            'matches_manifest':len(raw)==item['bytes'] and digest(raw)==item['sha256']})
    result['limitations']=['Read-only point-in-time observations do not authorize an automatic retry.',
      'A missing receipt does not prove the controller never began.',
      'Only the exact supervisor service journal within the failed execution window is read; environment and private configuration bytes are not exported.',
      'No service is started or restarted. The accepted fixture is retained, not rerun; no public episode is submitted.']
    if len(canonical(result))>24*1024*1024: raise ProbeError('complete reconciliation evidence ceiling')
    return result
