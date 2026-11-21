"""One pinned CPython acquisition and static data inspection; never installation.

The native entrypoint is unprivileged and writes only a new private runner leaf.
No archive member is extracted to a runtime path or executed.  A verified archive
is still not installation authority, dependency approval, or product acceptance.
"""
from contextlib import contextmanager
import base64
import datetime
import gzip
import hashlib
import http.client
import io
import json
import multiprocessing
import os
from pathlib import Path
import platform
import posixpath
import re
import resource
import signal
import ssl
import stat
import struct
import sys
import tarfile
import time
import urllib.parse
import uuid


OPERATION = "inspect-cpython-3.11.18-20261110-aarch64"
SCHEMA = "merlin-python-static-inspection-request/1"
ASSET_ID = 733710616
RELEASE_ID = 441136779
ASSET_URL = ("https://github.com/astral-sh/python-build-standalone/releases/download/20261110/"
             "cpython-3.11.18%2B20261110-aarch64-unknown-linux-gnu-install_only.tar.gz")
EXPECTED_BYTES = 49469868
EXPECTED_SHA256 = "623a370be4489d8c35c7a274be02f3007a030618cda29025780beb416c6c8861"
BUILD_COMMIT = "9244801782b78e4c4afc5c82a4524aa2101d3298"
MAX_COMPRESSED = 64 * 1024 * 1024
MAX_EXPANDED = 512 * 1024 * 1024
MAX_MEMBER = 64 * 1024 * 1024
MAX_MEMBERS = 20000
MAX_NOTICE = 256 * 1024
MAX_NOTICES_TOTAL = 4 * 1024 * 1024
MAX_JSONL = 32 * 1024 * 1024
MAX_JSON_LINE = 2 * 1024 * 1024
MAX_REDIRECTS = 2
DOWNLOAD_SECONDS = 180
INSPECTION_SECONDS = 120
STOP_GRACE_SECONDS = 4
WORKER_MEMORY = 1024 * 1024 * 1024
CANONICAL_EXECUTABLE = "python/bin/python3.11"
EXPECTED_LOADER = "/lib/ld-linux-aarch64.so.1"
ARCHIVE_FILE = "archive.data"
TAR_FILE = "decompressed-tar.data"
HEADER_LIMIT = 64 * 1024
ALLOWED_HOSTS = frozenset(("github.com", "release-assets.githubusercontent.com"))
EVIDENCE_FILES = frozenset((ARCHIVE_FILE, TAR_FILE, "acquisition.json", "archive-inventory.jsonl",
                          "license-notices.jsonl", "elf-observations.jsonl", "static-inspection.json",
                          "inspection-receipt.json"))


class InspectionError(Exception):
    """Only fixed error codes, never URLs, response bodies, or credentials."""


def require(value, code):
    if not value:
        raise InspectionError(code)


def failure(error):
    return {"code": str(error) if isinstance(error, InspectionError) else "unexpected_" + type(error).__name__,
            "type": type(error).__name__}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode() + b"\n"


def unique(items):
    result = {}
    for key, value in items:
        require(key not in result, "duplicate_json_key")
        result[key] = value
    return result


def validate_request(request, execution):
    require(isinstance(request, dict) and set(request) == {"schema", "request_id", "operation", "created_at"},
            "fixed_request_fields_required")
    require(request["schema"] == SCHEMA and request["operation"] == OPERATION, "fixed_operation_required")
    try:
        valid = (isinstance(request["request_id"], str)
                 and str(uuid.UUID(request["request_id"])) == request["request_id"]
                 and datetime.datetime.strptime(request["created_at"], "%Y-%m-%dT%H:%M:%SZ").strftime(
                     "%Y-%m-%dT%H:%M:%SZ") == request["created_at"])
    except (ValueError, TypeError, AttributeError):
        valid = False
    require(valid, "canonical_request_identity_required")
    require(isinstance(execution, dict)
            and execution.get("repository") == "morganaspim/Cace-app"
            and execution.get("ref") == "refs/heads/merlin/browser-operations-20261121"
            and execution.get("runner") == "cace-oci-a1"
            and type(execution.get("run_attempt")) is int and execution["run_attempt"] == 1
            and type(execution.get("run_id")) is int and execution["run_id"] > 44955762960
            and isinstance(execution.get("workflow_commit"), str)
            and re.fullmatch("[0-9a-f]{40}", execution["workflow_commit"]), "fixed_first_native_identity_required")


