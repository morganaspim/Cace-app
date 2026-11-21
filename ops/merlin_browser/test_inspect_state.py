"""Focused local controls for the separate read-only diagnostic.

These are filesystem/IO fixtures, not native browser or product acceptance.
No production path, supervisor, socket, provider or network is contacted.
"""
from contextlib import ExitStack, nullcontext
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import inspect_state as I


def info(kind=stat.S_IFREG, mode=0o600, uid=0, nlink=1, size=0, inode=123):
    return SimpleNamespace(st_mode=kind | mode, st_uid=uid, st_gid=0,
                           st_dev=7, st_ino=inode, st_nlink=nlink,
                           st_size=size, st_mtime_ns=1000, st_ctime_ns=2000)


def request():
    return {"schema": "merlin-browser-state-inspection-request/1",
            "request_id": "a7370d9b-6c49-49f5-93b9-c050bf8724ae",
            "operation": "inspect-state-44956695079", "created_at": "2026-11-21T23:00:00Z"}


def execution():
    return {"repository": "morganaspim/Cace-app",
            "ref": "refs/heads/merlin/browser-operations-20261121",
            "runner": "cace-oci-a1", "run_attempt": 1, "run_id": 44956695080,
            "workflow_commit": "a" * 40}


def unix_table(rows):
    return ("Num RefCount Protocol Flags Type St Inode Path\n" + "\n".join(rows) + "\n").encode()


def unix_row(path, inode=123):
    return "0000000000000000: 00000002 00000000 00010000 0001 01 %d %s" % (inode, path)


