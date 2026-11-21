"""Freeze the exact ledger continuation around the existing bounded OCI transport.

Source publication alone cannot invoke this workflow. A separate additive
UUID request commit is required after source review and fresh host preflight.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path

import workflow_base

ROOT = Path(__file__).resolve().parent
NAMES = ('bootstrap_browser.py', 'activate_browser.py', 'finish_runtime.py',
         'launch_episode.py', 'smoke_renderer.py', 'recover_capture.py',
         'complete_acceptance.py', 'test_complete_acceptance.py')
FROZEN_HELPERS = {
    'bootstrap_browser.py': '1c5197a76fb66aaac19eb4bad92fce841e1e1aa43fb657d7c8590b0866683474',
    'activate_browser.py': '3514af927a28c77fe2c219248f15ffd88577561454bd4bbf09d842657cc9f979',
    'finish_runtime.py': '6472f54038001fbe1aedac06e8ed480f8327d50709eb1755683e61488acf73d9',
    'launch_episode.py': '3f51b4506fbc740219daf7b4c52c68e81bea32b7e0a7757888581371d8996f5f',
    'smoke_renderer.py': 'a9cc3ab7b67ec2511a7ed56b2af4d829a424ad3a00f2632e0e860ceddc59e2f9',
    'recover_capture.py': 'b9f2d6bbd4bb879389332f2b4b87fdcd7748c108d07c98d746cad9d7f03f4c93',
}


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
            'git_blob': hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()}


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('exact reviewed wrapper section differs: ' + old[:80])
    return text.replace(old, new)


ROOT_BLOCK = r'''    (out/'ledger-continuation-plan.json').write_text(json.dumps({
       'operation':'complete-ledger-44946846703','predecessor_request_id':'18106dfc-0a56-4b68-9d30-5d334d7d6a69',
       'predecessor_run_id':44946846703,'product_successor_commit':'74bd09166f338172f4af3854a124c12b5b07081a',
       'system_package_installs':0,'python_package_installs':0,'runtime_dependency_acquisition':False,
       'automatic_retry':False,'prior_fixture_attempts':2,'prior_public_attempts':1,
       'remaining_public_attempts':2,'new_fixture_attempts':0,'arxiv_reacquisitions':0,
       'retained_recovery_before_new_public_submissions':True,'model_calls':0},sort_keys=True,indent=2))
    # Each source buffer is checked once and embedded as a compressed literal.
    # Root never imports mutable runner-owned helper files. Compression avoids
    # Linux's per-argument size ceiling while retaining exact source identities.
    root_code='import base64,hashlib,json,signal,sys,types,zlib\n'
    for module_name in ('bootstrap_browser','activate_browser','finish_runtime','recover_capture','complete_acceptance'):
        name=module_name+'.py';source=(out/name).read_bytes();check(source,pins[name])
        capsule=base64.b85encode(zlib.compress(source,9)).decode()
        root_code+=('raw=zlib.decompress(base64.b85decode('+repr(capsule)+'));'
            'assert len(raw)=='+repr(pins[name]['bytes'])+' and hashlib.sha256(raw).hexdigest()=='
            +repr(pins[name]['sha256'])+';m=types.ModuleType('+repr(module_name)+');'
            'sys.modules['+repr(module_name)+']=m;exec(compile(raw,'+repr('pinned-'+name)+',"exec"),m.__dict__)\n')
    root_code+='def expire(signum,frame): raise sys.modules["bootstrap_browser"].BootstrapError("root controller absolute deadline")\nsignal.signal(signal.SIGALRM,expire);signal.alarm(900)\n'
    root_code+='result=sys.modules["complete_acceptance"].run('+','.join(repr(v) for v in (str(out/'runtime.zip'),runtime_pin,request,execution,str(out)))+');signal.alarm(0);print(json.dumps(result,sort_keys=True))\n'
'''


def wrapper(pins, runtime):
    body = workflow_base.WRAPPER
    body = body.replace('import ast,base64,', 'import ast,base64,zlib,')
    body = body.replace('merlin/browser-bootstrap-requests/', 'merlin/browser-runtime-requests/')
    body = body.replace('merlin-browser-bootstrap-request/1', 'merlin-browser-runtime-request/1')
    body = body.replace('continue-zvbi-44942304091', 'complete-ledger-44946846703')
    body = body.replace('.github/workflows/merlin-browser-bootstrap.yml', '.github/workflows/merlin-browser-runtime.yml')
    body = once(body, "out=Path(os.environ['RUNNER_TEMP'])/('merlin-browser-bootstrap-%d-%d'",
                "out=Path(os.environ['RUNNER_TEMP'])/('merlin-browser-runtime-%d-%d'")
    body = once(body, "'controller_sha256':pins['bootstrap_browser.py']['sha256']",
                "'controller_sha256':pins['complete_acceptance.py']['sha256']")
    # Product count first, so the independent 33 new controller controls are not
    # accidentally transformed into 41 by a later broad replacement.
    body = once(body, 'r.testsRun==33', 'r.testsRun==41')
    body = once(body, "pattern='test_bootstrap_browser.py'", "pattern='test_complete_acceptance.py'")
    body = once(body, 'r.testsRun==36', 'r.testsRun==33')
    start = body.index('    # The inspected failed operation retained the complete signed closure.')
    end = body.index('    if len(root_code.encode())>115000:', start)
    body = body[:start] + ROOT_BLOCK + body[end:]
    body = body.replace('fixed_browser_bootstrap_finished', 'fixed_browser_ledger_continuation_finished')
    body = body.replace('@@SOURCE_PINS@@', repr(pins)).replace('@@RUNTIME_PIN@@', repr(runtime))
    if '@@' in body:
        raise ValueError('unresolved continuation workflow placeholder')
    ast.parse(body, feature_version=(3, 9))
    return body


def render(body):
    return '''name: Merlin fixed retained-browser ledger continuation

"on":
  push:
    branches: ["merlin/browser-operations-20261121"]
    paths: ["merlin/browser-runtime-requests/**"]

permissions:
  contents: read

concurrency:
  group: merlin-dot-oci-operations
  cancel-in-progress: false

jobs:
  fixed-browser-runtime:
    runs-on: [self-hosted, cace, oci, aarch64]
    timeout-minutes: 30
    steps:
      - name: Verify exact sources and complete the two remaining browser attempts
        shell: bash
        env:
          GITHUB_TOKEN: ${{ github.token }}
        run: |
          set -euo pipefail
          python3 - <<'PYCODE'
''' + ''.join('          ' + line + '\n' for line in body.splitlines()) + '''          PYCODE
      - name: Preserve original capture, derivative, complete native evidence and rollback
        if: always()
        uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02
        with:
          name: merlin-browser-runtime-${{ github.run_id }}-${{ github.run_attempt }}
          path: ${{ runner.temp }}/merlin-browser-runtime-${{ github.run_id }}-${{ github.run_attempt }}/
          include-hidden-files: true
          retention-days: 30
          if-no-files-found: warn
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.absolute()
    runtime = json.loads((root / 'runtime/runtime-pins.json').read_text())
    pins = {}
    for name in NAMES:
        raw = (root / 'ops/merlin_browser' / name).read_bytes()
        ast.parse(raw, feature_version=(3, 9))
        pins[name] = pin(raw)
        if name in FROZEN_HELPERS and pins[name]['sha256'] != FROZEN_HELPERS[name]:
            raise ValueError('frozen helper source changed: ' + name)
    body = wrapper(pins, runtime)
    workflow = render(body).encode()
    path = root / '.github/workflows/merlin-browser-runtime.yml'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(workflow)
    report = {
        'schema': 'merlin-browser-ledger-publication/1',
        'branch': 'merlin/browser-operations-20261121',
        'observed_base_commit': 'c8b61b30dfff6c1e3c7889595276d27adca7b5be',
        'product_successor_commit': '74bd09166f338172f4af3854a124c12b5b07081a',
        'sources': pins, 'runtime': runtime,
        'workflow': {'path': '.github/workflows/merlin-browser-runtime.yml', **pin(workflow)},
        'operation': 'complete-ledger-44946846703',
        'request_schema': 'merlin-browser-runtime-request/1',
        'request_trigger': 'merlin/browser-runtime-requests/<new UUID>.json',
        'request_fields': ['schema', 'request_id', 'operation', 'created_at'],
        'request_must_be_separate_single_added_file_commit': True,
        'native_prerequisites': {'controller_controls': 33, 'exact_runtime_product_controls': 41,
                                 'python': '3.9', 'skipped_tests_admitted': False},
        'acceptance_budget': {'original_ceiling': 5, 'previous_fixture_attempts': 2,
                              'previous_public_attempts': 1, 'remaining_public_attempts': 2,
                              'new_fixture_attempts': 0, 'arxiv_reacquisitions': 0, 'automatic_retry': False},
        'package_installs': 0, 'model_calls': 0, 'host_reboot': False,
        'root_envelope_seconds': {'alarm': 900, 'systemd': 930, 'kill_grace': 15, 'outer_wait': 950},
        'native_execution': False, 'remote_publication': False, 'dispatch': False,
    }
    (root / 'continuation-freeze.json').write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
    print(json.dumps(report, sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