def validate_url(value, initial=False):
    require(isinstance(value, str) and 0 < len(value) <= 8192 and value.isascii()
            and all(ord(c) > 32 and ord(c) != 127 for c in value), "invalid_https_url")
    try:
        parsed = urllib.parse.urlsplit(value)
        valid = (parsed.scheme == "https" and parsed.hostname in ALLOWED_HOSTS
                 and parsed.port in (None, 443) and parsed.username is None and parsed.password is None
                 and not parsed.fragment and parsed.path.startswith("/")
                 and "\\" not in value)
    except ValueError:
        valid = False
    require(valid, "unapproved_https_origin")
    require(not initial or value == ASSET_URL, "initial_asset_url_differs")
    require(initial or parsed.hostname == "release-assets.githubusercontent.com", "unexpected_redirect_host")
    return parsed


def _headers(response):
    pairs = response.getheaders()
    require(len(pairs) <= 64 and sum(len(k) + len(v) + 4 for k, v in pairs) <= HEADER_LIMIT,
            "response_headers_exceed_bound")
    result = {}
    for key, value in pairs:
        key = key.lower()
        if key in ("location", "content-length", "content-encoding", "transfer-encoding"):
            require(key not in result, "ambiguous_response_framing")
            result[key] = value
    return result


def validate_final_headers(headers):
    require("transfer-encoding" not in headers, "unsupported_transfer_encoding")
    require(headers.get("content-encoding", "identity").lower() == "identity", "unexpected_content_encoding")
    value = headers.get("content-length", "")
    require(re.fullmatch("[0-9]{1,12}", value) is not None, "exact_content_length_required")
    require(int(value) == EXPECTED_BYTES and int(value) <= MAX_COMPRESSED, "declared_archive_size_differs")


def copy_archive_body(response, destination, deadline):
    """Count actual bytes even when HTTPResponse.read1 accepts a short body."""
    digest = hashlib.sha256()
    size = 0
    while True:
        require(time.monotonic() < deadline, "acquisition_deadline")
        data = response.read1(min(65536, MAX_COMPRESSED + 1 - size))
        require(isinstance(data, bytes), "response_body_is_not_bytes")
        if not data:
            break
        size += len(data)
        require(size <= MAX_COMPRESSED and size <= EXPECTED_BYTES, "received_archive_size_exceeds_bound")
        destination.write(data)
        digest.update(data)
    require(time.monotonic() < deadline, "acquisition_deadline")
    require(size == EXPECTED_BYTES, "received_archive_size_differs")
    require(digest.hexdigest() == EXPECTED_SHA256, "archive_digest_differs")
    return {"bytes": size, "sha256": digest.hexdigest()}


def _new_data(directory, name):
    require(name in EVIDENCE_FILES, "unexpected_evidence_name")
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
    return os.fdopen(fd, "wb")


