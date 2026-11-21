"""Build the fixed inspection workflow without modifying acceptance inputs."""
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
    assert 1 <= args.test_count <= 64
    raw = BASE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == BASE_SHA
    original = textwrap.dedent(raw.decode().split("python3 - <<'PYCODE'\n", 1)[1].split("\n          PYCODE", 1)[0])
    common = original[original.index("def unique(items):"):original.index("try:\n    changed=")]
    common = common.replace("merlin-browser-runtime-%d-%d", "merlin-browser-state-inspection-%d-%d")
    launch = original[original.index("    unit='merlin-browser-bootstrap-"):original.index("    print(json.dumps({'status':'fixed_browser_ledger_continuation_finished'")]
    launch = launch.replace("merlin-browser-bootstrap-%d-%d.service", "merlin-browser-state-inspection-%d-%d.service")
    pins = {}
    for name in ("bootstrap_browser.py", "inspect_state.py", "test_inspect_state.py"):
        body = (ROOT / "ops/merlin_browser" / name).read_bytes()
        pins[name] = {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
                      "git_blob": hashlib.sha1(("blob %d\0" % len(body)).encode() + body).hexdigest()}
    assert pins["bootstrap_browser.py"]["sha256"] == "1c5197a76fb66aaac19eb4bad92fce841e1e1aa43fb657d7c8590b0866683474"
    prelude = '''import ast,base64,hashlib,json,os,re,selectors,signal,stat,subprocess,sys,time,urllib.request,zlib
from pathlib import Path
repo=os.environ['GITHUB_REPOSITORY'];commit=os.environ['GITHUB_SHA']
if (repo!='morganaspim/Cace-app' or os.environ['GITHUB_REF']!='refs/heads/merlin/browser-operations-20261121'
    or os.environ.get('RUNNER_NAME')!='cace-oci-a1' or os.geteuid()!=1000
    or sys.version_info[:2]!=(3,9) or not re.fullmatch('[0-9a-f]{40}',commit)):
    raise RuntimeError('unexpected native inspection execution identity')
run_id=int(os.environ['GITHUB_RUN_ID']);attempt=int(os.environ['GITHUB_RUN_ATTEMPT'])
if run_id<=44956695079 or attempt!=1: raise RuntimeError('fresh first inspection attempt required')
pins=@@PINS@@
clean={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C.UTF-8','LC_ALL':'C.UTF-8',
       'HOME':'/var/empty','XDG_CONFIG_HOME':'/var/empty','XDG_CACHE_HOME':'/var/empty',
       'XDG_DATA_HOME':'/var/empty','PYTHONDONTWRITEBYTECODE':'1','PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD':'1'}
'''.replace("@@PINS@@", repr(pins))
    operation = '''try:
    changed=api('commits/'+commit)['files']
    if len(changed)!=1 or changed[0]['status']!='added': raise RuntimeError('one additive inspection request required')
    path=changed[0]['filename']
    if not re.fullmatch(r'merlin/browser-state-inspection-requests/[0-9a-f-]{36}\\.json',path):
        raise RuntimeError('fixed inspection request path required')
    raw,_=fetch(path)
    if len(raw)>16000: raise RuntimeError('request byte ceiling')
    request=json.loads(raw,object_pairs_hook=unique)
    if (not isinstance(request,dict) or set(request)!={'schema','request_id','operation','created_at'}
        or request['schema']!='merlin-browser-state-inspection-request/1'
        or request['operation']!='inspect-state-44956695079'
        or path!='merlin/browser-state-inspection-requests/'+request['request_id']+'.json'):
        raise RuntimeError('fixed read-only inspection contract required')
    (out/'request.json').write_bytes(raw)
    for name,pin in pins.items():
        raw,_=fetch('ops/merlin_browser/'+name);check(raw,pin)
        ast.parse(raw,feature_version=(3,9));(out/name).write_bytes(raw)
    workflow,workflow_blob=fetch('.github/workflows/merlin-browser-state-inspection.yml')
    (out/'workflow-definition.yml').write_bytes(workflow)
    (out/'source-identities.json').write_text(json.dumps({'sources':pins,
        'workflow_git_blob':workflow_blob,'workflow_sha256':hashlib.sha256(workflow).hexdigest()},sort_keys=True,indent=2))
    execution={'repository':repo,'ref':os.environ['GITHUB_REF'],'runner':os.environ['RUNNER_NAME'],
        'workflow_commit':commit,'run_id':run_id,'run_attempt':attempt,
        'controller_sha256':pins['inspect_state.py']['sha256'],'python':sys.version}
    (out/'identity.json').write_text(json.dumps(execution,sort_keys=True,indent=2))
    code="import sys,unittest,json;sys.path.insert(0,sys.argv[1]);suite=unittest.defaultTestLoader.discover(sys.argv[1],pattern='test_inspect_state.py');r=unittest.TextTestRunner(verbosity=2).run(suite);print(json.dumps({'tests':r.testsRun,'errors':len(r.errors),'failures':len(r.failures),'skipped':len(r.skipped)}));sys.exit(0 if r.wasSuccessful() and not r.skipped and r.testsRun==@@COUNT@@ else 1)"
    fixed(['/usr/bin/python3','-I','-B','-c',code,str(out)],'inspection-controls.txt',40)
    for name,pin in pins.items(): check((out/name).read_bytes(),pin)
    root_code='import base64,hashlib,json,signal,sys,types,zlib\\n'
    for module_name in ('bootstrap_browser','inspect_state'):
        name=module_name+'.py';source=(out/name).read_bytes();check(source,pins[name])
        capsule=base64.b64encode(zlib.compress(source,9)).decode()
        root_code+=('raw=zlib.decompress(base64.b64decode('+repr(capsule)+',validate=True));'
            'assert len(raw)=='+repr(pins[name]['bytes'])+' and hashlib.sha256(raw).hexdigest()=='
            +repr(pins[name]['sha256'])+';m=types.ModuleType('+repr(module_name)+');'
            'sys.modules['+repr(module_name)+']=m;exec(compile(raw,'+repr('pinned-'+name)+',"exec"),m.__dict__)\\n')
    root_code+='def expire(signum,frame): raise sys.modules["bootstrap_browser"].BootstrapError("root inspection absolute deadline")\\nsignal.signal(signal.SIGALRM,expire);signal.alarm(900)\\n'
    root_code+='result=sys.modules["inspect_state"].run('+','.join(repr(v) for v in (request,execution,str(out)))+');signal.alarm(0);print(json.dumps({k:result[k] for k in ("status","complete","acceptance_allowed")},sort_keys=True));sys.exit(0 if result["complete"] else 2)\\n'
    if len(root_code.encode())>115000: raise RuntimeError('bounded fixed privileged code exceeded')
'''.replace("@@COUNT@@", str(args.test_count))
    ending = '''    print(json.dumps({'status':'fixed_browser_state_inspection_finished','run_id':run_id,
        'acceptance_allowed':False,'application_mutations':0,'connections':0,'acquisitions':0,'model_calls':0},sort_keys=True))
except BaseException as exc:
    (out/'operation-error.json').write_text(json.dumps({'status':'failed','type':type(exc).__name__,
        'message':str(exc)[:2000],'workflow_commit':commit,'run_id':run_id,'run_attempt':attempt},indent=2))
    raise
'''
    program = prelude + common + operation + launch + ending
    header = '''name: Merlin fixed browser state inspection

"on":
  push:
    branches: ["merlin/browser-operations-20261121"]
    paths: ["merlin/browser-state-inspection-requests/**"]

permissions:
  contents: read

concurrency:
  group: merlin-dot-oci-operations
  cancel-in-progress: false

jobs:
  fixed-browser-state-inspection:
    runs-on: [self-hosted, cace, oci, aarch64]
    timeout-minutes: 30
    steps:
      - name: Verify fixed inspector and record protected state without acceptance
        shell: bash
        env:
          GITHUB_TOKEN: ${{ github.token }}
        run: |
          set -euo pipefail
          python3 - <<'PYCODE'
'''
    footer = '''          PYCODE
      - name: Preserve exact read-only state observations and any failure
        if: always()
        uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02
        with:
          name: merlin-browser-state-inspection-${{ github.run_id }}-${{ github.run_attempt }}
          path: ${{ runner.temp }}/merlin-browser-state-inspection-${{ github.run_id }}-${{ github.run_attempt }}/
          include-hidden-files: true
          retention-days: 30
          if-no-files-found: warn
'''
    workflow = header + textwrap.indent(program, "          ") + footer
    path = ROOT / ".github/workflows/merlin-browser-state-inspection.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(workflow)
    print(path)
    print("bytes=" + str(path.stat().st_size))
    print("sha256=" + hashlib.sha256(path.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
