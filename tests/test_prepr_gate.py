from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.cace_prepr_gate import assess, discover_changes, run_quick_checks, GateError


def fixture(tmp_path: Path) -> Path:
    for path in ['cace_studio/ai','scripts','tests','quality','.github/workflows']:
        (tmp_path / path).mkdir(parents=True, exist_ok=True)
    (tmp_path/'cace_studio'/'ai'/'agent.py').write_text('value = 1\n')
    (tmp_path/'tests'/'test_agent.py').write_text('def test_agent(): assert True\n')
    (tmp_path/'scripts'/'check_bug_sweep.py').write_text('import argparse\np=argparse.ArgumentParser();p.add_argument("--output");p.parse_args()\n')
    (tmp_path/'quality'/'bug_classes.json').write_text('{"schema_version": 1, "classes": []}\n')
    (tmp_path/'quality'/'bug_incidents.json').write_text('{"schema_version": 1, "incidents": []}\n')
    return tmp_path


def codes(report): return {i['code'] for i in report['issues']}


def test_no_changes_fails_closed(tmp_path):
    root = fixture(tmp_path)
    result = assess(root, [], change_kind='feature')
    assert result['status'] == 'BLOCKED'
    assert 'NO_CHANGES' in codes(result)


def test_python_syntax_failure_is_identified_before_tests(tmp_path):
    root=fixture(tmp_path)
    (root/'cace_studio/ai/agent.py').write_text('def unfinished(\n')
    result=assess(root,['cace_studio/ai/agent.py','tests/test_agent.py'],change_kind='feature')
    assert 'PYTHON_SYNTAX' in codes(result)
    assert result['status'] == 'BLOCKED'


def test_json_parse_errors_are_highlighted(tmp_path):
    root=fixture(tmp_path)
    (root/'quality/bug_incidents.json').write_text('{broken')
    result=assess(root,['quality/bug_incidents.json'],change_kind='docs')
    assert 'JSON_PARSE' in codes(result)
    assert result['status'] == 'BLOCKED'


def test_code_change_without_matching_test_change_fails(tmp_path):
    root=fixture(tmp_path)
    result=assess(root,['cace_studio/ai/agent.py'],change_kind='feature')
    assert 'TEST_DELTA_MISSING' in codes(result)


def test_docs_only_passes_inspection_without_pytest(tmp_path):
    root=fixture(tmp_path)
    (root/'docs').mkdir(exist_ok=True)
    (root/'docs/intro.md').write_text('context\n')
    result=assess(root,['docs/intro.md'],change_kind='docs')
    assert result['status']=='PASS_STATIC_ONLY'
    assert result['qualification_status']=='NOT_RUN'


def test_docs_change_kind_rejected_for_runtime_diff(tmp_path):
    root=fixture(tmp_path)
    result=assess(root,['cace_studio/ai/agent.py','tests/test_agent.py'],change_kind='docs')
    assert 'MISCLASSIFIED_CHANGE' in codes(result)


def test_paths_cannot_escape_or_be_symlinks(tmp_path):
    root=fixture(tmp_path)
    (root/'scripts/shortcut.py').symlink_to(root/'cace_studio/ai/agent.py')
    result=assess(root,['../../outside','scripts/shortcut.py','tests/test_agent.py'],change_kind='feature')
    assert 'INVALID_PATH' in codes(result)
    assert 'SYMLINK_CHANGED' in codes(result)


def test_bugfix_demands_reproducer_and_canonical_closed_class(tmp_path):
    root=fixture(tmp_path)
    result=assess(root,['cace_studio/ai/agent.py','tests/test_agent.py'],change_kind='bugfix')
    assert 'BUG_FIX_NOT_REGISTERED' in codes(result)
    incident={
        'id':'BUG-101', 'status':'OPEN','summary':'Unexpected result',
        'root_cause':'Unchecked input','reproducer_test':'tests/test_agent.py',
        'sibling_sweep':'Reviewed sibling parsers', 'guarded_class_id':'BUG-101'
    }
    (root/'quality/bug_incidents.json').write_text(json.dumps({'schema_version':1,'incidents':[incident]}))
    result=assess(root,['quality/bug_incidents.json','cace_studio/ai/agent.py','tests/test_agent.py'],change_kind='bugfix')
    assert 'OPEN_BUG' in codes(result)
    incident['status']='GUARDED'
    (root/'quality/bug_incidents.json').write_text(json.dumps({'schema_version':1,'incidents':[incident]}))
    result=assess(root,['quality/bug_incidents.json','cace_studio/ai/agent.py','tests/test_agent.py'],change_kind='bugfix')
    assert 'UNREGISTERED_GUARD' in codes(result)
    (root/'quality/bug_classes.json').write_text(json.dumps({'schema_version':1,'classes':[{'id':'BUG-101','status':'GUARDED'}]}))
    result=assess(root,['quality/bug_classes.json','quality/bug_incidents.json','cace_studio/ai/agent.py','tests/test_agent.py'],change_kind='bugfix')
    assert result['status']=='PASS_STATIC_ONLY'


