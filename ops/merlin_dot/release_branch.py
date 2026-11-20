"""Fixed additive scheduler release. Reuses the existing private-service guards.

No service grants, unit, seed or private database are changed. The scheduler is
installed as a library; it is not exposed as a new remote execution tool.
"""
import base64
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import pwd
import stat
import subprocess
import sys
import tempfile
import zipfile

BASE_BLOB = '1d55b9a94ff843d847b0be9322f22257a21a2dbf'
BASE_SHA = 'efe57bada5cd86f45118cac0036faf497f9aa60972508e036aed09f7b8cf04db'
SLICE_BLOB = '02734876a67d31ed84f4736a4db5ab6fefc4a199'
SLICE_SHA = 'f3bd8fbbc91cddf30703026b123c39047ca3e5a1288d69937c6bda36a6c86ac9'
EXPERT_COMMIT = '5d5ecfbe2ed4bb29d7e5c0c86607e73780fd599f'
ADDITIONS = {
    'python/merlin/branch_research.py': '78cc71d4b506a59bf7712a41193ae24644f98f6ec59024c82ae4d7855da7e3b5',
    'tests/test_branch_research.py': '36ad328f121b0f545a00f4657a35d21bc6adf8addd583acb73d299c03c8f8f11',
    'tests/test_branch_research_boundaries.py': '34735ebc088b54f0e8f11d75871246dd215cabad15c0e0ee941092162adf905a',
}
SAFE_ENV = {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C.UTF-8'}
EXPECTED_TOOLS = {'health', 'context_status', 'context_search', 'context_fetch',
    'session_handoff', 'rsi_status', 'virtual_circuit_demo', 'research_contract',
    'research_episode_demo', 'mathematical_lenses_demo'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git_blob(raw):
    return hashlib.sha1(('blob %d\0' % len(raw)).encode() + raw).hexdigest()


def verify_additive(old, new):
    if (set(new) != set(old) | set(ADDITIONS) or set(old) & set(ADDITIONS)
            or any(new.get(k) != v for k, v in old.items())
            or any(new.get(k) != v for k, v in ADDITIONS.items())):
        raise ValueError('release must contain exactly the three pinned additions')


def assemble(base_raw, slice_raw, unpack_verified, output):
    if sha(base_raw) != BASE_SHA or sha(slice_raw) != SLICE_SHA:
        raise ValueError('pinned input archive mismatch')
    old = unpack_verified(base_raw, BASE_SHA, output / 'baseline')
    with zipfile.ZipFile(io.BytesIO(slice_raw)) as archive:
        if len(archive.namelist()) != 3 or set(archive.namelist()) != set(ADDITIONS):
            raise ValueError('slice file set mismatch')
        additions = {name: archive.read(name) for name in ADDITIONS}
    if any(sha(raw) != ADDITIONS[name] for name, raw in additions.items()):
        raise ValueError('source slice bytes mismatch')
    with zipfile.ZipFile(io.BytesIO(base_raw)) as archive:
        files = {name: archive.read(name) for name in old['files']}
    verify_additive(old['files'], {**old['files'], **ADDITIONS})
    files.update(additions)
    manifest = {**old, 'files': {name: sha(raw) for name, raw in sorted(files.items())}}
    # Preserve the original canonical base; additions have their own exact source
    # identity in the operation receipt rather than mislabelling the whole bundle.
    files['manifest.json'] = (json.dumps(manifest, sort_keys=True, indent=2) + '\n').encode()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name, raw in sorted(files.items()):
            info = zipfile.ZipInfo(name, (2026, 11, 20, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, raw)
    raw = buffer.getvalue()
    unpack_verified(raw, sha(raw), output / 'candidate')
    (output / 'runtime.zip').write_bytes(raw)
    return raw, manifest, sha((output / 'baseline/manifest.json').read_bytes())


def snapshot(g, release_sha, manifest_sha, expected_config=None):
    if os.geteuid() != 0:
        raise PermissionError('root-owned profile inspection requires root')
    source = g['SOURCE']
    for directory in (source, source / 'releases', g['CONFIG'].parent, g['UNIT'].parent):
        g['_root_directory'](directory)
    release = source / 'releases' / release_sha
    g['_current'](release)
    g['_regular'](g['UNIT'], expected=g['OLD_UNIT_SHA'], maximum=16000)
    config = g['_regular'](g['CONFIG'], maximum=16000)
    if expected_config is not None and sha(config) != expected_config:
        raise RuntimeError('configuration changed since validation')
    value = json.loads(config)
    grants = value.get('grants')
    if (value.get('schema') != 'merlin-private-host/1' or not isinstance(grants, list)
            or len(grants) != 1 or grants[0].get('uid') != 1000
            or grants[0].get('principal') != 'local-runner-opc'
            or not isinstance(grants[0].get('tools'), list)
            or len(grants[0]['tools']) != len(EXPECTED_TOOLS)
            or set(grants[0]['tools']) != EXPECTED_TOOLS):
        raise RuntimeError('existing grant profile differs from reviewed private service')
    if pwd.getpwnam('merlin-dot').pw_uid != 982 or pwd.getpwnam('opc').pw_uid != 1000:
        raise RuntimeError('service identity changed')
    g['_verify_release'](release, manifest_sha)
    return {'release_sha256': release_sha, 'manifest_sha256': manifest_sha,
            'config_sha256': sha(config), 'unit_sha256': g['OLD_UNIT_SHA'],
            'service_properties': g['_active'](), 'grants_changed': False}


def library_probe(release):
    code = """import sys,json,tempfile
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from merlin.branch_research import Branch,BranchResearch
import merlin.branch_research as m
assert Path(m.__file__).resolve()==Path(sys.argv[1])/'merlin/branch_research.py'
p=(Branch('root','Root',2),Branch('child','Child',1,('root',)))
with tempfile.TemporaryDirectory(prefix='merlin-release-smoke-') as t:
 r=BranchResearch(Path(t)/'test.sqlite3',p)
 def evaluate(key,inputs):
  inputs.clear()
  return {'passed':True,'detail':key}
 a=r.step(evaluate,budget=2)
 assert BranchResearch(r.database,p).status()==a and a['checkpoint']['cursor']==2
print(json.dumps({'installed_library_import':True,'restart_and_mutation_smoke':True,'remote_tool_exposed':False}))
"""
    result = subprocess.run(['/usr/bin/python3', '-I', '-B', '-c', code, str(release / 'python')],
        user=1000, group=1000, extra_groups=[], env=SAFE_ENV, cwd='/',
        capture_output=True, text=True, check=True, timeout=15)
    return json.loads(result.stdout)


def activate(g, unpack_verified, bundle_path, new_sha, old_manifest_sha, expected_config):
    source = g['SOURCE']
    old = source / 'releases' / BASE_SHA
    new = source / 'releases' / new_sha
    for directory in (source, source / 'releases', g['CONFIG'].parent):
        g['_root_directory'](directory)
    fd = os.open(source / '.research-upgrade.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077:
            raise RuntimeError('unsafe upgrade lock')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        before = snapshot(g, BASE_SHA, old_manifest_sha, expected_config)
        old_manifest = json.loads(g['_regular'](old / 'manifest.json', expected=old_manifest_sha))
        raw = g['_regular'](Path(bundle_path), root_owned=False, expected=new_sha, maximum=13 * 1024 * 1024)
        with tempfile.TemporaryDirectory(prefix='merlin-additive-release-') as temp:
            checked = Path(temp) / 'release'
            manifest = unpack_verified(raw, new_sha, checked)
            verify_additive(old_manifest['files'], manifest['files'])
            if {k: v for k, v in manifest.items() if k != 'files'} != {k: v for k, v in old_manifest.items() if k != 'files'}:
                raise RuntimeError('canonical base metadata changed')
            manifest_sha = sha((checked / 'manifest.json').read_bytes())
        if new.exists() or new.is_symlink():
            raise RuntimeError('release already exists; inspect prior attempt before retry')
        history = g['CONFIG'].parent / 'upgrade-history'
        g['_root_directory'](history)
        intent = history / ('branch-intent-' + new_sha + '.json')
        outcome = history / ('branch-result-' + new_sha + '.json')
        if any(path.exists() or path.is_symlink() for path in (intent, outcome)):
            raise RuntimeError('release history already exists; reconcile prior attempt')
        unpack_verified(raw, new_sha, new)
        g['_verify_release'](new, manifest_sha)
        record = {'schema': 'merlin-additive-library-release/1', 'old': before,
                  'new_bundle_sha256': new_sha, 'expert_source_commit': EXPERT_COMMIT,
                  'additions': ADDITIONS, 'unit_changed': False, 'grants_changed': False,
                  'private_state_edited_by_updater': False, 'remote_tool_exposed': False}
        g['_new_file'](intent, (json.dumps(record, indent=2) + '\n').encode())
        stopped = False
        try:
            snapshot(g, BASE_SHA, old_manifest_sha, expected_config)
            stopped = True
            g['_systemctl']('stop')
            g['_switch'](new, old, 'branch-' + new_sha)
            g['_systemctl']('restart')
            g['_wait_active']()
            after = snapshot(g, new_sha, manifest_sha, expected_config)
            probe = g['_probe_tools'](new)
            smoke = library_probe(new)
            result = {**record, 'status': 'upgraded', 'after': after,
                      'fixed_tool_probe': probe, 'library_probe': smoke}
        except Exception as exc:
            failure = type(exc).__name__ + ': ' + str(exc)[:500]
            try:
                if stopped:
                    g['_systemctl']('stop')
                target = os.readlink(source / 'current')
                if target == str(new):
                    g['_switch'](old, new, 'branch-rollback-' + new_sha)
                elif target != str(old):
                    raise RuntimeError('unexpected current link; refusing blind rollback')
                if stopped:
                    g['_systemctl']('restart')
                g['_wait_active']()
                after = snapshot(g, BASE_SHA, old_manifest_sha, expected_config)
                probe = g['_probe_tools'](old)
                result = {**record, 'status': 'rolled_back', 'error': failure,
                          'after': after, 'fixed_tool_probe': probe}
            except Exception as rollback_error:
                result = {**record, 'status': 'rollback_failed', 'error': failure,
                          'rollback_error': type(rollback_error).__name__ + ': ' + str(rollback_error)[:500]}
        g['_new_file'](outcome, (json.dumps(result, indent=2) + '\n').encode())
        return result
    finally:
        os.close(fd)


def run_tests(directory, output, name):
    code = """import sys,unittest,json
sys.path.insert(0,sys.argv[1])
s=unittest.defaultTestLoader.discover(sys.argv[2],pattern='test_*.py')
r=unittest.TextTestRunner(verbosity=2).run(s)
v={'tests':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'skipped':len(r.skipped),'passed':r.wasSuccessful() and not r.skipped}
print('MERLIN_TEST_RESULT='+json.dumps(v,sort_keys=True))
sys.exit(0 if v['passed'] else 1)
"""
    result = subprocess.run(['/usr/bin/python3', '-I', '-B', '-c', code,
        str(directory / 'python'), str(directory / 'tests')], cwd=str(directory),
        env={**SAFE_ENV, 'PYTHONPATH': str(directory / 'python'), 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1'}, capture_output=True, text=True, timeout=180)
    (output / (name + '.txt')).write_text(result.stdout + result.stderr)
    lines = [line for line in result.stdout.splitlines() if line.startswith('MERLIN_TEST_RESULT=')]
    if result.returncode or not lines:
        raise RuntimeError(name + ' failed: ' + result.stderr[-3000:])
    return json.loads(lines[-1].split('=', 1)[1])


def run(request, api, fetch, sources, output):
    def blob(identifier, expected):
        obj = api('git/blobs/' + identifier)
        raw = base64.b64decode(''.join(obj['content'].split()), validate=True)
        if obj.get('sha') != identifier or git_blob(raw) != identifier or sha(raw) != expected:
            raise RuntimeError('pinned blob mismatch')
        return raw
    installer = {}; exec(compile(sources['installer'], 'pinned-installer', 'exec'), installer)
    raw, manifest, old_manifest_sha = assemble(blob(BASE_BLOB, BASE_SHA), blob(SLICE_BLOB, SLICE_SHA), installer['unpack_verified'], output)
    new_sha = sha(raw)
    report = {'schema': 'merlin-dot-operation-receipt/1', 'operation': request['operation'],
        'request_id': request['request_id'], 'bundle_git_blob': git_blob(raw),
        'bundle_git_blob_storage': 'derived content identity; archive retained in validation artifact',
        'bundle_sha256': new_sha, 'source_files': manifest['files'],
        'runner': os.environ['RUNNER_NAME'], 'run_id': os.environ['GITHUB_RUN_ID'],
        'workflow_commit': os.environ['GITHUB_SHA'], 'qualification': False,
        'promotion_authority': False, 'host_configuration_changed': False,
        'expert_source_commit': EXPERT_COMMIT, 'additions': ADDITIONS,
        'python': sys.version, 'authority_change': False, 'scope': 'additive library, not new remote tools'}
    def root(expression):
        code = 'import hashlib,json; namespaces={}\n'
        for name in ('installer', 'guards', 'controller'):
            body = sources[name]
            code += 's=' + repr(body) + ';assert hashlib.sha256(s).hexdigest()==' + repr(sha(body)) + ';n={};exec(compile(s,' + repr('pinned-' + name) + ',"exec"),n);namespaces[' + repr(name) + ']=n\n'
        code += "g=namespaces['guards'];m=namespaces['controller'];i=namespaces['installer'];print(json.dumps(" + expression + '))'
        if len(code.encode()) > 110000:
            raise RuntimeError('root bootstrap size limit')
        result = subprocess.run(['/usr/bin/sudo', '-n', '/usr/bin/python3', '-I', '-B', '-c', code],
            cwd='/', env=SAFE_ENV, capture_output=True, text=True, timeout=180)
        (output / 'root-log.txt').write_text(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError('fixed root operation failed: ' + result.stderr[-3000:])
        return json.loads(result.stdout)
    if request['operation'] == 'inspect':
        report['inspection'] = root("{'snapshot':m['snapshot'](g," + repr(new_sha) + ',' + repr(sha((output / 'candidate/manifest.json').read_bytes())) + "),'tools':g['_probe_tools'](g['SOURCE']/'releases'/" + repr(new_sha) + "),'library':m['library_probe'](g['SOURCE']/'releases'/" + repr(new_sha) + ')}')
    else:
        baseline = run_tests(output / 'baseline', output, 'baseline-tests')
        candidate = run_tests(output / 'candidate', output, 'candidate-tests')
        if baseline['tests'] < 110 or candidate['tests'] != baseline['tests'] + 21:
            raise RuntimeError('expected baseline plus 21 focused tests required')
        report['baseline_tests'] = baseline
        report['tests'] = candidate
        report['preflight'] = root("m['snapshot'](g," + repr(BASE_SHA) + ',' + repr(old_manifest_sha) + ')')
        if request['operation'] == 'deploy':
            evidence = {}; exec(compile(sources['evidence'], 'pinned-evidence', 'exec'), evidence)
            report['prior_validation'] = evidence['check_validation'](request, api, git_blob(raw), new_sha, manifest['files'], candidate['tests'])
            prior = report['prior_validation']
            listing = api('actions/artifacts/' + str(prior['artifact_id']))
            archive = evidence['_download'](prior['artifact_id'], listing['size_in_bytes'])
            if 'sha256:' + sha(archive) != prior['archive_digest']:
                raise RuntimeError('prior archive changed')
            with zipfile.ZipFile(io.BytesIO(archive)) as handle:
                receipt_raw = handle.read('operation-receipt.json')
            if sha(receipt_raw) != prior['receipt_sha256']:
                raise RuntimeError('prior receipt changed')
            previous = json.loads(receipt_raw)
            if previous['preflight'] != report['preflight']:
                raise RuntimeError('live profile changed since validation')
            report['deployment'] = root("m['activate'](g,i['unpack_verified']," + repr(str(output / 'runtime.zip')) + ',' + repr(new_sha) + ',' + repr(old_manifest_sha) + ',' + repr(report['preflight']['config_sha256']) + ')')
            report['host_configuration_changed'] = report['deployment']['status'] == 'upgraded'
            if report['deployment']['status'] != 'upgraded':
                report['status'] = report['deployment']['status']
                (output / 'operation-receipt.json').write_text(json.dumps(report, indent=2))
                raise RuntimeError('release activation did not succeed')
    report['status'] = 'succeeded'
    (output / 'operation-receipt.json').write_text(json.dumps(report, sort_keys=True, indent=2))
    print(json.dumps({k:v for k,v in report.items() if k != 'source_files'}, indent=2))
    return report
