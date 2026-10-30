#!/usr/bin/env python3
"""MCFC–CACE project-only fail-fast, *local* pre-PR gate.

Static checks + bounded targeted tests + existing canonical bug sweep. This is
engineering feedback and has no Lean, proof, source-promoting, security-sandbox,
release, remote-runner, or production approval authority. Do not substitute its
quick PASS for the separate full CACE regression/qualification gates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
from typing import Any, Sequence

SCHEMA_VERSION = 1
CHANGE_KINDS = frozenset({'feature','bugfix','refactor','docs','test','infrastructure'})
MAX_CHANGED_FILES = 800
MAX_TARGETED_TESTS = 20
MAX_FILE_BYTES = 8 * 1024 * 1024

class GateError(RuntimeError):
    """Invalid or unavailable gate prerequisites. Never interpret as a PASS."""


def _issue(code: str, path: str, detail: str, next_action: str) -> dict[str, str]:
    return {'code':code,'path':path,'detail':detail,'next_action':next_action}


def _git(root: Path,*args: str) -> str:
    try:
        r=subprocess.run(['git','-C',str(root),*args],check=True,
                         capture_output=True,timeout=15)
        return r.stdout.decode('utf-8','surrogateescape')
    except (FileNotFoundError,subprocess.CalledProcessError,subprocess.TimeoutExpired,UnicodeError) as exc:
        raise GateError(f'GIT_STATE_UNAVAILABLE: {args[0]}: {type(exc).__name__}') from exc


def discover_changes(root: Path, base_ref: str = 'origin/main') -> tuple[str, ...]:
    """Collect branch delta, working tree and untracked files; missing base blocks."""
    root=Path(root).resolve()
    if not (root/'.git').exists():
        raise GateError('NOT_A_GIT_CHECKOUT: unable to establish source scope')
    if not isinstance(base_ref,str) or not re.fullmatch(r'[A-Za-z0-9_./^~-]{1,128}',base_ref) or base_ref.startswith('-'):
        raise GateError('INVALID_BASE_REF')
    _git(root,'rev-parse','--verify',f'{base_ref}^{{commit}}')
    commands=(('diff','--name-only','-z','--diff-filter=ACMRD',f'{base_ref}...HEAD'),
              ('diff','--name-only','-z','--diff-filter=ACMRD','HEAD'),
              ('ls-files','--others','--exclude-standard','-z'))
    files=set()
    for cmd in commands:
        data=_git(root,*cmd)
        files.update(part for part in data.split('\x00') if part)
    if len(files)>MAX_CHANGED_FILES:
        raise GateError(f'CONTEXT_BUDGET: {len(files)} changed paths exceeds {MAX_CHANGED_FILES}; split source shards')
    return tuple(sorted(files))


def _safe_relative(root: Path, name: str) -> Path:
    if not isinstance(name,str) or not name or '\x00' in name or '\\' in name:
        raise GateError('unsafe relative path')
    path=PurePosixPath(name)
    if path.is_absolute() or any(part in {'.','..'} for part in path.parts) or name.startswith('-'):
        raise GateError('absolute, traversal or option-shaped path')
    full=root.joinpath(*path.parts)
    for parent in (full,*full.parents):
        if parent==root.parent: break
        if parent.is_symlink(): raise GateError('symlink in changed path')
        if parent==root: break
    if not full.resolve(strict=False).is_relative_to(root.resolve()):
        raise GateError('path outside source root')
    return full


def _runtime(path: str) -> bool:
    return (path.startswith(('cace_studio/','scripts/','cpp/','formal/','ops/','security/')) or
            path.startswith('.github/workflows/') or path in {'pyproject.toml','CMakeLists.txt'})


def _related_test(src: str, tests: tuple[str, ...]) -> bool:
    if src.startswith(('cpp/','formal/')):
        return any(t.startswith(('tests/','cpp/tests/','formal/cace_formal/')) for t in tests)
    if src.startswith('.github/workflows/'):
        return any('workflow' in t or 'actions_policy' in t for t in tests)
    if src == 'pyproject.toml': return bool(tests)
    stem=PurePosixPath(src).stem.lower()
    aliases={stem,stem.replace('cace_',''),stem.replace('check_','')}
    if stem in {'__init__','__main__'}:
        return bool(tests)
    # A dependency-specific regression is preferred to arbitrary unrelated tests.
    return any(any((f'test_{a}' in PurePosixPath(t).stem.lower() or
                    f'test_ai_{a}' in PurePosixPath(t).stem.lower()) for a in aliases)
               for t in tests)


def _load_json(path: Path, label: str, issues: list[dict]) -> Any:
    try:
        if not path.exists():
            raise ValueError('required bug-closure registry missing')
        if path.stat().st_size>MAX_FILE_BYTES:
            raise ValueError('registry file exceeds size budget')
        return json.loads(path.read_text(encoding='utf-8'))
    except (ValueError,UnicodeError,PermissionError,OSError,json.JSONDecodeError) as exc:
        issues.append(_issue('REGISTRY_UNAVAILABLE',str(path.name),f'{label}: {type(exc).__name__}: {exc}',
                             'Restore a valid checked-in registry and re-run preflight'))
        return None


def _check_bug_queue(root: Path, issues: list[dict], change_kind: str, changed_tests: tuple[str,...]) -> None:
    current=_load_json(root/'quality/bug_incidents.json','bug incident queue',issues)
    classes=_load_json(root/'quality/bug_classes.json','canonical guarded classes',issues)
    if current is None or classes is None: return
    if not isinstance(current,dict) or current.get('schema_version')!=1 or not isinstance(current.get('incidents'),list):
        issues.append(_issue('BUG_QUEUE_SCHEMA','quality/bug_incidents.json','schema_version=1 and incidents list required','Correct queue structure'))
        return
    if not isinstance(classes,dict) or not isinstance(classes.get('classes'),list):
        issues.append(_issue('BUG_CLASS_SCHEMA','quality/bug_classes.json','canonical classes list absent','Repair canonical bug registry'))
        return
    canonical={item.get('id') for item in classes['classes'] if isinstance(item,dict) and item.get('status')=='GUARDED'}
    bugfix_closures=0
    seen=set()
    for i,item in enumerate(current['incidents']):
        if not isinstance(item,dict):
            issues.append(_issue('BUG_QUEUE_SCHEMA','quality/bug_incidents.json',f'incident #{i} must be object','Correct record'))
            continue
        ident=item.get('id')
        if not isinstance(ident,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{2,127}',ident) or ident in seen:
            issues.append(_issue('BUG_QUEUE_SCHEMA','quality/bug_incidents.json',f'invalid or duplicate incident #{i}','Assign unique stable bug ID'))
            continue
        seen.add(ident)
        state=item.get('status')
        if state=='OPEN':
            issues.append(_issue('OPEN_BUG',ident,'Unresolved recorded defect; do not hide or suppress it',
                                 'Reproduce, repair siblings, add regression and canonical guard'))
        elif state=='GUARDED':
            fields=('summary','root_cause','reproducer_test','sibling_sweep','guarded_class_id')
            if any(not isinstance(item.get(f),str) or not item[f].strip() for f in fields):
                issues.append(_issue('BUG_CLOSURE_INCOMPLETE',ident,'Root cause, reproducer, sweep and guarded class required',
                                     'Complete documented closure evidence'))
                continue
            try:
                test_path=_safe_relative(root,item['reproducer_test'])
                if not item['reproducer_test'].startswith('tests/') or not test_path.is_file():
                    raise GateError('regression test missing')
            except GateError:
                issues.append(_issue('BUG_REPRODUCER_MISSING',ident,'Referenced regression test absent or unsafe',
                                     'Add the actual reproducing regression test'))
                continue
            if item['guarded_class_id'] not in canonical:
                issues.append(_issue('UNREGISTERED_GUARD',ident,'No GUARDED record in canonical quality/bug_classes.json',
                                     'Complete bug-class closure and content hash through existing bug sweep'))
                continue
            if item['reproducer_test'] in changed_tests:
                bugfix_closures+=1
        else:
            issues.append(_issue('BUG_QUEUE_SCHEMA',ident,'Status must be OPEN or GUARDED','Set explicit known state'))
    if change_kind=='bugfix' and not bugfix_closures:
        issues.append(_issue('BUG_FIX_NOT_REGISTERED','quality/bug_incidents.json',
                             'A bugfix needs a changed regression and linked GUARDED canonical bug-class record',
                             'Register bug, add regression, sweep siblings, and guard class'))


def assess(root: Path,changed_files:Sequence[str],*,change_kind:str='feature') -> dict[str,Any]:
    """Deterministic static preflight; never executes model-supplied code."""
    root=Path(root).resolve()
    if change_kind not in CHANGE_KINDS: raise GateError('unsupported change kind')
    if len(changed_files)>MAX_CHANGED_FILES: raise GateError('source scope exceeds context budget')
    issues=[]
    changed=tuple(sorted(set(changed_files)))
    if not changed: issues.append(_issue('NO_CHANGES','.','No source diff found', 'Check base ref and working tree'))
    tests=tuple(p for p in changed if p.startswith('tests/test_') and p.endswith('.py'))
    if len(tests)>MAX_TARGETED_TESTS:
        issues.append(_issue('TEST_BUDGET_EXCEEDED','tests/',f'{len(tests)} changed tests exceed quick budget {MAX_TARGETED_TESTS}',
                             'Split work into deterministic test shards'))
    source=[p for p in changed if _runtime(p)]
    if change_kind=='docs' and source:
        issues.append(_issue('MISCLASSIFIED_CHANGE',source[0],'Runtime/CI change mislabeled documentation-only',
                             'Select an honest change kind'))
    if source and not tests:
        issues.append(_issue('TEST_DELTA_MISSING','tests/','Runtime or CI modifications require changed tests in branch diff',
                             'Add/update related regression test before PR'))
    for path in source:
        if not _related_test(path,tests):
            issues.append(_issue('RELATED_TEST_MISSING',path,'No related test changed for this source/CI path',
                                 'Add a focused regression test for modified behavior'))
    hashed=[]
    for name in changed:
        try:
            path=_safe_relative(root,name)
        except GateError as exc:
            code='SYMLINK_CHANGED' if 'symlink' in str(exc).lower() else 'INVALID_PATH'
            issues.append(_issue(code,name,str(exc),'Replace with a real repository-relative source path'))
            continue
        if not path.is_file():
            issues.append(_issue('CHANGED_FILE_MISSING',name,'File absent from source tree (may be a deletion)',
                                 'Confirm deletion and add a test for the removed behavior'))
            continue
        try:
            if path.stat().st_size>MAX_FILE_BYTES:
                issues.append(_issue('FILE_SIZE_BUDGET',name,'File exceeds bounded local preflight budget',
                                     'Use a separate content-appropriate gate'))
                continue
            data=path.read_bytes()
            hashed.append((name,hashlib.sha256(data).hexdigest()))
            if name.endswith('.py'):
                try: compile(data.decode('utf-8'),name,'exec')
                except (SyntaxError,UnicodeDecodeError,ValueError) as exc:
                    issues.append(_issue('PYTHON_SYNTAX',name,f'{type(exc).__name__}: {exc}',
                                         'Fix syntax/encoding before running tests'))
            if name.endswith('.json'):
                try: json.loads(data)
                except (json.JSONDecodeError,UnicodeDecodeError,ValueError) as exc:
                    issues.append(_issue('JSON_PARSE',name,f'{type(exc).__name__}: {exc}',
                                         'Correct JSON before running tests'))
        except (OSError,PermissionError) as exc:
            issues.append(_issue('READ_FAILURE',name,f'{type(exc).__name__}', 'Restore file access'))
    _check_bug_queue(root,issues,change_kind,tests)
    payload=json.dumps(hashed,sort_keys=True,separators=(',',':')).encode()
    return {'schema_version':SCHEMA_VERSION,'project':'MCFC-CACE','status':'BLOCKED' if issues else 'PASS_STATIC_ONLY',
            'change_kind':change_kind,'changed_files':list(changed),'changed_file_count':len(changed),
            'changed_tests':list(tests),'local_content_fingerprint_sha256':hashlib.sha256(payload).hexdigest(),
            'issues':issues,'qualification_status':'NOT_RUN','production_release_status':'NOT_RUN',
            'limits':['Static + targeted checks are not full Python/native/Lean/security qualification',
                      'Local content hashes are not authenticated evidence',
                      'Existing canonical bug-class hash validation remains required']}


def run_quick_checks(root:Path,report:dict[str,Any],*,timeout:int=120)->dict[str,Any]:
    if report.get('status')!='PASS_STATIC_ONLY': raise GateError('static preflight failed; refusing execution')
    root=Path(root).resolve()
    if not isinstance(timeout,int) or not 5<=timeout<=600: raise GateError('invalid timeout')
    tests=report['changed_tests']
    commands=[]
    if tests:
        commands.append(('targeted_pytest',[sys.executable,'-m','pytest','-q',*tests]))
    bug=root/'scripts/check_bug_sweep.py'
    if not bug.is_file():
        report=dict(report)
        report['status']='BLOCKED'
        report['issues']=[*report['issues'],_issue('BUG_SWEEP_UNAVAILABLE','scripts/check_bug_sweep.py',
                                'Canonical bug sweep missing','Restore canonical bug sweep')]
        report['commands']=[]
        return report
    with tempfile.TemporaryDirectory(prefix='cace-prepr-') as td:
        commands.append(('existing_bug_sweep',[sys.executable,'-m','scripts.check_bug_sweep','--output',str(Path(td)/'bug-sweep.json')]))
        result=dict(report)
        result['commands']=[]
        for ident,cmd in commands:
            try:
                ran=subprocess.run(cmd,cwd=root,capture_output=True,text=True,timeout=timeout,check=False)
                status='PASS' if ran.returncode==0 else 'FAIL'
                result['commands'].append({'id':ident,'state':status,'exit_code':ran.returncode,
                                           'output_tail':(ran.stdout+'\n'+ran.stderr)[-3000:]})
                if ran.returncode!=0:
                    result['issues']=[*result['issues'],_issue('TARGETED_TEST_FAILED' if ident=='targeted_pytest' else 'BUG_SWEEP_FAILED',
                                   ident,'Command failed; inspect output_tail','Repair root cause and re-run gate')]
                    result['status']='BLOCKED'
                    break
            except (OSError,subprocess.TimeoutExpired) as exc:
                result['commands'].append({'id':ident,'state':'NOT_COMPLETED','exit_code':None,
                                           'output_tail':type(exc).__name__})
                result['issues']=[*result['issues'],_issue('TOOL_UNAVAILABLE' if isinstance(exc,OSError) else 'QUICK_GATE_TIMEOUT',
                               ident,type(exc).__name__,'Resolve environment/tool or split the test budget')]
                result['status']='BLOCKED'
                break
        else:
            result['status']='PASS_QUICK_ONLY'
    return result


def main(argv:Sequence[str]|None=None)->int:
    p=argparse.ArgumentParser(description='MCFC–CACE local fail-fast pre-PR gate; NOT formal qualification')
    p.add_argument('--root',type=Path,default=Path.cwd())
    p.add_argument('--base-ref',default='origin/main')
    p.add_argument('--change-kind',choices=sorted(CHANGE_KINDS),required=True)
    p.add_argument('--profile',choices=('inspect','quick'),default='quick')
    p.add_argument('--timeout',type=int,default=120)
    p.add_argument('--output',type=Path,help='Optional JSON report for local retention')
    args=p.parse_args(argv)
    try:
        changed=discover_changes(args.root,args.base_ref)
        report=assess(args.root,changed,change_kind=args.change_kind)
        if args.profile=='quick' and report['status']=='PASS_STATIC_ONLY':
            report=run_quick_checks(args.root,report,timeout=args.timeout)
    except GateError as exc:
        report={'schema_version':SCHEMA_VERSION,'project':'MCFC-CACE','status':'BLOCKED',
                'qualification_status':'NOT_RUN','issues':[_issue('GATE_PREREQUISITE','.',str(exc),
                'Restore source context/prerequisite and rerun')], 'commands':[]}
    output=json.dumps(report,indent=2,sort_keys=True)+'\n'
    print(output,end='')
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(output,encoding='utf-8')
    return 0 if report['status'] in {'PASS_QUICK_ONLY','PASS_STATIC_ONLY'} else 1

if __name__=='__main__':raise SystemExit(main())