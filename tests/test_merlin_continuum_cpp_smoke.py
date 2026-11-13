from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "collaboration" / "merlin-continuum"
INCLUDE = FIXTURE / "cpp" / "include"
SOURCE_BINDING = FIXTURE / "SOURCE_BINDING.json"


def _git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def test_fixture_is_exactly_bound_to_expert_robot_source() -> None:
    binding = json.loads(SOURCE_BINDING.read_text(encoding="utf-8"))
    assert binding["schema"] == "merlin-cpp-runner-fixture-v1"
    assert binding["source_repository"] == "Mannyspiro/expert-robot"
    assert len(binding["source_commit"]) == 40
    assert binding["evidence_boundary"].startswith("Exact-byte fixture binding")
    for item in binding["source_files"]:
        data = (ROOT / item["fixture_path"]).read_bytes()
        assert _git_blob_sha1(data) == item["git_blob_sha1"], item["source_path"]


def test_exact_source_compiles_and_runs_on_cace_oci() -> None:
    compiler = shutil.which("g++") or shutil.which("clang++")
    assert compiler is not None, "C++20 compiler is required on the OCI runner"

    test_sources = (
        FIXTURE / "tests" / "continuum_simplex_smoke.cpp",
        FIXTURE / "tests" / "simplicial_complex_smoke.cpp",
    )
    binding = json.loads(SOURCE_BINDING.read_text(encoding="utf-8"))
    executions = []
    with tempfile.TemporaryDirectory(prefix="merlin-continuum-oci-") as temp_dir:
        temp = Path(temp_dir)
        for source in test_sources:
            binary = temp / source.stem
            compile_command = [
                    compiler,
                    "-std=c++20",
                    "-Wall",
                    "-Wextra",
                    "-Wpedantic",
                    "-Wconversion",
                    "-Wshadow",
                    "-I",
                    str(INCLUDE),
                    str(source),
                    *(
                        [str(FIXTURE / "cpp" / "src" / "sha256.cpp")]
                        if source.stem == "simplicial_complex_smoke"
                        else []
                    ),
                    "-o",
                    str(binary),
                ]
            compile_started = time.perf_counter()
            compile_result = subprocess.run(
                compile_command,
                cwd=ROOT,
                text=True,
                capture_output=True,
                timeout=90,
                check=False,
            )
            compile_seconds = time.perf_counter() - compile_started
            assert compile_result.returncode == 0, (
                compile_result.stdout + compile_result.stderr
            )
            run_started = time.perf_counter()
            run_result = subprocess.run(
                [str(binary)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )
            run_seconds = time.perf_counter() - run_started
            assert run_result.returncode == 0, (
                run_result.stdout + run_result.stderr
            )
            assert "PASS" in run_result.stdout
            executions.append({
                "test_source": source.relative_to(ROOT).as_posix(),
                "compile_command": compile_command,
                "compile_exit_code": compile_result.returncode,
                "compile_stdout": compile_result.stdout,
                "compile_stderr": compile_result.stderr,
                "compile_seconds": compile_seconds,
                "run_exit_code": run_result.returncode,
                "run_stdout": run_result.stdout,
                "run_stderr": run_result.stderr,
                "run_seconds": run_seconds,
            })

    runner_temp = os.environ.get("RUNNER_TEMP")
    artifact_dir_name = os.environ.get("CACE_ARTIFACT_DIR")
    if runner_temp and artifact_dir_name:
        artifact_dir = Path(runner_temp) / artifact_dir_name
        artifact_dir.mkdir(parents=True, exist_ok=True)
        version = subprocess.run(
            [compiler, "--version"], text=True, capture_output=True, check=False
        )
        persistence = {}
        for execution in executions:
            for line in execution["run_stdout"].splitlines():
                if line.startswith("PERSISTENCE_") and "=" in line:
                    key, value = line.split("=", 1)
                    persistence[key.lower()] = value
        receipt = {
            "schema": "merlin-cace-oci-cpp-reproduction-v1",
            "source_repository": binding["source_repository"],
            "source_commit": binding["source_commit"],
            "source_files": binding["source_files"],
            "runner": {
                "name": os.environ.get("RUNNER_NAME", "unknown"),
                "os": os.environ.get("RUNNER_OS", platform.system()),
                "arch": os.environ.get("RUNNER_ARCH", platform.machine()),
                "platform": platform.platform(),
                "identity": (
                    os.environ.get("RUNNER_NAME", "unknown") + "/" +
                    os.environ.get("RUNNER_OS", platform.system()) + "/" +
                    os.environ.get("RUNNER_ARCH", platform.machine())
                ),
                "compiler": version.stdout.splitlines()[0] if version.stdout else compiler,
            },
            "workflow": {
                "repository": os.environ.get("GITHUB_REPOSITORY", ""),
                "workflow": os.environ.get("GITHUB_WORKFLOW", ""),
                "workflow_ref": os.environ.get("GITHUB_WORKFLOW_REF", ""),
                "workflow_sha": os.environ.get("GITHUB_WORKFLOW_SHA", ""),
                "run_id": os.environ.get("GITHUB_RUN_ID", ""),
                "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
                "job": os.environ.get("GITHUB_JOB", ""),
            },
            "execution_id": ".".join(filter(None, [
                os.environ.get("GITHUB_RUN_ID", ""),
                os.environ.get("GITHUB_RUN_ATTEMPT", ""),
                os.environ.get("GITHUB_JOB", ""),
            ])),
            "executions": executions,
            "persistence": persistence,
        }
        payload = json.dumps(receipt, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        (artifact_dir / "merlin-continuum-cpp-reproduction-receipt.json").write_bytes(payload + b"\n")
