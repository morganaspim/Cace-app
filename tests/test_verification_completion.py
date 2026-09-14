import pytest

from cace_studio.core.executor import RunResult
from cace_studio.core.report import run_report
from cace_studio.core.types import EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState


@pytest.mark.parametrize("states,expected", [
    ([], False),
    ([VerificationState.NOT_RUN], False),
    ([VerificationState.PASS, VerificationState.NOT_RUN], False),
    ([VerificationState.PASS, VerificationState.FAIL], False),
    ([VerificationState.PASS], True),
])
def test_verification_requires_executed_passing_evidence(states, expected):
    records = [VerificationRecord("check", EvidenceKind.NUMERICAL, "test", state, "test") for state in states]
    result = RunResult("test", {}, [], {"node": records})
    assert result.all_verifiers_passed is expected
    report = run_report(result, "test")
    assert report["all_verifiers_passed"] is expected
    assert report["graph_certificate"]["all_verifiers_passed"] is expected
