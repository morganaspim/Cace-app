#!/usr/bin/env python3
"""Private, source-pinned OCI ARM64 technical ZIP assembly and native smoke.

Do not publish model bytes or this unqualified full bundle. Existing host
provider and Python are read only. Scratch files are removed after the job.
License texts are public-source inputs, not redistribution authorization.
"""
from __future__ import annotations
import base64
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import stat
import struct
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import uuid

REPO = "morganaspim/Cace-app"
BRANCH = "fix/merlin-native-offline-zip-source-20261122"
SOURCE_REPO = "Mannyspiro/expert-robot"
SOURCE_SHA = "94644a0a4c86177748c3924b8dca1b523b826a27"
MODEL_DIR = Path("/opt/merlin-model-provider/releases/"
    "3f432dc172cf06f1af75974dbc4ec2b9135a8a82bd1fa2bfc35c0e53fe69f33e")
LLAMA = MODEL_DIR / "llama-server"
GGUF = MODEL_DIR / "qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"
LLAMA_SHA = "af4c10f1f4a1e7f0878dc9b3896bb742f65170861276ef04ddecdf2a9be3cd82"
GGUF_SHA = "cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046"
PY_SHA = "6cfad927461ace659b09716fad2efa828c6a4b084b7be8181c3982a9f36f464c"
PY_ARCHIVE_BYTES = 49469868
STAGE_SHA256 = "2aaf1375f8969006c57e5523e91fd2a5b157990f069503b29764ec38c097ee82"
STAGE_BLOB = "b78089d302c9dced6cf4ecc9d4a5ccb9cc54bc6b"
STAGE_COMMIT = "71e6405a3475eb449d150b961915922edd3e9fb0"
MODEL_ORIGIN = "https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF"
LLAMA_ORIGIN = "https://github.com/ggml-org/llama.cpp"
PY_ORIGIN = "https://github.com/astral-sh/python-build-standalone"
LICENSE_PINS = {
    "qwen": "832dd9e00a68dd83b3c3fb9f5588dad7dcf337a0db50f7d9483f310cd292e92e",
    "llama": "94f29bbed6a22c35b992c5c6ebf0e7c92f13b836b90f36f461c9cf2f0f1d010d",
    "python": "3b2f81fe21d181c499c59a256c8e1968455d6689d269aa85373bfb6af41da3bf",
}
LLAMA_SOURCE_COMMIT = "56eea9e4b0f5d125da16b75b551440b170aa8b1f"


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def gitblob(raw):
    return hashlib.sha1(("blob %d\0" % len(raw)).encode() + raw).hexdigest()


def gh_api(owner, resource):
    req = urllib.request.Request(
        "https://api.github.com/repos/" + owner + "/" + resource,
        headers={"Authorization": "Bearer " + os.environ["GITHUB_TOKEN"],
                 "Accept": "application/vnd.github+json",
                 "User-Agent": "Merlin-private-offline-native-bundle"})
    with urllib.request.urlopen(req, timeout=30) as res:
        raw = res.read(1024 * 1024 + 1)
    require(len(raw) <= 1024 * 1024, "GitHub API payload too large")
    return json.loads(raw)


def content_from_repo(owner, path, commit, size, blob, digest):
    record = gh_api(owner, "contents/" + path + "?ref=" + commit)
    require(record.get("encoding") == "base64", "pinned source not base64")
    body = base64.b64decode("".join(record["content"].split()), validate=True)
    require(len(body) == size and gitblob(body) == blob
            and hashlib.sha256(body).hexdigest() == digest,
            "pinned public source identity changed")
    return body


def streaming_sha256(path, *, maximum=16 * 1024**3):
    n = 0
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while True:
            block = stream.read(4 * 1024 * 1024)
            if not block:
                break
            n += len(block)
            require(n <= maximum, "archive digest exceeded configured byte budget")
            digest.update(block)
    return digest.hexdigest(), n


