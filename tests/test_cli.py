import json
import subprocess
import sys

from cace_studio.cli import main


def test_registry_is_headless_and_machine_readable():
    proc = subprocess.run([sys.executable, "-m", "cace_studio.cli", "registry"], text=True, capture_output=True)
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["cli_schema"] == 1
    assert payload["metadata_is_verification_evidence"] is False
    assert any(m["metadata"]["module_id"] == "science.grid1d" for m in payload["modules"])


def test_modules_list_is_registry_compatible(capsys):
    assert main(["modules", "list"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "modules-list"
    assert payload["metadata_is_verification_evidence"] is False
    assert any(m["metadata"]["module_id"] == "science.grid1d" for m in payload["modules"])


def test_claims_list_is_read_only_truth_metadata(capsys):
    assert main(["claims", "list"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "claims-list"
    assert payload["proof_effect"] == "none"
    assert payload["metadata_is_verification_evidence"] is False
    assert payload["claims"]
    assert all("qualification_state" in claim for claim in payload["claims"])


def test_proofs_status_is_fail_closed_and_does_not_promote(capsys):
    assert main(["proofs", "status"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "proofs-status"
    assert payload["proof_effect"] == "none"
    assert payload["qualification_is_derived_fail_closed"] is True
    assert isinstance(payload["all_current_head_qualified"], bool)
    assert set(payload["state_counts"]).issubset({"QUALIFIED", "UNQUALIFIED", "CONFLICT"})


def test_claim_show_rejects_unknown_claim(capsys):
    assert main(["claims", "show", "cace.does.not.exist"]) == 2
    payload = json.loads(capsys.readouterr().err)
    assert payload["error_type"] == "KeyError"


def test_verified_example(tmp_path):
    output = tmp_path / "report.json"
    assert main(["run", "examples/verified_quadratic.cace", "--seed", "7", "--output", str(output)]) == 0
    payload = json.loads(output.read_text())
    assert payload["all_verifiers_passed"] is True
    assert payload["seed"] == 7


def test_missing_experiment_fails_with_json(capsys):
    assert main(["run", "nonexistent.cace"]) == 2
    assert json.loads(capsys.readouterr().err)["error_type"] == "FileNotFoundError"


def test_empty_experiment_is_unverified(tmp_path, capsys):
    path = tmp_path / "empty.cace"
    path.write_text(json.dumps({"schema_version": 1, "name": "empty", "nodes": [], "edges": []}))
    assert main(["run", str(path)]) == 3
    assert json.loads(capsys.readouterr().out)["all_verifiers_passed"] is False


def test_missing_required_input_returns_error(tmp_path, capsys):
    path = tmp_path / "failure.cace"
    path.write_text(json.dumps({"schema_version": 1, "name": "failure", "nodes": [
        {"id": "v", "module_id": "verify.constant_residual", "params": {"target": 2.0}}
    ], "edges": []}))
    assert main(["run", str(path)]) == 2
    assert "error" in json.loads(capsys.readouterr().err)
