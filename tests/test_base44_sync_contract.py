from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from scripts.check_base44_sync_contract import (
    Base44SyncPolicyError,
    classify_path,
    classify_paths,
    enforce_base44_boundary,
    load_policy,
    validate_policy,
)


ROOT = Path(__file__).resolve().parents[1]


def _policy():
    return load_policy(ROOT / "CACE_BASE44_GITHUB_SYNC_POLICY.json")


def test_policy_is_valid():
    validate_policy(_policy())


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("web/index.html", "base44_owned"),
        ("web/studio.js", "base44_owned"),
        ("base44/entities/User.json", "base44_owned"),
        ("api/index.py", "joint_review"),
        ("docs/help/MATH_COIN_HELP.json", "joint_review"),
        ("formal/cace_formal/CACEFormal/Main.lean", "protected"),
        ("cace_studio/core/executor.py", "protected"),
        ("cace_studio/modules/fem.py", "protected"),
        ("cace_studio/data/proof_contracts.json", "protected"),
        (".github/workflows/cace-exact-pin-lean-preflight.yml", "protected"),
        ("docs/help/generated/CACE_PUBLIC_HELP.md", "generated_read_only"),
        ("random/new-area.txt", "unclassified"),
    ],
)
def test_path_classification(path, expected):
    assert classify_path(path, _policy()) == expected


def test_base44_mode_allows_owned_and_joint_review_paths():
    classification = classify_paths(
        ["web/index.html", "api/index.py"],
        _policy(),
    )
    enforce_base44_boundary(classification)


def test_base44_mode_rejects_protected_paths():
    classification = classify_paths(
        ["web/index.html", "formal/cace_formal/CACEFormal/Main.lean"],
        _policy(),
    )
    with pytest.raises(Base44SyncPolicyError, match="formal/cace_formal"):
        enforce_base44_boundary(classification)


def test_base44_mode_rejects_generated_and_unknown_paths():
    classification = classify_paths(
        ["docs/help/generated/CACE_PUBLIC_HELP.md", "mystery/file.txt"],
        _policy(),
    )
    with pytest.raises(Base44SyncPolicyError, match="mystery/file.txt"):
        enforce_base44_boundary(classification)


def test_formal_authority_cannot_be_granted_to_base44():
    policy = deepcopy(_policy())
    policy["formal_proof"]["base44_authority"] = "qualified"
    with pytest.raises(Base44SyncPolicyError, match="must remain none"):
        validate_policy(policy)
