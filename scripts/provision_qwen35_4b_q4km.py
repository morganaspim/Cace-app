#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

MODEL_REPO = "Qwen/Qwen3.5-4B"
MODEL_REVISION = "a7b0d22b993d71000cf2eadfb37222a67cee521e"
LLAMA_REPO = "https://github.com/ggml-org/llama.cpp.git"
LLAMA_COMMIT = "b29c606e28a01b1bc8c1351026a0fa6e616bf6c4"
QUANTIZATION = "Q4_K_M"
MODEL_ALIAS = "Qwen/Qwen3.5-4B"


class ProvisionError(RuntimeError):
    pass


def run(cmd: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=cwd, check=True)


def capture(cmd: list[str], *, cwd: Path | None = None) -> str:
    return subprocess.check_output(cmd, cwd=cwd, text=True).strip()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def tree_size(root: Path) -> int:
    total = 0
    for p in root.rglob("*"):
        try:
            if p.is_file():
                total += p.stat().st_size
        except OSError:
            pass
    return total


def require_free_space(path: Path, minimum: int) -> int:
    free = shutil.disk_usage(path).free
    if free < minimum:
        raise ProvisionError(
            f"insufficient free disk: {free} bytes available, {minimum} required"
        )
    return free


def require_tool(name: str) -> str:
    tool = shutil.which(name)
    if not tool:
        raise ProvisionError(f"required tool not found: {name}")
    return tool


def snapshot_download_exact(target: Path) -> None:
    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise ProvisionError(
            "huggingface_hub is required in the explicit prepare environment; "
            "install it there before running this script"
        ) from exc

    target.mkdir(parents=True, exist_ok=True)
    resolved = snapshot_download(
        repo_id=MODEL_REPO,
        revision=MODEL_REVISION,
        local_dir=str(target),
        local_dir_use_symlinks=False,
    )
    resolved_path = Path(resolved).resolve()
    if resolved_path != target.resolve():
        raise ProvisionError(
            f"snapshot_download resolved unexpected target: {resolved_path}"
        )

    config_path = target / "config.json"
    if not config_path.is_file():
        raise ProvisionError("official model snapshot is missing config.json")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    architectures = config.get("architectures", [])
    if "Qwen3_5ForConditionalGeneration" not in architectures:
        raise ProvisionError(
            f"unexpected model architecture: {architectures!r}"
        )


def checkout_llama_cpp(target: Path) -> None:
    git = require_tool("git")
    if target.exists():
        if not (target / ".git").is_dir():
            raise ProvisionError(f"existing llama.cpp path is not a git repo: {target}")
        origin = capture([git, "remote", "get-url", "origin"], cwd=target)
        if origin.rstrip("/") != LLAMA_REPO.rstrip("/"):
            raise ProvisionError(f"unexpected llama.cpp origin: {origin}")
        run([git, "fetch", "--no-tags", "origin", LLAMA_COMMIT], cwd=target)
    else:
        run([git, "clone", "--filter=blob:none", LLAMA_REPO, str(target)])
        run([git, "fetch", "--no-tags", "origin", LLAMA_COMMIT], cwd=target)
    run([git, "checkout", "--detach", LLAMA_COMMIT], cwd=target)
    actual = capture([git, "rev-parse", "HEAD"], cwd=target)
    if actual != LLAMA_COMMIT:
        raise ProvisionError(f"llama.cpp commit mismatch: {actual}")


def build_llama_cpp(root: Path, jobs: int) -> tuple[Path, Path]:
    require_tool("cmake")
    build = root / "build"
    run([
        "cmake", "-S", str(root), "-B", str(build),
        "-DCMAKE_BUILD_TYPE=Release",
        "-DLLAMA_CURL=OFF",
    ])
    run([
        "cmake", "--build", str(build), "--parallel", str(jobs),
        "--target", "llama-server", "llama-quantize",
    ])

    candidates = {
        "server": [
            build / "bin" / "llama-server",
            build / "llama-server",
        ],
        "quantize": [
            build / "bin" / "llama-quantize",
            build / "llama-quantize",
        ],
    }
    found = {}
    for key, paths in candidates.items():
        path = next((p for p in paths if p.is_file() and os.access(p, os.X_OK)), None)
        if path is None:
            raise ProvisionError(f"built {key} binary not found")
        found[key] = path
    return found["server"], found["quantize"]


