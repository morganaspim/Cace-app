"""One inspected activation successor; reuse runtime and fixture, acquire 3 sources.

No package installation, runtime replacement, fixture replay, policy change or
model call is supported. The exact failed activation and every earlier receipt
remain immutable. Only the root supervisor's own directory setup is repaired.
"""
import fcntl
import os
from pathlib import Path
import platform
import pwd
import re
import stat
import sys
import time
import uuid

import bootstrap_browser as B

OPERATION='activate-supervisor-44945790158'
OLD_REQUEST='4e9b1d59-f966-44ed-a2c1-329aa77aa22e'
OLD_RUN=44945790158
OLD_COMMIT='230b06056b74a998e47e5d8646aa70ec484d811a'
OLD_INTENT='3cf066c08574d06f59fa3620413ecb72d58af655776a4f0ae5967cfcc3848e36'
OLD_RESULT='58bb11466d426164070ec07b476adcf919934491b7d6f5099e8266f845e31a37'
OLD_LINEAGE='5da96d5381d98981450f50e6c9a209d73c357f37d6bf6a0aaf4a2f3f83121d65'
OLD_HOST='728199723582985bc21357e72059fab26a0220e01a6d109f36288b39ecbd8600'
NEW_HOST='9c80b7d364aa6e7f9536df64b0b6ff3265d8b0cdd784ccda6a990fecfd7cafbd'
OLD_UNIT='b4169da017658c97a039c945af9f8d22b7513eb5d0230f9db4c6902ba4a85487'
SERVICE_CONFIG='ddebe3b75f64187425feb5c0de017336b2b9685d4dafeed55f548c8ac4950d3f'
INVENTORY='498f3ea85fe0dfcebbd2871c5029e1f1216ea2a6031f4ef20bd0eefaa69d79fd'
RUNTIME='5b967b6364bb8d3213c357e148c43073c309ab45d13338fe577d13565f8d0e9d'
MANIFEST='ea5ea521f055273cd6d82c8a164f6e713172ecf0db51bddefc915a3548ff1ef6'
FIXTURE_RECEIPT='3c54b1df854e33ae11573ddd3280a91b908b289d587025cf26536952af8b4b98'
FIXTURE_RESULT='bfa954af712061844777bb1859d6925e41cc97fd24911650c2054c757fdc110e'
VENV_LEDGER='84bec22a950a3422a925a85bc065b9648a2cfee49df2c4b781649e9da48447ca'
LOADER_SHA='49d528c1bc76e851bdc1db2ffcacd69b7f969c461a23741b9f5b8be4318c3403'
NATIVE_SHA='22870374b6f2acfa00ac7c54a09eb30aacb1cdac932aba97e654e3dff458318f'
INSPECTION={'run_id':44946215856,'workflow_commit':'0a39483ca8de7ea66cddd6cab58286553a2cfdb9',
    'artifact_sha256':'7248118a26a83a5b909b91f2f0d976919dfa0efd2b34a3201a6d8845ad75dfd1',
    'observed_failure':'233/RUNTIME_DIRECTORY before Python execution',
    'cause_scope':'directory setup permission denied; no claim about underlying policy mechanism'}
RELEASE=B.PREFIX/'releases'/RUNTIME
UNIT_PATH=Path('/etc/systemd/system')/B.SERVICE
UNIT_FIELDS=('LoadState','ActiveState','SubState','Result','MainPID','ExecMainPID','ExecMainCode','ExecMainStatus',
    'InvocationID','ControlGroup','User','Group','UMask','CPUQuotaPerSecUSec','MemoryMax','MemorySwapMax',
    'TasksMax','KillMode','PrivateTmp','ProtectHome','RestrictAddressFamilies','FragmentPath','UnitFileState',
    'RuntimeDirectory','ExecStartPre','ExecStart','NRestarts')


