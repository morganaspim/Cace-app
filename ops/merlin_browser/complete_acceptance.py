"""One exact-predecessor browser accounting recovery and acceptance operation.

Recover the retained arXiv acquisition under a separate operator-derived
identity, replace only the renderer producer and its tests, and spend at most
the two previously unsubmitted NASA/GitHub attempts. No installer, fixture
replay, arXiv submission, provider call, policy relaxation or automatic retry.
"""
import datetime
import fcntl
import os
from pathlib import Path
import platform
import pwd
import re
import shutil
import stat
import sys
import time
import uuid

import bootstrap_browser as B
import activate_browser as A
import finish_runtime as F
import recover_capture as R

OPERATION = 'complete-ledger-44946846703'
OLD_REQUEST = '18106dfc-0a56-4b68-9d30-5d334d7d6a69'
OLD_RUN = 44946846703
OLD_COMMIT = 'c8b61b30dfff6c1e3c7889595276d27adca7b5be'
OLD_INTENT = '9249a6aba693a59377defe4d7569fcebe4975fd4e9fe5ed94ccf7f24649f4155'
OLD_RESULT = 'a853ee9d9c43ebb3619250a4242328f60eb344c4791c78aceafa9bbcd9efb8f3'
OLD_LINEAGE = 'b24f041a9d311568bea5ab699bb6cd335f173c05a5f042b05303ed918efc318d'
OLD_PARTIAL = '48b310a4f0433a33dc4d7b1bc76e6f6786f1aa27b405b448f8d86ee81587676d'
OLD_FAILURE = 'f1c4bf5a5b5ef0e44de8328c0de78821ce05d653010cf3fbe7937b9a9719fe9c'
PRODUCT_COMMIT = '74bd09166f338172f4af3854a124c12b5b07081a'
NEW_RUNTIME = 'ebdca90a42bbb243ac04872bdf3f1210ea20583cce9b4c34c7867af1873cb959'
NEW_MANIFEST = '803a4563649df4afd8462c2528029e28432cde8cdfc1853d958c2dda2fe597a9'
NEW_PIN = {'bytes': 68872, 'sha256': NEW_RUNTIME,
           'git_blob': '0d1493e05a6710b8445bfb5fa453b372b86650c4',
           'expert_source_commit': '8e2f1d69371d5b4f7e01e3bbd5aa02a666ddd506'}
DERIVED_MANIFEST = '3cf87ae0920c1b30726cfda2ffad0f1acfbca2be6503b81dfcc2910ba80f0206'
DERIVED_PROVENANCE = '83add070bb91fc35f896626d7a3633f04dd3ad9471a0974d7ddc27de158a0add'
ARXIV_TEXT = '44cf16dd8d053ffb21659ed38cd5bfbd97359a58860c70ab70dd7b5461dc114d'
REMAINING_CASES = (
    ('news-nasa', 'https://www.nasa.gov/news/all-news/', ('NASA', 'News')),
    ('repository-openmdao', 'https://github.com/OpenMDAO/OpenMDAO', ('OpenMDAO',)),
)
EXPECTED_PRIOR_EPISODES = frozenset((
    'bootstrap-fixture-04d38719-4c94-4059-988b-9081375fd209',
    'bootstrap-fixture-4e9b1d59-f966-44ed-a2c1-329aa77aa22e',
    R.SOURCE_EPISODE,
))
CHANGED_PAYLOADS = {
    'python/merlin/public_browser.py': '9bddbc4343b5c6acb88c9d5b12f869290056f1913b93a2203774129d8975e884',
    'python/tests/test_public_browser.py': '4e3c7fb0a708dd838d2305a4e185bd3e3d508f0ee4780e4bf848a5644642d269',
}


def require(value, message):
    if not value:
        raise B.BootstrapError(message)


def existing_root(path):
    """Read-only parent check; unlike a directory creator, never repairs state."""
    path = Path(path)
    require(path.is_absolute() and '..' not in path.parts, 'fixed absolute root path required')
    for item in reversed([path] + list(path.parents)):
        info = item.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022,
                'existing root-owned directory required')
    return path


def checked_raw(path, expected, maximum=4 * 1024 * 1024):
    path = Path(path)
    existing_root(path.parent)
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and info.st_nlink == 1
            and not info.st_mode & 0o022, 'immutable root-owned retained input required')
    raw = B.regular(path, maximum)
    require(B.digest(raw) == expected, 'retained input identity differs: ' + str(path))
    return raw


def validate_request(request, execution):
    require(isinstance(request, dict)
            and set(request) == {'schema', 'request_id', 'operation', 'created_at'},
            'fixed continuation request fields required')
    require(request['schema'] == 'merlin-browser-runtime-request/1'
            and request['operation'] == OPERATION, 'exact ledger continuation required')
    try:
        valid_id = (isinstance(request['request_id'], str)
                    and str(uuid.UUID(request['request_id'])) == request['request_id'])
        stamp = datetime.datetime.strptime(request['created_at'], '%Y-%m-%dT%H:%M:%SZ')
        valid_date = stamp.strftime('%Y-%m-%dT%H:%M:%SZ') == request['created_at']
    except (ValueError, TypeError, AttributeError):
        valid_id = valid_date = False
    require(valid_id and valid_date and request['request_id'] not in
            (OLD_REQUEST, A.OLD_REQUEST, F.OLD_REQUEST), 'new UUID and canonical UTC timestamp required')
    require(isinstance(execution, dict)
            and execution.get('repository') == 'morganaspim/Cace-app'
            and execution.get('ref') == 'refs/heads/merlin/browser-operations-20261121'
            and execution.get('runner') == 'cace-oci-a1'
            and type(execution.get('run_attempt')) is int and execution['run_attempt'] == 1
            and type(execution.get('run_id')) is int and execution['run_id'] > OLD_RUN
            and isinstance(execution.get('workflow_commit'), str)
            and re.fullmatch('[0-9a-f]{40}', execution['workflow_commit']),
            'fixed first native continuation execution required')


