from __future__ import annotations
import hashlib, json, os, shutil, subprocess, time
from pathlib import Path

root=Path(__file__).resolve().parents[1]
formal=root/'formal'/'cace_formal'
out=formal/'FORMAL_BUILD_ATTESTATION.json'

def pretty(x):
    return json.dumps(x,indent=2,sort_keys=True)+'\n\n'

def discover_tool(name: str):
    direct=shutil.which(name)
    if direct:
        return direct
    bins=[]
    env_bin=os.environ.get("CACE_LEAN_BIN")
    if env_bin:
        bins.append(Path(env_bin))
    bins += [
        root/'formal'/'toolchain'/'bin',
        root/'formal'/'lean'/'bin',
        Path('/mnt/data/lean/bin'),
        Path('/mnt/data/lean4/bin'),
    ]
    try:
        for p in Path('/mnt/data').glob('*lean*'):
            if p.is_dir():
                bins.extend([
                    p/'bin', p,
                    p/'build'/'release'/'stage1'/'bin',
                    p/'build'/'release'/'stage0'/'bin',
                    p/'build'/'stage1'/'bin',
                    p/'stage1'/'bin',
                    p/'stage0'/'bin',
                ])
        # Uploaded full Lean source/build trees may not themselves contain "lean"
        # in the directory name. Search a shallow, bounded set of canonical stage paths.
        for pat in (
            '*/build/release/stage1/bin',
            '*/build/release/stage0/bin',
            '*/*/build/release/stage1/bin',
            '*/*/build/release/stage0/bin',
        ):
            bins.extend(Path('/mnt/data').glob(pat))
    except Exception:
        pass
    for b in bins:
        q=b/name
        if q.exists() and os.access(q,os.X_OK):
            return str(q)
    return None

lean=discover_tool('lean')
lake=discover_tool('lake')
result={
  'passed':False,
  'timestamp_unix':time.time(),
  'lean':lean,
  'lake':lake,
  'commands':[],
}
if not lake or not lean:
    result['status']='NOT_RUN'
    result['reason']='lean/lake executable not available; local uploaded toolchains are auto-detected via CACE_LEAN_BIN and /mnt/data/*lean*'
else:
    env=os.environ.copy()
    bindir=str(Path(lean).resolve().parent)
    env['PATH']=bindir+os.pathsep+env.get('PATH','')
    result['status']='RUNNING'
    for cmd in [[lake,'update'],[lake,'exe','cache','get'],[lake,'build']]:
        p=subprocess.run(cmd,cwd=formal,text=True,capture_output=True,check=False,env=env)
        result['commands'].append({
          'cmd':cmd,'returncode':p.returncode,
          'stdout_tail':p.stdout[-4000:],'stderr_tail':p.stderr[-4000:]
        })
        if p.returncode:
            result['status']='FAILED'
            result['reason']='command failed'
            break
    else:
        obligation=(formal/'CACEFormal'/'DiscreteOrthogonality.lean').read_text()
        open_marker='OPEN OBLIGATION' in obligation
        result['open_obligation_marker']=open_marker
        if open_marker:
            result['status']='BLOCKED_OPEN_THEOREM'
            result['reason']='DiscreteOrthogonality.lean still contains an explicit open-obligation marker'
        else:
            result['status']='PASS'
            result['passed']=True

result['project_files_sha256']=hashlib.sha256(
    ''.join(sorted(
        str(p.relative_to(formal))+hashlib.sha256(p.read_bytes()).hexdigest()
        for p in formal.rglob('*')
        if p.is_file() and p.name!='FORMAL_BUILD_ATTESTATION.json'
    )).encode()
).hexdigest()
out.write_text(pretty(result))
print(pretty(result),end='')
if result['passed']:
    raise SystemExit(0)
if result['status']=='NOT_RUN':
    raise SystemExit(77)
raise SystemExit(2)