def local_hash(path, size, sha):
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_uid == 0
            and not stat.S_IMODE(info.st_mode) & 0o022
            and info.st_size == size, "local provider source metadata changed")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    hashed = hashlib.sha256()
    count = 0
    try:
        before = os.fstat(fd)
        while True:
            block = os.read(fd, 4 * 1024 * 1024)
            if not block:
                break
            hashed.update(block)
            count += len(block)
            require(count <= size, "local asset byte bound exceeded")
        after = os.fstat(fd)
    finally:
        os.close(fd)
    require(count == size and hashed.hexdigest() == sha
            and (before.st_dev, before.st_ino, before.st_size) ==
                (after.st_dev, after.st_ino, after.st_size),
            "local provider asset digest or inode changed")
    return {"sha256": sha, "bytes": size, "host_uid": 0}


def run(cmd, *, cwd, timeout=150, env=None):
    child = subprocess.run(cmd, cwd=str(cwd),
                           env=env or os.environ.copy(),
                           stdin=subprocess.DEVNULL,
                           capture_output=True, timeout=timeout)
    require(child.returncode == 0
            and len(child.stdout) <= 32768
            and len(child.stderr) <= 32768,
            "bounded command failed: " + Path(cmd[0]).name + " " +
            child.stderr.decode("utf-8", "replace")[-220:])
    return child.stdout


def _run_packaged_version(cmd, *, cwd, timeout, env):
    """Run only an exact reviewed ELF's --version with no inherited credentials."""
    child = subprocess.run(cmd, cwd=str(cwd), env=env,
                           stdin=subprocess.DEVNULL,
                           capture_output=True, timeout=timeout)
    output = child.stdout + child.stderr
    require(child.returncode == 0 and 0 < len(output) <= 8192,
            "packaged inference executable version check failed")
    return output


def probe_packaged_llama(*, archive_root, expected_sha256, expected_bytes, runner):
    """A native ELF startup probe, not yet a GGUF inference acceptance test."""
    root = Path(archive_root)
    if (root.name != "Merlin_Studio" or not root.is_dir() or root.is_symlink()
            or not isinstance(expected_sha256, str)
            or re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None
            or type(expected_bytes) is not int
            or not 64 <= expected_bytes <= 512 * 1024 * 1024
            or not callable(runner)):
        raise ValueError("exact bounded extracted inference release required")
    executable = root / "bin" / "llama-server"
    try:
        st = executable.lstat()
    except FileNotFoundError as exc:
        raise ValueError("packaged inference executable absent") from exc
    if (not stat.S_ISREG(st.st_mode) or st.st_size != expected_bytes
            or stat.S_IMODE(st.st_mode) != 0o755
            or st.st_nlink != 1):
        raise ValueError("packaged inference ELF metadata differs")
    digest, size = streaming_sha256(executable, maximum=512 * 1024 * 1024)
    if digest != expected_sha256 or size != expected_bytes:
        raise ValueError("packaged inference ELF digest differs")
    with executable.open("rb") as stream:
        header = stream.read(20)
    if (len(header) != 20 or header[:6] != b"\x7fELF\x02\x01"
            or struct.unpack("<H", header[18:20])[0] != 183):
        raise ValueError("packaged inference executable is not Linux aarch64 ELF")
    output = runner([str(executable), "--version"], cwd=root, timeout=20,
                    env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8",
                         "HOME": str(root), "PYTHONDONTWRITEBYTECODE": "1"})
    if not isinstance(output, bytes) or not 0 < len(output) <= 8192:
        raise ValueError("packaged executable returned no bounded version output")
    return {"native_llama_binary_started": True,
            "model_inference_executed": False,
            "llama_sha256": expected_sha256,
            "llama_version_output_sha256": hashlib.sha256(output).hexdigest(),
            "llama_version_excerpt": output.decode("utf-8", "replace").strip()[:120],
            "production_qualified": False}