def _write_json(directory, name, value):
    raw = canonical(value)
    require(len(raw) <= 256 * 1024, "receipt_size_ceiling")
    with _new_data(directory, name) as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def download_archive(directory):
    result = {"stage": "acquisition", "status": "failed", "logical_acquisitions_attempted": 1,
              "automatic_retries": 0, "http_attempts": 0, "redirects": 0, "hops": [],
              "deadline_seconds": DOWNLOAD_SECONDS, "archive_verified": False,
              "installation_allowed": False, "fetched_code_executions": 0}
    deadline = time.monotonic() + DOWNLOAD_SECONDS
    current = ASSET_URL
    try:
        for hop in range(MAX_REDIRECTS + 1):
            parsed = validate_url(current, initial=hop == 0)
            remaining = deadline - time.monotonic()
            require(remaining > 0, "acquisition_deadline")
            connection = http.client.HTTPSConnection(parsed.hostname, 443, timeout=remaining,
                                                      context=ssl.create_default_context())
            result["http_attempts"] += 1
            record = {"origin": "https://" + parsed.hostname, "status": None}
            result["hops"].append(record)
            try:
                # Direct HTTPSConnection uses neither proxy environment nor cookies/authentication.
                target = urllib.parse.urlunsplit(("", "", parsed.path, parsed.query, ""))
                connection.request("GET", target, headers={"User-Agent": "Merlin-static-archive-review/1",
                                   "Accept": "application/octet-stream", "Accept-Encoding": "identity",
                                   "Connection": "close"})
                remaining = deadline - time.monotonic()
                require(remaining > 0, "acquisition_deadline")
                if connection.sock is not None:
                    connection.sock.settimeout(remaining)
                response = connection.getresponse()
                record["status"] = response.status
                headers = _headers(response)
                if response.status in (301, 302, 303, 307, 308):
                    require(hop < MAX_REDIRECTS, "redirect_ceiling")
                    location = headers.get("location")
                    require(isinstance(location, str) and 0 < len(location) <= 8192 and location.isascii()
                            and all(ord(c) > 32 and ord(c) != 127 for c in location), "invalid_redirect_location")
                    # No redirect response body or signed Location value is persisted.
                    next_url = urllib.parse.urljoin(current, location)
                    validate_url(next_url, initial=False)
                    current = next_url
                    result["redirects"] += 1
                    continue
                require(response.status == 200, "unexpected_archive_http_status")
                validate_final_headers(headers)
                with _new_data(directory, ARCHIVE_FILE) as destination:
                    identity = copy_archive_body(response, destination, deadline)
                    destination.flush()
                    os.fsync(destination.fileno())
                result.update({"status": "verified", "archive_verified": True, "archive": identity})
                break
            finally:
                connection.close()
        require(result["archive_verified"], "no_verified_archive_response")
    except Exception as error:
        result["error"] = failure(error)
    _write_json(directory, "acquisition.json", result)
    return result


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_uid, info.st_mode, info.st_nlink,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def read_archive_snapshot(directory):
    fd = os.open(ARCHIVE_FILE, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_uid == 1000 and before.st_nlink == 1
                and stat.S_IMODE(before.st_mode) == 0o600 and before.st_size == EXPECTED_BYTES,
                "archive_data_identity_not_trusted")
        chunks = []
        count = 0
        while True:
            raw = os.read(fd, min(65536, MAX_COMPRESSED + 1 - count))
            if not raw:
                break
            count += len(raw)
            require(count <= MAX_COMPRESSED, "archive_snapshot_ceiling")
            chunks.append(raw)
        raw = b"".join(chunks)
        require(_identity(before) == _identity(os.fstat(fd))
                == _identity(os.stat(ARCHIVE_FILE, dir_fd=directory, follow_symlinks=False)),
                "archive_changed_during_snapshot")
        require(len(raw) == EXPECTED_BYTES and hashlib.sha256(raw).hexdigest() == EXPECTED_SHA256,
                "archive_snapshot_digest_or_size_differs")
        # The subsequent gzip input is immutable process-local bytes, not a mutable file descriptor.
        return raw
    finally:
        os.close(fd)


def decompress_to_data(raw, destination):
    total = 0
    digest = hashlib.sha256()
    with gzip.GzipFile(fileobj=io.BytesIO(raw), mode="rb") as source:
        while True:
            chunk = source.read(min(65536, MAX_EXPANDED + 1 - total))
            if not chunk:
                break
            total += len(chunk)
            require(total <= MAX_EXPANDED, "expanded_archive_ceiling")
            destination.write(chunk)
            digest.update(chunk)
    require(total >= 1024 and total % 512 == 0, "invalid_tar_block_length")
    return {"bytes": total, "sha256": digest.hexdigest()}


