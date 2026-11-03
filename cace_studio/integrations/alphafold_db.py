from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen


ALPHAFOLD_API_BASE = "https://alphafold.com/api/prediction"
ALPHAFOLD_LICENSE_ID = "CC-BY-4.0"
ALPHAFOLD_ATTRIBUTION = (
    "AlphaFold Protein Structure Database (Google DeepMind and EMBL-EBI), "
    "data licensed CC BY 4.0. Cite the relevant AlphaFold DB entry/publications "
    "and preserve entry-specific attribution."
)
_ALLOWED_HOSTS = frozenset(
    {
        "alphafold.com",
        "www.alphafold.com",
        "alphafold.ebi.ac.uk",
        "www.alphafold.ebi.ac.uk",
    }
)
_ACCESSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{1,63}$")


class AlphaFoldDBError(RuntimeError):
    pass


def validate_accession(accession: str) -> str:
    value = str(accession).strip()
    if not _ACCESSION_RE.fullmatch(value):
        raise ValueError("AlphaFold/UniProt accession must be a simple canonical identifier")
    return value


def _validate_https_alphafold_url(url: str) -> str:
    value = str(url).strip()
    parts = urlsplit(value)
    host = (parts.hostname or "").lower()
    if parts.scheme != "https" or host not in _ALLOWED_HOSTS:
        raise AlphaFoldDBError(
            "AlphaFold API returned a URL outside the approved HTTPS AlphaFold domains"
        )
    if parts.username or parts.password:
        raise AlphaFoldDBError("credentials are not allowed in AlphaFold URLs")
    return value


def _read_bounded(
    url: str,
    *,
    opener: Callable[..., Any],
    timeout: float,
    max_bytes: int,
    accept: str,
) -> bytes:
    _validate_https_alphafold_url(url)
    request = Request(
        url,
        headers={
            "Accept": accept,
            "User-Agent": "CACE-Studio/3.36 AlphaFoldDB-import",
        },
        method="GET",
    )
    try:
        response = opener(request, timeout=float(timeout))
        with response:
            final_url = getattr(response, "geturl", lambda: url)()
            _validate_https_alphafold_url(final_url)
            content_length = response.headers.get("Content-Length")
            if content_length:
                try:
                    if int(content_length) > int(max_bytes):
                        raise AlphaFoldDBError("AlphaFold response exceeds configured size limit")
                except ValueError:
                    pass
            payload = response.read(int(max_bytes) + 1)
    except HTTPError as exc:
        if exc.code == 404:
            raise AlphaFoldDBError("AlphaFold DB has no prediction for this accession") from exc
        raise AlphaFoldDBError(f"AlphaFold DB HTTP error {exc.code}") from exc
    except URLError as exc:
        raise AlphaFoldDBError(f"AlphaFold DB network error: {exc.reason}") from exc
    except TimeoutError as exc:
        raise AlphaFoldDBError("AlphaFold DB request timed out") from exc
    if len(payload) > int(max_bytes):
        raise AlphaFoldDBError("AlphaFold response exceeds configured size limit")
    return payload


@dataclass(frozen=True)
class AlphaFoldPredictionRecord:
    accession: str
    model_entity_id: str
    sequence: str
    sequence_start: int | None
    sequence_end: int | None
    pdb_url: str
    cif_url: str
    bcif_url: str
    pae_doc_url: str
    global_metric_value: float | None
    latest_version: int | None
    gene: str
    organism_scientific_name: str
    entry_url: str
    api_url: str
    license_id: str = ALPHAFOLD_LICENSE_ID
    attribution: str = ALPHAFOLD_ATTRIBUTION

    def to_dict(self) -> dict[str, Any]:
        return {
            "accession": self.accession,
            "modelEntityId": self.model_entity_id,
            "sequence": self.sequence,
            "sequenceStart": self.sequence_start,
            "sequenceEnd": self.sequence_end,
            "pdbUrl": self.pdb_url,
            "cifUrl": self.cif_url,
            "bcifUrl": self.bcif_url,
            "paeDocUrl": self.pae_doc_url,
            "globalMetricValue": self.global_metric_value,
            "latestVersion": self.latest_version,
            "gene": self.gene,
            "organismScientificName": self.organism_scientific_name,
            "entryUrl": self.entry_url,
            "apiUrl": self.api_url,
            "licenseId": self.license_id,
            "attribution": self.attribution,
        }


