from dataclasses import replace

import pytest

from cace_studio.core.evidence_ledger import (
    CHAIN_ALGORITHM,
    EVIDENCE_BUNDLE_SCHEMA,
    EVIDENCE_LEDGER_SCHEMA,
    IDENTITY_ALGORITHM,
    MERKLE_ALGORITHM,
    EvidenceArtifact,
    EvidenceBundle,
    EvidenceLedgerError,
    append_entry,
    bundle_from_payload,
    ledger_from_payload,
    merkle_root,
    provenance_has_proof_effect,
    verify_artifact_bytes,
    verify_bundle,
    verify_ledger,
)


def _artifacts():
    return (
        EvidenceArtifact.from_bytes(
            "proof-source",
            b"theorem source",
            role="proof-source",
            media_type="text/plain",
            path="formal/Theorem.lean",
        ),
        EvidenceArtifact.from_bytes(
            "dependency-lock",
            b"lean=v4.32.1\nmathlib=520045a",
            role="dependency-lock",
            media_type="text/plain",
        ),
        EvidenceArtifact.from_bytes(
            "result-certificate",
            b'{"state":"PASS"}',
            role="verification-certificate",
            media_type="application/json",
        ),
    )


def _bundle(*, reversed_order=False):
    artifacts = _artifacts()
    if reversed_order:
        artifacts = tuple(reversed(artifacts))
    return EvidenceBundle(
        artifacts=artifacts,
        bindings={
            "claim_id": "example.claim",
            "git_commit": "0123456789abcdef",
            "toolchain": {"lean": "v4.32.1", "mathlib": "520045a"},
        },
        notes=("provenance only",),
    )


def test_bundle_uses_existing_identity_contract_and_provenance_only():
    bundle = _bundle()
    assert bundle.schema == EVIDENCE_BUNDLE_SCHEMA
    assert bundle.identity_algorithm == IDENTITY_ALGORITHM
    assert bundle.merkle_algorithm == MERKLE_ALGORITHM
    assert bundle.proof_effect == "none"
    assert provenance_has_proof_effect(bundle) is False
    assert verify_bundle(bundle) == bundle.bundle_sha256


def test_artifact_input_order_is_canonicalized():
    left = _bundle()
    right = _bundle(reversed_order=True)
    assert left.merkle_root_sha256 == right.merkle_root_sha256
    assert left.bundle_sha256 == right.bundle_sha256
    assert left.canonical_json() == right.canonical_json()


def test_mapping_field_order_does_not_change_bundle_identity():
    left = EvidenceBundle(
        artifacts=_artifacts(),
        bindings={"claim_id": "x", "git_commit": "y"},
    )
    right = EvidenceBundle(
        artifacts=_artifacts(),
        bindings={"git_commit": "y", "claim_id": "x"},
    )
    assert left.bundle_sha256 == right.bundle_sha256


def test_byte_mutation_is_detected():
    artifact = EvidenceArtifact.from_bytes("a", b"original", role="result")
    verify_artifact_bytes(artifact, b"original")
    with pytest.raises(EvidenceLedgerError, match="SHA-256 mismatch"):
        verify_artifact_bytes(artifact, b"mutated!")


def test_bundle_byte_set_is_exact_not_subset():
    artifacts = _artifacts()
    bundle = EvidenceBundle(artifacts=artifacts)
    byte_map = {
        "proof-source": b"theorem source",
        "dependency-lock": b"lean=v4.32.1\nmathlib=520045a",
        "result-certificate": b'{"state":"PASS"}',
    }
    verify_bundle(bundle, artifact_bytes=byte_map)
    partial = dict(byte_map)
    partial.pop("proof-source")
    with pytest.raises(EvidenceLedgerError, match="artifact byte set mismatch"):
        verify_bundle(bundle, artifact_bytes=partial)


def test_removing_artifact_changes_merkle_root():
    artifacts = _artifacts()
    full_root = merkle_root(artifacts)
    reduced_root = merkle_root(artifacts[:-1])
    assert full_root != reduced_root


def test_duplicate_artifact_ids_fail_closed():
    first = EvidenceArtifact.from_bytes("same", b"a", role="result")
    second = EvidenceArtifact.from_bytes("same", b"b", role="result")
    with pytest.raises(EvidenceLedgerError, match="unique"):
        EvidenceBundle(artifacts=(first, second))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema", "future-schema"),
        ("identity_algorithm", "sha512"),
        ("merkle_algorithm", "sha512-merkle"),
        ("proof_effect", "formally-verified"),
    ],
)
def test_unknown_or_proof_promoting_bundle_contract_fails_closed(field, value):
    with pytest.raises(EvidenceLedgerError):
        replace(_bundle(), **{field: value})


def test_hash_chain_round_trip_and_tip():
    bundle = _bundle()
    first = append_entry(
        [],
        bundle,
        timestamp_utc="2026-09-14T22:00:00Z",
        metadata={"verifier": "machine-a"},
    )
    second = append_entry(
        [first],
        bundle,
        timestamp_utc="2026-09-14T22:01:00Z",
        metadata={"verifier": "machine-b"},
    )
    assert first.schema == EVIDENCE_LEDGER_SCHEMA
    assert first.chain_algorithm == CHAIN_ALGORITHM
    assert first.proof_effect == "none"
    assert second.previous_entry_sha256 == first.entry_sha256
    assert verify_ledger([first, second]) == second.entry_sha256


