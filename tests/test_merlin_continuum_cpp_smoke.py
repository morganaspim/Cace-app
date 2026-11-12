from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
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
    with tempfile.TemporaryDirectory(prefix="merlin-continuum-oci-") as temp_dir:
        temp = Path(temp_dir)
        for source in test_sources:
            binary = temp / source.stem
            compile_result = subprocess.run(
                [
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
                    "-o",
                    str(binary),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                timeout=90,
                check=False,
            )
            assert compile_result.returncode == 0, (
                compile_result.stdout + compile_result.stderr
            )
            run_result = subprocess.run(
                [str(binary)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )
            assert run_result.returncode == 0, (
                run_result.stdout + run_result.stderr
            )
            assert "PASS" in run_result.stdout
