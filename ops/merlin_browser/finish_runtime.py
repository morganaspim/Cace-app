"""One inspected runtime-only successor; no RPM, pip, network or model install.

Reuse the exact installed dependency state. Retain every failed operation and
the old immutable release. Activate a new launcher release only after the
remaining bounded native fixture/public-source acceptance sequence.
"""
import fcntl
import hashlib
import os
from pathlib import Path
import platform
import pwd
import re
import stat
import sys
import uuid

import bootstrap_browser as B

OPERATION='finish-loader-44944424850'
OLD_REQUEST='04d38719-4c94-4059-988b-9081375fd209'
OLD_RUN=44944424850
OLD_COMMIT='b11bf02997dc720535b7d729d60e3a7919892a9a'
OLD_INTENT='b641bd1d8f2d5d6f5a7a016e74f8cf942a92c15c2d7db0b1d752d66709d3801f'
OLD_RESULT='0ce1241325e81b33e51d487bfd9e0c0b2b8f5531335fceb945e3155920bb8797'
OLD_LINEAGE='2cbac1011c002262d8239c7e8b21c3623a6290e3d3b8e38f353c5e887687df09'
OLD_INVENTORY='498f3ea85fe0dfcebbd2871c5029e1f1216ea2a6031f4ef20bd0eefaa69d79fd'
OLD_RUNTIME='58f9b4fee8b03db777a07e76149ef5fedcc8c1c9b3309c16499b3cadecfbac90'
OLD_MANIFEST='51c68b5f7ceb10debb270ffdde2409648968dddd11e5e93c3f989802ca25b8d8'
OLD_HOST='728199723582985bc21357e72059fab26a0220e01a6d109f36288b39ecbd8600'
NEW_RUNTIME='5b967b6364bb8d3213c357e148c43073c309ab45d13338fe577d13565f8d0e9d'
NEW_MANIFEST='ea5ea521f055273cd6d82c8a164f6e713172ecf0db51bddefc915a3548ff1ef6'
LOADER_PATH='/usr/lib/ld-linux-aarch64.so.1'
LOADER_SHA='49d528c1bc76e851bdc1db2ffcacd69b7f969c461a23741b9f5b8be4318c3403'
NATIVE_SHA='22870374b6f2acfa00ac7c54a09eb30aacb1cdac932aba97e654e3dff458318f'
PYTHON_SHA='59acf176bc9571b65545d2d08f9db5271d14855431f9ccafc1239bc81b5a8e8d'
NODE_SHA='d0b9f94a9771bba3c30a54f0aee622fa0bee37be684cc1df6da2d3448606d98d'
INSPECTION={'run_id':44944977868,'workflow_commit':'4c7068c80f75c84b7e556836e6167dc1168f4740',
    'artifact_sha256':'abc5ee857c894563d56d74189ab31c4f4e28739201d8687bdfe63bcf60e1c4c1'}
OLD_RELEASE=B.PREFIX/'releases'/OLD_RUNTIME


