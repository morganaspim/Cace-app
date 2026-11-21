"""Fixed exact-source OCI validation; generated only after a measured source freeze.

Retains the approved v2 root-owned loader and the existing temporary synthetic
drills. No user-selectable commands, deployment, credentials or grants.
"""
import base64
import hashlib
import io
import json
import lzma
import os
from pathlib import Path
import platform
import subprocess
import sys
import urllib.request
import zipfile
CANDIDATE = {'changed_paths': ['python/dot_ai_os/dual_coder.py', 'python/merlin/build_admission.py', 'python/merlin/build_loop.py', 'python/merlin/weight_binding.py', 'tests/test_build_admission.py', 'tests/test_weight_binding.py'], 'context_cases': ['acknowledgement_loss_after_real_process', 'actual_cancellation_stops_process_and_fences_successor', 'completed_process_checker_recovery_without_relaunch', 'context_restart_actual_worker_process_and_duplicate_replay', 'non_boolean_host_authority_cannot_start_process', 'wrong_output_cannot_pass_or_advance_dependency'], 'kernel_cases': ['aggregate_memory_limit', 'cpu_time_limit', 'detached_descendant_cleanup', 'fixed_program_and_actual_kernel_limits', 'inet_socket_creation_denied', 'manager_wall_deadline', 'revoked_authorization_stops_unit', 'tasks_max_fork_denial'], 'overlay_chunks': [{'bytes': 22398, 'git_blob': 'e4ba19f1703466271ed4a46cba95b268efc0462c', 'position': 0, 'sha256': '1de3d3e484a0c382bd6610f98f4db1c8a3c2cf638d9363a34ee69295f0732377'}, {'bytes': 22399, 'git_blob': 'f9bfa8fdf3d5eeffc4a7a31e770a85ab075d36ea', 'position': 1, 'sha256': '371e88833a225b67aca3ac376e1f433e272afce6c0f73b087688540a4c9bd834'}], 'overlay_encoded_bytes': 44797, 'overlay_encoded_sha256': '4e494eaf41e0435d6337591176fc4a9e6c3f3f18f0c97fe5497f415e7cbdae3e', 'overlay_expanded_bytes': 185732, 'overlay_expanded_sha256': 'aca1f789e033784c9f9d63a9eceb98465572aa2ddcfbbe96caf2c35c0f985fa0', 'overlay_packed_bytes': 33596, 'overlay_packed_sha256': '560b4188bf1f8b86c6a20eaa4ba612192d84f5aaecf892347f3f7b097190b723', 'software_tests': 473, 'source_commit': '01016e832f763c76744e404041355b33d15fb621', 'source_files': 121, 'source_map_sha256': '7dfff2dc84b43b9c3c35e0513c31052307ad71ce79f1211f59736bdfa446afe9', 'test_inventory_sha256': 'a70ce5d187c262cddc1a0c31d363d6be54bcb103cb47eae3b7bea87d7207f348'}
SOFTWARE_RUNNER = '"""Record discovered and actually started unittest IDs for a fixed source shard.\n\nThe controller supplies the verified source and immutable expected selection.\nThis helper grants no runtime authority and does not run kernel drills.\n"""\nimport argparse\nfrom contextlib import nullcontext\nimport hashlib\nimport json\nfrom pathlib import Path\nimport sys\nimport unittest\n\n\ndef canonical(value):\n    return json.dumps(value, sort_keys=True, separators=(\',\', \':\'),\n                      ensure_ascii=False, allow_nan=False).encode()\n\n\ndef digest_ids(ids):\n    if (not isinstance(ids, list) or not 1 <= len(ids) <= 100000\n            or len(ids) != len(set(ids))\n            or any(not isinstance(x, str) or not 0 < len(x) <= 400\n                   or x != x.strip() or any(ord(c) < 32 or ord(c) == 127 for c in x)\n                   for x in ids)):\n        raise ValueError(\'complete distinct bounded test IDs required\')\n    return hashlib.sha256(canonical({\n        \'schema\': \'merlin-executed-software-tests/1\',\n        \'test_ids\': sorted(ids),\n    })).hexdigest()\n\n\ndef check_source(root, manifest_path):\n    manifest = json.loads(Path(manifest_path).read_text())\n    mapping = {}\n    for name, expected in sorted(manifest[\'files\'].items()):\n        p = Path(name)\n        if (p.is_absolute() or \'\\\\\' in name\n                or any(x in (\'\', \'.\', \'..\') for x in name.split(\'/\'))):\n            raise ValueError(\'invalid source path\')\n        raw = (root / p).read_bytes()\n        actual = hashlib.sha256(raw).hexdigest()\n        blob = hashlib.sha1(b\'blob \' + str(len(raw)).encode() + b\'\\0\' + raw).hexdigest()\n        if actual != expected or blob != manifest[\'git_blobs\'][name]:\n            raise ValueError(\'fixed source bytes changed: \' + name)\n        mapping[name] = actual\n    actual = hashlib.sha256(canonical(mapping)).hexdigest()\n    if actual != manifest[\'source_map_sha256\']:\n        raise ValueError(\'source map differs\')\n    return manifest\n\n\ndef collect(root):\n    sys.path[:0] = [str(root / \'python\'), str(root), str(root / \'tests\')]\n    suite = unittest.defaultTestLoader.discover(str(root / \'tests\'), pattern=\'test_*.py\')\n    def flatten(node):\n        if isinstance(node, unittest.TestSuite):\n            for child in node:\n                yield from flatten(child)\n        else:\n            yield node.id()\n    ids = sorted(flatten(suite))\n    return suite, ids\n\n\nclass InventoryResult(unittest.TextTestResult):\n    def __init__(self, *args, progress=None, **kwargs):\n        super().__init__(*args, **kwargs)\n        self.executed_ids = []\n        self.progress = progress\n\n    def event(self, event, test):\n        if self.progress is not None:\n            self.progress.write(json.dumps({\'event\': event, \'test_id\': test.id()}, sort_keys=True) + \'\\n\')\n            self.progress.flush()\n\n    def startTest(self, test):\n        self.executed_ids.append(test.id())\n        self.event(\'start\', test)\n        super().startTest(test)\n\n    def stopTest(self, test):\n        self.event(\'stop\', test)\n        super().stopTest(test)\n\n    def addFailure(self, test, err):\n        self.event(\'failure\', test)\n        super().addFailure(test, err)\n\n    def addError(self, test, err):\n        self.event(\'error\', test)\n        super().addError(test, err)\n\n    def addSkip(self, test, reason):\n        self.event(\'skip\', test)\n        super().addSkip(test, reason)\n\n    def addSubTest(self, test, subtest, err):\n        if err is not None:\n            self.event(\'failure\' if issubclass(err[0], test.failureException) else \'error\', subtest)\n        super().addSubTest(test, subtest, err)\n\n    def addExpectedFailure(self, test, err):\n        self.event(\'expected_failure\', test)\n        super().addExpectedFailure(test, err)\n\n    def addUnexpectedSuccess(self, test):\n        self.event(\'unexpected_success\', test)\n        super().addUnexpectedSuccess(test)\n\n\ndef measure(root, manifest_path, *, execute, expected_count=None, expected_digest=None, progress_path=None):\n    root = Path(root)\n    before = check_source(root, manifest_path)\n    suite, collection = collect(root)\n    collection_digest = digest_ids(collection)\n    report = {\n        \'schema\': \'merlin-software-inventory/1\',\n        \'source_commit\': before.get(\'source_commit\'),\n        \'source_map_sha256\': before[\'source_map_sha256\'],\n        \'collection_ids\': collection,\n        \'collection_sha256\': collection_digest,\n        \'collected_tests\': len(collection),\n        \'qualification\': False,\n        \'promotion_authority\': False,\n    }\n    if not execute:\n        report.update(status=\'collected\', executed=False)\n        return report\n    if (type(expected_count) is not int or len(collection) != expected_count\n            or collection_digest != expected_digest):\n        report.update(status=\'failed\', passed=False, executed=False,\n                      reason=\'frozen discovery selection differs\',\n                      tests=0, executed_test_ids=[], test_inventory_sha256=None,\n                      failures=0, errors=0, skipped=0,\n                      failed_test_ids=[], error_test_ids=[], skipped_test_ids=[])\n        return report\n    with (Path(progress_path).open(\'w\') if progress_path is not None else nullcontext(None)) as journal:\n        factory = lambda *args, **kwargs: InventoryResult(*args, progress=journal, **kwargs)\n        result = unittest.TextTestRunner(verbosity=2, resultclass=factory).run(suite)\n    executed = sorted(result.executed_ids)\n    try:\n        executed_digest = digest_ids(executed)\n    except ValueError:\n        executed_digest = None\n    try:\n        after = check_source(root, manifest_path)\n        source_unchanged = before == after\n    except (ValueError, OSError) as exc:\n        source_unchanged = False\n        report[\'source_check_error\'] = str(exc)[:1500]\n    report.update(\n        tests=result.testsRun, errors=len(result.errors), failures=len(result.failures),\n        skipped=len(result.skipped),\n        expected_failures=len(result.expectedFailures),\n        unexpected_successes=len(result.unexpectedSuccesses),\n        failed_test_ids=sorted(t.id() for t, _ in result.failures),\n        error_test_ids=sorted(t.id() for t, _ in result.errors),\n        skipped_test_ids=sorted(t.id() for t, _ in result.skipped),\n        expected_failure_test_ids=sorted(t.id() for t, _ in result.expectedFailures),\n        unexpected_success_test_ids=sorted(t.id() for t in result.unexpectedSuccesses),\n        executed_test_ids=executed, test_inventory_sha256=executed_digest,\n        source_unchanged=source_unchanged, executed=True,\n    )\n    passed = (result.wasSuccessful() and not result.skipped\n              and not result.expectedFailures and not result.unexpectedSuccesses\n              and result.testsRun == expected_count == len(executed)\n              and len(set(executed)) == len(executed)\n              and executed == collection and executed_digest == expected_digest\n              and source_unchanged)\n    report.update(passed=passed, status=\'succeeded\' if passed else \'failed\')\n    return report\n\n\ndef main():\n    parser = argparse.ArgumentParser()\n    parser.add_argument(\'mode\', choices=(\'collect\', \'run\'))\n    parser.add_argument(\'source\')\n    parser.add_argument(\'manifest\')\n    parser.add_argument(\'output\')\n    parser.add_argument(\'--expected-count\', type=int)\n    parser.add_argument(\'--expected-digest\')\n    args = parser.parse_args()\n    output = Path(args.output)\n    try:\n        report = measure(args.source, args.manifest, execute=args.mode == \'run\',\n                         expected_count=args.expected_count, expected_digest=args.expected_digest,\n                         progress_path=output.with_suffix(\'.events.txt\'))\n    except Exception as exc:\n        report = {\'schema\': \'merlin-software-inventory/1\', \'status\': \'failed\',\n                  \'passed\': False, \'error_class\': type(exc).__name__, \'message\': str(exc)[:1500],\n                  \'qualification\': False, \'promotion_authority\': False}\n    output.write_text(json.dumps(report, indent=2, sort_keys=True) + \'\\n\')\n    print(\'RESULT=\' + json.dumps(report, sort_keys=True), flush=True)\n    return 0 if report[\'status\'] in (\'collected\', \'succeeded\') else 1\n\n\nif __name__ == \'__main__\':\n    raise SystemExit(main())\n'
PARENT_V2 = 'd5ca4a312d47627ed274e4fb8d20e383103e670d'
PARENT_V2_SHA = '21bb9ad254eb60a1facd18f62cc198eb30a2c19a0dbd49ff84f8fbffbfc2504f'
BASE_ARTIFACT = 14704988710
BASE_ARCHIVE_SHA = 'fbc803cef0c097bb8b43cdf2f3991d72b37c5a0ab80b3639e539130ead25457f'
BASE_SOURCE_SHA = '2e84f3cef17aec4fa3a93cc681761f3b134e8315770ed5010a42184cc8400475'
BASE_MAP = '76b9e39f143c4eac83e360b30c53e9c64cdd0df761e711c493766d70c2f66926'
LOADER_MAP = '15a7a2aa22675d76a9c3be6f5880dae831bf45a09d5aa959fddd21c186195384'
OLD_ANCHOR = '47874bc1ded7b59b167c0052564e8d6ff31daae2'
ENV = {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C.UTF-8'}
def sha(raw):
    return hashlib.sha256(raw).hexdigest()
def git(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
        ensure_ascii=False, allow_nan=False).encode()
def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError('reviewed controller preimage differs')
    return text.replace(before, after)
def fixed_blob(api, identity, size, digest):
    obj = api('git/blobs/' + identity)
    if (obj.get('sha') != identity or obj.get('encoding') != 'base64'
        or type(obj.get('size')) is not int or obj['size'] != size
        or not 0 < size <= 32000):
        raise ValueError('fixed bounded source object required')
    raw = base64.b64decode(''.join(obj['content'].split()), validate=True)
    if len(raw) != size or git(raw) != identity or sha(raw) != digest:
        raise ValueError('fixed source bytes differ')
    return raw
def fixed_overlay(api):
    parts = CANDIDATE['overlay_chunks']
    total = CANDIDATE['overlay_encoded_bytes']
    if (not isinstance(parts, list) or len(parts) != 2
        or type(total) is not int or not 2 <= total <= 64000):
        raise ValueError('exact two-chunk bounded overlay required')
    for index in (0, 1):
        part = parts[index]
        if (not isinstance(part, dict) or set(part) != {'position', 'git_blob', 'bytes', 'sha256'}
        or type(part['position']) is not int or part['position'] != index
        or type(part['bytes']) is not int or not 0 < part['bytes'] <= 32000):
            raise ValueError('fixed overlay chunk identity/order/size differs')
    if sum(part['bytes'] for part in parts) != total:
        raise ValueError('fixed overlay total size differs')
    encoded = b''.join(fixed_blob(api, parts[index]['git_blob'], parts[index]['bytes'],
        parts[index]['sha256']) for index in (0, 1))
    if len(encoded) != total or sha(encoded) != CANDIDATE['overlay_encoded_sha256']:
        raise ValueError('fixed ordered overlay concatenation differs')
    return encoded
def download_baseline(parent):
    url = ('https://api.github.com/repos/morganaspim/Cace-app/actions/artifacts/'
        + str(BASE_ARTIFACT) + '/zip')
    request = urllib.request.Request(url, headers={
        'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN'],
        'Accept': 'application/vnd.github+json',
    })
    opener = urllib.request.build_opener(parent['SafeRedirect']())
    with opener.open(request, timeout=20) as response:
        raw = response.read(600001)
    if len(raw) != 529239 or sha(raw) != BASE_ARCHIVE_SHA:
        raise ValueError('preserved baseline artifact identity differs')
    return raw