def member_path(value, directory=False):
    require(isinstance(value, str) and value and len(value.encode("utf-8")) <= 512
            and not value.startswith("/") and "\\" not in value
            and all(ord(c) >= 32 and ord(c) != 127 for c in value), "unsafe_member_path")
    name = value.rstrip("/") if directory else value
    require(all(part not in ("", ".", "..") for part in name.split("/"))
            and (name == "python" or name.startswith("python/")), "unexpected_archive_layout")
    return name


def link_target(name, value):
    require(isinstance(value, str) and value and len(value.encode("utf-8")) <= 512
            and not value.startswith("/") and "\\" not in value
            and all(ord(c) >= 32 and ord(c) != 127 for c in value), "unsafe_link_target")
    target = posixpath.normpath(posixpath.join(posixpath.dirname(name), value))
    require(target == "python" or target.startswith("python/"), "link_escapes_python_tree")
    return target


def resolve_link(name, entries):
    """Apply POSIX component order: follow each link before subsequent '..'."""
    stack = posixpath.dirname(name).split("/")
    pending = entries[name]["target"].split("/")
    hops = 1
    while pending:
        part = pending.pop(0)
        if part == "":
            continue
        current = "/".join(stack)
        require(entries.get(current, {}).get("type") == "directory", "link_traverses_non_directory")
        if part == ".":
            continue
        if part == "..":
            require(len(stack) > 1, "componentwise_link_escapes_python_tree")
            stack.pop()
            continue
        target = "/".join(stack + [part])
        require(target in entries, "dangling_archive_link")
        value = entries[target]
        if value["type"] == "symlink":
            hops += 1
            require(hops <= 64, "cyclic_or_overlong_archive_link")
            pending = value["target"].split("/") + pending
        else:
            stack.append(part)
            if pending:
                require(value["type"] == "directory", "link_traverses_non_directory")
    return "/".join(stack)


