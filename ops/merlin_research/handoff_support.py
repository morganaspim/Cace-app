"""Pinned copies of reviewed bounded I/O and anchored evidence-publication helpers.

No browser client, installation or provider operation is included.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import subprocess
import time
import uuid

ENV={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C.UTF-8','LC_ALL':'C.UTF-8',
     'HOME':'/var/empty','PYTHONDONTWRITEBYTECODE':'1'}

class OperationError(RuntimeError): pass


def canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()


def unique(items):
    result={}
    for key,value in items:
        if key in result: raise OperationError('duplicate JSON key')
        result[key]=value
    return result


def decode(raw):
    return json.loads(raw,object_pairs_hook=unique,
        parse_constant=lambda _: (_ for _ in ()).throw(OperationError('nonfinite JSON')))


def digest(raw): return hashlib.sha256(raw).hexdigest()


def safe_episode(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}',value):
        raise OperationError('safe episode identifier required')
    return value


def read(path,maximum,root=True):
    descriptor=os.open(str(path),os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        before=os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size>maximum or (root and (before.st_uid!=0 or before.st_mode&0o022)):
            raise OperationError('bounded immutable regular file required')
        pieces=[];count=0
        while True:
            piece=os.read(descriptor,min(1048576,maximum+1-count))
            if not piece: break
            pieces.append(piece);count+=len(piece)
            if count>maximum: raise OperationError('file byte ceiling')
        after=os.fstat(descriptor)
        if (before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_ino,after.st_size,after.st_mtime_ns):
            raise OperationError('file changed while read')
        return b''.join(pieces)
    finally: os.close(descriptor)


def root_directory(path,create=False,mode=0o700):
    path=Path(path)
    for part in reversed([path]+list(path.parents)):
        if create and not part.exists(): part.mkdir(mode=mode)
        info=part.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid!=0 or info.st_mode&0o022:
            raise OperationError('immutable root-owned directory required')
    return path


def write(path,raw,mode=0o600):
    descriptor=os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
    try:
        with os.fdopen(descriptor,'wb',closefd=False) as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
    finally: os.close(descriptor)
    directory=os.open(str(Path(path).parent),os.O_RDONLY|os.O_DIRECTORY)
    try: os.fsync(directory)
    finally: os.close(directory)


def command(argv,log,seconds=10,user=None,group=None,maximum=2*1024*1024):
    credentials={} if user is None else {'user':user,'group':group,'extra_groups':[]}
    process=subprocess.Popen(argv,cwd='/',env=ENV,stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True,**credentials)
    selector=selectors.DefaultSelector();selector.register(process.stdout,selectors.EVENT_READ)
    deadline=time.monotonic()+seconds;raw=bytearray();error=None
    try:
        while selector.get_map():
            left=deadline-time.monotonic()
            if left<=0: raise OperationError('fixed operation subprocess deadline')
            for key,_ in selector.select(min(.2,left)):
                chunk=os.read(key.fd,65536)
                if not chunk: selector.unregister(key.fileobj);continue
                if len(raw)+len(chunk)>maximum: raise OperationError('operation subprocess output ceiling')
                raw.extend(chunk)
        code=process.wait(timeout=max(.01,deadline-time.monotonic()))
        if code: raise OperationError('fixed operation subprocess failed with exit '+str(code))
        return bytes(raw)
    except BaseException as exc: error=exc;raise
    finally:
        selector.close()
        if error is not None or process.poll() is None:
            # The direct parent may already have exited while a descendant
            # still holds its stdout pipe. Always clean its whole group.
            try: os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError: pass
            if process.poll() is None: process.wait(timeout=5)
        process.stdout.close();write(log,bytes(raw))
        write(Path(str(log)+'.json'),canonical({'argv_sha256':digest(canonical(argv)),'returncode':process.returncode,
            'output_sha256':digest(raw),'bytes':len(raw),'error_type':type(error).__name__ if error else None}))


def duration_us(value):
    units={'us':1,'ms':1000,'s':1000000,'min':60000000,'h':3600000000}
    pieces=re.findall(r'([0-9]+(?:\.[0-9]+)?)(us|ms|min|s|h)',value or '')
    if not pieces or ''.join(n+u for n,u in pieces)!=re.sub(r'\s+','',value or ''):
        raise OperationError('bounded systemd duration required')
    return sum(round(float(number)*units[unit]) for number,unit in pieces)


def directory_descriptor(path):
    """Open a directory without following any absolute-path component."""
    path=Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise OperationError('absolute directory ancestry required')
    descriptor=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        for component in path.parts[1:]:
            child=os.open(component,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=descriptor)
            os.close(descriptor);descriptor=child
        return descriptor
    except BaseException:
        os.close(descriptor);raise


def publish_evidence(source,destination):
    """Copy only retained public evidence through an anchored destination fd.

    The runner owns the destination parent. It cannot redirect a privileged
    write by replacing that path after it is opened: every new descendant is
    created relative to an already verified directory descriptor.
    """
    source=root_directory(source);destination=Path(destination)
    if not destination.is_absolute() or '..' in destination.parts or destination.name!='operation':
        raise OperationError('fixed absolute evidence destination required')
    # Opening just the leaf with O_NOFOLLOW would still follow a substituted
    # ancestor. Hold each directory while opening its next component instead.
    parent=directory_descriptor(destination.parent)
    try:
        owner=os.fstat(parent)
        if owner.st_uid!=1000 or stat.S_IMODE(owner.st_mode)!=0o700:
            raise OperationError('protected runner-owned evidence parent required')
        os.mkdir(destination.name,mode=0o700,dir_fd=parent)
        descriptor=os.open(destination.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent)
    except BaseException:
        os.close(parent);raise
    try:
        target=os.fstat(descriptor)
        if target.st_uid!=0 or stat.S_IMODE(target.st_mode)!=0o700:
            raise OperationError('new protected evidence destination required')
        totals={'files':0,'bytes':0}
        def copy(directory,output_fd,depth=0):
            if depth>8: raise OperationError('evidence publication depth ceiling')
            root_directory(directory)
            for entry in sorted(directory.iterdir()):
                info=entry.lstat()
                if stat.S_ISDIR(info.st_mode):
                    os.mkdir(entry.name,mode=0o700,dir_fd=output_fd)
                    child=os.open(entry.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=output_fd)
                    try:
                        copy(entry,child,depth+1);os.fsync(child);os.fchown(child,1000,1000)
                    finally: os.close(child)
                elif stat.S_ISREG(info.st_mode):
                    raw=read(entry,16*1024*1024);totals['files']+=1;totals['bytes']+=len(raw)
                    if totals['files']>2048 or totals['bytes']>80*1024*1024:
                        raise OperationError('evidence publication ceiling')
                    leaf=os.open(entry.name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,
                                 0o600,dir_fd=output_fd)
                    try:
                        with os.fdopen(leaf,'wb',closefd=False) as stream:
                            stream.write(raw);stream.flush();os.fsync(stream.fileno())
                        os.fchown(leaf,1000,1000)
                    finally: os.close(leaf)
                else: raise OperationError('nonregular evidence publication entry')
        copy(source,descriptor);os.fsync(descriptor)
        visible_parent=directory_descriptor(destination.parent)
        try:
            observed=os.fstat(visible_parent)
            if (observed.st_dev,observed.st_ino)!=(owner.st_dev,owner.st_ino):
                raise OperationError('runner evidence parent moved during publication')
            final=os.stat(destination.name,dir_fd=visible_parent,follow_symlinks=False)
            if (final.st_dev,final.st_ino)!=(target.st_dev,target.st_ino):
                raise OperationError('runner evidence destination moved during publication')
        finally: os.close(visible_parent)
        os.fchown(descriptor,1000,1000)
        return totals
    finally: os.close(descriptor);os.close(parent)
