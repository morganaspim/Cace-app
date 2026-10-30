"""Host-scoped one-shot read capabilities for advisory M.E.R.L.I.N. data access.

Requires a trusted CACE host to own this object, session rights, input data and
its process boundary. ONLY the opaque single-use token, not this issuer object,
may cross to an untrusted model/tool caller. No shell/network/DB/write APIs.

In-process Python itself is not an isolation boundary; the parent process must
keep this issuer and session authority inaccessible to untrusted code.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from math import isfinite
from secrets import token_urlsafe
from time import monotonic
from typing import Any, Callable, Mapping

from .snapshot_broker import BrokerError, SnapshotBroker


class AccessDenied(ValueError):
    """Authorization, provenance, query or resource gate was not met."""


_ALLOWED_OPS = frozenset({'select', 'count', 'group_count'})
_ALLOWED_KINDS = frozenset({'synthetic', 'reported', 'observed', 'archival'})


def _text(value: Any, label: str, bound: int = 128) -> str:
    if not isinstance(value, str) or not (0 < len(value) <= bound):
        raise AccessDenied(f'{label} must be bounded text')
    if any(ord(c) < 32 for c in value):
        raise AccessDenied(f'{label} contains control characters')
    return value


def _canonical(query: object) -> str:
    try:
        return json.dumps(query, sort_keys=True, separators=(',', ':'),
                          ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError, OverflowError) as exc:
        raise AccessDenied('query is not bounded canonical scalar data') from exc


@dataclass(frozen=True)
class DatasetRight:
    dataset: str
    operations: frozenset[str]
    fields: frozenset[str]
    filter_fields: frozenset[str]
    max_rows: int = 10

    def __post_init__(self) -> None:
        _text(self.dataset, 'dataset')
        if not isinstance(self.operations, frozenset) or not self.operations or not self.operations <= _ALLOWED_OPS:
            raise AccessDenied('invalid fixed dataset operations')
        for group in (self.fields, self.filter_fields):
            if not isinstance(group, frozenset) or len(group) > 64:
                raise AccessDenied('invalid field rights')
            for field in group:
                _text(field, 'field', 64)
        if type(self.max_rows) is not int or not 1 <= self.max_rows <= 256:
            raise AccessDenied('invalid bounded row limit')


@dataclass(frozen=True)
class SourceDescriptor:
    source_id: str
    source_kind: str
    origin_family: str

    def __post_init__(self) -> None:
        _text(self.source_id, 'source id')
        _text(self.origin_family, 'origin family')
        if self.source_kind not in _ALLOWED_KINDS:
            raise AccessDenied('unknown source kind')


@dataclass(frozen=True)
class HostQuery:
    dataset: str
    operation: str
    fields: tuple[str, ...] = ()
    where: Mapping[str, Any] | None = None
    limit: int | None = None


@dataclass(frozen=True)
class AuthorizedObservation:
    source: SourceDescriptor
    snapshot_sha256: str
    query_sha256: str
    operation: str
    value: Any
    status: str = 'ADVISORY_SNAPSHOT_ONLY'
    permission_authority: str = 'TRUSTED_HOST_BOUNDARY_REQUIRED'
    evidence_authority: bool = False
    proof_status: str = 'NOT_RUN'


@dataclass(frozen=True)
class _Issued:
    session_id: str
    dataset: str
    query_json: str
    issued_at: float
    expires_at: float
    snapshot_sha256: str


class HostSnapshotAuthority:
    """Trusted-host-owned issuer/verifier for a narrow in-memory snapshot bus.

    Do not register this object with a local language model. Grants must be
    constructed from real session rights by privileged host code, NOT inferred
    from EngineeringSpec.permissions or a character's claims about authorization.
    """

    def __init__(self, broker: SnapshotBroker, *,
                 rights: Mapping[str, tuple[DatasetRight, ...]],
                 sources: Mapping[str, SourceDescriptor],
                 clock: Callable[[], float] = monotonic,
                 max_pending_per_session: int = 16) -> None:
        if not isinstance(broker, SnapshotBroker) or not callable(clock):
            raise AccessDenied('host broker and clock required')
        if type(max_pending_per_session) is not int or not 1 <= max_pending_per_session <= 64:
            raise AccessDenied('pending query budget invalid')
        self._broker = broker
        self._clock = clock
        self._cap = max_pending_per_session
        self._sources = dict(sources)
        self._rights: dict[str, dict[str, DatasetRight]] = {}
        self._revoked: set[str] = set()
        self._tokens: dict[str, _Issued] = {}
        for dataset, desc in self._sources.items():
            _text(dataset, 'dataset')
            if not isinstance(desc, SourceDescriptor):
                raise AccessDenied('untrusted source descriptor')
            try:
                broker.snapshot_sha256(dataset)
            except BrokerError as exc:
                raise AccessDenied('source descriptor for an unavailable dataset') from exc
        if len(rights) > 256:
            raise AccessDenied('too many sessions')
        for session, grants in rights.items():
            _text(session, 'session')
            if not isinstance(grants, (tuple, list)) or len(grants) > 32:
                raise AccessDenied('invalid session grants')
            mapping: dict[str, DatasetRight] = {}
            for grant in grants:
                if not isinstance(grant, DatasetRight) or grant.dataset not in self._sources:
                    raise AccessDenied('unrecognized dataset right')
                if grant.dataset in mapping:
                    raise AccessDenied('duplicate right per session/dataset')
                # Field references must be in the broker schema, not caller-defined.
                available = broker._fields[grant.dataset]
                if not (grant.fields | grant.filter_fields) <= available:
                    raise AccessDenied('right grants unknown schema fields')
                mapping[grant.dataset] = grant
            self._rights[session] = mapping

    def _now(self) -> float:
        try:
            now = self._clock()
        except Exception as exc:
            raise AccessDenied('host clock unavailable') from exc
        if type(now) not in (int, float) or not isfinite(now):
            raise AccessDenied('host clock invalid')
        return float(now)

    def issue(self, session_id: str, query: HostQuery, *, ttl_seconds: float = 30.0) -> str:
        """PRIVILEGED HOST CALL. Never expose this issuer to model tool schemas."""
        _text(session_id, 'session')
        if not isinstance(query, HostQuery) or session_id in self._revoked:
            raise AccessDenied('invalid or revoked host query')
        if type(ttl_seconds) not in (int, float) or not isfinite(ttl_seconds) or not 0 < ttl_seconds <= 300:
            raise AccessDenied('invalid capability TTL')
        rights = self._rights.get(session_id, {})
        right = rights.get(query.dataset)
        if right is None or type(query.operation) is not str or query.operation not in right.operations:
            raise AccessDenied('no host-issued right for query')
        fields = query.fields
        if not isinstance(fields, tuple) or len(fields) > 64 or any(type(x) is not str for x in fields) or len(fields) != len(set(fields)):
            raise AccessDenied('invalid query fields')
        if any(not isinstance(x, str) for x in fields) or not set(fields) <= right.fields:
            raise AccessDenied('query fields are not permitted')
        if query.operation == 'select' and not fields:
            raise AccessDenied('select needs permitted projected fields')
        if query.operation == 'count' and fields:
            raise AccessDenied('count cannot return projected fields')
        if query.operation == 'group_count' and (len(fields) != 1 or fields[0] not in right.filter_fields):
            raise AccessDenied('group_count requires a host-permitted grouping dimension')
        if query.operation == 'select' and (type(query.limit) is not int or not 1 <= query.limit <= right.max_rows):
            raise AccessDenied('select limit exceeds host policy')
        if query.operation != 'select' and query.limit is not None:
            raise AccessDenied('aggregate query does not support a row limit')
        where = {} if query.where is None else query.where
        if not isinstance(where, Mapping) or len(where) > 16:
            raise AccessDenied('filter requires a bounded mapping')
        if not all(isinstance(k, str) for k in where) or not set(where) <= right.filter_fields:
            raise AccessDenied('filter fields are not permitted')
        try:
            validated = self._broker._check(query.dataset,
                     fields or (next(iter(sorted(self._broker._fields[query.dataset]))),), where)
        except (BrokerError, KeyError, ValueError) as exc:
            raise AccessDenied('invalid bounded broker query') from exc
        payload = {
            'dataset': query.dataset, 'operation': query.operation,
            'fields': list(fields), 'where': validated, 'limit': query.limit,
        }
        data = _canonical(payload)
        if len(data.encode('utf-8')) > 8192:
            raise AccessDenied('query exceeds serialized limit')
        now = self._now()
        outstanding = sum(1 for item in self._tokens.values()
                          if item.session_id == session_id and item.expires_at > now)
        if outstanding >= self._cap:
            raise AccessDenied('too many pending capabilities')
        token = token_urlsafe(32)
        self._tokens[token] = _Issued(session_id, query.dataset, data, now,
                                      now + float(ttl_seconds),
                                      self._broker.snapshot_sha256(query.dataset))
        return token

    def consume(self, session_id: str, token: str) -> AuthorizedObservation:
        _text(session_id, 'session')
        if not isinstance(token, str) or len(token) > 256 or len(token) < 32:
            raise AccessDenied('invalid capability token')
        entry = self._tokens.get(token)
        if entry is None or entry.session_id != session_id or session_id in self._revoked:
            raise AccessDenied('capability unavailable for this session')
        now = self._now()
        if now >= entry.expires_at:
            self._tokens.pop(token, None)
            raise AccessDenied('capability expired')
        # Reserve token before data dispatch to prevent replay and reentrancy.
        self._tokens.pop(token, None)
        if self._broker.snapshot_sha256(entry.dataset) != entry.snapshot_sha256:
            raise AccessDenied('snapshot identity changed')
        query = json.loads(entry.query_json)
        dataset, operation = query['dataset'], query['operation']
        if operation == 'select':
            value = self._broker.select(dataset, tuple(query['fields']),
                                        where=query['where'], limit=query['limit'])
        elif operation == 'count':
            value = self._broker.count(dataset, where=query['where'])
        elif operation == 'group_count':
            value = self._broker.group_count(dataset, query['fields'][0], where=query['where'])
        else:
            raise AccessDenied('stored query operation unsupported')
        return AuthorizedObservation(self._sources[dataset], entry.snapshot_sha256,
                                     sha256(entry.query_json.encode('utf-8')).hexdigest(),
                                     operation, value)

    def revoke_session(self, session_id: str) -> None:
        _text(session_id, 'session')
        self._revoked.add(session_id)
        for token, entry in tuple(self._tokens.items()):
            if entry.session_id == session_id:
                self._tokens.pop(token, None)


def authorized_tool_for_snapshot(authority: HostSnapshotAuthority, *, session_id: str,
                                 token: str, tool_id: str, capability: str, cost: float = .1):
    """Host-created adapter. The token and issue API MUST remain invisible to AI."""
    if not isinstance(authority, HostSnapshotAuthority):
        raise AccessDenied('host-owned authority required')

    def _fixed_query(context: Mapping[str, Any]) -> AuthorizedObservation:
        if not isinstance(context, Mapping) or context:
            raise AccessDenied('model cannot override signed host query')
        return authority.consume(session_id, token)

    from .investigation import Tool
    return Tool(tool_id, capability, 'read_only', cost, _fixed_query,
                required_permission='project_dataset_read')
