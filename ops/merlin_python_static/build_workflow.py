"""Build a source-pinned, unprivileged inspection definition; never dispatch."""
import argparse
import hashlib
from pathlib import Path
import textwrap


ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / "browser-continuation-44956695079/artifact/workflow-definition.yml"
BASE_SHA = "2093b64ad89e68add600d4bbd7b70c933b26276bfd01eec1b19acc31cb55fc3f"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-count", type=int, required=True)
    args = parser.parse_args()
    assert 1 <= args.test_count <= 100
    original = BASE.read_bytes()
    assert hashlib.sha256(original).hexdigest() == BASE_SHA
    original = textwrap.dedent(original.decode().split("python3 - <<'PYCODE'\n", 1)[1].split("\n          PYCODE", 1)[0])
    common = original[original.index("def unique(items):"):original.index("try:\n    changed=")]
    common = common.replace("merlin-browser-runtime-%d-%d", "merlin-python-static-inspection-%d-%d")
    common = common.replace("# already exited before this handler. Root descendants are bounded by\n"
                            "        # the separately verified systemd control group below.",
                            "# already exited before this handler. Acquisition/inspection workers\n"
                            "        # remain in this same unprivileged controller process group.")
    # The exact existing bounded child runner is reused. No privileged launch or
    # acceptance code is included from the base workflow.
    pins = {}
    for name in ("acquire_inspect.py", "test_acquire_inspect.py"):
        raw = (ROOT / "ops/merlin_python_static" / name).read_bytes()
        pins[name] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                      "git_blob": hashlib.sha1(("blob %d\0" % len(raw)).encode() + raw).hexdigest()}
    prelude = '''import ast,base64,datetime,hashlib,json,os,re,selectors,signal,subprocess,sys,time,urllib.request,uuid,zlib
from pathlib import Path
repo=os.environ['GITHUB_REPOSITORY'];commit=os.environ['GITHUB_SHA']
if (repo!='morganaspim/Cace-app' or os.environ['GITHUB_REF']!='refs/heads/merlin/browser-operations-20261121'
    or os.environ.get('RUNNER_NAME')!='cace-oci-a1' or os.geteuid()!=1000
    or sys.version_info[:2]!=(3,9) or not re.fullmatch('[0-9a-f]{40}',commit)):
    raise RuntimeError('unexpected unprivileged static-inspection identity')
run_id=int(os.environ['GITHUB_RUN_ID']);attempt=int(os.environ['GITHUB_RUN_ATTEMPT'])
if run_id<=44955762960 or attempt!=1: raise RuntimeError('new first static-inspection attempt required')
pins=@@PINS@@
clean={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C.UTF-8','LC_ALL':'C.UTF-8',
       'HOME':'/var/empty','XDG_CONFIG_HOME':'/var/empty','XDG_CACHE_HOME':'/var/empty',
       'XDG_DATA_HOME':'/var/empty','PYTHONDONTWRITEBYTECODE':'1'}
'''.replace("@@PINS@@", repr(pins))
    operation = '''stage='request_validation'
try:
    changed=api('commits/'+commit)['files']
    if len(changed)!=1 or changed[0]['status']!='added': raise RuntimeError('one additive static-inspection request required')
    path=changed[0]['filename']
    if not re.fullmatch(r'merlin/python-static-inspection-requests/[0-9a-f-]{36}\\.json',path):
        raise RuntimeError('fixed static-inspection request path required')
    raw,_=fetch(path)
    if len(raw)>16000: raise RuntimeError('request byte ceiling')
    request=json.loads(raw,object_pairs_hook=unique)
    if (not isinstance(request,dict) or set(request)!={'schema','request_id','operation','created_at'}
        or request['schema']!='merlin-python-static-inspection-request/1'
        or request['operation']!='inspect-cpython-3.11.18-20261110-aarch64'
        or path!='merlin/python-static-inspection-requests/'+request['request_id']+'.json'
        or str(uuid.UUID(request['request_id']))!=request['request_id']
        or datetime.datetime.strptime(request['created_at'],'%Y-%m-%dT%H:%M:%SZ').strftime('%Y-%m-%dT%H:%M:%SZ')!=request['created_at']):
        raise RuntimeError('fixed acquisition-and-static-inspection contract required')
    (out/'request.json').write_bytes(raw)
    stage='source_verification'
    for name,pin in pins.items():
        raw,_=fetch('ops/merlin_python_static/'+name);check(raw,pin)
        ast.parse(raw,feature_version=(3,9));(out/name).write_bytes(raw)
    workflow,workflow_blob=fetch('.github/workflows/merlin-python-static-inspection.yml')
    (out/'workflow-definition.yml').write_bytes(workflow)
    (out/'source-identities.json').write_text(json.dumps({'sources':pins,
        'workflow_git_blob':workflow_blob,'workflow_sha256':hashlib.sha256(workflow).hexdigest()},sort_keys=True,indent=2))
    execution={'repository':repo,'ref':os.environ['GITHUB_REF'],'runner':os.environ['RUNNER_NAME'],
        'workflow_commit':commit,'run_id':run_id,'run_attempt':attempt,
        'controller_sha256':pins['acquire_inspect.py']['sha256'],'python':sys.version}
    (out/'identity.json').write_text(json.dumps(execution,sort_keys=True,indent=2))
    stage='local_fixture_controls'
    code="import sys,unittest,json;sys.path.insert(0,sys.argv[1]);suite=unittest.defaultTestLoader.discover(sys.argv[1],pattern='test_acquire_inspect.py');r=unittest.TextTestRunner(verbosity=2).run(suite);print(json.dumps({'tests':r.testsRun,'errors':len(r.errors),'failures':len(r.failures),'skipped':len(r.skipped)}));sys.exit(0 if r.wasSuccessful() and not r.skipped and r.testsRun==@@COUNT@@ else 1)"
    fixed(['/usr/bin/python3','-I','-B','-c',code,str(out)],'static-inspection-controls.txt',60)
    for name,pin in pins.items(): check((out/name).read_bytes(),pin)
    stage='bounded_unprivileged_acquisition_and_inspection'
    source=(out/'acquire_inspect.py').read_bytes();check(source,pins['acquire_inspect.py'])
    capsule=base64.b64encode(zlib.compress(source,9)).decode()
    code='import base64,hashlib,json,sys,types,zlib\\n'
    code+=('raw=zlib.decompress(base64.b64decode('+repr(capsule)+',validate=True));'
        'assert len(raw)=='+repr(len(source))+' and hashlib.sha256(raw).hexdigest()=='
        +repr(pins['acquire_inspect.py']['sha256'])+';m=types.ModuleType("pinned_static_inspector");'
        'sys.modules[m.__name__]=m;exec(compile(raw,"pinned-acquire_inspect.py","exec"),m.__dict__)\\n')
    code+='result=m.run('+','.join(repr(v) for v in (request,execution,str(out)))+');print(json.dumps({k:result[k] for k in ("status","installation_allowed","logical_acquisitions_attempted","fetched_code_executions")},sort_keys=True));sys.exit(0 if result["status"]=="static_observations_complete_installation_unapproved" else 2)\\n'
    if len(code.encode())>115000: raise RuntimeError('bounded static-inspection capsule exceeded')
    (out/'execution-input-identity.json').write_text(json.dumps({'code_bytes':len(code.encode()),
        'code_sha256':hashlib.sha256(code.encode()).hexdigest(),'controller_sha256':pins['acquire_inspect.py']['sha256'],
        'uid':1000,'outer_deadline_seconds':340,'installation_allowed':False,'fetched_code_executions':0},indent=2,sort_keys=True))
    fixed(['/usr/bin/python3','-I','-B','-c',code],'static-inspection-operation.txt',340)
    print(json.dumps({'status':'fixed_static_inspection_finished','installation_allowed':False,
        'native_installations':0,'fetched_code_executions':0,'model_calls':0},sort_keys=True))
except BaseException as exc:
    # Exception messages are deliberately excluded: third-party URL errors can
    # contain signed redirect queries. Stage and type retain the failure scope.
    (out/'operation-error.json').write_text(json.dumps({'status':'failed','stage':stage,
        'error_type':type(exc).__name__,'workflow_commit':commit,'run_id':run_id,
        'run_attempt':attempt,'installation_allowed':False,'model_calls':0},indent=2))
    print(json.dumps({'status':'failed','stage':stage,'error_type':type(exc).__name__,
        'installation_allowed':False},sort_keys=True))
    sys.exit(2)
'''.replace("@@COUNT@@", str(args.test_count))
    header = '''name: Merlin fixed CPython acquisition and static inspection

"on":
  push:
    branches: ["merlin/browser-operations-20261121"]
    paths: ["merlin/python-static-inspection-requests/**"]

permissions:
  contents: read

concurrency:
  group: merlin-dot-oci-operations
  cancel-in-progress: false

jobs:
  fixed-python-static-inspection:
    runs-on: [self-hosted, cace, oci, aarch64]
    timeout-minutes: 12
    steps:
      - name: Verify exact sources then acquire and inspect data as UID1000
        shell: bash
        env:
          GITHUB_TOKEN: ${{ github.token }}
        run: |
          set -euo pipefail
          python3 - <<'PYCODE'
'''
    footer = '''          PYCODE
      - name: Preserve bounded inspection data and all failure receipts
        if: always()
        uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02
        with:
          name: merlin-python-static-inspection-${{ github.run_id }}-${{ github.run_attempt }}
          path: ${{ runner.temp }}/merlin-python-static-inspection-${{ github.run_id }}-${{ github.run_attempt }}/
          include-hidden-files: true
          retention-days: 30
          if-no-files-found: warn
'''
    output = ROOT / ".github/workflows/merlin-python-static-inspection.yml"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(header + textwrap.indent(prelude + common + operation, "          ") + footer)
    print(output)
    print("bytes=" + str(output.stat().st_size))
    print("sha256=" + hashlib.sha256(output.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
