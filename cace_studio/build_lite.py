from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


class BuildLiteError(ValueError):
    pass


def _canonical(value: Any, field_name: str) -> str:
    text = str(value).strip()
    if not text or any(char.isspace() for char in text):
        raise BuildLiteError(f"{field_name} must be a non-empty canonical identifier")
    return text


@dataclass(frozen=True)
class BuildTask:
    task_id: str
    deps: tuple[str, ...] = ()
    triggers: tuple[str, ...] = ()
    cache_inputs: tuple[str, ...] = ()
    command: str = ""
    executor: str = "local"
    estimated_seconds: float = 1.0
    cpu_units: int = 1
    priority: float = 0.0
    fail_fast: bool = False
    proof_sensitive: bool = False
    cache_policy: str = "none"
    profiles: tuple[str, ...] = ("quick", "merge")

    def __post_init__(self) -> None:
        _canonical(self.task_id, "task_id")
        for dep in self.deps:
            _canonical(dep, "dependency")
        if self.estimated_seconds <= 0:
            raise BuildLiteError("estimated_seconds must be positive")
        if self.cpu_units <= 0:
            raise BuildLiteError("cpu_units must be positive")
        if self.cache_policy not in {"none", "skip_on_exact_hit", "restore_only"}:
            raise BuildLiteError(f"unsupported cache_policy: {self.cache_policy}")


@dataclass(frozen=True)
class TaskDecision:
    task_id: str
    selected: bool
    cache_hit: bool
    skip_execution: bool
    fingerprint: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class BuildBatch:
    index: int
    task_ids: tuple[str, ...]
    cpu_units: int
    estimated_seconds: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "task_ids": list(self.task_ids),
            "cpu_units": self.cpu_units,
            "estimated_seconds": self.estimated_seconds,
        }


@dataclass(frozen=True)
class BuildPlan:
    profile: str
    changed_paths: tuple[str, ...]
    selected_tasks: tuple[str, ...]
    skipped_tasks: tuple[str, ...]
    critical_path: tuple[str, ...]
    batches: tuple[BuildBatch, ...]
    decisions: tuple[TaskDecision, ...]
    serial_seconds: float
    scheduled_seconds: float
    note: str = (
        "CACE Build Lite optimizes build/test ordering only. It does not create "
        "verification evidence and cannot replace canonical Lean qualification."
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "cace.build-lite.plan.v1",
            "profile": self.profile,
            "changed_paths": list(self.changed_paths),
            "selected_tasks": list(self.selected_tasks),
            "skipped_tasks": list(self.skipped_tasks),
            "critical_path": list(self.critical_path),
            "batches": [batch.to_dict() for batch in self.batches],
            "decisions": [
                {
                    "task_id": item.task_id,
                    "selected": item.selected,
                    "cache_hit": item.cache_hit,
                    "skip_execution": item.skip_execution,
                    "fingerprint": item.fingerprint,
                    "reasons": list(item.reasons),
                }
                for item in self.decisions
            ],
            "serial_seconds": self.serial_seconds,
            "scheduled_seconds": self.scheduled_seconds,
            "estimated_speedup": (
                self.serial_seconds / self.scheduled_seconds
                if self.scheduled_seconds > 0
                else 1.0
            ),
            "note": self.note,
        }


