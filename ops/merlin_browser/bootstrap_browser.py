"""Pinned, install-only Oracle browser bootstrap; no request-supplied commands.

Acquisition runs as the existing unprivileged runner. Installation receives the
frozen manifest hash in authenticated fixed workflow code, recopies regular
artifacts into root-owned staging, and rechecks every hash/signature. Existing
packages are never upgraded, removed or replaced. Failure remains inspectable.
"""
import base64
import contextlib
import fcntl
import grp
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import pwd
import re
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import uuid
import zipfile

CHROMIUM_VERSION='156.0.8078.79'
CHROMIUM_RELEASE='1.0.1.el9'
ROOT_PACKAGES=('chromium-headless','chromium-common')
REPOS={
 'merlin-ol9-baseos':'https://yum.oracle.com/repo/OracleLinux/OL9/baseos/latest/aarch64/',
 'merlin-ol9-appstream':'https://yum.oracle.com/repo/OracleLinux/OL9/appstream/aarch64/',
 'merlin-ol9-epel':'https://yum.oracle.com/repo/OracleLinux/OL9/developer/EPEL/aarch64/',
 'merlin-ol9-codeready':'https://yum.oracle.com/repo/OracleLinux/OL9/codeready/builder/aarch64/'}
KEYS={
 'oracle-ol9.asc':{'url':'https://yum.oracle.com/RPM-GPG-KEY-oracle-ol9',
    'fingerprints':['3E6D826D3FBAB389C2F38E34BC4D06A08D8B756F','982231759C7467065D0CE9B2A7DD07088B4EFBE6']},
 'oracle-development.asc':{'url':'https://yum.oracle.com/RPM-GPG-KEY-oracle-development',
    'fingerprints':['490148F597750B1CBAD72DE9E4A8134ED3780CDA']}}
WHEELS=[
 {'name':'playwright','version':'1.60.0','filename':'playwright-1.60.0-py3-none-manylinux_2_17_aarch64.manylinux2014_aarch64.whl',
  'sha256':'43e66564125ee31b07a58cefb21e256d62d67d8d1713e6858df7a3019d8ed353',
  'url':'https://files.pythonhosted.org/packages/84/c2/1528d267d4442bd2c6b8eaeab819dd52c2030bf80e89293f0ba1f687473b/playwright-1.60.0-py3-none-manylinux_2_17_aarch64.manylinux2014_aarch64.whl'},
 {'name':'greenlet','version':'3.2.4','filename':'greenlet-3.2.4-cp39-cp39-manylinux2014_aarch64.manylinux_2_17_aarch64.whl',
  'sha256':'27890167f55d2387576d1f41d9487ef171849ea0359ce1510ca6e06c8bece11d',
  'url':'https://files.pythonhosted.org/packages/4d/f5/33f05dc3ba10a02dedb1485870cf81c109227d3d3aa280f0e48486cac248/greenlet-3.2.4-cp39-cp39-manylinux2014_aarch64.manylinux_2_17_aarch64.whl'},
 {'name':'pyee','version':'13.0.0','filename':'pyee-13.0.0-py3-none-any.whl',
  'sha256':'48195a3cddb3b1515ce0695ed76036b5ccc2ef3a9f963ff9f77aec0139845498',
  'url':'https://files.pythonhosted.org/packages/9b/4d/b9add7c84060d4c1906abe9a7e5359f2a60f7a9a4f67268b2766673427d8/pyee-13.0.0-py3-none-any.whl'},
 {'name':'typing-extensions','version':'4.14.1','filename':'typing_extensions-4.14.1-py3-none-any.whl',
  'sha256':'d1e1e3b58374dc93031d6eda2420a48ea44a36c2b4766a4fdeb3710755731d76',
  'url':'https://files.pythonhosted.org/packages/b5/00/d631e67a838026495268c2f6884f3711a15a9a2a96cd244fdaea53b823fb/typing_extensions-4.14.1-py3-none-any.whl'}]
ENV={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C.UTF-8','LC_ALL':'C.UTF-8',
     'HOME':'/var/empty','XDG_CONFIG_HOME':'/var/empty','XDG_CACHE_HOME':'/var/empty',
     'PYTHONDONTWRITEBYTECODE':'1','PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD':'1',
     'PIP_CONFIG_FILE':'/dev/null','PIP_DISABLE_PIP_VERSION_CHECK':'1'}
MAX_PACKAGES=64
MAX_DOWNLOAD=512*1024*1024
MAX_INSTALLED=2*1024*1024*1024
MAX_METADATA_SOURCE=512*1024*1024
MAX_DERIVED_CACHE=384*1024*1024
PREFIX=Path('/opt/merlin-public-browser')
STATE=Path('/var/lib/merlin-public-browser')
BOOTSTRAP_STATE=Path('/var/lib/merlin-browser-bootstrap')
CONFIG=Path('/etc/merlin-public-browser')
SERVICE='merlin-public-browser.service'
RPM_FORMAT='%{NAME}\t%{EPOCHNUM}\t%{VERSION}\t%{RELEASE}\t%{ARCH}\n'
PRIVATE_CONFIG_SHA='a25921442e2d3e463ccd685de6c67d824140b8c1592ab4fe942fb50c5d3b22e8'
PRIVATE_UNIT_SHA='f22462e9c91eedab99d4bd16d9e3bb14eb52fedbc1e9e3b9110bb3307a11e543'


class BootstrapError(RuntimeError): pass


def canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()


def digest(raw): return hashlib.sha256(raw).hexdigest()


def unique(items):
    result={}
    for key,value in items:
        if key in result: raise BootstrapError('duplicate JSON key')
        result[key]=value
    return result


def decode(raw):
    return json.loads(raw,object_pairs_hook=unique,
        parse_constant=lambda _: (_ for _ in ()).throw(BootstrapError('nonfinite JSON')))