def inspect_elf(raw):
    if not raw.startswith(b"\x7fELF"):
        return None
    require(len(raw) >= 64 and raw[4:7] == b"\x02\x01\x01", "unsupported_elf_encoding")
    fields = struct.unpack_from("<HHIQQQIHHHHHH", raw, 16)
    kind, machine, version, _, phoff, _, _, ehsize, phsize, phnum, _, _, _ = fields
    require(machine == 183 and version == 1 and ehsize == 64 and kind in (1, 2, 3), "elf_target_differs")
    require(phnum <= 256 and (not phnum or phsize == 56)
            and phoff + phnum * phsize <= len(raw), "elf_program_table_out_of_bounds")
    segments = []
    for index in range(phnum):
        segment = struct.unpack_from("<IIQQQQQQ", raw, phoff + index * phsize)
        require(segment[2] + segment[5] <= len(raw), "elf_segment_out_of_bounds")
        segments.append(segment)
    loaders = [s for s in segments if s[0] == 3]
    require(len(loaders) <= 1, "multiple_elf_loaders")
    loader = None
    if loaders:
        s = loaders[0]
        value = raw[s[2]:s[2] + s[5]]
        require(1 < len(value) <= 512 and value.endswith(b"\0") and b"\0" not in value[:-1], "invalid_elf_loader")
        loader = value[:-1].decode("ascii")
        require(loader == EXPECTED_LOADER, "unexpected_elf_loader")
    dynamic = [s for s in segments if s[0] == 2]
    require(len(dynamic) <= 1, "multiple_elf_dynamic_tables")
    needed, rpath, runpath = [], [], []
    if dynamic:
        s = dynamic[0]
        require(s[5] % 16 == 0 and s[5] <= 65536, "elf_dynamic_table_bound")
        entries = []
        terminated = False
        for offset in range(s[2], s[2] + s[5], 16):
            tag, value = struct.unpack_from("<qQ", raw, offset)
            if tag == 0:
                terminated = True
                break
            entries.append((tag, value))
        require(terminated, "unterminated_elf_dynamic_table")
        text_tags = [(tag, value) for tag, value in entries if tag in (1, 15, 29)]
        if text_tags:
            starts = [v for tag, v in entries if tag == 5]
            sizes = [v for tag, v in entries if tag == 10]
            require(len(starts) == len(sizes) == 1 and 0 < sizes[0] <= 16 * 1024 * 1024,
                    "invalid_elf_string_table")
            maps = [s for s in segments if s[0] == 1 and s[3] <= starts[0]
                    and starts[0] + sizes[0] <= s[3] + s[5]]
            require(len(maps) == 1, "elf_string_table_not_file_backed")
            start = maps[0][2] + starts[0] - maps[0][3]
            table = raw[start:start + sizes[0]]
            require(len(text_tags) <= 128, "elf_dependency_count_ceiling")
            for tag, offset in text_tags:
                require(offset < len(table), "elf_string_offset_out_of_bounds")
                end = table.find(b"\0", offset, min(len(table), offset + 1025))
                require(end >= offset, "unterminated_elf_string")
                text = table[offset:end].decode("ascii")
                require(all(ord(c) >= 32 and ord(c) != 127 for c in text), "unsafe_elf_string")
                (needed if tag == 1 else rpath if tag == 15 else runpath).append(text)
    return {"class_bits": 64, "endianness": "little", "machine": "AArch64", "elf_type": kind,
            "interpreter": loader, "needed": needed, "rpath": rpath, "runpath": runpath,
            "native_dependency_compatibility": "unverified", "execution_performed": False}


def is_notice(name):
    parts = name.lower().split("/")
    return (any(p in ("licenses", "licences") for p in parts)
            or re.fullmatch(r"(?:license|licence|copying|notice|copyright)(?:[._-].*)?", parts[-1]) is not None)


