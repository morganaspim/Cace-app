"""CACE research data: closed, in-memory, bounded read-only snapshot operations.

This broker deliberately has no Python callback, interpreter, filesystem, network,
SQL, arbitrary filter language, or external authorization interface. Data must be
validated/approved by the trusted CACE host. It does NOT sandbox other Python
code, establish truth, verify model output, or guarantee data are non-sensitive.
"""
from __future__ import annotations

import math
import re
from typing import Any, Mapping, Sequence

class BrokerError(ValueError):
    """Invalid data, schema, filter, or bounded query request."""

_IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,63}\Z")


def _identifier(value: str, name: str) -> str:
    if not isinstance(value, str) or _IDENTIFIER.fullmatch(value) is None:
        raise BrokerError(f"invalid {name}: expected simple bounded identifier")
    return value


def _value(value: Any) -> Any:
    if value is None or type(value) is bool:
        return value
    if type(value) is str and len(value) <= 2048 and all(ord(c) >= 32 or c in '\n\t' for c in value):
        return value
    if type(value) is int and abs(value) < 10**18:
        return value
    if type(value) is float and math.isfinite(value):
        return value
    raise BrokerError("only finite, bounded, scalar JSON-like values are supported")


def _matches(row: dict[str, Any], where: Mapping[str, Any]) -> bool:
    return all(type(row.get(k)) is type(v) and row.get(k) == v for k,v in where.items())

class SnapshotBroker:
    """Host-created immutable-snapshot query API. Not an OS-level security boundary."""
    def __init__(self, datasets: Mapping[str, Sequence[Mapping[str, Any]]],
                 schemas: Mapping[str, Sequence[str]], *, max_rows: int = 10000,
                 max_output: int = 256, min_group: int = 3) -> None:
        if any(type(v) is not int for v in (max_rows,max_output,min_group)) or not(1<=max_rows<=100000 and 1<=max_output<=1000 and 1<=min_group<=100):
            raise BrokerError('invalid resource or minimum group limit')
        if not isinstance(datasets, Mapping) or not isinstance(schemas, Mapping) or set(datasets)!=set(schemas):
            raise BrokerError('dataset/schema names must exactly match')
        if len(datasets)>32:
            raise BrokerError('too many datasets')
        self._max_output=max_output
        self._min_group=min_group
        self._fields={}
        self._data={}
        for name,rows in datasets.items():
            _identifier(name,'dataset')
            fields=tuple(schemas[name])
            if not fields or len(fields)>64 or len(set(fields))!=len(fields):
                raise BrokerError('schema must contain distinct permitted fields')
            for f in fields: _identifier(f,'field')
            if not isinstance(rows,(list,tuple)) or len(rows)>max_rows:
                raise BrokerError('dataset must be a bounded list or tuple')
            output=[]
            for row in rows:
                if not isinstance(row,Mapping):
                    raise BrokerError('records must be mappings')
                if any(k not in fields for k in row):
                    raise BrokerError('unexpected record field')
                output.append({field:_value(v) for field,v in row.items()})
            self._data[name]=tuple(output)
            self._fields[name]=frozenset(fields)

    def _check(self,dataset:str,fields: Sequence[str],where:Mapping[str, Any]|None):
        _identifier(dataset,'dataset')
        if dataset not in self._data: raise BrokerError('unknown dataset')
        if not isinstance(fields,(list,tuple)) or not fields or len(set(fields))!=len(fields):
            raise BrokerError('select at least one distinct field')
        for field in fields:
            _identifier(field,'field')
            if field not in self._fields[dataset]: raise BrokerError('field not permitted')
        if where is None: where={}
        if not isinstance(where,Mapping) or len(where)>32: raise BrokerError('filter must be a bounded mapping')
        checked={}
        for field,value in where.items():
            _identifier(field,'filter field')
            if field not in self._fields[dataset]: raise BrokerError('filter field not permitted')
            checked[field]=_value(value)
        return checked

    def select(self,dataset:str,fields:Sequence[str],*,where:Mapping[str,Any]|None=None,limit:int|None=None)->list[dict[str,Any]]:
        checked=self._check(dataset,fields,where)
        if limit is None:limit=self._max_output
        if type(limit) is not int or not 1<=limit<=self._max_output:raise BrokerError('invalid output limit')
        result=[]
        for row in self._data[dataset]:
            if _matches(row,checked):
                result.append({f:row.get(f) for f in fields})
                if len(result)>=limit:break
        return result

    def count(self,dataset:str,*,where:Mapping[str,Any]|None=None)->int:
        checked=self._check(dataset,(next(iter(sorted(self._fields.get(dataset,()))),'missing'),),where)
        return sum(_matches(row,checked) for row in self._data[dataset])

    def group_count(self,dataset:str,field:str,*,where:Mapping[str,Any]|None=None)->dict[Any,int]:
        checked=self._check(dataset,(field,),where)
        counts={}
        for row in self._data[dataset]:
            if _matches(row,checked):
                key=row.get(field)
                counts[key]=counts.get(key,0)+1
        return {k:v for k,v in sorted(counts.items(),key=lambda kv:(type(kv[0]).__name__,str(kv[0]))) if v>=self._min_group}


def tool_for_snapshot(broker: SnapshotBroker, *, dataset: str, operation: str,
                      tool_id: str, capability: str, fields: Sequence[str] = (),
                      cost: float = 0.1):
    """Construct a fixed-scope advisory Tool from a trusted in-memory snapshot.

    This is a host binding, not model authorization. Tool contents remain
    unverified source observations; access to the host's datasets must itself
    be authorized separately. No dynamic Python callbacks are accepted here.
    """
    if not isinstance(broker, SnapshotBroker):
        raise BrokerError('expected host-created SnapshotBroker')
    if operation not in {'count', 'select', 'group_count'}:
        raise BrokerError('unsupported snapshot operation')
    if operation == 'select':
        if not fields:
            raise BrokerError('select needs fixed output fields')
        fixed_fields = tuple(fields)
    elif operation == 'group_count':
        if len(fields) != 1:
            raise BrokerError('group_count needs one fixed group field')
        fixed_fields = tuple(fields)
    else:
        if fields:
            raise BrokerError('count does not accept selected fields')
        fixed_fields = ()
    # Validate requested operation and schema without reading or exposing records.
    validation_field = fixed_fields or (next(iter(sorted(broker._fields.get(dataset, ()))), 'missing'),)
    broker._check(dataset, validation_field, {})

    def _perform(request: Mapping[str, Any]):
        if not isinstance(request, Mapping) or set(request) - {'where'}:
            raise BrokerError('only the fixed snapshot operation and equality where are permitted')
        where = request.get('where')
        if operation == 'count':
            return broker.count(dataset, where=where)
        if operation == 'select':
            return broker.select(dataset, fixed_fields, where=where)
        return broker.group_count(dataset, fixed_fields[0], where=where)

    from .investigation import Tool
    return Tool(tool_id, capability, 'read_only', cost, _perform,
                required_permission='project_dataset_read')
