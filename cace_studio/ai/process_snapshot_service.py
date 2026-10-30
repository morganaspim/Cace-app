"""M.E.R.L.I.N. restricted research queries in an independent worker process.

Engineering prototype, NOT a full OS sandbox or a production authentication
service.  A PRIVILEGED CACE HOST must provide a genuine authentication callback,
owner-approved data/rights, and keep this whole service outside untrusted model
context; only a narrow query-result interface may be exposed. No network or
arbitrary Python tool operations are dispatched by this worker.

All response data are research metadata.  No proof, sensor, privacy or formal
verification status can be promoted by this service.
"""
from __future__ import annotations

from dataclasses import asdict
from math import isfinite
import json
import multiprocessing as mp
from multiprocessing.connection import Connection
import os
import threading
from typing import Any, Callable, Mapping, Sequence

from .host_snapshot_authority import (
    AccessDenied, AuthorizedObservation, DatasetRight, HostQuery,
    HostSnapshotAuthority, SourceDescriptor,
)
from .snapshot_broker import BrokerError, SnapshotBroker


class ServiceDenied(ValueError):
    """A request did not meet a defined host-owned policy."""


class ServiceUnavailable(RuntimeError):
    """The separate data worker could not safely complete the request."""


_MAX_REQUEST = 8192
_MAX_RESPONSE = 2_000_000


def _json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def _decode(data: bytes) -> Any:
    return json.loads(data, parse_constant=lambda _: (_ for _ in ()).throw(ValueError('invalid number')))


def _typed_key(value: Any) -> dict[str, Any]:
    if value is None:
        return {'type': 'null'}
    if type(value) is bool:
        return {'type': 'bool', 'value': value}
    if type(value) is int:
        return {'type': 'int', 'value': value}
    if type(value) is float and isfinite(value):
        return {'type': 'float', 'value': value}
    if type(value) is str:
        return {'type': 'str', 'value': value}
    raise ServiceDenied('unsupported grouped scalar')


def _restore_key(spec: Any) -> Any:
    if not isinstance(spec, dict) or set(spec) - {'type', 'value'}:
        raise ServiceUnavailable('invalid worker aggregate')
    typ = spec.get('type')
    if typ == 'null' and 'value' not in spec:
        return None
    target = {'bool': bool, 'int': int, 'float': float, 'str': str}.get(typ)
    if target is None or type(spec.get('value')) is not target:
        raise ServiceUnavailable('invalid worker scalar')
    return spec['value']


def _pack_observation(obs: AuthorizedObservation) -> dict[str, Any]:
    data = asdict(obs)
    if obs.operation == 'group_count':
        data['value'] = {'typed_groups': [
            [_typed_key(key), number] for key, number in obs.value.items()
        ]}
    return data


def _unpack_observation(data: Any) -> AuthorizedObservation:
    if not isinstance(data, dict):
        raise ServiceUnavailable('invalid worker observation')
    expected = {'source','snapshot_sha256','query_sha256','operation','value',
                'status','permission_authority','evidence_authority','proof_status'}
    if set(data) != expected or data.get('status') != 'ADVISORY_SNAPSHOT_ONLY' or data.get('evidence_authority') is not False or data.get('proof_status') != 'NOT_RUN':
        raise ServiceUnavailable('observation authority mismatch')
    operation = data['operation']
    if operation not in {'select', 'count', 'group_count'}:
        raise ServiceUnavailable('unknown observation operation')
    value = data['value']
    if operation == 'group_count':
        if not isinstance(value, dict) or set(value) != {'typed_groups'} or not isinstance(value['typed_groups'], list):
            raise ServiceUnavailable('invalid group response')
        grouped = {}
        for item in value['typed_groups']:
            if not isinstance(item, list) or len(item) != 2 or type(item[1]) is not int or item[1] < 0:
                raise ServiceUnavailable('invalid group entry')
            k = _restore_key(item[0])
            if k in grouped:
                raise ServiceUnavailable('duplicate group key')
            grouped[k] = item[1]
        value = grouped
    if not isinstance(data['source'], dict):
        raise ServiceUnavailable('source descriptor missing')
    return AuthorizedObservation(
        SourceDescriptor(**data['source']), data['snapshot_sha256'],
        data['query_sha256'], operation, value,
        status=data['status'], permission_authority=data['permission_authority'],
        evidence_authority=data['evidence_authority'], proof_status=data['proof_status'],
    )