class InspectStateControls(unittest.TestCase):
    def setUp(self):
        # Any unexpected host command or global file read fails the control.
        self.io = ExitStack()
        self.addCleanup(self.io.close)
        self.io.enter_context(mock.patch.object(I.B, "command", side_effect=AssertionError("unexpected command")))
        self.io.enter_context(mock.patch.object(I.B, "regular", side_effect=AssertionError("unexpected global file read")))
        self.io.enter_context(mock.patch.object(I.B, "write", side_effect=AssertionError("unexpected evidence write")))

    def path_observation(self, observations, target=None, readlink_error=None):
        with mock.patch.object(I, "parent_fd", side_effect=lambda _: nullcontext(91)), \
                mock.patch.object(I.os, "stat", side_effect=observations) as stats, \
                mock.patch.object(I.os, "readlink", return_value=target, side_effect=readlink_error) as links, \
                mock.patch.object(I.os, "open", side_effect=AssertionError("unexpected path open")):
            result = I.inspect_path(I.GUARD_PATHS[3])
            stat_calls, link_calls = list(stats.call_args_list), list(links.call_args_list)
        return result, stat_calls, link_calls

    def marker_observation(self, raw=b'{"schema":"fixture/1"}\n', before=None,
                           stats=None, fstats=None, reads=None, open_error=None):
        before = before or info(size=len(raw))
        with mock.patch.object(I, "parent_fd", side_effect=lambda _: nullcontext(91)), \
                mock.patch.object(I.os, "stat", side_effect=stats or [before, before]), \
                mock.patch.object(I.os, "fstat", side_effect=fstats or [before, before]), \
                mock.patch.object(I.os, "open", return_value=92, side_effect=open_error) as opened, \
                mock.patch.object(I.os, "read", side_effect=reads or [raw, b""]) as read, \
                mock.patch.object(I.os, "close") as closed:
            result = I.inspect_marker()
            calls = {"open": list(opened.call_args_list), "read": list(read.call_args_list),
                     "close": list(closed.call_args_list)}
        return result, calls

    def test_fixed_scope_has_exact_failed_request_paths(self):
        self.assertEqual(I.OPERATION, "inspect-state-44956695079")
        self.assertEqual(I.FAILED_RUN, 44956695079)
        self.assertEqual(tuple(map(str, I.GUARD_PATHS)), (
            "/var/lib/merlin-browser-bootstrap/3eadad53-ba62-4a35-9578-eebe65420f76",
            "/var/lib/merlin-browser-bootstrap/ledger-successor-from-18106dfc-0a56-4b68-9d30-5d334d7d6a69.json",
            "/opt/merlin-public-browser/releases/ebdca90a42bbb243ac04872bdf3f1210ea20583cce9b4c34c7867af1873cb959",
            "/opt/merlin-public-browser/current",
            "/run/merlin-public-browser/browser.sock",
            "/var/lib/merlin-public-browser/episodes/recovered-arxiv-18106dfc-0a56-4b68-9d30-5d334d7d6a69"))
        self.assertEqual(I.UNIT, "merlin-public-browser.service")
        self.assertEqual(str(I.PROC_UNIX), "/proc/net/unix")

    def test_request_requires_fixed_new_first_attempt_identity(self):
        I.validate_request(request(), execution())
        mutations = [("request", "operation", "complete-ledger-44946846703"),
                     ("request", "request_id", I.FAILED_REQUEST),
                     ("request", "request_id", I.PRIOR_REQUEST),
                     ("request", "created_at", "2026-02-30T23:00:00Z"),
                     ("request", "extra", "ignored?"),
                     ("execution", "run_attempt", 2),
                     ("execution", "run_attempt", True),
                     ("execution", "run_id", I.FAILED_RUN),
                     ("execution", "repository", "other/repository"),
                     ("execution", "workflow_commit", "A" * 40)]
        for kind, key, value in mutations:
            with self.subTest(kind=kind, key=key, value=value):
                req, exe = request(), execution()
                (req if kind == "request" else exe)[key] = value
                with self.assertRaises(I.B.BootstrapError):
                    I.validate_request(req, exe)

    def test_present_metadata_preserves_type_owner_mode_without_opening(self):
        for kind, label in ((stat.S_IFREG, "regular"), (stat.S_IFDIR, "directory"), (stat.S_IFSOCK, "socket")):
            with self.subTest(kind=label):
                metadata = info(kind=kind, uid=982, mode=0o750, size=42)
                result, calls, links = self.path_observation([metadata, metadata])
                self.assertEqual(result["status"], "present")
                self.assertIs(result["exists"], True)
                self.assertEqual(result["metadata"]["type"], label)
                self.assertEqual(result["metadata"]["uid"], 982)
                self.assertEqual(result["metadata"]["mode"], "0o750")
                self.assertEqual(result["metadata"]["bytes"], 42)
                self.assertTrue(all(c.kwargs == {"dir_fd": 91, "follow_symlinks": False} for c in calls))
                self.assertEqual(links, [])

    def test_missing_path_is_absent_without_claiming_other_paths(self):
        result, calls, links = self.path_observation([FileNotFoundError("fixture missing")])
        self.assertEqual(result["status"], "absent")
        self.assertIs(result["exists"], False)
        self.assertNotIn("metadata", result)
        self.assertEqual(len(calls), 1)
        self.assertEqual(links, [])

    def test_path_permission_error_is_unknown_not_absent(self):
        result, _, _ = self.path_observation([PermissionError("fixture denied")])
        self.assertEqual(result["status"], "unknown")
        self.assertIsNone(result["exists"])
        self.assertEqual(result["error"]["type"], "PermissionError")

    def test_symlink_reports_literal_target_without_following(self):
        metadata = info(kind=stat.S_IFLNK, mode=0o777)
        result, calls, links = self.path_observation([metadata, metadata], target="../releases/missing-target")
        self.assertEqual(result["status"], "present")
        self.assertEqual(result["readlink"], "../releases/missing-target")
        self.assertIs(result["follows_symlinks"], False)
        self.assertEqual(len(calls), 2)
        self.assertEqual(links, [mock.call("current", dir_fd=91)])

    def test_readlink_error_or_overlimit_target_is_unknown(self):
        metadata = info(kind=stat.S_IFLNK, mode=0o777)
        for target, error in ((None, PermissionError("fixture denied")), ("x" * (I.READLINK_LIMIT + 1), None)):
            with self.subTest(error=type(error).__name__ if error else "overlimit"):
                result, _, _ = self.path_observation([metadata, metadata], target=target, readlink_error=error)
                self.assertEqual(result["status"], "unknown")
                self.assertNotIn("readlink", result)

    def test_disappearing_or_changed_path_is_unknown_after_first_observation(self):
        before = info()
        for after in (FileNotFoundError("fixture disappeared"), info(inode=456)):
            with self.subTest(after=type(after).__name__):
                result, _, _ = self.path_observation([before, after])
                self.assertEqual(result["status"], "unknown")
                self.assertIs(result["exists"], True)

    def test_real_local_parent_symlink_is_refused(self):
        with tempfile.TemporaryDirectory(prefix="merlin-state-control-") as root:
            root = Path(root)
            (root / "target").mkdir()
            (root / "target" / "leaf").write_bytes(b"fixture")
            (root / "link").symlink_to("target", target_is_directory=True)
            direct = I.inspect_path(root / "target" / "leaf")
            linked = I.inspect_path(root / "link" / "leaf")
        self.assertEqual(direct["status"], "present")
        self.assertEqual(linked["status"], "unknown")
        self.assertIsNone(linked["exists"])

    def test_trusted_marker_preserves_exact_json_bytes_and_hash_only(self):
        raw = b'{ "schema" : "fixture/1", "value": 7 }\n'
        result, calls = self.marker_observation(raw)
        self.assertEqual(result["status"], "observed")
        self.assertIs(result["verified"], True)
        self.assertEqual(result["raw_json_utf8"].encode(), raw)
        self.assertEqual(result["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(result["bytes"], len(raw))
        self.assertIs(result["lineage_qualification"], False)
        flags = calls["open"][0].args[1]
        self.assertTrue(flags & os.O_NOFOLLOW)
        self.assertTrue(flags & os.O_NONBLOCK)
        self.assertEqual(calls["open"][0].kwargs, {"dir_fd": 91})
        self.assertEqual(calls["close"], [mock.call(92)])

    def test_untrusted_marker_is_never_opened_or_exported(self):
        variants = [info(kind=stat.S_IFLNK), info(kind=stat.S_IFDIR), info(kind=stat.S_IFSOCK),
                    info(uid=1000), info(mode=0o620), info(mode=0o602), info(nlink=2),
                    info(size=I.MARKER_LIMIT + 1)]
        for value in variants:
            with self.subTest(metadata=I.metadata(value)):
                result, calls = self.marker_observation(before=value)
                self.assertEqual(result["status"], "unknown")
                self.assertIs(result["verified"], False)
                self.assertNotIn("raw_json_utf8", result)
                self.assertNotIn("sha256", result)
                self.assertEqual(calls["open"], [])
                self.assertEqual(calls["read"], [])

    def test_marker_missing_and_permission_error_remain_distinct(self):
        for error, status in ((FileNotFoundError("fixture missing"), "absent"),
                              (PermissionError("fixture denied"), "unknown")):
            with self.subTest(status=status):
                result, calls = self.marker_observation(stats=[error])
                self.assertEqual(result["status"], status)
                self.assertIs(result["verified"], False)
                self.assertEqual(calls["open"], [])

    def test_marker_race_truncation_and_invalid_json_are_unverified(self):
        raw = b'{"schema":"fixture/1"}\n'
        before = info(size=len(raw))
        cases = [dict(raw=raw, before=before, fstats=[info(size=len(raw), inode=456)]),
                 dict(raw=raw, before=before, stats=[before, info(size=len(raw), inode=456)]),
                 dict(raw=raw, before=before, reads=[raw[:-1], b""]),
                 dict(raw=b"not-json"), dict(raw=b"[]"),
                 dict(raw=b'{"schema":1,"schema":2}'), dict(raw=b'{"value":NaN}'),
                 dict(raw=raw, open_error=PermissionError("fixture denied"))]
        for index, case in enumerate(cases):
            with self.subTest(case=index):
                result, _ = self.marker_observation(**case)
                self.assertEqual(result["status"], "unknown")
                self.assertIs(result["verified"], False)
                self.assertNotIn("raw_json_utf8", result)
                self.assertNotIn("sha256", result)

    def test_socket_table_exports_only_exact_matching_path(self):
        rows = [unix_row("/private/fixture-sensitive.sock", 11),
                unix_row(I.SOCKET_PATH + ".backup", 12), unix_row("@" + I.SOCKET_PATH, 13),
                unix_row(I.SOCKET_PATH, 14), unix_row(I.SOCKET_PATH + " extra", 15)]
        with mock.patch.object(I.B, "regular", return_value=unix_table(rows)) as read:
            result = I.inspect_socket_table()
        self.assertEqual(result["status"], "observed")
        self.assertEqual(result["matches"], 1)
        self.assertEqual(result["rows"][0]["inode"], "14")
        self.assertEqual(result["rows"][0]["raw"], rows[3])
        exported = json.dumps(result)
        self.assertNotIn("fixture-sensitive", exported)
        self.assertNotIn(".backup", exported)
        self.assertNotIn(" extra", exported)
        read.assert_called_once_with(Path("/proc/net/unix"), 128 * 1024)

    def test_socket_errors_bounds_and_bad_header_never_report_zero_matches(self):
        cases = [PermissionError("fixture denied"), I.B.BootstrapError("file ceiling"), b"bad header\n",
                 unix_table([unix_row(I.SOCKET_PATH, x) for x in range(I.SOCKET_ROW_LIMIT + 1)]),
                 unix_table([unix_row("/unrelated", x) for x in range(4096)])]
        for index, value in enumerate(cases):
            with self.subTest(case=index):
                with mock.patch.object(I.B, "regular", side_effect=value if isinstance(value, Exception) else None,
                                       return_value=value if isinstance(value, bytes) else None):
                    result = I.inspect_socket_table()
                self.assertEqual(result["status"], "unknown")
                self.assertIsNone(result["matches"])
                self.assertTrue(all(row["path"] == I.SOCKET_PATH for row in result["rows"]))

    def test_supervisor_uses_only_fixed_bounded_show_command(self):
        values = dict.fromkeys(I.UNIT_FIELDS, "")
        values.update(LoadState="loaded", ActiveState="inactive", SubState="dead", MainPID="0")
        raw = "".join(key + "=" + value + "\n" for key, value in values.items()).encode()
        with mock.patch.object(I.B, "command", return_value=raw) as command:
            result = I.inspect_supervisor(Path("/fixture/output"))
        expected = ["/usr/bin/systemctl", "show", "merlin-public-browser.service", "--no-pager"]
        expected += ["--property=" + key for key in I.UNIT_FIELDS]
        command.assert_called_once_with(expected, Path("/fixture/output/supervisor-state.txt"),
                                        timeout=5, limit=16384, allowed=(0, 3, 4))
        self.assertEqual(result["status"], "observed")
        self.assertEqual(result["properties"], values)
        self.assertEqual(result["sha256"], hashlib.sha256(raw).hexdigest())

    def test_supervisor_failure_or_incomplete_fields_are_unknown(self):
        good = "".join(key + "=" + ("0" if key == "MainPID" else "") + "\n" for key in I.UNIT_FIELDS).encode()
        for value in (TimeoutError("fixture deadline"), b"MainPID=0\n", good + b"MainPID=1\n",
                      good.replace(b"MainPID=0\n", b"MainPID=not-a-pid\n")):
            with self.subTest(case=type(value).__name__, size=len(value) if isinstance(value, bytes) else None):
                with mock.patch.object(I.B, "command", side_effect=value if isinstance(value, Exception) else None,
                                       return_value=value if isinstance(value, bytes) else None):
                    result = I.inspect_supervisor(Path("/fixture/output"))
                self.assertEqual(result["status"], "unknown")
                self.assertEqual(result["properties"], {})

    def collect(self, path_states, marker="absent", supervisor="observed", sockets="observed"):
        observations = [{"path": str(path), "status": state} for path, state in zip(I.GUARD_PATHS, path_states)]
        with mock.patch.object(I, "inspect_path", side_effect=observations) as paths, \
                mock.patch.object(I, "inspect_marker", return_value={"status": marker}), \
                mock.patch.object(I, "inspect_supervisor", return_value={"status": supervisor}), \
                mock.patch.object(I, "inspect_socket_table", return_value={"status": sockets}):
            result = I.collect_observation(Path("/fixture/output"), request(), execution())
            calls = list(paths.call_args_list)
        self.assertEqual(calls, [mock.call(path) for path in I.GUARD_PATHS])
        self.assertIs(result["acceptance_allowed"], False)
        self.assertIs(result["qualification"], False)
        for key in ("application_mutations", "connections", "acquisitions", "model_calls"):
            self.assertEqual(result[key], 0)
        return result

    def test_all_absent_complete_observation_still_disallows_acceptance(self):
        result = self.collect(["absent"] * 6)
        self.assertEqual(result["status"], "inspection_complete")
        self.assertIs(result["complete"], True)
        self.assertIs(result["all_six_absent_snapshot"], True)

    def test_incomplete_observation_or_present_path_cannot_be_promoted(self):
        result = self.collect(["unknown"] + ["absent"] * 5)
        self.assertEqual(result["status"], "inspection_incomplete")
        self.assertIsNone(result["all_six_absent_snapshot"])
        result = self.collect(["present"] + ["absent"] * 5)
        self.assertIs(result["all_six_absent_snapshot"], False)
        for subsystem in ("marker", "supervisor", "sockets"):
            with self.subTest(subsystem=subsystem):
                result = self.collect(["absent"] * 6, **{subsystem: "unknown"})
                self.assertEqual(result["status"], "inspection_incomplete")
                self.assertIs(result["complete"], False)


if __name__ == "__main__":
    unittest.main()
