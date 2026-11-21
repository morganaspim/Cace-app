"""Merlin Python subsystem package; share imports with repository-level modules."""
from pathlib import Path

_here = Path(__file__).resolve().parent
_other = _here.parent.parent / "merlin"
if _other.is_dir() and str(_other) not in __path__:
    __path__.append(str(_other))