def regular(path,limit):
    fd=os.open(str(path),os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size>limit: raise BootstrapError('regular bounded file required')
        chunks=[];total=0
        while True:
            raw=os.read(fd,min(1048576,limit+1-total))
            if not raw: break
            chunks.append(raw);total+=len(raw)
            if total>limit: raise BootstrapError('file ceiling')
        after=os.fstat(fd)
        if (before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_ino,after.st_size,after.st_mtime_ns):
            raise BootstrapError('file changed during read')
        return b''.join(chunks)
    finally: os.close(fd)


def identity(path,limit):
    fd=os.open(str(path),os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size>limit: raise BootstrapError('identity regular bounded file required')
        value=hashlib.sha256();size=0
        while True:
            chunk=os.read(fd,1048576)
            if not chunk: break
            size+=len(chunk)
            if size>limit: raise BootstrapError('identity ceiling')
            value.update(chunk)
        after=os.fstat(fd)
        if (before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_ino,after.st_size,after.st_mtime_ns):
            raise BootstrapError('identity changed during read')
        return {'sha256':value.hexdigest(),'bytes':size}
    finally: os.close(fd)


def write(path,raw,mode=0o600):
    fd=os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
    try:
        with os.fdopen(fd,'wb',closefd=False) as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
    finally: os.close(fd)


def rooted(path,mode=0o755):
    path=Path(path)
    for item in reversed([path]+list(path.parents)):
        if not item.exists(): item.mkdir(mode=mode)
        value=item.lstat()
        if not stat.S_ISDIR(value.st_mode) or value.st_uid!=0 or value.st_mode&0o022:
            raise BootstrapError('root-owned directory required')
    return path


def command(argv,log,timeout=60,limit=8*1024*1024,allowed=(0,),user=None,group=None):
    credentials={} if user is None else {'user':user,'group':group,'extra_groups':[]}
    isolated=os.geteuid()==0
    process=subprocess.Popen(argv,cwd='/',env=ENV,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,start_new_session=isolated,**credentials)
    output=bytearray();deadline=time.monotonic()+timeout;selector=selectors.DefaultSelector()
    selector.register(process.stdout,selectors.EVENT_READ)
    error=None
    try:
        while selector.get_map():
            left=deadline-time.monotonic()
            if left<=0: raise BootstrapError('fixed command deadline')
            for key,_ in selector.select(min(.2,left)):
                raw=os.read(key.fd,65536)
                if not raw: selector.unregister(key.fileobj);continue
                if len(output)+len(raw)>limit: raise BootstrapError('fixed command output ceiling')
                output.extend(raw)
        code=process.wait(timeout=max(.01,deadline-time.monotonic()))
        if code not in allowed: raise BootstrapError('fixed command failed with exit '+str(code))
        return bytes(output)
    except BaseException as exc: error=exc;raise
    finally:
        selector.close()
        if process.poll() is None:
            if isolated: os.killpg(process.pid,signal.SIGKILL)
            else: process.kill()
            process.wait(timeout=5)
        process.stdout.close()
        write(log,bytes(output))
        write(Path(str(log)+'.json'),canonical({'argv':argv,'returncode':process.returncode,
          'output_bytes':len(output),'output_sha256':digest(output),'error':type(error).__name__ if error else None}))


def validate_request(request,execution):
    if not isinstance(request,dict) or set(request)!={'schema','request_id','operation','created_at'}:
        raise BootstrapError('fixed request fields')
    if request['schema']!='merlin-browser-bootstrap-request/1' or request['operation']!='bootstrap':
        raise BootstrapError('fixed bootstrap only')
    if str(uuid.UUID(request['request_id']))!=request['request_id']:
        raise BootstrapError('canonical request UUID required')
    if not isinstance(request['created_at'],str) or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ',request['created_at']):
        raise BootstrapError('request time')
    if execution.get('runner')!='cace-oci-a1' or execution.get('run_attempt')!=1:
        raise BootstrapError('fixed runner and first attempt required')
    if type(execution.get('run_id')) is not int or execution['run_id']<=0:
        raise BootstrapError('run identity')
    if not re.fullmatch('[0-9a-f]{40}',execution.get('workflow_commit','')):
        raise BootstrapError('workflow source identity')


def fingerprints(raw):
    """Extract standard v4 public-primary-key fingerprints, never secret keys."""
    text=raw.decode('ascii');blocks=re.findall(r'-----BEGIN PGP PUBLIC KEY BLOCK-----\s*(.*?)\s*-----END PGP PUBLIC KEY BLOCK-----',text,re.S)
    if not blocks or len(blocks)>4: raise BootstrapError('bounded public key armor required')
    result=[]
    for block in blocks:
        lines=[line.strip() for line in block.splitlines() if line.strip() and ':' not in line and not line.startswith('=')]
        data=base64.b64decode(''.join(lines),validate=True);offset=0
        while offset<len(data):
            first=data[offset];offset+=1
            if not first&0x80: raise BootstrapError('invalid OpenPGP packet')
            if first&0x40:
                tag=first&0x3f
                if offset>=len(data): raise BootstrapError('short OpenPGP length')
                n=data[offset];offset+=1
                if n<192: length=n
                elif n<224:
                    if offset>=len(data): raise BootstrapError('short OpenPGP length')
                    length=(n-192)*256+data[offset]+192;offset+=1
                elif n==255:
                    if offset+4>len(data): raise BootstrapError('short OpenPGP length')
                    length=int.from_bytes(data[offset:offset+4],'big');offset+=4
                else: raise BootstrapError('partial key packet rejected')
            else:
                tag=(first>>2)&15;kind=first&3
                if kind==3: raise BootstrapError('indeterminate key packet rejected')
                width=(1,2,4)[kind]
                if offset+width>len(data): raise BootstrapError('short OpenPGP length')
                length=int.from_bytes(data[offset:offset+width],'big');offset+=width
            if length<=0 or offset+length>len(data): raise BootstrapError('key packet bounds')
            body=data[offset:offset+length];offset+=length
            if tag in (5,7): raise BootstrapError('secret key material prohibited')
            if tag==6:
                if body[0]!=4 or length>65535: raise BootstrapError('v4 public primary required')
                result.append(hashlib.sha1(b'\x99'+length.to_bytes(2,'big')+body).hexdigest().upper())
    if len(result)!=len(set(result)): raise BootstrapError('duplicate primary key')
    return sorted(result)


class FixedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,request,fp,code,msg,headers,newurl):
        raise BootstrapError('artifact redirect rejected; fixed final source required')


def download(url,path,maximum,expected=None):
    parsed=urllib.parse.urlsplit(url)
    if parsed.scheme!='https' or parsed.hostname not in ('yum.oracle.com','files.pythonhosted.org') or parsed.username or parsed.password or parsed.port not in (None,443):
        raise BootstrapError('fixed authenticated download origin required')
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),FixedRedirect())
    request=urllib.request.Request(url,headers={'User-Agent':'Merlin-fixed-browser-bootstrap/1'})
    start=time.monotonic();size=0;value=hashlib.sha256()
    fd=os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    try:
        with opener.open(request,timeout=20) as response,os.fdopen(fd,'wb',closefd=False) as stream:
            if response.status!=200 or response.geturl()!=url: raise BootstrapError('unexpected artifact response')
            declared=response.headers.get('Content-Length')
            if declared is not None and (not declared.isdigit() or int(declared)>maximum):
                raise BootstrapError('artifact declared byte ceiling')
            while True:
                if time.monotonic()-start>180: raise BootstrapError('artifact absolute deadline')
                # read1 avoids trying to fill a MiB across repeated reads. The
                # workflow separately kills the entire acquisition process
                # group at its absolute deadline, including DNS/header stalls.
                chunk=response.read1(min(1048576,maximum+1-size))
                if not chunk: break
                size+=len(chunk)
                if size>maximum: raise BootstrapError('artifact byte ceiling')
                value.update(chunk);stream.write(chunk)
            stream.flush();os.fsync(stream.fileno())
    finally: os.close(fd)
    result={'sha256':value.hexdigest(),'bytes':size}
    if expected and result['sha256']!=expected: raise BootstrapError('artifact hash differs from pin')
    return result


def installed(log):
    raw=command(['/usr/bin/rpm','-qa','--qf',RPM_FORMAT],log,timeout=20)
    rows=[]
    for line in raw.decode().splitlines():
        fields=line.split('\t')
        if len(fields)!=5: raise BootstrapError('RPM inventory format')
        rows.append(dict(zip(('name','epoch','version','release','arch'),fields)))
    return sorted(rows,key=lambda value:tuple(value[key] for key in ('name','epoch','version','release','arch')))