def _load_tasks(raw: Mapping[str, Any]) -> dict[str, BuildTask]:
    entries = raw.get("tasks")
    if not isinstance(entries, list) or not entries:
        raise BuildLiteError("build-lite config requires a non-empty tasks list")
    tasks: dict[str, BuildTask] = {}
    for item in entries:
        if not isinstance(item, Mapping):
            raise BuildLiteError("each build-lite task must be an object")
        task = BuildTask(
            task_id=str(item.get("id", "")),
            deps=tuple(str(value) for value in item.get("deps", ())),
            triggers=tuple(str(value) for value in item.get("triggers", ())),
            cache_inputs=tuple(str(value) for value in item.get("cache_inputs", ())),
            command=str(item.get("command", "")),
            executor=str(item.get("executor", "local")),
            estimated_seconds=float(item.get("estimated_seconds", 1.0)),
            cpu_units=int(item.get("cpu_units", 1)),
            priority=float(item.get("priority", 0.0)),
            fail_fast=bool(item.get("fail_fast", False)),
            proof_sensitive=bool(item.get("proof_sensitive", False)),
            cache_policy=str(item.get("cache_policy", "none")),
            profiles=tuple(str(value) for value in item.get("profiles", ("quick", "merge"))),
        )
        if task.task_id in tasks:
            raise BuildLiteError(f"duplicate task id: {task.task_id}")
        tasks[task.task_id] = task

    for task in tasks.values():
        unknown = sorted(set(task.deps) - set(tasks))
        if unknown:
            raise BuildLiteError(f"task {task.task_id} has unknown dependencies: {unknown}")
    _topological_order(tasks)
    return tasks


def load_build_lite_config(path: str | Path) -> tuple[dict[str, BuildTask], dict[str, Any]]:
    target = Path(path)
    raw = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise BuildLiteError("build-lite config root must be an object")
    if raw.get("schema") != "cace.build-lite.v1":
        raise BuildLiteError("unsupported build-lite config schema")
    return _load_tasks(raw), dict(raw)


def _topological_order(tasks: Mapping[str, BuildTask], selected: set[str] | None = None) -> tuple[str, ...]:
    selected = set(tasks) if selected is None else set(selected)
    indegree = {task_id: 0 for task_id in selected}
    children = {task_id: set() for task_id in selected}
    for task_id in selected:
        for dep in tasks[task_id].deps:
            if dep in selected:
                indegree[task_id] += 1
                children[dep].add(task_id)
    ready = sorted(task_id for task_id, degree in indegree.items() if degree == 0)
    result: list[str] = []
    while ready:
        task_id = ready.pop(0)
        result.append(task_id)
        for child in sorted(children[task_id]):
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
                ready.sort()
    if len(result) != len(selected):
        cycle_nodes = sorted(selected - set(result))
        raise BuildLiteError(f"build-lite task graph contains a cycle: {cycle_nodes}")
    return tuple(result)


def _matches(path: str, patterns: Sequence[str]) -> bool:
    normalized = str(path).replace("\\", "/").lstrip("./")
    return any(fnmatch(normalized, pattern) for pattern in patterns)


def _dependency_closure(tasks: Mapping[str, BuildTask], seeds: Iterable[str]) -> set[str]:
    selected = set(seeds)
    stack = list(selected)
    while stack:
        task_id = stack.pop()
        for dep in tasks[task_id].deps:
            if dep not in selected:
                selected.add(dep)
                stack.append(dep)
    return selected


def _descendant_counts(tasks: Mapping[str, BuildTask], selected: set[str]) -> dict[str, int]:
    children = {task_id: set() for task_id in selected}
    for task_id in selected:
        for dep in tasks[task_id].deps:
            if dep in selected:
                children[dep].add(task_id)
    counts: dict[str, int] = {}
    for task_id in selected:
        seen: set[str] = set()
        stack = list(children[task_id])
        while stack:
            child = stack.pop()
            if child in seen:
                continue
            seen.add(child)
            stack.extend(children[child])
        counts[task_id] = len(seen)
    return counts


def _matching_files(repo_root: Path, patterns: Sequence[str]) -> tuple[Path, ...]:
    if not patterns:
        return ()
    result: set[Path] = set()
    for pattern in patterns:
        for path in repo_root.glob(pattern):
            if path.is_file():
                result.add(path)
    return tuple(sorted(result))