@pytest.mark.parametrize(
    "timestamp",
    [
        "",
        "2026-09-14T22:00:00.123Z",
        "2026-09-14T22:00:00+00:00",
        "2026-09-14 22:00:00Z",
        "2026-02-30T22:00:00Z",
        "2026-09-14T22:00:00z",
    ],
)
def test_ledger_timestamp_must_be_canonical_second_resolution_utc(timestamp):
    with pytest.raises(EvidenceLedgerError, match="timestamp_utc"):
        append_entry([], _bundle(), timestamp_utc=timestamp)


def test_mutating_historical_entry_breaks_chain():
    bundle = _bundle()
    first = append_entry([], bundle, timestamp_utc="2026-09-14T22:00:00Z")
    second = append_entry([first], bundle, timestamp_utc="2026-09-14T22:01:00Z")
    tampered = replace(first, metadata={"changed": True})
    with pytest.raises(EvidenceLedgerError, match="entry hash mismatch"):
        verify_ledger([tampered, second])


def test_deleting_middle_entry_breaks_sequence_or_link():
    bundle = _bundle()
    first = append_entry([], bundle, timestamp_utc="2026-09-14T22:00:00Z")
    second = append_entry([first], bundle, timestamp_utc="2026-09-14T22:01:00Z")
    third = append_entry([first, second], bundle, timestamp_utc="2026-09-14T22:02:00Z")
    with pytest.raises(EvidenceLedgerError):
        verify_ledger([first, third])


def test_wrong_previous_hash_fails_closed_even_if_entry_rehashed():
    bundle = _bundle()
    first = append_entry([], bundle, timestamp_utc="2026-09-14T22:00:00Z")
    second = append_entry([first], bundle, timestamp_utc="2026-09-14T22:01:00Z")
    bad_previous = "0" * 64
    draft = replace(second, previous_entry_sha256=bad_previous, entry_sha256="")
    forged = replace(draft, entry_sha256=draft.computed_entry_sha256())
    with pytest.raises(EvidenceLedgerError, match="previous hash mismatch"):
        verify_ledger([first, forged])


def test_formal_looking_bindings_never_promote_proof():
    bundle = EvidenceBundle(
        artifacts=_artifacts(),
        bindings={
            "claim_id": "open.problem",
            "requested_evidence": "formally-verified",
            "runtime_state": "PASS",
        },
    )
    entry = append_entry([], bundle, timestamp_utc="2026-09-14T22:00:00Z")
    assert bundle.proof_effect == "none"
    assert entry.proof_effect == "none"
    assert provenance_has_proof_effect(bundle) is False
    assert provenance_has_proof_effect(entry) is False


def test_linked_bundle_verification_checks_merkle_binding():
    bundle = _bundle()
    entry = append_entry([], bundle, timestamp_utc="2026-09-14T22:00:00Z")
    assert verify_ledger([entry], bundles={bundle.bundle_sha256: bundle}) == entry.entry_sha256
    bad_entry_draft = replace(entry, merkle_root_sha256="0" * 64, entry_sha256="")
    bad_entry = replace(
        bad_entry_draft,
        entry_sha256=bad_entry_draft.computed_entry_sha256(),
    )
    with pytest.raises(EvidenceLedgerError, match="Merkle root mismatch"):
        verify_ledger([bad_entry], bundles={bundle.bundle_sha256: bundle})


def test_serialized_bundle_round_trip_and_declared_root_verification():
    bundle = _bundle()
    parsed = bundle_from_payload(bundle.payload())
    assert parsed.bundle_sha256 == bundle.bundle_sha256
    tampered = dict(bundle.payload())
    tampered["merkle_root_sha256"] = "0" * 64
    with pytest.raises(EvidenceLedgerError, match="does not match"):
        bundle_from_payload(tampered)


def test_serialized_bundle_unknown_fields_fail_closed():
    payload = _bundle().payload()
    payload["future_field"] = True
    with pytest.raises(EvidenceLedgerError, match="keys mismatch"):
        bundle_from_payload(payload)


def test_serialized_ledger_round_trip_and_tamper_detection():
    bundle = _bundle()
    first = append_entry([], bundle, timestamp_utc="2026-09-14T22:00:00Z")
    second = append_entry([first], bundle, timestamp_utc="2026-09-14T22:01:00Z")
    payload = [first.payload(), second.payload()]
    parsed = ledger_from_payload(payload)
    assert parsed[-1].entry_sha256 == second.entry_sha256

    tampered = [dict(first.payload()), dict(second.payload())]
    tampered[0]["metadata"] = {"changed": True}
    with pytest.raises(EvidenceLedgerError, match="entry hash mismatch"):
        ledger_from_payload(tampered)


def test_serialized_ledger_rejects_noncanonical_timestamp_before_acceptance():
    entry = append_entry([], _bundle(), timestamp_utc="2026-09-14T22:00:00Z")
    payload = [dict(entry.payload())]
    payload[0]["timestamp_utc"] = "2026-09-14T22:00:00+00:00"
    with pytest.raises(EvidenceLedgerError, match="timestamp_utc"):
        ledger_from_payload(payload)