def prior_receipt(raw, partial_raw):
    require(B.digest(raw) == OLD_RESULT and B.digest(partial_raw) == OLD_PARTIAL,
            'exact failed activation and partial native acceptance required')
    prior = B.decode(raw)
    partial = B.decode(partial_raw)
    rollback = prior.get('rollback', {})
    require(prior.get('schema') == 'merlin-browser-bootstrap/1'
            and prior.get('status') == 'failed'
            and prior.get('request', {}).get('request_id') == OLD_REQUEST
            and prior.get('execution', {}).get('run_id') == OLD_RUN
            and prior.get('execution', {}).get('workflow_commit') == OLD_COMMIT
            and prior.get('runtime_pin', {}).get('sha256') == A.RUNTIME
            and prior.get('error') == {'type': 'BootstrapError',
                                       'message': 'actual caller episode failed; see preserved native evidence'}
            and prior.get('before') == prior.get('after_failure')
            and prior.get('native_acceptance') is None
            and prior.get('model_calls') == 0 and prior.get('system_package_mutations') == 0
            and prior.get('python_package_installs') == 0
            and prior.get('public_worker_shutdown', {}).get('all_stopped') is True
            and prior.get('fixture', {}).get('status') == 'succeeded'
            and prior.get('fixture_reused') is True
            and prior.get('package_failure_observation') == {
                'count': 971, 'equals_retained_before': True, 'sha256': A.INVENTORY,
                'system_package_mutations_requested': 0}
            and rollback.get('host', {}).get('restored_sha256') == A.OLD_HOST
            and rollback.get('unit', {}).get('restored_sha256') == A.OLD_UNIT
            and rollback.get('automatic_retry') is False,
            'ambiguous predecessor cannot enter accounting continuation')
    properties = prior.get('supervisor_final', {}).get('properties', {})
    A.require_inactive(properties)
    require(properties.get('UnitFileState') == 'disabled', 'predecessor supervisor must be disabled')
    cases = partial.get('public_cases')
    require(partial.get('schema') == 'merlin-browser-native-acceptance/1'
            and partial.get('status') == 'started'
            and partial.get('caller_uid') == 982 and partial.get('caller_gid') == 1000
            and partial.get('model_calls') == 0
            and isinstance(cases, list) and len(cases) == 1
            and cases[0].get('id') == 'database-arxiv'
            and cases[0].get('episode_id') == R.SOURCE_EPISODE
            and cases[0].get('url') == 'https://arxiv.org/abs/1706.03762'
            and cases[0].get('submit_status') == 'failed'
            and cases[0].get('failure_ref', {}).get('sha256') == OLD_FAILURE,
            'only the exact single prior public attempt may be recovered')
    return prior


def validate_episode_budget(names):
    require(len(names) == len(set(names)) and set(names) == EXPECTED_PRIOR_EPISODES,
            'unexpected or missing prior episode requires budget reconciliation')
    return {'maximum_attempts': 5, 'prior_fixture_attempts': 2, 'prior_public_attempts': 1,
            'retained_arxiv_recovered_without_acquisition': True, 'planned_fixture_attempts': 0,
            'remaining_public_attempts': 2, 'attempts_started': [], 'model_calls': 0}


def validate_runtime_delta(old, new):
    before = {row['path']: row for row in old['files']}
    after = {row['path']: row for row in new['files']}
    require(len(before) == len(after) == 14 and set(before) == set(after),
            'exact fourteen-member runtime closure required')
    changed = {name for name in before if before[name] != after[name]}
    require(changed == set(CHANGED_PAYLOADS), 'only renderer producer and tests may change')
    for name, digest in CHANGED_PAYLOADS.items():
        row = after[name]
        require(row['sha256'] == digest
                and row.get('origin', {}).get('repository') == 'Mannyspiro/expert-robot'
                and row.get('origin', {}).get('commit') == PRODUCT_COMMIT,
                'published product successor pin differs')
    require(new.get('derivation') == {
        'kind': 'resource-accounting-producer-and-regression-successor',
        'parent_runtime_sha256': A.RUNTIME, 'parent_manifest_sha256': A.MANIFEST,
        'successor_product_commit': PRODUCT_COMMIT,
        'changed_payloads': sorted(CHANGED_PAYLOADS)}, 'explicit runtime derivation required')
    return {'changed_payloads': sorted(changed), 'unchanged_payload_count': 12,
            'producer_product_commit': PRODUCT_COMMIT}


def new_active_state(old_host, old_unit):
    require(B.digest(old_host) == A.OLD_HOST, 'previous host configuration differs')
    release = B.PREFIX / 'releases' / NEW_RUNTIME
    host = B.decode(old_host)
    host.update(release=str(release), runtime_manifest_sha256=NEW_MANIFEST)
    repaired = A.repaired_unit(old_unit)
    old_path = str(A.RELEASE).encode()
    require(repaired.count(old_path) == 2, 'exact two supervisor runtime paths required')
    unit = repaired.replace(old_path, str(release).encode())
    return B.canonical(host), unit


