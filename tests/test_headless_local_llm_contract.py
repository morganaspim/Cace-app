#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "headless_local_llm.json"
LAUNCHER = ROOT / "scripts" / "run_cace_headless_local.sh"
PROVISION = ROOT / "config" / "model_provision_policy.json"


def main() -> int:
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["trust_role"] == "untrusted-informal-reasoner"
    assert payload["llm_endpoint"] == "http://127.0.0.1:8080/v1"
    assert payload["cace_api_endpoint"] == "http://127.0.0.1:8765"
    assert payload["model"]["repo_id"] == "Qwen/Qwen3.5-4B"
    assert payload["model"]["revision"] == "a7b0d22b993d71000cf2eadfb37222a67cee521e"
    assert payload["llama_cpp"]["commit"] == "b29c606e28a01b1bc8c1351026a0fa6e616bf6c4"

    provision = json.loads(PROVISION.read_text(encoding="utf-8"))
    assert provision["schema_version"] == 1
    assert provision["source"]["repository"] == "Qwen/Qwen3.5-4B"
    assert provision["source"]["revision"] == "a7b0d22b993d71000cf2eadfb37222a67cee521e"
    assert provision["source"]["license"] == "Apache-2.0"
    assert provision["converter"]["commit"] == "b29c606e28a01b1bc8c1351026a0fa6e616bf6c4"
    assert provision["converter"]["target_quantization"] == "Q4_K_M"
    assert provision["artifact_policy"]["third_party_quantization_default_allowed"] is False
    assert provision["phases"]["runtime"]["network_allowed"] is False

    safety = payload["safety"]
    assert safety["public_bind_forbidden"] is True
    assert safety["download_at_runtime_forbidden"] is True
    assert safety["external_model_api_forbidden"] is True
    assert safety["llama_cpp_agent_mode_enabled"] is False
    assert safety["llm_may_mark_verified"] is False
    assert safety["llm_may_promote_claims"] is False
    assert safety["llm_may_modify_proof_ledger"] is False
    assert safety["llm_may_expand_authority"] is False

    script = LAUNCHER.read_text(encoding="utf-8")
    assert "--host 127.0.0.1" in script
    assert "--port 8080" in script
    assert "--port 8765" in script
    assert "--alias Qwen/Qwen3.5-4B" in script
    assert "CACE_MODEL_GGUF is required" in script
    assert "sha256sum" in script

    forbidden = (
        "0.0.0.0",
        "--agent",
        "huggingface-cli",
        "hf_hub_download",
        "wget ",
        "curl ",
        "git clone",
    )
    for marker in forbidden:
        assert marker not in script, f"forbidden headless runtime marker: {marker}"

    print("CACE headless local LLM contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