def validate_transaction(packages,before,removed):
    if removed: raise BootstrapError('package removals/replacements prohibited')
    if not isinstance(packages,list) or not 1<=len(packages)<=MAX_PACKAGES: raise BootstrapError('bounded install-only transaction required')
    old={(p['name'],p['arch']) for p in before}
    names=set();total_download=total_install=0
    for package in packages:
        if set(package)!={'name','epoch','version','release','arch','repository','url','filename','sha256','bytes','install_bytes','requires'}:
            raise BootstrapError('package manifest fields')
        key=(package['name'],package['arch'])
        if key in old or key in names: raise BootstrapError('existing or duplicate package replacement prohibited')
        names.add(key)
        if package['arch'] not in ('aarch64','noarch') or package['repository'] not in REPOS:
            raise BootstrapError('package architecture/repository differs')
        if not isinstance(package['url'],str) or not package['url'].startswith(REPOS[package['repository']]):
            raise BootstrapError('package source prefix differs: '+json.dumps({
                'repository':package['repository'],'url':package['url'],
                'expected_prefix':REPOS[package['repository']],'filename':package['filename']},sort_keys=True)[:2000])
        if not isinstance(package['filename'],str) or not re.fullmatch(r'[A-Za-z0-9_.+~-]+\.rpm',package['filename']):
            raise BootstrapError('package filename differs: '+json.dumps({
                'repository':package['repository'],'url':package['url'],'filename':package['filename']},sort_keys=True)[:2000])
        if urllib.parse.urlsplit(package['url']).path.rsplit('/',1)[-1]!=package['filename']:
            raise BootstrapError('RPM basename differs')
        if not re.fullmatch('[0-9a-f]{64}',package['sha256']): raise BootstrapError('SHA256 metadata required')
        if type(package['bytes']) is not int or type(package['install_bytes']) is not int or not 0<package['bytes']<=MAX_DOWNLOAD or not 0<package['install_bytes']<=MAX_INSTALLED:
            raise BootstrapError('package declared size ceiling')
        total_download+=package['bytes'];total_install+=package['install_bytes']
    if total_download>MAX_DOWNLOAD or total_install>MAX_INSTALLED: raise BootstrapError('transaction size ceiling')
    for name in ROOT_PACKAGES:
        matched=[p for p in packages if p['name']==name]
        if len(matched)!=1 or matched[0]['version']!=CHROMIUM_VERSION or matched[0]['release']!=CHROMIUM_RELEASE or str(matched[0]['epoch'])!='0' or matched[0]['arch']!='aarch64':
            raise BootstrapError('exact Chromium root package absent')
    return {'new_packages':len(packages),'download_bytes':total_download,'installed_bytes':total_install,
            'upgrades':0,'downgrades':0,'removals':0,'reinstalls':0}


def checked_transaction(directory,packages,before,removed,diagnostics=None,label='candidate',runner_readable=False):
    """Persist exact unvalidated input before either transaction admission."""
    directory=Path(directory)
    candidate={'schema':'merlin-browser-unvalidated-package-plan/1','validated':False,
               'packages':packages,'removed':removed,'repositories':REPOS,
               'installed_packages_sha256':digest(canonical(before)),
               'installed_package_count':len(before),'resolution_diagnostics':diagnostics}
    raw=canonical(candidate);path=directory/(label+'-plan.json')
    if len(raw)>2*1024*1024:
        path=directory/(label+'-plan-oversize.json')
        write(path,canonical({'validated':False,'bytes':len(raw),'sha256':digest(raw),
            'packages':len(packages),'raw_repository_metadata_retained':True}))
        if runner_readable: os.chown(path,1000,1000)
        raise BootstrapError('unvalidated candidate plan evidence ceiling')
    write(path,raw)
    if runner_readable: os.chown(path,1000,1000)
    try: return validate_transaction(packages,before,removed)
    except BaseException as exc:
        failure=directory/(label+'-rejection.json')
        write(failure,canonical({'schema':'merlin-browser-package-plan-rejection/1','validated':False,
            'candidate_sha256':digest(raw),'type':type(exc).__name__,'message':str(exc)[:4000]}))
        if runner_readable: os.chown(failure,1000,1000)
        raise


def metadata_identities(stage):
    """Keep source metadata and generated solver bytes separately bounded.

    Native attempt44933072217 measured329,903,655 original repository bytes
    and244,983,256 generated cache bytes. Both categories remain retained.
    """
    stage=Path(stage);rows=[];totals={'repository_source':0,'derived_solver_cache':0}
    ceilings={'repository_source':MAX_METADATA_SOURCE,'derived_solver_cache':MAX_DERIVED_CACHE}
    for directory,dirs,files in os.walk(stage/'cache',followlinks=False):
        dirs.sort();files.sort()
        for filename in files:
            path=Path(directory)/filename
            category='repository_source' if 'repodata' in path.relative_to(stage/'cache').parts else 'derived_solver_cache'
            info=identity(path,256*1024*1024);totals[category]+=info['bytes']
            if len(rows)>=256 or totals[category]>ceilings[category]:
                raise BootstrapError('repository metadata '+category+' evidence ceiling')
            rows.append({'path':str(path.relative_to(stage)),'category':category,**info})
    return {'files':rows,'bytes_by_category':totals,'ceiling_bytes_by_category':ceilings,
            'total_bytes':sum(totals.values()),'overall_ceiling_bytes':sum(ceilings.values())}


