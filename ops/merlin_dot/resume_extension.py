# Appended to the exact, separately pinned release_branch.py. This replaces only
# activation with one reconciled resume; package/source identities do not change.
import time

RESUME_SHA = 'd4fa47482b94c8f086b87d2c2e532a64a5874124b31283d834bc9be8350c3365'
PRIOR_RESULT_SHA = 'e87341332fd0f787c164e141e6dc010fb5428e4bc99ac5e51dde3840e6183085'
HEALTH_WAIT = '''def await_health(call, clock, sleep, seconds=10):
    start = clock()
    attempts = 0
    while True:
        attempts += 1
        try:
            reply = call()
        except (FileNotFoundError, ConnectionRefusedError):
            if clock() - start >= seconds:
                raise TimeoutError('private socket did not become ready within budget')
            sleep(min(0.2, max(0, seconds - (clock() - start))))
            continue
        if (reply.get('ok') is not True or reply.get('qualification') is not False
                or reply.get('promotion_authority') is not False
                or reply.get('result', {}).get('transport') != 'unix'
                or reply.get('result', {}).get('public_listener') is not False):
            raise RuntimeError('private health contract failed; no retry')
        return {'attempts': attempts, 'elapsed_seconds': clock() - start}
'''


def error_details(exc):
    result = {'class': type(exc).__name__}
    if isinstance(exc, subprocess.CalledProcessError):
        # Preserve actual failure diagnostics, not a truncated command string.
        result.update(returncode=exc.returncode, stderr=(exc.stderr or '')[-4000:])
    else:
        result['message'] = str(exc)[:1000]
    return result


def ready_probe(g, release):
    code = '''import sys,json,time
sys.path.insert(0,sys.argv[1])
from dot_ai_os.private_runtime import call_socket
''' + HEALTH_WAIT + '''
def call():
 return call_socket('/run/merlin-dot-private/tools.sock', {'schema':'merlin-private-call/1','request_id':'branch-ready-health','tool':'health','arguments':{}},expected_server_uid=982,timeout_seconds=5)
print(json.dumps(await_health(call,time.monotonic,time.sleep)))
'''
    process = subprocess.run(['/usr/bin/python3', '-I', '-B', '-c', code, str(release / 'python')],
        user=1000, group=1000, extra_groups=[], env=SAFE_ENV, cwd='/',
        capture_output=True, text=True, check=True, timeout=20)
    readiness = json.loads(process.stdout)
    # Run the unchanged full probe once after real socket health succeeds.
    return {'readiness': readiness, 'fixed_tools': g['_probe_tools'](release)}


def activate(g, unpack_verified, bundle_path, new_sha, old_manifest_sha, expected_config):
    if new_sha != RESUME_SHA:
        raise ValueError('only the previously attempted exact release can resume')
    source = g['SOURCE']; old = source / 'releases' / BASE_SHA; new = source / 'releases' / new_sha
    history = g['CONFIG'].parent / 'upgrade-history'
    for directory in (source, source / 'releases', g['CONFIG'].parent, history):
        g['_root_directory'](directory)
    fd = os.open(source / '.research-upgrade.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077:
            raise RuntimeError('unsafe upgrade lock')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        before = snapshot(g, BASE_SHA, old_manifest_sha, expected_config)
        prior_raw = g['_regular'](history / ('branch-result-' + new_sha + '.json'), expected=PRIOR_RESULT_SHA, maximum=16000)
        prior = json.loads(prior_raw)
        if (prior.get('status') != 'rollback_failed' or prior.get('new_bundle_sha256') != new_sha
                or prior.get('expert_source_commit') != EXPERT_COMMIT or prior.get('additions') != ADDITIONS
                or prior.get('old', {}).get('config_sha256') != expected_config
                or prior.get('old', {}).get('release_sha256') != BASE_SHA):
            raise RuntimeError('prior attempt does not match reconciled rollback')
        old_manifest = json.loads(g['_regular'](old / 'manifest.json', expected=old_manifest_sha))
        raw = g['_regular'](Path(bundle_path), root_owned=False, expected=new_sha, maximum=13 * 1024 * 1024)
        with tempfile.TemporaryDirectory(prefix='merlin-resume-verify-') as temp:
            checked = Path(temp) / 'release'; manifest = unpack_verified(raw, new_sha, checked)
            verify_additive(old_manifest['files'], manifest['files'])
            if {k:v for k,v in manifest.items() if k != 'files'} != {k:v for k,v in old_manifest.items() if k != 'files'}:
                raise RuntimeError('canonical base changed')
            manifest_sha = sha((checked / 'manifest.json').read_bytes())
        # Reuse only the already root-owned, byte-verified release. No deletion,
        # overwrite, permission relaxation or fake new package identity.
        g['_verify_release'](new, manifest_sha)
        intent = history / ('branch-resume-intent-' + new_sha + '.json')
        outcome = history / ('branch-resume-result-' + new_sha + '.json')
        if any(p.exists() or p.is_symlink() for p in (intent, outcome)):
            raise RuntimeError('resume already attempted; inspect instead of blind retry')
        original_probe = ready_probe(g, old)
        library_probe(new)
        record = {'schema':'merlin-additive-library-resume/1','old':before,
            'parent_result_sha256':PRIOR_RESULT_SHA,'new_bundle_sha256':new_sha,
            'expert_source_commit':EXPERT_COMMIT,'additions':ADDITIONS,
            'unit_changed':False,'grants_changed':False,'private_state_edited_by_updater':False,
            'remote_tool_exposed':False,'original_probe':original_probe}
        g['_new_file'](intent, (json.dumps(record, indent=2) + '\n').encode())
        stopped = False
        try:
            snapshot(g, BASE_SHA, old_manifest_sha, expected_config)
            stopped = True; g['_systemctl']('stop')
            g['_switch'](new, old, 'branch-resume-' + new_sha)
            g['_systemctl']('restart'); g['_wait_active']()
            probe = ready_probe(g, new)
            after = snapshot(g, new_sha, manifest_sha, expected_config)
            result = {**record,'status':'upgraded','after':after,'fixed_tool_probe':probe,'library_probe':library_probe(new)}
        except Exception as exc:
            failure = error_details(exc)
            try:
                if stopped: g['_systemctl']('stop')
                target = os.readlink(source / 'current')
                if target == str(new): g['_switch'](old, new, 'branch-resume-rollback-' + new_sha)
                elif target != str(old): raise RuntimeError('unexpected link; refusing blind rollback')
                if stopped: g['_systemctl']('restart')
                g['_wait_active'](); probe = ready_probe(g, old)
                after = snapshot(g, BASE_SHA, old_manifest_sha, expected_config)
                result = {**record,'status':'rolled_back','error':failure,'after':after,'fixed_tool_probe':probe}
            except Exception as rollback_error:
                result = {**record,'status':'rollback_failed','error':failure,'rollback_error':error_details(rollback_error)}
        g['_new_file'](outcome, (json.dumps(result, indent=2) + '\n').encode())
        return result
    finally:
        os.close(fd)
