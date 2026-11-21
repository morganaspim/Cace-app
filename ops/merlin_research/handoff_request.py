"""Fixed native retained-source handoff; no acquisition, installation or model IO.

All request inputs are data. Source files and installed runtime identities come
from the pinned workflow, not from request fields. The only new research writes
are the already published handoff module's fixed same-project records.
"""
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import time
import uuid

from handoff_support import (OperationError, canonical, command, decode, digest,
    directory_descriptor, duration_us, publish_evidence, read, root_directory,
    safe_episode, write)

STATE = Path('/var/lib/merlin-public-browser')
REGISTRY = STATE / 'registry'
OPERATIONS = STATE / 'handoff-operations'
BROWSER = Path('/opt/merlin-public-browser')
PRIVATE = Path('/opt/merlin-dot-private')
PROJECT = 'merlin-browser-research'
INSTALLED_FIELDS = {'schema','runtime_sha256','runtime_manifest_sha256','host_config_sha256',
    'service_config_sha256','unit_sha256','browser_uid','browser_gid','opc_gid',
    'expert_source_commit','bootstrap_run_id','bootstrap_workflow_commit'}
PRODUCT_FIELDS = {'schema','repository','source_commit','module','tests','native_test_count',
    'program','private_release_sha256','private_manifest_sha256','private_dependencies',
    'installed_browser_pins'}
DEPENDENCIES = {'python/merlin/__init__.py','python/merlin/artifact_ref.py',
    'python/merlin/project_registry.py','python/merlin/scientific_loop.py',
    'python/dot_ai_os/__init__.py','python/dot_ai_os/bridge.py','python/dot_ai_os/research_protocol.py'}
SOURCE_NAMES = {'module':'browser_research_handoff.py','tests':'test_browser_research_handoff.py',
                'program':'program.json'}
MAX_RECORD = 2 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise OperationError(message)


def hash_value(value, length=64):
    require(isinstance(value,str) and re.fullmatch('[0-9a-f]{%d}' % length,value), 'exact lowercase digest required')
    return value


def identifier(value):
    require(isinstance(value,str) and str(uuid.UUID(value))==value, 'canonical request UUID required')
    return value


def publication_ref(value, episode):
    require(type(value) is dict and set(value)=={'schema','project_id','logical_path','version','sha256'},
            'exact publication ArtifactRef required')
    require(value['schema']=='merlin-artifact-ref/1' and value['project_id']==PROJECT
            and value['logical_path']=='browser/episodes/'+safe_episode(episode)+'/publication.json'
            and type(value['version']) is int and value['version']==1, 'fixed project publication identity differs')
    hash_value(value['sha256'])
    return value


def operation_request(value):
    require(type(value) is dict and set(value)=={'schema','request_id','operation','created_at','arguments'}
            and value['schema']=='merlin-browser-handoff-operation-request/1', 'exact handoff operation fields required')
    identifier(value['request_id'])
    require(isinstance(value['created_at'],str) and re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ',value['created_at']),
            'UTC operation timestamp required')
    require(len(canonical(value))<=16384 and type(value['arguments']) is dict, 'bounded typed operation required')
    args=value['arguments']
    if value['operation']=='submit':
        require(set(args)=={'episode_id','publication_ref','launch_receipt_sha256'}, 'fixed saved-source submit fields required')
        publication_ref(args['publication_ref'],args['episode_id']);hash_value(args['launch_receipt_sha256'])
        return {'schema':'merlin-browser-research-handoff-request/1','request_id':value['request_id'],
                'episode_id':args['episode_id'],'publication_ref':args['publication_ref']}
    require(value['operation']=='status' and set(args)=={'handoff_request_id'}, 'only saved handoff submit/status are available')
    return {'operation':'status','request_id':identifier(args['handoff_request_id'])}