def _worker(conn: Connection, datasets: Mapping[str, Sequence[Mapping[str, Any]]],
            schemas: Mapping[str, Sequence[str]], rights: Mapping[str, tuple[DatasetRight, ...]],
            sources: Mapping[str, SourceDescriptor],
            required_where: Mapping[str, Mapping[str, Mapping[str, Any]]],
            max_aggregate_issues_per_session: int) -> None:
    """Worker receives only fixed, JSON-framed commands from its trusted parent."""
    try:
        broker = SnapshotBroker(datasets, schemas, max_output=256)
        authority = HostSnapshotAuthority(broker, rights=rights, sources=sources)
        # A missing or malformed owner scope must never silently grant access.
        if not isinstance(required_where, Mapping):
            raise ServiceDenied('malformed host row policy')
        scoped: dict[str, dict[str, dict[str, Any]]] = {}
        for session, datasets_scope in required_where.items():
            if session not in rights or not isinstance(datasets_scope, Mapping):
                raise ServiceDenied('malformed session scope')
            scoped[session] = {}
            for dataset, condition in datasets_scope.items():
                if dataset not in broker._fields or not isinstance(condition, Mapping) or not condition:
                    raise ServiceDenied('malformed dataset scope')
                grant = next((g for g in rights[session] if g.dataset == dataset), None)
                if grant is None or not set(condition) <= grant.filter_fields:
                    raise ServiceDenied('scope not included in host rights')
                field = next(iter(sorted(broker._fields[dataset])))
                validated = broker._check(dataset, (field,), condition)
                scoped[session][dataset] = validated
        aggregate_issues: dict[str,int] = {}
        while True:
            try:
                packet = conn.recv_bytes(_MAX_REQUEST)
            except (EOFError, OSError):
                break
            try:
                request = _decode(packet)
                if not isinstance(request, dict) or not isinstance(request.get('kind'), str):
                    raise ServiceDenied('unsupported request')
                kind = request['kind']
                if kind == 'stop' and set(request) == {'kind'}:
                    conn.send_bytes(_json({'status':'OK'}))
                    break
                if kind == 'issue' and set(request) == {'kind','session','query','ttl'}:
                    query = request['query']
                    if not isinstance(query, dict) or set(query) != {'dataset','operation','fields','where','limit'}:
                        raise ServiceDenied('invalid query fields')
                    fields = query['fields']
                    q = HostQuery(query['dataset'], query['operation'],
                                  tuple(fields) if isinstance(fields, list) else fields,
                                  query['where'], query['limit'])
                    required = scoped.get(request['session'], {}).get(q.dataset)
                    if required is not None:
                        where = q.where
                        if not isinstance(where, Mapping) or not all(
                            key in where and type(where[key]) is type(value) and where[key] == value
                            for key, value in required.items()
                        ):
                            raise ServiceDenied('query violates immutable row scope')
                    is_aggregate = q.operation in {'count', 'group_count'}
                    used = aggregate_issues.get(request['session'], 0)
                    if is_aggregate and used >= max_aggregate_issues_per_session:
                        raise ServiceDenied('host aggregate query budget exhausted')
                    issued = authority.issue(request['session'], q, ttl_seconds=request['ttl'])
                    if is_aggregate:
                        aggregate_issues[request['session']] = used + 1
                    result = {'status':'OK','token':issued}
                elif kind == 'consume' and set(request) == {'kind','session','token'}:
                    obs = authority.consume(request['session'], request['token'])
                    result = {'status':'OK', 'observation':_pack_observation(obs)}
                elif kind == 'revoke' and set(request) == {'kind','session'}:
                    authority.revoke_session(request['session'])
                    result = {'status':'OK'}
                else:
                    raise ServiceDenied('unregistered worker request')
                response = _json(result)
                if len(response) > _MAX_RESPONSE:
                    raise ServiceDenied('result exceeds IPC output size limit')
            except (AccessDenied, BrokerError, ServiceDenied, ValueError, KeyError, TypeError, OverflowError, UnicodeError):
                # Never echo raw credentials, token, query or dataset names in error output.
                response = _json({'status':'DENIED'})
            except Exception:
                # Host may collect internal diagnostics outside model-visible response.
                response = _json({'status':'UNAVAILABLE'})
            try:
                conn.send_bytes(response)
            except (BrokenPipeError, EOFError, OSError):
                break
    finally:
        conn.close()


