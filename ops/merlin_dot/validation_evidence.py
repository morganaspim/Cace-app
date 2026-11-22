"""Bind a host-changing operation to a specific successful validate receipt."""
import base64
import hashlib
from io import BytesIO
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import zipfile


REPOSITORY = "morganaspim/Cace-app"
WORKFLOW = ".github/workflows/merlin-dot-oci-operations.yml"
MAX_ARCHIVE = 4 * 1024 * 1024
MAX_RECEIPT = 256 * 1024
# The workflow itself pins its operation and installer blobs. This historical
# producer was inspected at validation run 44144790708 (3080cca6...).
REVIEWED_PRIOR_WORKFLOW = "97ada08fd912d80034ad4926f255f8e9a788c224"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _download(artifact_id, expected_size):
    # Only the repository API receives the existing read-only Actions token.
    # A separate header-free request follows GitHub's signed storage URL.
    api_url = f"https://api.github.com/repos/{REPOSITORY}/actions/artifacts/{artifact_id}/zip"
    request = urllib.request.Request(api_url, headers={"Authorization": "Bearer " + os.environ["GITHUB_TOKEN"],
                                                       "Accept": "application/vnd.github+json"})
    opener = urllib.request.build_opener(_NoRedirect())
    try:
        with opener.open(request, timeout=20):
            raise RuntimeError("missing Actions artifact download redirect")
    except urllib.error.HTTPError as response:
        with response:
            if response.code != 302:
                raise RuntimeError("Actions artifact unavailable") from None
            location = response.headers.get("Location", "")
    url = urllib.parse.urlsplit(location)
    if (url.scheme != "https" or url.username is not None or url.password is not None or url.port not in (443, None)
            or not url.hostname or not url.hostname.endswith((".blob.core.windows.net", ".actions.githubusercontent.com",
                                                              ".githubusercontent.com"))):
        raise RuntimeError("unexpected Actions storage redirect")
    try:
        with opener.open(urllib.request.Request(location), timeout=20) as response:
            return response.read(expected_size + 1)
    except (OSError, ValueError):
        raise RuntimeError("unable to read Actions artifact") from None


def _json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate evidence field")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs)


