"""Fixed runner-side acquisition and dispatch for one reviewed real episode."""
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import urllib.request
from urllib.parse import urlsplit
import zipfile

PINS = {'host': {'bytes': 41164, 'git_blob': '9c9164b75c814aab8687a9efd85bc4ebec9648bc', 'sha256': '37ccabbd4fd2e33c028ec64a8da0f73394135118a4eba04c7948375e59ea3bff'}, 'native_validation': {'artifact_bytes': 648079, 'artifact_id': 14712123112, 'artifact_sha256': '77ad1e585dc978022515ef05683f2d59a5fd54b2f9bc576782ad600c72aeb75a', 'controller_git_blob': 'd4e3325a9d1c5c8c9d03b93c4b19b58e09232d04', 'controller_sha256': 'bb55bba0fe1fdf4b77e53c02d2f724f4301e550a96c75266092f11b3435503ef', 'report_sha256': '004c916100162ca83cd34dce50fc9704ea98cca058a4a20acd9660071910a271', 'run_attempt': 1, 'run_id': 44916652257, 'software_tests': 597, 'source_commit': 'ed6be62d577f0675d50a4487b7a9f43270bb515f', 'source_map_sha256': '85bc3c30d91c72c2f960a98539cdb72809a2ae0610df8e239018c77940452c2a', 'source_package_sha256': 'c4263a03ccfa9f728f186e0caf9f1382f8e4fc8501e4dc56f1cb2fde3b50cab6', 'test_inventory_sha256': '141f459fc85791b6cfca49001653847a32c1f08b30cbd865491c629e4c9ae1c8', 'workflow_commit': 'b2a7aacfcf73396ab92f2104245d70715fd2dd9d', 'workflow_git_blob': 'bb86a2d649d7ecaa2036dedf6622194f61f4b10d'}, 'notes': {'bytes': 4708, 'git_blob': '733d47fad0ce6379420a42b85e2d95317f61a089', 'sha256': 'ad412f724f95df30077a6fb21503a5f291478a0048f762e2c16bddefdbfb7192'}, 'oracle': {'bytes': 11332, 'git_blob': '4c7d2fbe711224de5b391c8e12b5cf1a877136aa', 'sha256': '73ad01b8443ab3e72ee3d54c43a75ff55104b75a3d4125cc17599cced87e9abb'}}
ENV = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def unique(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


class ArtifactRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        parsed = urlsplit(new_url)
        if (parsed.scheme != "https" or parsed.username or parsed.password or parsed.port not in (None, 443)
                or not (parsed.hostname and (parsed.hostname.endswith(".blob.core.windows.net")
                    or parsed.hostname.endswith(".actions.githubusercontent.com")
                    or parsed.hostname.endswith(".githubusercontent.com")))):
            raise ValueError("unexpected Actions artifact redirect")
        return urllib.request.Request(new_url, headers={"Accept": "application/zip"}, method="GET")


def exact_blob(api, identity, maximum):
    obj = api("git/blobs/" + identity["git_blob"])
    if obj.get("encoding") != "base64":
        raise ValueError("fixed blob encoding differs")
    raw = base64.b64decode("".join(obj["content"].split()), validate=True)
    if (len(raw) > maximum or len(raw) != identity["bytes"] or sha(raw) != identity["sha256"]
            or hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() != identity["git_blob"]):
        raise ValueError("fixed published blob bytes differ")
    return raw


def native_artifact(api):
    n = PINS["native_validation"]
    run = api("actions/runs/" + str(n["run_id"]))
    if (run.get("id") != n["run_id"] or run.get("head_sha") != n["workflow_commit"]
            or run.get("run_attempt") != 1 or run.get("status") != "completed"
            or run.get("conclusion") != "success" or run.get("head_branch") != "merlin/platform-acceptance-20261120"
            or run.get("path") != ".github/workflows/merlin-egm-context.yml"):
        raise ValueError("actual native validation run differs")
    artifact = api("actions/artifacts/" + str(n["artifact_id"]))
    if (artifact.get("expired") is not False or artifact.get("size_in_bytes") != n["artifact_bytes"]
            or artifact.get("workflow_run", {}).get("id") != n["run_id"]
            or artifact.get("workflow_run", {}).get("head_sha") != n["workflow_commit"]
            or artifact.get("digest") != "sha256:" + n["artifact_sha256"]):
        raise ValueError("actual native artifact identity differs")
    request = urllib.request.Request("https://api.github.com/repos/morganaspim/Cace-app/actions/artifacts/"
        + str(n["artifact_id"]) + "/zip", headers={"Authorization": "Bearer " + os.environ["GITHUB_TOKEN"],
                                                   "Accept": "application/vnd.github+json"})
    with urllib.request.build_opener(ArtifactRedirect()).open(request, timeout=30) as response:
        raw = response.read(n["artifact_bytes"] + 1)
    if len(raw) != n["artifact_bytes"] or sha(raw) != n["artifact_sha256"]:
        raise ValueError("native artifact download bytes differ")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        items = archive.infolist()
        if len(items) > 64 or len({item.filename for item in items}) != len(items) or sum(item.file_size for item in items) > 8 * 1024 * 1024:
            raise ValueError("native evidence archive ceiling")
        report_raw = archive.read("report.json")
        if sha(report_raw) != n["report_sha256"]:
            raise ValueError("native report bytes differ")
        report = json.loads(report_raw, object_pairs_hook=unique)
        if (report.get("status") != "succeeded" or report.get("source_commit") != n["source_commit"]
                or report.get("source_map_sha256") != n["source_map_sha256"]
                or report.get("source_package_sha256") != n["source_package_sha256"]):
            raise ValueError("native report source binding differs")
        source = archive.read("tested-source.zip")
        if len(source) > 4 * 1024 * 1024 or sha(source) != n["source_package_sha256"]:
            raise ValueError("actual tested source package differs")
    return source


def run(api, request, output):
    output = Path(output)
    source = native_artifact(api)
    host = exact_blob(api, PINS["host"], 48 * 1024)
    oracle = exact_blob(api, PINS["oracle"], 32000)
    notes = exact_blob(api, PINS["notes"], 32000)
    for name, raw in (("tested-source.zip", source), ("research_episode_host.py", host),
                      ("oracle.json", oracle), ("source-notes.json", notes)):
        (output / name).write_bytes(raw)
    invocation = {"request_id": request["request_id"], "run_id": int(os.environ["GITHUB_RUN_ID"]),
                  "run_attempt": int(os.environ["GITHUB_RUN_ATTEMPT"]), "workflow_commit": os.environ["GITHUB_SHA"]}
    if invocation["run_attempt"] != 1:
        raise ValueError("automatic workflow retry is not a provider retry authorization")
    (output / "invocation.json").write_bytes(canonical(invocation))
    (output / "native-validation-binding.json").write_bytes(canonical(PINS["native_validation"]))
    program = ("import hashlib;source=" + repr(host) + ";assert hashlib.sha256(source).hexdigest()=="
        + repr(PINS["host"]["sha256"]) + ";namespace={'_HOST_SOURCE_SHA256':" + repr(PINS["host"]["sha256"])
        + "};exec(compile(source,'pinned-research-host','exec'),namespace);namespace['root_run']("
        + repr(str(output)) + "," + repr(str(output)) + ")")
    if len(program.encode()) > 96 * 1024:
        raise ValueError("fixed privileged invocation byte ceiling")
    try:
        result = subprocess.run(["/usr/bin/sudo", "-n", "/usr/bin/python3", "-I", "-B", "-S", "-c", program],
                                env=ENV, cwd="/", capture_output=True, timeout=4000)
        if len(result.stdout) + len(result.stderr) > 128 * 1024:
            raise ValueError("supervisor diagnostic ceiling")
        (output / "host-process.txt").write_bytes(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError("actual fixed research host operation failed")
    except subprocess.TimeoutExpired as exc:
        (output / "host-timeout.txt").write_bytes((exc.stdout or b"")[:65536] + (exc.stderr or b"")[:65536])
        raise
    receipt = json.loads((output / "host-receipt.json").read_bytes(), object_pairs_hook=unique)
    if receipt.get("status") != "succeeded" or receipt.get("native_validation") != PINS["native_validation"]:
        raise ValueError("actual research operation receipt differs")
