from __future__ import annotations
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class Interval:
    lo: float
    hi: float
    def __post_init__(self):
        if math.isnan(self.lo) or math.isnan(self.hi) or self.lo > self.hi:
            raise ValueError("invalid interval")
    def to_list(self): return [self.lo, self.hi]

def down(x: float) -> float: return math.nextafter(float(x), -math.inf)
def up(x: float) -> float: return math.nextafter(float(x), math.inf)
def singleton(x: float) -> Interval: return Interval(float(x), float(x))

def add(a: Interval,b: Interval)->Interval:
    return Interval(down(a.lo+b.lo),up(a.hi+b.hi))

def neg(a: Interval)->Interval:
    return Interval(-a.hi,-a.lo)

def sub(a: Interval,b: Interval)->Interval:
    return add(a,neg(b))

def mul(a: Interval,b: Interval)->Interval:
    ps=(a.lo*b.lo,a.lo*b.hi,a.hi*b.lo,a.hi*b.hi)
    return Interval(down(min(ps)),up(max(ps)))

def abs_interval(a: Interval)->Interval:
    if a.lo <= 0.0 <= a.hi:
        return Interval(0.0,up(max(abs(a.lo),abs(a.hi))))
    return Interval(down(min(abs(a.lo),abs(a.hi))),up(max(abs(a.lo),abs(a.hi))))

def square(a: Interval) -> Interval:
    if a.lo <= 0.0 <= a.hi:
        high = max(a.lo*a.lo, a.hi*a.hi)
        return Interval(0.0, up(high))
    p1, p2 = a.lo*a.lo, a.hi*a.hi
    return Interval(down(min(p1,p2)), up(max(p1,p2)))

def sqrt_interval(a: Interval)->Interval:
    if a.lo < 0: raise ValueError('sqrt interval requires nonnegative lower bound')
    return Interval(0.0 if a.lo == 0.0 else down(math.sqrt(a.lo)),up(math.sqrt(a.hi)))

def sum_intervals(items)->Interval:
    out=Interval(0.0,0.0)
    for x in items: out=add(out,x)
    return out


def div(a: Interval,b: Interval)->Interval:
    if b.lo <= 0.0 <= b.hi:
        raise ZeroDivisionError('interval divisor contains zero')
    qs=(a.lo/b.lo,a.lo/b.hi,a.hi/b.lo,a.hi/b.hi)
    return Interval(down(min(qs)),up(max(qs)))

def cube(a: Interval)->Interval:
    # monotone on R
    return Interval(down(a.lo*a.lo*a.lo),up(a.hi*a.hi*a.hi))
