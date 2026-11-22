"""Fixed-file, cache-only Lean research compiler. Not a multi-tenant sandbox.
No shell, installs, cache writes, production registration, or proof promotion.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import signal
import subprocess
import sys
import time

PIN = '520045ab14e26149ee970e2e617ca04b09bde5d6'
ALLOWED_AXIOMS = frozenset({'propext', 'Classical.choice', 'Quot.sound'})
FILES = ('XenoCore.lean', 'LegacyCandidates.lean', 'GlyphNotation.lean')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def expected_names(text):
    names = re.findall(r'^#print axioms ([A-Za-z_][A-Za-z_0-9.]*)\s*$', text, re.M)
    declarations = re.findall(r'^theorem ([A-Za-z_][A-Za-z_0-9]*)\b', text, re.M)
    if not names or len(names) != len(set(names)) or len(names) != len(declarations):
        raise ValueError('missing or duplicate theorem audits')
    if sorted(x.rsplit('.', 1)[-1] for x in names) != sorted(declarations):
        raise ValueError('audit names do not match theorem declarations')
    return names


def audit_output(output, names):
    pattern = r"'([^']+)' (?:depends on axioms:\s*\[([^\]]*)\]|does not depend on any axioms)"
    matches = re.findall(pattern, output, re.S)
    records = {}
    duplicate = False
    for name, axioms in matches:
        if name in records:
            duplicate = True
        records[name] = [x.strip() for x in axioms.split(',') if x.strip()]
    unexpected = {n: [a for a in aa if a not in ALLOWED_AXIOMS]
                  for n, aa in records.items() if any(a not in ALLOWED_AXIOMS for a in aa)}
    valid = (not duplicate and set(records) == set(names) and not unexpected)
    return {'passed': valid, 'axioms': records, 'unexpected': unexpected,
            'missing_names': sorted(set(names) - set(records)),
            'extra_names': sorted(set(records) - set(names)), 'duplicate': duplicate}


def source_gate(text):
    # Defense-in-depth for these exact reviewed files, NOT a complete Lean parser.
    clean = re.sub(r'/\-.*?\-/', '', text, flags=re.S)
    clean = re.sub(r'--[^\n]*', '', clean)
    if re.findall(r'^import\s+(.+)$', clean, re.M) != ['Mathlib']:
        raise ValueError('only the reviewed Mathlib import is allowed')
    if re.search(r'\b(sorry|admit|axiom|unsafe|run_cmd|native_decide|initialize|IO|extern|implemented_by|unlock_limits)\b', clean):
        raise ValueError('unreviewed proof or execution construct')
    if re.search(r'^\s*#(?!print axioms\b)', clean, re.M):
        raise ValueError('unreviewed command')
    return expected_names(clean)


def child_limits():
    resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, 4 * 1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (8 * 1024**2, 8 * 1024**2))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def run_bounded(command, cwd, env, log_path, timeout=150):
    start = time.monotonic()
    timed_out = False
    with open(log_path, 'wb') as log:
        proc = subprocess.Popen(command, cwd=str(cwd), env=env,
            stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
            start_new_session=True, preexec_fn=child_limits)
        try:
            rc = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(proc.pid, signal.SIGKILL)
            rc = proc.wait()
    return {'returncode': rc, 'timed_out': timed_out,
            'elapsed_seconds': time.monotonic()-start,
            'log_sha256': digest(log_path), 'log_bytes': Path(log_path).stat().st_size}


def main():
    root = Path(__file__).resolve().parent
    out = root/'evidence'
    out.mkdir(exist_ok=False)
    receipt = {'schema': 'merlin-xenomath-lean-research/1',
        'status': 'started', 'modules': [], 'negative_controls': {},
        'source_commit': os.environ.get('SOURCE_COMMIT'),
        'workflow_run_id': os.environ.get('RESEARCH_RUN_ID'),
        'workflow_run_attempt': os.environ.get('RESEARCH_RUN_ATTEMPT'),
        'qualification': False, 'promotion_authority': False,
        'independent_cace_verification': 'not_established',
        'production_registration': 'not_performed', 'avrea_used': False,
        'cache_mutation': False, 'package_installation': False,
        'scope': 'fixed reviewed source files, Lean elaboration and axiom audit; not a multi-tenant OS sandbox'}
    try:
        manifest = json.loads((root/'manifest.json').read_text())
        if set(manifest['files']) != set(FILES):
            raise ValueError('file allowlist mismatch')
        for name in FILES:
            if digest(root/name) != manifest['files'][name]:
                raise ValueError('source identity mismatch: '+name)
            source_gate((root/name).read_text())
        tool = Path('/var/lib/cace-cache/elan/toolchains/leanprover--lean4---v4.32.1/bin/lean')
        cache = Path('/var/lib/cace-cache/mathlib/v4.32.1-'+PIN+'/packages')
        if not tool.is_file() or not cache.is_dir():
            raise RuntimeError('pinned preinstalled Lean or package cache unavailable; no install attempted')
        git_env = {'PATH': '/usr/bin:/bin', 'HOME': str(root), 'LANG': 'C.UTF-8', 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null'}
        revision = subprocess.check_output(['/usr/bin/git','-C',str(cache/'mathlib'),'rev-parse','HEAD'],env=git_env,timeout=10,text=True).strip()
        if revision != PIN:
            raise RuntimeError('Mathlib revision mismatch')
        dirty = subprocess.check_output(['/usr/bin/git','-C',str(cache/'mathlib'),'status','--porcelain','--untracked-files=no'],env=git_env,timeout=15,text=True).strip()
        if dirty:
            raise RuntimeError('Mathlib tracked sources are modified')
        packages = sorted(p for p in cache.iterdir() if p.is_dir())
        if len(packages)>30:
            raise RuntimeError('unexpected cache breadth')
        libs=[p/'.lake/build/lib/lean' for p in packages if (p/'.lake/build/lib/lean').is_dir()]
        if not (cache/'mathlib/.lake/build/lib/lean/Mathlib.olean').is_file():
            raise RuntimeError('compiled Mathlib root missing; no download attempted')
        env={'PATH':'/usr/bin:/bin','HOME':str(root),'LANG':'C.UTF-8',
             'TMPDIR':str(root), 'LEAN_PATH':os.pathsep.join(map(str,libs))}
        version=subprocess.check_output([str(tool),'--version'],env=env,timeout=10,text=True).strip()
        if not re.search(r'\b4\.32\.1\b', version):
            raise RuntimeError('compiler version mismatch')
        receipt.update({'lean_version':version,'lean_binary_sha256':digest(tool),
                        'mathlib_commit':revision,'mathlib_tracked_clean':True,
                        'mathlib_olean_sha256':digest(cache/'mathlib/.lake/build/lib/lean/Mathlib.olean'),
                        'package_libraries':list(map(str,libs))})
        for name in FILES:
            source=root/name
            expected=source_gate(source.read_text())
            log_path=out/(source.stem+'.log')
            command=[str(tool),'-DmaxHeartbeats=4000000','-DmaxRecDepth=4096',
                     '-o',str(out/(source.stem+'.olean')),str(source)]
            result=run_bounded(command,root,env,log_path)
            audit=audit_output(log_path.read_text(errors='replace'),expected)
            result.update({'name':name,'source_sha256':digest(source), 'theorem_count':len(expected),
                           'audit':audit,'passed':result['returncode']==0 and not result['timed_out'] and audit['passed']})
            receipt['modules'].append(result)
            (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        controls={
          'FalseControl.lean':'import Mathlib\ntheorem false_control : (1 : Nat) = 0 := by norm_num\n',
          'UnprovedControl.lean':'import Mathlib\ntheorem unproved_control : False := by sorry\n#print axioms unproved_control\n'}
        for name,text in controls.items():
            path=root/name;path.write_text(text)
            log_path=out/(path.stem+'.log')
            result=run_bounded([str(tool),str(path)],root,env,log_path,timeout=60)
            text_out=log_path.read_text(errors='replace')
            if name=='FalseControl.lean':
                ok=result['returncode']!=0 and not result['timed_out'] and ('unsolved goals' in text_out or 'tactic' in text_out.lower())
            else:
                audit=audit_output(text_out,['unproved_control'])
                ok=(result['returncode']==0 and not audit['passed'] and
                    'sorryAx' in audit['axioms'].get('unproved_control',[]))
                result['audit']=audit
            result['rejection_observed']=ok
            receipt['negative_controls'][name]=result
        passed=all(m['passed'] for m in receipt['modules']) and all(v['rejection_observed'] for v in receipt['negative_controls'].values())
        receipt['status']='passed' if passed else 'failed'
        receipt['audited_theorems']=sum(m['theorem_count'] for m in receipt['modules'] if m['passed'])
    except Exception as exc:
        receipt['status']='blocked'
        receipt['error_type']=type(exc).__name__
        receipt['error']=str(exc)[:1000]
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'status':receipt['status'],'audited_theorems':receipt.get('audited_theorems',0),'error':receipt.get('error')}))
    return 0 if receipt['status']=='passed' else 1

if __name__=='__main__':
    raise SystemExit(main())
