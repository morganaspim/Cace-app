from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

from cace_studio.build_lite import (
    commands_for_plan,
    load_build_lite_config,
    load_cache_state,
    plan_build,
)


def _git_changed(repo_root: Path, base: str) -> list[str]:
    command = ["git", "diff", "--name-only", "--diff-filter=ACMR", base, "--"]
    result = subprocess.run(
        command,
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="CACE Build Lite: deterministic low-cost build/test planner for coding agents."
    )
    parser.add_argument("--repo", default=".", help="Repository root.")
    parser.add_argument("--config", default="CACE_BUILD_LITE.json")
    parser.add_argument("--profile", default="quick")
    parser.add_argument("--changed", action="append", default=[], help="Changed path; repeatable.")
    parser.add_argument("--git-base", default="", help="Use git diff NAME as changed-path input.")
    parser.add_argument("--target", action="append", default=[], help="Explicit task target; repeatable.")
    parser.add_argument("--all", action="store_true", help="Select all tasks in the profile.")
    parser.add_argument("--cache-state", default=".cace/build-lite-cache.json")
    parser.add_argument("--cpu-budget", type=int, default=4)
    parser.add_argument("--max-parallel", type=int, default=4)
    parser.add_argument("--output", default="", help="Write plan JSON to this path.")
    parser.add_argument(
        "--commands",
        action="store_true",
        help="Include executor/command rows. Build Lite never executes them itself.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo).resolve()
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = repo_root / config_path

    tasks, raw = load_build_lite_config(config_path)
    changed = list(args.changed)
    if args.git_base:
        changed.extend(_git_changed(repo_root, args.git_base))

    plan = plan_build(
        tasks,
        repo_root=repo_root,
        changed_paths=changed,
        profile=args.profile,
        cache_state=load_cache_state(
            (repo_root / args.cache_state)
            if not Path(args.cache_state).is_absolute()
            else args.cache_state
        ),
        cpu_budget=args.cpu_budget,
        max_parallel=args.max_parallel,
        explicit_targets=args.target,
        select_all=args.all,
    )
    payload = plan.to_dict()
    payload["planner_version"] = str(raw.get("version", "1"))
    if args.commands:
        payload["execution_batches"] = commands_for_plan(tasks, plan)

    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = Path(args.output)
        if not output.is_absolute():
            output = repo_root / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