def inspect_tar(source, emit_member, emit_notice, emit_elf):
    """Inspect tar data; never call extract/extractall or apply archive modes/owners."""
    entries, elf_records = {}, {}
    total_files = notice_bytes = notice_count = 0
    end_of_members = 0
    with tarfile.open(fileobj=source, mode="r:", errorlevel=2) as archive:
        for member in archive:
            require(len(entries) < MAX_MEMBERS, "member_count_ceiling")
            name = member_path(member.name, member.isdir())
            require(name not in entries, "duplicate_archive_member")
            require(member.sparse is None and not any(k.startswith("GNU.sparse") for k in member.pax_headers),
                    "sparse_member_not_supported")
            require(not member.mode & 0o6000, "setid_archive_member")
            require(0 <= member.size <= MAX_MEMBER, "member_size_ceiling")
            require(not member.islnk(), "hardlink_requires_separate_review")
            kind = "directory" if member.isdir() else "symlink" if member.issym() else "regular" if member.isfile() else None
            require(kind is not None, "special_or_unknown_archive_member")
            require(kind == "regular" or member.size == 0, "nonfile_member_has_payload")
            record = {"path": name, "type": kind, "bytes": member.size, "mode": oct(member.mode),
                      "archive_uid": member.uid, "archive_gid": member.gid,
                      "pax_keys": sorted(member.pax_headers)}
            end_of_members = max(end_of_members, member.offset_data + ((member.size + 511) // 512) * 512)
            if kind == "symlink":
                record["target"] = member.linkname
                record["lexical_target"] = link_target(name, member.linkname)
            elif kind == "regular":
                stream = archive.extractfile(member)
                require(stream is not None, "member_stream_missing")
                raw = stream.read(MAX_MEMBER + 1)
                require(len(raw) == member.size and len(raw) <= MAX_MEMBER, "member_data_truncated_or_oversized")
                total_files += len(raw)
                require(total_files <= MAX_EXPANDED, "member_total_ceiling")
                record["sha256"] = hashlib.sha256(raw).hexdigest()
                elf = inspect_elf(raw)
                if elf is not None:
                    elf_record = {"path": name, "bytes": len(raw), "sha256": record["sha256"], **elf}
                    elf_records[name] = elf_record
                    emit_elf(elf_record)
                if is_notice(name):
                    require(len(raw) <= MAX_NOTICE and notice_bytes + len(raw) <= MAX_NOTICES_TOTAL,
                            "notice_capture_ceiling")
                    notice_bytes += len(raw)
                    notice_count += 1
                    emit_notice({"path": name, "bytes": len(raw), "sha256": record["sha256"],
                                 "encoding": "base64_exact_original_bytes", "data_base64": base64.b64encode(raw).decode("ascii")})
            entries[name] = record
            if kind != "symlink":
                emit_member(record)
    require(entries.get("python", {}).get("type") == "directory", "python_root_directory_missing")
    # Reject hidden concatenated archives/junk and missing POSIX terminator blocks.
    source.seek(end_of_members)
    tail_bytes = 0
    while True:
        chunk = source.read(65536)
        if not chunk:
            break
        tail_bytes += len(chunk)
        require(not any(chunk), "nonzero_data_after_tar_members")
    require(tail_bytes >= 1024, "tar_terminator_missing")
    for name in entries:
        parent = posixpath.dirname(name)
        while parent:
            require(entries.get(parent, {}).get("type") == "directory", "archive_ancestor_not_directory")
            parent = posixpath.dirname(parent)
    for name, record in entries.items():
        if record["type"] != "symlink":
            continue
        record["resolved_target"] = resolve_link(name, entries)
        emit_member(record)
    executable = entries.get(CANONICAL_EXECUTABLE)
    require(executable is not None and executable["type"] == "regular"
            and executable["path"] in elf_records and int(executable["mode"], 8) & 0o111,
            "expected_versioned_elf_executable_missing")
    require(elf_records[CANONICAL_EXECUTABLE]["elf_type"] in (2, 3), "canonical_elf_not_executable")
    require(elf_records[CANONICAL_EXECUTABLE]["interpreter"] == EXPECTED_LOADER,
            "versioned_executable_loader_missing")
    require(notice_count > 0, "license_notice_inventory_empty")
    return {"members": len(entries), "regular_file_bytes": total_files, "elf_files": len(elf_records),
            "notice_files": notice_count, "notice_bytes": notice_bytes,
            "executable": {"path": CANONICAL_EXECUTABLE, "bytes": executable["bytes"], "sha256": executable["sha256"]},
            "dependency_names_observed": sorted({v for elf in elf_records.values() for v in elf["needed"]}),
            "all_symlink_targets_inside_inspected_tree": True, "tar_trailing_data_zero_only": True,
            "symlink_resolution_rule": "component_order_follow_then_dotdot_max_64_hops",
            "notice_discovery": "fixed_filename_and_directory_rule_completeness_unverified",
            "native_dependency_compatibility": "unverified", "license_clearance": "not_granted",
            "installation_allowed": False, "fetched_code_executions": 0}


class JsonLines:
    def __init__(self, stream):
        self.stream, self.bytes, self.records = stream, 0, 0

    def emit(self, value):
        raw = canonical(value)
        require(len(raw) <= MAX_JSON_LINE and self.bytes + len(raw) <= MAX_JSONL, "inventory_output_ceiling")
        self.stream.write(raw)
        self.stream.flush()
        self.bytes += len(raw)
        self.records += 1


def inspect_archive(directory):
    result = {"stage": "static_inspection", "status": "failed", "installation_allowed": False,
              "fetched_code_executions": 0, "native_dependency_compatibility": "unverified",
              "deadline_seconds": INSPECTION_SECONDS, "partial_inventory_is_acceptance": False}
    try:
        snapshot = read_archive_snapshot(directory)
        with _new_data(directory, TAR_FILE) as destination:
            tar_identity = decompress_to_data(snapshot, destination)
            destination.flush()
            os.fsync(destination.fileno())
        del snapshot
        fd = os.open(TAR_FILE, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        with os.fdopen(fd, "rb") as source, _new_data(directory, "archive-inventory.jsonl") as members, \
                _new_data(directory, "license-notices.jsonl") as notices, _new_data(directory, "elf-observations.jsonl") as elfs:
            before = os.fstat(source.fileno())
            require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_uid == 1000
                    and stat.S_IMODE(before.st_mode) == 0o600 and before.st_size == tar_identity["bytes"],
                    "tar_data_identity_not_trusted")
            member_writer, notice_writer, elf_writer = JsonLines(members), JsonLines(notices), JsonLines(elfs)
            observations = inspect_tar(source, member_writer.emit, notice_writer.emit, elf_writer.emit)
            source.seek(0)
            digest = hashlib.sha256()
            for chunk in iter(lambda: source.read(65536), b""):
                digest.update(chunk)
            require(digest.hexdigest() == tar_identity["sha256"]
                    and _identity(before) == _identity(os.fstat(source.fileno()))
                    == _identity(os.stat(TAR_FILE, dir_fd=directory, follow_symlinks=False)), "tar_changed_during_inspection")
            result.update({"status": "observed", "decompressed_tar": tar_identity, "observations": observations,
                           "inventory_records": member_writer.records, "notice_records": notice_writer.records,
                           "elf_records": elf_writer.records})
    except Exception as error:
        result["error"] = failure(error)
    _write_json(directory, "static-inspection.json", result)
    return result


def _worker(stage, directory):
    try:
        # Keep the workflow child's process group so its outer deadline kills
        # both controller and worker; never detach an acquisition descendant.
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_AS, (WORKER_MEMORY, WORKER_MEMORY))
        resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_EXPANDED, MAX_EXPANDED))
        (download_archive if stage == "acquisition" else inspect_archive)(directory)
    except BaseException as error:
        result = {"stage": stage, "status": "failed", "error": failure(error),
                  "installation_allowed": False, "fetched_code_executions": 0}
        name = "acquisition.json" if stage == "acquisition" else "static-inspection.json"
        _write_json(directory, name, result)