def verify_launch(launch, episode):
    require(launch.get('status') == 'succeeded' and launch.get('episode_id') == episode
            and launch.get('all_workers_stopped') is True and launch.get('scratch_unmounted') is True,
            'native worker completion and shutdown gate failed')
    for role, network, memory in (('broker', 'no', '134217728'),
                                  ('renderer', 'yes', '1073741824')):
        samples = launch.get('live_unit_samples', {}).get(role, [])
        require(isinstance(samples, list) and samples, 'actual live worker profile missing')
        for sample in samples:
            cpu = sample.get('cpu.max', '').split()
            require(sample.get('User') == '980' and sample.get('PrivateNetwork') == network
                    and sample.get('NoNewPrivileges') == 'yes'
                    and sample.get('MemoryMax') == memory and sample.get('MemorySwapMax') == '0'
                    and sample.get('KillMode') == 'control-group'
                    and len(cpu) == 2 and all(value.isdigit() for value in cpu)
                    and int(cpu[1]) > 0 and int(cpu[0]) / int(cpu[1]) == (.25 if role == 'broker' else 1)
                    and sample.get('memory.max', '').strip() == memory
                    and sample.get('memory.swap.max', '').strip() == '0'
                    and sample.get('pids.max', '').strip() == '128',
                    'observed worker isolation or resource profile differs')


def verify_read(readback, expected, *, exact_text_sha=None):
    text = readback.get('content', '')
    require(readback.get('kind') == 'text' and readback.get('encoding') == 'utf-8'
            and isinstance(text, str) and len(text.encode()) >= 100
            and all(word.lower() in text.lower() for word in expected)
            and type(readback.get('document_status')) is int
            and 200 <= readback['document_status'] < 300
            and readback.get('model_calls') == 0 and readback.get('qualification') is False,
            'public source text/status acceptance failed')
    if exact_text_sha is not None:
        require(B.digest(text.encode()) == exact_text_sha
                and readback.get('artifact_ref', {}).get('sha256') == exact_text_sha,
                'recovered original rendered text differs')
    return readback


def invoke_native(release, value, logs, name, uid=982):
    code = ("import json,os,sys,time\nsys.path.insert(0," + repr(str(release / 'python')) + ")\n"
            "from merlin.browser_client import request_browser\n"
            "v=json.loads(" + repr(B.canonical(value).decode()) + ")\n"
            "deadline=time.monotonic()+8\nattempts=0\nwhile True:\n"
            " attempts+=1\n try:\n  response=request_browser(v)\n  break\n"
            " except (FileNotFoundError,ConnectionRefusedError):\n"
            "  if time.monotonic()>=deadline: raise\n  time.sleep(.1)\n"
            "print(json.dumps({'caller_uid':os.getuid(),'caller_gid':os.getgid(),"
            "'connection_attempts':attempts,'response':response},sort_keys=True))")
    raw = B.command([str(release / 'venv/bin/python'), '-I', '-B', '-c', code],
                    logs / name, timeout=82, limit=2 * 1024 * 1024, user=uid, group=1000)
    answer = B.decode(raw)
    require(answer.get('caller_uid') == uid and answer.get('caller_gid') == 1000,
            'actual caller kernel identity differs')
    return answer['response']


def wait_socket():
    deadline = time.monotonic() + 8
    while not Path('/run/merlin-public-browser/browser.sock').is_socket():
        require(time.monotonic() < deadline, 'browser supervisor readiness deadline')
        time.sleep(.1)


def observe_workers(request_id, logs, label):
    result = {'all_stopped': True, 'units': {}}
    for prefix, _, _ in B.PUBLIC_CASES:
        for role in ('broker', 'renderer'):
            unit = 'merlin-browser-' + role + '-' + prefix + '-' + request_id + '.service'
            try:
                raw = B.command(['/usr/bin/systemctl', 'show', unit, '--no-pager',
                                 '--property=MainPID', '--property=ActiveState', '--property=ControlGroup'],
                                logs / (label + '-' + unit + '.txt'), timeout=3, limit=8192)
                observed = dict(line.split('=', 1) for line in raw.decode().splitlines() if '=' in line)
                result['units'][unit] = observed
                A.require_inactive(observed)
            except BaseException as error:
                result['all_stopped'] = False
                result['units'].setdefault(unit, {})['observation_error'] = type(error).__name__
    return result


def read_request(publication):
    require(publication.get('status') == 'completed'
            and publication.get('qualification') is False
            and publication.get('promotion_authority') is False
            and publication.get('model_calls') == 0,
            'completed context-only publication required')
    sources = publication.get('sources')
    require(isinstance(sources, list) and len(sources) == 1,
            'single captured source required for fixed acceptance')
    return {'schema': 'merlin-browser-request-api/1', 'operation': 'read',
            'episode_id': publication['episode_id'], 'observation_id': sources[0]['observation_id'],
            'kind': 'text', 'start_byte': 0, 'length_bytes': 16384, 'link_start': 0, 'link_limit': 20}