class ProcessSnapshotService:
    """Host-only authenticated façade for an independent process owning snapshots.

    authenticate(credential)->approved session id is an integration point to
    *existing* authenticated account/service state. A fake callback used in tests
    does NOT mean an actual CACE identity provider has been connected.

    The service/issuer must not be exposed to untrusted AI code or prompt tools.
    This process separation does NOT apply OS seccomp, sandbox profiles, ulimits,
    user-namespace restrictions or verified encryption of parent-held inputs.
    """

    def __init__(self, datasets: Mapping[str, Sequence[Mapping[str, Any]]],
                 schemas: Mapping[str, Sequence[str]],
                 rights: Mapping[str, tuple[DatasetRight, ...]],
                 sources: Mapping[str, SourceDescriptor], *,
                 authenticate: Callable[[str], str | None], timeout: float = 5.0,
                 required_where: Mapping[str, Mapping[str, Mapping[str, Any]]] | None = None,
                 max_aggregate_issues_per_session: int = 8) -> None:
        if not callable(authenticate):
            raise ValueError('trusted credential resolver is required')
        if type(timeout) not in (int, float) or not isfinite(timeout) or not 0.1 <= timeout <= 30:
            raise ValueError('timeout must be 0.1 to 30 seconds')
        if type(max_aggregate_issues_per_session) is not int or not 1 <= max_aggregate_issues_per_session <= 100:
            raise ValueError('aggregate issue budget must be from 1 to 100')
        if required_where is not None and not isinstance(required_where, Mapping):
            raise ValueError('host row-scope registry must be a mapping')
        self._authenticate = authenticate
        self._timeout = float(timeout)
        self._lock = threading.RLock()
        self._closed = False
        ctx = mp.get_context('spawn')
        self._conn, child = ctx.Pipe(duplex=True)
        self._proc = ctx.Process(target=_worker,
                                 args=(child,datasets,schemas,rights,sources,
                                       required_where if required_where is not None else {},
                                       max_aggregate_issues_per_session),
                                 daemon=True, name='cace-research-snapshot-worker')
        try:
            self._proc.start()
        except BaseException:
            self._conn.close()
            child.close()
            self._closed = True
            raise
        child.close()

    @property
    def worker_pid(self) -> int:
        return int(self._proc.pid or 0)

    def _session(self, credential: str) -> str:
        if not isinstance(credential, str) or not credential or len(credential) > 4096:
            raise ServiceDenied('not authorized')
        try:
            session = self._authenticate(credential)
        except Exception:
            raise ServiceDenied('not authorized') from None
        if not isinstance(session,str) or not (0 < len(session) <= 128) or any(ord(c)<32 for c in session):
            raise ServiceDenied('not authorized')
        return session

    def _rpc(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            if self._closed or not self._proc.is_alive():
                raise ServiceUnavailable('research worker is not available')
            try:
                packet = _json(payload)
                if len(packet) > _MAX_REQUEST:
                    raise ServiceDenied('query exceeds request budget')
                self._conn.send_bytes(packet)
                if not self._conn.poll(self._timeout):
                    self._proc.terminate()
                    self._proc.join(timeout=1)
                    self._closed=True
                    raise ServiceUnavailable('research worker timed out and was terminated')
                response = _decode(self._conn.recv_bytes(_MAX_RESPONSE))
            except ServiceDenied:
                raise
            except ServiceUnavailable:
                raise
            except (EOFError, OSError, BufferError, TypeError, ValueError, OverflowError, UnicodeError):
                raise ServiceUnavailable('research IPC unavailable') from None
            if not isinstance(response, dict) or response.get('status') != 'OK':
                if isinstance(response,dict) and response.get('status') == 'DENIED':
                    raise ServiceDenied('research request denied')
                raise ServiceUnavailable('research operation failed')
            return response

    def issue(self, credential: str, query: HostQuery, *, ttl_seconds: float = 30.0) -> str:
        session = self._session(credential)
        if not isinstance(query, HostQuery):
            raise ServiceDenied('fixed host query required')
        return self._rpc({'kind':'issue', 'session':session, 'query':{
            'dataset':query.dataset, 'operation':query.operation,
            'fields':query.fields, 'where':query.where, 'limit':query.limit},
            'ttl':ttl_seconds})['token']

    def consume(self, credential: str, token: str) -> AuthorizedObservation:
        session = self._session(credential)
        result = self._rpc({'kind':'consume', 'session':session, 'token':token})
        return _unpack_observation(result['observation'])

    def revoke_session(self, session_id: str) -> None:
        """Privileged host-only revocation; not exposed on model tool bus."""
        self._rpc({'kind':'revoke', 'session':session_id})

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            if self._proc.is_alive():
                try:
                    self._conn.send_bytes(_json({'kind':'stop'}))
                    if self._conn.poll(min(self._timeout,1.0)):
                        self._conn.recv_bytes(256)
                except (OSError, EOFError, ValueError):
                    pass
                self._proc.join(timeout=1)
            if self._proc.is_alive():
                self._proc.terminate()
                self._proc.join(timeout=1)
            self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False
