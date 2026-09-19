from __future__ import annotations

import argparse
import fnmatch
import json
from pathlib import Path
import subprocess
from typing import Iterable


POLICY_PATH = Path("CACE_BASE44_GITHUB_SYNC_POLICY.json")


class Base44SyncPolicyError(ValueError):
    pass


def load_policy(path: str | Path = POLICY_PATH) -> dict:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise Base44SyncPolicyError("Base44 sync policy must be a JSON object")
    return raw


def validate_policy(policy: dict) -> None:
    if policy.get("schema") != "cace.base44-github-sync.v1":
        raise Base44SyncPolicyError("unexpected Base44 sync policy schema")

    required_lists = (
        "base44_owned_paths",
        "joint_review_paths",
        "cace_protected_paths",
        "generated_read_only_paths",
    )
    for key in required_lists:
        value = policy.get(key)
        if not isinstance(value, list) or not value:
            raise Base44SyncPolicyError(f"{key} must be a non-empty list")
        if any(not isinstance(item, str) or not item.strip() for item in value):
            raise Base44SyncPolicyError(f"{key} contains invalid path patterns")

    source = policy.get("source_of_truth")
    if not isinstance(source, dict) or source.get("canonical_system") is None:
        raise Base44SyncPolicyError("source_of_truth is incomplete")

    formal = policy.get("formal_proof")
    if not isinstance(formal, dict) or formal.get("base44_authority") != "none":
        raise Base44SyncPolicyError("Base44 formal proof authority must remain none")

    secrets = policy.get("secrets")
    if not isinstance(secrets, dict) or secrets.get("server_side_only") is not True:
        raise Base44SyncPolicyError("Base44 sync must keep secrets server-side")

    database = policy.get("database_boundary")
    if not isinstance(database, dict):
        raise Base44SyncPolicyError("database_boundary is required")
    if not database.get("never_sync_to_git"):
        raise Base44SyncPolicyError("database never-sync list cannot be empty")


def _matches(path: str, patterns: Iterable[str]) -> bool:
    normalized = path.replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return any(
        fnmatch.fnmatchcase(normalized, pattern)
        or (
            pattern.endswith("/**")
            and normalized == pattern[:-3].rstrip("/")
        )
        for pattern in patterns
    )


def classify_path(path: str, policy: dict) -> str:
    # Precedence is intentionally conservative.
    if _matches(path, policy["cace_protected_paths"]):
        return "protected"
    if _matches(path, policy["generated_read_only_paths"]):
        return "generated_read_only"
    if _matches(path, policy["joint_review_paths"]):
        return "joint_review"
    if _matches(path, policy["base44_owned_paths"]):
        return "base44_owned"
    return "unclassified"


def classify_paths(paths: Iterable[str], policy: dict) -> dict[str, list[str]]:
    result = {
        "base44_owned": [],
        "joint_review": [],
        "protected": [],
        "generated_read_only": [],
        "unclassified": [],
    }
    for raw in paths:
        path = raw.strip().replace("\\", "/")
        if not path:
            continue
        result[classify_path(path, policy)].append(path)
    for items in result.values():
        items.sort()
    return result


def git_changed_paths(git_base: str) -> list[str]:
    completed = subprocess.run(
        ["git", "diff", "--name-only", f"{git_base}...HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def enforce_base44_boundary(classification: dict[str, list[str]]) -> None:
    blocked = (
        classification["protected"]
        + classification["generated_read_only"]
        + classification["unclassified"]
    )
    if blocked:
        message = [
            "Base44 sync boundary rejected changed paths outside the permitted "
            "owned/joint-review zones:",
        ]
        for path in blocked:
            message.append(f"  - {path}")
        message.append(
            "Protected work must be implemented through the normal CACE review path; "
            "unclassified paths must first be assigned an ownership class."
        )
        raise Base44SyncPolicyError("\n".join(message))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default=str(POLICY_PATH))
    parser.add_argument("--git-base")
    parser.add_argument("--paths-file")
    parser.add_argument("--base44", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    policy = load_policy(args.policy)
    validate_policy(policy)

    paths: list[str] = []
    if args.git_base:
        paths.extend(git_changed_paths(args.git_base))
    if args.paths_file:
        paths.extend(
            Path(args.paths_file).read_text(encoding="utf-8").splitlines()
        )

    classification = classify_paths(paths, policy)
    if args.base44:
        enforce_base44_boundary(classification)

    if args.json:
        print(json.dumps(classification, indent=2, sort_keys=True))
    else:
        print("CACE_BASE44_SYNC_POLICY_OK")
        for key, values in classification.items():
            if values:
                print(f"{key}:")
                for value in values:
                    print(f"  {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