def validate_installed(pins):
    require(type(pins) is dict and set(pins)==INSTALLED_FIELDS
            and pins['schema']=='merlin-browser-installed-operation-pins/1', 'actual installed browser pins required')
    for name in ('runtime_sha256','runtime_manifest_sha256','host_config_sha256','service_config_sha256','unit_sha256'):
        hash_value(pins[name])
    for name in ('expert_source_commit','bootstrap_workflow_commit'):
        hash_value(pins[name],40)
    for name in ('browser_uid','browser_gid','opc_gid','bootstrap_run_id'):
        require(type(pins[name]) is int and pins[name]>0, 'actual positive installed identity required')
    require(pins['browser_uid'] not in (982,1000), 'dedicated browser UID required')


def validate_product(pins):
    require(type(pins) is dict and set(pins)==PRODUCT_FIELDS
            and pins['schema']=='merlin-browser-handoff-product-pins/1'
            and pins['repository']=='Mannyspiro/expert-robot'
            and type(pins['native_test_count']) is int and pins['native_test_count']==23,
            'fixed published handoff product pins required')
    hash_value(pins['source_commit'],40)
    for name in ('private_release_sha256','private_manifest_sha256'):
        hash_value(pins[name])
    expected={'module':'python/merlin/browser_research_handoff.py','tests':'tests/test_browser_research_handoff.py',
              'program':'config/merlin/research-program.json'}
    for name,path in expected.items():
        pin=pins[name]
        require(type(pin) is dict and pin.get('path')==path and type(pin.get('bytes')) is int
                and 0<pin['bytes']<=131072, 'fixed bounded product file required')
        hash_value(pin['sha256'])
    rows=pins['private_dependencies']
    require(isinstance(rows,list) and len(rows)==7 and {row['path'] for row in rows}==DEPENDENCIES,
            'exact seven existing dependency identities required')
    for row in rows:
        require(type(row.get('bytes')) is int and 0<row['bytes']<=131072, 'bounded dependency source required')
        hash_value(row['sha256'])


def check_bytes(raw,pin):
    require(len(raw)==pin['bytes'] and digest(raw)==pin['sha256'], 'fixed source bytes differ')
    if 'git_blob' in pin:
        require(hashlib.sha1(('blob %d\0'%len(raw)).encode()+raw).hexdigest()==pin['git_blob'], 'fixed source Git blob differs')


def current_release(prefix, digest_value):
    root_directory(prefix);release=root_directory(prefix/'releases'/digest_value)
    link=(prefix/'current').lstat()
    require(stat.S_ISLNK(link.st_mode) and link.st_uid==0
            and os.readlink(prefix/'current')==str(release), 'active release link differs')
    return release


def private_runtime(product):
    release=current_release(PRIVATE,product['private_release_sha256'])
    raw=read(release/'manifest.json',131072)
    require(digest(raw)==product['private_manifest_sha256'], 'private release manifest differs')
    manifest=decode(raw);observed=[]
    require(type(manifest.get('files')) is dict, 'private manifest source map required')
    for pin in product['private_dependencies']:
        root_directory((release/pin['path']).parent)
        require(manifest['files'].get(pin['path'])==pin['sha256'], 'private dependency manifest binding differs')
        body=read(release/pin['path'],pin['bytes']);check_bytes(body,pin)
        observed.append({'path':pin['path'],'bytes':len(body),'sha256':digest(body)})
    return release,{'release_sha256':product['private_release_sha256'],
                    'manifest_sha256':digest(raw),'dependencies':observed}