def source_tree(root, evidence):
    target = root / "source"
    target.mkdir(mode=0o700)
    env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": str(root),
           "GIT_TERMINAL_PROMPT": "0", "GIT_LFS_SKIP_SMUDGE": "1",
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_ALLOW_PROTOCOL": "https"}
    command = lambda args, limit=150: run(["/usr/bin/git", "-C", str(target), *args],
                                          cwd=root, timeout=limit, env=env)
    command(["init", "-q"])
    command(["remote", "add", "origin", "https://github.com/" + SOURCE_REPO + ".git"])
    command(["sparse-checkout", "init", "--cone"])
    command(["sparse-checkout", "set", "portable", "python/merlin",
             "cpp/include/expert_robot", "cpp/src", "scripts"])
    command(["fetch", "--quiet", "--depth=1", "--filter=blob:none",
             "origin", SOURCE_SHA], 270)
    command(["checkout", "--quiet", "--detach", "FETCH_HEAD"], 180)
    require(command(["rev-parse", "HEAD"]).decode().strip() == SOURCE_SHA,
            "checked-out product source differs")
    require(command(["status", "--porcelain", "--untracked-files=no"]) == b"",
            "source tree is dirty")
    for path in ("README.md", "portable/build_portable.py",
                 "portable/build_offline_profile.py",
                 "scripts/verify_offline_profile.py",
                 "scripts/extract_offline_profile.py"):
        require((target / path).is_file(), "sparse source lacks: " + path)
    (evidence / "source-sha.txt").write_text(SOURCE_SHA + "\n")
    return target


def public_license(url, expected_host, expected_text, *, expected_sha256):
    require(isinstance(expected_sha256, str)
            and re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is not None,
            "explicit pinned license digest required")
    parsed = urllib.parse.urlsplit(url)
    require(parsed.scheme == "https" and parsed.hostname == expected_host
            and parsed.username is None and parsed.password is None
            and parsed.port in (None, 443), "license URI is not fixed HTTPS publisher")
    req = urllib.request.Request(url,
        headers={"User-Agent": "Merlin-private-license-receipt/1",
                 "Accept": "text/plain"})
    with urllib.request.urlopen(req, timeout=30) as res:
        actual = urllib.parse.urlsplit(res.url)
        require(actual.scheme == "https" and actual.hostname == expected_host
                and actual.port in (None, 443), "license redirected off publisher")
        body = res.read(131073)
    require(150 <= len(body) <= 131072
            and expected_text.lower() in body.decode("utf-8").lower(),
            "official license text differs from expected marker")
    require(hashlib.sha256(body).hexdigest() == expected_sha256,
            "upstream license receipt digest differs")
    return body


