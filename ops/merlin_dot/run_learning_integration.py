"""Pinned, unprivileged Merlin/LMS/Titan integration and retrieval validation."""
import base64
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import stat
import subprocess
import sys
import zipfile

BLOB = "f69f9d69a5bd8f9fe4f7bb667dd724df08ed5593"
DIGEST = "d19cea17621469286a075a3ed800616209809e317f46aee26d11f13be77a37dd"
SOURCE_COMMIT = "47260febc9726ec6d02c798b0fd99780b19dba29"
MINIMUM_TESTS = 130
FIXTURE_PATH = "tests/fixtures/learning-evidence-eval-v1.json"
PATTERNS = ["test_merlin_learning_platform.py", "test_learning_submission_binding.py",
    "test_learning_lab_bridge.py", "test_learning_titan_integration.py", "test_titan_crypto_lab.py",
    "test_titan_protocol_model.py", "test_titan_registry_integration.py", "test_titan_hermes_evidence_flow.py",
    "test_cace_adapter.py", "test_cace_attestation.py", "test_registry_concurrent_publication.py",
    "test_knowledge_graph_concurrency.py", "test_project_registry.py",
    "test_dot_context.py", "test_learning_evidence.py", "test_learning_evidence_evaluation.py"]

TEST_CODE = """import unittest,json,sys
s=unittest.TestSuite()
for pattern in json.loads(sys.argv[1]):s.addTests(unittest.defaultTestLoader.discover('tests',pattern=pattern))
r=unittest.TextTestRunner(verbosity=2).run(s)
v={'tests':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'skipped':len(r.skipped),'passed':r.wasSuccessful() and not r.skipped and r.testsRun>=int(sys.argv[2])}
print('MERLIN_LEARNING_TESTS='+json.dumps(v,sort_keys=True));sys.exit(0 if v['passed'] else 1)
"""
DEMO_CODE = """import json,sys
from pathlib import Path
from merlin.learning_titan_course import run_synthetic_titan_demo
root=Path(sys.argv[1]);first=run_synthetic_titan_demo(root/'titan',sys.argv[2]);again=run_synthetic_titan_demo(root/'titan',sys.argv[2])
assert first['lab']==again['lab'] and first['frozen_transcript_ref']==again['frozen_transcript_ref']
assert first['submission']['status']=='pending_review' and again['submission']['duplicate'] is True
for result in (first,again):
 assert result['mastery_updated'] is False and result['proof_qualified'] is False
 assert result['cryptographic_security_verified'] is False and result['educational_efficacy_established'] is False
 assert result['promotion_authority'] is False and result['lab']['qualification'] is False
 assert result['lab']['verification_status']=='blocked_missing_credentials'
summary={'schema':'merlin-learning-titan-oci-demo/2','fixture_class':'synthetic_known_fixture',
 'source_commit':sys.argv[2],'course_id':first['course_id'],'course_version':first['version'],
 'course_manifest_sha256':first['manifest_sha256'],'frozen_transcript_ref':first['frozen_transcript_ref'],
 'lab_artifact_ref':first['lab']['artifact_ref'],'model_sha256':first['lab']['model_sha256'],
 'vectors_sha256':first['lab']['vectors_sha256'],'vector_count':first['lab']['vector_count'],
 'submission_status':first['submission']['status'],'replay_duplicate':again['submission']['duplicate'],
 'canonical_receipt_replay_equal':True,'verification_status':first['lab']['verification_status'],
 'synthetic_publication_review':True,'mastery_updated':False,'qualification':False,
 'cryptographic_security_verified':False,'educational_efficacy_established':False,'promotion_authority':False}
from merlin.learning_evidence_eval import run_synthetic_evidence_demo
from merlin.project_registry import MerlinRegistry
import hashlib
evidence_root=root/'retrieval'
evidence=run_synthetic_evidence_demo(evidence_root,sys.argv[2])
replay=run_synthetic_evidence_demo(evidence_root,sys.argv[2])
assert evidence==replay
assert evidence['metrics']=={'case_count':4,'passed':4,'failed':0,'development_passed':1,'evaluation_passed':3}
registry=MerlinRegistry(evidence_root/'registry')
def export(ref):
 raw=registry.read_artifact_ref(ref)['content']
 assert hashlib.sha256(raw).hexdigest()==ref['sha256']
 return {'ref':ref,'content_utf8':raw.decode('utf-8')}
report=export(evidence['report_ref']);protocol=export(evidence['protocol_ref'])
parsed=json.loads(report['content_utf8'])
candidates=[export(case['candidate_ref']) for case in parsed['cases']]
(root.parent/'learning-evidence-evaluation.json').write_text(json.dumps({'schema':'merlin-learning-evidence-canonical-export/1','source_commit':sys.argv[2],'protocol':protocol,'report':report,'candidates':candidates,'raw_private_context_included':False},indent=2,sort_keys=True))
summary['retrieval_evaluation']={**evidence,'canonical_replay_equal':True}
print(json.dumps(summary,sort_keys=True))
"""


