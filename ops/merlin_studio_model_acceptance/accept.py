"""Fixed two-request real-model Studio acceptance, bracketed by provider identity.

This file is a local draft until root reviews and publishes its exact workflow.
No installation, service mutation, paid service, download or automatic retry.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import sys
import uuid

PRODUCT_COMMIT = "8497597f297bba83189afef2026c27f9244537ce"
OPS_REPOSITORY = "morganaspim/Cace-app"
OPS_REF = "refs/heads/merlin/browser-operations-20261121"
OPERATION = "accept-studio-model-8497597"
MODEL_ID = "merlin-qwen-coder-1.5b-q4"
MANIFEST_SHA256 = "35cf7ea56185126587e7dc10bb400ec53df51057407f9920d0ab03aff4299203"
BOOTSTRAP_RECEIPT_SHA256 = "7b7489297414d8304f12e8c0e28aec8ddd806704889f8b17986eac8ada0cba57"
MODEL_SHA256 = "cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046"
BINARY_SHA256 = "af4c10f1f4a1e7f0878dc9b3896bb742f65170861276ef04ddecdf2a9be3cd82"
UNIT_SHA256 = "77629b0ef1afc4bcca4fa11282e6ca0bb7f0164110982fe85ae8ca6c267cad99"
ARGV_SHA256 = "53409829c524241d6baaad015cb2c60d874014c4e17ae13cb57f54b4c4466952"

# Populated from the explicit local assets by freeze_route.py before review.
ASSET_PINS = {'expected-studio-source.json': {'bytes': 1683, 'sha256': '321550afea765a8e5ab85bd54462c4b0621d61c1a08a04eee12d6574341d3816', 'git_blob': '95bd02518caa9a4c2422fae7e1611034cf02f73c'}, 'frozen_provider_inspector.py': {'bytes': 57177, 'sha256': 'f47637659c5d71e5d75cdb7198a0e07092a69f1b7857d45c92fa19be40bd8fa5', 'git_blob': '67c699c2f27c1acfdc202eeed5b0468cb12ae029'}, 'initial-model-request.json': {'bytes': 2394, 'sha256': '07545d5ef91771730f35054d290e721dadfd0efe401b1948e15ea8a4f816a4de', 'git_blob': '0ee7e0e99447b2126b2a7141d317150ae5e1427d'}, 'inspect_provider_readonly.py': {'bytes': 6115, 'sha256': 'd950903a2f72d8c528f87baa5f772b2e1e028c4ef8819d865ee8028539e448e7', 'git_blob': '341561b8c9fff42e566c9657f42f6f67e75ba03b'}, 'product-source.zip': {'bytes': 104129, 'sha256': '99964ba99ea41a3b3580b85574533e5aaa8a2e72cca111b1b2233c948bb1cf8b', 'git_blob': '09d10789ab63c776cf47b8226cd0507e8cce1e49'}, 'run_studio_acceptance.py': {'bytes': 27038, 'sha256': '80d30cdfd9ff99531fe65e71a136cbdb3352ed4455e750ab634d7540e6543add', 'git_blob': 'c15feff08ad833277a90be2ddfb9c4881eb74885'}, 'source-pins.json': {'bytes': 8350, 'sha256': '4f0a420a6067c6e8ce51dd3110539e5a47b8a372fb216c540c39ba7ff41e8429', 'git_blob': 'bba11aced1eeb2d31c264f749408653fa618c879'}, 'validation_support.py': {'bytes': 37082, 'sha256': '39d82d37caa78a7f4a01cddb90821f1c4727f75472ca903b7054d840049447ee', 'git_blob': 'd950f862e4025db559c4c1a99cdba4aec9bae6c7'}}  # FROZEN_ASSET_PINS

ROOT_LOADER = r'''
import hashlib,os,stat,sys
path=sys.argv[1]
fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
try:
    st=os.fstat(fd)
    if not stat.S_ISREG(st.st_mode) or st.st_size>65536:raise RuntimeError('fixed root wrapper file required')
    raw=os.read(fd,65537)
finally:os.close(fd)
if hashlib.sha256(raw).hexdigest()!='ROOT_WRAPPER_SHA256':raise RuntimeError('root wrapper identity differs')
sys.argv=[path,sys.argv[2]]
exec(compile(raw,'verified_readonly_provider_wrapper','exec'),{'__name__':'__main__'})
'''


class AcceptanceError(RuntimeError):
    pass


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as output:
        json.dump(value, output, sort_keys=True, indent=2, allow_nan=False)
        output.write("\n")


def validate_request(request, execution):
    if (not isinstance(request, dict) or set(request) != {"schema", "request_id", "operation", "created_at"}
        or request.get("schema") != "merlin-studio-model-acceptance-request/1" or request.get("operation") != OPERATION):
        raise AcceptanceError("only the fixed model acceptance request is allowed")
    try:
        parsed = uuid.UUID(request["request_id"])
        when = datetime.strptime(request["created_at"], "%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise AcceptanceError("canonical request UUID and UTC timestamp required") from exc
    if str(parsed) != request["request_id"] or parsed.version != 4 or when.strftime("%Y-%m-%dT%H:%M:%SZ") != request["created_at"]:
        raise AcceptanceError("canonical UUID4 and UTC timestamp required")
    if (execution.get("repository") != OPS_REPOSITORY or execution.get("ref") != OPS_REF
        or execution.get("runner") != "cace-oci-a1" or execution.get("uid") != 1000
        or execution.get("system") != "Linux" or execution.get("machine") != "aarch64"
        or type(execution.get("run_id")) is not int or execution["run_id"] <= 0
        or type(execution.get("run_attempt")) is not int or execution["run_attempt"] != 1
        or not isinstance(execution.get("workflow_commit"), str)
        or not re.fullmatch("[0-9a-f]{40}", execution["workflow_commit"])):
        raise AcceptanceError("fixed first-attempt unprivileged OCI execution identity required")


def load_assets(directory):
    directory = Path(directory)
    if not ASSET_PINS:
        raise AcceptanceError("route assets have not been frozen")
    values = {}
    for name, pin in ASSET_PINS.items():
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise AcceptanceError("fixed regular route asset required")
        raw = path.read_bytes()
        if len(raw) != pin["bytes"] or hashlib.sha256(raw).hexdigest() != pin["sha256"]:
            raise AcceptanceError("route asset differs: " + name)
        values[name] = raw
    support = {"__name__": "fixed_studio_validation_support"}
    exec(compile(values["validation_support.py"], "validation_support", "exec"), support)
    return support, values


def validate_root_receipt(value):
    if (not isinstance(value, dict) or value.get("schema") != "merlin-studio-root-provider-inspection/1"
        or value.get("passed") is not True or value.get("source_entry_point") != "inspect_ready"
        or value.get("inspector_sha256") != ASSET_PINS["frozen_provider_inspector.py"]["sha256"]
        or value.get("model_generation_calls") != 0 or value.get("file_writes") != 0
        or value.get("service_mutations") is not False):
        raise AcceptanceError("complete root read-only provider proof required")
    proof = value.get("inspection", {})
    service = proof.get("service", {})
    if (proof.get("schema") != "merlin-local-model-inspect/1" or proof.get("status") != "ready"
        or proof.get("manifest_sha256") != MANIFEST_SHA256
        or proof.get("bootstrap_receipt_sha256") != BOOTSTRAP_RECEIPT_SHA256
        or proof.get("inference_requests") != 0 or proof.get("qualification") is not False
        or service.get("unit") != "merlin-model-provider.service"
        or service.get("unit_sha256") != UNIT_SHA256 or service.get("argv_sha256") != ARGV_SHA256
        or service.get("mapped_model_sha256") != MODEL_SHA256
        or service.get("active_state") != "active" or service.get("sub_state") != "running"
        or service.get("user") != "merlin-model" or service.get("group") != "merlin-model"
        or service.get("uid") != 981 or service.get("gid") != 981
        or type(service.get("main_pid")) is not int or service["main_pid"] <= 1
        or not re.fullmatch("[0-9]+", str(service.get("process_start_ticks", "")))
        or not re.fullmatch(r"net:\[[0-9]+\]", service.get("network_namespace", ""))
        or service.get("private_network") is not False
        or service.get("restrict_address_families") != ["AF_INET", "AF_UNIX"]
        or service.get("actual_cgroup") != {"cpu.max": "150000 100000", "memory.max": "3221225472",
                                          "memory.swap.max": "0", "pids.max": "32"}):
        raise AcceptanceError("provider live process/limits/authority identity differs")
    return proof


def inspect_provider(v, controls, out, env):
    """Only root-readable fixed inspect_ready; no root file writes or network."""
    out.mkdir(mode=0o700, exist_ok=False)
    sudo, _ = v["trusted_executable"]("/usr/bin/sudo")
    root_python, _ = v["trusted_executable"]("/usr/bin/python3")
    wrapper = controls / "inspect_provider_readonly.py"
    frozen = controls / "frozen_provider_inspector.py"
    loader = ROOT_LOADER.replace("ROOT_WRAPPER_SHA256", ASSET_PINS["inspect_provider_readonly.py"]["sha256"])
    process = v["run_process"]([str(sudo), "-n", str(root_python), "-I", "-B", "-c", loader,
                                str(wrapper), str(frozen)], cwd="/", env=env,
                               log=out / "root-inspection.json", seconds=100, maximum=128 * 1024)
    write_json(out / "execution.json", process)
    if not process["passed"]:
        raise AcceptanceError("fixed root read-only inspection unavailable or failed")
    value = v["parse_json"](v["read_small"](out / "root-inspection.json", 128 * 1024))
    validate_root_receipt(value)
    return value


def inspect_transport(v, token_request):
    health = v["local_json"]("GET", "/health")
    models = v["local_json"]("GET", "/v1/models")
    if (not isinstance(health, dict) or health.get("status") != "ok"
        or not isinstance(models, dict) or not isinstance(models.get("data"), list)
        or [item.get("id") for item in models["data"] if isinstance(item, dict)] != [MODEL_ID]):
        raise AcceptanceError("existing loopback provider is not ready with its exact alias")
    tokens = v["local_json"]("POST", "/v1/chat/completions/input_tokens", token_request)
    count = tokens.get("input_tokens") if isinstance(tokens, dict) else None
    if (type(count) is not int or count <= 0 or tokens.get("object") != "response.input_tokens"
        or count + 2048 + 128 > 4096):
        raise AcceptanceError("fixed initial request fails context preflight")
    return {"passed": True, "health": health, "model_ids": [MODEL_ID], "input_tokens": count,
            "context_tokens": 4096, "max_tokens": 2048, "margin": 128,
            "tokenization_calls": 1, "generation_calls": 0,
            "request_sha256": hashlib.sha256(token_request).hexdigest()}


def matching_after(before, after):
    first = validate_root_receipt(before)
    second = validate_root_receipt(after)
    return (first["service"] == second["service"] and first["manifest_sha256"] == second["manifest_sha256"]
            and first["bootstrap_receipt_sha256"] == second["bootstrap_receipt_sha256"])


def run(request, execution, controls, out):
    validate_request(request, execution)
    controls, out = Path(controls), Path(out)
    v, assets = load_assets(controls)
    source_pins = v["parse_json"](assets["source-pins.json"])
    members = v["validate_bundle"](source_pins, assets["product-source.zip"])
    source = out / "exact-product-source"
    v["extract_bundle"](members, source)
    temporary = out / "temporary"
    temporary.mkdir(mode=0o700)
    env = v["child_env"](temporary)
    python_inventory = v["inspect_python"](out, env)
    write_json(out / "python-inventory.json", python_inventory)
    receipt = {"schema": "merlin-studio-fixed-model-acceptance/1", "request": request,
               "execution": execution, "source_commit": PRODUCT_COMMIT, "started_at": now(),
               "status": "blocked", "passed": False, "generation_requests_attempted": 0,
               "real_model_inference_observed": False, "automatic_retry": False,
               "maximum_generation_requests": 2, "maximum_requested_output_tokens": 4096,
               "studio_deadline_seconds": 45, "studio_work_deadline_seconds": 180,
               "paid_model_calls": 0, "research_source_acquisitions": 0,
               "software_installation": False, "service_mutations": False,
               "promotion_authority": False, "qualification": False,
               "isolation_scope": "ordinary UID1000 Studio process; root only reads fixed provider identity"}
    before = None
    after = None
    try:
        if not python_inventory["passed"]:
            raise AcceptanceError("existing supported Python is unavailable; no root probe or generation attempted")
        before = inspect_provider(v, controls, out / "provider-before", env)
        transport = inspect_transport(v, assets["initial-model-request.json"])
        write_json(out / "provider-transport.json", transport)
        # The frozen root inspector validates exactly the accepted authority
        # record, live executable/argv, mapped model, UID and cgroup limits.
        preflight = {"schema": "merlin-studio-model-preflight/1", "passed": True,
                     "observed_at": now(), "studio_revision": PRODUCT_COMMIT,
                     "provider_identity": {"model_sha256": MODEL_SHA256, "binary_sha256": BINARY_SHA256,
                                           "service_unit_sha256": UNIT_SHA256, "active_state": "active",
                                           "sub_state": "running", "model_id": MODEL_ID},
                     "python": {key: python_inventory["selected"][key] for key in ("version", "executable")},
                     "initial_context": transport, "root_process_proof_sha256": hashlib.sha256(
                         (out / "provider-before/root-inspection.json").read_bytes()).hexdigest()}
        preflight_path = out / "studio-model-preflight.json"
        write_json(preflight_path, preflight)
        interpreter = python_inventory["selected"]["executable"]
        harness_out = out / "model-loop"
        argv = [interpreter, "-I", "-B", str(controls / "run_studio_acceptance.py"), "--mode", "run",
                "--app-dir", str(source / "portable/merlin_studio"), "--evidence-dir", str(harness_out),
                "--expected-source", str(controls / "expected-studio-source.json"), "--preflight", str(preflight_path)]
        receipt["status"] = "attempted"
        receipt["generation_requests_attempted"] = None
        receipt["generation_accounting"] = "pending_harness_receipt"
        process = v["run_process"](argv, cwd="/", env=env, log=out / "model-harness.txt",
                                    seconds=220, maximum=2 * 1024 * 1024)
        receipt["harness_process"] = process
        result = v["parse_json"](v["read_small"](harness_out / "acceptance-result.json", 128 * 1024))
        attempted = result.get("generation_requests_attempted", result.get("generation_requests"))
        if type(attempted) is not int or not 0 <= attempted <= 2:
            raise AcceptanceError("harness generation request budget receipt is invalid")
        receipt["generation_requests_attempted"] = attempted
        receipt["generation_accounting"] = "complete_harness_receipt"
        receipt["real_model_inference_observed"] = result.get("real_model_inference_observed") is True
        receipt["model_loop"] = result
        receipt["passed"] = bool(process["passed"] and result.get("passed") is True and attempted == 2
                                  and result.get("real_model_inference_observed") is True)
        receipt["status"] = "passed" if receipt["passed"] else "failed"
    except Exception as exc:
        receipt["error_type"] = type(exc).__name__
        receipt["error"] = str(exc)[:1500]
        if receipt["status"] == "attempted":
            receipt["status"] = "failed"
        receipt["passed"] = False
    finally:
        if before is not None:
            try:
                after = inspect_provider(v, controls, out / "provider-after", env)
                receipt["provider_identity_unchanged"] = matching_after(before, after)
                if not receipt["provider_identity_unchanged"]:
                    raise AcceptanceError("provider process or pinned identity changed during acceptance")
            except Exception as exc:
                receipt["after_inspection_error"] = type(exc).__name__ + ": " + str(exc)[:1000]
                receipt["provider_identity_unchanged"] = False
                receipt["passed"] = False
                receipt["status"] = "failed"
        try:
            for name, pin in source_pins["files"].items():
                if v["identity"](v["read_small"](source / name, 256 * 1024)) != pin:
                    raise AcceptanceError("source member changed: " + name)
            receipt["source_unchanged"] = True
        except Exception as exc:
            receipt["source_unchanged"] = False
            receipt["source_error"] = type(exc).__name__ + ": " + str(exc)[:1000]
            receipt["passed"] = False
            receipt["status"] = "failed"
        receipt["finished_at"] = now()
        write_json(out / "acceptance-receipt.json", receipt)
    return receipt
