"""Fixed read-only reconciliation for browser run 44956695079.

This module has no acceptance, activation, cleanup, connection or acquisition
entrypoint. The original acceptance controller and its absence guard are
unchanged. Only the private runner evidence leaf may receive new files.
"""
from contextlib import contextmanager
import datetime
import fcntl
import os
from pathlib import Path
import platform
import re
import stat
import sys
import uuid

import bootstrap_browser as B


OPERATION = "inspect-state-44956695079"
FAILED_RUN = 44956695079
FAILED_REQUEST = "3eadad53-ba62-4a35-9578-eebe65420f76"
PRIOR_REQUEST = "18106dfc-0a56-4b68-9d30-5d334d7d6a69"
STATE = Path("/var/lib/merlin-browser-bootstrap")
SOCKET_PATH = "/run/merlin-public-browser/browser.sock"
MARKER_PATH = STATE / ("ledger-successor-from-" + PRIOR_REQUEST + ".json")
GUARD_PATHS = (
    STATE / FAILED_REQUEST,
    MARKER_PATH,
    Path("/opt/merlin-public-browser/releases/ebdca90a42bbb243ac04872bdf3f1210ea20583cce9b4c34c7867af1873cb959"),
    Path("/opt/merlin-public-browser/current"),
    Path(SOCKET_PATH),
    Path("/var/lib/merlin-public-browser/episodes/recovered-arxiv-" + PRIOR_REQUEST),
)
PROC_UNIX = Path("/proc/net/unix")
PROC_LIMIT = 128 * 1024
MARKER_LIMIT = 32 * 1024
READLINK_LIMIT = 1024
SOCKET_ROW_LIMIT = 16
UNIT = "merlin-public-browser.service"
UNIT_FIELDS = (
    "LoadState", "ActiveState", "SubState", "Result", "MainPID", "ExecMainPID",
    "ExecMainCode", "ExecMainStatus", "UnitFileState", "FragmentPath",
    "ControlGroup", "User", "Group", "RuntimeDirectory", "NRestarts",
    "InvocationID", "ActiveEnterTimestampMonotonic", "InactiveEnterTimestampMonotonic",
)
EVIDENCE_FILES = ("supervisor-state.txt", "supervisor-state.txt.json", "state-inspection.json")


def require(value, message):
    if not value:
        raise B.BootstrapError(message)


def error_record(error):
    return {"type": type(error).__name__, "message": str(error)[:800]}


def validate_request(request, execution):
    require(isinstance(request, dict)
            and set(request) == {"schema", "request_id", "operation", "created_at"},
            "fixed inspection request fields required")
    require(request["schema"] == "merlin-browser-state-inspection-request/1"
            and request["operation"] == OPERATION, "fixed read-only operation required")
    try:
        request_id = request["request_id"]
        valid_id = isinstance(request_id, str) and str(uuid.UUID(request_id)) == request_id
        stamp = datetime.datetime.strptime(request["created_at"], "%Y-%m-%dT%H:%M:%SZ")
        valid_date = stamp.strftime("%Y-%m-%dT%H:%M:%SZ") == request["created_at"]
    except (ValueError, TypeError, AttributeError):
        valid_id = valid_date = False
    require(valid_id and valid_date and request_id not in
            (FAILED_REQUEST, PRIOR_REQUEST, "99cc5d7f-488f-4718-8257-5edda04726e4"),
            "new canonical inspection UUID and UTC timestamp required")
    require(isinstance(execution, dict)
            and execution.get("repository") == "morganaspim/Cace-app"
            and execution.get("ref") == "refs/heads/merlin/browser-operations-20261121"
            and execution.get("runner") == "cace-oci-a1"
            and type(execution.get("run_attempt")) is int and execution["run_attempt"] == 1
            and type(execution.get("run_id")) is int and execution["run_id"] > FAILED_RUN
            and isinstance(execution.get("workflow_commit"), str)
            and re.fullmatch("[0-9a-f]{40}", execution["workflow_commit"]),
            "fixed first native inspection identity required")


def metadata(info):
    kinds = {stat.S_IFREG: "regular", stat.S_IFDIR: "directory", stat.S_IFLNK: "symlink",
             stat.S_IFSOCK: "socket", stat.S_IFIFO: "fifo", stat.S_IFCHR: "character",
             stat.S_IFBLK: "block"}
    return {"type": kinds.get(stat.S_IFMT(info.st_mode), "unknown"),
            "uid": info.st_uid, "gid": info.st_gid, "mode": oct(stat.S_IMODE(info.st_mode)),
            "mode_bits": info.st_mode, "dev": info.st_dev, "inode": info.st_ino,
            "nlink": info.st_nlink, "bytes": info.st_size,
            "mtime_ns": info.st_mtime_ns, "ctime_ns": info.st_ctime_ns}


