from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Iterable, Mapping


SCHEMA_VERSION = 1
FORMAT_NAME = "cace.lean-theorem-metadata"
FOUNDATIONAL_AXIOM_WHITELIST = frozenset(
    {"propext", "Classical.choice", "Quot.sound"}
)

_PRINT_AXIOMS_RE = re.compile(
    r"^\s*#print\s+axioms\s+([^\s]+)\s*(?:--.*)?$",
    re.MULTILINE,
)
_DEPENDS_RE = re.compile(
    r"'([^']+)'\s+depends on axioms:\s*\[([^\]]*)\]"
)
_NO_AXIOMS_RE = re.compile(
    r"'([^']+)'\s+does not depend on any axioms"
)


class LeanTheoremMetadataError(RuntimeError):
    """Raised when Lean theorem metadata cannot be exported safely."""


@dataclass(frozen=True)
class TheoremMetadata:
    name: str
    axioms: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {"name": self.name, "axioms": list(self.axioms)}


def discover_audited_theorems(audit_source: str) -> tuple[str, ...]:
    names = tuple(match.group(1) for match in _PRINT_AXIOMS_RE.finditer(audit_source))
    if not names:
        raise LeanTheoremMetadataError(
            "audit source contains no '#print axioms' commands"
        )
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise LeanTheoremMetadataError(
            f"audit source contains duplicate theorem commands: {duplicates}"
        )
    return tuple(sorted(names))


def _split_axioms(payload: str) -> tuple[str, ...]:
    axioms = tuple(sorted({item.strip() for item in payload.split(",") if item.strip()}))
    return axioms


def parse_lean_axiom_reports(lean_output: str) -> dict[str, tuple[str, ...]]:
    reports: dict[str, tuple[str, ...]] = {}
    occurrences: list[str] = []

    for match in _DEPENDS_RE.finditer(lean_output):
        name = match.group(1)
        occurrences.append(name)
        reports[name] = _split_axioms(match.group(2))

    for match in _NO_AXIOMS_RE.finditer(lean_output):
        name = match.group(1)
        occurrences.append(name)
        reports[name] = ()

    duplicates = sorted(
        {name for name in occurrences if occurrences.count(name) > 1}
    )
    if duplicates:
        raise LeanTheoremMetadataError(
            f"Lean output contains duplicate axiom reports: {duplicates}"
        )
    return reports


def build_theorem_metadata(
    *,
    audit_source: str,
    lean_output: str,
    audit_source_label: str,
    allowed_axioms: Iterable[str] = FOUNDATIONAL_AXIOM_WHITELIST,
) -> dict[str, object]:
    expected = discover_audited_theorems(audit_source)
    reports = parse_lean_axiom_reports(lean_output)
    expected_set = set(expected)
    report_set = set(reports)

    missing = sorted(expected_set - report_set)
    unexpected = sorted(report_set - expected_set)
    if missing:
        raise LeanTheoremMetadataError(
            f"missing theorem axiom reports: {missing}"
        )
    if unexpected:
        raise LeanTheoremMetadataError(
            f"unexpected theorem axiom reports: {unexpected}"
        )

    allowed = frozenset(allowed_axioms)
    theorem_records: list[TheoremMetadata] = []
    for name in expected:
        axioms = reports[name]
        forbidden = sorted(set(axioms) - allowed)
        if forbidden:
            raise LeanTheoremMetadataError(
                f"{name} depends on non-whitelisted axioms: {forbidden}"
            )
        theorem_records.append(TheoremMetadata(name=name, axioms=axioms))

    source_sha256 = hashlib.sha256(audit_source.encode("utf-8")).hexdigest()
    return {
        "schema_version": SCHEMA_VERSION,
        "format": FORMAT_NAME,
        "audit_source": audit_source_label.replace("\\", "/"),
        "audit_source_sha256": source_sha256,
        "theorem_count": len(theorem_records),
        "theorems": [record.to_dict() for record in theorem_records],
    }


def canonical_json_bytes(metadata: Mapping[str, object]) -> bytes:
    return (
        json.dumps(
            metadata,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            separators=(",", ": "),
        )
        + "\n"
    ).encode("utf-8")