def _read_stage_receipt(directory, stage):
    name = "acquisition.json" if stage == "acquisition" else "static-inspection.json"
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_uid == 1000 and before.st_nlink == 1
                and stat.S_IMODE(before.st_mode) == 0o600 and before.st_size <= 256 * 1024,
                "untrusted_worker_receipt")
        raw = bytearray()
        while True:
            chunk = os.read(fd, min(65536, 256 * 1024 + 1 - len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
            require(len(raw) <= 256 * 1024, "worker_receipt_ceiling")
        require(len(raw) == before.st_size and _identity(before) == _identity(os.fstat(fd))
                == _identity(os.stat(name, dir_fd=directory, follow_symlinks=False)),
                "worker_receipt_changed")
        result = json.loads(raw, object_pairs_hook=unique,
                            parse_constant=lambda _: require(False, "nonfinite_worker_receipt"))
        require(isinstance(result, dict) and result.get("stage") == stage
                and result.get("installation_allowed") is False
                and result.get("fetched_code_executions") == 0, "invalid_worker_receipt")
        return result
    finally:
        os.close(fd)


def run_stage(stage, directory):
    require(stage in ("acquisition", "static_inspection"), "unexpected_stage")
    budget = DOWNLOAD_SECONDS if stage == "acquisition" else INSPECTION_SECONDS
    started = time.monotonic()
    process = multiprocessing.get_context("fork").Process(target=_worker, args=(stage, directory))
    result = None
    try:
        process.start()
        remaining = budget - (time.monotonic() - started)
        require(remaining > 0, "stage_absolute_deadline")
        process.join(max(0, remaining))
        require(not process.is_alive() and process.exitcode == 0 and time.monotonic() - started <= budget,
                "stage_worker_not_cleanly_finished")
        # Read bounded regular data only after the writer has exited. No pipe
        # poll/recv framing can block the parent on a partially sent message.
        result = _read_stage_receipt(directory, stage)
        require(time.monotonic() - started <= budget, "stage_absolute_deadline")
    except BaseException as error:
        result = {"stage": stage, "status": "failed", "error": failure(error),
                  "http_attempts": None if stage == "acquisition" else 0,
                  "worker_receipt_unconfirmed": True, "installation_allowed": False,
                  "fetched_code_executions": 0}
    finally:
        if process.pid is not None and process.is_alive():
            process.terminate()
            process.join(STOP_GRACE_SECONDS / 2)
            if process.is_alive():
                process.kill()
                process.join(STOP_GRACE_SECONDS / 2)
    result["elapsed_seconds"] = time.monotonic() - started
    result["absolute_stage_deadline_seconds"] = budget
    result["stop_grace_seconds"] = STOP_GRACE_SECONDS
    result["worker_exit_code"] = process.exitcode
    result["worker_stopped"] = not process.is_alive() if process.pid is not None else True
    return result


@contextmanager
def private_directory(path):
    path = Path(path)
    require(path.is_absolute() and ".." not in path.parts, "absolute_private_output_required")
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        info = os.fstat(fd)
        require(info.st_uid == 1000 and stat.S_IMODE(info.st_mode) == 0o700, "private_unprivileged_output_required")
        yield fd
    finally:
        os.close(fd)


def run(request, execution, output_path):
    validate_request(request, execution)
    require(os.geteuid() == 1000 and platform.system() == "Linux" and platform.machine() == "aarch64"
            and sys.version_info[:2] == (3, 9), "fixed_unprivileged_native_runtime_required")
    expected_leaf = "merlin-python-static-inspection-%d-1" % execution["run_id"]
    require(Path(output_path).name == expected_leaf, "fixed_evidence_leaf_required")
    result = {"schema": "merlin-python-static-inspection/1", "operation": OPERATION,
              "request": request, "execution": execution, "status": "failed",
              "publisher_expected": {"asset_id": ASSET_ID, "release_id": RELEASE_ID, "build_commit": BUILD_COMMIT,
                                     "bytes": EXPECTED_BYTES, "sha256": EXPECTED_SHA256},
              "logical_acquisitions_attempted": 0, "automatic_retries": 0,
              "installation_allowed": False, "native_installations": 0, "discovery_entries_created": 0,
              "fetched_code_executions": 0, "provider_changes": 0, "system_python_changes": 0,
              "model_calls": 0, "product_tests_run": 0, "qualification": False,
              "observed_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    with private_directory(output_path) as directory:
        try:
            require(not any(name in EVIDENCE_FILES for name in os.listdir(directory)), "existing_inspection_evidence_requires_review")
            result["logical_acquisitions_attempted"] = 1
            acquired = run_stage("acquisition", directory)
            result["acquisition"] = acquired
            require(acquired.get("status") == "verified" and acquired.get("archive_verified") is True
                    and acquired.get("worker_stopped") is True, "acquisition_not_verified")
            inspected = run_stage("static_inspection", directory)
            result["static_inspection"] = inspected
            require(inspected.get("status") == "observed" and inspected.get("worker_stopped") is True,
                    "static_inspection_incomplete")
            result["status"] = "static_observations_complete_installation_unapproved"
        except BaseException as error:
            result["error"] = failure(error)
        result["next_gate"] = ("Review actual member/link/notice/ELF observations and prepare a separately scoped, "
                               "hash-bound installer before any installation decision. Native dependency compatibility remains unverified.")
        _write_json(directory, "inspection-receipt.json", result)
    return result