def acquire(stage):
    if os.geteuid()!=1000 or platform.machine()!='aarch64' or sys.version_info[:2]!=(3,9):
        raise BootstrapError('native unprivileged Oracle acquisition required')
    stage=Path(stage);stage.mkdir(mode=0o700,exist_ok=False)
    for name in ('rpms','wheels','keys','cache','persist','logs'): (stage/name).mkdir(mode=0o700)
    before=installed(stage/'logs'/'rpm-before.txt')
    import dnf
    import hawkey
    with dnf.Base() as base:
        conf=base.conf
        conf.cachedir=str(stage/'cache');conf.persistdir=str(stage/'persist');conf.logdir=str(stage/'logs')
        conf.reposdir=[];conf.plugins=False;conf.install_weak_deps=False;conf.best=True
        conf.gpgcheck=True;conf.localpkg_gpgcheck=True;conf.sslverify=True
        conf.timeout=20;conf.retries=1;conf.max_parallel_downloads=1
        conf.substitutions['releasever']='9';conf.substitutions['basearch']='aarch64';conf.substitutions['arch']='aarch64'
        for name,url in REPOS.items():
            repo=base.repos.add_new_repo(name,conf,baseurl=[url])
            repo.gpgcheck=True;repo.sslverify=True;repo.skip_if_unavailable=False
        base.fill_sack(load_system_repo=True)
        for name in ROOT_PACKAGES:
            base.install(name+'-'+CHROMIUM_VERSION+'-'+CHROMIUM_RELEASE+'.aarch64',reponame='merlin-ol9-epel',strict=True)
        base.resolve(allow_erasing=False)
        packages=[];locations=[];repo_diagnostics={}
        for repo in base.repos.iter_enabled():
            try:
                mirrors=list(repo._repo.getMirrors())
                repo_diagnostics[repo.id]={'baseurl':list(repo.baseurl),'effective_mirrors':mirrors[:32],
                                         'effective_mirror_count':len(mirrors),'mirrors_truncated':len(mirrors)>32}
            except Exception as exc:
                repo_diagnostics[repo.id]={'baseurl':list(repo.baseurl),'mirror_observation_error':type(exc).__name__}
        for package in base.transaction.install_set:
            checksum=package.chksum
            if not checksum or checksum[0]!=hawkey.CHKSUM_SHA256: raise BootstrapError('repository SHA256 required')
            sha=bytes(checksum[1]).hex()
            url=package.remote_location(schemes=('https',))
            packages.append({'name':package.name,'epoch':str(package.epoch),'version':package.version,'release':package.release,
                'arch':package.arch,'repository':package.reponame,'url':url,'filename':urllib.parse.urlsplit(url).path.rsplit('/',1)[-1],
                'sha256':sha,'bytes':int(package.downloadsize),'install_bytes':int(package.installsize),
                'requires':sorted(str(item) for item in package.requires)})
            locations.append({'name':package.name,'epoch':str(package.epoch),'version':package.version,
                'release':package.release,'arch':package.arch,'repository':package.reponame,
                'metadata_location':package.location,'package_baseurl':package.baseurl,'returned_url':url})
        packages.sort(key=lambda value:(value['name'],value['arch']))
        removed=[str(item) for item in base.transaction.remove_set]
        bounds=checked_transaction(stage,packages,before,removed,
            {'repositories':repo_diagnostics,'package_locations':sorted(locations,key=lambda value:(value['name'],value['arch']))})
        write(stage/'resolved-transaction.json',canonical({'packages':packages,'removed':removed,'bounds':bounds,'repositories':REPOS}))
        for package in packages:
            obtained=download(package['url'],stage/'rpms'/package['filename'],package['bytes'],package['sha256'])
            if obtained['bytes']!=package['bytes']: raise BootstrapError('RPM length differs from metadata')
    keys=[]
    for name,pin in KEYS.items():
        got=download(pin['url'],stage/'keys'/name,65536)
        observed=fingerprints(regular(stage/'keys'/name,65536))
        if observed!=sorted(pin['fingerprints']): raise BootstrapError('Oracle full signing-key fingerprint differs')
        keys.append({'filename':name,'url':pin['url'],'fingerprints':observed,**got})
    wheels=[]
    for pin in WHEELS:
        got=download(pin['url'],stage/'wheels'/pin['filename'],64*1024*1024,pin['sha256'])
        wheels.append({**pin,**got})
    metadata=metadata_identities(stage)
    manifest={'schema':'merlin-browser-acquisition/1','chromium_version':CHROMIUM_VERSION,'chromium_release':CHROMIUM_RELEASE,
       'python':'3.9','playwright':'1.60.0','repositories':REPOS,'packages':packages,'removed':removed,'bounds':bounds,
       'before_packages':before,'keys':keys,'wheels':wheels,'repository_metadata':metadata,
       'metadata_authentication':'HTTPS plus each RPM signature; no signed-repomd claim',
       'support_scope':'Oracle EPEL development packages and CodeReady are not a Playwright-supported Oracle platform; actual native smoke required'}
    write(stage/'acquisition.json',canonical(manifest));return manifest


def verify_signatures(stage,manifest,logs):
    db=stage/'verification-rpmdb';db.mkdir(mode=0o700,exist_ok=False)
    command(['/usr/bin/rpm','--dbpath',str(db),'--initdb'],logs/'rpmdb-init.txt')
    for item in manifest['keys']:
        path=stage/'keys'/item['filename']
        pin=KEYS.get(item['filename'])
        if pin is None or item['url']!=pin['url'] or fingerprints(regular(path,65536))!=sorted(pin['fingerprints']):
            raise BootstrapError('exact Oracle signing keys required')
        command(['/usr/bin/rpm','--dbpath',str(db),'--import',str(path)],logs/('import-'+item['filename']+'.txt'))
    ids={value[-8:].lower() for pin in KEYS.values() for value in pin['fingerprints']}
    signatures=[]
    for index,package in enumerate(manifest['packages']):
        path=stage/'rpms'/package['filename']
        raw=command(['/usr/bin/rpmkeys','--dbpath',str(db),'--checksig','--verbose',str(path)],logs/('signature-%02d.txt'%index))
        text=raw.decode();found=re.findall(r'Signature, key ID ([0-9a-fA-F]{8,16}): OK',text)
        if not found or any(item[-8:].lower() not in ids for item in found) or re.search(r'NOKEY|NOT OK|BAD|NOTTRUSTED',text):
            raise BootstrapError('RPM cryptographic signature did not verify against pinned key')
        meta=command(['/usr/bin/rpm','--dbpath',str(db),'-qp','--qf',RPM_FORMAT,str(path)],logs/('package-%02d.txt'%index))
        expected='\t'.join(str(package[k]) for k in ('name','epoch','version','release','arch'))+'\n'
        if meta.decode()!=expected: raise BootstrapError('signed RPM metadata differs from solver')
        files=command(['/usr/bin/rpm','--dbpath',str(db),'-qpl',str(path)],logs/('package-files-%02d.txt'%index))
        if any(line.startswith(('/etc/systemd/','/usr/lib/systemd/system/','/etc/sudoers','/etc/cron','/etc/pam.d/','/etc/ssh/')) for line in files.decode().splitlines()):
            raise BootstrapError('dependency would install unrelated privileged service or policy')
        command(['/usr/bin/rpm','--dbpath',str(db),'-qp','--scripts',str(path)],logs/('package-scripts-%02d.txt'%index))
        signatures.append({'filename':package['filename'],'verified_key_ids':found,'sha256':package['sha256']})
    return signatures


def snapshot(logs,tag):
    paths=('/etc/merlin-dot-private/config.json','/etc/systemd/system/merlin-dot-private.service',
           '/etc/merlin-model-provider/manifest.json','/etc/systemd/system/merlin-model-provider.service')
    hashes={path:identity(Path(path),1048576)['sha256'] for path in paths}
    if hashes[paths[0]]!=PRIVATE_CONFIG_SHA or hashes[paths[1]]!=PRIVATE_UNIT_SHA:
        raise BootstrapError('private deployed configuration differs from reviewed baseline')
    result={'files':hashes,'private_current':os.readlink('/opt/merlin-dot-private/current'),'services':{}}
    properties=('ActiveState','SubState','MainPID','User','Group','MemoryMax','MemorySwapMax','CPUQuotaPerSecUSec','TasksMax')
    for service in ('merlin-dot-private.service','merlin-model-provider.service'):
        raw=command(['/usr/bin/systemctl','show',service,'--no-pager']+['--property='+name for name in properties],logs/(tag+'-'+service+'.txt'))
        result['services'][service]=dict(line.split('=',1) for line in raw.decode().splitlines() if '=' in line)
        if result['services'][service].get('ActiveState')!='active': raise BootstrapError('existing runtime unavailable')
    return result


def duration_us(value):
    units={'us':1,'ms':1000,'s':1000000,'min':60000000,'h':3600000000}
    if not isinstance(value,str) or not value: raise BootstrapError('systemd bounded duration required')
    pieces=re.findall(r'([0-9]+(?:\.[0-9]+)?)(us|ms|min|s|h)',value)
    if not pieces or ''.join(number+unit for number,unit in pieces)!=re.sub(r'\s+','',value):
        raise BootstrapError('systemd duration grammar differs')
    return sum(round(float(number)*units[unit]) for number,unit in pieces)


