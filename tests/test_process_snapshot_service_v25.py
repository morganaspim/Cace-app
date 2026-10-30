"""RED before GREEN: authenticated, process-owned CACE research snapshot gate."""
from __future__ import annotations
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from cace_studio.ai.process_snapshot_service import (
    ProcessSnapshotService, ServiceDenied, ServiceUnavailable,
)
from cace_studio.ai.host_snapshot_authority import DatasetRight, HostQuery, SourceDescriptor


@pytest.fixture
def service():
    accounts = {"credential-one": "session-1", "credential-two": "session-2"}
    datasets = {"records": [
        {"tag": "safe", "value": 10, "record": "a"},
        {"tag": "safe", "value": 11, "record": "b"},
        {"tag": "restricted", "value": 99, "record": "c"},
    ]}
    schemas = {"records": ("tag", "value", "record")}
    rights = {"session-1": (DatasetRight(
        "records", frozenset({"select", "count"}),
        frozenset({"tag", "value"}), frozenset({"tag"}), 2
    ),), "session-2": ()}
    sources = {"records": SourceDescriptor("toy-dataset", "synthetic", "toy-source")}
    with ProcessSnapshotService(datasets, schemas, rights, sources,
                                authenticate=lambda credential: accounts.get(credential),
                                timeout=5) as s:
        yield s, accounts


def test_broker_runs_in_different_process_and_not_just_callback(service):
    s, _ = service
    assert s.worker_pid != os.getpid()
    assert s.worker_pid > 0
    assert not hasattr(s, 'run_python')
    assert not hasattr(s, 'execute_shell')


def test_credential_authentication_and_host_scoped_field_gate(service):
    s, _ = service
    q = HostQuery('records', 'select', ('value',), {'tag': 'safe'}, 2)
    token = s.issue('credential-one', q)
    result = s.consume('credential-one', token)
    assert result.value == [{'value': 10}, {'value': 11}]
    assert result.source.source_kind == 'synthetic'
    assert result.evidence_authority is False
    assert result.proof_status == 'NOT_RUN'
    assert len(result.snapshot_sha256) == 64
    assert len(result.query_sha256) == 64


def test_unknown_credentials_and_no_rights_fail_closed(service):
    s, _ = service
    q = HostQuery('records', 'count', where={'tag': 'safe'})
    for credential in ('unknown', 'credential-two'):
        with pytest.raises(ServiceDenied): s.issue(credential, q)
    with pytest.raises(ServiceDenied): s.issue('', q)


def test_token_replay_and_cross_session_binding(service):
    s, _ = service
    q = HostQuery('records', 'count', where={'tag': 'safe'})
    token = s.issue('credential-one', q)
    with pytest.raises(ServiceDenied): s.consume('credential-two', token)
    assert s.consume('credential-one', token).value == 2
    with pytest.raises(ServiceDenied): s.consume('credential-one', token)


def test_authentication_revocation_even_when_worker_token_exists(service):
    s, accounts = service
    token = s.issue('credential-one', HostQuery('records', 'count'))
    accounts.pop('credential-one')
    with pytest.raises(ServiceDenied): s.consume('credential-one', token)
    # Service owner can still explicitly revoke the worker-session token.
    s.revoke_session('session-1')


def test_worker_side_session_revocation(service):
    s, _ = service
    q = HostQuery('records', 'count')
    token = s.issue('credential-one', q)
    s.revoke_session('session-1')
    with pytest.raises(ServiceDenied): s.consume('credential-one', token)
    with pytest.raises(ServiceDenied): s.issue('credential-one', q)


def test_query_privilege_escalation_and_malformed_filter_fail(service):
    s, _ = service
    forbidden = (
        HostQuery('records','select',('record',),{'tag':'safe'},1),
        HostQuery('records','select',('value',),{'record':'c'},1),
        HostQuery('records','select',('value',),[],1),
        HostQuery('records','select',('value',),{'tag':'safe'},3),
        HostQuery('records','group_count',('tag',)),
    )
    for q in forbidden:
        with pytest.raises(ServiceDenied): s.issue('credential-one',q)


def test_concurrent_token_consume_is_at_most_once(service):
    s, _ = service
    token = s.issue('credential-one', HostQuery('records', 'count'))
    barrier = threading.Barrier(5)
    def work(_):
        barrier.wait()
        try:
            return s.consume('credential-one', token).value
        except ServiceDenied:
            return 'DENIED'
    with ThreadPoolExecutor(max_workers=5) as pool:
        outcomes=list(pool.map(work, range(5)))
    assert outcomes.count(3)==1
    assert outcomes.count('DENIED')==4


def test_invalid_worker_rpc_request_cannot_run_unregistered_operations(service):
    s, _ = service
    with pytest.raises(ServiceDenied): s._rpc({'kind':'exec','python':'print(123)'})
    with pytest.raises(ServiceDenied): s._rpc({'kind':'read_file','path':'/etc/passwd'})


def test_request_response_error_does_not_echo_secret_query(service):
    s, _ = service
    needle='DO_NOT_ECHO_SECRET_93fd9fa2'
    with pytest.raises(ServiceDenied) as exc:
        s.issue('credential-one',HostQuery('records','select',('value',),{'tag':needle},9))
    assert needle not in str(exc.value)


