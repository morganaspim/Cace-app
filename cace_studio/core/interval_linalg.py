from __future__ import annotations
from cace_studio.core.interval import Interval, singleton, add, sub, mul, div


def det2(a: list[list[Interval]]) -> Interval:
    return sub(mul(a[0][0], a[1][1]), mul(a[0][1], a[1][0]))


def inv2(a: list[list[Interval]]) -> list[list[Interval]]:
    d = det2(a)
    if d.lo <= 0.0 <= d.hi:
        raise ZeroDivisionError("interval determinant contains zero")
    return [
        [div(a[1][1], d), div(Interval(-a[0][1].hi, -a[0][1].lo), d)],
        [div(Interval(-a[1][0].hi, -a[1][0].lo), d), div(a[0][0], d)],
    ]


def transpose2(a: list[list[Interval]]) -> list[list[Interval]]:
    return [[a[0][0], a[1][0]], [a[0][1], a[1][1]]]


def matvec2(a: list[list[Interval]], x: list[Interval]) -> list[Interval]:
    return [add(mul(a[i][0], x[0]), mul(a[i][1], x[1])) for i in range(2)]


def dot2(a: list[Interval], b: list[Interval]) -> Interval:
    return add(mul(a[0], b[0]), mul(a[1], b[1]))