def test_open_incident_always_blocks_regardless_of_change_kind(tmp_path):
    root=fixture(tmp_path)
    incident={'id':'BUG-1','status':'OPEN','summary':'Known defect','root_cause':'Unknown yet','reproducer_test':'tests/test_agent.py','sibling_sweep':'pending','guarded_class_id':''}
    (root/'quality/bug_incidents.json').write_text(json.dumps({'schema_version':1,'incidents':[incident]}))
    result=assess(root,['docs/intro.md'],change_kind='docs')
    assert 'OPEN_BUG' in codes(result)


def test_runtime_change_with_unrelated_test_file_does_not_suffice(tmp_path):
    root=fixture(tmp_path)
    (root/'tests/test_unrelated.py').write_text('def test_unrelated(): assert True\n')
    result=assess(root,['cace_studio/ai/agent.py','tests/test_unrelated.py'],change_kind='feature')
    assert 'RELATED_TEST_MISSING' in codes(result)


def test_git_changed_file_discovery_includes_worktree_and_untracked(tmp_path):
    root=fixture(tmp_path)
    def git(*args): subprocess.run(['git',*args],cwd=root,check=True,capture_output=True)
    git('init','-q');git('config','user.email','tests@example.invalid');git('config','user.name','Test')
    git('add','.');git('commit','-qm','baseline')
    base=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
    (root/'cace_studio/ai/agent.py').write_text('value = 2\n')
    (root/'tests/test_extra.py').write_text('def test_extra(): pass\n')
    changed=discover_changes(root,base)
    assert 'cace_studio/ai/agent.py' in changed
    assert 'tests/test_extra.py' in changed
    with pytest.raises(GateError): discover_changes(root,'this-ref-is-unavailable')


def test_quick_gate_executes_test_then_bug_sweep_no_shell(tmp_path):
    root=fixture(tmp_path)
    report=assess(root,['cace_studio/ai/agent.py','tests/test_agent.py'],change_kind='feature')
    assert report['status']=='PASS_STATIC_ONLY'
    finished=run_quick_checks(root,report,timeout=30)
    assert finished['status']=='PASS_QUICK_ONLY'
    assert [x['id'] for x in finished['commands']]==['targeted_pytest','existing_bug_sweep']
    assert finished['qualification_status']=='NOT_RUN'


def test_quick_gate_refuses_to_execute_failed_static_check(tmp_path):
    root=fixture(tmp_path)
    (root/'cace_studio/ai/agent.py').write_text('def bad(\n')
    bad=assess(root,['cace_studio/ai/agent.py','tests/test_agent.py'],change_kind='feature')
    with pytest.raises(GateError): run_quick_checks(root,bad)


def test_quick_gate_fails_closed_on_failing_test(tmp_path):
    root=fixture(tmp_path)
    (root/'tests/test_agent.py').write_text('def test_agent(): assert False\n')
    report=assess(root,['cace_studio/ai/agent.py','tests/test_agent.py'],change_kind='feature')
    finished=run_quick_checks(root,report,timeout=30)
    assert finished['status']=='BLOCKED'
    assert 'TARGETED_TEST_FAILED' in codes(finished)


def test_unknown_change_kind_and_targeted_file_cap_fail_closed(tmp_path):
    root=fixture(tmp_path)
    with pytest.raises(GateError): assess(root,['tests/test_agent.py'],change_kind='anything')
    tests=[]
    for i in range(25):
        rel=f'tests/test_agent_{i}.py'
        (root/rel).write_text('def test_x(): pass\n')
        tests.append(rel)
    report=assess(root,['cace_studio/ai/agent.py',*tests,'tests/test_agent.py'],change_kind='feature')
    assert 'TEST_BUDGET_EXCEEDED' in codes(report)


def test_failfast_scope_includes_web_api_mobile_and_native(tmp_path):
    root=fixture(tmp_path)
    for rel in ('web/studio.js','api/index.py','ios_companion/LocalModelService.swift','cpp/src/solver.cpp'):
        p=root/rel
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text('value=1\n')
        result=assess(root,[rel],change_kind='feature')
        assert 'TEST_DELTA_MISSING' in codes(result), rel


def test_unsupported_native_language_gate_is_exposed_not_claimed_as_passed(tmp_path):
    root=fixture(tmp_path)
    p=root/'ios_companion/LocalModelService.swift'
    p.parent.mkdir(exist_ok=True)
    p.write_text('struct Hello {}\n')
    t=root/'tests/test_LocalModelService.py'
    t.write_text('def test_local_model_service(): assert True\n')
    result=assess(root,['ios_companion/LocalModelService.swift','tests/test_LocalModelService.py'],change_kind='feature')
    assert result['status']=='PASS_STATIC_ONLY'
    assert 'swift_build_and_device_tests' in result['outstanding_specialized_gates']
    assert result['qualification_status']=='NOT_RUN'