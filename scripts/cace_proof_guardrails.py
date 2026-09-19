#!/usr/bin/env python3
"""Permanent CACE proof guardrails.

Commands:
  validate
      Fail closed if the audited root import surface drifts from the explicit
      allowlist, a quarantined module enters the root, required files vanish,
      or policy/configuration is malformed.

  impacted --base-ref REF
      Print changed CACEFormal modules plus every audited-root reverse
      dependent, in dependency-first order.  This is used for cheap targeted
      compilation before the full root build.

  plan-hash ...
      Emit a content-addressed SHA-256 that binds the Lean/Mathlib pins,
      target, compile-root flag, guardrail policy, and every Lean source file
      in the audited root's recursive CACEFormal import closure.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "formal" / "cace_formal" / "proof_guardrails.json"
IMPORT_RE = re.compile(r"^\s*import\s+([A-Za-z0-9_.]+)\s*$")


class GuardrailError(RuntimeError):
    pass


def load_config() -> dict:
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GuardrailError(f"cannot load guardrail config: {exc}") from exc
    if data.get("schema_version") != 1:
        raise GuardrailError("unsupported proof_guardrails.json schema_version")
    return data


def parse_imports(path: Path) -> tuple[str, ...]:
    imports: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = IMPORT_RE.match(line)
        if match:
            imports.append(match.group(1))
    return tuple(imports)


def module_to_path(module_root: Path, module: str) -> Path:
    return module_root / (module.replace(".", "/") + ".lean")


def path_to_module(module_root: Path, path: Path) -> str | None:
    try:
        relative = path.resolve().relative_to(module_root.resolve())
    except ValueError:
        return None
    if relative.suffix != ".lean":
        return None
    return ".".join(relative.with_suffix("").parts)


def cace_module_graph(module_root: Path) -> dict[str, tuple[str, ...]]:
    graph: dict[str, tuple[str, ...]] = {}
    for path in sorted(module_root.rglob("*.lean")):
        module = path_to_module(module_root, path)
        if module is None:
            continue
        graph[module] = tuple(
            imp for imp in parse_imports(path)
            if imp.startswith("CACEFormal.")
        )
    return graph


def root_closure(
    root_imports: Iterable[str],
    graph: dict[str, tuple[str, ...]],
) -> set[str]:
    seen: set[str] = set()
    stack = list(root_imports)
    while stack:
        module = stack.pop()
        if module in seen:
            continue
        seen.add(module)
        stack.extend(graph.get(module, ()))
    return seen


def validate(config: dict) -> None:
    audited_root = ROOT / config["audited_root"]
    module_root = ROOT / config["module_root"]
    ledger = ROOT / config["failure_ledger"]

    for path, label in (
        (audited_root, "audited root"),
        (module_root, "module root"),
        (ledger, "failure ledger"),
    ):
        if not path.exists():
            raise GuardrailError(f"missing {label}: {path.relative_to(ROOT)}")

    actual = parse_imports(audited_root)
    allowed = tuple(config.get("allowed_root_imports", ()))
    if not allowed:
        raise GuardrailError("allowed_root_imports must be non-empty")

    if len(actual) != len(set(actual)):
        raise GuardrailError("audited root contains duplicate imports")
    if len(allowed) != len(set(allowed)):
        raise GuardrailError("guardrail allowlist contains duplicate imports")

    actual_set = set(actual)
    allowed_set = set(allowed)
    if actual_set != allowed_set:
        raise GuardrailError(
            "audited-root import drift: "
            f"missing_from_root={sorted(allowed_set - actual_set)}, "
            f"unapproved_in_root={sorted(actual_set - allowed_set)}"
        )

    quarantined = set(config.get("quarantined_root_imports", ()))
    forbidden = actual_set & quarantined
    if forbidden:
        raise GuardrailError(
            f"quarantined modules imported by audited root: {sorted(forbidden)}"
        )

    for module in sorted(allowed_set | quarantined | {config["canary_module"]}):
        path = module_to_path(module_root, module)
        # Quarantined modules are allowed to be intentionally deleted later.
        if module in quarantined and not path.exists():
            continue
        if not path.is_file():
            raise GuardrailError(
                f"configured Lean module does not exist: {module} -> "
                f"{path.relative_to(ROOT)}"
            )

    graph = cace_module_graph(module_root)
    closure = root_closure(actual, graph)
    missing_internal = sorted(
        module
        for module in closure
        if module.startswith("CACEFormal.") and module not in graph
    )
    if missing_internal:
        raise GuardrailError(
            f"audited root closure has missing CACEFormal modules: {missing_internal}"
        )

    for relative in config.get("guardrail_sources", ()):
        path = ROOT / relative
        if not path.is_file():
            raise GuardrailError(f"missing guardrail source: {relative}")

    ledger_text = ledger.read_text(encoding="utf-8")
    ids = re.findall(r"^##\s+(F-\d{3})\b", ledger_text, flags=re.MULTILINE)
    if len(ids) != len(set(ids)) or not ids:
        raise GuardrailError("failure ledger IDs must be non-empty and unique")

    print(
        "CACE_PROOF_GUARDRAILS_OK",
        json.dumps(
            {
                "root_import_count": len(actual),
                "root_closure_count": len(closure),
                "quarantined_count": len(quarantined),
                "failure_ledger_entries": len(ids),
            },
            sort_keys=True,
        ),
    )


def git_changed_paths(base_ref: str) -> list[Path]:
    try:
        proc = subprocess.run(
            ["git", "diff", "--name-only", f"{base_ref}...HEAD", "--"],
            cwd=ROOT,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as exc:
        raise GuardrailError(
            f"git diff failed for base {base_ref!r}: {exc.stderr.strip()}"
        ) from exc
    return [ROOT / line for line in proc.stdout.splitlines() if line.strip()]


def dependency_first_order(
    modules: set[str],
    graph: dict[str, tuple[str, ...]],
) -> list[str]:
    ordered: list[str] = []
    temporary: set[str] = set()
    permanent: set[str] = set()

    def visit(module: str) -> None:
        if module in permanent:
            return
        if module in temporary:
            raise GuardrailError(f"cycle in CACEFormal import graph at {module}")
        temporary.add(module)
        for dep in graph.get(module, ()):
            if dep in modules:
                visit(dep)
        temporary.remove(module)
        permanent.add(module)
        ordered.append(module)

    for module in sorted(modules):
        visit(module)
    return ordered


def impacted_modules(config: dict, base_ref: str) -> list[str]:
    module_root = ROOT / config["module_root"]
    audited_root = ROOT / config["audited_root"]
    graph = cace_module_graph(module_root)
    root_imports = parse_imports(audited_root)
    closure = root_closure(root_imports, graph)

    changed_modules: set[str] = set()
    root_changed = False
    for path in git_changed_paths(base_ref):
        if path.resolve() == audited_root.resolve():
            root_changed = True
            continue
        module = path_to_module(module_root, path)
        if module is not None:
            changed_modules.add(module)

    if root_changed:
        impacted = set(closure)
    else:
        reverse: dict[str, set[str]] = {module: set() for module in graph}
        for module, deps in graph.items():
            for dep in deps:
                reverse.setdefault(dep, set()).add(module)

        impacted = set(changed_modules) & closure
        stack = list(impacted)
        while stack:
            module = stack.pop()
            for dependent in reverse.get(module, ()):
                if dependent in closure and dependent not in impacted:
                    impacted.add(dependent)
                    stack.append(dependent)

    quarantined = set(config.get("quarantined_root_imports", ()))
    impacted -= quarantined
    return dependency_first_order(impacted, graph)


def source_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def proof_plan(config: dict, args: argparse.Namespace) -> dict:
    module_root = ROOT / config["module_root"]
    audited_root = ROOT / config["audited_root"]
    graph = cace_module_graph(module_root)
    imports = parse_imports(audited_root)
    closure = root_closure(imports, graph)

    source_records = [
        {
            "path": str(audited_root.relative_to(ROOT)),
            "sha256": source_digest(audited_root),
        }
    ]
    for module in sorted(closure):
        path = module_to_path(module_root, module)
        if not path.is_file():
            raise GuardrailError(f"root-closure source missing: {module}")
        source_records.append(
            {
                "module": module,
                "path": str(path.relative_to(ROOT)),
                "sha256": source_digest(path),
            }
        )

    impacted: list[str] = []
    if args.impacted_file:
        impacted = [
            line.strip()
            for line in Path(args.impacted_file).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    payload = {
        "schema_version": 1,
        "lean_toolchain": args.toolchain,
        "mathlib_commit": args.mathlib_commit,
        "target": args.target,
        "compile_root": args.compile_root.lower() == "true",
        "guardrail_config_sha256": source_digest(CONFIG_PATH),
        "guardrail_sources": [
            {
                "path": relative,
                "sha256": source_digest(ROOT / relative),
            }
            for relative in sorted(config.get("guardrail_sources", ()))
        ],
        "canary_module": config["canary_module"],
        "impacted_modules": impacted,
        "root_sources": source_records,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload["plan_sha256"] = hashlib.sha256(canonical).hexdigest()
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("validate")

    impacted_parser = sub.add_parser("impacted")
    impacted_parser.add_argument("--base-ref", required=True)

    hash_parser = sub.add_parser("plan-hash")
    hash_parser.add_argument("--toolchain", required=True)
    hash_parser.add_argument("--mathlib-commit", required=True)
    hash_parser.add_argument("--target", required=True)
    hash_parser.add_argument("--compile-root", required=True, choices=("true", "false"))
    hash_parser.add_argument("--impacted-file")

    args = parser.parse_args()
    try:
        config = load_config()
        if args.command == "validate":
            validate(config)
            return 0
        if args.command == "impacted":
            validate(config)
            for module in impacted_modules(config, args.base_ref):
                print(module)
            return 0
        if args.command == "plan-hash":
            validate(config)
            print(json.dumps(proof_plan(config, args), sort_keys=True))
            return 0
    except GuardrailError as exc:
        print(f"CACE_PROOF_GUARDRAIL_REJECTED: {exc}", file=sys.stderr)
        return 2
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