@contextmanager
def parent_fd(path):
    """Walk only fixed path parents, refusing symlink traversal and listing none."""
    path = Path(path)
    require(path.is_absolute() and ".." not in path.parts, "fixed absolute observation path required")
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parent.parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        yield fd
    finally:
        os.close(fd)


def inspect_path(path):
    path = Path(path)
    result = {"path": str(path), "status": "unknown", "exists": None, "follows_symlinks": False}
    observed = False
    try:
        with parent_fd(path) as fd:
            before = os.stat(path.name, dir_fd=fd, follow_symlinks=False)
            observed = True
            result.update({"status": "present", "exists": True, "metadata": metadata(before)})
            if stat.S_ISLNK(before.st_mode):
                target = os.readlink(path.name, dir_fd=fd)
                require(len(os.fsencode(target)) <= READLINK_LIMIT, "readlink target exceeds bound")
                result["readlink"] = target
            after = os.stat(path.name, dir_fd=fd, follow_symlinks=False)
            require(metadata(before) == metadata(after), "path changed during metadata observation")
    except FileNotFoundError as error:
        if observed:
            result.update({"status": "unknown", "error": error_record(error)})
        else:
            result.update({"status": "absent", "exists": False})
    except Exception as error:
        result.update({"status": "unknown", "error": error_record(error)})
    return result


def inspect_marker():
    result = {"path": str(MARKER_PATH), "status": "unknown", "verified": False,
              "byte_limit": MARKER_LIMIT, "follows_symlinks": False}
    observed = False
    fd = None
    try:
        with parent_fd(MARKER_PATH) as directory:
            before = os.stat(MARKER_PATH.name, dir_fd=directory, follow_symlinks=False)
            observed = True
            result["metadata"] = metadata(before)
            require(stat.S_ISREG(before.st_mode) and before.st_uid == 0
                    and before.st_nlink == 1 and not before.st_mode & 0o022,
                    "marker is not an immutable root-owned regular single-link file")
            require(before.st_size <= MARKER_LIMIT, "marker byte ceiling")
            fd = os.open(MARKER_PATH.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
            require(metadata(os.fstat(fd)) == metadata(before), "marker changed before read")
            chunks = []
            size = 0
            while True:
                raw = os.read(fd, min(8192, MARKER_LIMIT + 1 - size))
                if not raw:
                    break
                chunks.append(raw)
                size += len(raw)
                require(size <= MARKER_LIMIT, "marker byte ceiling")
            raw = b"".join(chunks)
            require(metadata(os.fstat(fd)) == metadata(before)
                    and metadata(os.stat(MARKER_PATH.name, dir_fd=directory, follow_symlinks=False)) == metadata(before)
                    and len(raw) == before.st_size, "marker changed during read")
            value = B.decode(raw)
            require(isinstance(value, dict), "marker must contain a JSON object")
            text = raw.decode("utf-8")
            result.update({"status": "observed", "verified": True, "bytes": len(raw),
                           "sha256": B.digest(raw), "raw_json_utf8": text,
                           "schema": value.get("schema"),
                           "lineage_qualification": False})
    except FileNotFoundError as error:
        if observed:
            result["error"] = error_record(error)
        else:
            result.update({"status": "absent", "reason": "marker absent at observation"})
    except Exception as error:
        result["error"] = error_record(error)
    finally:
        if fd is not None:
            os.close(fd)
    return result


def inspect_socket_table():
    result = {"source": str(PROC_UNIX), "status": "unknown", "matching_path": SOCKET_PATH,
              "byte_limit": PROC_LIMIT, "row_limit": SOCKET_ROW_LIMIT, "rows": [], "matches": None}
    try:
        raw = B.regular(PROC_UNIX, PROC_LIMIT)
        lines = raw.decode("utf-8", "surrogateescape").splitlines()
        require(lines and lines[0].split() == ["Num", "RefCount", "Protocol", "Flags", "Type", "St", "Inode", "Path"],
                "unexpected proc Unix table header")
        require(len(lines) <= 4096, "proc Unix table row ceiling")
        for line in lines[1:]:
            columns = line.split(None, 7)
            if len(columns) != 8 or columns[7] != SOCKET_PATH:
                continue
            require(len(line.encode("utf-8", "surrogateescape")) <= 2048, "matching socket row byte ceiling")
            require(len(result["rows"]) < SOCKET_ROW_LIMIT, "matching socket row count ceiling")
            result["rows"].append({"raw": line, "num": columns[0], "ref_count": columns[1],
                                   "protocol": columns[2], "flags": columns[3], "type": columns[4],
                                   "state": columns[5], "inode": columns[6], "path": columns[7]})
        result.update({"status": "observed", "matches": len(result["rows"])})
    except Exception as error:
        result["error"] = error_record(error)
    return result


def inspect_supervisor(output):
    argv = ["/usr/bin/systemctl", "show", UNIT, "--no-pager"] + ["--property=" + key for key in UNIT_FIELDS]
    result = {"unit": UNIT, "status": "unknown", "properties": {}, "timeout_seconds": 5,
              "byte_limit": 16384, "raw_evidence": "supervisor-state.txt"}
    try:
        raw = B.command(argv, output / "supervisor-state.txt", timeout=5, limit=16384, allowed=(0, 3, 4))
        properties = B.unique(line.split("=", 1) for line in raw.decode("utf-8").splitlines() if "=" in line)
        require(set(properties) == set(UNIT_FIELDS), "fixed supervisor fields incomplete or unexpected")
        require(properties["MainPID"].isdigit(), "supervisor MainPID is not numeric")
        result.update({"status": "observed", "properties": properties, "bytes": len(raw), "sha256": B.digest(raw)})
    except Exception as error:
        result["error"] = error_record(error)
    return result


def collect_observation(output, request, execution):
    paths = [inspect_path(path) for path in GUARD_PATHS]
    marker = inspect_marker()
    unit = inspect_supervisor(output)
    sockets = inspect_socket_table()
    present = any(item["status"] == "present" for item in paths)
    known = all(item["status"] in ("present", "absent") for item in paths)
    complete = known and marker["status"] in ("observed", "absent") and unit["status"] == sockets["status"] == "observed"
    return {"schema": "merlin-browser-state-inspection/1", "operation": OPERATION,
            "request": request, "execution": execution, "failed_run_id": FAILED_RUN,
            "failed_request_id": FAILED_REQUEST, "status": "inspection_complete" if complete else "inspection_incomplete",
            "complete": bool(complete), "observed_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "paths": paths, "successor_marker": marker, "supervisor": unit, "unix_socket_table": sockets,
            "all_six_absent_snapshot": False if present else (True if known else None),
            "acceptance_allowed": False, "qualification": False, "application_mutations": 0,
            "connections": 0, "acquisitions": 0, "model_calls": 0,
            "observation_scope": "Metadata for six fixed paths; bounded exact marker JSON if trusted; fixed unit fields; matching Unix socket rows only. No atomic cross-subsystem snapshot claimed."}


def existing_root(path):
    for item in reversed([path] + list(path.parents)):
        info = item.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022,
                "existing root-owned state directory required")