def assemble(parent, api, output):
    raw = download_baseline(parent)
    (output / 'baseline-artifact-identity.json').write_text(json.dumps({
        'artifact_id': BASE_ARTIFACT, 'archive_sha256': sha(raw),
        'archive_bytes': len(raw), 'source_package_sha256': BASE_SOURCE_SHA,
        'source_map_sha256': BASE_MAP,
    }, indent=2) + '\n')
    members = parent['zip_members'](raw)
    source = members['tested-source.zip']
    if sha(source) != BASE_SOURCE_SHA:
        raise ValueError('baseline source package differs')
    files = parent['zip_members'](source)
    manifest = json.loads(files.pop('manifest.json'), object_pairs_hook=parent['unique'])
    if len(files) != 117 or set(files) != set(manifest['files']):
        raise ValueError('baseline source membership differs')
    if set(files) != set(manifest['git_blobs']):
        raise ValueError('baseline Git identity membership differs')
    for name, body in files.items():
        if sha(body) != manifest['files'][name] or git(body) != manifest['git_blobs'][name]:
            raise ValueError('baseline source bytes differ')
    if sha(canonical({n: sha(b) for n, b in sorted(files.items())})) != BASE_MAP:
        raise ValueError('baseline map differs')
    encoded = fixed_overlay(api)
    packed = base64.b64decode(encoded.strip(), validate=True)
    if len(packed) != CANDIDATE['overlay_packed_bytes'] or sha(packed) != CANDIDATE['overlay_packed_sha256']:
        raise ValueError('candidate overlay archive differs')
    decoder = lzma.LZMADecompressor(memlimit=128 * 1024 * 1024)
    raw = decoder.decompress(packed, max_length=CANDIDATE['overlay_expanded_bytes'] + 1)
    if (len(raw) != CANDIDATE['overlay_expanded_bytes']
        or not decoder.eof or decoder.unused_data
        or sha(raw) != CANDIDATE['overlay_expanded_sha256']):
        raise ValueError('candidate overlay expansion differs')
    overlay = json.loads(raw, object_pairs_hook=parent['unique'])
    if (set(overlay) != {'schema', 'parent_source_map_sha256', 'source_map_sha256', 'files'}
        or overlay['schema'] != 'merlin-egm-overlay/4'
        or overlay['parent_source_map_sha256'] != BASE_MAP
        or overlay['source_map_sha256'] != CANDIDATE['source_map_sha256']
        or set(overlay['files']) != set(CANDIDATE['changed_paths'])
        or any(not isinstance(value, str) for value in overlay['files'].values())):
        raise ValueError('fixed code-only overlay scope differs')
    files.update({name: text.encode('utf-8') for name, text in overlay['files'].items()})
    if (len(files) != CANDIDATE['source_files'] or len(files) > 200
        or sum(map(len, files.values())) > 4 * 1024 * 1024
        or sha(canonical({n: sha(b) for n, b in sorted(files.items())})) != CANDIDATE['source_map_sha256']):
        raise ValueError('complete candidate source map differs')
    return files