def validate_request(request,execution):
    if (not isinstance(request,dict) or set(request)!={'schema','request_id','operation','created_at'}
        or request.get('schema')!='merlin-browser-runtime-request/1' or request.get('operation')!=OPERATION
        or not isinstance(request.get('request_id'),str) or str(uuid.UUID(request['request_id']))!=request['request_id']
        or request['request_id']==OLD_REQUEST or not isinstance(request.get('created_at'),str)
        or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ',request['created_at'])):
        raise B.BootstrapError('exact inspected activation successor request required')
    if (execution.get('repository')!='morganaspim/Cace-app'
        or execution.get('ref')!='refs/heads/merlin/browser-operations-20261121'
        or execution.get('runner')!='cace-oci-a1' or execution.get('run_attempt')!=1
        or type(execution.get('run_id')) is not int or execution['run_id']<=0
        or not re.fullmatch('[0-9a-f]{40}',execution.get('workflow_commit',''))):
        raise B.BootstrapError('fixed native activation execution required')


def checked_raw(path,expected,maximum=4*1024*1024):
    B.rooted(Path(path).parent,0o700);info=Path(path).lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid!=0 or info.st_mode&0o022:
        raise B.BootstrapError('root-owned retained operation input required')
    raw=B.regular(path,maximum)
    if B.digest(raw)!=expected: raise B.BootstrapError('retained operation identity differs: '+str(path))
    return raw


def prior_receipt(raw):
    if B.digest(raw)!=OLD_RESULT: raise B.BootstrapError('exact failed activation receipt required')
    prior=B.decode(raw)
    if (prior.get('schema')!='merlin-browser-bootstrap/1' or prior.get('status')!='failed'
        or prior.get('request',{}).get('request_id')!=OLD_REQUEST
        or prior.get('execution',{}).get('run_id')!=OLD_RUN
        or prior.get('execution',{}).get('workflow_commit')!=OLD_COMMIT
        or prior.get('error')!={'type':'BootstrapError','message':'browser supervisor readiness deadline'}
        or prior.get('runtime_pin',{}).get('sha256')!=RUNTIME
        or prior.get('before')!=prior.get('after_failure')
        or prior.get('rollback',{}).get('previous_host_restored') is not True
        or prior.get('package_failure_observation',{}).get('sha256')!=INVENTORY
        or prior.get('package_failure_observation',{}).get('equals_retained_before') is not True
        or prior.get('system_package_mutations')!=0 or prior.get('model_calls')!=0
        or prior.get('fixture',{}).get('status')!='succeeded'
        or prior.get('fixture',{}).get('all_workers_stopped') is not True
        or prior.get('fixture',{}).get('scratch_unmounted') is not True
        or prior.get('fixture_observation',{}).get('status')!='succeeded'
        or prior.get('native_acceptance') is not None):
        raise B.BootstrapError('ambiguous prior activation cannot be resumed')
    return prior


def runtime_parent_code(parent='/run',owner=0,group=1000):
    # The production unit uses only the fixed default. Tests use an isolated
    # temporary root to exercise creation under the supervisor's actual0077.
    return ("import os,stat;p=os.open("+repr(str(parent))+",os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);"
        "s=os.fstat(p);assert s.st_uid=="+str(owner)+" and not s.st_mode&0o022,'unexpected runtime parent';"
        "n='merlin-public-browser';os.access(n,os.F_OK,dir_fd=p,follow_symlinks=False) or os.mkdir(n,0o755,dir_fd=p);"
        "d=os.open(n,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=p);s=os.fstat(d);"
        "assert s.st_uid=="+str(owner)+" and not s.st_mode&0o022,'unexpected browser runtime directory';"
        "os.fchown(d,"+str(owner)+","+str(group)+");os.fchmod(d,0o755);s=os.fstat(d);"
        "assert (s.st_uid,s.st_gid,stat.S_IMODE(s.st_mode))==("+str(owner)+","+str(group)+",0o755);os.close(d);os.close(p)")


def repaired_unit(old):
    if B.digest(old)!=OLD_UNIT or old!=B.service_unit(RELEASE):
        raise B.BootstrapError('exact observed supervisor unit required')
    before=b'RuntimeDirectory=merlin-public-browser\nRuntimeDirectoryMode=0755\nRuntimeDirectoryPreserve=yes\n'
    if old.count(before)!=1: raise B.BootstrapError('single observed directory block required')
    code=runtime_parent_code()
    if any(value in code for value in ('\n','"','%','$')): raise B.BootstrapError('fixed systemd code encoding differs')
    replacement=('ExecStartPre=/usr/bin/python3 -I -B -c "'+code+'"\n').encode()
    return old.replace(before,replacement)


def atomic_replace(target,raw,temporary,mode):
    B.write(temporary,raw,mode);os.replace(temporary,target)
    descriptor=os.open(str(Path(target).parent),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try: os.fsync(descriptor)
    finally: os.close(descriptor)
    if B.regular(target,65536)!=raw: raise B.BootstrapError('atomic replacement readback differs')


def restore_after_attempt(target,old,new_sha,temporary,mode):
    actual=B.digest(B.regular(target,65536));old_sha=B.digest(old)
    if actual==old_sha: return {'already_previous':True,'observed_sha256':actual}
    if actual!=new_sha:
        raise B.BootstrapError('unrecognized replacement state preserved for reconciliation')
    atomic_replace(target,old,temporary,mode)
    return {'restored':True,'observed_before_restore_sha256':actual,'restored_sha256':old_sha}


def observe_supervisor(logs,label,since):
    """Always preserve the exact service, including startup failures before Python."""
    result={'unit':B.SERVICE,'since_unix':since,'observed_until_unix':int(time.time())+1,'commands':{}}
    commands={
      'unit':['/usr/bin/systemctl','show',B.SERVICE,'--no-pager']+['--property='+key for key in UNIT_FIELDS],
      'journal':['/usr/bin/journalctl','--no-pager','--all','--output=json',
       '--output-fields=__REALTIME_TIMESTAMP,__MONOTONIC_TIMESTAMP,_BOOT_ID,_SYSTEMD_UNIT,_PID,_COMM,MESSAGE',
       '--unit='+B.SERVICE,'--since=@'+str(int(since)),'--until=@'+str(result['observed_until_unix']),'--lines=512']}
    for name,argv in commands.items():
        path=logs/(label+'-supervisor-'+name+'.txt')
        try:
            raw=B.command(argv,path,timeout=5,limit=2*1024*1024,allowed=(0,1,3,4))
            result['commands'][name]={'bytes':len(raw),'sha256':B.digest(raw),'path':path.name}
            if name=='unit': result['properties']=dict(line.split('=',1) for line in raw.decode().splitlines() if '=' in line)
        except BaseException as error:
            result['commands'][name]={'observation_error':{'type':type(error).__name__,'message':str(error)[:1000]},
                'raw_log_retained':path.exists(),'path':path.name}
    return result


def require_inactive(properties):
    if (properties.get('MainPID')!='0' or properties.get('ControlGroup')!=''
        or properties.get('ActiveState') not in ('inactive','failed')):
        raise B.BootstrapError('browser supervisor is not confirmed stopped')


def public_workers_stopped(request_id,logs):
    result={'all_stopped':True,'units':{}}
    for prefix,_,_ in B.PUBLIC_CASES:
        for role in ('broker','renderer'):
            unit='merlin-browser-'+role+'-'+prefix+'-'+request_id+'.service'
            try:
                raw=B.command(['/usr/bin/systemctl','show',unit,'--no-pager','--property=MainPID',
                    '--property=ActiveState','--property=ControlGroup'],logs/(unit+'.txt'),timeout=3,limit=8192)
                observed=dict(line.split('=',1) for line in raw.decode().splitlines() if '=' in line)
                result['units'][unit]=observed;require_inactive(observed)
            except BaseException as error:
                result['all_stopped']=False
                result['units'].setdefault(unit,{})['observation_error']=type(error).__name__
    return result


def verify_runtime(old_stage,prior,logs):
    manifest=B.decode(checked_raw(RELEASE/'manifest.json',MANIFEST,1048576))
    files=manifest.get('files');observed=[]
    if not isinstance(files,list) or len(files)!=14: raise B.BootstrapError('retained runtime closure differs')
    for row in files:
        name=row.get('path','')
        if not re.fullmatch(r'(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+',name) or '..' in Path(name).parts:
            raise B.BootstrapError('retained runtime member path rejected')
        raw=checked_raw(RELEASE/name,row['sha256'],2*1024*1024)
        if len(raw)!=row['bytes']: raise B.BootstrapError('retained runtime member size differs')
        observed.append({'path':name,'bytes':len(raw),'sha256':B.digest(raw)})
    if len({row['path'] for row in observed})!=14: raise B.BootstrapError('unique retained runtime members required')
    ledger_raw=checked_raw(old_stage/'venv-copy-ledger.json',VENV_LEDGER)
    ledger=B.decode(ledger_raw);items=ledger.get('files',ledger.get('entries'))
    if not isinstance(items,list): raise B.BootstrapError('retained venv copy ledger differs')
    count=0;total=0;seen=set()
    for row in items:
        name=row.get('path','')
        if (not re.fullmatch(r'(?:[A-Za-z0-9_.+~() -]+/)*[A-Za-z0-9_.+~() -]+',name)
            or '..' in Path(name).parts or name in seen): raise B.BootstrapError('retained venv member path rejected')
        seen.add(name);path=RELEASE/'venv'/name
        B.rooted(path.parent)
        if row.get('kind')=='symlink':
            if name!='lib64' or row.get('target')!='lib' or not path.is_symlink() or path.lstat().st_uid!=0 or os.readlink(path)!='lib':
                raise B.BootstrapError('only retained lib64 venv link is admitted')
            continue
        info=path.lstat()
        if (row.get('kind')!='regular' or not stat.S_ISREG(info.st_mode) or info.st_uid!=0
            or info.st_mode&0o022 or oct(stat.S_IMODE(info.st_mode))!=row.get('mode')):
            raise B.BootstrapError('retained venv file ownership differs')
        found=B.identity(path,256*1024*1024)
        if found!={'bytes':row['bytes'],'sha256':row['sha256']}:
            raise B.BootstrapError('retained venv file identity differs')
        count+=1;total+=found['bytes']
        if count>1500 or total>192*1024*1024: raise B.BootstrapError('retained venv ceiling')
    if count!=1420 or total!=153044541: raise B.BootstrapError('retained venv count/bytes differs')
    actual=set()
    for parent,dirs,files in os.walk(RELEASE/'venv',followlinks=False):
        B.rooted(Path(parent))
        if len(Path(parent).relative_to(RELEASE/'venv').parts)>16: raise B.BootstrapError('retained venv depth ceiling')
        for name in list(dirs):
            path=Path(parent)/name
            if path.is_symlink():
                relative=str(path.relative_to(RELEASE/'venv'));actual.add(relative);dirs.remove(name)
                if relative!='lib64' or os.readlink(path)!='lib': raise B.BootstrapError('extra venv link')
        for name in files: actual.add(str((Path(parent)/name).relative_to(RELEASE/'venv')))
        if len(actual)>1500: raise B.BootstrapError('retained venv inventory ceiling')
    if actual!=seen: raise B.BootstrapError('retained venv gained or lost files')
    if B.identity('/usr/lib/ld-linux-aarch64.so.1',2*1024*1024)!={'bytes':842664,'sha256':LOADER_SHA}:
        raise B.BootstrapError('observed native loader differs')
    if B.identity('/usr/lib64/chromium-browser/headless_shell',256*1024*1024)!={'bytes':221959928,'sha256':NATIVE_SHA}:
        raise B.BootstrapError('native Chromium differs')
    B.write(logs/'runtime-reverification.json',B.canonical(observed))
    return {'runtime_manifest_sha256':MANIFEST,'runtime_files':len(observed),'venv_files':count,
        'venv_bytes':total,'venv_ledger_sha256':VENV_LEDGER,'software_reinstalled':False}


def verify_fixture(prior):
    episode=B.STATE/'episodes'/('bootstrap-fixture-'+OLD_REQUEST)
    receipt=B.decode(checked_raw(episode/'launch-receipt.json',FIXTURE_RECEIPT))
    result=B.decode(checked_raw(episode/'result/fixture.json',FIXTURE_RESULT))
    if receipt!=prior['fixture'] or result!=prior['fixture_observation']:
        raise B.BootstrapError('retained successful fixture differs from failed activation receipt')
    if (result.get('chromium_sandbox') is not True or result.get('observed_text')!='renderer-js-42'
        or result.get('isolation',{}).get('uid')!=980 or result.get('isolation',{}).get('interfaces')!=['lo']
        or result.get('forbidden_host_paths_visible')!=[] or result.get('public_network_requests')!=0):
        raise B.BootstrapError('retained native fixture acceptance differs')
    rows=receipt.get('output',{}).get('files',[])
    if len(rows)!=61: raise B.BootstrapError('retained complete fixture count differs')
    seen=set()
    for row in rows:
        name=row.get('path','')
        if (not re.fullmatch(r'(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+',name)
            or '..' in Path(name).parts or name in seen): raise B.BootstrapError('fixture path rejected')
        seen.add(name);raw=checked_raw(episode/'result'/name,row['sha256'],2*1024*1024)
        if len(raw)!=row['bytes']: raise B.BootstrapError('retained fixture file size differs')
    return receipt,result


def run(bundle,bundle_pin,request,execution,output):
    if os.geteuid()!=0 or platform.machine()!='aarch64' or sys.version_info[:2]!=(3,9):
        raise B.BootstrapError('native root activation successor required')
    os.umask(0o022);validate_request(request,execution)
    if bundle_pin!={'bytes':66202,'sha256':RUNTIME,'git_blob':'19754c4e50b46d32a05eee8c3a019d1cb450ee67',
                    'expert_source_commit':'8e2f1d69371d5b4f7e01e3bbd5aa02a666ddd506'}:
        raise B.BootstrapError('exact accepted installed runtime pin required')
    if B.identity(bundle,1048576)!={'bytes':66202,'sha256':RUNTIME}:
        raise B.BootstrapError('reviewed immutable runtime evidence differs')
    output_path=Path(output);parent_fd=B.operation_directory(output_path);leaf_fd=None;owned=False
    try:
        os.mkdir('root-evidence',mode=0o700,dir_fd=parent_fd)
        leaf_fd=os.open('root-evidence',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent_fd)
        info=os.fstat(leaf_fd)
        if info.st_uid!=0 or stat.S_IMODE(info.st_mode)!=0o700 or os.listdir(leaf_fd):
            raise B.BootstrapError('new private root evidence leaf required')
        owned=True
        return run_owned(bundle_pin,request,execution,output_path,parent_fd,leaf_fd)
    finally:
        if leaf_fd is not None:
            if owned: os.fchown(leaf_fd,1000,1000)
            os.close(leaf_fd)
        os.close(parent_fd)


def run_owned(bundle_pin,request,execution,output_path,parent_fd,leaf_fd):
    output=Path('/proc/self/fd')/str(leaf_fd);state=B.rooted(B.BOOTSTRAP_STATE,0o700)
    lock=os.open(str(state/'operation.lock'),os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    old_stage=state/OLD_REQUEST;old_intent=checked_raw(old_stage/'bootstrap-intent.json',OLD_INTENT)
    old_result=checked_raw(old_stage/'operation-receipt.json',OLD_RESULT);prior=prior_receipt(old_result)
    checked_raw(old_stage/'bootstrap-result.json',OLD_RESULT);checked_raw(old_stage/'successor-lineage.json',OLD_LINEAGE)
    checked_raw(state/'runtime-successor-from-04d38719-4c94-4059-988b-9081375fd209.json',OLD_LINEAGE)
    checked_raw(state/'bootstrap-intent.json',B.PREDECESSOR['intent_sha256'])
    checked_raw(state/'bootstrap-result.json',B.PREDECESSOR['result_sha256'])
    old_host=checked_raw(B.CONFIG/'host.json',OLD_HOST,65536)
    new_host=checked_raw(old_stage/'installed-host.json',NEW_HOST,65536)
    old_unit=checked_raw(UNIT_PATH,OLD_UNIT,65536);new_unit=repaired_unit(old_unit);new_unit_sha=B.digest(new_unit)
    config=checked_raw(B.CONFIG/'service.json',SERVICE_CONFIG,65536)
    marker=state/('activation-successor-from-'+OLD_REQUEST+'.json')
    for path in (marker,state/request['request_id'],B.PREFIX/'current',Path('/run/merlin-public-browser/browser.sock')):
        if path.exists() or path.is_symlink(): raise B.BootstrapError('existing activation state requires explicit reconciliation')
    for prefix in ('database-arxiv','news-nasa','repository-openmdao'):
        path=B.STATE/'episodes'/(prefix+'-'+OLD_REQUEST)
        if path.exists() or path.is_symlink(): raise B.BootstrapError('prior public attempt would exceed retained budget')
    staged=state/request['request_id'];staged.mkdir(mode=0o700);logs=staged/'logs';logs.mkdir(mode=0o700)
    receipt={'schema':'merlin-browser-bootstrap/1','request':request,'execution':execution,'runtime_pin':bundle_pin,
      'status':'started','model_calls':0,'external_model_cost_usd':0,'qualification':False,'promotion_authority':False,
      'system_package_mutations':0,'python_package_installs':0,'network_acquisition':False,
      'dependency_reuse_prior_completed':True,'predecessor_run_id':OLD_RUN,'predecessor_result_sha256':OLD_RESULT,
      'inspection':INSPECTION,'original_failed_records_preserved':True,'accounts':prior['accounts'],
      'native_executable':prior['native_executable'],'package_support_limit':prior['package_support_limit'],
      'acceptance_budget':{'maximum_attempts':5,'prior_fixture_attempts':2,'prior_fixture_completed':1,
        'prior_failed_fixture_attempts':1,'prior_fixture_id':'bootstrap-fixture-'+OLD_REQUEST,
        'remaining_attempt_ceiling':3,'planned_fixture_attempts':0,'planned_public_attempts':3,'model_calls':0},
      'fixture_reused':True,'fixture_source_run_id':OLD_RUN,'fixture_source_request_id':OLD_REQUEST,
      'fixture_source_receipt_sha256':FIXTURE_RECEIPT,'fixture_source_result_sha256':FIXTURE_RESULT,
      'host_reboot_performed':False}
    B.write(marker,B.canonical({'schema':'merlin-browser-activation-successor/1','prior_run_id':OLD_RUN,
       'prior_result_sha256':OLD_RESULT,'successor_request':request,'execution':execution,'automatic_retry':False}))
    for name,raw in (('bootstrap-intent.json',B.canonical(receipt)),('predecessor-intent.json',old_intent),
       ('predecessor-result.json',old_result),('previous-host.json',old_host),('installed-host.json',new_host),
       ('previous-supervisor.service',old_unit),('installed-supervisor.service',new_unit),
       ('service-config.json',config),('successor-lineage.json',B.regular(marker,65536))): B.write(staged/name,raw)
    host_attempt=False;unit_attempt=False;service_attempt=False;safe_export=False;since=int(time.time())-2
    try:
        receipt['controller_envelope']=B.controller_envelope(execution,logs)
        receipt['before']=B.snapshot(logs,'before')
        if receipt['before']!=prior['before']: raise B.BootstrapError('existing private/model state differs')
        before=B.installed(logs/'rpm-before.txt')
        if len(before)!=971 or B.digest(B.canonical(before))!=INVENTORY:
            raise B.BootstrapError('retained installed package state differs')
        receipt['installed_packages_before_sha256']=INVENTORY
        receipt['daemon_before']=B.daemon_absence(logs,'before',True)
        account=pwd.getpwnam('merlin-browser')
        if (account.pw_uid,account.pw_gid,account.pw_dir,account.pw_shell)!=(980,980,'/var/empty','/sbin/nologin'):
            raise B.BootstrapError('retained dedicated account differs')
        initial=observe_supervisor(logs,'before',since);receipt['supervisor_before']=initial
        require_inactive(initial.get('properties',{}))
        if initial.get('properties',{}).get('UnitFileState')!='disabled': raise B.BootstrapError('prior supervisor enable state differs')
        for unit in ('merlin-browser-bootstrap-44945790158-1.service',
                     'merlin-browser-fixture-bootstrap-fixture-'+OLD_REQUEST+'.service'):
            raw=B.command(['/usr/bin/systemctl','show',unit,'--no-pager','--property=MainPID',
                '--property=ActiveState','--property=ControlGroup'],logs/(unit+'.txt'),timeout=5)
            require_inactive(dict(line.split('=',1) for line in raw.decode().splitlines() if '=' in line))
        receipt['reused_runtime']=verify_runtime(old_stage,prior,logs)
        receipt['fixture'],receipt['fixture_observation']=verify_fixture(prior)
        host_attempt=True;receipt['host_config_replacement_attempted']=True
        B.write(staged/'host-replacement-intent.json',B.canonical({'previous_sha256':OLD_HOST,'next_sha256':NEW_HOST}))
        atomic_replace(B.CONFIG/'host.json',new_host,B.CONFIG/('host-activation-'+request['request_id']+'.json'),0o600)
        receipt['host_config_sha256']=NEW_HOST
        unit_attempt=True;receipt['supervisor_unit_replacement_attempted']=True
        B.write(staged/'unit-replacement-intent.json',B.canonical({'previous_sha256':OLD_UNIT,'next_sha256':new_unit_sha}))
        atomic_replace(UNIT_PATH,new_unit,UNIT_PATH.parent/('merlin-browser-activation-'+request['request_id']+'.tmp'),0o644)
        os.symlink(str(RELEASE),B.PREFIX/'current')
        B.command(['/usr/bin/systemctl','daemon-reload'],logs/'daemon-reload.txt',timeout=10)
        service_attempt=True;receipt['service_start_attempted']=True
        B.command(['/usr/bin/systemctl','enable','--now',B.SERVICE],logs/'service-enable.txt',timeout=20)
        receipt['supervisor_after_start']=observe_supervisor(logs,'after-start',since)
        receipt['acceptance_budget']['public_attempts_reserved']=3
        receipt['native_acceptance']=B.native_acceptance(RELEASE,1000,980,request['request_id'],logs);safe_export=True
        receipt['supervisor_after_acceptance']=observe_supervisor(logs,'after-acceptance',since)
        actual=receipt['supervisor_after_acceptance'].get('properties',{})
        if (actual.get('ActiveState')!='active' or not actual.get('MainPID','').isdigit() or int(actual['MainPID'])<=0
            or actual.get('User')!='root' or actual.get('Group')!='root' or actual.get('UMask')!='0077'
            or actual.get('MemoryMax')!='268435456' or actual.get('MemorySwapMax')!='0'
            or actual.get('CPUQuotaPerSecUSec')!='250ms' or actual.get('TasksMax')!='32'
            or actual.get('RuntimeDirectory')!='' or actual.get('RestrictAddressFamilies')!='AF_UNIX'):
            raise B.BootstrapError('observed active supervisor profile differs')
        run_parent=Path('/run/merlin-public-browser');info=run_parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or (info.st_uid,info.st_gid,stat.S_IMODE(info.st_mode))!=(0,1000,0o755):
            raise B.BootstrapError('actual runtime parent metadata differs')
        receipt['runtime_parent']={'path':str(run_parent),'uid':info.st_uid,'gid':info.st_gid,'mode':'0755',
            'recursive_changes':False,'host_reboot_performed':False}
        receipt['after']=B.snapshot(logs,'after')
        if receipt['after']!=receipt['before']: raise B.BootstrapError('existing private/model state changed')
        after=B.installed(logs/'rpm-after.txt')
        if after!=before: raise B.BootstrapError('activation changed system package state')
        receipt['installed_packages_after_sha256']=B.digest(B.canonical(after))
        receipt['daemon_after_acceptance']=B.daemon_absence(logs,'after-acceptance',True)
        checked_raw(B.CONFIG/'host.json',NEW_HOST,65536);checked_raw(B.CONFIG/'service.json',SERVICE_CONFIG,65536)
        checked_raw(UNIT_PATH,new_unit_sha,65536);checked_raw(old_stage/'bootstrap-result.json',OLD_RESULT)
        checked_raw(state/'bootstrap-intent.json',B.PREDECESSOR['intent_sha256'])
        checked_raw(state/'bootstrap-result.json',B.PREDECESSOR['result_sha256'])
        receipt['service_config_sha256']=SERVICE_CONFIG;receipt['unit_sha256']=new_unit_sha
        receipt['public_episode_acceptance']=receipt['native_acceptance']['status']
        receipt['status']='installed_native_passed' if receipt['public_episode_acceptance']=='passed' else 'installed_source_acceptance_incomplete'
    except BaseException as error:
        receipt['status']='failed';receipt['error']={'type':type(error).__name__,'message':str(error)[:2000]}
        receipt['supervisor_at_failure']=observe_supervisor(logs,'at-failure',since)
        receipt['rollback']={'automatic_retry':False,'accepted_runtime_retained':True,'accepted_fixture_retained':True,
            'system_package_rollback_needed':False}
        stopped=not service_attempt
        if service_attempt:
            try:
                B.command(['/usr/bin/systemctl','disable','--now',B.SERVICE],logs/'failed-service-stop.txt',timeout=10,allowed=(0,1,5))
                stopped_state=observe_supervisor(logs,'after-stop',since);receipt['supervisor_after_stop']=stopped_state
                require_inactive(stopped_state.get('properties',{}));stopped=True
            except BaseException as stop_error: receipt['rollback']['stop_error']=type(stop_error).__name__
        receipt['public_worker_shutdown']=public_workers_stopped(request['request_id'],logs)
        safe_export=stopped and receipt['public_worker_shutdown']['all_stopped']
        if stopped:
            current=B.PREFIX/'current'
            if current.is_symlink() and os.readlink(current)==str(RELEASE): current.unlink()
            for label,attempted,target,old,new_sha,temporary,mode in (
              ('host',host_attempt,B.CONFIG/'host.json',old_host,NEW_HOST,B.CONFIG/('host-restore-'+request['request_id']+'.json'),0o600),
              ('unit',unit_attempt,UNIT_PATH,old_unit,new_unit_sha,UNIT_PATH.parent/('merlin-browser-restore-'+request['request_id']+'.tmp'),0o644)):
                if attempted:
                    try: receipt['rollback'][label]=restore_after_attempt(target,old,new_sha,temporary,mode)
                    except BaseException as restore_error:
                        receipt['rollback'][label+'_restore_error']={'type':type(restore_error).__name__,'message':str(restore_error)[:1000]}
            if unit_attempt:
                try: B.command(['/usr/bin/systemctl','daemon-reload'],logs/'restore-daemon-reload.txt',timeout=10)
                except BaseException as reload_error: receipt['rollback']['reload_error']=type(reload_error).__name__
        else: receipt['rollback']['reconciliation_required']='supervisor shutdown not proved; pointers/configuration preserved'
        try:
            rows=B.installed(logs/'rpm-after-failure.txt');receipt['package_failure_observation']={
                'count':len(rows),'sha256':B.digest(B.canonical(rows)),'equals_retained_before':B.digest(B.canonical(rows))==INVENTORY,
                'system_package_mutations_requested':0}
            receipt['after_failure']=B.snapshot(logs,'after-failure')
        except BaseException as observed_error: receipt['failure_state_observation_error']=type(observed_error).__name__
    finally:
        receipt['supervisor_final']=observe_supervisor(logs,'final',since)
        B.write(staged/'bootstrap-result.json',B.canonical(receipt));B.write(staged/'operation-receipt.json',B.canonical(receipt))
        exported=output/'bootstrap-evidence';exported.mkdir(mode=0o700)
        for path in sorted(staged.iterdir()):
            if path.is_file():
                B.write(exported/path.name,B.regular(path,4*1024*1024));os.chown(exported/path.name,1000,1000)
        for path in sorted(logs.iterdir()):
            B.write(exported/path.name,B.regular(path,8*1024*1024));os.chown(exported/path.name,1000,1000)
        os.chown(exported,1000,1000);trees={}
        fixture_id='bootstrap-fixture-'+OLD_REQUEST
        trees[fixture_id]=B.export_tree(B.STATE/'episodes'/fixture_id,output/fixture_id)
        for prefix in ('database-arxiv','news-nasa','repository-openmdao'):
            episode=prefix+'-'+request['request_id'];trees[episode]=(B.export_tree(B.STATE/'episodes'/episode,output/episode) if safe_export else
                {'exported':False,'reason':'supervisor or isolated worker shutdown not proved','retained_path':str(B.STATE/'episodes'/episode)})
        trees['canonical_registry']=(B.export_tree(B.STATE/'registry',output/'canonical-browser-registry') if safe_export else
            {'exported':False,'reason':'supervisor or isolated worker shutdown not proved','retained_path':str(B.STATE/'registry')})
        B.write(output/'raw-evidence-export.json',B.canonical(trees));os.chown(output/'raw-evidence-export.json',1000,1000)
        check_parent=B.operation_directory(output_path);check_leaf=B.operation_directory(output_path/'root-evidence',owner=0)
        try:
            for first,second in ((parent_fd,check_parent),(leaf_fd,check_leaf)):
                a=os.fstat(first);b=os.fstat(second)
                if (a.st_dev,a.st_ino)!=(b.st_dev,b.st_ino): raise B.BootstrapError('activation evidence path moved during publication')
        finally: os.close(check_parent);os.close(check_leaf);os.close(lock)
    if receipt['status']=='failed': raise B.BootstrapError('activation successor failed; state and raw evidence retained')
    return receipt
