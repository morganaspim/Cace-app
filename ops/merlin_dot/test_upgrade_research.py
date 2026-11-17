from contextlib import ExitStack
import hashlib
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import install_private
import upgrade_research as target


class ResearchUpgradeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.releases = self.source / "releases"
        self.releases.mkdir(parents=True)
        self.config_dir = self.root / "etc"
        self.config_dir.mkdir()
        self.unit_dir = self.root / "units"
        self.unit_dir.mkdir()
        self.config = self.config_dir / "config.json"
        self.unit = self.unit_dir / target.SERVICE
        fixture = Path(__file__).with_name("merlin-dot-private-runtime-only.zip")
        old_raw = fixture.read_bytes()
        self.assertEqual(hashlib.sha256(old_raw).hexdigest(), target.OLD_SHA)
        self.old = self.releases / target.OLD_SHA
        self.old_manifest = install_private.unpack_verified(old_raw, target.OLD_SHA, self.old)
        with zipfile.ZipFile(io.BytesIO(old_raw)) as archive:
            self.old_contents = {name: archive.read(name) for name in archive.namelist() if name != "manifest.json"}
        self.unit.write_bytes(self.old_contents["ops/merlin-dot-private.service"])
        self.source.joinpath("current").symlink_to(self.old)
        self.old_config = {"schema": "merlin-private-host/1", "project_id": "dot-production-docs",
            "namespaces": ["merlin", "expert-robot"], "grants": [{"uid": 1000,
            "principal": "local-runner-opc", "tools": ["health", "context_status", "context_search",
            "context_fetch", "session_handoff", "rsi_status", "virtual_circuit_demo"]}]}
        self.old_config_raw = (json.dumps(self.old_config, indent=2) + "\n").encode()
        self.assertEqual(hashlib.sha256(self.old_config_raw).hexdigest(), target.OLD_CONFIG_SHA)
        self.config.write_bytes(self.old_config_raw)
        for directory in (self.source, self.releases, self.config_dir, self.unit_dir):
            directory.chmod(0o755)
        self.config.chmod(0o644)
        self.unit.chmod(0o644)
        self.calls = []
        self.restart_count = 0
        self.stop_count = 0
        self.fail_first_activation = False
        self.fail_all_restarts = False
        self.fail_first_stop = False
        self.fail_new_probe = False
        self.probes = []

    def bundle(self, changes=None):
        content = dict(self.old_contents)
        for name in ["research_protocol", "research_tools", "math_lenses"]:
            content["python/dot_ai_os/" + name + ".py"] = b"# Synthetic upgrade orchestration fixture; never executed.\n"
        content["python/dot_ai_os/private_runtime.py"] += b"\n# versioned test fixture\n"
        content["research-policy/SKILL.md"] = b"Synthetic method policy fixture.\n"
        content.update(changes or {})
        manifest = {"schema": "merlin-dot-release/1", "source_repository": "Mannyspiro/expert-robot",
                    "source_base_commit": "b" * 40,
                    "files": {name: hashlib.sha256(raw).hexdigest() for name, raw in content.items()}}
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, raw in content.items():
                archive.writestr(name, raw)
            archive.writestr("manifest.json", json.dumps(manifest, indent=2).encode())
        raw = output.getvalue()
        self.newsha = hashlib.sha256(raw).hexdigest()
        self.bundle_path = self.root / "new.zip"
        self.bundle_path.write_bytes(raw)
        self.new = self.releases / self.newsha
        return self.bundle_path, self.newsha

    def systemctl(self, action):
        self.calls.append(action)
        if action == "stop":
            self.stop_count += 1
            if self.fail_first_stop and self.stop_count == 1:
                raise subprocess.TimeoutExpired("fixed-service-stop", 30)
            return ""
        if action == "restart":
            self.restart_count += 1
            if self.fail_all_restarts:
                raise subprocess.CalledProcessError(1, "fixed-service-restart")
            return ""
        active = not (self.fail_first_activation and self.restart_count == 1)
        return "\n".join(["ActiveState=" + ("active" if active else "failed"),
            "SubState=" + ("running" if active else "failed"), "UnitFileState=enabled",
            "User=merlin-dot", "Group=opc", "PrivateNetwork=yes", "NoNewPrivileges=yes",
            "RestrictAddressFamilies=AF_UNIX", "DropInPaths="])

    def run_upgrade(self):
        # Simulate root ownership with this test user's owned fixture paths. No
        # actual root privileges, systemd, state seeding or VM access are used.
        with ExitStack() as stack:
            for name, value in [("ROOT_UID", os.geteuid()), ("SOURCE", self.source),
                                ("CONFIG", self.config), ("UNIT", self.unit)]:
                stack.enter_context(patch.object(target, name, value))
            stack.enter_context(patch.object(target.pwd, "getpwnam", side_effect=lambda name:
                SimpleNamespace(pw_uid=982 if name == "merlin-dot" else 1000)))
            stack.enter_context(patch.object(target, "_systemctl", side_effect=self.systemctl))
            stack.enter_context(patch.object(target.time, "sleep"))
            def probe(release, research=True):
                self.probes.append((release, research))
                if research and self.fail_new_probe:
                    raise RuntimeError("fixed new tool unavailable")
                return {"fixture_probe": True, "research": research}
            stack.enter_context(patch.object(target, "_probe_tools", side_effect=probe))
            return target.upgrade(self.bundle_path, self.newsha, install_private.unpack_verified)

    def test_success_preserves_v1_and_only_adds_three_readonly_grants(self):
        self.bundle()
        result = self.run_upgrade()
        self.assertEqual(result["status"], "upgraded")
        self.assertEqual(os.readlink(self.source / "current"), str(self.new))
        config = json.loads(self.config.read_text())
        expected = dict(self.old_config)
        expected["grants"] = [dict(self.old_config["grants"][0])]
        expected["grants"][0]["tools"] = self.old_config["grants"][0]["tools"] + list(target.NEW_TOOLS)
        self.assertEqual(config, expected)
        self.assertTrue(self.old.is_dir() and self.new.is_dir())
        self.assertEqual(self.unit.read_bytes(), self.old_contents["ops/merlin-dot-private.service"])
        self.assertEqual(Path(result["config_backup"]).read_bytes(), self.old_config_raw)
        self.assertEqual(self.calls.count("stop"), 1)
        self.assertEqual(self.calls.count("restart"), 1)
        self.assertFalse(result["state_seed_changed"])
        self.assertFalse(result["promotion_authority"])

    def test_failed_activation_rolls_back_exact_link_config_and_keeps_releases(self):
        self.bundle()
        self.fail_first_activation = True
        result = self.run_upgrade()
        self.assertEqual(result["status"], "rolled_back")
        self.assertEqual(os.readlink(self.source / "current"), str(self.old))
        self.assertEqual(self.config.read_bytes(), self.old_config_raw)
        self.assertTrue(self.old.is_dir() and self.new.is_dir())
        self.assertEqual(self.calls.count("stop"), 2)
        self.assertEqual(self.calls.count("restart"), 2)

    def test_failed_rollback_is_explicit(self):
        self.bundle()
        self.fail_all_restarts = True
        result = self.run_upgrade()
        self.assertEqual(result["status"], "rollback_failed")
        self.assertIn("rollback_error_class", result["service_properties"])
        self.assertEqual(os.readlink(self.source / "current"), str(self.old))
        self.assertEqual(self.config.read_bytes(), self.old_config_raw)

    def test_ambiguous_stop_still_attempts_old_service_recovery(self):
        self.bundle()
        self.fail_first_stop = True
        result = self.run_upgrade()
        self.assertEqual(result["status"], "rolled_back")
        self.assertGreaterEqual(self.calls.count("restart"), 1)
        self.assertEqual(self.config.read_bytes(), self.old_config_raw)

    def test_umask_077_does_not_make_new_release_or_config_unreadable(self):
        self.bundle()
        previous = os.umask(0o077)
        try:
            result = self.run_upgrade()
        finally:
            os.umask(previous)
        self.assertEqual(result["status"], "upgraded")
        self.assertEqual(stat.S_IMODE(self.config.stat().st_mode), 0o644)
        self.assertEqual(stat.S_IMODE(self.new.stat().st_mode), 0o755)
        self.assertEqual(stat.S_IMODE(Path(result["config_backup"]).stat().st_mode), 0o600)

    def test_old_unit_config_and_source_tamper_fail_before_service_stop(self):
        for selected in [self.unit, self.config, self.old / "python/merlin/project_registry.py"]:
            original = selected.read_bytes()
            self.bundle()
            selected.write_bytes(original + b"tamper")
            try:
                with self.assertRaises(RuntimeError):
                    self.run_upgrade()
            finally:
                selected.write_bytes(original)
            self.assertNotIn("stop", self.calls)
            self.assertFalse(self.new.exists())

    def test_changed_unit_seed_canonical_dependency_or_nonruntime_payload_rejected(self):
        changes = [{"ops/merlin-dot-private.service": b"changed unit"},
                   {"seed-documents.json": b"private data prohibited"},
                   {"python/merlin/engineering_ir.py": b"changed canonical dependency"},
                   {"raw-context/export.txt": b"private data prohibited"}]
        for change in changes:
            self.bundle(change)
            with self.subTest(change=next(iter(change))), self.assertRaises(RuntimeError):
                self.run_upgrade()
            self.assertFalse(self.new.exists())
            self.assertNotIn("stop", self.calls)

    def test_existing_new_release_is_not_overwritten(self):
        self.bundle()
        self.new.mkdir()
        sentinel = self.new / "sentinel"
        sentinel.write_text("preserve")
        with self.assertRaises(RuntimeError):
            self.run_upgrade()
        self.assertEqual(sentinel.read_text(), "preserve")
        self.assertNotIn("stop", self.calls)

    def test_unexpected_current_link_or_writable_parent_rejected(self):
        self.bundle()
        current = self.source / "current"
        current.unlink()
        current.symlink_to(self.releases / "unexpected")
        with self.assertRaises(RuntimeError):
            self.run_upgrade()
        current.unlink()
        current.symlink_to(self.old)
        self.config_dir.chmod(0o775)
        with self.assertRaises(RuntimeError):
            self.run_upgrade()
        self.assertNotIn("stop", self.calls)

    def test_production_entry_rejects_nonroot(self):
        self.bundle()
        with patch.object(target.os, "geteuid", return_value=1000):
            with self.assertRaises(PermissionError):
                target.upgrade(self.bundle_path, self.newsha, install_private.unpack_verified)

    def test_failed_fixed_tool_probe_rolls_back_even_when_systemd_is_active(self):
        self.bundle()
        self.fail_new_probe = True
        result = self.run_upgrade()
        self.assertEqual(result["status"], "rolled_back")
        self.assertEqual(self.config.read_bytes(), self.old_config_raw)
        self.assertEqual(os.readlink(self.source / "current"), str(self.old))
        self.assertEqual(self.probes, [(self.new, True), (self.old, False)])

    def test_rename_then_fsync_error_still_restores_actual_current_target(self):
        self.bundle()
        original = target._sync
        failed = []
        def sync(path):
            if path == self.source and not failed:
                failed.append(True)
                raise OSError("fixture fsync error after pointer rename")
            return original(path)
        with patch.object(target, "_sync", side_effect=sync):
            result = self.run_upgrade()
        self.assertEqual(result["status"], "rolled_back")
        self.assertEqual(os.readlink(self.source / "current"), str(self.old))
        self.assertEqual(self.config.read_bytes(), self.old_config_raw)

    def test_fixed_probe_uses_isolated_verified_import_and_exact_peer_uid(self):
        report = {"tools": {name: {"ok": True} for name in ("health",) + target.NEW_TOOLS},
                  "job_submit": "tool_not_allowed"}
        with patch.object(target.subprocess, "run", return_value=SimpleNamespace(stdout=json.dumps(report))) as call:
            self.assertEqual(target._probe_tools(self.old), report)
        args, options = call.call_args
        self.assertEqual(args[0][:4], ["/usr/bin/python3", "-I", "-B", "-c"])
        self.assertEqual(options["user"], 1000)
        self.assertEqual(options["group"], 1000)
        self.assertEqual(options["extra_groups"], [])
        self.assertEqual(options["cwd"], str(self.old))
        self.assertEqual(options["env"], target.SAFE_ENV)

    def test_config_rename_then_fsync_error_restores_actual_config_bytes(self):
        self.bundle()
        original = target._sync
        calls = []
        def sync(path):
            if path == self.config_dir:
                calls.append(path)
                # _new_file fsyncs the parent once; replacement then fsyncs
                # it again. Inject after the replacement has actually happened.
                if len(calls) == 2:
                    raise OSError("fixture fsync error after config rename")
            return original(path)
        with patch.object(target, "_sync", side_effect=sync):
            result = self.run_upgrade()
        self.assertEqual(result["status"], "rolled_back")
        self.assertEqual(os.readlink(self.source / "current"), str(self.old))
        self.assertEqual(self.config.read_bytes(), self.old_config_raw)


if __name__ == "__main__":
    unittest.main()