def check_validation(request, api, bundle_blob, bundle_sha, manifest_files, minimum_tests, download=None):
    run_id, commit = request["validation_run_id"], request["validation_commit"]
    if type(run_id) is not int or run_id < 1 or not isinstance(commit, str) or not re.fullmatch("[0-9a-f]{40}", commit):
        raise ValueError("invalid validation run binding")
    branch = os.environ["GITHUB_REF"].removeprefix("refs/heads/")
    run = api(f"actions/runs/{run_id}")
    attempt = run.get("run_attempt")
    if (run.get("id") != run_id or type(attempt) is not int or attempt < 1 or run.get("event") != "push"
            or run.get("path") != WORKFLOW or run.get("head_sha") != commit or run.get("head_branch") != branch
            or not branch.startswith("merlin/dot-ops/") or run.get("repository", {}).get("full_name") != REPOSITORY
            or run.get("head_repository", {}).get("full_name") != REPOSITORY or run.get("status") != "completed"
            or run.get("conclusion") != "success"):
        raise ValueError("successful exact same-branch validation run required")
    # A successful run on the same branch can still use unrelated workflow code.
    current_workflow = api(f"contents/{WORKFLOW}?ref=" + os.environ["GITHUB_SHA"]).get("sha")
    prior_workflow = api(f"contents/{WORKFLOW}?ref=" + commit).get("sha")
    if (not isinstance(current_workflow, str) or not re.fullmatch("[0-9a-f]{40}", current_workflow)
            or prior_workflow not in {current_workflow, REVIEWED_PRIOR_WORKFLOW}):
        raise ValueError("prior validation workflow definition is outside the reviewed producers")
    revision = api("commits/" + commit)
    files = revision.get("files", [])
    if revision.get("sha") != commit or len(files) != 1 or files[0].get("status") != "added":
        raise ValueError("validation commit must add exactly one request")
    added = files[0]
    match = re.fullmatch(r"merlin/dot-requests/([0-9a-f-]{36})\.json", added.get("filename", ""))
    if not match or not re.fullmatch("[0-9a-f]{40}", added.get("sha", "")):
        raise ValueError("invalid prior request identity")
    blob = api("git/blobs/" + added["sha"])
    if (blob.get("sha") != added["sha"] or blob.get("encoding") != "base64"
            or type(blob.get("size")) is not int or not 1 <= blob["size"] <= 16000
            or not isinstance(blob.get("content"), str) or len(blob["content"]) > 24000):
        raise ValueError("invalid prior request blob")
    raw = base64.b64decode("".join(blob["content"].split()), validate=True)
    if len(raw) != blob["size"] or hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest() != added["sha"]:
        raise ValueError("prior request bytes mismatch")
    prior = _json(raw)
    if (set(prior) != {"schema", "request_id", "operation", "created_at"}
            or prior.get("schema") != "merlin-dot-ops-request-v1" or prior.get("operation") != "validate"
            or prior.get("request_id") != match.group(1)):
        raise ValueError("prior request must be validate for this request ID")
    name = f"merlin-dot-operation-{run_id}-{attempt}"
    listing = api(f"actions/runs/{run_id}/artifacts?name={name}&per_page=2")
    if listing.get("total_count") != 1 or len(listing.get("artifacts", [])) != 1:
        raise ValueError("one exact validation attempt artifact required")
    item = listing["artifacts"][0]
    origin = item.get("workflow_run") or {}
    archive_id, size, archive_digest = item.get("id"), item.get("size_in_bytes"), item.get("digest")
    if (item.get("name") != name or item.get("expired") is not False or origin.get("id") != run_id
            or origin.get("head_sha") != commit or origin.get("head_branch") != branch
            or origin.get("repository_id") != run["repository"]["id"]
            or origin.get("head_repository_id") != run["head_repository"]["id"]
            or type(archive_id) is not int or archive_id < 1 or type(size) is not int or not 1 <= size <= MAX_ARCHIVE
            or not isinstance(archive_digest, str) or not re.fullmatch("sha256:[0-9a-f]{64}", archive_digest)):
        raise ValueError("validation attempt artifact metadata mismatch")
    archive = (download or _download)(archive_id, size)
    if len(archive) != size or "sha256:" + hashlib.sha256(archive).hexdigest() != archive_digest:
        raise ValueError("validation archive digest or size mismatch")
    with zipfile.ZipFile(BytesIO(archive)) as handle:
        members = [member for member in handle.infolist() if member.filename == "operation-receipt.json"]
        if len(members) != 1 or not 1 <= members[0].file_size <= MAX_RECEIPT:
            raise ValueError("one bounded operation receipt required")
        with handle.open(members[0]) as stream:
            receipt_bytes = stream.read(MAX_RECEIPT + 1)
    if len(receipt_bytes) != members[0].file_size:
        raise ValueError("validation receipt size mismatch")
    receipt = _json(receipt_bytes)
    expected = {"schema": "merlin-dot-operation-receipt/1", "operation": "validate", "status": "succeeded",
                "runner": "cace-oci-a1", "request_id": prior["request_id"], "bundle_git_blob": bundle_blob,
                "bundle_sha256": bundle_sha, "source_files": manifest_files, "run_id": str(run_id),
                "workflow_commit": commit, "host_configuration_changed": False, "qualification": False,
                "promotion_authority": False}
    if any(field not in receipt or json.dumps(receipt[field], sort_keys=True) != json.dumps(value, sort_keys=True)
           for field, value in expected.items()):
        raise ValueError("validation receipt differs from operation, source, package or run")
    tests = receipt.get("tests", {})
    if (tests.get("passed") is not True or type(tests.get("tests")) is not int or tests["tests"] < minimum_tests
            or any(type(tests.get(key)) is not int or tests[key] != 0 for key in ("errors", "failures", "skipped"))):
        raise ValueError("validation receipt lacks required passing tests")
    return {"validation_run_id": run_id, "validation_run_attempt": attempt, "validation_commit": commit,
            "validation_request_id": prior["request_id"], "workflow_git_blob": prior_workflow,
            "artifact_id": archive_id, "archive_digest": archive_digest,
            "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(), "bundle_sha256": bundle_sha,
            "bundle_git_blob": bundle_blob, "tests_passed": tests["tests"]}