def native_acceptance(release, request_id, logs, recovery, result, budget):
    """Read recovered arXiv first, submit exactly the remaining two, reread all."""
    require(tuple(case[0] for case in REMAINING_CASES) == ('news-nasa', 'repository-openmdao')
            and budget['remaining_public_attempts'] == 2 and budget['attempts_started'] == [],
            'two untouched fixed acceptance attempts required')
    base = {'schema': 'merlin-browser-request-api/1'}
    wait_socket()
    ready = {**base, 'operation': 'status', 'episode_id': 'readiness-' + request_id}
    require(invoke_native(release, ready, logs, 'caller-readiness.txt').get('status') == 'not_found',
            'actual Merlin status route failed')
    denied = invoke_native(release, ready, logs, 'unauthorized-peer.txt', uid=1000)
    require(denied.get('status') == 'denied', 'unauthorized runner peer was not denied')
    result['unauthorized_peer'] = {'uid': 1000, 'status': 'denied'}
    retained = invoke_native(release, {**base, 'operation': 'status', 'episode_id': R.DERIVED_EPISODE},
                             logs, 'recovered-arxiv-status.txt')
    require(retained.get('status') == 'completed' and retained.get('publication') == recovery['publication'],
            'actual caller did not observe the recovered canonical publication')
    read = read_request(recovery['publication'])
    reread = verify_read(invoke_native(release, read, logs, 'recovered-arxiv-read.txt'),
                        ('Attention Is All You Need',), exact_text_sha=ARXIV_TEXT)
    result['recovered_arxiv'] = {
        'episode_id': R.DERIVED_EPISODE, 'source_episode_id': R.SOURCE_EPISODE,
        'derivation_kind': 'operator_reconstructed_resource_accounting',
        'new_browser_execution': False, 'network_reacquired': False,
        'artifact_ref': reread['artifact_ref'], 'acceptance': True,
    }
    repeats = [(read, reread)]
    for name, url, expected in REMAINING_CASES:
        episode = name + '-' + request_id
        require(len(budget['attempts_started']) < 2, 'remaining public attempt ceiling')
        intent = {'case': name, 'episode_id': episode, 'url': url, 'attempt': 1,
                  'automatic_retry': False, 'model_calls': 0}
        # Persist reservation before submission. A lost response never invites
        # a resubmit; it remains consumed/unknown until separately reconciled.
        B.write(logs / (name + '-attempt-intent.json'), B.canonical(intent))
        budget['attempts_started'].append(intent)
        case = {'id': name, 'episode_id': episode, 'url': url, 'submit_started': True,
                'new_browser_execution': True, 'acceptance': False}
        result['public_cases'].append(case)
        submitted = invoke_native(release, {**base, 'operation': 'submit', 'episode_id': episode,
                                  'actions': [{'action': 'open', 'url': url}]}, logs, name + '-submit.txt')
        case.update(submit_status=submitted.get('status'), failure_ref=submitted.get('failure_ref'))
        require(submitted.get('status') == 'completed', 'actual caller episode failed; preserve and stop')
        launch_raw = B.regular(B.STATE / 'episodes' / episode / 'launch-receipt.json', 2 * 1024 * 1024)
        verify_launch(B.decode(launch_raw), episode)
        publication = submitted.get('publication', {})
        require(publication.get('episode_id') == episode, 'submitted publication identity differs')
        read = read_request(publication)
        reread = verify_read(invoke_native(release, read, logs, name + '-read.txt'), expected)
        case.update(acceptance=True, publication=publication, artifact_ref=reread['artifact_ref'],
                    capture_event_ref=reread['capture_event_ref'], title=reread['title'],
                    text_bytes=reread['total_bytes'], document_status=reread['document_status'],
                    launch_receipt_sha256=B.digest(launch_raw))
        repeats.append((read, reread))
    B.command(['/usr/bin/systemctl', 'restart', B.SERVICE], logs / 'supervisor-restart.txt', timeout=10)
    wait_socket()
    result['post_restart_reads'] = []
    for ordinal, (read, expected) in enumerate(repeats, 1):
        observed = invoke_native(release, read, logs, 'post-restart-read-%d.txt' % ordinal)
        require(observed == expected, 'canonical retained read changed across supervisor restart')
        result['post_restart_reads'].append({'episode_id': read['episode_id'], 'unchanged': True,
                                            'new_acquisition': False, 'artifact_ref': observed['artifact_ref']})
    require(len(result['public_cases']) == 2 and len(result['post_restart_reads']) == 3,
            'complete fixed native acceptance required')
    result['status'] = 'passed'
    return result


def preflight(prior, execution, logs, since):
    result = {'phase': 'read-first', 'source_run_id': OLD_RUN, 'runtime_mutations': 0,
              'public_submissions': 0, 'model_calls': 0}
    result['controller_envelope'] = B.controller_envelope(execution, logs)
    result['before'] = B.snapshot(logs, 'before')
    require(result['before'] == prior['before'], 'existing private/model state differs from inspected predecessor')
    before = B.installed(logs / 'rpm-before.txt')
    require(len(before) == 971 and B.digest(B.canonical(before)) == A.INVENTORY,
            'retained installed package state differs')
    result['installed_packages_before_sha256'] = A.INVENTORY
    result['daemon_before'] = B.daemon_absence(logs, 'before', True)
    account = pwd.getpwnam('merlin-browser')
    require((account.pw_uid, account.pw_gid, account.pw_dir, account.pw_shell)
            == (980, 980, '/var/empty', '/sbin/nologin'), 'retained browser account differs')
    result['supervisor_before'] = A.observe_supervisor(logs, 'before', since)
    properties = result['supervisor_before'].get('properties', {})
    A.require_inactive(properties)
    require(properties.get('UnitFileState') == 'disabled', 'retained supervisor enable state differs')
    result['prior_worker_shutdown'] = observe_workers(OLD_REQUEST, logs, 'prior-workers')
    require(result['prior_worker_shutdown']['all_stopped'], 'prior workers are not all stopped')
    episodes = existing_root(B.STATE / 'episodes')
    names = []
    for path in episodes.iterdir():
        require(len(names) < 16 and stat.S_ISDIR(path.lstat().st_mode), 'bounded prior episode directories required')
        existing_root(path)
        names.append(path.name)
    result['acceptance_budget'] = validate_episode_budget(names)
    # All manifest and venv parent directories must already exist before the
    # frozen verifier is called; a missing tree is not repaired by preflight.
    old_manifest = B.decode(checked_raw(A.RELEASE / 'manifest.json', A.MANIFEST, 1048576))
    for row in old_manifest['files']:
        checked_raw(A.RELEASE / row['path'], row['sha256'], 2 * 1024 * 1024)
    venv_ledger = B.decode(checked_raw(B.BOOTSTRAP_STATE / A.OLD_REQUEST / 'venv-copy-ledger.json', A.VENV_LEDGER))
    for row in venv_ledger.get('files', venv_ledger.get('entries', [])):
        existing_root((A.RELEASE / 'venv' / row['path']).parent)
    result['reused_runtime'] = A.verify_runtime(B.BOOTSTRAP_STATE / A.OLD_REQUEST, prior, logs)
    result['fixture'], result['fixture_observation'] = A.verify_fixture(prior)
    launch = B.decode(checked_raw(B.STATE / 'episodes' / R.SOURCE_EPISODE / 'launch-receipt.json', R.SOURCE_LAUNCH))
    verify_launch(launch, R.SOURCE_EPISODE)
    checked = R.inspect_original(B.STATE / 'episodes' / R.SOURCE_EPISODE / 'result')
    derived = R.derive_bytes(checked)
    require(derived['manifest_sha256'] == DERIVED_MANIFEST
            and derived['provenance_sha256'] == DERIVED_PROVENANCE,
            'reviewed retained-capture derivative differs')
    result['retained_arxiv'] = {'manifest_sha256': R.SOURCE_MANIFEST, 'launch_receipt_sha256': R.SOURCE_LAUNCH,
                               'files': 42, 'bytes': launch['output']['bytes'], 'requests': 31,
                               'response_body_bytes': 738314, 'derivation_verified_in_memory': True}
    require(shutil.disk_usage(B.PREFIX).free >= 768 * 1024 * 1024,
            'insufficient space to copy the existing immutable venv and preserve evidence')
    result['status'] = 'passed'
    return result, old_manifest, checked


