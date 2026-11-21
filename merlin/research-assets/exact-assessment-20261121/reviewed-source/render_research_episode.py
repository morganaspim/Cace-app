"""Local fixed-template renderer; no network, model, native process or host writes.

Root authenticates the supplied accepted native observations and published blob
readbacks. This helper verifies their retained bytes and exact fixed cohort; it
does not manufacture provider authentication or turn fixture checks into evidence.
"""
import argparse
import ast
import base64
import hashlib
import io
import functools
import tokenize
import json
from pathlib import Path
import re
import stat
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SOURCE_COMMIT = '761756025fb88f7e722c799ca91964e3ad24c53a'
SOURCE_MAP = '548194d9fddd5a587feeb5384bf6b71f9fe7cee4976dab519725251fb2ca3654'
TEST_INVENTORY = '8fea9b239870559acc888ddd7d003d8754234dfa1f8497020de5dc108c8cfd4b'
WORKER_SHA = '7f0947df45c3239cce48dd7e112886f4ccff98dd097673d0275844d227caf8f6'
TEMPLATES = {
    'host': ('ops/merlin_dot/research_episode_host.py.in', 'b5e68f87b4539e703fce5b9960a5be5ef18303b4fb08770b08886967c11ec4c6'),
    'runner': ('ops/merlin_dot/run_research_episode.py.in', 'a3b5360bf6a60e12cdd45d74de83a199bb654b6cff4d171dd60bfe59a3646642'),
    'workflow': ('merlin-research-episode.yml.in', '4356f7106fd1e7ac48c40dd48f95c307d4e43c91893297f55689cd58a7bd4fed'),
}
ORACLE = {'bytes': 11332, 'sha256': '73ad01b8443ab3e72ee3d54c43a75ff55104b75a3d4125cc17599cced87e9abb'}
RETAINED = {'bytes': 24509, 'sha256': '8f7a13740d46e2bb0150ffc365e7485ae463a1a158d2bb0221d60e424c1642f2'}
RECORDS_SHA = '4f6655bcc146fe0ab4e8b93349c45332d674e04bf30f3f0609561c6f65822213'
DECISION_SHA = 'd799c4e916176b2245a76752a0984cc2ab0a6f636a98837dcdb9e74cd56dd5f7'
NOTES = {'bytes': 4708, 'sha256': 'ad412f724f95df30077a6fb21503a5f291478a0048f762e2c16bddefdbfb7192'}
NUMBERS = {'run_id', 'run_attempt', 'artifact_id', 'artifact_bytes', 'software_tests'}
GIT_FIELDS = {'workflow_commit', 'workflow_git_blob', 'controller_git_blob', 'source_commit'}
DIGEST_FIELDS = {'controller_sha256', 'artifact_sha256', 'report_sha256', 'source_package_sha256',
                 'test_inventory_sha256', 'source_map_sha256'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode()


def decode(raw):
    def unique(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON field')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))


def read(path, maximum=4 * 1024 * 1024):
    with Path(path).open('rb') as stream:
        raw = stream.read(maximum + 1)
    require(len(raw) <= maximum, 'local input byte ceiling')
    return raw


def identity(raw):
    return {'bytes': len(raw), 'sha256': sha(raw), 'git_blob': git(raw)}


def template(name):
    path, expected = TEMPLATES[name]
    raw = read(HERE / path, 64 * 1024 if name == 'host' else 48 * 1024)
    require(sha(raw) == expected, 'frozen template preimage differs: ' + name)
    return raw.decode()


def render(name, marker, value, maximum):
    text = template(name)
    require(text.count(marker) == 1, 'one fixed substitution required')
    raw = text.replace(marker, repr(decode(canonical(value)))).encode()
    if name == 'host': raw = compact_host(raw)
    require(len(raw) <= maximum, name + ' source byte ceiling')
    ast.parse(raw, feature_version=(3, 9))
    return raw


def compact_host(raw):
    """Remove only lexical whitespace/comments; preserve the complete Python3.9 AST.

    The readable template is separately retained and pinned. No code compression,
    hidden source, identifier rewriting or relaxed expanded-code ceiling is used.
    """
    text = raw.decode()
    @functools.lru_cache(None)
    def separator(a, b):
        atoms = {tokenize.NAME, tokenize.NUMBER, tokenize.STRING}
        if a[0] in atoms and b[0] in atoms:
            return True
        seen = []
        try:
            for token in tokenize.generate_tokens(io.StringIO(a[1] + b[1]).readline):
                if token.type not in {tokenize.NEWLINE, tokenize.NL, tokenize.ENDMARKER, tokenize.INDENT, tokenize.DEDENT}:
                    seen.append((token.type, token.string))
        except (tokenize.TokenError, IndentationError):
            pass
        return seen != [a, b]
    parts, depth, line, previous = [], 0, True, None
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        kind, value = token.type, token.string
        if kind in {tokenize.COMMENT, tokenize.NL, tokenize.ENDMARKER}: continue
        if kind == tokenize.INDENT: depth += 1; continue
        if kind == tokenize.DEDENT: depth -= 1; continue
        if kind == tokenize.NEWLINE:
            parts.append('\n'); line, previous = True, None; continue
        current = (kind, value)
        if line: parts.append(' ' * depth); line = False
        elif previous is not None and separator(previous, current): parts.append(' ')
        parts.append(value); previous = current
    compact = ''.join(parts).encode()
    require(ast.dump(ast.parse(raw, feature_version=(3, 9)), include_attributes=False)
            == ast.dump(ast.parse(compact, feature_version=(3, 9)), include_attributes=False),
            'whitespace changed host Python3.9 AST')
    return compact


def retained_data(raw, native):
    require(len(raw) == RETAINED['bytes'] and sha(raw) == RETAINED['sha256'], 'fixed retained-data bytes differ')
    data = decode(raw)
    require(data['schema'] == 'merlin-retained-assessment-inputs/2'
            and len(data['records']) == 39 and sha(canonical(data['records'])) == RECORDS_SHA
            and data['root_decision_sha256'] == DECISION_SHA
            and sha(data['root_decision_utf8'].encode()) == DECISION_SHA
            and data['admission_static']['native_validation'] == data['receipt_static']['native_validation'] == native,
            'retained decision/39 records/native pins differ')
    return data


def members(raw, *, count, maximum):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        names = [item.filename for item in infos]
        require(len(infos) <= count and len(set(names)) == len(names), 'archive member count/duplicates')
        require(sum(item.file_size for item in infos) <= maximum, 'archive expansion ceiling')
        for item in infos:
            require(not item.is_dir() and not stat.S_ISLNK(item.external_attr >> 16)
                    and not item.flag_bits & 1 and not item.filename.startswith('/')
                    and '\\' not in item.filename
                    and all(part not in ('', '.', '..') for part in item.filename.split('/')),
                    'invalid archive member')
        return {name: archive.read(name) for name in names}


def native_pins(value):
    require(isinstance(value, dict) and set(value) == NUMBERS | GIT_FIELDS | DIGEST_FIELDS,
            'exact native_validation pin fields required')
    require(all(type(value[key]) is int and value[key] > 0 for key in NUMBERS), 'actual positive native IDs/counts required')
    for width, fields in ((40, GIT_FIELDS), (64, DIGEST_FIELDS)):
        require(all(isinstance(value[key], str) and re.fullmatch('[0-9a-f]{%d}' % width, value[key]) for key in fields),
                'native Git/digest identity required')
    require(value['run_attempt'] == 1 and value['artifact_bytes'] <= 4 * 1024 * 1024,
            'fixed native attempt/artifact ceiling')
    require(value['source_commit'] == SOURCE_COMMIT and value['source_map_sha256'] == SOURCE_MAP
            and value['software_tests'] == 599 and value['test_inventory_sha256'] == TEST_INVENTORY,
            'fixed published130-file/599-test cohort required')
    return value


def accepted_review(review, pins):
    require(review.get('schema') == 'merlin-independent-native-artifact-review/2'
            and review.get('status') == 'accepted_within_recorded_scope' and review.get('mismatches') == []
            and review.get('qualification') is False and review.get('promotion_authority') is False,
            'actual accepted native review required')
    fields = ('run_id', 'run_attempt', 'artifact_id', 'artifact_bytes', 'artifact_sha256', 'workflow_commit',
              'source_commit', 'source_map_sha256', 'software_tests', 'test_inventory_sha256')
    require(all(key in review and canonical(review[key]) == canonical(pins[key]) for key in fields),
            'accepted review identity differs')
    require(review.get('source_files') == 130 and review.get('kernel_cases') == 8 and review.get('context_cases') == 6,
            'accepted review cohort differs')
    checks = review.get('checks')
    require(isinstance(checks, list) and len(checks) >= 40
            and all(isinstance(row, dict) and row.get('passed') is True for row in checks),
            'complete passing native measurement review required')


def verify_native(pins, prepared, review, archive):
    native_pins(pins); accepted_review(review, pins)
    prepared = Path(prepared)
    proposal = decode(read(prepared / 'final/pins.json'))
    require(proposal.get('upload_readback_status') == 'EXACT_BYTES_VERIFIED'
            and proposal.get('finalized_bytes_equal_proposal') is True, 'actual finalized native proposal required')
    for key in ('source_commit', 'source_map_sha256', 'software_tests', 'test_inventory_sha256'):
        require(proposal.get(key) == pins[key], 'native proposal cohort differs')
    require(proposal.get('source_files') == 130, 'native proposal membership differs')
    controller = read(prepared / 'final/validate_egm_context_v6.py', 32000)
    workflow = read(prepared / 'final/merlin-egm-context.yml', 32000)
    require(identity(controller) == {key: proposal['controller'][key] for key in ('bytes', 'sha256', 'git_blob')}
            and sha(controller) == pins['controller_sha256'] and git(controller) == pins['controller_git_blob'],
            'reviewed native controller bytes differ')
    require(git(workflow) == proposal['workflow']['git_blob'] == pins['workflow_git_blob']
            and sha(workflow) == proposal['workflow']['sha256'], 'reviewed native workflow bytes differ')
    require(len(archive) == pins['artifact_bytes'] and sha(archive) == pins['artifact_sha256'], 'actual native archive differs')
    data = members(archive, count=64, maximum=8 * 1024 * 1024)
    require(sha(data['report.json']) == pins['report_sha256'] and data['controller.txt'] == controller
            and sha(data['tested-source.zip']) == pins['source_package_sha256'], 'native retained report/source/controller differs')
    report = decode(data['report.json'])
    expected = {'schema': 'merlin-egm-oci-validation/2', 'status': 'succeeded', 'runner': 'cace-oci-a1',
        'architecture': 'aarch64', **{key: pins[key] for key in ('run_id', 'run_attempt', 'workflow_commit',
        'source_commit', 'source_map_sha256', 'source_package_sha256')}}
    require(all(key in report and canonical(report[key]) == canonical(value) for key, value in expected.items()),
            'accepted native report identity/status differs')
    require(all(report.get(key) is False for key in ('qualification', 'promotion_authority', 'permissions_modified',
        'production_service_modified', 'private_context_used', 'actual_native_model_review_performed')),
        'accepted native report scope differs')
    software = decode(data['software-report.json'])
    require(software == report['tests'] and software.get('status') == 'succeeded' and software.get('passed') is True
            and software.get('source_unchanged') is True and software.get('tests') == 599
            and software.get('test_inventory_sha256') == TEST_INVENTORY
            and all(type(software.get(key)) is int and software[key] == 0 for key in
                    ('failures', 'errors', 'skipped', 'expected_failures', 'unexpected_successes')),
            'actual599-test result differs')
    for field in ('executed_test_ids', 'collection_ids'):
        ids = software.get(field)
        require(isinstance(ids, list) and len(ids) == len(set(ids)) == 599 and all(isinstance(x, str) for x in ids)
                and sha(canonical({'schema': 'merlin-executed-software-tests/1', 'test_ids': sorted(ids)})) == TEST_INVENTORY,
                'actual software inventory differs')
    files = members(data['tested-source.zip'], count=131, maximum=4 * 1024 * 1024)
    manifest = decode(files.pop('manifest.json'))
    frozen = decode(read(prepared / 'source-manifest.json'))
    mapping = {name: sha(body) for name, body in sorted(files.items())}
    require(len(files) == 130 and mapping == frozen['files'] == manifest['files']
            and sha(canonical(mapping)) == SOURCE_MAP and manifest['source_commit'] == SOURCE_COMMIT
            and manifest['git_blobs'] == frozen['git_blobs'] == {name: git(body) for name, body in files.items()},
            'exact selected source membership/hash/Git identity differs')
    return files


def host_pins(native, files, oracle, notes):
    require(len(oracle) == ORACLE['bytes'] and sha(oracle) == ORACLE['sha256'], 'fixed independent oracle bytes differ')
    require(len(notes) == NOTES['bytes'] and sha(notes) == NOTES['sha256'], 'fixed source notes bytes differ')
    require(sha(files['python/dot_ai_os/fixed_solver_worker.py']) == WORKER_SHA, 'fixed worker source differs')
    return expected_host_pins(native)


def expected_host_pins(native):
    return {'source_commit': SOURCE_COMMIT, 'source_map_sha256': SOURCE_MAP, 'source_file_count': 130,
        'source_package_sha256': native['source_package_sha256'], 'native_validation_sha256': sha(canonical(native)),
        'retained_inputs_sha256': RETAINED['sha256'], 'retained_inputs_bytes': RETAINED['bytes'],
        'retained_records_sha256': RECORDS_SHA, 'root_decision_sha256': DECISION_SHA,
        'worker_sha256': WORKER_SHA, 'oracle_sha256': ORACLE['sha256'], 'source_notes_sha256': NOTES['sha256']}


def prepare_assets(args):
    native_raw = read(args.native_pins); pins = native_pins(decode(native_raw))
    review_raw = read(args.native_review); review = decode(review_raw)
    archive = read(args.native_artifact)
    files = verify_native(pins, args.native_prepared, review, archive)
    oracle, notes = read(args.oracle, 32000), read(args.notes, 32000)
    retained = read(args.retained_inputs, 32000); retained_data(retained, pins)
    values = host_pins(pins, files, oracle, notes)
    host = render('host', '__FROZEN_RELEASE_PINS__', values, 48 * 1024)
    assets = {'host': ('research_episode_host.py', host), 'oracle': ('oracle.json', oracle),
              'notes': ('source-notes.json', notes), 'retained': ('retained-inputs.json', retained)}
    record = {'schema': 'merlin-research-assets/1', 'status': 'prepared_pending_actual_publication',
        'native_validation': pins, 'native_review_sha256': sha(review_raw),
        'native_pins_input_sha256': sha(native_raw), 'template_sha256': {key: row[1] for key, row in TEMPLATES.items()},
        'assets': {key: {'file': name, **identity(raw)} for key, (name, raw) in assets.items()},
        'provenance': 'Root supplies independently accepted actual provider evidence; this is a local byte consistency check.',
        'model_execution': False, 'native_execution': False, 'publication': False}
    out = Path(args.output); out.mkdir(parents=True, exist_ok=False)
    for name, raw in assets.values(): (out / name).write_bytes(raw)
    for name, value in (('host-pins.json', values), ('native-pins.json', pins), ('assets.json', record)):
        (out / name).write_bytes(canonical(value) + b'\n')
    (out / 'accepted-native-review.json').write_bytes(review_raw)
    return record


def verify_readback(value, raw):
    expected = identity(raw)
    require(isinstance(value, dict) and value.get('encoding') == 'base64'
            and type(value.get('size')) is int and value['size'] == len(raw)
            and value.get('sha') == expected['git_blob'], 'actual published blob identity differs')
    require(base64.b64decode(''.join(value['content'].split()), validate=True) == raw,
            'actual published blob bytes differ')
    return expected


def privileged_program(host, host_sha, output):
    return ('import hashlib;source=' + repr(host) + ';assert hashlib.sha256(source).hexdigest()=='
        + repr(host_sha) + ";namespace={'_HOST_SOURCE_SHA256':" + repr(host_sha)
        + "};exec(compile(source,'pinned-research-host','exec'),namespace);namespace['root_run']("
        + repr(str(output)) + ',' + repr(str(output)) + ')')


def finalize_controller(args):
    source = Path(args.assets)
    record = decode(read(source / 'assets.json')); values = decode(read(source / 'host-pins.json'))
    pins = native_pins(decode(read(source / 'native-pins.json')))
    review_raw = read(source / 'accepted-native-review.json'); accepted_review(decode(review_raw), pins)
    require(record.get('schema') == 'merlin-research-assets/1' and record['native_validation'] == pins
            and record['native_review_sha256'] == sha(review_raw) and values == expected_host_pins(pins),
            'prepared acceptance binding changed')
    host = read(source / 'research_episode_host.py', 48 * 1024)
    oracle, notes = read(source / 'oracle.json', 32000), read(source / 'source-notes.json', 32000)
    require(host == render('host', '__FROZEN_RELEASE_PINS__', values, 48 * 1024), 'prepared host source changed')
    require(len(oracle) == ORACLE['bytes'] and sha(oracle) == ORACLE['sha256']
            and len(notes) == NOTES['bytes'] and sha(notes) == NOTES['sha256'], 'prepared fixed assets changed')
    retained = read(source / 'retained-inputs.json', 32000); retained_data(retained, pins)
    blobs, readbacks = {}, {}
    for name, raw, path in (('host', host, args.host_readback), ('oracle', oracle, args.oracle_readback),
                            ('notes', notes, args.notes_readback), ('retained', retained, args.retained_readback)):
        observed_raw = read(path, 128 * 1024)
        blobs[name] = verify_readback(decode(observed_raw), raw)
        require(blobs[name] == {key: record['assets'][name][key] for key in ('bytes', 'sha256', 'git_blob')},
                'prepared asset identity changed')
        readbacks[name] = sha(observed_raw)
    runner_values = {'native_validation': pins, **blobs}
    runner = render('runner', '__FROZEN_RUNNER_PINS__', runner_values, 32000)
    # A Linux path of <=4096 bytes can need at most four repr bytes per input byte.
    # Use that worst representation twice; the unchanged runner rechecks the actual program.
    maximum_program_bytes = len(privileged_program(host, blobs['host']['sha256'], '\x01' * 4096).encode())
    require(maximum_program_bytes <= 96 * 1024, 'privileged program worst-path ceiling')
    workflow = template('workflow')
    for marker, value in (('__RUNNER_GIT_BLOB__', git(runner)), ('__RUNNER_SHA256__', sha(runner))):
        require(workflow.count(marker) == 1, 'workflow pin substitution preimage differs')
        workflow = workflow.replace(marker, value)
    raw_workflow = workflow.encode()
    result = {'schema': 'merlin-research-controller-proposal/1', 'native_validation': pins,
        'runner': identity(runner), 'workflow': identity(raw_workflow), 'assets': blobs,
        'actual_readback_file_sha256': readbacks, 'privileged_program_worst_path_bytes': maximum_program_bytes,
        'caps': {'host': 48 * 1024, 'runner': 32000, 'privileged_program': 96 * 1024},
        'provenance': 'Caller supplies actual published Git blob readbacks; local bytes matched without remote calls.',
        'template_bytes_unchanged': True, 'model_execution': False, 'native_execution': False,
        'publication': False, 'actual_host_acceptance': False}
    out = Path(args.output); out.mkdir(parents=True, exist_ok=False)
    (out / 'run_research_episode.py').write_bytes(runner)
    (out / 'merlin-research-episode.yml').write_bytes(raw_workflow)
    (out / 'runner-pins.json').write_bytes(canonical(runner_values) + b'\n')
    (out / 'proposal.json').write_bytes(canonical(result) + b'\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    first = commands.add_parser('prepare-assets')
    for name in ('native-pins', 'native-prepared', 'native-artifact', 'native-review', 'output'):
        first.add_argument('--' + name, required=True)
    first.add_argument('--oracle', default=str(ROOT / 'verification/release-continuation/oracle/oracle.canonical.json'))
    first.add_argument('--notes', default=str(ROOT / 'verification/release-continuation/oracle/source-notes.json'))
    first.add_argument('--retained-inputs', default=str(HERE / 'retained-inputs.json'))
    second = commands.add_parser('finalize-controller')
    for name in ('assets', 'host-readback', 'oracle-readback', 'notes-readback', 'retained-readback', 'output'):
        second.add_argument('--' + name, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare_assets(args) if args.command == 'prepare-assets' else finalize_controller(args), indent=2))


if __name__ == '__main__':
    main()
