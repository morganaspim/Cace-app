#!/usr/bin/python3 -I
"""Fixed root supervisor helper for one bounded anonymous browser episode.

The caller supplies an episode identifier only. Requests are already in a
root-owned tree. Browser processes never receive the root-owned evidence store,
the private Merlin runtime, credentials, or this launcher's privilege.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import time

PREFIX = Path('/opt/merlin-public-browser')
STATE = Path('/var/lib/merlin-public-browser')
RUN = Path('/run/merlin-public-browser/episodes')
CONFIG = Path('/etc/merlin-public-browser/host.json')
ELF_LOADER = '/usr/lib/ld-linux-aarch64.so.1'
ELF_LOADER_SHA256 = '49d528c1bc76e851bdc1db2ffcacd69b7f969c461a23741b9f5b8be4318c3403'
ENV = {'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C.UTF-8','LC_ALL':'C.UTF-8',
       'HOME':'/var/empty','PYTHONDONTWRITEBYTECODE':'1'}
CEILINGS = {'wall_seconds':60,'action_seconds':15,'request_seconds':10,'max_actions':8,
            'max_requests':64,'max_resource_bytes':1048576,'max_network_bytes':8388608,
            'max_text_bytes':262144,'max_dom_bytes':524288,'max_screenshot_bytes':1048576,
            'max_evidence_bytes':12582912,'max_links':100}
PROPERTIES = ('User','Group','MainPID','ActiveState','SubState','Result','ExecMainStatus',
              'ControlGroup','MemoryMax','MemorySwapMax','CPUQuotaPerSecUSec','TasksMax',
              'RuntimeMaxUSec','NoNewPrivileges','PrivateNetwork','KillMode',
              'MemoryCurrent','MemoryPeak','CPUUsageNSec','TasksCurrent')


class LaunchError(RuntimeError):
    pass


def canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()


def unique(items):
    result = {}
    for key,value in items:
        if key in result: raise LaunchError('duplicate JSON key')
        result[key] = value
    return result


def decode(raw):
    return json.loads(raw,object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(LaunchError('nonfinite JSON')))


def safe_id(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}',value):
        raise LaunchError('invalid episode identifier')
    return value


def directory(path,create=False,mode=0o700):
    path=Path(path)
    for part in reversed([path]+list(path.parents)):
        if create and not part.exists(): part.mkdir(mode=mode)
        info=part.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid!=0 or info.st_mode&0o022:
            raise LaunchError('unsafe root-owned directory')
    return path


def read(path,limit,root=True):
    fd=os.open(str(path),os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        before=os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_size>limit
            or (root and (before.st_uid!=0 or before.st_mode&0o022))):
            raise LaunchError('unsafe bounded file')
        chunks=[];total=0
        while True:
            chunk=os.read(fd,min(1048576,limit+1-total))
            if not chunk: break
            chunks.append(chunk);total+=len(chunk)
            if total>limit: raise LaunchError('file byte limit')
        after=os.fstat(fd)
        if (before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_ino,after.st_size,after.st_mtime_ns):
            raise LaunchError('file changed during read')
        return b''.join(chunks)
    finally: os.close(fd)


def write(path,raw,mode=0o600):
    fd=os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
    try:
        with os.fdopen(fd,'wb',closefd=False) as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
    finally: os.close(fd)


def file_sha256(path,limit):
    fd=os.open(str(path),os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_uid!=0 or before.st_mode&0o022 or before.st_size>limit:
            raise LaunchError('unsafe immutable binary')
        digest=hashlib.sha256();total=0
        while True:
            raw=os.read(fd,1048576)
            if not raw: break
            total+=len(raw)
            if total>limit: raise LaunchError('immutable binary size ceiling')
            digest.update(raw)
        after=os.fstat(fd)
        if (before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_ino,after.st_size,after.st_mtime_ns):
            raise LaunchError('immutable binary changed during read')
        return digest.hexdigest()
    finally: os.close(fd)


def command(argv,timeout=10,limit=1024*1024,allowed=(0,),observe=None):
    process=subprocess.Popen(argv,cwd='/',env=ENV,stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
    selector=selectors.DefaultSelector();selector.register(process.stdout,selectors.EVENT_READ)
    output=bytearray();deadline=time.monotonic()+timeout
    try:
        observed_at=0
        while selector.get_map():
            left=deadline-time.monotonic()
            if left<=0: raise LaunchError('fixed command deadline')
            if observe is not None and time.monotonic()-observed_at>=.5:
                observe();observed_at=time.monotonic()
            for key,_ in selector.select(min(left,0.2)):
                raw=os.read(key.fd,65536)
                if not raw: selector.unregister(key.fileobj);continue
                if len(output)+len(raw)>limit: raise LaunchError('fixed command output ceiling')
                output.extend(raw)
        code=process.wait(timeout=max(.01,deadline-time.monotonic()))
        if code not in allowed: raise LaunchError('fixed command exit '+str(code)+': '+bytes(output[-2000:]).decode(errors='replace'))
        return bytes(output)
    finally:
        selector.close()
        if process.poll() is None:
            os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=5)
        process.stdout.close()


def show(unit):
    raw=command(['/usr/bin/systemctl','show',unit,'--no-pager']+
                ['--property='+name for name in PROPERTIES],allowed=(0,1,4),timeout=2)
    return dict(line.split('=',1) for line in raw.decode().splitlines() if '=' in line)


def validate_limits(value):
    if not isinstance(value,dict) or set(value)!=set(CEILINGS): raise LaunchError('exact bounded limits required')
    for name,ceiling in CEILINGS.items():
        if type(value[name]) is not int or not 1<=value[name]<=ceiling:
            raise LaunchError('episode budget exceeds host ceiling')
    if value['request_seconds']>value['action_seconds'] or value['action_seconds']>value['wall_seconds']:
        raise LaunchError('nested deadlines required')
    return value


def load_runtime(require_active=True):
    directory(CONFIG.parent)
    config=decode(read(CONFIG,32768))
    if set(config)!={'schema','release','browser_uid','browser_gid','executable','executable_sha256','runtime_manifest_sha256'} or config['schema']!='merlin-browser-host/1':
        raise LaunchError('host configuration contract')
    release=Path(config['release'])
    if release.parent!=PREFIX/'releases' or not re.fullmatch('[0-9a-f]{64}',release.name):
        raise LaunchError('immutable release path required')
    directory(release)
    if require_active and os.readlink(PREFIX/'current')!=str(release): raise LaunchError('active release differs from host configuration')
    manifest_raw=read(release/'manifest.json',1048576)
    if hashlib.sha256(manifest_raw).hexdigest()!=config['runtime_manifest_sha256']:
        raise LaunchError('runtime manifest changed')
    manifest=decode(manifest_raw)
    if manifest.get('schema')!='merlin-browser-runtime/1': raise LaunchError('runtime manifest schema')
    for item in manifest['files']:
        name=item['path']
        if not isinstance(name,str) or Path(name).is_absolute() or '..' in Path(name).parts:
            raise LaunchError('runtime manifest path')
        directory((release/name).parent)
        raw=read(release/name,item['bytes'])
        if len(raw)!=item['bytes'] or hashlib.sha256(raw).hexdigest()!=item['sha256']:
            raise LaunchError('runtime source changed')
    account=pwd.getpwnam('merlin-browser')
    if (account.pw_uid!=config['browser_uid'] or account.pw_gid!=config['browser_gid']
        or account.pw_uid==0 or account.pw_dir!='/var/empty' or account.pw_shell not in ('/usr/sbin/nologin','/sbin/nologin')):
        raise LaunchError('dedicated account changed')
    binary=Path(config['executable'])
    if binary.parent!=Path('/usr/lib64/chromium-browser') or binary.name!='headless_shell':
        raise LaunchError('fixed native browser required')
    if file_sha256(binary,512*1024*1024)!=config['executable_sha256']:
        raise LaunchError('native browser changed')
    if file_sha256(Path(ELF_LOADER),2*1024*1024)!=ELF_LOADER_SHA256:
        raise LaunchError('observed native ELF loader changed')
    return config,release


def sandbox(release,run,uid,gid,network=False):
    """Empty mount tree: code/libraries + this episode's three bounded mounts."""
    argv=['/usr/bin/bwrap','--unshare-user','--uid',str(uid),'--gid',str(gid),
          '--unshare-pid','--unshare-ipc','--unshare-uts','--new-session','--die-with-parent',
          '--cap-drop','ALL','--proc','/proc','--dev','/dev','--bind',str(run/'scratch'/'tmp'),'/tmp',
          '--dir','/home','--dir','/usr','--dir','/usr/bin','--dir','/usr/lib',
          '--ro-bind','/usr/lib64','/usr/lib64','--symlink','usr/lib64','/lib64',
          '--ro-bind',ELF_LOADER,ELF_LOADER,
          '--symlink','usr/lib','/lib','--symlink','usr/bin','/bin',
          '--ro-bind','/usr/bin/python3.9','/usr/bin/python3.9','--symlink','python3.9','/usr/bin/python3',
          '--dir','/etc','--dir','/usr/share','--dir','/work','--dir','/runtime',
          '--ro-bind',str(release/'venv'),'/runtime/venv',
          '--ro-bind',str(release/'python'),'/runtime/python',
          '--ro-bind',str(release/'bin'),'/runtime/bin',
          '--ro-bind',str(run/'input'),'/work/input',
          '--bind',str(run/'scratch'/'output'),'/work/output',
          '--bind',str(run/'scratch'/'socket'),'/work/socket']
    for source in ('/usr/lib/python3.9','/usr/share/fonts','/usr/share/fontconfig','/usr/share/zoneinfo',
                   '/etc/fonts','/etc/ld.so.cache'):
        if Path(source).exists(): argv += ['--ro-bind',source,source]
    if network:
        # Only public system resolver/CA configuration, never passwd, host homes,
        # service credentials, GitHub token, private Merlin state or registry.
        for source in ('/etc/resolv.conf','/etc/nsswitch.conf','/etc/hosts'):
            if Path(source).exists(): argv += ['--ro-bind',source,source]
        argv += ['--dir','/etc/ssl','--dir','/etc/ssl/certs','--ro-bind',
                 '/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem','/etc/ssl/certs/ca-certificates.crt']
    argv += ['--clearenv','--setenv','PATH','/usr/bin','--setenv','HOME','/tmp',
             '--setenv','LANG','C.UTF-8','--setenv','LC_ALL','C.UTF-8',
             '--setenv','PYTHONDONTWRITEBYTECODE','1',
             '--setenv','PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD','1',
             '--setenv','SSL_CERT_FILE','/etc/ssl/certs/ca-certificates.crt','--chdir','/tmp']
    return argv