def publish_recovery(checked, logs):
    """Use the unchanged strict importer; never overwrite the rejected episode."""
    sys.path.insert(0, str(A.RELEASE / 'python'))
    from merlin.browser_ingest import validate_episode, publish_episode
    from merlin.browser_policy import BrowserPolicyError
    from merlin.project_registry import MerlinRegistry
    original = B.STATE / 'episodes' / R.SOURCE_EPISODE / 'result'
    try:
        validate_episode(original)
    except BrowserPolicyError as error:
        require(str(error) == 'resource byte ledger differs', 'original failure differs from inspected defect')
    else:
        raise B.BootstrapError('original invalid ledger unexpectedly passed strict validation')
    registry_path = existing_root(B.STATE / 'registry')
    registry = MerlinRegistry(registry_path)
    project = 'merlin-browser-research'
    failure = registry.artifact_ref(project, 'browser/episodes/' + R.SOURCE_EPISODE + '/execution-failure.json')
    require(failure['sha256'] == OLD_FAILURE, 'canonical original failure identity differs')
    require(B.digest(registry.read_artifact_ref(failure, max_bytes=65536)['content']) == OLD_FAILURE,
            'canonical original failure bytes differ')
    derived_root = B.STATE / 'episodes' / R.DERIVED_EPISODE
    derived_root.mkdir(mode=0o700, exist_ok=False)
    derived = R.write_derived(checked, derived_root / 'result')
    require(derived['manifest_sha256'] == DERIVED_MANIFEST
            and derived['provenance_sha256'] == DERIVED_PROVENANCE,
            'written derivative differs from reviewed accounting')
    validate_episode(derived_root / 'result')
    publication = publish_episode(derived_root / 'result', registry, project_id=project)
    require(publication['episode_id'] == R.DERIVED_EPISODE
            and publication['manifest_sha256'] == DERIVED_MANIFEST, 'canonical derivative identity differs')
    after = R.inspect_original(original)
    require(after['manifest_bytes'] == checked['manifest_bytes'] and after['files'] == checked['files'],
            'original retained bytes changed during recovery')
    result = {'schema': 'merlin-browser-native-ledger-recovery/1',
              'source_episode_id': R.SOURCE_EPISODE, 'derived_episode_id': R.DERIVED_EPISODE,
              'source_manifest_sha256': R.SOURCE_MANIFEST, 'derived_manifest_sha256': DERIVED_MANIFEST,
              'provenance_sha256': DERIVED_PROVENANCE, 'publication': publication,
              'original_manifest_still_rejected': True, 'original_bytes_modified': False,
              'new_browser_execution': False, 'network_reacquired': False, 'model_calls': 0,
              'qualification': False, 'promotion_authority': False}
    B.write(logs / 'retained-arxiv-recovery.json', B.canonical(result))
    return result