def assemble(root, evidence, archive, details):
    source = source_tree(root, evidence)
    out = root / "Merlin-Studio-source-only.zip"
    run(["/usr/bin/python3", "-I", "-B",
         str(source / "portable/build_portable.py"),
         "--output", str(out)], cwd=source, timeout=150)
    run(["/usr/bin/python3", "-I", "-B",
         str(source / "scripts/verify_portable.py"),
         str(out)], cwd=source, timeout=75)
    details["source_only_zip_sha256"] = hashlib.sha256(out.read_bytes()).hexdigest()
    python_dir = root / "private-python"
    python_dir.mkdir(mode=0o700)
    stage_script = root / "python-stage.py"
    script = content_from_repo(SOURCE_REPO, "scripts/merlin_python_private_stage.py",
                               STAGE_COMMIT, 13722, STAGE_BLOB, STAGE_SHA256)
    stage_script.write_bytes(script)
    response = run(["/usr/bin/python3", "-I", "-B", str(stage_script),
                    "--archive", str(archive), "--parent", str(python_dir),
                    "--stage"], cwd=root, timeout=160,
                   env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8",
                        "HOME": str(root), "PYTHONDONTWRITEBYTECODE": "1"})
    stage = json.loads(response)
    require(stage.get("schema") == "merlin-private-cpython-stage/1"
            and stage.get("staged_files") == 3900
            and stage.get("symlink_entries") == 1049
            and stage.get("entrypoint_sha256") == PY_SHA,
            "Python interpreter staging evidence differs")
    root_python = Path(stage["staging_path"]) / "python"
    py = root_python / "bin/python3"
    require(py.is_file() and py.resolve(strict=True).is_relative_to(root_python),
            "staged Python entrypoint absent or escaped")
    details["python_archive_files"] = 3900
    details["python_safe_links"] = 1049
    notices = root / "notices"
    notices.mkdir(mode=0o700)
    qwen_notice = notices / "QWEN_LICENSE"
    llama_notice = notices / "LLAMA_LICENSE"
    py_notice = notices / "PYTHON_LICENSE"
    qwen_url = MODEL_ORIGIN + "/raw/main/LICENSE"
    qwen_notice.write_bytes(public_license(
        qwen_url, "huggingface.co", "Apache License",
        expected_sha256=LICENSE_PINS["qwen"]))
    # Exact upstream llama.cpp commit, not a moving master branch.
    llama_url = ("https://raw.githubusercontent.com/ggml-org/llama.cpp/"
                 + LLAMA_SOURCE_COMMIT + "/LICENSE")
    llama_notice.write_bytes(public_license(
        llama_url, "raw.githubusercontent.com", "MIT License",
        expected_sha256=LICENSE_PINS["llama"]))
    # python-build-standalone places the CPython license inside lib/python3.11
    # in the pinned extraction, rather than at the extracted runtime root.
    # Reject missing, symlinked, duplicate, or out-of-root notices.
    candidates = (root_python / "LICENSE.txt",
                  root_python / "lib/python3.11/LICENSE.txt")
    eligible = [path for path in candidates
                if path.is_file() and not path.is_symlink()
                and path.resolve(strict=True).is_relative_to(root_python.resolve(strict=True))
                and 150 <= path.stat().st_size <= 131072]
    require(len(eligible) == 1,
            "expected exactly one safe standalone Python license receipt")
    original_python_license = eligible[0]
    require(hashlib.sha256(original_python_license.read_bytes()).hexdigest()
            == LICENSE_PINS["python"], "pinned standalone Python license digest differs")
    shutil.copyfile(original_python_license, py_notice)
    details["python_license_path_in_runtime"] = original_python_license.relative_to(root_python).as_posix()
    details["license_receipts"] = {
        "model": {"source": qwen_url, "sha256": hashlib.sha256(qwen_notice.read_bytes()).hexdigest()},
        "inference": {"source": llama_url, "sha256": hashlib.sha256(llama_notice.read_bytes()).hexdigest()},
        "python": {"source": PY_ORIGIN, "sha256": hashlib.sha256(py_notice.read_bytes()).hexdigest()},
    }
    bundle = root / "Merlin-Studio-ARM64-private-technical.zip"
    cmd = ["/usr/bin/python3", "-I", "-B",
           str(source / "portable/build_offline_profile.py"),
           "--studio-zip", str(out), "--python-root", str(root_python),
           "--python-sha256", PY_SHA, "--llama-server", str(LLAMA),
           "--llama-sha256", LLAMA_SHA, "--gguf-model", str(GGUF),
           "--gguf-sha256", GGUF_SHA,
           "--model-license", str(qwen_notice),
           "--inference-license", str(llama_notice),
           "--python-license", str(py_notice),
           "--target", "linux-aarch64", "--model-origin", MODEL_ORIGIN,
           "--inference-origin", LLAMA_ORIGIN, "--python-origin", PY_ORIGIN,
           "--output", str(bundle)]
    run(cmd, cwd=source, timeout=530)
    verified = run(["/usr/bin/python3", "-I", "-B",
                    str(source / "scripts/verify_offline_profile.py"),
                    str(bundle)], cwd=source, timeout=190)
    verification = json.loads(verified)
    require(verification["verified"] is True
            and verification["contains_model_weights"] is True
            and verification["contains_python_runtime"] is True
            and verification["target_platform"] == "linux-aarch64"
            and verification["production_qualified"] is False,
            "complete native package integrity differs")
    details["complete_package_sha256"], details["complete_package_size"] = (
        streaming_sha256(bundle))
    details["manifest_files_verified"] = verification["files_checked"]
    details["package_integrity_passed"] = True
    # Use the separately verified safe extractor to preserve all POSIX links.
    destination = root / "private-install"
    extracted = run(["/usr/bin/python3", "-I", "-B",
                     str(source / "scripts/extract_offline_profile.py"),
                     str(bundle), "--destination", str(destination)],
                    cwd=source, timeout=250)
    extract_report = json.loads(extracted)
    require(extract_report["status"] == "extracted_unqualified"
            and extract_report["restored_safe_symlinks"] >= 1049,
            "native package extraction did not restore runtime links")
    details["extracted_regular_files"] = extract_report["written_regular_files"]
    details["restored_symlinks"] = extract_report["restored_safe_symlinks"]
    binary = destination / "Merlin_Studio/runtime/python/bin/python3"
    require(binary.is_file() and binary.resolve(strict=True).is_relative_to(destination),
            "packaged Python entrypoint unavailable")
    version = run([str(binary), "-I", "-B", "-S", "-c",
                   "import sys; print(sys.version.split()[0])"],
                  cwd=destination,
                  env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8",
                       "HOME": str(root), "PYTHONDONTWRITEBYTECODE": "1"},
                  timeout=20).decode("ascii").strip()
    require(version.startswith("3.11."), "real packaged Python 3.11 did not execute")
    details["packaged_python_version"] = version
    details["actual_packaged_python_executed"] = True
    details.update(probe_packaged_llama(
        archive_root=destination / "Merlin_Studio",
        expected_sha256=LLAMA_SHA, expected_bytes=14614984,
        runner=_run_packaged_version))
    # The isolated GGUF test helper is a distinct exact-pinned Git source.
    # No untrusted archive text may substitute the test program.
    module_path = Path(__file__).resolve().parent / "run_packaged_model_from_zip.py"
    require(module_path.is_file() and not module_path.is_symlink()
            and module_path.stat().st_size == 16661
            and hashlib.sha256(module_path.read_bytes()).hexdigest()
            == "776d7c7a17a67b89c82ba68a7192099a9baa16c67c101cdac71ee751cf31d31c",
            "packaged model isolated inference source pin differs")
    sys.path.insert(0, str(module_path.parent))
    from run_packaged_model_from_zip import invoke
    model_scratch = root / "isolated-model-smoke"
    model_scratch.mkdir(mode=0o700, exist_ok=False)
    model_probe = invoke(destination / "Merlin_Studio", model_scratch)
    require(model_probe["model_inference_executed"] is True
            and model_probe["model_process_terminated"] is True
            and model_probe["host_mutations"] == 0
            and model_probe["external_network_allowed"] is False,
            "private bundled model did not complete verified generation")
    details["private_model_smoke_status"] = model_probe["status"]
    details["model_inference_executed"] = True
    details["packaged_model_answer_exact_42"] = model_probe["answer_exact_42"]
    details["packaged_model_response_sha256"] = model_probe["answer_sha256"]
    details["model_process_terminated"] = True
    details["private_network_loopback_only"] = True
    return details


