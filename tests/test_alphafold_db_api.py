from __future__ import annotations

import json
from urllib.error import HTTPError

import pytest

from cace_studio.core.module import ExecutionContext
from cace_studio.integrations.alphafold_db import (
    ALPHAFOLD_ATTRIBUTION,
    ALPHAFOLD_LICENSE_ID,
    AlphaFoldDBClient,
    AlphaFoldDBError,
)
from cace_studio.modules import molecular_materials as mm


def _pdb_line(serial, residue, chain, index, x, y, z, bfactor):
    return (
        f"ATOM  {serial:5d}  CA  {residue:>3s} {chain}{index:4d}    "
        f"{x:8.3f}{y:8.3f}{z:8.3f}  1.00{bfactor:6.2f}           C"
    )


PDB_TEXT = "\n".join(
    (
        _pdb_line(1, "ALA", "A", 1, 0.0, 0.0, 0.0, 91.0),
        _pdb_line(2, "GLY", "A", 2, 3.8, 0.0, 0.0, 88.0),
    )
)

METADATA = [
    {
        "modelEntityId": "AF-P12345-F1",
        "uniprotAccession": "P12345",
        "sequence": "AG",
        "sequenceStart": 1,
        "sequenceEnd": 2,
        "globalMetricValue": 89.5,
        "latestVersion": 6,
        "gene": "EXAMPLE",
        "organismScientificName": "Example organism",
        "pdbUrl": "https://alphafold.ebi.ac.uk/files/AF-P12345-F1-model_v6.pdb",
        "cifUrl": "https://alphafold.ebi.ac.uk/files/AF-P12345-F1-model_v6.cif",
        "bcifUrl": "https://alphafold.ebi.ac.uk/files/AF-P12345-F1-model_v6.bcif",
        "paeDocUrl": "https://alphafold.ebi.ac.uk/files/AF-P12345-F1-predicted_aligned_error_v6.json",
    }
]


class _Response:
    def __init__(self, url: str, payload: bytes):
        self._url = url
        self._payload = payload
        self.headers = {"Content-Length": str(len(payload))}

    def read(self, amount=-1):
        return self._payload if amount < 0 else self._payload[:amount]

    def geturl(self):
        return self._url

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeAlphaFoldService:
    def __init__(self, *, metadata=None, pdb_text=PDB_TEXT):
        self.metadata = METADATA if metadata is None else metadata
        self.pdb_text = pdb_text
        self.urls = []

    def __call__(self, request, timeout):
        url = request.full_url
        self.urls.append(url)
        if "/api/prediction/" in url:
            return _Response(url, json.dumps(self.metadata).encode("utf-8"))
        if url.endswith(".pdb"):
            return _Response(url, self.pdb_text.encode("utf-8"))
        raise HTTPError(url, 404, "not found", None, None)


def test_current_prediction_api_fields_and_pdb_hash_are_preserved():
    service = _FakeAlphaFoldService()
    fetched = AlphaFoldDBClient(opener=service).fetch_pdb("P12345")
    record = fetched.prediction
    assert record.model_entity_id == "AF-P12345-F1"
    assert record.sequence == "AG"
    assert record.sequence_start == 1
    assert record.sequence_end == 2
    assert record.latest_version == 6
    assert record.global_metric_value == pytest.approx(89.5)
    assert record.license_id == ALPHAFOLD_LICENSE_ID == "CC-BY-4.0"
    assert record.attribution == ALPHAFOLD_ATTRIBUTION
    assert fetched.pdb_text == PDB_TEXT
    assert len(fetched.pdb_sha256) == 64
    assert len(fetched.metadata_sha256) == 64
    assert service.urls[0].startswith("https://alphafold.com/api/prediction/P12345")


def test_old_field_names_are_only_a_backward_compatibility_fallback():
    metadata = [
        {
            "entryId": "AF-P12345-F1",
            "uniprotAccession": "P12345",
            "uniprotSequence": "AG",
            "uniprotStart": 1,
            "uniprotEnd": 2,
            "pdbUrl": METADATA[0]["pdbUrl"],
        }
    ]
    record = AlphaFoldDBClient(
        opener=_FakeAlphaFoldService(metadata=metadata)
    ).prediction_records("P12345")[0]
    assert record.model_entity_id == "AF-P12345-F1"
    assert record.sequence == "AG"
    assert record.sequence_start == 1
    assert record.sequence_end == 2


def test_api_rejects_structure_urls_outside_approved_alphafold_domains():
    metadata = [dict(METADATA[0], pdbUrl="https://example.com/evil.pdb")]
    client = AlphaFoldDBClient(opener=_FakeAlphaFoldService(metadata=metadata))
    with pytest.raises(AlphaFoldDBError, match="approved HTTPS AlphaFold domains"):
        client.prediction_records("P12345")


def test_api_module_emits_typed_structure_attribution_and_integrity_record(monkeypatch):
    client = AlphaFoldDBClient(opener=_FakeAlphaFoldService())
    monkeypatch.setattr(mm, "AlphaFoldDBClient", lambda timeout: client)

    module = mm.AlphaFoldDBAPIImportModule()
    params = module.resolved_params(
        {
            "uniprot_accession": "P12345",
            "prediction_index": 0,
            "timeout_seconds": 5.0,
        }
    )
    module.validate({}, params)
    outputs = module.execute(
        {},
        params,
        ExecutionContext(run_id="afdb-test", seed=0),
    )
    structure = outputs["structure"]
    assert structure.sequence.sequence == "AG"
    assert structure.plddt == (91.0, 88.0)
    assert structure.provenance is not None
    assert structure.provenance.license_id == "CC-BY-4.0"
    assert "AlphaFold Protein Structure Database" in structure.provenance.attribution
    assert outputs["source_url"].endswith("/entry/P12345")
    assert outputs["global_metric_value"] == pytest.approx(89.5)

    records = module.verify(
        {},
        params,
        outputs,
        ExecutionContext(run_id="afdb-test", seed=0),
    )
    assert len(records) == 1
    assert records[0].passed
    assert records[0].metrics["hash_matches"] is True
    assert records[0].metrics["license_preserved"] is True
    assert records[0].metrics["attribution_preserved"] is True


def test_api_module_validation_is_offline_and_rejects_bad_accession(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("validation must not perform network access")

    monkeypatch.setattr(mm, "AlphaFoldDBClient", forbidden)
    module = mm.AlphaFoldDBAPIImportModule()
    with pytest.raises(Exception, match="accession"):
        module.validate(
            {},
            {
                "uniprot_accession": "https://evil.invalid/x",
                "prediction_index": 0,
                "timeout_seconds": 5.0,
            },
        )
