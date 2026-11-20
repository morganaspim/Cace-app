"""Fixed, unprivileged source assembly and synthetic integration validation.

This controller never changes a service, installs dependencies, reads private
state, or accepts caller-selected code. Input archives are exact content pins.
"""
import base64
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import stat
import subprocess
import sys
import zipfile
import zlib

SOURCE = '8baae309bc215d8c019f57d41410fa5989be0d6f'
PARENT = '54973bd683021a5566aa197bdc510d4f3bca20a1'
PINS = {
    'baseline': ('ed668d9ebd37604aa827d06c5a6ea35d34152302', 'fc1ba9893938176be76aae0068f3be33c7dcc3ebb16e858892f8e5e05568ceb3'),
    'runtime': ('1d55b9a94ff843d847b0be9322f22257a21a2dbf', 'efe57bada5cd86f45118cac0036faf497f9aa60972508e036aed09f7b8cf04db'),
    'scheduler_tests': ('02734876a67d31ed84f4736a4db5ab6fefc4a199', 'f3bd8fbbc91cddf30703026b123c39047ca3e5a1288d69937c6bda36a6c86ac9'),
    'overlay_transport': ('bdbfd258edda1e1c944d6e3d1a324fe15d42aa18', '8b0a5942a4a15cff9df4a816968686fd118e4fe0c188ee87665fdfb8a2f70ff9'),
}
OVERLAY_SHA = '7056bbf543aaf2c7243afad8888301a49d30dc47d217b6851df5324a5b594b49'
OVERLAY_FILES = {
    'python/merlin/branch_research.py': '29f69cc519a684ae5315a5eead0651a5ccf5040ce52e582a0d93355ada806af7',
    'python/merlin/branch_registry.py': '11498d00b9ffbb4f16de7ad208b373b66371119046bd3c52195f959a46a7a70d',
    'tests/test_branch_registry.py': 'db669198b787b5be1024eef4f94bfd85006a5699f695b2759aa4993c34e1afe8',
}
DEPENDENCIES = {
    'python/merlin/scientific_loop.py': '5c1315694377fd64e739d7d379193fe793f108b7',
    'python/merlin/engineering_ir.py': '0eadcdb5c240486ec7dcc336ba4f3d82752d6d04',
    'python/dot_ai_os/research_protocol.py': '8a7db9e9e3b255b602acacd7435942276fe9e429',
    'python/dot_ai_os/research_tools.py': 'a04514e96a14edb959afc07f8e66d86679bf908f',
    'python/dot_ai_os/job_inbox.py': '61e6a4b8186df4e52ba781fbf6eed3cfcf2edece',
    'python/dot_ai_os/math_lenses.py': '3173df34c930578cba6eee631a5fda26bccbcead',
    'python/dot_ai_os/dual_coder.py': '915570ab37f61e3cc353d2e7bd4e1c14709bc7e0',
    'python/dot_ai_os/simulation_research.py': '27026f71c47f07e9af1334dddd87d817cf5184b7',
    'python/dot_ai_os/private_runtime.py': 'f4e9949dff9ac20389adfc0e7a9ff8786377999e',
}
OLD_TESTS = {
    'tests/test_branch_research.py': '36ad328f121b0f545a00f4657a35d21bc6adf8addd583acb73d299c03c8f8f11',
    'tests/test_branch_research_boundaries.py': '34735ebc088b54f0e8f11d75871246dd215cabad15c0e0ee941092162adf905a',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git_blob(raw):
    return hashlib.sha1(('blob %d\0' % len(raw)).encode() + raw).hexdigest()


def unique(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('duplicate JSON field')
        result[key] = value
    return result


def unpack(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        if len(infos) > 100 or sum(i.file_size for i in infos) > 4 * 1024 * 1024:
            raise ValueError('archive limits')
        result = {}
        for info in infos:
            name = info.filename
            if (name in result or info.is_dir() or PurePosixPath(name).is_absolute()
                    or any(x in ('', '.', '..') for x in name.split('/')) or '\\' in name
                    or info.flag_bits & 1 or stat.S_IFMT(info.external_attr >> 16) not in (0, stat.S_IFREG)):
                raise ValueError('unsafe archive member')
            result[name] = archive.read(info)
    return result


def checked_manifest(files):
    manifest = json.loads(files['manifest.json'], object_pairs_hook=unique)
    if set(files) != set(manifest['files']) | {'manifest.json'}:
        raise ValueError('manifest file set')
    if any(sha(files[name]) != expected for name, expected in manifest['files'].items()):
        raise ValueError('manifest source bytes')
    return manifest


def assemble(inputs):
    if set(inputs) != set(PINS):
        raise ValueError('exact fixed input set required')
    for name, (blob, checksum) in PINS.items():
        raw = inputs[name]
        if len(raw) > 1024 * 1024 or git_blob(raw) != blob or sha(raw) != checksum:
            raise ValueError('input bytes differ: ' + name)
    baseline = unpack(inputs['baseline']); manifest = checked_manifest(baseline)
    if (manifest.get('schema') != 'merlin-learning-integration/1'
            or manifest.get('source_commit') != PARENT or manifest.get('raw_private_context_included') is not False):
        raise ValueError('canonical baseline identity')
    files = {name: baseline[name] for name in manifest['files']}
    runtime = unpack(inputs['runtime']); checked_manifest(runtime)
    for name, expected in DEPENDENCIES.items():
        raw = runtime[name]
        # Runtime packaging added one trailing newline to these two source files.
        # Restore the already reviewed repository bytes, then require exact Git identity.
        if name in {'python/merlin/scientific_loop.py', 'python/merlin/engineering_ir.py'}:
            if not raw.endswith(b'\n'):
                raise ValueError('source newline reconciliation differs')
            raw = raw[:-1]
        if name in files or git_blob(raw) != expected:
            raise ValueError('dependency identity mismatch')
        files[name] = raw
    tests = unpack(inputs['scheduler_tests'])
    if set(tests) != set(OLD_TESTS) | {'python/merlin/branch_research.py'}:
        raise ValueError('scheduler baseline slice differs')
    for name, expected in OLD_TESTS.items():
        if name in files or sha(tests[name]) != expected:
            raise ValueError('retained test identity mismatch')
        files[name] = tests[name]
    # One base64 transcription character corrupted this transport object during
    # upload. Preserve it, apply the single measured byte correction, and require
    # BOTH the original intended compressed digest and every committed file hash.
    # No supplied or inferred patch operations are accepted.
    packed = bytearray(inputs['overlay_transport'])
    if len(packed) != 11458 or packed[787] != 56:
        raise ValueError('fixed transport correction precondition')
    packed[787] = 248
    if sha(packed) != OVERLAY_SHA:
        raise ValueError('corrected transport identity mismatch')
    decoder = zlib.decompressobj()
    expanded = decoder.decompress(bytes(packed), 65537)
    if len(expanded) > 65536 or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
        raise ValueError('overlay expansion limit or trailer')
    overlay = json.loads(expanded, object_pairs_hook=unique)
    if (set(overlay) != {'schema', 'source_repository', 'source_commit', 'files'}
            or overlay['schema'] != 'merlin-code-overlay/1'
            or overlay['source_repository'] != 'Mannyspiro/expert-robot'
            or overlay['source_commit'] != SOURCE or set(overlay['files']) != set(OVERLAY_FILES)):
        raise ValueError('fixed overlay identity mismatch')
    for name, expected in OVERLAY_FILES.items():
        raw = overlay['files'][name].encode('utf-8')
        if name in files or sha(raw) != expected:
            raise ValueError('committed candidate file mismatch')
        files[name] = raw
    if any(not (name == 'tests/fixtures/learning-evidence-eval-v1.json' or
                (name.endswith('.py') and name.startswith(('python/merlin/', 'python/dot_ai_os/', 'tests/'))))
           for name in files):
        raise ValueError('payload exceeds code/synthetic fixture scope')
    file_digests = {name: sha(raw) for name, raw in sorted(files.items())}
    if sha(json.dumps(file_digests, sort_keys=True, separators=(',', ':')).encode()) != '7d1dba4ce8506b0196a22d39232659cdbf7f26013560e93f7a7ca0d526dd15b4':
        raise ValueError('complete reviewed source dependency closure differs')
    result = {'schema': 'merlin-canonical-branch-validation-source/1', 'source_commit': SOURCE,
              'parent_source_commit': PARENT, 'source_repository': 'Mannyspiro/expert-robot',
              'files': {name: sha(raw) for name, raw in sorted(files.items())},
              'git_blobs': {name: git_blob(raw) for name, raw in sorted(files.items())},
              'test_patterns': manifest['test_patterns'] + [Path(name).name for name in OLD_TESTS] + ['test_branch_registry.py'],
              'qualification': False, 'promotion_authority': False,
              'raw_private_context_included': False}
    return files, result


def run(api, output):
    report = {'schema': 'merlin-canonical-branch-validation/1', 'run_id': os.environ['GITHUB_RUN_ID'],
              'workflow_commit': os.environ['GITHUB_SHA'], 'source_commit': SOURCE,
              'runner': os.environ.get('RUNNER_NAME'), 'python': sys.version,
              'architecture': platform.machine(), 'host_configuration_changed': False,
              'production_service_modified': False, 'private_state_accessed': False,
              'qualification': False, 'promotion_authority': False}
    inputs = {}
    try:
        for name, (blob, _) in PINS.items():
            obj = api('git/blobs/' + blob)
            if obj.get('sha') != blob or obj.get('encoding') != 'base64':
                raise ValueError('fixed input object unavailable')
            inputs[name] = base64.b64decode(''.join(obj['content'].split()), validate=True)
        files, manifest = assemble(inputs)
        root = output / 'source'; root.mkdir(mode=0o700)
        for name, raw in files.items():
            target = root / name; target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as handle:
                handle.write(raw)
        encoded = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()
        (output / 'source-manifest.json').write_bytes(encoded)
        with zipfile.ZipFile(output / 'tested-source.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, raw in sorted({**files, 'manifest.json': encoded}.items()):
                info = zipfile.ZipInfo(name, (2026, 11, 20, 0, 0, 0)); info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED; archive.writestr(info, raw)
        report['source_package_sha256'] = sha((output / 'tested-source.zip').read_bytes())
        report['source_files'] = manifest['files']
        code = "import sys,json,unittest;from pathlib import Path;p=Path(sys.argv[1]);sys.path[:0]=[str(p/'python'),str(p)];s=unittest.TestSuite();[s.addTests(unittest.defaultTestLoader.discover(str(p/'tests'),pattern=x)) for x in json.loads(sys.argv[2])];r=unittest.TextTestRunner(verbosity=2).run(s);v={'tests':r.testsRun,'errors':len(r.errors),'failures':len(r.failures),'skipped':len(r.skipped),'passed':r.wasSuccessful() and not r.skipped and r.testsRun==208};print('RESULT='+json.dumps(v,sort_keys=True));sys.exit(0 if v['passed'] else 1)"
        executed = subprocess.run(['/usr/bin/python3', '-I', '-B', '-c', code, str(root), json.dumps(manifest['test_patterns'])],
                                  cwd=str(root), env={'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C.UTF-8'},
                                  capture_output=True, text=True, timeout=210)
        (output / 'tests.txt').write_text(executed.stdout + executed.stderr)
        lines = [line for line in executed.stdout.splitlines() if line.startswith('RESULT=')]
        report['tests'] = json.loads(lines[-1][7:]) if lines else {'passed': False}
        report['status'] = 'succeeded' if executed.returncode == 0 and report['tests'].get('passed') else 'failed'
    except Exception as exc:
        report.update(status='failed', error_class=type(exc).__name__, message=str(exc)[:1500])
    (output / 'report.json').write_text(json.dumps(report, indent=2, sort_keys=True))
    print(json.dumps({k: v for k, v in report.items() if k != 'source_files'}, indent=2, sort_keys=True))
    if report['status'] != 'succeeded':
        raise RuntimeError('fixed canonical candidate validation failed')
    return report