def run(request, execution, output_path):
    require(os.geteuid() == 0 and platform.machine() == "aarch64" and sys.version_info[:2] == (3, 9),
            "native root read-only state inspection required")
    os.umask(0o022)
    validate_request(request, execution)
    output_path = Path(output_path)
    parent = B.operation_directory(output_path)
    leaf = lock = None
    try:
        os.mkdir("root-evidence", mode=0o700, dir_fd=parent)
        leaf = os.open("root-evidence", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        info = os.fstat(leaf)
        require(info.st_uid == 0 and stat.S_IMODE(info.st_mode) == 0o700 and not os.listdir(leaf),
                "new private root evidence leaf required")
        output = Path("/proc/self/fd") / str(leaf)
        try:
            existing_root(STATE)
            lock = os.open(str(STATE / "operation.lock"), os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK)
            info = os.fstat(lock)
            require(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022,
                    "existing immutable root-owned operation lock required")
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = collect_observation(output, request, execution)
        except Exception as error:
            result = {"schema": "merlin-browser-state-inspection/1", "operation": OPERATION,
                      "request": request, "execution": execution, "failed_run_id": FAILED_RUN,
                      "failed_request_id": FAILED_REQUEST, "status": "inspection_incomplete",
                      "complete": False, "error": error_record(error), "acceptance_allowed": False,
                      "qualification": False, "application_mutations": 0, "connections": 0,
                      "acquisitions": 0, "model_calls": 0}
        raw = B.canonical(result)
        require(len(raw) <= 192 * 1024, "inspection evidence byte ceiling")
        B.write(output / "state-inspection.json", raw)
        # Check held evidence inodes before returning the read-only receipt.
        parent_check = B.operation_directory(output_path)
        leaf_check = B.operation_directory(output_path / "root-evidence", owner=0)
        try:
            for first, second in ((parent, parent_check), (leaf, leaf_check)):
                left, right = os.fstat(first), os.fstat(second)
                require((left.st_dev, left.st_ino) == (right.st_dev, right.st_ino), "inspection evidence path moved")
        finally:
            os.close(parent_check)
            os.close(leaf_check)
        return result
    finally:
        if lock is not None:
            os.close(lock)
        if leaf is not None:
            for name in EVIDENCE_FILES:
                try:
                    info = os.stat(name, dir_fd=leaf, follow_symlinks=False)
                except FileNotFoundError:
                    continue
                require(stat.S_ISREG(info.st_mode) and info.st_uid == 0, "unexpected evidence member")
                os.chown(name, 1000, 1000, dir_fd=leaf, follow_symlinks=False)
            os.fchown(leaf, 1000, 1000)
            os.close(leaf)
        os.close(parent)