def installed_runtime(pins,logs,label):
    validate_installed(pins);release=current_release(BROWSER,pins['runtime_sha256'])
    locations=((Path('/etc/merlin-public-browser/host.json'),'host_config_sha256'),
        (Path('/etc/merlin-public-browser/service.json'),'service_config_sha256'),
        (Path('/etc/systemd/system/merlin-public-browser.service'),'unit_sha256'),
        (release/'manifest.json','runtime_manifest_sha256'))
    for path,name in locations:
        root_directory(path.parent)
        require(digest(read(path,1048576))==pins[name], 'installed browser source/configuration differs')
    manifest=decode(read(release/'manifest.json',1048576))
    require(manifest.get('schema')=='merlin-browser-runtime/1'
            and manifest.get('expert_source_commit')==pins['expert_source_commit'], 'installed browser source commit differs')
    require(isinstance(manifest.get('files'),list) and 1<=len(manifest['files'])<=64, 'bounded installed manifest required')
    names=set()
    for item in manifest['files']:
        name=item['path'];path=Path(name)
        require(isinstance(name,str) and not path.is_absolute() and '..' not in path.parts
                and name.startswith(('python/','bin/')) and name not in names, 'installed browser file path differs')
        names.add(name);root_directory((release/path).parent)
        check_bytes(read(release/path,item['bytes']),item)
    host=decode(read('/etc/merlin-public-browser/host.json',65536))
    config=decode(read('/etc/merlin-public-browser/service.json',65536))
    require(host['browser_uid']==pins['browser_uid'] and host['browser_gid']==pins['browser_gid']
            and config['allowed_uids']==[0,982] and config['socket_gid']==pins['opc_gid']
            and config['registry_root']==str(REGISTRY) and config['project_id']==PROJECT,
            'installed browser authority/project differs')
    raw=command(['/usr/bin/systemctl','show','merlin-public-browser.service','--no-pager',
        '--property=ActiveState','--property=MainPID','--property=User'],logs/('browser-'+label+'.txt'))
    service=dict(line.split('=',1) for line in raw.decode().splitlines() if '=' in line)
    require(service.get('ActiveState')=='active' and service.get('User')=='root'
            and service.get('MainPID','0').isdigit() and int(service['MainPID'])>0,
            'accepted browser supervisor unavailable')
    return release,{'runtime_sha256':pins['runtime_sha256'],'manifest_sha256':pins['runtime_manifest_sha256'],
                    'host_config_sha256':pins['host_config_sha256'],'service_config_sha256':pins['service_config_sha256'],
                    'unit_sha256':pins['unit_sha256'],'service':service}


def controller_envelope(execution,logs):
    unit='merlin-browser-handoff-%d-%d.service'%(execution['run_id'],execution['run_attempt'])
    fields=('MainPID','ControlGroup','RuntimeMaxUSec','TimeoutStopUSec','KillMode','MemoryMax','MemorySwapMax',
            'TasksMax','CPUQuotaPerSecUSec','PrivateNetwork','NoNewPrivileges','RestrictAddressFamilies')
    raw=command(['/usr/bin/systemctl','show',unit,'--no-pager']+['--property='+key for key in fields],logs/'controller-envelope.txt')
    value=dict(line.split('=',1) for line in raw.decode().splitlines() if '=' in line)
    group='/system.slice/'+unit
    require(value.get('MainPID')==str(os.getpid()) and value.get('ControlGroup')==group
        and value.get('KillMode')=='control-group' and value.get('MemoryMax')=='536870912'
        and value.get('MemorySwapMax')=='0' and value.get('TasksMax')=='64'
        and duration_us(value.get('RuntimeMaxUSec'))==150000000
        and duration_us(value.get('TimeoutStopUSec'))==15000000
        and duration_us(value.get('CPUQuotaPerSecUSec'))==500000
        and value.get('PrivateNetwork')=='yes' and value.get('NoNewPrivileges')=='yes'
        and value.get('RestrictAddressFamilies')=='AF_UNIX'
        and '0::'+group in read('/proc/self/cgroup',16384).decode().splitlines(),
        'actual bounded no-network controller envelope differs')
    return value


def retained_file(directory,name,pin):
    """Read exact public source from an anchored runner directory; never execute it here."""
    parent=directory_descriptor(directory)
    try:
        info=os.fstat(parent)
        require(info.st_uid==1000 and stat.S_IMODE(info.st_mode)==0o700, 'protected runner source directory required')
        descriptor=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
        try:
            info=os.fstat(descriptor)
            require(stat.S_ISREG(info.st_mode) and info.st_uid==1000 and info.st_nlink==1
                    and info.st_size==pin['bytes'], 'bounded runner-owned public source required')
            pieces=[];total=0
            while True:
                raw=os.read(descriptor,min(65536,pin['bytes']+1-total))
                if not raw: break
                pieces.append(raw);total+=len(raw)
                require(total<=pin['bytes'], 'staged public source grew')
            raw=b''.join(pieces);check_bytes(raw,pin);return raw
        finally: os.close(descriptor)
    finally: os.close(parent)


