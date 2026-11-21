"""Verify the prepared controller and packaging without any native host action.

Executes only newly changed controller controls, loads the exact root source
capsule without calling run(), and exercises the actual recovery coordinator
against temporary copies of the retained native capture/registry. All source
captures, receipts and live host paths are left untouched.
"""
import argparse
import ast
import base64
import contextlib
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import zipfile
import zlib
from unittest.mock import patch

import build_continuation_workflow as workflow
import build_runtime

ROOT = Path(__file__).resolve().parent
BASE = Path('/workspace/scratch/abed42219434/browser-operations')
REPAIR = Path('/workspace/scratch/abed42219434/browser-ledger-successor')
SOURCE = BASE / 'activation-44946846703/artifact/root-evidence'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def inventory(root):
    return {str(path.relative_to(root)): sha(path.read_bytes())
            for path in sorted(root.rglob('*')) if path.is_file()}


def check(raw, pin):
    if workflow.pin(raw) != {key: pin[key] for key in ('bytes', 'sha256', 'git_blob')}:
        raise AssertionError('prepared source pin differs')


def recovery_integration(evidence):
    sys.path.insert(0, str(ROOT / 'ops/merlin_browser'))
    import complete_acceptance as C
    original = SOURCE / C.R.SOURCE_EPISODE
    original_inventory = inventory(original)
    registry_inventory = inventory(SOURCE / 'canonical-browser-registry')
    with tempfile.TemporaryDirectory(prefix='merlin-ledger-local-integration-') as folder:
        temporary = Path(folder)
        state = temporary / 'state'
        episodes = state / 'episodes'
        episodes.mkdir(parents=True)
        shutil.copytree(original, episodes / C.R.SOURCE_EPISODE)
        shutil.copytree(SOURCE / 'canonical-browser-registry', state / 'registry')
        release = temporary / 'pinned-runtime'
        release.mkdir()
        payload = (ROOT / 'runtime/merlin-browser-runtime.zip').read_bytes()
        if sha(payload) != C.NEW_RUNTIME:
            raise AssertionError('candidate runtime changed')
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            manifest = json.loads(archive.read('manifest.json'))
            for row in manifest['files']:
                if row['path'].startswith('python/'):
                    raw = archive.read(row['path'])
                    check(raw, row)
                    target = release / row['path']
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(raw)
        logs = temporary / 'logs'
        logs.mkdir()
        checked = C.R.inspect_original(episodes / C.R.SOURCE_EPISODE / 'result')

        def local_directory(path):
            path = Path(path)
            if not path.is_dir() or not path.resolve().is_relative_to(temporary.resolve()):
                raise AssertionError('simulation escaped its temporary directory')
            return path

        with patch.object(C.B, 'STATE', state), patch.object(C.A, 'RELEASE', release), \
             patch.object(C, 'existing_root', side_effect=local_directory):
            result = C.publish_recovery(checked, logs)
        copied_after = inventory(episodes / C.R.SOURCE_EPISODE)
        if copied_after != original_inventory:
            raise AssertionError('temporary original capture was changed')
        replay_code = '''import hashlib,json,sys
sys.path.insert(0,sys.argv[1])
from merlin.project_registry import MerlinRegistry
registry=MerlinRegistry(sys.argv[2])
project='merlin-browser-research';episode=sys.argv[3]
publication=registry.artifact_ref(project,'browser/episodes/'+episode+'/publication.json')
value=json.loads(registry.read_artifact_ref(publication,max_bytes=262144)['content'])
ref=value['sources'][0]['artifacts']['text']
raw=registry.read_artifact_ref(ref,max_bytes=262144)['content']
original=registry.artifact_ref(project,'browser/episodes/'+sys.argv[4]+'/execution-failure.json')
print(json.dumps({'episode_id':episode,'manifest_sha256':value['manifest_sha256'],
 'text_sha256':hashlib.sha256(raw).hexdigest(),'text_bytes':len(raw),'original_failure_sha256':original['sha256'],
 'qualified':value['qualification'],'model_calls':value['model_calls']},sort_keys=True))
'''
        replay = subprocess.run([sys.executable, '-I', '-B', '-c', replay_code,
                                 str(release / 'python'), str(state / 'registry'),
                                 C.R.DERIVED_EPISODE, C.R.SOURCE_EPISODE],
                                capture_output=True, timeout=15, check=True)
        observed = json.loads(replay.stdout)
        if (observed['manifest_sha256'] != C.DERIVED_MANIFEST or observed['text_sha256'] != C.ARXIV_TEXT
                or observed['text_bytes'] != 3184 or observed['original_failure_sha256'] != C.OLD_FAILURE
                or observed['qualified'] is not False or observed['model_calls'] != 0):
            raise AssertionError('fresh-process recovered canonical read differs')
        (evidence / 'local-recovery-fresh-process.json').write_bytes(replay.stdout)
        summary = {key: value for key, value in result.items() if key != 'publication'}
        summary.update(temporary_copy_only=True, original_input_files_unchanged=True,
                       fresh_process_canonical_read=observed, host_execution=False,
                       native_unix_route_tested=False, original_file_count=len(original_inventory))
    if inventory(original) != original_inventory or inventory(SOURCE / 'canonical-browser-registry') != registry_inventory:
        raise AssertionError('retained native input changed')
    return summary