def controller_envelope(execution,logs):
    unit='merlin-browser-bootstrap-%d-%d.service'%(execution['run_id'],execution['run_attempt'])
    names=('MainPID','ControlGroup','RuntimeMaxUSec','TimeoutStopUSec','KillMode','MemoryMax',
           'MemorySwapMax','CPUQuotaPerSecUSec','TasksMax')
    raw=command(['/usr/bin/systemctl','show',unit,'--no-pager']+['--property='+name for name in names],logs/'controller-envelope.txt',timeout=5)
    value=dict(line.split('=',1) for line in raw.decode().splitlines() if '=' in line)
    group='/system.slice/'+unit
    if (value.get('MainPID')!=str(os.getpid()) or value.get('ControlGroup')!=group
        or value.get('KillMode')!='control-group' or value.get('MemoryMax')!='2147483648'
        or value.get('MemorySwapMax')!='0' or value.get('TasksMax')!='256'
        or duration_us(value.get('RuntimeMaxUSec'))!=930000000
        or duration_us(value.get('TimeoutStopUSec'))!=15000000
        or duration_us(value.get('CPUQuotaPerSecUSec'))!=1000000):
        raise BootstrapError('actual whole-controller systemd envelope differs')
    observed=regular(Path('/proc/self/cgroup'),16384).decode().splitlines()
    if '0::'+group not in observed: raise BootstrapError('controller kernel cgroup differs')
    value['kernel_cgroup']=group;value['whole_descendant_kill_mode']='control-group'
    return value


