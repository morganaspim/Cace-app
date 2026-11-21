"""Pinned unprivileged worker/outbox validation; no caller-selected code or host changes."""
import base64
import hashlib
import json
import lzma
import os
from pathlib import Path, PurePosixPath
import platform
import subprocess
import sys
import zipfile

SOURCE = 'b66f2d72cd755a8aa6b4d74da35f24620f71cebb'
TARGET = '5b0053ce04c2a9f9da80d9581efa148784aada8a'
PRIOR = '2a4ae2bd7bf451ed18b57af9be28272831b67377'
PARTS = ('80c4536dfa0f7ccae806a93ba1f9e22fda448a35', 'ec156ade290857eebbe09376aa1e04a35075e0d0',
         'f425e5866885cf43c56a5915aa82fa8ddf216bbc', '6655a1aaf1be1c4f7b67bc01e5cfb916a5789a9d')
DELTA_SHA = '75db0b064408d9aba1d5e0f90eeeec0af74cd7d65afcb1867c9f623318c99f68'
MAP_SHA = 'b944ff402a3fc7f2901286808d6dab90b3c6862565ed57a6b56c2389493a7f34'
CHANGED = {'python/dot_ai_os/bridge.py', 'python/merlin/branch_registry.py', 'python/merlin/council.py',
           'python/merlin/council_runtime.py', 'python/merlin/hermes_worker.py', 'python/merlin/learning_evidence.py',
           'python/merlin/learning_evidence_eval.py', 'python/merlin/research_evidence.py',
           'python/merlin/scientific_loop.py', 'python/merlin/titan_crypto_lab.py',
           'tests/test_branch_registry.py', 'tests/test_branch_worker.py'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON field')
        result[key] = value
    return result


def blob(api, identity, limit=1024 * 1024):
    obj = api('git/blobs/' + identity)
    if obj.get('sha') != identity or obj.get('encoding') != 'base64' or type(obj.get('size')) is not int or not 0 <= obj['size'] <= limit:
        raise ValueError('fixed bounded source object required')
    raw = base64.b64decode(''.join(obj['content'].split()), validate=True)
    if len(raw) != obj['size'] or git(raw) != identity:
        raise ValueError('exact source bytes differ')
    return raw


def apply_delta(files, packed):
    if len(packed) != 15016 or sha(packed) != DELTA_SHA:
        raise ValueError('fixed delta bytes differ')
    decoder = lzma.LZMADecompressor(memlimit=128 * 1024 * 1024)
    raw = decoder.decompress(packed, max_length=60958)
    if len(raw) != 60957 or not decoder.eof or decoder.unused_data:
        raise ValueError('delta expansion or trailer differs')
    delta = json.loads(raw, object_pairs_hook=unique)
    if (set(delta) != {'schema', 'source_commit', 'target_commit', 'changes'}
            or delta['schema'] != 'merlin-fixed-worker-delta/1' or delta['source_commit'] != SOURCE
            or delta['target_commit'] != TARGET or set(delta['changes']) != CHANGED):
        raise ValueError('delta source or path scope differs')
    files = dict(files)
    for name, change in delta['changes'].items():
        before = files.get(name, b'')
        if set(change) != {'before', 'after', 'git_blob', 'edits'} or sha(before) != change['before']:
            raise ValueError('delta preimage differs')
        text = before.decode('utf-8')
        end = 0
        for edit in change['edits']:
            if (not isinstance(edit, list) or len(edit) != 3 or type(edit[0]) is not int
                    or type(edit[1]) is not int or not isinstance(edit[2], str)
                    or not end <= edit[0] <= edit[1] <= len(text)):
                raise ValueError('invalid fixed delta edit')
            end = edit[1]
        for start, end, replacement in reversed(change['edits']):
            text = text[:start] + replacement + text[end:]
        after = text.encode('utf-8')
        if sha(after) != change['after'] or git(after) != change['git_blob']:
            raise ValueError('delta postimage differs')
        files[name] = after
    digests = {name: sha(body) for name, body in sorted(files.items())}
    if len(files) != 102 or sha(json.dumps(digests, sort_keys=True, separators=(',', ':')).encode()) != MAP_SHA:
        raise ValueError('full tested source map differs')
    return files


def run(api, output):
    report = {'schema': 'merlin-worker-replay-validation/1', 'source_commit': SOURCE,
              'target_commit': TARGET, 'run_id': os.environ['GITHUB_RUN_ID'],
              'workflow_commit': os.environ['GITHUB_SHA'], 'runner': os.environ['RUNNER_NAME'],
              'architecture': platform.machine(), 'python': sys.version,
              'host_configuration_changed': False, 'production_service_modified': False,
              'private_state_accessed': False, 'qualification': False, 'promotion_authority': False,
              'scope': 'Synthetic task/authority fixtures through actual canonical worker, outbox, handlers and stores; not provider or full-platform qualification.'}
    try:
        old = {}; exec(compile(blob(api, PRIOR, 32000), 'pinned-prior-assembly', 'exec'), old)
        baseline, prior_manifest = old['assemble']({name: blob(api, identity) for name, (identity, _) in old['PINS'].items()})
        files = apply_delta(baseline, b''.join(blob(api, identity, 4500) for identity in PARTS))
        root = output / 'source'; root.mkdir(mode=0o700)
        for name, body in files.items():
            path = PurePosixPath(name)
            if path.is_absolute() or any(x in ('', '.', '..') for x in name.split('/')) or '\\' in name:
                raise ValueError('unsafe source path')
            destination = root / name; destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open('xb') as stream:
                stream.write(body)
        manifest = {'schema': 'merlin-worker-source/1', 'source_commit': SOURCE, 'target_commit': TARGET,
                    'files': {name: sha(body) for name, body in sorted(files.items())},
                    'git_blobs': {name: git(body) for name, body in sorted(files.items())},
                    'qualification': False, 'promotion_authority': False}
        encoded = (json.dumps(manifest, sort_keys=True, indent=2) + '\n').encode()
        (output / 'source-manifest.json').write_bytes(encoded)
        with zipfile.ZipFile(output / 'tested-source.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, body in sorted({**files, 'manifest.json': encoded}.items()):
                info = zipfile.ZipInfo(name, (2026, 11, 20, 0, 0, 0)); info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED; archive.writestr(info, body)
        report.update(source_package_sha256=sha((output / 'tested-source.zip').read_bytes()),
                      source_map_sha256=MAP_SHA, source_files=manifest['files'])
        code = "import sys,json,unittest;from pathlib import Path;p=Path(sys.argv[1]);sys.path[:0]=[str(p/'python'),str(p)];s=unittest.defaultTestLoader.discover(str(p/'tests'),pattern='test_*.py');r=unittest.TextTestRunner(verbosity=2).run(s);v={'tests':r.testsRun,'errors':len(r.errors),'failures':len(r.failures),'skipped':len(r.skipped),'passed':r.wasSuccessful() and not r.skipped and r.testsRun==232};print('RESULT='+json.dumps(v,sort_keys=True));sys.exit(0 if v['passed'] else 1)"
        result = subprocess.run(['/usr/bin/python3', '-I', '-B', '-c', code, str(root)],
                    cwd=str(root), env={'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C.UTF-8'},
                    capture_output=True, text=True, timeout=210)
        (output / 'tests.txt').write_text(result.stdout + result.stderr)
        lines = [line for line in result.stdout.splitlines() if line.startswith('RESULT=')]
        report['tests'] = json.loads(lines[-1][7:]) if lines else {'passed': False}
        report['status'] = 'succeeded' if result.returncode == 0 and report['tests'].get('passed') else 'failed'
    except Exception as exc:
        report.update(status='failed', error_class=type(exc).__name__, message=str(exc)[:1500])
    (output / 'report.json').write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'source_files'}, sort_keys=True, indent=2))
    if report['status'] != 'succeeded':
        raise RuntimeError('fixed worker replay validation failed')
    return report