def convert_and_quantize(
    llama_root: Path,
    model_root: Path,
    quantizer: Path,
    out_dir: Path,
) -> tuple[Path, Path]:
    converter = llama_root / "convert_hf_to_gguf.py"
    if not converter.is_file():
        raise ProvisionError("pinned llama.cpp converter not found")

    out_dir.mkdir(parents=True, exist_ok=True)
    f16 = out_dir / "qwen3.5-4b-f16.gguf"
    q4 = out_dir / "qwen3.5-4b-q4_k_m.gguf"

    run([
        sys.executable, str(converter), str(model_root),
        "--outfile", str(f16),
        "--outtype", "f16",
    ])
    if not f16.is_file() or f16.stat().st_size < 100_000_000:
        raise ProvisionError("F16 GGUF conversion did not produce a plausible artifact")

    run([str(quantizer), str(f16), str(q4), QUANTIZATION])
    if not q4.is_file() or q4.stat().st_size < 100_000_000:
        raise ProvisionError("Q4_K_M quantization did not produce a plausible artifact")
    return f16, q4


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Provision exact pinned Qwen3.5-4B Q4_K_M for local CACE"
    )
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--jobs", type=int, default=min(os.cpu_count() or 2, 8))
    parser.add_argument(
        "--minimum-free-gb",
        type=int,
        default=28,
        help="Fail before downloads unless this much free disk is available.",
    )
    parser.add_argument(
        "--keep-f16",
        action="store_true",
        help="Retain intermediate F16 GGUF after successful Q4_K_M creation.",
    )
    args = parser.parse_args()

    if args.jobs < 1 or args.jobs > 64:
        raise ProvisionError("--jobs must be between 1 and 64")
    if args.minimum_free_gb < 20:
        raise ProvisionError("--minimum-free-gb may not be below 20")

    work = Path(args.work_dir).resolve()
    output = Path(args.output_dir).resolve()
    work.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)

    free_before = require_free_space(
        work, args.minimum_free_gb * 1024**3
    )

    model_root = work / "qwen3.5-4b-source"
    llama_root = work / "llama.cpp"

    snapshot_download_exact(model_root)
    source_bytes = tree_size(model_root)
    checkout_llama_cpp(llama_root)
    server, quantizer = build_llama_cpp(llama_root, args.jobs)

    # Re-check space after source/runtime materialization before creating the
    # large F16 intermediate and Q4 result.
    require_free_space(work, 12 * 1024**3)

    f16, q4 = convert_and_quantize(
        llama_root, model_root, quantizer, output
    )

    manifest = {
        "schema_version": 1,
        "created_unix": int(time.time()),
        "model": {
            "repo_id": MODEL_REPO,
            "revision": MODEL_REVISION,
            "architecture": "Qwen3_5ForConditionalGeneration",
            "source_bytes": source_bytes,
            "license": "Apache-2.0",
        },
        "llama_cpp": {
            "repository": LLAMA_REPO,
            "commit": LLAMA_COMMIT,
            "server_path": str(server),
            "server_sha256": sha256(server),
            "quantizer_path": str(quantizer),
            "quantizer_sha256": sha256(quantizer),
        },
        "artifact": {
            "path": str(q4),
            "size_bytes": q4.stat().st_size,
            "sha256": sha256(q4),
            "quantization": QUANTIZATION,
            "model_alias": MODEL_ALIAS,
        },
        "network_policy": {
            "prepare_phase": "explicit-upstream-only",
            "qualification_phase": "deny",
            "runtime_phase": "deny",
        },
        "trust_role": "untrusted-informal-reasoner",
        "authority_expanded": False,
        "free_disk_before_bytes": free_before,
    }

    manifest_path = output / "cace-qwen3.5-4b-q4_k_m.manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if not args.keep_f16:
        f16.unlink()

    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProvisionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