def main():
    run_id = int(os.environ["GITHUB_RUN_ID"])
    attempt = int(os.environ["GITHUB_RUN_ATTEMPT"])
    sha = os.environ["GITHUB_SHA"]
    if (os.environ["GITHUB_REPOSITORY"] != REPO
        or os.environ["GITHUB_REF"] != "refs/heads/" + BRANCH
        or os.environ.get("RUNNER_NAME") != "cace-oci-a1"
        or os.geteuid() != 1000 or platform.machine() != "aarch64"
        or attempt != 1 or re.fullmatch(r"[0-9a-f]{40}", sha) is None):
        raise SystemExit("unexpected OCI runner, project, source or privilege")
    scratch = Path(os.environ["RUNNER_TEMP"]) / (
        "merlin-native-offline-bundle-%d-%d" % (run_id, attempt))
    scratch.mkdir(mode=0o700, exist_ok=False)
    evidence = scratch / "evidence"
    evidence.mkdir(mode=0o700)
    result = {"schema": "merlin-private-native-offline-zip/1",
              "status": "blocked", "source_commit": SOURCE_SHA,
              "runner_commit": sha, "host_mutations": 0,
              "provider_modified": False, "model_weights_exported": False,
              "archive_published": False, "model_inference_executed": False,
              "license_review_complete": False, "production_qualified": False}
    success = False
    try:
        changes = gh_api(REPO, "commits/" + sha).get("files", [])
        require(len(changes) == 1 and changes[0].get("status") == "added",
                "exact additive request required")
        name = changes[0]["filename"]
        match = re.fullmatch(
            r"merlin/oci-native-offline-bundle-requests/([0-9a-f-]{36})\.json",
            name)
        require(match is not None, "unexpected request path")
        item = gh_api(REPO, "contents/" + name + "?ref=" + sha)
        require(item.get("encoding") == "base64", "request source format differs")
        raw = base64.b64decode("".join(item["content"].split()), validate=True)
        request = json.loads(raw)
        require(len(raw) < 4096 and item["sha"] == gitblob(raw)
                and set(request) == {"schema", "request_id", "operation", "created_at"}
                and request["schema"] == "merlin-oci-native-offline-bundle-request/1"
                and request["operation"] == "assemble-private-arm64-zip-and-run-python"
                and request["request_id"] == match.group(1)
                and request["request_id"] == str(uuid.UUID(request["request_id"]))
                and datetime.datetime.strptime(request["created_at"], "%Y-%m-%dT%H:%M:%SZ"),
                "native technical bundle request differs")
        result["request_id"] = request["request_id"]
        archive_parent = Path(os.environ["RUNNER_TEMP"]) / (
            "merlin-native-offline-python-%d-%d" % (run_id, attempt))
        py_archive = archive_parent / "archive.data"
        require(py_archive.is_file() and not py_archive.is_symlink()
                and py_archive.stat().st_size == PY_ARCHIVE_BYTES,
                "pinned CPython archive unavailable")
        result["provider_model"] = local_hash(GGUF, 1117320768, GGUF_SHA)
        result["provider_inference"] = local_hash(LLAMA, 14614984, LLAMA_SHA)
        require(shutil.disk_usage(scratch).free >= 12 * 1024**3,
                "insufficient scratch storage for private ZIP and extract")
        prepared = assemble(scratch, evidence, py_archive, result)
        require(prepared["package_integrity_passed"]
                and prepared["actual_packaged_python_executed"]
                and prepared["native_llama_binary_started"]
                and prepared["model_inference_executed"] is True
                and prepared["model_process_terminated"] is True,
                "private bundle acceptance incomplete")
        result["status"] = "private_package_python_llama_and_gguf_smoke_passed"
        success = True
    except BaseException as exc:
        result["failure_type"] = type(exc).__name__
        result["failure_reason"] = str(exc)[:380]
    finally:
        # Never retain full model, model ZIP or untrusted copied assets.
        try:
            for path in list(scratch.iterdir()):
                if path != evidence:
                    if path.is_dir() and not path.is_symlink():
                        shutil.rmtree(path)
                    elif path.is_file() or path.is_symlink():
                        path.unlink()
            result["scratch_cleaned"] = True
        except BaseException as exc:
            result["scratch_cleaned"] = False
            result["cleanup_error_type"] = type(exc).__name__
            success = False
        (evidence / "result.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
        print(json.dumps({"status": result["status"],
            "package_verified": result.get("package_integrity_passed", False),
            "packaged_python_executed": result.get("actual_packaged_python_executed", False),
            "scratch_cleaned": result.get("scratch_cleaned", False),
            "production_qualified": False}, sort_keys=True))
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