def stage_product(product,source_directory):
    target=root_directory(OPERATIONS/'sources',create=True,mode=0o755)/digest(canonical(product))
    if not target.exists(): target.mkdir(mode=0o755)
    root_directory(target)
    for key,name in SOURCE_NAMES.items():
        destination=target/name;pin=product[key]
        if destination.exists(): check_bytes(read(destination,pin['bytes']),pin)
        else: write(destination,retained_file(source_directory,name,pin),mode=0o444)
    return target


def import_product(private,stage,product):
    require(not any(name in sys.modules for name in ('merlin','dot_ai_os')), 'clean pinned root import context required')
    sys.path.insert(0,str(private/'python'))
    import merlin
    from merlin.project_registry import MerlinRegistry
    spec=importlib.util.spec_from_file_location('merlin.browser_research_handoff',str(stage/'browser_research_handoff.py'))
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    for name,value in list(sys.modules.items()):
        if name in ('merlin','dot_ai_os') or name.startswith(('merlin.','dot_ai_os.')):
            location=Path(value.__file__).resolve()
            expected=stage/'browser_research_handoff.py' if name==spec.name else private/'python'/Path(*name.split('.'))
            if name in ('merlin','dot_ai_os'): expected=expected/'__init__.py'
            elif name!=spec.name: expected=expected.with_suffix('.py')
            require(location==expected.resolve(), 'import origin escaped pinned source closure')
    require(module.PROJECT==PROJECT and module.REGISTRY_ROOT==str(REGISTRY), 'published handoff root/project differs')
    return module,MerlinRegistry


CHILD = r'''import importlib.util,json,os,pathlib,sys,unittest
private,stage,program,source,operation,argument=sys.argv[1:]
sys.path.insert(0,str(pathlib.Path(private)/'python'))
from merlin.project_registry import MerlinRegistry
spec=importlib.util.spec_from_file_location('merlin.browser_research_handoff',str(pathlib.Path(stage)/'browser_research_handoff.py'))
module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
if operation=='tests':
    t=importlib.util.spec_from_file_location('native_handoff_tests',str(pathlib.Path(stage)/'test_browser_research_handoff.py'))
    tests=importlib.util.module_from_spec(t);t.loader.exec_module(tests)
    suite=unittest.defaultTestLoader.loadTestsFromModule(tests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    summary={'tests':result.testsRun,'errors':len(result.errors),'failures':len(result.failures),'skips':len(result.skipped),'uid':os.getuid()}
    print(json.dumps(summary,sort_keys=True),flush=True)
    sys.exit(0 if result.wasSuccessful() and not result.skipped and result.testsRun==23 else 1)
if operation!='status': raise ValueError('fixed child operation required')
worker=module.BrowserResearchHandoff(MerlinRegistry('/var/lib/merlin-public-browser/registry'),
    source_commit=source,program_bytes=pathlib.Path(program).read_bytes(),authorize=lambda action,binding: action=='read')
print(json.dumps({'pid':os.getpid(),'uid':os.getuid(),'response':worker.status(argument)},sort_keys=True),flush=True)
'''


def product_child(private,stage,product,operation,argument,log,*,runner_gid):
    require(operation in ('tests','status'), 'fixed source-only child required')
    argv=['/usr/bin/python3','-I','-B','-c',CHILD,str(private),str(stage),str(stage/'program.json'),
          product['source_commit'],operation,argument]
    raw=command(argv,log,seconds=45 if operation=='tests' else 30,
                user=1000 if operation=='tests' else None,group=runner_gid if operation=='tests' else None)
    answer=decode(raw.decode().splitlines()[-1])
    if operation=='tests':
        require(answer.get('tests')==23 and answer.get('errors')==answer.get('failures')==answer.get('skips')==0
                and answer.get('uid')==1000, 'native 23-test handoff gate differs')
    else:
        require(type(answer.get('pid')) is int and answer['pid']!=os.getpid() and answer.get('uid')==0,
                'actual separate status process required')
    return answer