def test_worker_killed_causes_explicit_unavailable_not_pass(service):
    s,_=service
    s._proc.terminate();s._proc.join(timeout=2)
    with pytest.raises(ServiceUnavailable):
        s.issue('credential-one',HostQuery('records','count'))


def test_close_is_idempotent_and_denies_future_work(service):
    s,_=service
    s.close();s.close()
    with pytest.raises(ServiceUnavailable):
        s.issue('credential-one',HostQuery('records','count'))


def test_short_ttl_expires_in_child(service):
    s,_=service
    token=s.issue('credential-one',HostQuery('records','count'),ttl_seconds=.03)
    time.sleep(.09)
    with pytest.raises(ServiceDenied):s.consume('credential-one',token)


def test_response_has_no_authority_to_promote_proof(service):
    s,_=service
    obs=s.consume('credential-one',s.issue('credential-one',HostQuery('records','count')))
    assert obs.status=='ADVISORY_SNAPSHOT_ONLY'
    assert obs.permission_authority=='TRUSTED_HOST_BOUNDARY_REQUIRED'
    assert obs.evidence_authority is False
    assert obs.proof_status=='NOT_RUN'


def test_host_required_row_scope_is_not_removable():
    data={'records':[{'owner':'session-1','value':3}, {'owner':'session-2','value':900}]}
    rights={'session-1':(DatasetRight('records',frozenset({'select','count'}),
            frozenset({'value'}),frozenset({'owner'}),2),)}
    with ProcessSnapshotService(data,{'records':('owner','value')},rights,
       {'records':SourceDescriptor('test','synthetic','independent')},
       authenticate=lambda cred: 'session-1' if cred=='good' else None,
       required_where={'session-1': {'records': {'owner':'session-1'}}},timeout=4) as s:
        for query in (HostQuery('records','count'),
                      HostQuery('records','count',where={'owner':'session-2'}),
                      HostQuery('records','select',('value',),where={},limit=2)):
            with pytest.raises(ServiceDenied): s.issue('good',query)
        q=HostQuery('records','select',('value',),{'owner':'session-1'},2)
        assert s.consume('good',s.issue('good',q)).value==[{'value':3}]


def test_host_bounds_aggregate_differencing_requests():
    data={'records':[{'tag':'a'},{'tag':'b'}]}
    rights={'session-1':(DatasetRight('records',frozenset({'count'}),
            frozenset(),frozenset({'tag'}),1),)}
    with ProcessSnapshotService(data, {'records':('tag',)},rights,
       {'records':SourceDescriptor('toy','synthetic','demo')},
       authenticate=lambda key: 'session-1' if key=='ok' else None,
       max_aggregate_issues_per_session=2,timeout=4) as s:
        q1=HostQuery('records','count',where={'tag':'a'})
        q2=HostQuery('records','count',where={'tag':'b'})
        assert s.consume('ok',s.issue('ok',q1)).value==1
        assert s.consume('ok',s.issue('ok',q2)).value==1
        with pytest.raises(ServiceDenied):s.issue('ok',q1)


def test_malformed_host_row_scope_fails_closed():
    data={'records':[{'owner':'a'}]}
    rights={'session-1':(DatasetRight('records',frozenset({'count'}),
            frozenset(),frozenset({'owner'}),1),)}
    with ProcessSnapshotService(data,{'records':('owner',)},rights,
       {'records':SourceDescriptor('toy','synthetic','demo')},
       authenticate=lambda k: 'session-1' if k=='ok' else None,
       required_where={'session-1': {'records': {'non_schema':'bad'}}},timeout=4) as s:
        with pytest.raises((ServiceDenied,ServiceUnavailable)):
            s.issue('ok',HostQuery('records','count',where={'owner':'a'}))


def test_group_count_typed_scalar_keys_are_not_conflated():
    data={'d':[{'k':True},{'k':True},{'k':True},{'k':None},{'k':None},{'k':None}]}
    rights={'s':(DatasetRight('d',frozenset({'group_count'}),
            frozenset({'k'}),frozenset({'k'}),1),)}
    with ProcessSnapshotService(data,{'d':('k',)},rights,
       {'d':SourceDescriptor('toy','synthetic','demo')},
       authenticate=lambda k: 's' if k=='ok' else None,timeout=4) as s:
        v=s.consume('ok',s.issue('ok',HostQuery('d','group_count',('k',)))).value
        assert v[True]==3
        assert v[None]==3


def test_raw_ipc_cannot_self_assert_approved_session(service):
    s, _ = service
    forged = {'kind':'issue', 'session':'session-1', 'query':{
        'dataset':'records','operation':'count','fields':(), 'where':{}, 'limit':None
    }, 'ttl':30}
    with pytest.raises(ServiceDenied):
        s._rpc(forged)
    with pytest.raises(ServiceDenied):
        s._rpc({'kind':'revoke', 'session':'session-1'})
    # Failed forging did not revoke real host session.
    assert s.consume('credential-one',s.issue('credential-one',
             HostQuery('records','count'))).value == 3