def rollback_active_state(receipt, release, old_host, old_unit, new_host, new_unit,
                          logs, request_id, since, attempted):
    rollback = {'automatic_retry': False, 'old_release_retained': True,
                'new_release_retained_for_inspection': True, 'original_capture_retained': True,
                'derived_canonical_evidence_retained': True, 'system_package_rollback_needed': False}
    receipt['rollback'] = rollback
    stopped = False
    if attempted['service']:
        try:
            B.command(['/usr/bin/systemctl', 'disable', '--now', B.SERVICE], logs / 'failed-service-stop.txt',
                      timeout=10, allowed=(0, 1, 5))
            stopped_state = A.observe_supervisor(logs, 'after-stop', since)
            receipt['supervisor_after_stop'] = stopped_state
            A.require_inactive(stopped_state.get('properties', {}))
            require(stopped_state.get('properties', {}).get('UnitFileState') == 'disabled',
                    'rollback did not disable browser supervisor')
            stopped = True
        except BaseException as error:
            rollback['stop_error'] = {'type': type(error).__name__, 'message': str(error)[:1000]}
    else:
        # A failed read-first gate must not stop a pre-existing unexpected
        # service or assume it is inactive merely because we did not start it.
        observed = A.observe_supervisor(logs, 'failure-without-start', since)
        receipt['supervisor_without_start'] = observed
        try:
            A.require_inactive(observed.get('properties', {}))
            require(observed.get('properties', {}).get('UnitFileState') == 'disabled',
                    'pre-existing browser supervisor is enabled')
            stopped = True
        except BaseException as error:
            rollback['pre_existing_state_error'] = {'type': type(error).__name__, 'message': str(error)[:1000]}
    workers = observe_workers(request_id, logs, 'rollback-workers')
    receipt['public_worker_shutdown'] = workers
    safe = stopped and workers.get('all_stopped') is True
    if not safe:
        rollback['reconciliation_required'] = 'supervisor or worker shutdown unproved; active pointers preserved'
        return False
    current = B.PREFIX / 'current'
    if attempted['pointer'] and current.is_symlink() and os.readlink(current) == str(release):
        current.unlink()
        rollback['current_removed'] = True
    elif current.exists() or current.is_symlink():
        rollback['reconciliation_required'] = 'unexpected current pointer preserved'
        return False
    for label, touched, target, old, new, temporary, mode in (
        ('host', attempted['host'], B.CONFIG / 'host.json', old_host, new_host,
         B.CONFIG / ('host-restore-' + request_id + '.json'), 0o600),
        ('unit', attempted['unit'], A.UNIT_PATH, old_unit, new_unit,
         A.UNIT_PATH.parent / ('merlin-browser-restore-' + request_id + '.tmp'), 0o644),
    ):
        if touched:
            try:
                rollback[label] = A.restore_after_attempt(target, old, B.digest(new), temporary, mode)
            except BaseException as error:
                rollback[label + '_restore_error'] = {'type': type(error).__name__, 'message': str(error)[:1000]}
    if attempted['unit']:
        try:
            B.command(['/usr/bin/systemctl', 'daemon-reload'], logs / 'restore-daemon-reload.txt', timeout=10)
        except BaseException as error:
            rollback['reload_error'] = type(error).__name__
    return safe