def copy_verified(source,target,pin,maximum):
    # Immutable root staging closes the verification/use gap after acquisition.
    source=Path(source);target=Path(target)
    if identity(source,maximum)!=pin: raise BootstrapError('frozen input changed before root copy')
    source_fd=os.open(str(source),os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    target_fd=os.open(str(target),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o400)
    try:
        if not stat.S_ISREG(os.fstat(source_fd).st_mode): raise BootstrapError('copy source not regular')
        value=hashlib.sha256();count=0
        while True:
            chunk=os.read(source_fd,1048576)
            if not chunk: break
            count+=len(chunk)
            if count>maximum: raise BootstrapError('root copy ceiling')
            value.update(chunk)
            with memoryview(chunk) as view:
                while view:
                    written=os.write(target_fd,view);view=view[written:]
        os.fsync(target_fd)
        if {'sha256':value.hexdigest(),'bytes':count}!=pin: raise BootstrapError('frozen input changed while copying')
    finally: os.close(source_fd);os.close(target_fd)


def unpack_runtime(archive,pin,destination):
    if identity(archive,16*1024*1024)!={'sha256':pin['sha256'],'bytes':pin['bytes']}:
        raise BootstrapError('derived runtime ZIP differs from reviewed pin')
    destination.mkdir(mode=0o755,exist_ok=False)
    with zipfile.ZipFile(archive) as bundle:
        names=bundle.namelist()
        if len(names)!=len(set(names)) or not 1<len(names)<=512 or 'manifest.json' not in names:
            raise BootstrapError('bounded unique runtime ZIP entries required')
        manifest_raw=bundle.read('manifest.json')
        if len(manifest_raw)>1048576: raise BootstrapError('runtime manifest ceiling')
        manifest=decode(manifest_raw)
        if manifest.get('schema')!='merlin-browser-runtime/1' or manifest.get('expert_source_commit')!=pin['expert_source_commit']:
            raise BootstrapError('runtime source binding differs')
        entries=manifest.get('files')
        if not isinstance(entries,list) or set(names)!={'manifest.json'}|{item['path'] for item in entries}:
            raise BootstrapError('runtime archive exact manifest closure')
        total=0
        for entry in entries:
            name=entry['path'];pure=PurePosixPath(name)
            if pure.is_absolute() or '..' in pure.parts or not re.fullmatch(r'(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+',name) or not name.startswith(('python/','bin/')):
                raise BootstrapError('runtime member path')
            info=bundle.getinfo(name)
            if stat.S_IFMT(info.external_attr>>16) not in (0,stat.S_IFREG) or info.file_size>2*1024*1024:
                raise BootstrapError('runtime regular bounded member')
            raw=bundle.read(name);total+=len(raw)
            if total>16*1024*1024 or len(raw)!=entry['bytes'] or digest(raw)!=entry['sha256']:
                raise BootstrapError('runtime member integrity')
            parent=rooted((destination/name).parent)
            write(parent/pure.name,raw,0o755 if name=='bin/launch-episode' else 0o644)
        write(destination/'manifest.json',manifest_raw,0o644)
    required={'bin/launch-episode','bin/smoke_renderer.py','python/merlin/public_browser.py',
              'python/merlin/browser_egress.py','python/merlin/browser_policy.py','python/merlin/browser_service.py',
              'python/merlin/browser_ingest.py'}
    if not required.issubset(set(names)): raise BootstrapError('callable runtime closure incomplete')
    return manifest,digest(manifest_raw)


def service_unit(release):
    return ('[Unit]\nDescription=Merlin bounded public research browser\nAfter=network.target\n\n[Service]\n'
      'Type=simple\nUser=root\nGroup=root\nUMask=0077\n'
      'RuntimeDirectory=merlin-public-browser\nRuntimeDirectoryMode=0755\nRuntimeDirectoryPreserve=yes\n'
      'ExecStart='+str(release/'venv'/'bin'/'python')+' -I -B -c "import sys;sys.path.insert(0,\''+str(release/'python')+'\');from merlin.browser_service import main;raise SystemExit(main())" --config /etc/merlin-public-browser/service.json\n'
      'Environment=PYTHONDONTWRITEBYTECODE=1\nEnvironment=HOME=/var/empty\n'
      'Restart=on-failure\nRestartSec=2\nTimeoutStopSec=5\nKillMode=control-group\n'
      'MemoryMax=256M\nMemorySwapMax=0\nCPUQuota=25%\nTasksMax=32\n'
      # The trusted root helper creates a bounded host-visible episode tmpfs
      # for PID1-launched sibling units. Mount namespaces belong to workers;
      # a supervisor-private mount would be invisible to those sibling units.
      'RestrictAddressFamilies=AF_UNIX\nProtectHome=no\nPrivateTmp=no\n'
      '[Install]\nWantedBy=multi-user.target\n').encode()


PUBLIC_CASES=(
 ('database-arxiv','https://arxiv.org/abs/1706.03762',('Attention Is All You Need',)),
 ('news-nasa','https://www.nasa.gov/news/all-news/',('NASA','News')),
 ('repository-openmdao','https://github.com/OpenMDAO/OpenMDAO',('OpenMDAO',)))


def native_acceptance(release,opc_gid,browser_uid,request_id,logs):
    """Three fixed public episodes as the actual Merlin UID, then read restart."""
    result={'schema':'merlin-browser-native-acceptance/1','status':'started','public_cases':[],
      'max_public_episodes':3,'fixture_episodes':1,'parallel_episodes':1,'model_calls':0,
      'external_spend_usd':0,'caller_uid':982,'caller_gid':opc_gid,
      'historical_private_records':'not touched; independent existing-private-runtime check remains authoritative'}
    def invoke(value,name,uid=982):
        code=("import json,os,sys,time\nsys.path.insert(0,"+repr(str(release/'python'))+")\n"
              "from merlin.browser_client import request_browser\n"
              "v=json.loads("+repr(canonical(value).decode())+")\n"
              "deadline=time.monotonic()+8\nattempts=0\nwhile True:\n"
              " attempts+=1\n try:\n  response=request_browser(v)\n  break\n"
              " except (FileNotFoundError,ConnectionRefusedError):\n"
              "  if time.monotonic()>=deadline: raise\n  time.sleep(.1)\n"
              "print(json.dumps({'caller_uid':os.getuid(),'caller_gid':os.getgid(),"
              "'connection_attempts':attempts,'response':response},sort_keys=True))")
        raw=command([str(release/'venv'/'bin'/'python'),'-I','-B','-c',code],logs/name,
                    timeout=82,limit=2*1024*1024,user=uid,group=opc_gid)
        answer=decode(raw)
        if answer.get('caller_uid')!=uid or answer.get('caller_gid')!=opc_gid:
            raise BootstrapError('native caller kernel identity differs')
        return answer['response']
    base={'schema':'merlin-browser-request-api/1'}
    status_request={**base,'operation':'status','episode_id':'readiness-'+request_id}
    deadline=time.monotonic()+8
    socket_path=Path('/run/merlin-public-browser/browser.sock')
    while not socket_path.is_socket():
        if time.monotonic()>deadline: raise BootstrapError('browser supervisor readiness deadline')
        time.sleep(.1)
    if invoke(status_request,'caller-readiness.txt').get('status')!='not_found':
        raise BootstrapError('actual Merlin status route failed')
    denied=invoke(status_request,'unauthorized-peer.txt',uid=1000)
    if denied.get('status')!='denied': raise BootstrapError('unauthorized runner peer was not denied')
    result['unauthorized_peer']={'uid':1000,'status':denied['status']}
    repeat_request=None;repeat_response=None
    for name,url,expected in PUBLIC_CASES:
        episode=name+'-'+request_id
        submitted=invoke({**base,'operation':'submit','episode_id':episode,'actions':[{'action':'open','url':url}]},name+'-submit.txt')
        case={'id':name,'episode_id':episode,'url':url,'submit_status':submitted.get('status')}
        result['public_cases'].append(case)
        if submitted.get('status')!='completed':
            case['failure_ref']=submitted.get('failure_ref')
            write(logs/'native-acceptance-partial.json',canonical(result))
            raise BootstrapError('actual caller episode failed; see preserved native evidence')
        launch=decode(regular(STATE/'episodes'/episode/'launch-receipt.json',2*1024*1024))
        if launch.get('status')!='succeeded' or launch.get('all_workers_stopped') is not True or launch.get('scratch_unmounted') is not True:
            raise BootstrapError('native worker shutdown/isolation gate failed')
        for role,private_network,memory in (('broker','no','134217728'),('renderer','yes','1073741824')):
            samples=launch.get('live_unit_samples',{}).get(role,[])
            if not samples: raise BootstrapError('actual live worker resource profile missing')
            if any(sample.get('User')!=str(browser_uid) or sample.get('PrivateNetwork')!=private_network or
                   sample.get('NoNewPrivileges')!='yes' or sample.get('MemoryMax')!=memory or
                   sample.get('MemorySwapMax')!='0' or sample.get('KillMode')!='control-group' for sample in samples):
                raise BootstrapError('observed worker resource/isolation profile differs')
            for sample in samples:
                cpu=sample.get('cpu.max','').split()
                if (len(cpu)!=2 or not all(value.isdigit() for value in cpu)
                    or int(cpu[1])<=0 or int(cpu[0])/int(cpu[1])!=(.25 if role=='broker' else 1)
                    or sample.get('memory.max','').strip()!=memory
                    or sample.get('memory.swap.max','').strip()!='0' or sample.get('pids.max','').strip()!='128'):
                    raise BootstrapError('observed cgroup resource limits differ')
        publication=submitted.get('publication',{})
        sources=publication.get('sources',[])
        if not sources: raise BootstrapError('canonical browser publication has no source')
        capture=sources[0]['observation_id']
        read_request={**base,'operation':'read','episode_id':episode,'observation_id':capture,'kind':'text',
                      'start_byte':0,'length_bytes':16384,'link_start':0,'link_limit':20}
        readback=invoke(read_request,name+'-read.txt')
        text=readback.get('content','')
        passed=(readback.get('kind')=='text' and readback.get('encoding')=='utf-8'
                and isinstance(text,str) and len(text.encode())>=100
                and all(word.lower() in text.lower() for word in expected)
                and type(readback.get('document_status')) is int and 200<=readback['document_status']<300
                and readback.get('model_calls')==0 and readback.get('qualification') is False)
        case.update(acceptance=passed,document_status=readback.get('document_status'),title=readback.get('title'),
                    text_bytes=readback.get('total_bytes'),artifact_ref=readback.get('artifact_ref'),
                    capture_event_ref=readback.get('capture_event_ref'),publication=publication,
                    launch_receipt_sha256=digest(canonical(launch)))
        if repeat_request is None: repeat_request,repeat_response=read_request,readback
    command(['/usr/bin/systemctl','restart',SERVICE],logs/'supervisor-restart.txt',timeout=10)
    # Socket replacement can lag the completed restart job. A bounded readiness
    # check does not submit a new browser episode or reacquire source bytes.
    deadline=time.monotonic()+8
    while not socket_path.is_socket():
        if time.monotonic()>deadline: raise BootstrapError('restarted supervisor readiness deadline')
        time.sleep(.1)
    reread=invoke(repeat_request,'post-restart-read.txt')
    if reread!=repeat_response: raise BootstrapError('canonical retained read changed across supervisor restart')
    result['post_restart_read']={'unchanged':True,'new_acquisition':False,'artifact_ref':reread['artifact_ref']}
    result['status']='passed' if all(case['acceptance'] for case in result['public_cases']) else 'source_acceptance_incomplete'
    write(logs/'native-acceptance.json',canonical(result))
    return result


def export_tree(source,target,limit=256*1024*1024):
    """Bounded raw export of operation-owned evidence, rejecting every link."""
    source=Path(source)
    if not source.exists(): return {'present':False}
    if not stat.S_ISDIR(source.lstat().st_mode): raise BootstrapError('evidence root is not a directory')
    target.mkdir(mode=0o700,exist_ok=False);os.chown(target,1000,1000)
    total=count=0
    for parent,dirs,files in os.walk(source,followlinks=False):
        dirs.sort();files.sort()
        for name in dirs:
            path=Path(parent)/name
            if not stat.S_ISDIR(path.lstat().st_mode): raise BootstrapError('evidence directory link rejected')
            relative=path.relative_to(source)
            if len(relative.parts)>16: raise BootstrapError('evidence directory depth')
            dest=target/relative;dest.mkdir(mode=0o700);os.chown(dest,1000,1000)
        for name in files:
            path=Path(parent)/name;raw=regular(path,min(16*1024*1024,limit-total));total+=len(raw);count+=1
            if total>limit or count>8192: raise BootstrapError('raw evidence export ceiling')
            dest=target/path.relative_to(source);write(dest,raw);os.chown(dest,1000,1000)
    return {'present':True,'files':count,'bytes':total}


def install(acquisition,acquisition_sha,bundle,bundle_pin,request,execution,output):
    if os.geteuid()!=0 or platform.machine()!='aarch64' or sys.version_info[:2]!=(3,9):
        raise BootstrapError('fixed native root installation required')
    os.umask(0o022)
    validate_request(request,execution)
    output=Path(output);source=Path(acquisition)
    raw=regular(source/'acquisition.json',2*1024*1024)
    if digest(raw)!=acquisition_sha: raise BootstrapError('acquisition manifest pin differs')
    manifest=decode(raw)
    if manifest.get('schema')!='merlin-browser-acquisition/1' or manifest.get('repositories')!=REPOS:
        raise BootstrapError('fixed acquisition contract differs')
    checked_transaction(output,manifest['packages'],manifest['before_packages'],manifest['removed'],
                        label='root-candidate',runner_readable=True)
    rooted(BOOTSTRAP_STATE,0o700)
    lock=os.open(str(BOOTSTRAP_STATE/'operation.lock'),os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    intent=BOOTSTRAP_STATE/'bootstrap-intent.json';outcome=BOOTSTRAP_STATE/'bootstrap-result.json'
    if any(path.exists() or path.is_symlink() for path in (intent,outcome,PREFIX/'current',CONFIG/'host.json')):
        raise BootstrapError('existing bootstrap state requires explicit reconciliation')
    staged=BOOTSTRAP_STATE/request['request_id'];staged.mkdir(mode=0o700,exist_ok=False)
    logs=staged/'logs';logs.mkdir(mode=0o700)
    receipt={'schema':'merlin-browser-bootstrap/1','request':request,'execution':execution,
      'runtime_pin':bundle_pin,'acquisition_sha256':acquisition_sha,'status':'started','model_calls':0,
      'external_model_cost_usd':0,'qualification':False,'promotion_authority':False,
      'package_support_limit':manifest['support_scope'],'rpm_install_attempted':False,'rpm_install_completed':False}
    write(intent,canonical(receipt));write(staged/'acquisition.json',raw)
    changed=False
    try:
        receipt['controller_envelope']=controller_envelope(execution,logs)
        receipt['before']=snapshot(logs,'before')
        opc=grp.getgrnam('opc');merlin=pwd.getpwuid(982)
        private=receipt['before']['services']['merlin-dot-private.service']
        pid=private.get('MainPID','')
        if merlin.pw_name!='merlin-dot' or private.get('Group')!='opc' or not re.fullmatch('[1-9][0-9]{0,8}',pid):
            raise BootstrapError('observed private caller identity differs')
        status=regular(Path('/proc')/pid/'status',32768).decode()
        fields=dict(line.split(':',1) for line in status.splitlines() if ':' in line)
        uid=[int(v) for v in fields.get('Uid','').split()]
        gid=[int(v) for v in fields.get('Gid','').split()]
        if len(uid)!=4 or uid[1]!=982 or len(gid)!=4 or gid[1]!=opc.gr_gid:
            raise BootstrapError('live Merlin effective UID/GID differs')
        try: pwd.getpwnam('merlin-browser')
        except KeyError: pass
        else: raise BootstrapError('dedicated browser identity already exists')
        receipt['private_caller']={'uid':982,'effective_gid':opc.gr_gid,'private_service_pid':int(pid),
                                   'unit_group':'opc','account_groups_changed':False}
        write(staged/'preflight.json',canonical({'before':receipt['before'],'private_caller':receipt['private_caller']}))
        if installed(logs/'rpm-live-before.txt')!=manifest['before_packages']:
            raise BootstrapError('installed package set changed since dependency resolution')
        if Path('/etc/os-release').is_symlink() or identity(Path('/etc/os-release'),8192)['sha256']!='a542f10c7ce5e1f1d1e15265abcd5e2dff55ea0023e801221d5eb92c2622569c':
            raise BootstrapError('observed Oracle9.8 host identity changed')
        for kind,items in (('rpms',manifest['packages']),('wheels',manifest['wheels']),('keys',manifest['keys'])):
            (staged/kind).mkdir(mode=0o700)
            for item in items:
                if kind=='wheels':
                    match=[pin for pin in WHEELS if pin['filename']==item['filename']]
                    if len(match)!=1 or any(item[key]!=match[0][key] for key in match[0]): raise BootstrapError('fixed wheel pin differs')
                copy_verified(source/kind/item['filename'],staged/kind/item['filename'],
                              {'sha256':item['sha256'],'bytes':item['bytes']},MAX_DOWNLOAD)
        if {v['filename'] for v in manifest['wheels']}!={v['filename'] for v in WHEELS} or {v['filename'] for v in manifest['keys']}!=set(KEYS):
            raise BootstrapError('exact dependency/signing-key closure required')
        copy_verified(bundle,staged/'runtime.zip',{'sha256':bundle_pin['sha256'],'bytes':bundle_pin['bytes']},16*1024*1024)
        receipt['signatures']=verify_signatures(staged,manifest,logs)
        paths=[str(staged/'rpms'/p['filename']) for p in manifest['packages']]
        for item in manifest['keys']:
            command(['/usr/bin/rpm','--import',str(staged/'keys'/item['filename'])],logs/('host-key-'+item['filename']+'.txt'))
        command(['/usr/bin/rpm','--install','--test']+paths,logs/'rpm-install-test.txt',timeout=90)
        receipt['frozen_install_plan']={'packages':manifest['packages'],'signature_check':'all verified','rpm_test':'passed',
                                       'before_packages_sha256':digest(canonical(manifest['before_packages']))}
        write(staged/'frozen-install-plan.json',canonical(receipt['frozen_install_plan']))
        receipt['rpm_install_attempted']=True
        write(staged/'rpm-install-intent.json',canonical({'packages':manifest['packages'],'operation':'install-only'}))
        command(['/usr/bin/rpm','--install']+paths,logs/'rpm-install.txt',timeout=240)
        changed=True;receipt['rpm_install_completed']=True
        after=installed(logs/'rpm-after.txt')
        old=[v for v in manifest['before_packages'] if v['name']!='gpg-pubkey']
        new=[{key:p[key] for key in ('name','epoch','version','release','arch')} for p in manifest['packages']]
        expected=sorted(old+new,key=lambda value:tuple(value[key] for key in ('name','epoch','version','release','arch')))
        observed=[v for v in after if v['name']!='gpg-pubkey']
        if observed!=expected: raise BootstrapError('installed package delta exceeds exact additive transaction')
        receipt['package_delta']={'added':new,'gpg_keys':[v for v in after if v['name']=='gpg-pubkey'],
                                  'prior_packages_preserved':True}
        command(['/usr/sbin/useradd','--system','--user-group','--no-create-home','--home-dir','/var/empty',
                 '--shell','/sbin/nologin','merlin-browser'],logs/'create-user.txt')
        account=pwd.getpwnam('merlin-browser')
        if account.pw_uid==0 or os.getgrouplist(account.pw_name,account.pw_gid)!=[account.pw_gid]:
            raise BootstrapError('browser/private caller account contract')
        receipt['accounts']={'browser_uid':account.pw_uid,'browser_gid':account.pw_gid,'opc_gid':opc.gr_gid,
                             'authorized_client_uid':982,'private_client_effective_group_verified':True}
        rooted(PREFIX/'releases');release=PREFIX/'releases'/bundle_pin['sha256']
        runtime,manifest_sha=unpack_runtime(staged/'runtime.zip',bundle_pin,release)
        command(['/usr/bin/python3','-I','-B','-m','venv','--copies',str(release/'venv')],logs/'venv-create.txt',timeout=60)
        command([str(release/'venv'/'bin'/'python'),'-I','-B','-m','pip','--isolated','install','--no-index','--no-deps',
                 '--no-compile']+[str(staged/'wheels'/pin['filename']) for pin in WHEELS],logs/'wheel-install.txt',timeout=90)
        command([str(release/'venv'/'bin'/'python'),'-I','-B','-m','pip','--isolated','check'],logs/'wheel-check.txt')
        version_code='import json;from importlib.metadata import version;print(json.dumps({n:version(n) for n in '+repr([pin['name'] for pin in WHEELS])+'},sort_keys=True))'
        versions=decode(command([str(release/'venv'/'bin'/'python'),'-I','-B','-c',version_code],logs/'wheel-versions.txt'))
        if versions!={pin['name']:pin['version'] for pin in WHEELS}: raise BootstrapError('installed wheel versions differ')
        binary=Path('/usr/lib64/chromium-browser/headless_shell')
        receipt['native_executable']={'path':str(binary),**identity(binary,512*1024*1024)}
        rooted(CONFIG);rooted(STATE);rooted(STATE/'episodes',0o700);rooted(STATE/'registry',0o700)
        host={'schema':'merlin-browser-host/1','release':str(release),'browser_uid':account.pw_uid,'browser_gid':account.pw_gid,
              'executable':str(binary),'executable_sha256':receipt['native_executable']['sha256'],'runtime_manifest_sha256':manifest_sha}
        write(CONFIG/'host.json',canonical(host),0o600)
        launcher={};exec(compile(regular(release/'bin'/'launch-episode',100000),'pinned-episode-launcher','exec'),launcher)
        fixture_id='bootstrap-fixture-'+request['request_id']
        episode=STATE/'episodes'/fixture_id;episode.mkdir(mode=0o700);(episode/'request').mkdir(mode=0o700)
        write(episode/'request'/'actions.json',canonical([{'action':'open','url':'https://example.com/'}]))
        write(episode/'request'/'limits.json',canonical(launcher['CEILINGS']))
        receipt['fixture']=launcher['run_episode'](fixture_id,fixture=True)
        fixture=decode(regular(episode/'result'/'fixture.json',65536))
        if fixture.get('status')!='succeeded' or fixture.get('playwright')!='1.60.0' or not fixture.get('chromium','').startswith(CHROMIUM_VERSION) or fixture.get('chromium_sandbox') is not True:
            raise BootstrapError('actual native fixture acceptance failed')
        receipt['fixture_observation']=fixture
        os.symlink(str(release),PREFIX/'current')
        service_config={'schema':'merlin-browser-service-config/1','registry_root':str(STATE/'registry'),
            'project_id':'merlin-browser-research','episodes_root':str(STATE/'episodes'),
            'socket_path':'/run/merlin-public-browser/browser.sock','socket_gid':opc.gr_gid,'allowed_uids':[0,982],
            'launcher':str(PREFIX/'current'/'bin'/'launch-episode'),'limits':launcher['CEILINGS'],'launch_timeout_seconds':75}
        write(CONFIG/'service.json',canonical(service_config),0o600)
        run_parent=rooted(Path('/run/merlin-public-browser'))
        os.chown(run_parent,0,opc.gr_gid);os.chmod(run_parent,0o755)
        unit=service_unit(release);write(Path('/etc/systemd/system')/SERVICE,unit,0o644)
        command(['/usr/bin/systemctl','daemon-reload'],logs/'daemon-reload.txt')
        command(['/usr/bin/systemctl','enable','--now',SERVICE],logs/'service-enable.txt',timeout=20)
        receipt['native_acceptance']=native_acceptance(release,opc.gr_gid,account.pw_uid,request['request_id'],logs)
        receipt['after']=snapshot(logs,'after')
        if receipt['after']!=receipt['before']: raise BootstrapError('existing private/model runtime changed')
        receipt['service_config_sha256']=digest(canonical(service_config));receipt['unit_sha256']=digest(unit)
        receipt['status']='installed_native_passed' if receipt['native_acceptance']['status']=='passed' else 'installed_source_acceptance_incomplete'
        receipt['public_episode_acceptance']=receipt['native_acceptance']['status']
    except BaseException as exc:
        receipt['status']='failed';receipt['error']={'type':type(exc).__name__,'message':str(exc)[:4000]}
        receipt['rollback']={'direct_private_runtime_mutation_requested':False,'new_browser_service_stopped':False,
          'package_install_attempted':receipt['rpm_install_attempted'],'automatic_retry':False}
        try:
            observed=installed(logs/'rpm-after-failure.txt')
            prior=manifest['before_packages']
            added=[row for row in observed if row not in prior]
            removed=[row for row in prior if row not in observed]
            receipt['package_failure_observation']={'installed_packages':observed,'added':added,'removed':removed,
                'install_attempted':receipt['rpm_install_attempted'],'install_command_completed':receipt['rpm_install_completed'],
                'partial_transaction_possible':receipt['rpm_install_attempted'] and not receipt['rpm_install_completed']}
            receipt['rollback']['additive_packages_retained_for_inspection']=bool(added)
        except BaseException as inventory_error:
            receipt['package_failure_observation']={'inventory_error':type(inventory_error).__name__,
                'install_attempted':receipt['rpm_install_attempted'],'state':'requires_reconciliation'}
        try:
            command(['/usr/bin/systemctl','disable','--now',SERVICE],logs/'failed-new-service-stop.txt',allowed=(0,1,5))
            receipt['rollback']['new_browser_service_stopped']=True
        except BaseException as stop_error: receipt['rollback']['stop_error']=type(stop_error).__name__
        current=PREFIX/'current'
        if current.is_symlink() and os.readlink(current)==str(PREFIX/'releases'/bundle_pin['sha256']):
            current.unlink();receipt['rollback']['inactive_release_pointer_removed']=True
        try: receipt['after_failure']=snapshot(logs,'after-failure')
        except BaseException as observed_error: receipt['after_failure_error']=type(observed_error).__name__
    finally:
        write(outcome,canonical(receipt));write(staged/'operation-receipt.json',canonical(receipt))
        # Evidence export contains only operation-owned artifacts/logs, no host
        # credentials, environment, arbitrary filesystem or existing user data.
        export=output/'bootstrap-evidence';export.mkdir(mode=0o700,exist_ok=False)
        for path in (intent,outcome,staged/'acquisition.json',staged/'operation-receipt.json'):
            write(export/path.name,regular(path,4*1024*1024))
        for path in sorted(logs.iterdir()):
            write(export/path.name,regular(path,8*1024*1024))
        for name in ('preflight.json','frozen-install-plan.json','rpm-install-intent.json'):
            frozen=staged/name
            if frozen.exists(): write(export/frozen.name,regular(frozen,4*1024*1024))
        for path in export.iterdir(): os.chown(path,1000,1000)
        os.chown(export,1000,1000)
        exported={}
        for prefix in ('bootstrap-fixture','database-arxiv','news-nasa','repository-openmdao'):
            episode=prefix+'-'+request['request_id']
            exported[episode]=export_tree(STATE/'episodes'/episode,output/episode)
        exported['canonical_registry']=export_tree(STATE/'registry',output/'canonical-browser-registry')
        write(output/'raw-evidence-export.json',canonical(exported));os.chown(output/'raw-evidence-export.json',1000,1000)
        os.close(lock)
    if receipt['status']=='failed': raise BootstrapError('bootstrap failed; raw evidence preserved')
    return receipt
