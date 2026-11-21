"""Synthetic static-inspection controls: no external request or fetched execution.

The sole real process-control fixture runs this local module in a new process
group and starts a sleeping local child. No candidate archive member runs.
"""
from contextlib import ExitStack
import base64
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import selectors
import signal
import struct
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

import acquire_inspect as A


NOTICE = b"Synthetic license notice. No license clearance is granted.\n"


def request():
    return {"schema": A.SCHEMA, "operation": A.OPERATION,
            "request_id": "80cd4c09-457c-470c-8e52-d41695f4f240", "created_at": "2026-11-21T22:30:00Z"}


def execution():
    return {"repository": "morganaspim/Cace-app", "ref": "refs/heads/merlin/browser-operations-20261121",
            "runner": "cace-oci-a1", "run_attempt": 1, "run_id": 44955762961, "workflow_commit": "a" * 40}


def elf_bytes(kind=3, machine=183, loader=None):
    loader = (A.EXPECTED_LOADER if loader is None else loader).encode() + b"\0"
    raw = bytearray(120 + len(loader))
    raw[:16] = b"\x7fELF\x02\x01\x01" + b"\0" * 9
    struct.pack_into("<HHIQQQIHHHHHH", raw, 16, kind, machine, 1, 0, 64, 0, 0, 64, 56, 1, 0, 0, 0)
    struct.pack_into("<IIQQQQQQ", raw, 64, 3, 4, 120, 0, 0, len(loader), len(loader), 1)
    raw[120:] = loader
    return bytes(raw)


def base_members(executable=None):
    return [("python", "directory", b""), ("python/bin", "directory", b""),
            ("python/lib", "directory", b""), ("python/etc", "directory", b""),
            (A.CANONICAL_EXECUTABLE, "regular", elf_bytes() if executable is None else executable),
            ("python/LICENSE", "regular", NOTICE), ("python/bin/python3", "symlink", "python3.11")]