def unit_command(unit,config,run,release,role,seconds):
    properties={'User':str(config['browser_uid']),'Group':str(config['browser_gid']),
        'NoNewPrivileges':'yes','CapabilityBoundingSet':'','AmbientCapabilities':'',
        'PrivateNetwork':'yes' if role!='broker' else 'no','PrivateTmp':'yes',
        'ProtectHome':'yes','ProtectSystem':'strict','ProtectKernelTunables':'yes',
        'ProtectKernelModules':'yes','ProtectControlGroups':'yes','RestrictSUIDSGID':'yes',
        'LockPersonality':'yes','UMask':'0077','MemoryMax':'128M' if role=='broker' else '1G','MemorySwapMax':'0',
        'CPUQuota':'25%' if role=='broker' else '100%','TasksMax':'128','RuntimeMaxSec':str(seconds),'TimeoutStopSec':'2',
        'KillMode':'control-group','LimitFSIZE':'16777216','LimitNOFILE':'256',
        'MemoryAccounting':'yes','CPUAccounting':'yes',
        'ReadWritePaths':str(run/'scratch'),
        'StandardOutput':'append:'+str(run/(role+'.log')),
        'StandardError':'append:'+str(run/(role+'.log'))}
    argv=['/usr/bin/systemd-run','--unit='+unit,'--quiet','--service-type=exec']
    if role!='broker': argv += ['--wait']
    if role=='renderer': properties['StandardInput']='file:'+str(run/'input'/'actions.jsonl')
    for name,value in properties.items(): argv+=['--property='+name+'='+value]
    argv+=['--']+sandbox(release,run,config['browser_uid'],config['browser_gid'],role=='broker')
    python=['/runtime/venv/bin/python','-I','-B','-c']
    if role=='fixture':
        return argv+python+["import runpy;runpy.run_path('/runtime/bin/smoke_renderer.py',run_name='__main__')",
                           '--executable',config['executable'],'--output','/work/output/fixture']
    module='browser_egress' if role=='broker' else 'public_browser'
    argv+=python+["import sys;sys.path.insert(0,'/runtime/python');from merlin."+module+" import main;raise SystemExit(main())"]
    if role=='broker':
        argv+=['--socket','/work/socket/egress.sock','--browser-uid',str(config['browser_uid']),
               '--limits','/work/input/limits.json']
    else:
        argv+=['--episode',run.name,'--output','/work/output/result','--broker-socket','/work/socket/egress.sock',
               '--broker-uid',str(config['browser_uid']),'--executable',config['executable'],
               '--limits','/work/input/limits.json']
    return argv