def main():
    global ROOT, REPAIR, SOURCE
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--installed-runtime-zip', type=Path,
                        default=BASE / 'runtime-loader-44944977868/merlin-browser-runtime.zip')
    parser.add_argument('--repair-checkout', type=Path, default=REPAIR)
    parser.add_argument('--retained-evidence-root', type=Path, default=SOURCE)
    args = parser.parse_args()
    ROOT, REPAIR, SOURCE = args.root.absolute(), args.repair_checkout.absolute(), args.retained_evidence_root.absolute()
    evidence = ROOT / 'evidence'
    evidence.mkdir(exist_ok=True)
    freeze = json.loads((ROOT / 'continuation-freeze.json').read_text())
    for name, pin in freeze['sources'].items():
        raw = (ROOT / 'ops/merlin_browser' / name).read_bytes()
        check(raw, pin)
        ast.parse(raw, feature_version=(3, 9))
    check((ROOT / freeze['workflow']['path']).read_bytes(), freeze['workflow'])
    original = args.installed_runtime_zip.read_bytes()
    replacements = {name: (REPAIR / pin['source_path']).read_bytes()
                    for name, pin in build_runtime.REPLACEMENTS.items()}
    rebuilt, _, runtime_pin, _ = build_runtime.build(original, replacements)
    if rebuilt != (ROOT / 'runtime/merlin-browser-runtime.zip').read_bytes() or runtime_pin != freeze['runtime']:
        raise AssertionError('candidate ZIP is not reproducible')
    source_tests = "import sys,unittest,json;sys.path.insert(0,sys.argv[1]);suite=unittest.defaultTestLoader.discover(sys.argv[1],pattern='test_complete_acceptance.py');r=unittest.TextTestRunner(verbosity=2).run(suite);print(json.dumps({'tests':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'skipped':len(r.skipped)}));sys.exit(0 if r.wasSuccessful() and not r.skipped and r.testsRun==33 else 1)"
    controls = subprocess.run([sys.executable, '-I', '-B', '-c', source_tests,
                               str(ROOT / 'ops/merlin_browser')], capture_output=True, timeout=20)
    (evidence / 'controller-controls.txt').write_bytes(controls.stdout + controls.stderr)
    if controls.returncode:
        raise AssertionError('new controller controls failed; see retained log')
    with tempfile.TemporaryDirectory(prefix='merlin-root-capsule-review-') as folder:
        out = Path(folder)
        for name in workflow.NAMES:
            shutil.copyfile(ROOT / 'ops/merlin_browser' / name, out / name)
        request = {'schema': 'merlin-browser-runtime-request/1', 'operation': freeze['operation'],
                   'request_id': '2fbf6605-4eb8-4820-af10-f021288dcb17', 'created_at': '2026-11-21T21:30:00Z'}
        execution = {'repository': 'morganaspim/Cace-app', 'ref': 'refs/heads/' + freeze['branch'],
                     'runner': 'cace-oci-a1', 'run_id': 44946846704, 'run_attempt': 1, 'workflow_commit': 'd' * 40}
        namespace = dict(out=out, pins=freeze['sources'], runtime_pin=runtime_pin, request=request,
                         execution=execution, base64=base64, zlib=zlib, json=json, check=check)
        exec(compile(textwrap.dedent(workflow.ROOT_BLOCK), 'reviewed-root-capsule-builder', 'exec'), namespace)
        root_code = namespace['root_code']
        ast.parse(root_code, feature_version=(3, 9))
        if len(root_code.encode()) > 115000:
            raise AssertionError('root argument ceiling')
        prefix = root_code[:root_code.index('def expire(')]
        module_check = subprocess.run([sys.executable, '-I', '-B', '-c', prefix +
                                      "print(json.dumps({'module_load_only':True,'run_function_invoked':False}))\n"],
                                     capture_output=True, timeout=15, check=True)
        (evidence / 'root-capsule-module-load.txt').write_bytes(module_check.stdout + module_check.stderr)
        capsule = {'bytes': len(root_code.encode()), 'argument_ceiling': 115000,
                   'python39_syntax': True, 'all_five_pinned_modules_loaded': True,
                   'run_function_invoked': False, 'root_code_sha256_with_simulated_invocation': sha(root_code.encode())}
    recovered = recovery_integration(evidence)
    report = {'schema': 'merlin-browser-ledger-local-verification/1',
              'controller_controls': json.loads(controls.stdout),
              'control_scope': 'exact retained receipt + simulated host/transport ordering, budget and rollback',
              'runtime_reproduced_byte_for_byte': True, 'runtime_sha256': runtime_pin['sha256'],
              'changed_runtime_payloads': sorted(build_runtime.REPLACEMENTS), 'unchanged_runtime_payloads': 12,
              'root_capsule': capsule, 'recovery_coordinator_temporary_integration': recovered,
              'source_and_workflow_hashes_checked': True, 'python39_syntax_checked': True,
              'local_python': sys.version, 'native_execution': False, 'public_acquisitions': 0,
              'fixture_replays': 0, 'model_calls': 0, 'remote_mutations': 0,
              'native_41_product_controls': 'not rerun locally; required on native Python3.9 before activation',
              'freeze_sha256': sha((ROOT / 'continuation-freeze.json').read_bytes())}
    (evidence / 'local-verification.json').write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
    print(json.dumps(report, sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