def admit_receipt(receipt,episode,release,expected_sha,raw,manifest_raw,actions_raw):
    require(digest(raw)==expected_sha and receipt.get('schema')=='merlin-browser-launch/1'
            and receipt.get('episode_id')==episode and receipt.get('release')==str(release)
            and receipt.get('status')=='succeeded' and receipt.get('all_workers_stopped') is True
            and receipt.get('scratch_unmounted') is True and 'fixture_command' not in receipt,
            'accepted stopped-worker launch receipt required')
    require(type(receipt.get('model_calls')) is int and receipt['model_calls']==0
            and type(receipt.get('external_model_cost_usd')) is int and receipt['external_model_cost_usd']==0
            and receipt.get('qualification') is False and receipt.get('promotion_authority') is False,
            'browser launch authority/model scope differs')
    require(receipt.get('actions_sha256')==digest(actions_raw), 'launch action bytes differ')
    shutdown=receipt.get('unit_shutdown')
    require(type(shutdown) is dict and set(shutdown)=={'broker','renderer'}, 'both real browser worker shutdowns required')
    for row in shutdown.values():
        require(row.get('ActiveState') in ('inactive','failed') and row.get('MainPID') in ('0',''), 'worker shutdown receipt differs')
    output=receipt.get('output')
    require(type(output) is dict and isinstance(output.get('files'),list) and 1<=len(output['files'])<=321,
            'bounded stopped output inventory required')
    rows=[row for row in output['files'] if row.get('path')=='episode.json']
    require(len(rows)==1 and rows[0].get('bytes')==len(manifest_raw) and rows[0].get('sha256')==digest(manifest_raw),
            'stopped output manifest binding differs')
    manifest=decode(manifest_raw)
    require(manifest.get('schema')=='merlin-public-browser-episode/1' and manifest.get('episode_id')==episode
            and manifest.get('status')=='completed' and manifest.get('limits')==receipt.get('limits'),
            'accepted browser episode manifest differs')
    return manifest


def admission(arguments,release,installed,registry,logs,evidence):
    episode=safe_episode(arguments['episode_id']);ref=publication_ref(arguments['publication_ref'],episode)
    target=root_directory(STATE/'episodes'/episode);root_directory(target/'request');root_directory(target/'result')
    raw=read(target/'launch-receipt.json',MAX_RECORD);receipt=decode(raw)
    manifest_raw=read(target/'result'/'episode.json',131072)
    actions_raw=read(target/'request'/'actions.json',65536)
    manifest=admit_receipt(receipt,episode,release,arguments['launch_receipt_sha256'],raw,manifest_raw,actions_raw)
    require(manifest.get('isolation',{}).get('uid')==installed['browser_uid']
            and manifest.get('isolation',{}).get('euid')==installed['browser_uid'], 'accepted renderer UID differs')
    observed={}
    for role in ('broker','renderer'):
        unit='merlin-browser-'+role+'-'+episode+'.service'
        value=command(['/usr/bin/systemctl','show',unit,'--no-pager','--property=ActiveState',
            '--property=MainPID','--property=ControlGroup'],logs/('stopped-'+role+'.txt'))
        row=dict(line.split('=',1) for line in value.decode().splitlines() if '=' in line)
        require(row.get('ActiveState') in ('inactive','failed') and row.get('MainPID') in ('0',''), 'browser worker is not stopped')
        group=row.get('ControlGroup','')
        if group:
            require(group=='/system.slice/'+unit, 'worker cgroup path differs')
            members=Path('/sys/fs/cgroup'+group)/'cgroup.procs'
            if members.exists(): require(not read(members,65536).strip(), 'browser worker cgroup is populated')
        observed[role]=row
    publication_raw=registry.read_artifact_ref(ref,max_bytes=262144)['content'];publication=decode(publication_raw)
    require(publication.get('schema')=='merlin-browser-publication/1' and publication.get('episode_id')==episode
            and publication.get('status')=='completed' and publication.get('manifest_sha256')==digest(manifest_raw),
            'canonical publication is not the admitted stopped episode')
    manifest_ref=publication.get('manifest_ref')
    require(type(manifest_ref) is dict and manifest_ref.get('project_id')==PROJECT
            and manifest_ref.get('logical_path')=='browser/episodes/'+episode+'/episode.json'
            and manifest_ref.get('version')==1 and manifest_ref.get('sha256')==digest(manifest_raw)
            and registry.read_artifact_ref(manifest_ref,max_bytes=131072)['content']==manifest_raw,
            'canonical manifest differs from stopped output')
    for name,body in (('accepted-launch-receipt.json',raw),('accepted-episode.json',manifest_raw),
                      ('accepted-actions.json',actions_raw),('accepted-publication.json',publication_raw)):
        write(evidence/name,body)
    return {'episode_id':episode,'publication_ref':ref,'launch_receipt_sha256':digest(raw),
            'manifest_sha256':digest(manifest_raw),'actions_sha256':digest(actions_raw),'current_workers':observed,
            'browser_runtime_sha256':installed['runtime_sha256'],'new_browser_calls':0}