def export_tree(source,target,limit,max_files=1024):
    """Copy only stopped-worker regular bytes into root-owned publication input."""
    if not source.exists(): raise LaunchError('worker result absent')
    info=source.lstat()
    if not stat.S_ISDIR(info.st_mode): raise LaunchError('worker result is not a directory')
    target.mkdir(mode=0o700,exist_ok=False)
    count=total=0;identities=[]
    for parent,dirs,files in os.walk(source,followlinks=False):
        dirs.sort();files.sort()
        for name in dirs:
            path=Path(parent)/name
            if not stat.S_ISDIR(path.lstat().st_mode): raise LaunchError('non-directory worker entry')
            relative=path.relative_to(source)
            if len(relative.parts)>6: raise LaunchError('worker depth limit')
            (target/relative).mkdir(mode=0o700)
        for name in files:
            path=Path(parent)/name;relative=path.relative_to(source)
            if not re.fullmatch(r'(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_.-]+',str(relative)):
                raise LaunchError('worker filename contract')
            raw=read(path,limit-total,root=False);count+=1;total+=len(raw)
            if count>max_files or total>limit: raise LaunchError('worker output ceiling')
            write(target/relative,raw)
            identities.append({'path':str(relative),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
    return {'files':identities,'bytes':total,'count':count}


def prepare_run_tree(run):
    # mkdir modes are affected by the root supervisor's UMask=0077. Explicit
    # modes here protect the actual API path as well as the direct fixture.
    for path,mode in ((run,0o755),(run/'input',0o755),(run/'scratch',0o700)):
        path.mkdir(mode=mode,exist_ok=False);os.chmod(path,mode)


def run_episode(episode,fixture=False):
    started=time.monotonic();absolute_deadline=started+60
    if os.geteuid()!=0: raise LaunchError('fixed privileged supervisor required')
    os.umask(0o022)
    episode=safe_id(episode);config,release=load_runtime(require_active=not fixture)
    directory(STATE/'episodes',create=True)
    target=directory(STATE/'episodes'/episode)
    request=directory(target/'request')
    for existing in ('launch-intent.json','launch-receipt.json','result'):
        if (target/existing).exists() or (target/existing).is_symlink(): raise LaunchError('episode reuse prohibited')
    limits=validate_limits(decode(read(request/'limits.json',32768)))
    absolute_deadline=min(absolute_deadline,started+limits['wall_seconds'])
    actions=decode(read(request/'actions.json',65536))
    if not isinstance(actions,list) or not 1<=len(actions)<=limits['max_actions']: raise LaunchError('bounded action plan required')
    sys.path.insert(0,str(release/'python'))
    from merlin.public_browser import validate_action
    for value in actions: validate_action(value)
    lock=os.open(str(STATE/'episode.lock'),os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    info=os.fstat(lock)
    if not stat.S_ISREG(info.st_mode) or info.st_uid!=0 or info.st_mode&0o077: raise LaunchError('unsafe episode lock')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    receipt={'schema':'merlin-browser-launch/1','episode_id':episode,'release':str(release),
        'started_at_unix':time.time(),'limits':limits,'status':'started','model_calls':0,
        'external_model_cost_usd':0,'qualification':False,'promotion_authority':False,
        'host_paths_exposed':['system libraries','immutable browser runtime','episode input/output/socket'],
        'scratch_ceiling_bytes':134217728,'scratch_inode_ceiling':4096,
        'absolute_execution_ceiling_seconds':limits['wall_seconds'],'cleanup_ceiling_seconds':12,
        'actions_sha256':hashlib.sha256(read(request/'actions.json',65536)).hexdigest(),
        'live_unit_samples':{}}
    write(target/'launch-intent.json',canonical(receipt))
    units={name:'merlin-browser-'+name+'-'+episode+'.service' for name in ('broker','renderer','fixture')}
    started_roles=[];mounted=False;failure=None;run=RUN/episode
    def left():
        remaining=absolute_deadline-time.monotonic()
        if remaining<1: raise LaunchError('absolute episode execution deadline')
        return remaining
    def observe(role):
        samples=receipt['live_unit_samples'].setdefault(role,[])
        if len(samples)>=12: return
        try:
            sample=show(units[role])
            if sample.get('MainPID') not in ('0','',None):
                sample['observed_elapsed_seconds']=round(time.monotonic()-started,3)
                group=sample.get('ControlGroup','')
                if re.fullmatch(r'/system.slice/merlin-browser-[A-Za-z0-9_.-]+',group):
                    for name in ('memory.current','memory.peak','memory.max','memory.swap.max',
                                 'cpu.max','cpu.stat','pids.max','cgroup.events'):
                        path=Path('/sys/fs/cgroup'+group)/name
                        if path.exists(): sample[name]=path.read_text()[:4096]
                samples.append(sample)
        except BaseException as exc:
            receipt.setdefault('observation_errors',[]).append(type(exc).__name__)
    try:
        directory(RUN,create=True,mode=0o755)
        prepare_run_tree(run)
        command(['/usr/bin/mount','-t','tmpfs','-o','size=134217728,nr_inodes=4096,nodev,nosuid,noexec,mode=0755',
                 'merlin-browser-'+episode,str(run/'scratch')],timeout=min(3,left()))
        mounted=True
        for name in ('output','socket','tmp'):
            (run/'scratch'/name).mkdir(mode=0o700);os.chown(run/'scratch'/name,config['browser_uid'],config['browser_gid'])
        write(run/'input'/'limits.json',canonical(limits),0o444)
        write(run/'input'/'actions.jsonl',b''.join(canonical(value) for value in actions),0o444)
        if fixture:
            role='fixture';started_roles.append(role)
            argv=unit_command(units[role],config,run,release,role,max(1,int(left())))
            receipt['fixture_command']=argv
            command(argv,timeout=left(),observe=lambda:observe(role))
        else:
            started_roles.append('broker')
            argv=unit_command(units['broker'],config,run,release,'broker',max(1,int(left())))
            receipt['broker_command']=argv;command(argv,timeout=min(4,left()))
            ready_deadline=min(absolute_deadline,time.monotonic()+4)
            while not (run/'scratch'/'socket'/'egress.sock').exists():
                if time.monotonic()>ready_deadline: raise LaunchError('broker readiness deadline')
                time.sleep(.05)
            socket_info=(run/'scratch'/'socket'/'egress.sock').lstat()
            if not stat.S_ISSOCK(socket_info.st_mode) or socket_info.st_uid!=config['browser_uid'] or stat.S_IMODE(socket_info.st_mode)!=0o600:
                raise LaunchError('broker socket ownership contract')
            observe('broker');started_roles.append('renderer')
            argv=unit_command(units['renderer'],config,run,release,'renderer',max(1,int(left())))
            receipt['renderer_command']=argv
            command(argv,timeout=left(),observe=lambda:observe('renderer'))
        receipt['status']='succeeded'
    except BaseException as exc:
        failure=exc;receipt['status']='failed';receipt['error']={'type':type(exc).__name__,'message':str(exc)[:4000]}
    finally:
        cleanup_started=time.monotonic();all_stopped=True;receipt['unit_shutdown']={}
        if started_roles:
            try: command(['/usr/bin/systemctl','stop']+[units[role] for role in started_roles],timeout=4,allowed=(0,1,5))
            except BaseException as exc:
                all_stopped=False;receipt['stop_error']={'type':type(exc).__name__,'message':str(exc)[:1000]};failure=failure or exc
        for role in started_roles:
            try:
                after=show(units[role]);receipt['unit_shutdown'][role]=after
                if after.get('ActiveState') not in ('inactive','failed') or after.get('MainPID') not in ('0',''):
                    raise LaunchError('worker did not stop')
                group=after.get('ControlGroup','')
                if group and re.fullmatch(r'/system.slice/merlin-browser-[A-Za-z0-9_.-]+',group):
                    members=Path('/sys/fs/cgroup'+group)/'cgroup.procs'
                    if members.exists() and members.read_text().strip(): raise LaunchError('worker cgroup remains populated')
            except BaseException as exc:
                all_stopped=False;receipt.setdefault('shutdown_errors',[]).append({'type':type(exc).__name__,'message':str(exc)[:1000]});failure=failure or exc
        receipt['all_workers_stopped']=all_stopped;receipt['logs']={}
        if all_stopped:
            for role in started_roles:
                path=run/(role+'.log')
                if path.exists():
                    try:
                        raw=read(path,16*1024*1024);write(target/(role+'.log'),raw)
                        receipt['logs'][role]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
                    except BaseException as exc:
                        receipt.setdefault('log_errors',[]).append(type(exc).__name__);failure=failure or exc
            source=run/'scratch'/'output'/('fixture' if fixture else 'result')
            try:
                if source.exists():
                    receipt['output']=export_tree(source,target/'result',limits['max_evidence_bytes'])
                    marker='fixture.json' if fixture else 'episode.json'
                    summary=decode(read(target/'result'/marker,2*1024*1024))
                    expected_status='succeeded' if fixture else 'completed'
                    if summary.get('status')!=expected_status: raise LaunchError('worker result did not succeed')
                else: raise LaunchError('worker returned no result marker')
            except BaseException as exc:
                receipt['export_error']={'type':type(exc).__name__,'message':str(exc)[:1000]};failure=failure or exc
            if mounted:
                try:
                    command(['/usr/bin/umount',str(run/'scratch')],timeout=3)
                    receipt['scratch_unmounted']=True
                except BaseException as exc:
                    receipt['scratch_unmounted']=False;receipt['unmount_error']={'type':type(exc).__name__,'message':str(exc)[:1000]};failure=failure or exc
        else:
            receipt['output_quarantined']=True;receipt['scratch_unmounted']=False
        if failure: receipt['status']='failed'
        receipt['cleanup_seconds']=round(time.monotonic()-cleanup_started,3)
        receipt['completed_at_unix']=time.time();receipt['elapsed_seconds']=round(time.monotonic()-started,3)
        write(target/'launch-receipt.json',canonical(receipt));os.close(lock)
    if failure: raise LaunchError('browser launch failed; preserved receipt and raw output') from failure
    return receipt


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--episode',required=True)
    args=parser.parse_args()
    print(json.dumps(run_episode(args.episode),sort_keys=True))


if __name__=='__main__': main()
