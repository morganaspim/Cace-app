from pathlib import Path
import pytest

from cace_studio.runtime.sandbox import Airlock, SandboxPolicy, GrowthSandbox, SandboxViolation


def test_growth_sandbox_command_is_fail_closed_and_networkless(tmp_path):
    inp = tmp_path / "in"
    out = tmp_path / "out"
    inp.mkdir()
    sandbox = GrowthSandbox(SandboxPolicy(memory_mb=128, cpus=0.5, pids_limit=32), runtime="/usr/bin/podman")
    command = sandbox.build_command(image="example.invalid/cace-growth:locked", argv=["python", "run.py"], input_dir=inp, output_dir=out)
    joined = " ".join(command)
    assert "--network=none" in joined
    assert "--read-only" in joined
    assert "--cap-drop=ALL" in joined
    assert "--security-opt=no-new-privileges" in joined
    assert f"src={inp.resolve()},dst=/cace/input,ro" in joined


def test_airlock_hashes_exact_output_and_requires_matching_human_approval(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "candidate.json").write_text('{"ok":true}\n', encoding="utf-8")
    manifest = Airlock().inspect(out)
    assert manifest.file_count == 1
    approval = Airlock.authorize(
        manifest=manifest,
        reviewer="operator@example",
        approved_manifest_sha256=manifest.sha256,
    )
    assert approval["decision"] == "APPROVED_FOR_IMPORT"
    with pytest.raises(SandboxViolation):
        Airlock.authorize(manifest=manifest, reviewer="operator@example", approved_manifest_sha256="0" * 64)