def export_from_text(
    *,
    audit_source: str,
    lean_output: str,
    audit_source_label: str,
) -> bytes:
    metadata = build_theorem_metadata(
        audit_source=audit_source,
        lean_output=lean_output,
        audit_source_label=audit_source_label,
    )
    return canonical_json_bytes(metadata)


def run_lean_axiom_audit(
    *,
    formal_dir: str | Path,
    audit_source_path: str | Path,
) -> str:
    formal_root = Path(formal_dir).resolve()
    audit_path = Path(audit_source_path)
    if not audit_path.is_absolute():
        audit_path = (formal_root / audit_path).resolve()
    else:
        audit_path = audit_path.resolve()

    try:
        relative = audit_path.relative_to(formal_root)
    except ValueError as exc:
        raise LeanTheoremMetadataError(
            "audit source must be inside the formal project directory"
        ) from exc
    if not audit_path.is_file():
        raise LeanTheoremMetadataError(
            f"audit source does not exist: {relative.as_posix()}"
        )

    completed = subprocess.run(
        ["lake", "env", "lean", relative.as_posix()],
        cwd=formal_root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if completed.returncode != 0:
        raise LeanTheoremMetadataError(
            "Lean axiom audit failed before metadata export "
            f"(exit {completed.returncode})\n{completed.stdout}"
        )
    return completed.stdout


def export_from_files(
    *,
    formal_dir: str | Path,
    audit_source_path: str | Path,
    output_path: str | Path,
    lean_output_path: str | Path | None = None,
) -> dict[str, object]:
    formal_root = Path(formal_dir).resolve()
    audit_path = Path(audit_source_path)
    if not audit_path.is_absolute():
        audit_path = formal_root / audit_path
    audit_path = audit_path.resolve()
    try:
        audit_label = audit_path.relative_to(formal_root).as_posix()
    except ValueError as exc:
        raise LeanTheoremMetadataError(
            "audit source must be inside the formal project directory"
        ) from exc

    audit_source = audit_path.read_text(encoding="utf-8")
    if lean_output_path is None:
        lean_output = run_lean_axiom_audit(
            formal_dir=formal_root,
            audit_source_path=audit_path,
        )
    else:
        lean_output = Path(lean_output_path).read_text(encoding="utf-8")

    metadata = build_theorem_metadata(
        audit_source=audit_source,
        lean_output=lean_output,
        audit_source_label=audit_label,
    )
    payload = canonical_json_bytes(metadata)

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    temporary.write_bytes(payload)
    temporary.replace(destination)
    return metadata


def _argument_parser():
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Export deterministic theorem/axiom metadata from Lean '#print axioms' "
            "reports. The command fails closed on missing, duplicate, unexpected, "
            "or non-whitelisted axiom dependencies."
        )
    )
    parser.add_argument(
        "--formal-dir",
        default="formal/cace_formal",
        help="Lean project directory (default: formal/cace_formal)",
    )
    parser.add_argument(
        "--audit-source",
        default="CACEFormal/V330AxiomAudit.lean",
        help="Audit source path relative to --formal-dir",
    )
    parser.add_argument(
        "--lean-output",
        help=(
            "Optional file containing output from `lake env lean <audit-source>`. "
            "If omitted, the exporter runs the pinned Lean project itself."
        ),
    )
    parser.add_argument("--output", required=True, help="Destination JSON path")
    return parser


def main(argv: list[str] | None = None) -> int:
    import sys

    args = _argument_parser().parse_args(argv)
    try:
        metadata = export_from_files(
            formal_dir=Path(args.formal_dir),
            audit_source_path=Path(args.audit_source),
            output_path=Path(args.output),
            lean_output_path=Path(args.lean_output) if args.lean_output else None,
        )
    except (LeanTheoremMetadataError, OSError) as exc:
        print(f"theorem metadata export rejected: {exc}", file=sys.stderr)
        return 2

    print(
        f"theorem metadata export PASS: {metadata['theorem_count']} theorem(s) -> "
        f"{args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