def task_fingerprint(repo_root: str | Path, task: BuildTask) -> str:
    root = Path(repo_root).resolve()
    files = _matching_files(root, task.cache_inputs)
    digest = sha256()
    digest.update(task.task_id.encode("utf-8"))
    digest.update(task.command.encode("utf-8"))
    for path in files:
        rel = path.resolve().relative_to(root).as_posix()
        digest.update(rel.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def load_cache_state(path: str | Path | None) -> dict[str, str]:
    if path is None:
        return {}
    target = Path(path)
    if not target.is_file():
        return {}
    raw = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise BuildLiteError("cache state must be a JSON object")
    values = raw.get("successful_fingerprints", raw)
    if not isinstance(values, Mapping):
        raise BuildLiteError("cache state successful_fingerprints must be an object")
    return {str(key): str(value) for key, value in values.items()}


def write_cache_state(path: str | Path, fingerprints: Mapping[str, str]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "cace.build-lite.cache.v1",
        "successful_fingerprints": dict(sorted(fingerprints.items())),
    }
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _critical_path(
    tasks: Mapping[str, BuildTask],
    runnable: set[str],
) -> tuple[str, ...]:
    if not runnable:
        return ()
    order = _topological_order(tasks, runnable)
    distance: dict[str, float] = {}
    predecessor: dict[str, str | None] = {}
    for task_id in order:
        parents = [dep for dep in tasks[task_id].deps if dep in runnable]
        if not parents:
            distance[task_id] = tasks[task_id].estimated_seconds
            predecessor[task_id] = None
            continue
        best_parent = max(parents, key=lambda dep: (distance[dep], dep))
        distance[task_id] = distance[best_parent] + tasks[task_id].estimated_seconds
        predecessor[task_id] = best_parent
    end = max(order, key=lambda task_id: (distance[task_id], task_id))
    path: list[str] = []
    current: str | None = end
    while current is not None:
        path.append(current)
        current = predecessor[current]
    path.reverse()
    return tuple(path)


def plan_build(
    tasks: Mapping[str, BuildTask],
    *,
    repo_root: str | Path,
    changed_paths: Sequence[str] = (),
    profile: str = "quick",
    cache_state: Mapping[str, str] | None = None,
    cpu_budget: int = 4,
    max_parallel: int = 4,
    explicit_targets: Sequence[str] = (),
    select_all: bool = False,
) -> BuildPlan:
    if cpu_budget <= 0 or max_parallel <= 0:
        raise BuildLiteError("cpu_budget and max_parallel must be positive")
    cache_state = dict(cache_state or {})
    changed = tuple(sorted({str(path).replace("\\", "/").lstrip("./") for path in changed_paths}))

    seeds: set[str] = set()
    if select_all:
        seeds.update(task_id for task_id, task in tasks.items() if profile in task.profiles)
    else:
        for task_id, task in tasks.items():
            if profile not in task.profiles:
                continue
            if task.triggers and any(_matches(path, task.triggers) for path in changed):
                seeds.add(task_id)
        for task_id in explicit_targets:
            if task_id not in tasks:
                raise BuildLiteError(f"unknown explicit target: {task_id}")
            seeds.add(task_id)

    selected = _dependency_closure(tasks, seeds)
    decisions: list[TaskDecision] = []
    skipped: set[str] = set()
    fingerprints: dict[str, str] = {}
    root = Path(repo_root)
    for task_id in sorted(tasks):
        task = tasks[task_id]
        if task_id not in selected:
            decisions.append(TaskDecision(task_id, False, False, False, "", ()))
            continue
        fingerprint = task_fingerprint(root, task)
        fingerprints[task_id] = fingerprint
        hit = bool(cache_state.get(task_id)) and cache_state.get(task_id) == fingerprint
        reasons = []
        if task_id in seeds:
            if explicit_targets and task_id in explicit_targets:
                reasons.append("explicit-target")
            if task.triggers and any(_matches(path, task.triggers) for path in changed):
                reasons.append("changed-path-trigger")
            if select_all:
                reasons.append("profile-select-all")
        if task_id not in seeds:
            reasons.append("dependency")
        if hit:
            reasons.append("exact-cache-hit")
        skip = (
            hit
            and task.cache_policy == "skip_on_exact_hit"
            and not task.proof_sensitive
        )
        if task.proof_sensitive and hit:
            reasons.append("proof-sensitive-cache-restore-only")
        if skip:
            reasons.append("execution-skipped")
            skipped.add(task_id)
        decisions.append(
            TaskDecision(
                task_id=task_id,
                selected=True,
                cache_hit=hit,
                skip_execution=skip,
                fingerprint=fingerprint,
                reasons=tuple(reasons),
            )
        )

    runnable = selected - skipped
    critical = _critical_path(tasks, runnable)
    critical_set = set(critical)
    descendants = _descendant_counts(tasks, selected)

    indegree = {task_id: 0 for task_id in runnable}
    children = {task_id: set() for task_id in runnable}
    for task_id in runnable:
        for dep in tasks[task_id].deps:
            if dep in runnable:
                indegree[task_id] += 1
                children[dep].add(task_id)

    def rank(task_id: str) -> tuple[float, str]:
        task = tasks[task_id]
        score = task.priority
        score += 1000.0 if task.fail_fast else 0.0
        score += 250.0 if task_id in critical_set else 0.0
        score += 10.0 * descendants.get(task_id, 0)
        score += 1.0 / max(task.estimated_seconds, 0.001)
        return (-score, task_id)

    ready = sorted((task_id for task_id, degree in indegree.items() if degree == 0), key=rank)
    batches: list[BuildBatch] = []
    completed: set[str] = set()
    while ready:
        chosen: list[str] = []
        used_cpu = 0
        for task_id in list(ready):
            task = tasks[task_id]
            if len(chosen) >= max_parallel:
                break
            if chosen and used_cpu + task.cpu_units > cpu_budget:
                continue
            if not chosen and task.cpu_units > cpu_budget:
                chosen.append(task_id)
                used_cpu = task.cpu_units
                break
            chosen.append(task_id)
            used_cpu += task.cpu_units
        if not chosen:
            chosen = [ready[0]]
            used_cpu = tasks[ready[0]].cpu_units

        for task_id in chosen:
            ready.remove(task_id)
        batch_seconds = max(tasks[task_id].estimated_seconds for task_id in chosen)
        batches.append(
            BuildBatch(
                index=len(batches),
                task_ids=tuple(chosen),
                cpu_units=used_cpu,
                estimated_seconds=batch_seconds,
            )
        )
        completed.update(chosen)
        for task_id in chosen:
            for child in children[task_id]:
                indegree[child] -= 1
                if indegree[child] == 0:
                    ready.append(child)
        ready.sort(key=rank)

    if completed != runnable:
        missing = sorted(runnable - completed)
        raise BuildLiteError(f"scheduler failed to place runnable tasks: {missing}")

    serial_seconds = sum(tasks[task_id].estimated_seconds for task_id in runnable)
    scheduled_seconds = sum(batch.estimated_seconds for batch in batches)
    return BuildPlan(
        profile=profile,
        changed_paths=changed,
        selected_tasks=tuple(_topological_order(tasks, selected)) if selected else (),
        skipped_tasks=tuple(sorted(skipped)),
        critical_path=critical,
        batches=tuple(batches),
        decisions=tuple(decisions),
        serial_seconds=serial_seconds,
        scheduled_seconds=scheduled_seconds,
    )


def commands_for_plan(tasks: Mapping[str, BuildTask], plan: BuildPlan) -> list[dict[str, Any]]:
    rows = []
    for batch in plan.batches:
        rows.append(
            {
                "batch": batch.index,
                "parallel": [
                    {
                        "task_id": task_id,
                        "executor": tasks[task_id].executor,
                        "command": tasks[task_id].command,
                        "proof_sensitive": tasks[task_id].proof_sensitive,
                    }
                    for task_id in batch.task_ids
                ],
            }
        )
    return rows
