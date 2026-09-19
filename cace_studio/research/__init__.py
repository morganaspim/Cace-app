"""Research-navigation objects.

These objects organize hypotheses and research questions. They are outside the
formal/scientific evidence trusted base unless downstream CACE verifiers produce
independent evidence.
"""
from .open_problems import (
    ALLOWED_PROBLEM_STATUSES,
    OpenProblem,
    OpenProblemCatalog,
    default_open_problem_catalog,
)

__all__ = [
    "ALLOWED_PROBLEM_STATUSES",
    "OpenProblem",
    "OpenProblemCatalog",
    "default_open_problem_catalog",
]