def source_package(files, output):
    manifest = {
        'schema': 'merlin-egm-source/2',
        'source_commit': CANDIDATE['source_commit'],
        'source_kind': 'exact_selected_candidate_shard',
        'parent_source_map_sha256': BASE_MAP,
        'files': {n: sha(b) for n, b in sorted(files.items())},
        'git_blobs': {n: git(b) for n, b in sorted(files.items())},
        'source_map_sha256': CANDIDATE['source_map_sha256'],
        'qualification': False, 'promotion_authority': False,
    }
    raw = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()
    (output / 'source-manifest.json').write_bytes(raw)
    with zipfile.ZipFile(output / 'tested-source.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, body in sorted({**files, 'manifest.json': raw}.items()):
            item = zipfile.ZipInfo(name, (2026, 11, 21, 0, 0, 0))
            item.external_attr = 0o100644 << 16
            item.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(item, body)
    return manifest
def retain_timeout(output, phase, exc):
    def as_bytes(value):
        return value if isinstance(value, bytes) else (value or '').encode()
    stdout, stderr = as_bytes(exc.output), as_bytes(exc.stderr)
    log = 'tests.txt' if phase == 'software' else 'live-execution.txt'
    (output / log).write_bytes(stdout + b'\nSTDERR\n' + stderr)
    receipt = {
        'status': 'failed', 'termination': 'timeout', 'timeout_seconds': exc.timeout,
        'phase': phase, 'source_commit': CANDIDATE['source_commit'],
        'source_map_sha256': CANDIDATE['source_map_sha256'],
        'run_id': int(os.environ['GITHUB_RUN_ID']),
        'stdout_bytes': len(stdout), 'stdout_sha256': sha(stdout),
        'stderr_bytes': len(stderr), 'stderr_sha256': sha(stderr),
        'execution_evidence_complete': False, 'passed': False,
        'qualification': False, 'promotion_authority': False,
    }
    if phase == 'software':
        path = output / 'software-report.events.txt'
        events = []
        if path.exists():
            raw = path.read_bytes()
            receipt['progress_sha256'] = sha(raw)
            if len(raw) <= 4 * 1024 * 1024:
                for line in raw.decode(errors='replace').splitlines():
                    try:
                        item = json.loads(line)
                    except ValueError:
                        receipt['partial_progress_line'] = True
                        continue
                    if (isinstance(item, dict) and isinstance(item.get('test_id'), str)
        and 0 < len(item['test_id']) <= 400):
                        events.append(item)
            else:
                receipt['progress_parse_omitted'] = 'retained progress exceeds 4 MiB parse ceiling'
        starts = [e['test_id'] for e in events if e.get('event') == 'start']
        stops = [e['test_id'] for e in events if e.get('event') == 'stop']
        receipt.update(
        tests=len(starts), executed_test_ids=sorted(starts),
        unfinished_test_ids=sorted(set(starts) - set(stops)),
        failures=None, errors=None, skipped=None,
        failed_test_ids=sorted(e['test_id'] for e in events if e.get('event') == 'failure'),
        error_test_ids=sorted(e['test_id'] for e in events if e.get('event') == 'error'),
        skipped_test_ids=sorted(e['test_id'] for e in events if e.get('event') == 'skip'),
        test_inventory_sha256=sha(canonical({'schema': 'merlin-executed-software-tests/1',
        'test_ids': sorted(starts)}))
        if starts and len(starts) == len(set(starts)) else None,
        )
        (output / 'software-report.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    (output / (phase + '-timeout.json')).write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    return receipt
def named_cases(value, expected, *, run_id, service_unchanged, kind='kernel'):
    result = {key: value[key] for key in value if key != 'cases'}
    rows = value.get('cases')
    if not isinstance(rows, list) or len(rows) > 1000:
        rows = []
    result['cases'] = []
    for row in rows:
        if not isinstance(row, dict):
            result['cases'].append({'name': None, 'passed': False, 'error_class': 'MalformedCase'})
            continue
        result['cases'].append({key: row[key] for key in ('name', 'passed', 'error_class', 'error') if key in row})
    names = [row.get('name') for row in result['cases']]
    names_valid = all(isinstance(name, str) and name in expected for name in names)
    exact = (names_valid and len(names) == len(expected) and len(set(names)) == len(names)
        and set(names) == set(expected))
    observed_commit = value.get('source_commit')
    observed_map = value.get('source_map_sha256')
    identity_exact = (
        (observed_commit == CANDIDATE['source_commit'] if kind == 'context'
        else observed_commit in (None, CANDIDATE['source_commit']))
        and observed_map in (None, CANDIDATE['source_map_sha256']))
    scope_exact = (
        value.get('private_context_used') is False
        and value.get('actual_native_model_review_performed') is False
        if kind == 'context' else value.get('private_state_accessed') is False)
    result.update(
        source_commit=observed_commit if kind == 'context' or 'source_commit' in value else CANDIDATE['source_commit'],
        source_map_sha256=observed_map if 'source_map_sha256' in value else CANDIDATE['source_map_sha256'],
        source_identity_origin='fixture_declared_and_host_checked' if kind == 'context' else 'host_bound_verified_source',
        source_identity_exact=identity_exact, scope_exact=scope_exact,
        run_id=run_id, service_unchanged=service_unchanged,
        required_case_names=sorted(expected),
        case_inventory_exact=exact,
        failed_case_ids=sorted(row['name'] for row in result['cases']
        if isinstance(row.get('name'), str) and row.get('passed') is not True),
    )
    result['accepted'] = (exact and identity_exact and scope_exact and value.get('status') == 'succeeded'
        and type(value.get('tests')) is int and value['tests'] == len(expected)
        and type(value.get('passed')) is int and value['passed'] == len(expected)
        and value.get('qualification') is False and value.get('promotion_authority') is False
        and value.get('production_service_modified') is False
        and value.get('permissions_modified') is False
        and all(row.get('passed') is True for row in result['cases']))
    return result
def candidate_run(parent, api, output):
    output = Path(output)
    report = {
        'schema': 'merlin-egm-oci-validation/2',
        'source_commit': CANDIDATE['source_commit'],
        'source_kind': 'exact_selected_candidate_shard',
        'source_map_sha256': CANDIDATE['source_map_sha256'],
        'parent_source_map_sha256': BASE_MAP,
        'run_id': int(os.environ['GITHUB_RUN_ID']),
        'run_attempt': int(os.environ['GITHUB_RUN_ATTEMPT']),
        'workflow_commit': os.environ['GITHUB_SHA'],
        'runner': os.environ['RUNNER_NAME'], 'python': sys.version,
        'architecture': platform.machine(), 'actual_native_model_review_performed': False,
        'private_context_used': False, 'production_service_modified': False,
        'permissions_modified': False, 'avrea_used': False,
        'qualification': False, 'promotion_authority': False,
    }
    protocol = {
        'question': 'Exact candidate checks and completed-process recovery through the existing synthetic OCI path',
        'source_commit': CANDIDATE['source_commit'], 'source_map_sha256': CANDIDATE['source_map_sha256'],
        'software_tests': CANDIDATE['software_tests'],
        'software_test_inventory_sha256': CANDIDATE['test_inventory_sha256'],
        'required_kernel_cases': CANDIDATE['kernel_cases'],
        'required_context_cases': CANDIDATE['context_cases'],
        'synthetic_only': True, 'deployment': False, 'maximum_corrective_runs': 2,
        'model_review': 'Blocked until native fresh-context runtime and authenticated complete trace exist',
    }
    (output / 'protocol.json').write_text(json.dumps(protocol, indent=2, sort_keys=True) + '\n')
    try:
        files = assemble(parent, api, output)
        root = output / 'source'
        root.mkdir(mode=0o700)
        for name, body in files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
        source_package(files, output)
        report['source_package_sha256'] = sha((output / 'tested-source.zip').read_bytes())
        (output / 'software-runner.txt').write_text(SOFTWARE_RUNNER)
        try:
            result = subprocess.run(
        ['/usr/bin/python3', '-I', '-B', '-c', SOFTWARE_RUNNER, 'run', str(root),
        str(output / 'source-manifest.json'), str(output / 'software-report.json'),
        '--expected-count', str(CANDIDATE['software_tests']),
        '--expected-digest', CANDIDATE['test_inventory_sha256']],
        cwd=root, env=ENV, capture_output=True, text=True, timeout=210)
        except subprocess.TimeoutExpired as exc:
            report['tests'] = retain_timeout(output, 'software', exc)
            raise RuntimeError('software acceptance timed out with retained partial evidence') from exc
        (output / 'tests.txt').write_text(result.stdout + result.stderr)
        report['tests'] = json.loads((output / 'software-report.json').read_text())
        report['tests']['run_id'] = report['run_id']
        (output / 'software-report.json').write_text(json.dumps(report['tests'], indent=2, sort_keys=True) + '\n')
        if result.returncode or report['tests'].get('passed') is not True:
            raise RuntimeError('exact executed software inventory not accepted')
        bootstrap = parent['ROOT_BOOTSTRAP']
        bootstrap = replace_once(
        bootstrap, "if len(files)!=116 or checksum!='" + LOADER_MAP + "'",
        "if len(files)!=" + str(CANDIDATE['source_files']) + " or checksum!='" + CANDIDATE['source_map_sha256'] + "'")
        if bootstrap.count(OLD_ANCHOR) != 2:
            raise ValueError('fixture source anchor preimage differs')
        bootstrap = bootstrap.replace(OLD_ANCHOR, CANDIDATE['source_commit'])
        for name in ('root-loader.txt', 'loader-repair.json'):
            (output / name).rename(output / ('parent-' + name))
        (output / 'root-loader.txt').write_text(bootstrap)
        (output / 'loader-repair.json').write_text(json.dumps({
        'parent_v2_git_blob': PARENT_V2,
        'parent_loader_sha256': sha(parent['ROOT_BOOTSTRAP'].encode()),
        'root_loader_sha256': sha(bootstrap.encode()),
        'candidate_source_map_sha256': CANDIDATE['source_map_sha256'],
        'runtime_permissions_changed': False,
        'change': 'Only the reviewed candidate source count, source map and fixture source commit change.',
        }, indent=2) + '\n')
        compile(bootstrap, 'candidate-root-owned-source-loader', 'exec')
        report['service_before'] = parent['service']()
        if report['service_before'].get('ActiveState') != 'active':
            raise RuntimeError('production service not active before drill')
        payload = canonical({n: base64.b64encode(b).decode() for n, b in sorted(files.items())})
        if len(payload) > 4 * 1024 * 1024:
            raise ValueError('privileged source payload ceiling')
        try:
            try:
                result = subprocess.run(
        ['/usr/bin/sudo', '-n', '/usr/bin/python3', '-I', '-B', '-S', '-c', bootstrap],
        input=payload, env=ENV, cwd='/', capture_output=True, timeout=100)
            except subprocess.TimeoutExpired as exc:
                report['live_timeout'] = retain_timeout(output, 'native', exc)
                raise RuntimeError('native acceptance timed out with retained partial evidence') from exc
            (output / 'live-execution.txt').write_bytes(result.stdout + b'\nSTDERR\n' + result.stderr)
            lines = [line[len('EGM_LIVE_REPORT='):] for line in result.stdout.decode(errors='replace').splitlines()
        if line.startswith('EGM_LIVE_REPORT=')]
            live = json.loads(lines[-1]) if lines else {'status': 'failed', 'reason': 'missing live receipt'}
            (output / 'live-report.json').write_text(json.dumps(live, indent=2, sort_keys=True) + '\n')
        finally:
            report['service_after'] = parent['service']()
            report['service_unchanged'] = report['service_before'] == report['service_after']
        for key in ('kernel', 'context'):
            report[key] = named_cases(live.get(key, {}), CANDIDATE[key + '_cases'],
        run_id=report['run_id'], service_unchanged=report['service_unchanged'], kind=key)
        report['fixture_frame_source_anchor'] = live.get('fixture_frame_source_anchor')
        if (result.returncode or not report['service_unchanged']
        or report['kernel']['accepted'] is not True or report['context']['accepted'] is not True
        or live.get('fixture_frame_source_anchor') != CANDIDATE['source_commit']
        or live.get('tested_source_map_sha256') != CANDIDATE['source_map_sha256']):
            raise RuntimeError('exact kernel/context case integration not accepted')
        report['status'] = 'succeeded'
    except Exception as exc:
        report.update(status='failed', error_class=type(exc).__name__, message=str(exc)[:1500])
    (output / 'report.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('tests', 'kernel', 'context')}, indent=2, sort_keys=True))
    if report['status'] != 'succeeded':
        raise RuntimeError('candidate EGM integration acceptance failed')
    return report
def run(api, output):
    raw = fixed_blob(api, PARENT_V2, 2494, PARENT_V2_SHA)
    source = replace_once(raw.decode(), "return namespace['run'](api, output)",
        'return candidate_run(namespace, api, output)')
    namespace = {'candidate_run': candidate_run}
    exec(compile(source, 'exact-v2-loader-candidate-hook', 'exec'), namespace)
    (Path(output) / 'parent-v2-identity.json').write_text(json.dumps({
        'git_blob': PARENT_V2, 'sha256': sha(raw), 'hooked_controller_sha256': sha(source.encode()),
        'scope': 'Reuse the exact prior v2 loader; replace only the final run call.',
    }, indent=2) + '\n')
    return namespace['run'](api, output)