def validate_request(request,execution):
    if (not isinstance(request,dict) or set(request)!={'schema','request_id','operation','created_at'}
        or request.get('schema')!='merlin-browser-runtime-request/1' or request.get('operation')!=OPERATION
        or not isinstance(request.get('request_id'),str) or str(uuid.UUID(request['request_id']))!=request['request_id']
        or request['request_id']==OLD_REQUEST or not isinstance(request.get('created_at'),str)
        or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ',request['created_at'])):
        raise B.BootstrapError('exact inspected runtime successor request required')
    if (execution.get('repository')!='morganaspim/Cace-app'
        or execution.get('ref')!='refs/heads/merlin/browser-operations-20261121'
        or execution.get('runner')!='cace-oci-a1' or execution.get('run_attempt')!=1
        or type(execution.get('run_id')) is not int or execution['run_id']<=0
        or not re.fullmatch('[0-9a-f]{40}',execution.get('workflow_commit',''))):
        raise B.BootstrapError('fixed native runtime successor execution required')


def checked_raw(path,expected,maximum=4*1024*1024):
    B.rooted(Path(path).parent,0o700);info=Path(path).lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid!=0 or info.st_mode&0o022:
        raise B.BootstrapError('root-owned retained operation input required')
    raw=B.regular(path,maximum)
    if B.digest(raw)!=expected: raise B.BootstrapError('retained operation identity differs: '+str(path))
    return raw


def prior_receipt(raw):
    if B.digest(raw)!=OLD_RESULT: raise B.BootstrapError('exact installed predecessor result required')
    prior=B.decode(raw)
    if (prior.get('status')!='failed' or prior.get('request',{}).get('request_id')!=OLD_REQUEST
        or prior.get('execution',{}).get('run_id')!=OLD_RUN
        or prior.get('execution',{}).get('workflow_commit')!=OLD_COMMIT
        or prior.get('rpm_install_completed') is not True
        or prior.get('package_stages_completed')!=['zvbi-library-only','remaining-dependencies']
        or prior.get('accounts')!={'authorized_client_uid':982,'browser_gid':980,'browser_uid':980,
            'opc_gid':1000,'private_client_effective_group_verified':True}
        or prior.get('before')!=prior.get('after_failure')
        or prior.get('error')!={'type':'LaunchError','message':'browser launch failed; preserved receipt and raw output'}
        or prior.get('runtime_pin',{}).get('sha256')!=OLD_RUNTIME):
        raise B.BootstrapError('ambiguous predecessor cannot enter runtime-only continuation')
    rows=prior.get('package_failure_observation',{}).get('installed_packages')
    if not isinstance(rows,list) or len(rows)!=971 or B.digest(B.canonical(rows))!=OLD_INVENTORY:
        raise B.BootstrapError('exact retained installed package state required')
    return prior


def clone_venv(source,destination,ledger_path):
    """Copy the existing immutable venv; preserve only its observed lib64 link."""
    B.rooted(source);destination.mkdir(mode=0o755,exist_ok=False)
    entries=[];total=0;count=0
    for parent,dirs,files in os.walk(source,followlinks=False):
        dirs.sort();files.sort();relative=Path(parent).relative_to(source)
        if len(relative.parts)>16: raise B.BootstrapError('venv depth ceiling')
        B.rooted(Path(parent))
        for name in list(dirs):
            path=Path(parent)/name;rel=path.relative_to(source);info=path.lstat();target=destination/rel
            if stat.S_ISLNK(info.st_mode):
                link=os.readlink(path)
                if str(rel)!='lib64' or link!='lib' or info.st_uid!=0:
                    raise B.BootstrapError('unobserved venv directory link')
                os.symlink(link,target);dirs.remove(name);entries.append({'path':str(rel),'kind':'symlink','target':link})
            elif stat.S_ISDIR(info.st_mode) and info.st_uid==0 and not info.st_mode&0o022:
                target.mkdir(mode=0o755)
            else: raise B.BootstrapError('unsafe venv directory')
        for name in files:
            path=Path(parent)/name;rel=path.relative_to(source);info=path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_uid!=0 or info.st_mode&0o022:
                raise B.BootstrapError('unsafe venv member')
            pin=B.identity(path,256*1024*1024);total+=pin['bytes'];count+=1
            if count>8192 or total>384*1024*1024: raise B.BootstrapError('venv copy ceiling')
            target=destination/rel;B.copy_verified(path,target,pin,256*1024*1024)
            mode=0o755 if info.st_mode&0o111 else 0o644;os.chmod(target,mode)
            entries.append({'path':str(rel),'kind':'regular','mode':oct(mode),**pin})
    raw=B.canonical({'schema':'merlin-browser-reused-venv/1','source':str(source),'destination':str(destination),
                     'entries':entries,'packages_installed':False,'network_acquisition':False})
    B.write(ledger_path,raw)
    return {'files':count,'bytes':total,'ledger_sha256':B.digest(raw),'packages_installed':False,
            'source_release':OLD_RUNTIME,'allowed_symlink':'lib64 -> lib'}


def replace_host(raw,expected,temporary):
    target=B.CONFIG/'host.json';current=checked_raw(target,expected,65536)
    B.write(temporary,raw,0o600);os.replace(temporary,target)
    if B.regular(target,65536)!=raw: raise B.BootstrapError('atomic host configuration replacement differs')
    return current


def restore_host_after_attempt(old_raw,new_sha,temporary):
    actual=B.digest(B.regular(B.CONFIG/'host.json',65536))
    if actual==OLD_HOST:
        return {'previous_host_already_present':True,'observed_sha256':actual}
    if actual!=new_sha:
        raise B.BootstrapError('host configuration needs reconciliation; unexpected actual hash '+actual)
    replace_host(old_raw,new_sha,temporary)
    return {'previous_host_restored':True,'observed_before_restore_sha256':actual}


def run(bundle,bundle_pin,request,execution,output):
    if os.geteuid()!=0 or platform.machine()!='aarch64' or sys.version_info[:2]!=(3,9):
        raise B.BootstrapError('native root runtime successor required')
    os.umask(0o022);validate_request(request,execution)
    if bundle_pin!={'bytes':66202,'sha256':NEW_RUNTIME,'git_blob':'19754c4e50b46d32a05eee8c3a019d1cb450ee67',
                    'expert_source_commit':'8e2f1d69371d5b4f7e01e3bbd5aa02a666ddd506'}:
        raise B.BootstrapError('exact reviewed replacement runtime pin required')
    output_path=Path(output);parent_fd=B.operation_directory(output_path);leaf_fd=None;owned=False
    try:
        os.mkdir('root-evidence',mode=0o700,dir_fd=parent_fd)
        leaf_fd=os.open('root-evidence',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent_fd)
        info=os.fstat(leaf_fd)
        if info.st_uid!=0 or stat.S_IMODE(info.st_mode)!=0o700 or os.listdir(leaf_fd):
            raise B.BootstrapError('new private root evidence leaf required')
        owned=True
        return run_owned(bundle,bundle_pin,request,execution,output_path,parent_fd,leaf_fd)
    finally:
        if leaf_fd is not None:
            if owned: os.fchown(leaf_fd,1000,1000)
            os.close(leaf_fd)
        os.close(parent_fd)


def run_owned(bundle,bundle_pin,request,execution,output_path,parent_fd,leaf_fd):
    output=Path('/proc/self/fd')/str(leaf_fd);state=B.rooted(B.BOOTSTRAP_STATE,0o700)
    lock=os.open(str(state/'operation.lock'),os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    old_stage=state/OLD_REQUEST
    old_intent=checked_raw(old_stage/'bootstrap-intent.json',OLD_INTENT)
    old_result=checked_raw(old_stage/'operation-receipt.json',OLD_RESULT);prior=prior_receipt(old_result)
    checked_raw(old_stage/'bootstrap-result.json',OLD_RESULT)
    checked_raw(old_stage/'successor-lineage.json',OLD_LINEAGE)
    checked_raw(state/'bootstrap-intent.json',B.PREDECESSOR['intent_sha256'])
    checked_raw(state/'bootstrap-result.json',B.PREDECESSOR['result_sha256'])
    old_host=checked_raw(B.CONFIG/'host.json',OLD_HOST,65536)
    marker=state/('runtime-successor-from-'+OLD_REQUEST+'.json')
    for path in (marker,state/request['request_id'],B.PREFIX/'current',B.CONFIG/'service.json',Path('/etc/systemd/system')/B.SERVICE):
        if path.exists() or path.is_symlink(): raise B.BootstrapError('existing runtime successor requires explicit reconciliation')
    staged=state/request['request_id'];staged.mkdir(mode=0o700);logs=staged/'logs';logs.mkdir(mode=0o700)
    receipt={'schema':'merlin-browser-bootstrap/1','request':request,'execution':execution,'runtime_pin':bundle_pin,
      'status':'started','model_calls':0,'external_model_cost_usd':0,'qualification':False,'promotion_authority':False,
      'system_package_mutations':0,'python_package_installs':0,'network_acquisition':False,
      'dependency_reuse_prior_completed':True,'predecessor_run_id':OLD_RUN,'predecessor_result_sha256':OLD_RESULT,
      'inspection':INSPECTION,'original_failed_records_preserved':True,'accounts':prior['accounts'],
      'native_executable':prior['native_executable'],'package_support_limit':prior['package_support_limit'],
      'acceptance_budget':{'maximum_attempts':5,'prior_failed_fixture_attempts':1,
        'prior_fixture_id':'bootstrap-fixture-'+OLD_REQUEST,'remaining_attempt_ceiling':4,
        'planned_fixture_attempts':1,'planned_public_attempts':3,'model_calls':0}}
    B.write(marker,B.canonical({'schema':'merlin-browser-runtime-successor/1','prior_run_id':OLD_RUN,
        'prior_result_sha256':OLD_RESULT,'successor_request':request,'execution':execution,'automatic_retry':False}))
    for name,raw in (('bootstrap-intent.json',B.canonical(receipt)),('predecessor-intent.json',old_intent),
                     ('predecessor-result.json',old_result),('previous-host.json',old_host),
                     ('successor-lineage.json',B.regular(marker,65536))): B.write(staged/name,raw)
    host_replace_attempted=False;new_host_sha=None;release=B.PREFIX/'releases'/NEW_RUNTIME
    try:
        receipt['controller_envelope']=B.controller_envelope(execution,logs)
        receipt['before']=B.snapshot(logs,'before')
        if receipt['before']!=prior['before']: raise B.BootstrapError('existing private/model state differs')
        before_packages=B.installed(logs/'rpm-before.txt')
        if len(before_packages)!=971 or B.digest(B.canonical(before_packages))!=OLD_INVENTORY:
            raise B.BootstrapError('installed dependency state changed')
        receipt['installed_packages_before_sha256']=OLD_INVENTORY
        receipt['daemon_before']=B.daemon_absence(logs,'before',True)
        account=pwd.getpwnam('merlin-browser')
        if (account.pw_uid,account.pw_gid,account.pw_dir,account.pw_shell)!=(980,980,'/var/empty','/sbin/nologin'):
            raise B.BootstrapError('observed dedicated account differs')
        for unit in ('merlin-browser-bootstrap-44944424850-1.service',
                     'merlin-browser-fixture-bootstrap-fixture-'+OLD_REQUEST+'.service'):
            raw=B.command(['/usr/bin/systemctl','show',unit,'--no-pager','--property=MainPID',
                '--property=ActiveState','--property=ControlGroup'],logs/(unit+'.txt'))
            fields=dict(line.split('=',1) for line in raw.decode().splitlines() if '=' in line)
            if fields.get('MainPID')!='0' or fields.get('ControlGroup')!='' or fields.get('ActiveState') not in ('failed','inactive'):
                raise B.BootstrapError('predecessor workers are not confirmed stopped')
        old_manifest=B.decode(checked_raw(OLD_RELEASE/'manifest.json',OLD_MANIFEST,1048576))
        for item in old_manifest['files']:
            checked_raw(OLD_RELEASE/item['path'],item['sha256'],2*1024*1024)
        for path,expected in ((Path(LOADER_PATH),LOADER_SHA),(Path(prior['native_executable']['path']),NATIVE_SHA),
            (OLD_RELEASE/'venv/bin/python',PYTHON_SHA),(OLD_RELEASE/'venv/lib/python3.9/site-packages/playwright/driver/node',NODE_SHA)):
            if B.identity(path,256*1024*1024)['sha256']!=expected:
                raise B.BootstrapError('observed runtime binary identity differs')
        B.copy_verified(bundle,staged/'runtime.zip',{'sha256':NEW_RUNTIME,'bytes':bundle_pin['bytes']},16*1024*1024)
        runtime,manifest_sha=B.unpack_runtime(staged/'runtime.zip',bundle_pin,release)
        if manifest_sha!=NEW_MANIFEST: raise B.BootstrapError('new exact runtime manifest differs')
        receipt['reused_venv']=clone_venv(OLD_RELEASE/'venv',release/'venv',staged/'venv-copy-ledger.json')
        code='import json;from importlib.metadata import version;print(json.dumps({n:version(n) for n in '+repr([p['name'] for p in B.WHEELS])+'},sort_keys=True))'
        versions=B.decode(B.command([str(release/'venv/bin/python'),'-I','-B','-c',code],logs/'reused-wheel-versions.txt'))
        if versions!={p['name']:p['version'] for p in B.WHEELS}: raise B.BootstrapError('reused pinned wheel versions differ')
        host=B.decode(old_host);host.update(release=str(release),runtime_manifest_sha256=manifest_sha)
        new_host=B.canonical(host);new_host_sha=B.digest(new_host)
        host_replace_attempted=True;receipt['host_config_replacement_attempted']=True
        B.write(staged/'host-replacement-intent.json',B.canonical({'prior_sha256':OLD_HOST,'new_sha256':new_host_sha,
            'new_runtime_sha256':NEW_RUNTIME,'target':str(B.CONFIG/'host.json')}))
        replace_host(new_host,OLD_HOST,B.CONFIG/('host-next-'+request['request_id']+'.json'))
        receipt['host_config_sha256']=new_host_sha;B.write(staged/'installed-host.json',new_host)
        launcher={};exec(compile(B.regular(release/'bin/launch-episode',100000),'pinned-episode-launcher','exec'),launcher)
        fixture_id='bootstrap-fixture-'+request['request_id'];episode=B.STATE/'episodes'/fixture_id
        episode.mkdir(mode=0o700);(episode/'request').mkdir(mode=0o700)
        B.write(episode/'request/actions.json',B.canonical([{'action':'open','url':'https://example.com/'}]))
        B.write(episode/'request/limits.json',B.canonical(launcher['CEILINGS']))
        receipt['acceptance_budget']['fixture_attempt_started']=True
        receipt['fixture']=launcher['run_episode'](fixture_id,fixture=True)
        fixture=B.decode(B.regular(episode/'result/fixture.json',65536))
        if (fixture.get('status')!='succeeded' or fixture.get('playwright')!='1.60.0'
            or not fixture.get('chromium','').startswith(B.CHROMIUM_VERSION) or fixture.get('chromium_sandbox') is not True):
            raise B.BootstrapError('actual native fixture acceptance failed')
        receipt['fixture_observation']=fixture;os.symlink(str(release),B.PREFIX/'current')
        config={'schema':'merlin-browser-service-config/1','registry_root':str(B.STATE/'registry'),
            'project_id':'merlin-browser-research','episodes_root':str(B.STATE/'episodes'),
            'socket_path':'/run/merlin-public-browser/browser.sock','socket_gid':1000,'allowed_uids':[0,982],
            'launcher':str(B.PREFIX/'current/bin/launch-episode'),'limits':launcher['CEILINGS'],'launch_timeout_seconds':75}
        B.write(B.CONFIG/'service.json',B.canonical(config),0o600)
        run_parent=B.rooted(Path('/run/merlin-public-browser'));os.chown(run_parent,0,1000);os.chmod(run_parent,0o755)
        unit=B.service_unit(release);B.write(Path('/etc/systemd/system')/B.SERVICE,unit,0o644)
        B.command(['/usr/bin/systemctl','daemon-reload'],logs/'daemon-reload.txt')
        B.command(['/usr/bin/systemctl','enable','--now',B.SERVICE],logs/'service-enable.txt',timeout=20)
        receipt['acceptance_budget']['public_attempts_reserved']=3
        receipt['native_acceptance']=B.native_acceptance(release,1000,980,request['request_id'],logs)
        receipt['after']=B.snapshot(logs,'after')
        if receipt['after']!=receipt['before']: raise B.BootstrapError('existing private/model runtime changed')
        after_packages=B.installed(logs/'rpm-after.txt')
        if after_packages!=before_packages: raise B.BootstrapError('runtime-only operation changed system packages')
        receipt['installed_packages_after_sha256']=B.digest(B.canonical(after_packages))
        receipt['daemon_after_acceptance']=B.daemon_absence(logs,'after-acceptance',True)
        checked_raw(old_stage/'operation-receipt.json',OLD_RESULT)
        checked_raw(state/'bootstrap-intent.json',B.PREDECESSOR['intent_sha256'])
        checked_raw(state/'bootstrap-result.json',B.PREDECESSOR['result_sha256'])
        receipt['service_config_sha256']=B.digest(B.canonical(config));receipt['unit_sha256']=B.digest(unit)
        receipt['public_episode_acceptance']=receipt['native_acceptance']['status']
        receipt['status']='installed_native_passed' if receipt['native_acceptance']['status']=='passed' else 'installed_source_acceptance_incomplete'
    except BaseException as exc:
        receipt['status']='failed';receipt['error']={'type':type(exc).__name__,'message':str(exc)[:4000]}
        receipt['rollback']={'automatic_retry':False,'old_release_retained':True,'system_package_rollback_needed':False}
        try: B.command(['/usr/bin/systemctl','disable','--now',B.SERVICE],logs/'new-service-stop.txt',allowed=(0,1,5))
        except BaseException as error: receipt['rollback']['stop_error']=type(error).__name__
        current=B.PREFIX/'current'
        if current.is_symlink() and os.readlink(current)==str(release): current.unlink()
        if host_replace_attempted:
            try:
                receipt['rollback'].update(restore_host_after_attempt(old_host,new_host_sha,
                    B.CONFIG/('host-restore-'+request['request_id']+'.json')))
            except BaseException as error:
                receipt['rollback']['host_restore_error']={'type':type(error).__name__,'message':str(error)[:2000]}
        try:
            observed=B.installed(logs/'rpm-after-failure.txt')
            receipt['package_failure_observation']={'count':len(observed),'sha256':B.digest(B.canonical(observed)),
                'equals_retained_before':B.digest(B.canonical(observed))==OLD_INVENTORY,'system_package_mutations_requested':0}
            receipt['after_failure']=B.snapshot(logs,'after-failure')
        except BaseException as error: receipt['failure_state_observation_error']=type(error).__name__
    finally:
        B.write(staged/'bootstrap-result.json',B.canonical(receipt));B.write(staged/'operation-receipt.json',B.canonical(receipt))
        exported=output/'bootstrap-evidence';exported.mkdir(mode=0o700)
        for path in sorted(staged.iterdir()):
            if path.is_file() and path.name!='runtime.zip':
                B.write(exported/path.name,B.regular(path,4*1024*1024));os.chown(exported/path.name,1000,1000)
        for path in sorted(logs.iterdir()):
            B.write(exported/path.name,B.regular(path,8*1024*1024));os.chown(exported/path.name,1000,1000)
        os.chown(exported,1000,1000)
        trees={}
        for prefix in ('bootstrap-fixture','database-arxiv','news-nasa','repository-openmdao'):
            episode=prefix+'-'+request['request_id'];trees[episode]=B.export_tree(B.STATE/'episodes'/episode,output/episode)
        trees['canonical_registry']=B.export_tree(B.STATE/'registry',output/'canonical-browser-registry')
        B.write(output/'raw-evidence-export.json',B.canonical(trees));os.chown(output/'raw-evidence-export.json',1000,1000)
        check_parent=B.operation_directory(output_path);check_leaf=B.operation_directory(output_path/'root-evidence',owner=0)
        try:
            for first,second in ((parent_fd,check_parent),(leaf_fd,check_leaf)):
                a=os.fstat(first);b=os.fstat(second)
                if (a.st_dev,a.st_ino)!=(b.st_dev,b.st_ino): raise B.BootstrapError('runtime evidence path moved during publication')
        finally: os.close(check_parent);os.close(check_leaf);os.close(lock)
    if receipt['status']=='failed': raise B.BootstrapError('runtime successor failed; state and raw evidence retained')
    return receipt