def run(bundle, bundle_pin, request, execution, output):
    require(os.geteuid() == 0 and platform.machine() == 'aarch64' and sys.version_info[:2] == (3, 9),
            'native root accounting continuation required')
    os.umask(0o022)
    validate_request(request, execution)
    require(bundle_pin == NEW_PIN, 'exact published producer successor runtime required')
    require(B.identity(bundle, 1048576) == {'bytes': NEW_PIN['bytes'], 'sha256': NEW_RUNTIME},
            'reviewed runtime archive identity differs')
    parent_fd = B.operation_directory(Path(output))
    leaf_fd = None
    try:
        os.mkdir('root-evidence', mode=0o700, dir_fd=parent_fd)
        leaf_fd = os.open('root-evidence', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
        info = os.fstat(leaf_fd)
        require(info.st_uid == 0 and stat.S_IMODE(info.st_mode) == 0o700 and not os.listdir(leaf_fd),
                'new private root evidence leaf required')
        return run_owned(bundle, request, execution, Path(output), parent_fd, leaf_fd)
    finally:
        if leaf_fd is not None:
            os.fchown(leaf_fd, 1000, 1000)
            os.close(leaf_fd)
        os.close(parent_fd)


def run_owned(bundle, request, execution, output_path, parent_fd, leaf_fd):
    output = Path('/proc/self/fd') / str(leaf_fd)
    state = existing_root(B.BOOTSTRAP_STATE)
    lock = os.open(str(state / 'operation.lock'), os.O_RDWR | os.O_NOFOLLOW, 0o600)
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    staged = state / request['request_id']
    marker = state / ('ledger-successor-from-' + OLD_REQUEST + '.json')
    release = B.PREFIX / 'releases' / NEW_RUNTIME
    for path in (staged, marker, release, B.PREFIX / 'current',
                 Path('/run/merlin-public-browser/browser.sock'),
                 B.STATE / 'episodes' / R.DERIVED_EPISODE):
        require(not path.exists() and not path.is_symlink(),
                'existing continuation or active state requires explicit reconciliation')
    staged.mkdir(mode=0o700)
    logs = staged / 'logs'
    logs.mkdir(mode=0o700)
    receipt = {'schema': 'merlin-browser-ledger-continuation/1', 'request': request, 'execution': execution,
               'status': 'started', 'phase': 'read-first', 'runtime_pin': NEW_PIN,
               'product_source_commit': PRODUCT_COMMIT, 'predecessor_run_id': OLD_RUN,
               'predecessor_result_sha256': OLD_RESULT, 'model_calls': 0, 'external_model_cost_usd': 0,
               'system_package_mutations': 0, 'python_package_installs': 0,
               'runtime_dependency_acquisition': False, 'fixture_replayed': False,
               'arxiv_reacquired': False, 'host_reboot_performed': False,
               'qualification': False, 'promotion_authority': False, 'automatic_retry': False}
    B.write(staged / 'operation-intent.json', B.canonical(receipt))
    attempted = {'host': False, 'unit': False, 'pointer': False, 'service': False}
    safe_export = False
    old_host = old_unit = new_host = new_unit = None
    since = int(time.time()) - 2
    try:
        prior_stage = state / OLD_REQUEST
        prior_raw = checked_raw(prior_stage / 'operation-receipt.json', OLD_RESULT)
        partial_raw = checked_raw(prior_stage / 'logs/native-acceptance-partial.json', OLD_PARTIAL)
        prior = prior_receipt(prior_raw, partial_raw)
        checked_raw(prior_stage / 'bootstrap-result.json', OLD_RESULT)
        intent_raw = checked_raw(prior_stage / 'bootstrap-intent.json', OLD_INTENT)
        lineage_raw = checked_raw(prior_stage / 'successor-lineage.json', OLD_LINEAGE)
        checked_raw(state / ('activation-successor-from-' + A.OLD_REQUEST + '.json'), OLD_LINEAGE)
        checked_raw(state / 'bootstrap-intent.json', B.PREDECESSOR['intent_sha256'])
        checked_raw(state / 'bootstrap-result.json', B.PREDECESSOR['result_sha256'])
        old_host = checked_raw(B.CONFIG / 'host.json', A.OLD_HOST, 65536)
        old_unit = checked_raw(A.UNIT_PATH, A.OLD_UNIT, 65536)
        checked_raw(B.CONFIG / 'service.json', A.SERVICE_CONFIG, 65536)
        new_host, new_unit = new_active_state(old_host, old_unit)
        for name, raw in (('predecessor-intent.json', intent_raw), ('predecessor-result.json', prior_raw),
                          ('predecessor-lineage.json', lineage_raw), ('predecessor-native-partial.json', partial_raw),
                          ('previous-host.json', old_host), ('previous-supervisor.service', old_unit),
                          ('candidate-host.json', new_host), ('candidate-supervisor.service', new_unit)):
            B.write(staged / name, raw)
        observed, old_manifest, checked = preflight(prior, execution, logs, since)
        receipt.update(observed)
        receipt['status'] = 'started'
        B.write(logs / 'read-first-preflight.json', B.canonical(observed))
        # Freeze the single successor only after read-first checks. Any later
        # failure preserves this marker, so another UUID cannot replay work.
        lineage = {'schema': 'merlin-browser-ledger-successor/1', 'prior_run_id': OLD_RUN,
                   'prior_result_sha256': OLD_RESULT, 'successor_request': request, 'execution': execution,
                   'runtime_sha256': NEW_RUNTIME, 'product_source_commit': PRODUCT_COMMIT,
                   'remaining_public_attempts': 2, 'automatic_retry': False}
        B.write(marker, B.canonical(lineage))
        B.write(staged / 'successor-lineage.json', B.canonical(lineage))
        receipt['phase'] = 'retained-arxiv-recovery'
        receipt['recovery'] = publish_recovery(checked, logs)
        receipt['phase'] = 'producer-runtime-copy'
        B.copy_verified(bundle, staged / 'runtime.zip', {'sha256': NEW_RUNTIME, 'bytes': NEW_PIN['bytes']}, 1048576)
        manifest, manifest_sha = B.unpack_runtime(staged / 'runtime.zip', NEW_PIN, release)
        require(manifest_sha == NEW_MANIFEST, 'new runtime manifest differs')
        receipt['runtime_delta'] = validate_runtime_delta(old_manifest, manifest)
        receipt['reused_venv'] = F.clone_venv(A.RELEASE / 'venv', release / 'venv', staged / 'venv-copy-ledger.json')
        old_venv_ledger = B.decode(checked_raw(state / A.OLD_REQUEST / 'venv-copy-ledger.json', A.VENV_LEDGER))
        copied_venv_ledger = B.decode(B.regular(staged / 'venv-copy-ledger.json', 4 * 1024 * 1024))
        require(copied_venv_ledger['source'] == str(A.RELEASE / 'venv')
                and copied_venv_ledger['destination'] == str(release / 'venv')
                and copied_venv_ledger['entries'] == old_venv_ledger['entries'],
                'copied venv member bytes or modes differ from the exact installed ledger')
        # The frozen older copy helper's convenience label named its old
        # source release; bind this operation's label to the verified ledger.
        receipt['reused_venv']['source_release'] = A.RUNTIME
        receipt['reused_venv']['all_installed_member_identities_unchanged'] = True
        require(receipt['reused_venv']['files'] == 1420 and receipt['reused_venv']['bytes'] == 153044541,
                'copied existing venv closure differs')
        code = ('import json;from importlib.metadata import version;print(json.dumps({n:version(n) for n in '
                + repr([p['name'] for p in B.WHEELS]) + '},sort_keys=True))')
        versions = B.decode(B.command([str(release / 'venv/bin/python'), '-I', '-B', '-c', code],
                                      logs / 'reused-wheel-versions.txt', timeout=10, limit=65536))
        require(versions == {p['name']: p['version'] for p in B.WHEELS}, 'reused pinned wheel versions differ')
        receipt['phase'] = 'browser-supervisor-activation'
        attempted['host'] = True
        B.write(staged / 'host-replacement-intent.json', B.canonical({'previous_sha256': A.OLD_HOST,
                                                                  'next_sha256': B.digest(new_host)}))
        A.atomic_replace(B.CONFIG / 'host.json', new_host,
                         B.CONFIG / ('host-ledger-' + request['request_id'] + '.json'), 0o600)
        attempted['unit'] = True
        B.write(staged / 'unit-replacement-intent.json', B.canonical({'previous_sha256': A.OLD_UNIT,
                                                                  'next_sha256': B.digest(new_unit)}))
        A.atomic_replace(A.UNIT_PATH, new_unit,
                         A.UNIT_PATH.parent / ('merlin-browser-ledger-' + request['request_id'] + '.tmp'), 0o644)
        attempted['pointer'] = True
        os.symlink(str(release), B.PREFIX / 'current')
        B.command(['/usr/bin/systemctl', 'daemon-reload'], logs / 'daemon-reload.txt', timeout=10)
        attempted['service'] = True
        B.command(['/usr/bin/systemctl', 'enable', '--now', B.SERVICE], logs / 'service-enable.txt', timeout=20)
        receipt['supervisor_after_start'] = A.observe_supervisor(logs, 'after-start', since)
        receipt['phase'] = 'remaining-public-acceptance'
        native = {'schema': 'merlin-browser-native-ledger-acceptance/1', 'status': 'started',
                  'public_cases': [], 'max_new_public_episodes': 2, 'fixture_episodes_replayed': 0,
                  'arxiv_acquisitions_replayed': 0, 'parallel_episodes': 1, 'model_calls': 0,
                  'caller_uid': 982, 'caller_gid': 1000, 'qualification': False}
        receipt['native_acceptance'] = native
        native_acceptance(release, request['request_id'], logs, receipt['recovery'], native, receipt['acceptance_budget'])
        receipt['supervisor_after_acceptance'] = A.observe_supervisor(logs, 'after-acceptance', since)
        active = receipt['supervisor_after_acceptance'].get('properties', {})
        require(active.get('ActiveState') == 'active' and active.get('UnitFileState') == 'enabled'
                and active.get('MainPID', '').isdigit() and int(active['MainPID']) > 0
                and active.get('User') == 'root' and active.get('Group') == 'root'
                and active.get('UMask') == '0077' and active.get('MemoryMax') == '268435456'
                and active.get('MemorySwapMax') == '0' and active.get('CPUQuotaPerSecUSec') == '250ms'
                and active.get('TasksMax') == '32' and active.get('RuntimeDirectory') == ''
                and active.get('RestrictAddressFamilies') == 'AF_UNIX',
                'actual active supervisor profile differs')
        receipt['public_worker_shutdown'] = observe_workers(request['request_id'], logs, 'accepted-workers')
        require(receipt['public_worker_shutdown']['all_stopped'], 'completed public workers remain active')
        safe_export = True
        receipt['after'] = B.snapshot(logs, 'after')
        require(receipt['after'] == receipt['before'], 'existing private/model state changed')
        packages = B.installed(logs / 'rpm-after.txt')
        require(len(packages) == 971 and B.digest(B.canonical(packages)) == A.INVENTORY,
                'system package state changed')
        receipt['installed_packages_after_sha256'] = A.INVENTORY
        checked_raw(B.CONFIG / 'host.json', B.digest(new_host), 65536)
        checked_raw(A.UNIT_PATH, B.digest(new_unit), 65536)
        checked_raw(B.CONFIG / 'service.json', A.SERVICE_CONFIG, 65536)
        checked_raw(prior_stage / 'operation-receipt.json', OLD_RESULT)
        receipt['daemon_after_acceptance'] = B.daemon_absence(logs, 'after-acceptance', True)
        receipt.update(status='installed_native_passed', phase='completed',
                       host_config_sha256=B.digest(new_host), unit_sha256=B.digest(new_unit),
                       service_config_sha256=A.SERVICE_CONFIG)
    except BaseException as error:
        receipt['status'] = 'failed'
        receipt['error'] = {'type': type(error).__name__, 'message': str(error)[:2000]}
        receipt['supervisor_at_failure'] = A.observe_supervisor(logs, 'at-failure', since)
        safe_export = rollback_active_state(receipt, release, old_host, old_unit, new_host, new_unit,
                                            logs, request['request_id'], since, attempted)
        try:
            packages = B.installed(logs / 'rpm-after-failure.txt')
            receipt['package_failure_observation'] = {
                'count': len(packages), 'sha256': B.digest(B.canonical(packages)),
                'equals_retained_before': B.digest(B.canonical(packages)) == A.INVENTORY,
                'system_package_mutations_requested': 0}
            receipt['after_failure'] = B.snapshot(logs, 'after-failure')
        except BaseException as observation_error:
            receipt['failure_state_observation_error'] = type(observation_error).__name__
    finally:
        receipt['supervisor_final'] = A.observe_supervisor(logs, 'final', since)
        B.write(staged / 'operation-receipt.json', B.canonical(receipt))
        exported = output / 'continuation-evidence'
        exported.mkdir(mode=0o700)
        for parent in (staged, logs):
            for path in sorted(parent.iterdir()):
                if path.is_file() and path.name != 'runtime.zip':
                    B.write(exported / path.name, B.regular(path, 8 * 1024 * 1024))
                    os.chown(exported / path.name, 1000, 1000)
        os.chown(exported, 1000, 1000)
        trees = {}
        episodes = [R.SOURCE_EPISODE, R.DERIVED_EPISODE, 'bootstrap-fixture-' + A.OLD_REQUEST]
        episodes += [case[0] + '-' + request['request_id'] for case in REMAINING_CASES]
        for episode in episodes:
            source = B.STATE / 'episodes' / episode
            trees[episode] = (B.export_tree(source, output / episode) if safe_export else
                              {'exported': False, 'reason': 'shutdown not proved', 'retained_path': str(source)})
        registry = B.STATE / 'registry'
        trees['canonical_registry'] = (B.export_tree(registry, output / 'canonical-browser-registry') if safe_export else
                                       {'exported': False, 'reason': 'shutdown not proved', 'retained_path': str(registry)})
        B.write(output / 'raw-evidence-export.json', B.canonical(trees))
        os.chown(output / 'raw-evidence-export.json', 1000, 1000)
        parent_check = B.operation_directory(output_path)
        leaf_check = B.operation_directory(output_path / 'root-evidence', owner=0)
        try:
            for first, second in ((parent_fd, parent_check), (leaf_fd, leaf_check)):
                left, right = os.fstat(first), os.fstat(second)
                require((left.st_dev, left.st_ino) == (right.st_dev, right.st_ino),
                        'continuation evidence path moved during publication')
        finally:
            os.close(parent_check)
            os.close(leaf_check)
            os.close(lock)
    require(receipt['status'] == 'installed_native_passed', 'ledger continuation failed; raw state and receipt retained')
    return receipt