@dataclass(frozen=True)
class AlphaFoldFetchResult:
    prediction: AlphaFoldPredictionRecord
    pdb_text: str
    pdb_sha256: str
    metadata_sha256: str

    def to_metadata_dict(self) -> dict[str, Any]:
        result = self.prediction.to_dict()
        result["pdbSha256"] = self.pdb_sha256
        result["metadataSha256"] = self.metadata_sha256
        return result


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _record_from_mapping(
    raw: Mapping[str, Any],
    *,
    requested_accession: str,
    api_url: str,
) -> AlphaFoldPredictionRecord:
    model_entity_id = str(raw.get("modelEntityId") or raw.get("entryId") or "").strip()
    if not model_entity_id:
        raise AlphaFoldDBError("AlphaFold prediction metadata has no modelEntityId")
    sequence = str(raw.get("sequence") or raw.get("uniprotSequence") or "").strip().upper()
    accession = str(raw.get("uniprotAccession") or requested_accession).strip()
    pdb_url = _validate_https_alphafold_url(str(raw.get("pdbUrl") or ""))
    cif_raw = str(raw.get("cifUrl") or "").strip()
    bcif_raw = str(raw.get("bcifUrl") or "").strip()
    pae_raw = str(raw.get("paeDocUrl") or "").strip()
    cif_url = _validate_https_alphafold_url(cif_raw) if cif_raw else ""
    bcif_url = _validate_https_alphafold_url(bcif_raw) if bcif_raw else ""
    pae_doc_url = _validate_https_alphafold_url(pae_raw) if pae_raw else ""
    return AlphaFoldPredictionRecord(
        accession=accession,
        model_entity_id=model_entity_id,
        sequence=sequence,
        sequence_start=_optional_int(raw.get("sequenceStart", raw.get("uniprotStart"))),
        sequence_end=_optional_int(raw.get("sequenceEnd", raw.get("uniprotEnd"))),
        pdb_url=pdb_url,
        cif_url=cif_url,
        bcif_url=bcif_url,
        pae_doc_url=pae_doc_url,
        global_metric_value=_optional_float(raw.get("globalMetricValue")),
        latest_version=_optional_int(raw.get("latestVersion")),
        gene=str(raw.get("gene") or ""),
        organism_scientific_name=str(raw.get("organismScientificName") or ""),
        entry_url=f"https://alphafold.com/entry/{quote(accession, safe='')}",
        api_url=api_url,
    )


class AlphaFoldDBClient:
    """Small allowlisted client for AlphaFold DB prediction metadata + PDB files."""

    def __init__(
        self,
        *,
        opener: Callable[..., Any] = urlopen,
        timeout: float = 15.0,
        metadata_max_bytes: int = 2_000_000,
        pdb_max_bytes: int = 64_000_000,
    ) -> None:
        if not 0.5 <= float(timeout) <= 120.0:
            raise ValueError("AlphaFold DB timeout must be in 0.5..120 seconds")
        self.opener = opener
        self.timeout = float(timeout)
        self.metadata_max_bytes = int(metadata_max_bytes)
        self.pdb_max_bytes = int(pdb_max_bytes)

    def prediction_records(self, accession: str) -> tuple[AlphaFoldPredictionRecord, ...]:
        accession = validate_accession(accession)
        api_url = f"{ALPHAFOLD_API_BASE}/{quote(accession, safe='')}"
        payload = _read_bounded(
            api_url,
            opener=self.opener,
            timeout=self.timeout,
            max_bytes=self.metadata_max_bytes,
            accept="application/json",
        )
        try:
            raw = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AlphaFoldDBError("AlphaFold prediction metadata is not valid JSON") from exc
        if not isinstance(raw, list) or not raw:
            raise AlphaFoldDBError("AlphaFold DB returned no prediction records")
        if len(raw) > 256:
            raise AlphaFoldDBError("AlphaFold DB returned an unexpectedly large prediction list")
        records = []
        for item in raw:
            if not isinstance(item, Mapping):
                raise AlphaFoldDBError("AlphaFold prediction record is not an object")
            records.append(
                _record_from_mapping(
                    item,
                    requested_accession=accession,
                    api_url=api_url,
                )
            )
        return tuple(records)

    def fetch_pdb(
        self,
        accession: str,
        *,
        prediction_index: int = 0,
    ) -> AlphaFoldFetchResult:
        records = self.prediction_records(accession)
        index = int(prediction_index)
        if not 0 <= index < len(records):
            raise AlphaFoldDBError(
                f"prediction_index {index} is outside available range 0..{len(records)-1}"
            )
        record = records[index]
        pdb_bytes = _read_bounded(
            record.pdb_url,
            opener=self.opener,
            timeout=self.timeout,
            max_bytes=self.pdb_max_bytes,
            accept="chemical/x-pdb,text/plain;q=0.9,*/*;q=0.1",
        )
        try:
            pdb_text = pdb_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise AlphaFoldDBError("AlphaFold PDB response is not UTF-8 text") from exc
        if not pdb_text.strip():
            raise AlphaFoldDBError("AlphaFold PDB response is empty")
        metadata_payload = json.dumps(
            record.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return AlphaFoldFetchResult(
            prediction=record,
            pdb_text=pdb_text,
            pdb_sha256=sha256(pdb_bytes).hexdigest(),
            metadata_sha256=sha256(metadata_payload).hexdigest(),
        )
