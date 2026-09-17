from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Iterable

from .claim_registry import ClaimRegistry
from .proof_ledger import ProofLedger


PROVENANCE_ONLY_PATHS = frozenset(
    {
        "cace_studio/data/claim_registry.json",
        "cace_studio/data/proof_ledger.json",
    }
)

QUALIFICATION_SENSITIVE_EXACT_PATHS = frozenset(
    {
        "cace_studio/app.py",
        "cace_studio/modules/__init__.py",
        "pyproject.toml",
        "schema/claim.schema.json",
        "schema/proof-ledger.schema.json",
        "scripts/check_qualification_drift.py",
        "scripts/verify_continuum_qualification_bundle.py",
        "tests/test_claim_promotion_v330.py",
        "tests/test_claim_registry_v331.py",
        "tests/test_independent_qualification_verifier_v338.py",
        "tests/test_qualification_drift_v331.py",
        ".github/workflows/cace-formal-v330.yml",
    }
)

QUALIFICATION_SENSITIVE_PREFIXES = (
    "formal/",
    "cace_studio/core/",
)

QUALIFICATION_SENSITIVE_MODULE_PREFIX = "cace_studio/modules/formal"


@dataclass(frozen=True)
class QualificationDriftResult:
    claim_id: str
    attested_commit: str
    changed_paths: tuple[str, ...]
    sensitive_paths: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.sensitive_paths

    def to_dict(self) -> dict[str, object]:
        return {
            "claim_id": self.claim_id,
            "attested_commit": self.attested_commit,
            "changed_paths": list(self.changed_paths),
            "sensitive_paths": list(self.sensitive_paths),
            "passed": self.passed,
        }


def is_qualification_sensitive(path: str) -> bool:
    path = path.replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    path = path.lstrip("/")
    if path in PROVENANCE_ONLY_PATHS:
        return False
    if path in QUALIFICATION_SENSITIVE_EXACT_PATHS:
        return True
    if path.startswith(QUALIFICATION_SENSITIVE_PREFIXES):
        return True
    if path.startswith(QUALIFICATION_SENSITIVE_MODULE_PREFIX):
        return True
    return False


def classify_qualification_sensitive(paths: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({p for p in paths if is_qualification_sensitive(p)}))


def _git(repo_root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _git_lines(repo_root: Path, *args: str) -> tuple[str, ...]:
    result = _git(repo_root, *args)
    return tuple(line.strip() for line in result.stdout.splitlines() if line.strip())


def _changed_paths(repo_root: Path, attested_commit: str, head: str) -> tuple[str, ...]:
    ancestor = _git(repo_root, "merge-base", "--is-ancestor", attested_commit, head, check=False)
    if ancestor.returncode != 0:
        raise RuntimeError(
            f"attested commit {attested_commit} is not an ancestor of {head}; "
            "qualification cannot be inherited"
        )

    committed = _git_lines(
        repo_root,
        "diff",
        "--name-only",
        "--diff-filter=ACMRTUXB",
        f"{attested_commit}..{head}",
        "--",
    )
    working = _git_lines(
        repo_root,
        "diff",
        "--name-only",
        "--diff-filter=ACMRTUXB",
        head,
        "--",
    )
    return tuple(sorted(set(committed) | set(working)))


def audit_current_qualifications(
    repo_root: str | Path = ".",
    *,
    head: str = "HEAD",
    registry: ClaimRegistry | None = None,
    ledger: ProofLedger | None = None,
) -> tuple[QualificationDriftResult, ...]:
    root = Path(repo_root).resolve()
    reg = registry or ClaimRegistry.load_default()
    proof_ledger = ledger or ProofLedger.load_default()
    results: list[QualificationDriftResult] = []

    for claim in reg.claims:
        if not claim.current_head_qualified:
            continue

        ledger_entry = proof_ledger.for_claim(claim.claim_id)
        if ledger_entry is None:
            raise RuntimeError(f"{claim.claim_id}: missing proof-ledger entry")
        if not ledger_entry.current_head_qualified:
            raise RuntimeError(
                f"{claim.claim_id}: claim is current-head qualified but proof ledger is not"
            )
        if claim.attested_commit != ledger_entry.commit:
            raise RuntimeError(
                f"{claim.claim_id}: claim/ledger attested commit mismatch"
            )
        if claim.proof_artifact_sha256 != ledger_entry.proof_artifact_sha256:
            raise RuntimeError(
                f"{claim.claim_id}: claim/ledger proof artifact mismatch"
            )
        if claim.attested_commit is None:
            raise RuntimeError(f"{claim.claim_id}: missing attested commit")

        changed = _changed_paths(root, claim.attested_commit, head)
        sensitive = classify_qualification_sensitive(changed)
        results.append(
            QualificationDriftResult(
                claim_id=claim.claim_id,
                attested_commit=claim.attested_commit,
                changed_paths=changed,
                sensitive_paths=sensitive,
            )
        )

    return tuple(results)


def assert_no_qualification_drift(
    repo_root: str | Path = ".",
    *,
    head: str = "HEAD",
    registry: ClaimRegistry | None = None,
    ledger: ProofLedger | None = None,
) -> tuple[QualificationDriftResult, ...]:
    results = audit_current_qualifications(
        repo_root,
        head=head,
        registry=registry,
        ledger=ledger,
    )
    failures = [result for result in results if not result.passed]
    if failures:
        details = "; ".join(
            f"{result.claim_id}: {', '.join(result.sensitive_paths)}"
            for result in failures
        )
        raise RuntimeError(
            "formal qualification drift detected; a fresh formal attestation is required: "
            + details
        )
    return results