def effective_operation(operation,prior_intent):
    return 'status' if operation=='status' or prior_intent else 'submit'


def check_response(value):
    require(type(value) is dict and value.get('status') in ('recorded','reconciliation_needed','not_found')
            and value.get('execution_retried') is False, 'fixed handoff response differs')
    if value['status']=='recorded':
        result=value.get('result')
        require(type(result) is dict and result.get('schema')=='merlin-browser-research-handoff-result/1'
                and result.get('domain_execution')=='not_run' and result.get('new_browser_calls')==0
                and result.get('model_calls')==0 and result.get('external_model_cost_usd')==0
                and result.get('qualification') is False and result.get('promotion_authority') is False,
                'handoff scope/cost receipt differs')
    return value['status']


def export_canonical(registry,response,destination):
    """Retain exact public source/plan/measurement/review bytes, never private state."""
    root_directory(destination,create=True);refs=[];seen=set();total=0
    if response['status']=='recorded':
        result=response['result'];refs=[response['result_ref']]+[result[name] for name in
            ('intent_ref','program_ref','plan_ref','measurement_ref','review_ref')]
        measurement=decode(registry.read_artifact_ref(result['measurement_ref'],max_bytes=262144)['content'])
        refs += [row['artifact_ref'] for row in measurement['input_artifacts']]
    else:
        refs=[response[name] for name in ('intent_ref','failure_ref') if response.get(name)]
    require(len(refs)<=340, 'canonical export count ceiling')
    rows=[]
    for ref in refs:
        require(type(ref) is dict and ref.get('project_id')==PROJECT and ref.get('version')==1,
                'cross-project or revised export rejected')
        path=ref['logical_path'];identity=canonical(ref)
        require(isinstance(path,str) and not Path(path).is_absolute() and '..' not in Path(path).parts
                and path.startswith(('browser/episodes/','research/','research-handoffs/')), 'fixed canonical export scope required')
        if identity in seen: continue
        seen.add(identity);raw=registry.read_artifact_ref(ref,max_bytes=12*1024*1024)['content'];total+=len(raw)
        require(total<=16*1024*1024, 'canonical export byte ceiling')
        target=destination/path;root_directory(target.parent,create=True);write(target,raw)
        rows.append({'path':path,'artifact_ref':ref,'bytes':len(raw),'sha256':digest(raw)})
    return {'files':rows,'bytes':total,'original_sources_reacquired':False}


