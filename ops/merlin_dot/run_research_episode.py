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

PINS = {'host': {'bytes': 48844, 'git_blob': 'a987382418e578942793ff4147b1a74f1b404747', 'sha256': '927651cd0499fe2b2ec6165abcaafb3025c82105748696cb95e56e0c2a91a1e9'}, 'native_validation': {'artifact_bytes': 650520, 'artifact_id': 14712858088, 'artifact_sha256': '8c0f034e899dc73ac6731f802a2f390aa1c80eb37c2f1216968da709a081598d', 'controller_git_blob': 'cf612303b8b74f91ff6eddec7dfcf1f32eb3a3c5', 'controller_sha256': '58d07437d683b617d8452af666025ace74b0395a7fa26708fc0423a4b468e258', 'report_sha256': 'b187142c4f522a3d4876f66a10c2d5792ee2b146e8d3a952e36bfe1e3755f43d', 'run_attempt': 1, 'run_id': 44919201279, 'software_tests': 599, 'source_commit': '761756025fb88f7e722c799ca91964e3ad24c53a', 'source_map_sha256': '548194d9fddd5a587feeb5384bf6b71f9fe7cee4976dab519725251fb2ca3654', 'source_package_sha256': '31afbda693cfcbe75bdfa56a3b47571271c7a6e817fd1264a56d6f23930da4ad', 'test_inventory_sha256': '8fea9b239870559acc888ddd7d003d8754234dfa1f8497020de5dc108c8cfd4b', 'workflow_commit': 'c1c901f320f45f4ed6b9b93fb886b18ffeb25bcf', 'workflow_git_blob': '86f5f0bb48d61972d778d078922cdb9855d49851'}, 'notes': {'bytes': 4708, 'git_blob': '733d47fad0ce6379420a42b85e2d95317f61a089', 'sha256': 'ad412f724f95df30077a6fb21503a5f291478a0048f762e2c16bddefdbfb7192'}, 'oracle': {'bytes': 11332, 'git_blob': '4c7d2fbe711224de5b391c8e12b5cf1a877136aa', 'sha256': '73ad01b8443ab3e72ee3d54c43a75ff55104b75a3d4125cc17599cced87e9abb'}}
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
