"""Pinned harness repair: root-owned source paths for source-inspecting modules."""
import base64
import hashlib
import json

PARENT = '03e9b885e9b1f7ca472d22f0d3e1008e5b46e7ef'


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError('loader repair preimage differs')
    return text.replace(before, after)


def run(api, output):
    obj = api('git/blobs/' + PARENT)
    raw = base64.b64decode(''.join(obj['content'].split()), validate=True)
    if len(raw) > 32000 or hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() != PARENT:
        raise ValueError('exact parent controller required')
    namespace = {}
    exec(compile(raw, 'pinned-egm-controller', 'exec'), namespace)
    bootstrap = namespace['ROOT_BOOTSTRAP']
    bootstrap = replace_once(bootstrap, 'modules={}\nfor path,body in files.items():', '''# Already verified bytes only, under a private root-owned source directory.
source_stage=tempfile.TemporaryDirectory(prefix='merlin-egm-approved-source-',dir='/run')
source_root=Path(source_stage.name)
for path,body in files.items():
 relative=Path(path)
 if relative.is_absolute() or '..' in relative.parts: raise ValueError('invalid approved source path')
 dest=source_root/relative;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(body);dest.chmod(0o444)
modules={}
for path,body in files.items():''')
    bootstrap = replace_once(bootstrap,
        "path,body,package=modules[module.__name__];module.__file__='verified-memory:'+path",
        "path,body,package=modules[module.__name__];module.__file__=str(source_root/path)")
    bootstrap = replace_once(bootstrap,
        "sys.exit(0 if kernel['status']=='succeeded' and context['status']=='succeeded' else 1)",
        "source_stage.cleanup()\nsys.exit(0 if kernel['status']=='succeeded' and context['status']=='succeeded' else 1)")
    compile(bootstrap, 'root-owned-source-loader', 'exec')
    namespace['ROOT_BOOTSTRAP'] = bootstrap
    (output / 'root-loader.txt').write_text(bootstrap)
    (output / 'loader-repair.json').write_text(json.dumps({
        'parent_controller_git_blob': PARENT,
        'root_loader_sha256': hashlib.sha256(bootstrap.encode()).hexdigest(),
        'source_map_changed': False, 'runtime_permissions_changed': False,
        'repair': 'Exact verified bytes gain real root-owned paths for source hashing; imports still execute verified buffers.'
    }, indent=2) + '\n')
    return namespace['run'](api, output)