def run(request,execution,installed,product,source_directory,output):
    require(os.geteuid()==0,'fixed root coordinator required')
    os.umask(0o022);inner=operation_request(request);validate_installed(installed);validate_product(product)
    require(execution.get('repository')=='morganaspim/Cace-app'
        and execution.get('ref')=='refs/heads/merlin/browser-operations-20261121'
        and execution.get('runner')=='cace-oci-a1'
        and type(execution.get('run_id')) is int and execution['run_id']>0
        and type(execution.get('run_attempt')) is int and execution['run_attempt']>0,
        'fixed native request identity required')
    hash_value(execution.get('workflow_commit'),40)
    output=Path(output)
    require(output.name=='operation' and output.parent.name=='merlin-browser-handoff-%d-%d'%(execution['run_id'],execution['run_attempt']),
            'fixed evidence destination required')
    root_directory(OPERATIONS,create=True,mode=0o755);root_directory(REGISTRY)
    require(stat.S_IMODE(OPERATIONS.stat().st_mode)==0o755, 'traversable coordinator source root required')
    lock=os.open(str(OPERATIONS/'requests.lock'),os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    info=os.fstat(lock);require(stat.S_ISREG(info.st_mode) and info.st_uid==0 and not info.st_mode&0o077,'safe coordinator lock required')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    root_directory(OPERATIONS/'requests',create=True)
    record=OPERATIONS/'requests'/request['request_id'];existed=record.exists() or record.is_symlink()
    if existed: root_directory(record)
    else: record.mkdir(mode=0o700)
    invocation=record/('%d-%d'%(execution['run_id'],execution['run_attempt']));invocation.mkdir(mode=0o700)
    logs=invocation/'logs';logs.mkdir(mode=0o700);evidence=invocation/'evidence';evidence.mkdir(mode=0o700)
    receipt={'schema':'merlin-browser-handoff-native-operation/1','request':request,'execution':execution,
        'installed_pins':installed,'product_pins':product,'status':'started','new_browser_calls':0,'model_calls':0,
        'external_model_cost_usd':0,'software_installation':False,'provider_contacts':0,
        'domain_execution':'not_run','qualification':False,'promotion_authority':False}
    registry=None;response=None
    try:
        receipt['controller_envelope']=controller_envelope(execution,logs)
        for path in (REGISTRY,OPERATIONS,output.parent):
            require(shutil.disk_usage(path).free>=1024*1024*1024+84*1024*1024,'fixed evidence reserve unavailable')
        release,browser_before=installed_runtime(installed,logs,'before')
        private,private_before=private_runtime(product)
        receipt['browser_before']=browser_before;receipt['private_before']=private_before
        stage=stage_product(product,source_directory)
        receipt['native_handoff_tests']=product_child(private,stage,product,'tests','',logs/'native-handoff-tests.txt',runner_gid=installed['opc_gid'])
        # Recheck the actual installed dependency root after native controls, before importing it as root.
        require(private_runtime(product)[1]==private_before,'private dependencies changed during native tests')
        module,RegistryClass=import_product(private,stage,product);registry=RegistryClass(REGISTRY)
        target_id=inner['request_id']
        if request['operation']=='submit': arguments=request['arguments']
        else:
            original=OPERATIONS/'requests'/target_id/'intent.json';root_directory(original.parent)
            previous=decode(read(original,MAX_RECORD))
            require(previous.get('request',{}).get('operation')=='submit'
                    and previous.get('request',{}).get('request_id')==target_id
                    and previous.get('installed_pins')==installed and previous.get('product_pins')==product,
                    'original admitted handoff request binding differs')
            operation_request(previous['request']);arguments=previous['request']['arguments']
        receipt['source_admission']=admission(arguments,release,installed,registry,logs,evidence)
        binding={'schema':'merlin-browser-handoff-native-intent/1','request':request,'request_sha256':digest(canonical(request)),
            'handoff_request_id':target_id,'installed_pins':installed,'product_pins':product,
            'source_admission':receipt['source_admission']}
        intent_path=record/'intent.json';prior=intent_path.exists() or intent_path.is_symlink()
        if prior:
            previous=decode(read(intent_path,MAX_RECORD))
            require(previous.get('request_sha256')==binding['request_sha256'] and previous.get('request')==request
                and previous.get('handoff_request_id')==target_id and previous.get('installed_pins')==installed
                and previous.get('product_pins')==product, 'native request identity reused with different inputs')
        elif existed: raise OperationError('incomplete prior native request requires reconciliation')
        else: write(intent_path,canonical(binding))
        effective=effective_operation(request['operation'],prior);deadline=time.monotonic()+45
        def authorize(action,identity):
            return (time.monotonic()<deadline and action in (('read','write') if effective=='submit' else ('read',))
                and identity.get('source_commit')==product['source_commit']
                and identity.get('executor_sha256')==product['module']['sha256']
                and identity.get('program_sha256')==product['program']['sha256'])
        worker=module.BrowserResearchHandoff(registry,source_commit=product['source_commit'],
            program_bytes=read(stage/'program.json',product['program']['bytes']),authorize=authorize)
        response=worker.submit(inner) if effective=='submit' else worker.status(target_id)
        state=check_response(response);receipt['response']=response;receipt['handoff_status']=state
        receipt['idempotency']={'prior_native_intent':prior,'effective_operation':effective,'measurement_retried':False}
        write(invocation/'response.json',canonical(response))
        if state=='recorded':
            child=product_child(private,stage,product,'status',target_id,logs/'fresh-process-status.txt',runner_gid=installed['opc_gid'])
            check_response(child['response'])
            require(child['response'].get('result_ref')==response.get('result_ref')
                    and child['response'].get('result')==response.get('result'), 'fresh process retained result differs')
            receipt['fresh_process_readback']=child
        require(private_runtime(product)[1]==private_before,'private runtime source changed during handoff')
        _,browser_after=installed_runtime(installed,logs,'after')
        require(browser_after==browser_before,'browser runtime/service changed during handoff')
        receipt['browser_after']=browser_after;receipt['private_after']=private_before
        receipt['status']='completed' if state=='recorded' else 'reconciliation_needed'
        if not prior: write(record/'outcome.json',canonical({'schema':'merlin-browser-handoff-native-outcome/1',
            'request_sha256':binding['request_sha256'],'response':response,'status':receipt['status'],
            'first_invocation':invocation.name,'measurement_retried':False}))
    except BaseException as error:
        receipt['status']='failed';receipt['error']={'type':type(error).__name__,'message':str(error)[:2000]}
    finally:
        if registry is not None and response is not None:
            try: receipt['canonical_export']=export_canonical(registry,response,evidence/'canonical')
            except BaseException as error:
                receipt['status']='failed';receipt['export_error']={'type':type(error).__name__,'message':str(error)[:1000]}
        write(invocation/'operation-receipt.json',canonical(receipt));write(evidence/'operation-receipt.json',canonical(receipt))
        for name in ('intent.json','outcome.json'):
            if (record/name).exists(): write(evidence/name,read(record/name,MAX_RECORD))
        if (invocation/'response.json').exists(): write(evidence/'response.json',read(invocation/'response.json',MAX_RECORD))
        for path in sorted(logs.iterdir()): write(evidence/path.name,read(path,MAX_RECORD))
        delivery={'schema':'merlin-browser-handoff-evidence-delivery/1','operation_status':receipt['status'],
            'operation_receipt_sha256':digest(canonical(receipt)),'retained_host_directory':str(evidence),'status':'started'}
        try:
            delivery['copied']=publish_evidence(evidence,output);delivery['status']='published'
        except BaseException as error:
            delivery['status']='failed';delivery['error']={'type':type(error).__name__,'message':str(error)[:1000]}
            raise
        finally:
            try:
                write(invocation/'publication-result.json',canonical(delivery));print(canonical(delivery).decode(),end='',flush=True)
            finally: os.close(lock)
    require(receipt['status']=='completed','native handoff did not complete; retained exact evidence')
    return receipt
