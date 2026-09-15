from __future__ import annotations

import json

import pytest

from cace_studio.core.lean_theorem_metadata import (
    LeanTheoremMetadataError,
    build_theorem_metadata,
    canonical_json_bytes,
    discover_audited_theorems,
    export_from_text,
    parse_lean_axiom_reports,
)


AUDIT = """\
#print axioms CACEFormal.Test.zeta
#print axioms CACEFormal.Test.alpha
"""

LEAN_OUTPUT = """\
'CACEFormal.Test.zeta' depends on axioms: [Quot.sound, propext, Classical.choice]
'CACEFormal.Test.alpha' does not depend on any axioms
"""


def test_discovers_and_sorts_theorems_from_lean_audit_source():
    assert discover_audited_theorems(AUDIT) == (
        "CACEFormal.Test.alpha",
        "CACEFormal.Test.zeta",
    )


def test_export_is_canonical_and_deterministic():
    first = export_from_text(
        audit_source=AUDIT,
        lean_output=LEAN_OUTPUT,
        audit_source_label="CACEFormal/V330AxiomAudit.lean",
    )
    second = export_from_text(
        audit_source=AUDIT,
        lean_output=LEAN_OUTPUT,
        audit_source_label="CACEFormal/V330AxiomAudit.lean",
    )
    assert first == second
    assert first.endswith(b"\n")

    document = json.loads(first)
    assert document["schema_version"] == 1
    assert document["format"] == "cace.lean-theorem-metadata"
    assert document["theorem_count"] == 2
    assert [item["name"] for item in document["theorems"]] == [
        "CACEFormal.Test.alpha",
        "CACEFormal.Test.zeta",
    ]
    assert document["theorems"][0]["axioms"] == []
    assert document["theorems"][1]["axioms"] == [
        "Classical.choice",
        "Quot.sound",
        "propext",
    ]
    assert canonical_json_bytes(document) == first


def test_parser_rejects_duplicate_source_commands():
    with pytest.raises(LeanTheoremMetadataError, match="duplicate theorem commands"):
        discover_audited_theorems(
            "#print axioms CACEFormal.Test.x\n"
            "#print axioms CACEFormal.Test.x\n"
        )


def test_parser_rejects_duplicate_lean_reports():
    duplicate = """\
'CACEFormal.Test.x' depends on axioms: [propext]
'CACEFormal.Test.x' depends on axioms: [propext]
"""
    with pytest.raises(LeanTheoremMetadataError, match="duplicate axiom reports"):
        parse_lean_axiom_reports(duplicate)


def test_export_rejects_missing_or_unexpected_reports():
    with pytest.raises(LeanTheoremMetadataError, match="missing theorem axiom reports"):
        build_theorem_metadata(
            audit_source=AUDIT,
            lean_output="'CACEFormal.Test.alpha' does not depend on any axioms\n",
            audit_source_label="audit.lean",
        )

    unexpected = LEAN_OUTPUT + (
        "'CACEFormal.Test.extra' depends on axioms: [propext]\n"
    )
    with pytest.raises(LeanTheoremMetadataError, match="unexpected theorem axiom reports"):
        build_theorem_metadata(
            audit_source=AUDIT,
            lean_output=unexpected,
            audit_source_label="audit.lean",
        )


def test_export_rejects_sorry_or_any_non_whitelisted_axiom():
    output = """\
'CACEFormal.Test.zeta' depends on axioms: [propext, sorryAx]
'CACEFormal.Test.alpha' does not depend on any axioms
"""
    with pytest.raises(LeanTheoremMetadataError, match="non-whitelisted axioms"):
        build_theorem_metadata(
            audit_source=AUDIT,
            lean_output=output,
            audit_source_label="audit.lean",
        )


def test_source_hash_and_label_are_stable_and_machine_independent():
    metadata = build_theorem_metadata(
        audit_source=AUDIT,
        lean_output=LEAN_OUTPUT,
        audit_source_label=r"CACEFormal\V330AxiomAudit.lean",
    )
    assert metadata["audit_source"] == "CACEFormal/V330AxiomAudit.lean"
    assert len(metadata["audit_source_sha256"]) == 64
    int(metadata["audit_source_sha256"], 16)