def run_learning_integration(request, api, output):
    report = {"schema": "merlin-learning-integration-validation/1", "operation": "validate_learning",
        "request_id": request["request_id"], "run_id": os.environ["GITHUB_RUN_ID"],
        "workflow_commit": os.environ["GITHUB_SHA"], "runner": os.environ.get("RUNNER_NAME"),
        "source_repository": "Mannyspiro/expert-robot", "source_commit": SOURCE_COMMIT,
        "package_git_blob": BLOB, "package_sha256": DIGEST, "architecture": platform.machine(),
        "python": list(sys.version_info[:3]), "host_configuration_changed": False,
        "production_service_modified": False, "raw_private_context_included": False,
        "qualification": False, "promotion_authority": False}

    def save():
        (output / "learning-integration-receipt.json").write_text(json.dumps(report, indent=2, sort_keys=True))

    try:
        obj = api("git/blobs/" + BLOB)
        if obj.get("sha") != BLOB or obj.get("encoding") != "base64":
            raise ValueError("fixed learning package object required")
        raw = base64.b64decode(obj["content"])
        if len(raw) > 1024 * 1024 or hashlib.sha256(raw).hexdigest() != DIGEST:
            raise ValueError("fixed learning package size/digest mismatch")
        root = output / "learning-source"
        root.mkdir(mode=0o700)
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            infos = archive.infolist()
            names = [i.filename for i in infos]
            if len(names) != len(set(names)) or len(names) > 100 or sum(i.file_size for i in infos) > 4 * 1024 * 1024:
                raise ValueError("bounded unique code/fixture archive required")
            manifest = json.loads(archive.read("manifest.json"))
            if (manifest.get("schema") != "merlin-learning-integration/1"
                    or manifest.get("source_commit") != SOURCE_COMMIT
                    or manifest.get("test_patterns") != PATTERNS or manifest.get("minimum_tests") != MINIMUM_TESTS
                    or manifest.get("qualification") is not False or manifest.get("promotion_authority") is not False
                    or manifest.get("raw_private_context_included") is not False
                    or set(names) != set(manifest["files"]) | {"manifest.json"}):
                raise ValueError("fixed source/test/authority manifest required")
            for info in infos:
                name = info.filename
                path = PurePosixPath(name)
                kind = stat.S_IFMT(info.external_attr >> 16)
                if (path.is_absolute() or ".." in path.parts or "\\" in name or info.is_dir()
                        or kind not in (0, stat.S_IFREG) or info.flag_bits & 1 or info.file_size > 600000):
                    raise ValueError("unsafe archive member")
                if name == "manifest.json":
                    continue
                if not (name == FIXTURE_PATH or (name.endswith(".py") and (name.startswith("python/merlin/") or name.startswith("python/dot_ai_os/") or name.startswith("tests/")))):
                    raise ValueError("only reviewed Python code/tests and the one frozen synthetic fixture are allowed")
                content = archive.read(info)
                if hashlib.sha256(content).hexdigest() != manifest["files"][name]:
                    raise ValueError("learning source identity mismatch")
                target = root / name
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                with target.open("xb") as stream:
                    stream.write(content)
                target.chmod(0o600)
        report["source_files"] = manifest["files"]
        env = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C.UTF-8",
            "PYTHONPATH": str(root / "python") + os.pathsep + str(root),
            "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"}
        tests = subprocess.run(["/usr/bin/python3", "-s", "-c", TEST_CODE, json.dumps(PATTERNS), str(MINIMUM_TESTS)],
            cwd=str(root), env=env, capture_output=True, text=True, timeout=180)
        (output / "learning-tests.txt").write_text(tests.stdout + tests.stderr)
        lines = [line for line in tests.stdout.splitlines() if line.startswith("MERLIN_LEARNING_TESTS=")]
        report["tests"] = json.loads(lines[-1].split("=", 1)[1]) if lines else {"passed": False}
        if tests.returncode or not report["tests"].get("passed"):
            report["status"] = "validation_failed"
            save(); print(tests.stderr[-18000:]); return report
        demo = subprocess.run(["/usr/bin/python3", "-s", "-c", DEMO_CODE, str(output / "synthetic-state"), SOURCE_COMMIT],
            cwd=str(root), env=env, capture_output=True, text=True, timeout=45)
        (output / "learning-demo-log.txt").write_text(demo.stdout + demo.stderr)
        if demo.returncode:
            raise RuntimeError("fixed synthetic integration failed: " + demo.stderr[-4000:])
        report["demo"] = json.loads(demo.stdout)
        report["status"] = "succeeded"
    except Exception as exc:
        report["status"] = "validation_failed"
        report["error"] = {"class": type(exc).__name__, "message": str(exc)[-4000:]}
    save()
    print(json.dumps({k: v for k, v in report.items() if k != "source_files"}, indent=2, sort_keys=True))
    return report
