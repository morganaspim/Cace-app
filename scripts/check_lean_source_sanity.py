#!/usr/bin/env python3
"""Cheap fail-closed lexical sanity checks for Lean source edits."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
from pathlib import Path

DECL = r"(?:noncomputable\s+def|theorem|lemma|def|abbrev|structure|inductive|class)"
# Plain `def` appears legitimately inside identifiers such as `inner_def`.
# The corruption we want to catch is a declaration opener glued to a previous
# token, especially the exact seam class observed in generated patches:
# `...Densitynoncomputable def ...`.
GLUED_DECL_RE = re.compile(
    r"[A-Za-z0-9_'](?=noncomputable\s+def\b)"
    r"|[A-Za-z0-9_'](?=(?:theorem|lemma|abbrev|structure|inductive|class)\s+[A-Za-z_])"
)
DUP_DECL_RE = re.compile(
    rf"\b(?P<kind>{DECL})\s+(?P<name>[A-Za-z_][A-Za-z0-9_'.]*)"
    rf".*?\b(?P=kind)\s+(?P=name)\b"
)
RCASES_PAT_RE = re.compile(r"\brcases\b.*?\bwith\b.*?⟨(?P<body>[^⟩]*)⟩")
RCASES_RESERVED = {
    "by", "fun", "match", "let", "where", "do", "if", "then", "else", "in", "end"
}

EXIT_CLEAN = 0
EXIT_SOURCE_ISSUES = 1
EXIT_INPUT_ERROR = 2
EXIT_SCAN_GUARD_FAILURE = 3


class ScanInputError(RuntimeError):
    """Raised when the requested Lean source input cannot be scanned."""


def _issue(path: Path, line: int, column: int, kind: str, detail: str) -> dict:
    return {
        "path": path.as_posix(),
        "line": line,
        "column": column,
        "kind": kind,
        "detail": detail,
    }


def scan_text(path: Path, text: str) -> list[dict]:
    issues: list[dict] = []
    cleaned = list(text)
    stack: list[tuple[int, int, bool]] = []
    in_string = False
    string_start = (0, 0)
    escaped = False
    line_comment = False
    line = 1
    column = 1
    i = 0

    def blank(start: int, count: int) -> None:
        for j in range(start, min(start + count, len(cleaned))):
            if cleaned[j] != "\n":
                cleaned[j] = " "

    while i < len(text):
        ch = text[i]
        if ch == "\n":
            line += 1
            column = 1
            line_comment = False
            if in_string:
                escaped = False
            i += 1
            continue
        if line_comment:
            cleaned[i] = " "
            column += 1
            i += 1
            continue
        if in_string:
            cleaned[i] = " "
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            column += 1
            i += 1
            continue
        if stack:
            if text.startswith("/-", i):
                is_doc = text.startswith("/--", i)
                if is_doc:
                    issues.append(
                        _issue(
                            path,
                            line,
                            column,
                            "nested-doc-comment",
                            "doc comment opened inside another block comment; likely patch seam",
                        )
                    )
                stack.append((line, column, is_doc))
                count = 3 if is_doc else 2
                blank(i, count)
                column += count
                i += count
                continue
            if text.startswith("-/", i):
                stack.pop()
                blank(i, 2)
                column += 2
                i += 2
                continue
            cleaned[i] = " "
            column += 1
            i += 1
            continue
        if text.startswith("--", i):
            line_comment = True
            blank(i, 2)
            column += 2
            i += 2
            continue
        if text.startswith("/-", i):
            is_doc = text.startswith("/--", i)
            stack.append((line, column, is_doc))
            count = 3 if is_doc else 2
            blank(i, count)
            column += count
            i += count
            continue
        if text.startswith("-/", i):
            issues.append(
                _issue(
                    path,
                    line,
                    column,
                    "stray-block-comment-close",
                    "block comment closes without a matching opener",
                )
            )
            blank(i, 2)
            column += 2
            i += 2
            continue
        if ch == '"':
            in_string = True
            string_start = (line, column)
            cleaned[i] = " "
            column += 1
            i += 1
            continue
        column += 1
        i += 1

    if stack:
        start_line, start_column, _ = stack[0]
        issues.append(
            _issue(
                path,
                start_line,
                start_column,
                "unterminated-block-comment",
                f"{len(stack)} block comment(s) remain open at EOF",
            )
        )
    if in_string:
        issues.append(
            _issue(
                path,
                string_start[0],
                string_start[1],
                "unterminated-string",
                "string literal remains open at EOF",
            )
        )

    for lineno, source_line in enumerate("".join(cleaned).splitlines(), start=1):
        glued = GLUED_DECL_RE.search(source_line)
        if glued:
            issues.append(
                _issue(
                    path,
                    lineno,
                    glued.start() + 2,
                    "glued-declaration-keyword",
                    "declaration keyword is glued to the preceding token",
                )
            )
        duplicate = DUP_DECL_RE.search(source_line)
        if duplicate:
            issues.append(
                _issue(
                    path,
                    lineno,
                    duplicate.start() + 1,
                    "duplicated-declaration-fragment",
                    f"declaration {duplicate.group('kind')} {duplicate.group('name')} appears twice on one line",
                )
            )
        rcases_match = RCASES_PAT_RE.search(source_line)
        if rcases_match:
            body = rcases_match.group("body")
            for token_match in re.finditer(r"[A-Za-z_][A-Za-z0-9_']*", body):
                token = token_match.group(0)
                if token in RCASES_RESERVED:
                    issues.append(
                        _issue(
                            path,
                            lineno,
                            rcases_match.start("body") + token_match.start() + 1,
                            "reserved-rcases-identifier",
                            f"Lean reserved keyword {token!r} used as an rcases pattern identifier",
                        )
                    )
    return issues


def _lean_files(paths: list[Path]) -> list[Path]:
    result: set[Path] = set()
    for path in paths:
        if path.is_dir():
            result.update(p for p in path.rglob("*.lean") if p.is_file())
        elif path.suffix == ".lean" and path.is_file():
            result.add(path)
        else:
            raise ScanInputError(f"Lean source path not found or unsupported: {path}")
    return sorted(result)


def _source_bundle_sha256(files: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in files:
        raw = path.read_bytes()
        digest.update(path.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(raw).digest())
        digest.update(b"\0")
    return digest.hexdigest()


def scan_paths(
    paths: list[Path],
    *,
    required_sentinels: list[Path] | None = None,
) -> tuple[dict, int]:
    sentinels = list(required_sentinels or [])
    input_paths = [path.as_posix() for path in paths]
    try:
        files = _lean_files(paths)
    except ScanInputError as exc:
        return (
            {
                "schema": "cace-lean-source-sanity-v2",
                "status": "INPUT_ERROR",
                "input_paths": input_paths,
                "required_sentinels": [p.as_posix() for p in sentinels],
                "file_count": 0,
                "source_bundle_sha256": None,
                "issues": [],
                "error": str(exc),
            },
            EXIT_INPUT_ERROR,
        )

    if not files:
        return (
            {
                "schema": "cace-lean-source-sanity-v2",
                "status": "SCAN_GUARD_FAILURE",
                "input_paths": input_paths,
                "required_sentinels": [p.as_posix() for p in sentinels],
                "file_count": 0,
                "source_bundle_sha256": None,
                "issues": [],
                "error": "scan resolved zero Lean source files",
            },
            EXIT_SCAN_GUARD_FAILURE,
        )

    resolved_files = {path.resolve() for path in files}
    missing_sentinels = [
        sentinel.as_posix()
        for sentinel in sentinels
        if sentinel.resolve() not in resolved_files
    ]
    if missing_sentinels:
        return (
            {
                "schema": "cace-lean-source-sanity-v2",
                "status": "SCAN_GUARD_FAILURE",
                "input_paths": input_paths,
                "required_sentinels": [p.as_posix() for p in sentinels],
                "file_count": len(files),
                "source_bundle_sha256": _source_bundle_sha256(files),
                "issues": [],
                "error": "required sentinel source missing from scanned file set",
                "missing_sentinels": missing_sentinels,
            },
            EXIT_SCAN_GUARD_FAILURE,
        )

    issues = [
        issue
        for path in files
        for issue in scan_text(path, path.read_text(encoding="utf-8"))
    ]
    status = "PASS" if not issues else "SOURCE_ISSUES"
    return (
        {
            "schema": "cace-lean-source-sanity-v2",
            "status": status,
            "input_paths": input_paths,
            "required_sentinels": [p.as_posix() for p in sentinels],
            "file_count": len(files),
            "source_bundle_sha256": _source_bundle_sha256(files),
            "issues": issues,
        },
        EXIT_CLEAN if not issues else EXIT_SOURCE_ISSUES,
    )


def run_self_test() -> tuple[dict, int]:
    checks: dict[str, bool] = {}
    checks["known_good_text"] = scan_text(
        Path("Good.lean"), "theorem ok : True := by\n  trivial\n"
    ) == []
    checks["known_bad_text"] = bool(
        scan_text(
            Path("Bad.lean"),
            "Barnoncomputable def broken : Nat := 0\n",
        )
    )

    with tempfile.TemporaryDirectory(prefix="cace-lean-source-sanity-") as tmp:
        root = Path(tmp)
        good_root = root / "good"
        good_root.mkdir()
        sentinel = good_root / "CACEFormal.lean"
        sentinel.write_text("theorem root_ok : True := by trivial\n", encoding="utf-8")
        nested = good_root / "Nested"
        nested.mkdir()
        (nested / "Other.lean").write_text(
            "theorem other_ok : True := by trivial\n",
            encoding="utf-8",
        )
        report, code = scan_paths([good_root], required_sentinels=[sentinel])
        checks["nonempty_tree"] = code == EXIT_CLEAN and report["file_count"] == 2

        empty_root = root / "empty"
        empty_root.mkdir()
        _, empty_code = scan_paths([empty_root])
        checks["empty_tree_fails_closed"] = empty_code == EXIT_SCAN_GUARD_FAILURE

        _, sentinel_code = scan_paths(
            [good_root],
            required_sentinels=[good_root / "MissingSentinel.lean"],
        )
        checks["missing_sentinel_fails_closed"] = (
            sentinel_code == EXIT_SCAN_GUARD_FAILURE
        )

        _, missing_input_code = scan_paths([root / "missing"])
        checks["missing_input_distinct"] = missing_input_code == EXIT_INPUT_ERROR

        bad_root = root / "bad"
        bad_root.mkdir()
        (bad_root / "Broken.lean").write_text(
            "Barnoncomputable def broken : Nat := 0\n",
            encoding="utf-8",
        )
        _, bad_code = scan_paths([bad_root])
        checks["source_issue_distinct"] = bad_code == EXIT_SOURCE_ISSUES

    passed = all(checks.values())
    report = {
        "schema": "cace-lean-source-sanity-self-test-v1",
        "status": "PASS" if passed else "FAIL",
        "checks": checks,
    }
    return report, EXIT_CLEAN if passed else EXIT_INPUT_ERROR


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument(
        "--require-sentinel",
        action="append",
        default=[],
        type=Path,
        help="Require this exact Lean file to be included in the resolved scan set.",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run dependency-free known-good/known-bad scanner self-tests.",
    )
    args = parser.parse_args()

    if args.self_test:
        report, code = run_self_test()
    else:
        paths = args.paths or [Path("formal/cace_formal")]
        report, code = scan_paths(
            paths,
            required_sentinels=args.require_sentinel,
        )
    print(json.dumps(report, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
