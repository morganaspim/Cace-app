#!/usr/bin/env python3
"""Cheap lexical sanity checks for Lean source edits."""
from __future__ import annotations

import argparse
import json
import re
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
PROOF_HOLE_RE = re.compile(r"\b(?:sorry|admit)\b")


def _issue(path: Path, line: int, column: int, kind: str, detail: str) -> dict:
    return {"path": path.as_posix(), "line": line, "column": column, "kind": kind, "detail": detail}


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
                    issues.append(_issue(path, line, column, "nested-doc-comment",
                        "doc comment opened inside another block comment; likely patch seam"))
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
            issues.append(_issue(path, line, column, "stray-block-comment-close",
                "block comment closes without a matching opener"))
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
        issues.append(_issue(path, start_line, start_column, "unterminated-block-comment",
            f"{len(stack)} block comment(s) remain open at EOF"))
    if in_string:
        issues.append(_issue(path, string_start[0], string_start[1], "unterminated-string",
            "string literal remains open at EOF"))

    cleaned_text = "".join(cleaned)
    for match in PROOF_HOLE_RE.finditer(cleaned_text):
        line_number = cleaned_text.count("\n", 0, match.start()) + 1
        line_start = cleaned_text.rfind("\n", 0, match.start()) + 1
        issues.append(_issue(
            path,
            line_number,
            match.start() - line_start + 1,
            "proof-hole-token",
            f"forbidden Lean proof-hole token {match.group(0)!r}",
        ))

    for lineno, source_line in enumerate(cleaned_text.splitlines(), start=1):
        glued = GLUED_DECL_RE.search(source_line)
        if glued:
            issues.append(_issue(path, lineno, glued.start() + 2, "glued-declaration-keyword",
                "declaration keyword is glued to the preceding token"))
        duplicate = DUP_DECL_RE.search(source_line)
        if duplicate:
            issues.append(_issue(path, lineno, duplicate.start() + 1, "duplicated-declaration-fragment",
                f"declaration {duplicate.group('kind')} {duplicate.group('name')} appears twice on one line"))
        rcases_match = RCASES_PAT_RE.search(source_line)
        if rcases_match:
            body = rcases_match.group("body")
            for token_match in re.finditer(r"[A-Za-z_][A-Za-z0-9_']*", body):
                token = token_match.group(0)
                if token in RCASES_RESERVED:
                    issues.append(_issue(
                        path,
                        lineno,
                        rcases_match.start("body") + token_match.start() + 1,
                        "reserved-rcases-identifier",
                        f"Lean reserved keyword {token!r} used as an rcases pattern identifier",
                    ))
    return issues


def _lean_files(paths: list[Path]) -> list[Path]:
    result: set[Path] = set()
    for path in paths:
        if path.is_dir():
            result.update(p for p in path.rglob("*.lean") if p.is_file())
        elif path.suffix == ".lean" and path.is_file():
            result.add(path)
        else:
            raise SystemExit(f"Lean source path not found or unsupported: {path}")
    return sorted(result)


def _self_test() -> int:
    fixtures = (
        (
            "valid-source",
            Path("SelfTestValid.lean"),
            "theorem ok : True := by\n  trivial\n",
            None,
        ),
        (
            "glued-declaration",
            Path("SelfTestGlued.lean"),
            "Barnoncomputable def baz : Nat := 1\n",
            "glued-declaration-keyword",
        ),
        (
            "unterminated-comment",
            Path("SelfTestComment.lean"),
            "/-- broken\ntheorem x : True := by trivial\n",
            "unterminated-block-comment",
        ),
        (
            "reserved-rcases",
            Path("SelfTestRCases.lean"),
            "theorem bad (p : Nat × Nat) : True := by\n"
            "  rcases p with ⟨x, by⟩\n"
            "  trivial\n",
            "reserved-rcases-identifier",
        ),
    )
    failures: list[dict] = []
    for name, path, source, expected_kind in fixtures:
        issues = scan_text(path, source)
        kinds = {item["kind"] for item in issues}
        if expected_kind is None:
            if issues:
                failures.append({"fixture": name, "unexpected_issues": issues})
        elif expected_kind not in kinds:
            failures.append({
                "fixture": name,
                "expected_kind": expected_kind,
                "observed_kinds": sorted(kinds),
            })

    payload = {
        "schema": "cace-lean-source-sanity-self-test-v1",
        "status": "PASS" if not failures else "FAIL",
        "fixture_count": len(fixtures),
        "failures": failures,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not failures else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--require-sentinel", type=Path)
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args()

    if args.self_test:
        if args.paths or args.require_sentinel is not None:
            parser.error("--self-test cannot be combined with scan paths or --require-sentinel")
        return _self_test()

    paths = args.paths or [Path("formal/cace_formal")]
    files = _lean_files(paths)

    if args.require_sentinel is not None:
        sentinel = args.require_sentinel
        resolved_files = {path.resolve() for path in files}
        if not sentinel.is_file() or sentinel.resolve() not in resolved_files:
            print(json.dumps({
                "schema": "cace-lean-source-sanity-v1",
                "file_count": len(files),
                "issues": [{
                    "path": sentinel.as_posix(),
                    "line": 0,
                    "column": 0,
                    "kind": "missing-required-sentinel",
                    "detail": "required sentinel is absent from the requested Lean scan surface",
                }],
            }, indent=2, sort_keys=True))
            return 2

    issues = [issue for path in files for issue in scan_text(path, path.read_text(encoding="utf-8"))]
    print(json.dumps({"schema": "cace-lean-source-sanity-v1", "file_count": len(files), "issues": issues},
                     indent=2, sort_keys=True))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