def make_tar(members=None):
    result = io.BytesIO()
    with tarfile.open(fileobj=result, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for entry in base_members() if members is None else members:
            name, kind, body, *options = entry
            opts = options[0] if options else {}
            info = tarfile.TarInfo(name)
            info.mode = opts.get("mode", 0o755 if name == A.CANONICAL_EXECUTABLE or kind == "directory" else 0o644)
            info.uid = info.gid = 0
            info.mtime = 0
            info.pax_headers = opts.get("pax_headers", {})
            if kind == "directory":
                info.type = tarfile.DIRTYPE
            elif kind == "symlink":
                info.type = tarfile.SYMTYPE
                info.linkname = body
            elif kind == "hardlink":
                info.type = tarfile.LNKTYPE
                info.linkname = body
            elif kind == "fifo":
                info.type = tarfile.FIFOTYPE
            else:
                info.type = tarfile.REGTYPE
                info.size = len(body)
            archive.addfile(info, io.BytesIO(body) if kind == "regular" else None)
    return result.getvalue()


def link_escape_tar():
    # Lexical normalization says python/etc; actual component traversal follows
    # pivot to python/lib first, then the two parents escape the python root.
    return make_tar(base_members() + [("python/bin/pivot", "symlink", "../lib"),
                                     ("python/escape", "symlink", "bin/pivot/../../etc")])


def inspect(raw, module=A):
    members, notices, elfs = [], [], []
    result = module.inspect_tar(io.BytesIO(raw), members.append, notices.append, elfs.append)
    return result, members, notices, elfs


class Response:
    def __init__(self, body=b"", status=200, headers=()):
        self.stream = io.BytesIO(body)
        self.status, self.headers = status, list(headers)

    def read1(self, size):
        return self.stream.read(size)

    def getheaders(self):
        return list(self.headers)


class RequestAndTransportTests(unittest.TestCase):
    def test_fixed_request_and_native_identity_reject_scope_changes(self):
        A.validate_request(request(), execution())
        bad_requests = [{**request(), "url": "https://example.org"}, {**request(), "operation": "install"},
                        {**request(), "created_at": "2026-11-21"}, {**request(), "request_id": "not-uuid"}]
        for item in bad_requests:
            with self.subTest(item=item), self.assertRaises(A.InspectionError):
                A.validate_request(item, execution())
        for key, value in (("runner", "other"), ("repository", "other/repo"), ("run_attempt", 2),
                           ("run_attempt", True), ("run_id", True), ("workflow_commit", "main")):
            with self.subTest(key=key), self.assertRaises(A.InspectionError):
                A.validate_request(request(), {**execution(), key: value})

    def test_only_fixed_https_initial_and_release_asset_redirect_origins(self):
        self.assertEqual(A.validate_url(A.ASSET_URL, initial=True).hostname, "github.com")
        target = "https://release-assets.githubusercontent.com/fixture?token=opaque"
        self.assertEqual(A.validate_url(target).hostname, "release-assets.githubusercontent.com")
        for value in ("http://release-assets.githubusercontent.com/x", "https://evil.example/x",
                      "https://github.com/other", "https://release-assets.githubusercontent.com.evil/x",
                      "https://user:pass@release-assets.githubusercontent.com/x",
                      "https://release-assets.githubusercontent.com:444/x",
                      "https://release-assets.githubusercontent.com/x#fragment",
                      "https://release-assets.githubusercontent.com/x\r\nX:y",
                      "https://release-assets.githubusercontent.com\\@evil.example/x"):
            with self.subTest(value=value), self.assertRaises(A.InspectionError):
                A.validate_url(value)
        with self.assertRaises(A.InspectionError):
            A.validate_url(A.ASSET_URL + "?changed", initial=True)

    def test_exact_headers_and_duplicate_framing_bounds(self):
        with patch.object(A, "EXPECTED_BYTES", 3):
            A.validate_final_headers({"content-length": "3"})
            for headers in ({}, {"content-length": "2"}, {"content-length": "+3"},
                            {"content-length": "3", "transfer-encoding": "chunked"},
                            {"content-length": "3", "content-encoding": "gzip"}):
                with self.subTest(headers=headers), self.assertRaises(A.InspectionError):
                    A.validate_final_headers(headers)
        for pairs in ((('Content-Length', '3'), ('content-length', '3')),
                      (('Location', 'https://example.org'), ('location', 'https://example.org')),
                      tuple(("X-%d" % n, "x") for n in range(65))):
            with self.subTest(pairs=pairs[:2]), self.assertRaises(A.InspectionError):
                A._headers(Response(headers=pairs))

    def test_body_exact_bytes_hash_truncation_oversize_and_deadline(self):
        body = b"synthetic archive bytes"
        with patch.object(A, "EXPECTED_BYTES", len(body)), patch.object(A, "EXPECTED_SHA256", hashlib.sha256(body).hexdigest()):
            destination = io.BytesIO()
            result = A.copy_archive_body(Response(body), destination, time.monotonic() + 2)
            self.assertEqual(destination.getvalue(), body)
            self.assertEqual(result["sha256"], hashlib.sha256(body).hexdigest())
            for raw in (body[:-1], body + b"x", b"X" * len(body)):
                with self.subTest(raw=raw), self.assertRaises(A.InspectionError):
                    A.copy_archive_body(Response(raw), io.BytesIO(), time.monotonic() + 2)
            with self.assertRaises(A.InspectionError):
                A.copy_archive_body(Response(body), io.BytesIO(), time.monotonic() - 1)

    def _download_fixture(self, responses, body=b"fixture archive"):
        connections = []
        class Connection:
            def __init__(self, *args, **kwargs):
                self.response = responses[len(connections)]
                self.sock = Mock()
                self.calls = []
                self.closed = False
                connections.append(self)
            def request(self, *args, **kwargs): self.calls.append((args, kwargs))
            def getresponse(self): return self.response
            def close(self): self.closed = True
        with tempfile.TemporaryDirectory() as temp:
            fd = os.open(temp, os.O_RDONLY | os.O_DIRECTORY)
            try:
                with patch.object(A.http.client, "HTTPSConnection", Connection), \
                     patch.object(A.ssl, "create_default_context", return_value=object()), \
                     patch.object(A, "EXPECTED_BYTES", len(body)), \
                     patch.object(A, "EXPECTED_SHA256", hashlib.sha256(body).hexdigest()):
                    result = A.download_archive(fd)
                persisted = (Path(temp) / "acquisition.json").read_bytes()
                saved = (Path(temp) / A.ARCHIVE_FILE).read_bytes() if (Path(temp) / A.ARCHIVE_FILE).exists() else None
            finally:
                os.close(fd)
        self.assertTrue(all(item.closed for item in connections))
        return result, persisted, saved, connections

    def test_download_redirect_is_bounded_and_signed_value_is_not_exported(self):
        body = b"fixture archive"
        signed = "https://release-assets.githubusercontent.com/fixture?sig=SYNTHETIC_SECRET"
        result, persisted, saved, connections = self._download_fixture([
            Response(status=302, headers=[("Location", signed)]),
            Response(body, headers=[("Content-Length", str(len(body)))]),
        ])
        self.assertEqual(result["status"], "verified")
        self.assertEqual((result["http_attempts"], result["redirects"]), (2, 1))
        self.assertFalse(result["installation_allowed"])
        self.assertEqual(saved, body)
        self.assertNotIn(b"SYNTHETIC_SECRET", persisted)
        self.assertNotIn(signed.encode(), persisted)
        self.assertTrue(all("Authorization" not in c.calls[0][1]["headers"] for c in connections))

    def test_redirect_controls_wrong_origin_loops_and_http_error_stop_without_retry(self):
        for location in ("https://evil.example/file?token=SYNTHETIC_SECRET",
                         " https://release-assets.githubusercontent.com/file",
                         "https://release-assets.githubusercontent.com/file\r\nX:secret"):
            with self.subTest(location=location):
                result, persisted, saved, connections = self._download_fixture([Response(status=302, headers=[("Location", location)])])
                self.assertEqual(result["status"], "failed")
                self.assertEqual(len(connections), 1)
                self.assertIsNone(saved)
                self.assertNotIn(b"SYNTHETIC_SECRET", persisted)
        target = "https://release-assets.githubusercontent.com/loop?sig=SYNTHETIC_SECRET"
        result, persisted, _, connections = self._download_fixture([
            Response(status=302, headers=[("Location", target)]) for _ in range(3)])
        self.assertEqual((len(connections), result["error"]["code"]), (3, "redirect_ceiling"))
        self.assertNotIn(b"SYNTHETIC_SECRET", persisted)
        result, _, _, connections = self._download_fixture([Response(status=503)])
        self.assertEqual((len(connections), result["automatic_retries"]), (1, 0))

    def test_unexpected_errors_never_export_raw_exception_messages(self):
        error = RuntimeError("https://release-assets.githubusercontent.com/file?sig=SYNTHETIC_SECRET")
        self.assertEqual(A.failure(error), {"code": "unexpected_RuntimeError", "type": "RuntimeError"})
        self.assertNotIn("SYNTHETIC_SECRET", json.dumps(A.failure(error)))


class ArchiveAndElfTests(unittest.TestCase):
    def test_valid_static_archive_preserves_notice_elf_hash_and_noninstallation(self):
        raw = make_tar()
        with patch.object(tarfile.TarFile, "extract", side_effect=AssertionError("extraction forbidden")), \
             patch.object(tarfile.TarFile, "extractall", side_effect=AssertionError("extraction forbidden")):
            result, members, notices, elfs = inspect(raw)
        self.assertEqual(result["members"], 7)
        self.assertFalse(result["installation_allowed"])
        self.assertEqual(result["fetched_code_executions"], 0)
        self.assertEqual(result["native_dependency_compatibility"], "unverified")
        self.assertEqual(result["license_clearance"], "not_granted")
        self.assertEqual(base64.b64decode(notices[0]["data_base64"], validate=True), NOTICE)
        self.assertEqual(notices[0]["sha256"], hashlib.sha256(NOTICE).hexdigest())
        self.assertEqual(elfs[0]["machine"], "AArch64")
        self.assertEqual(elfs[0]["interpreter"], A.EXPECTED_LOADER)
        self.assertEqual(result["executable"]["sha256"], hashlib.sha256(elf_bytes()).hexdigest())

    def test_symlink_then_parent_traversal_cannot_claim_inside_tree(self):
        with self.assertRaises(A.InspectionError):
            inspect(link_escape_tar())

    def test_relocatable_object_cannot_be_the_canonical_executable(self):
        with self.assertRaises(A.InspectionError):
            inspect(make_tar(base_members(elf_bytes(kind=1))))

    def test_ordinary_aliases_and_safe_parent_relative_links_still_work(self):
        result, members, _, _ = inspect(make_tar(base_members() + [("python/bin/lib", "symlink", "../lib")]))
        self.assertTrue(result["all_symlink_targets_inside_inspected_tree"])
        alias = next(item for item in members if item["path"] == "python/bin/python3")
        self.assertEqual(alias["resolved_target"], A.CANONICAL_EXECUTABLE)

    def test_serialized_link_inventory_contains_actual_component_resolved_target(self):
        archive = make_tar(base_members() + [("python/lib/subdir", "directory", b""),
                                            ("python/bin/pivot", "symlink", "../lib"),
                                            ("python/alias", "symlink", "bin/pivot/subdir")])
        # Production JsonLines freezes each record at emit time; a list.append
        # callback would retain the same dict and hide a later mutation bug.
        member_bytes, notice_bytes, elf_bytes_out = io.BytesIO(), io.BytesIO(), io.BytesIO()
        writers = [A.JsonLines(stream) for stream in (member_bytes, notice_bytes, elf_bytes_out)]
        A.inspect_tar(io.BytesIO(archive), *(writer.emit for writer in writers))
        entries = [json.loads(line) for line in member_bytes.getvalue().splitlines()]
        alias = next(item for item in entries if item["path"] == "python/alias")
        self.assertEqual(alias["resolved_target"], "python/lib/subdir")
        self.assertNotEqual(alias["resolved_target"], "python/bin/pivot/subdir")
        self.assertTrue(all("resolved_target" in item for item in entries if item["type"] == "symlink"))

    def test_unsafe_paths_duplicates_and_non_directory_ancestors_rejected(self):
        for name in ("/absolute", "../escape", "python/../escape", "python//x", "python/./x", "python\\x"):
            with self.subTest(name=name), self.assertRaises(A.InspectionError):
                inspect(make_tar(base_members() + [(name, "regular", b"x")]))
        with self.assertRaises(A.InspectionError):
            inspect(make_tar(base_members() + [("python/LICENSE", "regular", b"duplicate")]))
        with self.assertRaises(A.InspectionError):
            inspect(make_tar(base_members() + [("python/file", "regular", b"x"),
                                               ("python/file/child", "regular", b"x")]))
        with self.assertRaises(A.InspectionError):
            inspect(make_tar(base_members() + [("python/alias", "symlink", "lib"), ("python/alias/child", "regular", b"x")]))

    def test_dangling_cyclic_escaping_and_absolute_links_rejected(self):
        for extra in ([("python/link", "symlink", "missing")],
                      [("python/link", "symlink", "link")],
                      [("python/a", "symlink", "b"), ("python/b", "symlink", "a")],
                      [("python/link", "symlink", "../../outside")],
                      [("python/link", "symlink", "/etc/passwd")]):
            with self.subTest(extra=extra), self.assertRaises(A.InspectionError):
                inspect(make_tar(base_members() + extra))

    def test_special_hardlink_setid_and_member_notice_count_bounds_rejected(self):
        for item in (("python/fifo", "fifo", b""),
                     ("python/hard", "hardlink", A.CANONICAL_EXECUTABLE),
                     ("python/setid", "regular", b"x", {"mode": 0o4755})):
            with self.subTest(item=item), self.assertRaises(A.InspectionError):
                inspect(make_tar(base_members() + [item]))
        for name, value in (("MAX_MEMBER", 16), ("MAX_MEMBERS", 3), ("MAX_NOTICE", 3), ("MAX_NOTICES_TOTAL", 3)):
            with self.subTest(bound=name), patch.object(A, name, value), self.assertRaises(A.InspectionError):
                inspect(make_tar())

    def test_nonzero_trailing_data_concatenated_tar_and_missing_terminator_rejected(self):
        raw = make_tar()
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
            last = max(member.offset_data + ((member.size + 511) // 512) * 512 for member in archive)
        for altered in (raw + b"hidden", raw + make_tar(), raw[:last + 512]):
            with self.subTest(length=len(altered)), self.assertRaises(A.InspectionError):
                inspect(altered)

    def test_gzip_integrity_and_expansion_cap_precede_tar_parsing(self):
        raw = make_tar()
        target = io.BytesIO()
        self.assertEqual(A.decompress_to_data(gzip.compress(raw, mtime=0), target)["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(target.getvalue(), raw)
        compressed = gzip.compress(raw, mtime=0)
        for altered in (compressed[:-5], compressed[:-8] + b"\0" * 8, compressed + b"junk"):
            with self.subTest(length=len(altered)), self.assertRaises((A.InspectionError, EOFError, OSError)):
                A.decompress_to_data(altered, io.BytesIO())
        with tempfile.TemporaryDirectory() as temp:
            fd = os.open(temp, os.O_RDONLY | os.O_DIRECTORY)
            try:
                with patch.object(A, "read_archive_snapshot", return_value=gzip.compress(b"A" * 65536, mtime=0)), \
                     patch.object(A, "MAX_EXPANDED", 1024), \
                     patch.object(A, "inspect_tar", side_effect=AssertionError("must not reach tar parser")) as parser:
                    result = A.inspect_archive(fd)
                self.assertEqual(result["error"]["code"], "expanded_archive_ceiling")
                parser.assert_not_called()
                self.assertLessEqual((Path(temp) / A.TAR_FILE).stat().st_size, 1024)
            finally:
                os.close(fd)

    def test_wrong_elf_machine_loader_and_program_table_bounds_rejected(self):
        invalid = [elf_bytes(machine=62), elf_bytes(loader="/tmp/other-loader")]
        raw = bytearray(elf_bytes())
        struct.pack_into("<Q", raw, 32, 999999)
        invalid.append(bytes(raw))
        for body in invalid:
            with self.subTest(sha256=hashlib.sha256(body).hexdigest()), self.assertRaises(A.InspectionError):
                A.inspect_elf(body)
        self.assertIsNone(A.inspect_elf(b"not an executable"))

    def test_inventory_output_bound_stops_before_oversized_write(self):
        destination = io.BytesIO()
        writer = A.JsonLines(destination)
        with patch.object(A, "MAX_JSON_LINE", 16), self.assertRaises(A.InspectionError):
            writer.emit({"too_large": "x" * 30})
        self.assertEqual(destination.getvalue(), b"")


class StageOwnershipTests(unittest.TestCase):
    def test_stalled_child_deadline_never_reads_a_partial_receipt(self):
        class Process:
            pid = 43210
            exitcode = None
            alive = True
            def start(self): pass
            def join(self, seconds): self.last_join = seconds
            def is_alive(self): return self.alive
            def terminate(self): self.alive = False; self.exitcode = -signal.SIGTERM
            def kill(self): self.alive = False; self.exitcode = -signal.SIGKILL
        process = Process()
        context = Mock()
        context.Process.return_value = process
        with patch.object(A.multiprocessing, "get_context", return_value=context), \
             patch.object(A, "DOWNLOAD_SECONDS", 0.1), \
             patch.object(A, "_read_stage_receipt", side_effect=AssertionError("partial receipt read forbidden")) as reader:
            result = A.run_stage("acquisition", -1)
        reader.assert_not_called()
        self.assertEqual(result["status"], "failed")
        self.assertTrue(result["worker_stopped"])
        self.assertTrue(result["worker_receipt_unconfirmed"])
        self.assertIsNone(result["http_attempts"])
        self.assertFalse(result["installation_allowed"])

    def test_local_sleeping_worker_remains_owned_by_outer_process_group(self):
        # A local fixture imports reviewed control code only; it replaces all
        # acquisition with a sleeping function before starting the worker.
        source = str(Path(A.__file__).resolve().parent)
        code = '''import json,multiprocessing,os,signal,sys,time
sys.path.insert(0,sys.argv[1])
import acquire_inspect as A
def hold(_):
 os.write(1,(json.dumps({'pid':os.getpid(),'pgid':os.getpgrp(),'parent':os.getppid()})+'\\n').encode())
 while True: time.sleep(1)
A.download_archive=hold
p=multiprocessing.get_context('fork').Process(target=A._worker,args=('acquisition',-1))
p.start()
p.join()
'''
        process = subprocess.Popen([sys.executable, "-I", "-B", "-c", code, source],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        child_pid = None
        child_detached = False
        selector = selectors.DefaultSelector()
        try:
            selector.register(process.stdout, selectors.EVENT_READ)
            pending = b""
            deadline = time.monotonic() + 4
            while b"\n" not in pending:
                self.assertLess(time.monotonic(), deadline, "local child failed to announce")
                if selector.select(max(0, deadline - time.monotonic())):
                    chunk = os.read(process.stdout.fileno(), 4096)
                    self.assertTrue(chunk, "local child exited without announcement")
                    pending += chunk
            identity = json.loads(pending.splitlines()[0])
            child_pid = identity["pid"]
            child_detached = identity["pgid"] != process.pid
            self.assertEqual(identity["parent"], process.pid)
            self.assertEqual(identity["pgid"], process.pid, "worker detached from outer cancellation group")
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=2)
            self.assertTrue(selector.select(2), "worker retained stdout after group cancellation")
            self.assertEqual(os.read(process.stdout.fileno(), 4096), b"")
        finally:
            selector.close()
            try: os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            if child_pid is not None and child_detached:
                try: os.kill(child_pid, signal.SIGKILL)
                except ProcessLookupError: pass
            process.communicate(timeout=2)

    def test_successful_mocked_stages_never_authorize_installation_or_execution(self):
        from contextlib import contextmanager
        @contextmanager
        def directory(_): yield -1
        stages = [{"status": "verified", "archive_verified": True, "worker_stopped": True},
                  {"status": "observed", "worker_stopped": True}]
        with patch.object(A.os, "geteuid", return_value=1000), \
             patch.object(A.platform, "system", return_value="Linux"), \
             patch.object(A.platform, "machine", return_value="aarch64"), \
             patch.object(A.sys, "version_info", (3, 9, 25)), \
             patch.object(A, "private_directory", directory), \
             patch.object(A.os, "listdir", return_value=[]), \
             patch.object(A, "run_stage", side_effect=stages), \
             patch.object(A, "_write_json"):
            result = A.run(request(), execution(), "/tmp/merlin-python-static-inspection-44955762961-1")
        self.assertEqual(result["status"], "static_observations_complete_installation_unapproved")
        self.assertFalse(result["installation_allowed"])
        self.assertFalse(result["qualification"])
        for key in ("fetched_code_executions", "native_installations", "discovery_entries_created", "provider_changes", "system_python_changes", "model_calls", "product_tests_run"):
            self.assertEqual(result[key], 0)

    def test_failed_acquisition_does_not_start_inspection_or_retry(self):
        from contextlib import contextmanager
        @contextmanager
        def directory(_): yield -1
        with patch.object(A.os, "geteuid", return_value=1000), \
             patch.object(A.platform, "system", return_value="Linux"), \
             patch.object(A.platform, "machine", return_value="aarch64"), \
             patch.object(A.sys, "version_info", (3, 9, 25)), \
             patch.object(A, "private_directory", directory), \
             patch.object(A.os, "listdir", return_value=[]), \
             patch.object(A, "run_stage", return_value={"status": "failed", "worker_stopped": True}) as stages, \
             patch.object(A, "_write_json"):
            result = A.run(request(), execution(), "/tmp/merlin-python-static-inspection-44955762961-1")
        self.assertEqual(stages.call_count, 1)
        self.assertEqual(result["status"], "failed")
        self.assertFalse(result["installation_allowed"])


class ImplicitDirectoryTests(unittest.TestCase):
    def test_no_explicit_directories_is_a_valid_archive_namespace(self):
        raw = make_tar([entry for entry in base_members() if entry[1] != "directory"])
        with patch.object(tarfile.TarFile, "extract", side_effect=AssertionError("no extraction")), \
             patch.object(tarfile.TarFile, "extractall", side_effect=AssertionError("no extraction")):
            result, members, _, _ = inspect(raw)
        self.assertEqual(result["members"], 3)
        self.assertEqual(result["namespace_nodes"], 5)
        self.assertEqual(result["inferred_directories"], ["python", "python/bin"])
        self.assertEqual(len(members), 3)
        self.assertFalse(any(item["type"] == "directory" for item in members))
        self.assertEqual(next(item for item in members if item["type"] == "symlink")["resolved_target"],
                         A.CANONICAL_EXECUTABLE)
        self.assertFalse(result["installation_allowed"])
        self.assertEqual(result["fetched_code_executions"], 0)

    def test_missing_root_only_does_not_invent_root_metadata(self):
        result, members, _, _ = inspect(make_tar([entry for entry in base_members() if entry[0] != "python"]))
        self.assertEqual(result["inferred_directories"], ["python"])
        self.assertFalse(any(item["path"] == "python" for item in members))

    def test_mixed_explicit_implicit_ancestors_preserve_actual_member_count(self):
        entries = base_members() + [("python/lib/pkg/deep/module.py", "regular", b"value = 1\n")]
        result, members, _, _ = inspect(make_tar(entries))
        self.assertEqual(result["members"], len(entries))
        self.assertEqual(result["inferred_directories"], ["python/lib/pkg", "python/lib/pkg/deep"])
        self.assertEqual(result["namespace_nodes"], len(entries) + 2)
        self.assertEqual(len(members), len(entries))

    def test_symlink_can_resolve_to_directory_proven_by_a_descendant(self):
        entries = [entry for entry in base_members() if entry[1] != "directory"]
        entries += [("python/lib/pkg/value", "regular", b"x"),
                    ("python/bin/pkg", "symlink", "../lib/pkg")]
        result, members, _, _ = inspect(make_tar(entries))
        alias = next(item for item in members if item["path"] == "python/bin/pkg")
        self.assertEqual(alias["resolved_target"], "python/lib/pkg")
        self.assertEqual(result["members"], len(entries))

    def test_member_order_does_not_turn_explicit_directory_into_inferred_metadata(self):
        entries = base_members()
        directories = [entry for entry in entries if entry[1] == "directory"]
        other = [entry for entry in entries if entry[1] != "directory"]
        result, members, _, _ = inspect(make_tar(other + directories))
        self.assertEqual(result["inferred_directories"], [])
        self.assertEqual(result["members"], len(entries))
        self.assertEqual(sum(item["type"] == "directory" for item in members), 4)

    def test_explicit_non_directory_ancestor_is_rejected_in_either_order(self):
        child = ("python/parent/child", "regular", b"x")
        for kind, target in (("regular", b"x"), ("symlink", "lib")):
            parent = ("python/parent", kind, target)
            for extra in ((parent, child), (child, parent)):
                with self.subTest(kind=kind, order=extra), self.assertRaisesRegex(
                        A.InspectionError, "archive_ancestor_not_directory"):
                    inspect(make_tar(base_members() + list(extra)))

    def test_link_target_alone_cannot_infer_a_directory(self):
        with self.assertRaisesRegex(A.InspectionError, "dangling_archive_link"):
            inspect(make_tar(base_members() + [("python/alias", "symlink", "missing/subdir")]))

    def test_componentwise_escape_is_still_rejected_with_implicit_ancestors(self):
        entries = [entry for entry in base_members() if entry[1] != "directory"]
        entries += [("python/lib/child", "regular", b"x"),
                    ("python/bin/pivot", "symlink", "../lib"),
                    ("python/escape", "symlink", "bin/pivot/../../etc")]
        with self.assertRaisesRegex(A.InspectionError, "componentwise_link_escapes_python_tree"):
            inspect(make_tar(entries))

    def test_inferred_namespace_nodes_are_bounded(self):
        entries = [entry for entry in base_members() if entry[1] != "directory"]
        with patch.object(A, "MAX_MEMBERS", 4), self.assertRaisesRegex(
                A.InspectionError, "namespace_node_ceiling"):
            inspect(make_tar(entries))

    def test_no_members_cannot_infer_a_python_root(self):
        with self.assertRaisesRegex(A.InspectionError, "python_root_directory_missing"):
            inspect(make_tar([]))

    def test_explicit_root_cannot_be_a_file_or_symlink(self):
        for entry in (("python", "regular", b"x"), ("python", "symlink", "python")):
            with self.subTest(kind=entry[1]), self.assertRaises(A.InspectionError):
                inspect(make_tar([item for item in base_members() if item[0] != "python"] + [entry]))

    def test_serialized_inventory_stays_one_record_per_actual_member(self):
        entries = [entry for entry in base_members() if entry[1] != "directory"]
        outputs = [io.BytesIO(), io.BytesIO(), io.BytesIO()]
        writers = [A.JsonLines(output) for output in outputs]
        result = A.inspect_tar(io.BytesIO(make_tar(entries)), *(writer.emit for writer in writers))
        measured = [json.loads(line) for line in outputs[0].getvalue().splitlines()]
        self.assertEqual(len(measured), len(entries))
        self.assertEqual(writers[0].records, result["members"])
        self.assertFalse(any("origin" in item for item in measured))


if __name__ == "__main__":
    unittest.main(verbosity=2)
