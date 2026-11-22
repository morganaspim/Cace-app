"""Offline failure-injection tests for fixed stale-browser-socket handoff."""
from __future__ import annotations
import copy
import os
from pathlib import Path
import socket
import stat
import tempfile
import unittest

from quarantine_stale_socket import classify_live_gate, quarantine_same_inode

SERVICE = {
    "LoadState": "loaded", "ActiveState": "inactive", "SubState": "dead",
    "UnitFileState": "disabled", "MainPID": "0", "ControlGroup": "",
    "User": "root", "Group": "root",
    "FragmentPath": "/etc/systemd/system/merlin-public-browser.service",
}


class StaleSocketQuarantineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "browser.sock"
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(str(self.path))
        sock.close()
        os.chmod(self.path, 0o660)
        self.live = os.stat(self.path, follow_symlinks=False)
        self.expected = {
            "dev": self.live.st_dev, "inode": self.live.st_ino,
            "uid": self.live.st_uid, "gid": self.live.st_gid,
            "mode": "0o660", "nlink": self.live.st_nlink,
            "ctime_ns": self.live.st_ctime_ns, "mtime_ns": self.live.st_mtime_ns,
        }

    def gate(self, service=None, listeners=0, observed=None, pair_accepted=True):
        return classify_live_gate(observed if observed is not None else self.live,
                                  self.expected, service if service is not None else SERVICE,
                                  listeners, pair_accepted=pair_accepted)

    def test_exact_stale_inode_is_candidate_not_authority(self):
        out = self.gate()
        self.assertEqual(out["status"], "eligible_for_separate_quarantine_approval")
        self.assertFalse(out["authority_granted"])
        self.assertFalse(out["may_unlink_socket"])
        self.assertEqual(out["host_mutations"], 0)

    def test_active_supervisor_and_nonzero_listener_block(self):
        for key, bad in (("ActiveState", "active"), ("SubState", "running"),
                         ("UnitFileState", "enabled"), ("MainPID", "999"),
                         ("ControlGroup", "/system.slice/merlin-public-browser.service"),
                         ("LoadState", "not-found"), ("User", "opc"), ("Group", "opc")):
            with self.subTest(key=key):
                changed = dict(SERVICE); changed[key] = bad
                self.assertEqual(self.gate(service=changed)["status"], "blocked")
        for listeners in (1, None, -1, False, True):
            with self.subTest(listeners=listeners):
                self.assertEqual(self.gate(listeners=listeners)["status"], "blocked")

    def test_socket_identity_aba_and_wrong_owner_modes_block(self):
        for key, value in (("dev", self.live.st_dev + 1),
                           ("inode", self.live.st_ino + 1),
                           ("uid", self.live.st_uid + 1),
                           ("gid", self.live.st_gid + 1),
                           ("mode", "0o666"),
                           ("nlink", self.live.st_nlink + 1),
                           ("ctime_ns", self.live.st_ctime_ns + 1),
                           ("mtime_ns", self.live.st_mtime_ns + 1)):
            with self.subTest(key=key):
                old = self.expected
                self.expected = dict(old, **{key:value})
                self.assertEqual(self.gate()["status"], "blocked")
                self.expected = old

    def test_pair_verification_not_replaced_by_historical_guess(self):
        self.assertEqual(self.gate(pair_accepted=False)["status"], "blocked")
        self.assertEqual(self.gate(pair_accepted=1)["status"], "blocked")

    def test_regular_file_and_symlink_never_quarantined(self):
        self.path.unlink()
        self.path.write_text("ordinary file")
        self.assertEqual(self.gate(observed=self.path.lstat())["status"], "blocked")
        self.path.unlink()
        self.path.symlink_to(self.root / "other")
        self.assertEqual(self.gate(observed=self.path.lstat())["status"], "blocked")

    def test_atomic_quarantine_preserves_inode_for_explicit_followup(self):
        with os.scandir(self.root):
            fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            receipt = quarantine_same_inode(fd, "browser.sock",
                                            "browser.sock.quarantine-test",
                                            self.expected, precheck=lambda: self.gate(),
                                            postcheck=lambda: SERVICE)
        finally:
            os.close(fd)
        self.assertEqual(receipt["status"], "quarantined")
        self.assertFalse(self.path.exists())
        moved = self.root / "browser.sock.quarantine-test"
        self.assertTrue(moved.exists())
        self.assertEqual(moved.lstat().st_ino, self.live.st_ino)
        self.assertEqual(receipt["socket_inode"], self.live.st_ino)
        self.assertFalse(receipt["production_qualified"])

    def test_postcheck_failure_restores_original_inode(self):
        fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            with self.assertRaisesRegex(RuntimeError, "postcheck"):
                quarantine_same_inode(fd, "browser.sock",
                    "browser.sock.quarantine-test", self.expected,
                    precheck=lambda: self.gate(),
                    postcheck=lambda: {"ActiveState":"active"})
        finally:
            os.close(fd)
        self.assertTrue(self.path.exists())
        self.assertEqual(self.path.lstat().st_ino, self.live.st_ino)
        self.assertFalse((self.root / "browser.sock.quarantine-test").exists())

    def test_quarantine_destination_collision_fails_without_mutation(self):
        target = self.root / "browser.sock.quarantine-test"
        target.write_text("untouched")
        fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            with self.assertRaises(ValueError):
                quarantine_same_inode(fd, "browser.sock",
                    "browser.sock.quarantine-test", self.expected,
                    precheck=lambda: self.gate(), postcheck=lambda: SERVICE)
        finally:
            os.close(fd)
        self.assertTrue(self.path.exists())
        self.assertEqual(target.read_text(), "untouched")

    def test_wrong_source_inode_fails_without_mutation(self):
        expected = dict(self.expected, inode=self.live.st_ino + 1)
        fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            with self.assertRaises(ValueError):
                quarantine_same_inode(fd, "browser.sock",
                    "browser.sock.quarantine-test", expected,
                    precheck=lambda: self.gate(), postcheck=lambda: SERVICE)
        finally:
            os.close(fd)
        self.assertTrue(self.path.exists())

    def test_inactive_gate_required_for_transaction(self):
        fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            with self.assertRaises(ValueError):
                quarantine_same_inode(fd, "browser.sock",
                    "browser.sock.quarantine-test", self.expected,
                    precheck=lambda: self.gate(listeners=1), postcheck=lambda: SERVICE)
        finally:
            os.close(fd)
        self.assertTrue(self.path.exists())

    def test_no_user_selected_paths_or_unbounded_destination(self):
        fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            for name in ("../steal", "/tmp/steal", "browser.sock", "bad/name",
                         "browser.sock.quarantine-" + "a" * 150):
                with self.subTest(name=name):
                    with self.assertRaises(ValueError):
                        quarantine_same_inode(fd, "browser.sock", name, self.expected,
                                              precheck=lambda: self.gate(), postcheck=lambda: SERVICE)
        finally:
            os.close(fd)
        self.assertTrue(self.path.exists())

    def test_source_remains_after_precheck_exception(self):
        fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            with self.assertRaisesRegex(RuntimeError, "no observation"):
                quarantine_same_inode(fd, "browser.sock", "browser.sock.quarantine-test",
                    self.expected, precheck=lambda: (_ for _ in ()).throw(
                        RuntimeError("no observation")), postcheck=lambda: SERVICE)
        finally:
            os.close(fd)
        self.assertTrue(self.path.exists())


    def test_receipt_failure_rolls_back_quarantine_before_reporting_success(self):
        fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        def broken_writer(_):
            raise RuntimeError("read-only disk receipt failure")
        try:
            with self.assertRaisesRegex(RuntimeError, "receipt failure"):
                quarantine_same_inode(fd, "browser.sock",
                    "browser.sock.quarantine-test", self.expected,
                    precheck=lambda: self.gate(), postcheck=lambda: SERVICE,
                    record_receipt=broken_writer)
        finally:
            os.close(fd)
        self.assertEqual(self.path.lstat().st_ino, self.live.st_ino)
        self.assertFalse((self.root / "browser.sock.quarantine-test").exists())

    def test_destination_created_after_absence_check_cannot_be_overwritten(self):
        from unittest.mock import patch
        import quarantine_stale_socket as source
        fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            real = source._atomic_rename_no_replace
            def race(dfd, old, new):
                (self.root / new).write_text("must remain")
                return real(dfd, old, new)
            with patch.object(source, "_atomic_rename_no_replace", side_effect=race):
                with self.assertRaises(FileExistsError):
                    quarantine_same_inode(fd, "browser.sock",
                        "browser.sock.quarantine-test", self.expected,
                        precheck=lambda: self.gate(), postcheck=lambda: SERVICE)
        finally:
            os.close(fd)
        self.assertEqual((self.root / "browser.sock.quarantine-test").read_text(),
                         "must remain")
        self.assertEqual(self.path.lstat().st_ino, self.live.st_ino)



    def test_receipt_writer_handles_short_writes_and_preserves_exact_bytes(self):
        from unittest.mock import patch
        import quarantine_stale_socket as source
        output = self.root / "receipt.json"
        body = {"status": "quarantined", "source": "browser.sock", "automatic_retry": False}
        original = os.write
        def short_write(fd, data):
            return original(fd, data[:max(1, len(data) // 3)])
        with patch.object(source.os, "write", side_effect=short_write):
            source._write_unique_receipt(output, body)
        import json
        self.assertEqual(json.loads(output.read_text()), body)
        with self.assertRaises(FileExistsError):
            source._write_unique_receipt(output, body)

    def test_listener_parser_rejects_malformed_matching_and_duplicate_rows(self):
        import quarantine_stale_socket as source
        empty = b"Num RefCount Protocol Flags Type St Inode Path\n"
        self.assertEqual(source._parse_listeners(empty), 0)
        valid = empty + b"00000000: 00000002 00000000 00010000 0001 01 123 /run/merlin-public-browser/browser.sock\n"
        self.assertEqual(source._parse_listeners(valid), 1)
        with self.assertRaises(ValueError):
            source._parse_listeners(empty + b"/run/merlin-public-browser/browser.sock\n")
        with self.assertRaises(ValueError):
            source._parse_listeners(valid + valid.splitlines()[-1] + b"\n")

    def test_cli_dry_run_does_not_touch_workspace_socket(self):
        from contextlib import redirect_stdout
        from io import StringIO
        import json
        from quarantine_stale_socket import main
        out = StringIO()
        with redirect_stdout(out):
            self.assertEqual(main(["--dry-run"]), 0)
        report = json.loads(out.getvalue())
        self.assertEqual(report["host_mutations"], 0)
        self.assertFalse(report["authority_granted"])
        self.assertEqual(self.path.lstat().st_ino, self.live.st_ino)



if __name__ == "__main__":
    unittest.main(verbosity=2)
