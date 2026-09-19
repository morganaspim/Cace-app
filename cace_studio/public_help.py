from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping

from cace_studio.app import build_registry
from cace_studio.core.types import port_connection_error


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "CACE_PUBLIC_HELP_POLICY.json"
HELP_ROOT = ROOT / "docs" / "help"


class PublicHelpError(ValueError):
    pass


def _load_json(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise PublicHelpError(f"{path.name} must contain a JSON object")
    return raw


def _slug(text: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", str(text).casefold()).strip("-")
    return value[:80] or "module"


def _public_key(name: str, category: str, index: int) -> str:
    stem = f"{_slug(category)}--{_slug(name)}"
    digest = sha256(f"{category}\0{name}\0{index}".encode("utf-8")).hexdigest()[:8]
    return f"{stem}--{digest}"


def _port(port) -> dict[str, Any]:
    return {
        "name": str(port.name),
        "type": str(port.type_name),
        "required": bool(port.required),
        "unit": port.unit,
    }


def _parameter(param) -> dict[str, Any]:
    return {
        "name": str(param.name),
        "type": str(param.type_name),
        "unit": param.unit,
    }


def _visible_contract(cls, index: int) -> dict[str, Any]:
    metadata = cls.metadata
    inputs = [_port(port) for port in cls.inputs]
    outputs = [_port(port) for port in cls.outputs]
    params = [_parameter(param) for param in cls.parameters]
    evidence = sorted(item.value for item in cls.proof_status.evidence)
    required = [item for item in inputs if item["required"]]
    return {
        "public_key": _public_key(metadata.name, metadata.category, index),
        "name": str(metadata.name),
        "category": str(metadata.category),
        "maturity": str(metadata.maturity.value),
        "inputs": inputs,
        "outputs": outputs,
        "parameters": params,
        "declared_evidence_categories": evidence,
        "what_it_looks_for": {
            "required_inputs": [
                {
                    "name": item["name"],
                    "type": item["type"],
                    "unit": item["unit"],
                }
                for item in required
            ],
            "visible_parameters": [item["name"] for item in params],
        },
        "rigor": (
            "CACE validates the public input/output/parameter contract before execution. "
            "Execution and verification remain separate. Evidence labels identify the kind "
            "of executed check; missing, stale, failed, or not-run verification is never "
            "treated as success. Formal status uses a separate canonical qualification path."
        ),
    }


def _feature_entries() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in sorted(HELP_ROOT.glob("*_HELP.json")):
        raw = _load_json(path)
        schema = raw.get("schema")
        if schema not in {
            "cace.public-feature-help.v1",
            "cace.public-feature-help-fragment.v1",
        }:
            raise PublicHelpError(f"unsupported help schema in {path.name}")
        entries = raw.get("features")
        if not isinstance(entries, list):
            raise PublicHelpError(f"{path.name} features must be a list")
        for entry in entries:
            if not isinstance(entry, dict):
                raise PublicHelpError(f"{path.name} contains a non-object feature")
            feature_id = str(entry.get("id", "")).strip()
            if not feature_id or feature_id in seen:
                raise PublicHelpError(f"duplicate/blank feature id: {feature_id!r}")
            seen.add(feature_id)
            result.append(entry)
    return result


def _display_ports(items: list[dict[str, Any]]) -> str:
    if not items:
        return "no required upstream input"
    parts: list[str] = []
    for item in items[:4]:
        unit = f" [{item['unit']}]" if item.get("unit") else ""
        parts.append(f"{item['name']} ({item['type']}{unit})")
    if len(items) > 4:
        parts.append(f"+{len(items)-4} more")
    return ", ".join(parts)


def _module_examples(module: dict[str, Any]) -> list[str]:
    inputs = [item for item in module["inputs"] if item["required"]]
    outputs = module["outputs"]
    params = module["parameters"]
    first = (
        f"Baseline experiment: add {module['name']} to the canvas, provide "
        f"{_display_ports(inputs)}, run it, then inspect the visible outputs and the "
        "verification/evidence panel."
    )
    if params:
        second = (
            f"Controlled comparison: duplicate {module['name']}, keep the same inputs, "
            f"change only the visible parameter '{params[0]['name']}', run both versions, "
            "and compare outputs plus evidence states."
        )
    elif inputs:
        second = (
            f"Input comparison: place two {module['name']} instances, give them two "
            f"different valid '{inputs[0]['name']}' inputs while keeping the rest of the "
            "public contract the same, then compare outputs and verification states."
        )
    else:
        second = (
            f"Repeatability check: run two independent {module['name']} instances under "
            "the same visible settings and compare public outputs/evidence."
        )
    return [first, second]


def _connection_candidates(classes: list[type]) -> dict[int, list[tuple[int, str]]]:
    result: dict[int, list[tuple[int, str]]] = {i: [] for i in range(len(classes))}
    for src_i, src in enumerate(classes):
        for dst_i, dst in enumerate(classes):
            if src_i == dst_i:
                continue
            for out_port in src.outputs:
                for in_port in dst.inputs:
                    if port_connection_error(out_port, in_port) is None:
                        unit = f" [{out_port.unit}]" if out_port.unit else ""
                        sentence = (
                            f"{src.metadata.name} -> {dst.metadata.name}: connect "
                            f"'{out_port.name}' ({out_port.type_name}{unit}) to "
                            f"'{in_port.name}'. The edge is public type/unit compatible; "
                            "still check scientific appropriateness and verification state."
                        )
                        result[src_i].append((dst_i, sentence))
                        result[dst_i].append((src_i, sentence))
    return result


def _connection_examples(
    module: dict[str, Any],
    candidates: list[tuple[int, str]],
) -> list[str]:
    picked: list[str] = []
    peers: set[int] = set()
    for peer, sentence in candidates:
        if peer in peers:
            continue
        peers.add(peer)
        picked.append(sentence)
        if len(picked) == 2:
            break
    while len(picked) < 2:
        if not picked:
            picked.append(
                f"Parallel comparison: use two {module['name']} nodes with independent "
                "valid inputs/settings, then compare their public outputs and evidence."
            )
        else:
            picked.append(
                f"Cross-check workflow: combine {module['name']} with a separate compatible "
                "verification/reporting step when one is available, or compare two independent "
                "runs. Compatibility is based only on visible type/unit contracts."
            )
    return picked[:2]


def build_public_help_catalog() -> dict[str, Any]:
    policy = _load_json(POLICY_PATH)
    if policy.get("schema") != "cace.public-help-policy.v1":
        raise PublicHelpError("unsupported public-help policy schema")

    registry = build_registry()
    classes = sorted(
        registry.classes(),
        key=lambda cls: (
            str(cls.metadata.category),
            str(cls.metadata.name),
            str(cls.metadata.module_id),
        ),
    )
    modules = [_visible_contract(cls, i) for i, cls in enumerate(classes)]
    candidates = _connection_candidates(classes)
    for index, module in enumerate(modules):
        module["examples"] = _module_examples(module)
        module["connection_examples"] = _connection_examples(module, candidates[index])

    features = _feature_entries()
    return {
        "schema": "cace.public-help-catalog.v1",
        "role": "customer-facing help only; no proprietary implementation or proof internals",
        "module_count": len(modules),
        "feature_count": len(features),
        "public_rigor": list(policy.get("public_rigor_topics", [])),
        "connection_rule": str(policy.get("connection_rule", "")),
        "features": features,
        "modules": modules,
    }


def render_markdown(catalog: Mapping[str, Any]) -> str:
    lines: list[str] = []
    add = lines.append
    add("# CACE Customer Help: Features, Modules, Examples, and Rigorous Connections")
    add("")
    add("> Customer-facing documentation only. It intentionally excludes proprietary")
    add("> algorithms, custom internal mathematics, theorem bodies, source architecture,")
    add("> credentials, and implementation details.")
    add("")
    add("## What makes CACE rigorous")
    add("")
    for item in catalog["public_rigor"]:
        add(f"- {item}.")
    add("")
    add(
        "A canvas connection means the public data contract is type/unit compatible. "
        "It does not by itself prove scientific appropriateness."
    )
    add("")
    add(
        f"Generated coverage: {catalog['feature_count']} features and "
        f"{catalog['module_count']} registered modules."
    )
    add("")
    add("## Feature help")
    add("")
    for feature in catalog["features"]:
        add(f"### {feature['title']}")
        add("")
        add(f"Availability: {feature['status']}")
        add("")
        add(str(feature["what_you_see"]))
        add("")
        add("What it looks for:")
        for value in feature["what_it_looks_for"]:
            add(f"- {value}")
        add("")
        add(f"Rigor: {feature['rigor']}")
        add("")
        add("Examples:")
        for number, example in enumerate(feature["examples"], 1):
            add(f"{number}. {example}")
        add("")
    add("## Module help")
    add("")
    for module in catalog["modules"]:
        add(f"### {module['name']}")
        add("")
        add(f"Category: {module['category']}")
        add(f"Maturity: {module['maturity']}")
        evidence = ", ".join(module["declared_evidence_categories"]) or "none declared"
        add(f"Declared evidence categories: {evidence}")
        add("")
        add("What it looks for:")
        required = module["what_it_looks_for"]["required_inputs"]
        if required:
            for item in required:
                unit = f" [{item['unit']}]" if item.get("unit") else ""
                add(f"- Required input: {item['name']} - {item['type']}{unit}")
        else:
            add("- No required upstream input is declared.")
        if module["parameters"]:
            for item in module["parameters"]:
                unit = f" [{item['unit']}]" if item.get("unit") else ""
                add(f"- Parameter: {item['name']} - {item['type']}{unit}")
        else:
            add("- No user-visible parameters are declared.")
        add("")
        add("Outputs:")
        if module["outputs"]:
            for item in module["outputs"]:
                unit = f" [{item['unit']}]" if item.get("unit") else ""
                add(f"- {item['name']} - {item['type']}{unit}")
        else:
            add("- No data output port is declared; inspect the visible run/status result.")
        add("")
        add(f"Rigor: {module['rigor']}")
        add("")
        add("Two example experiments:")
        for number, example in enumerate(module["examples"], 1):
            add(f"{number}. {example}")
        add("")
        add("Two combined-module examples:")
        for number, example in enumerate(module["connection_examples"], 1):
            add(f"{number}. {example}")
        add("")
    return "\n".join(lines).rstrip() + "\n"


def validate_public_help(catalog: Mapping[str, Any], rendered: str | None = None) -> None:
    policy = _load_json(POLICY_PATH)
    minimums = policy.get("example_minimums", {})
    feature_min = int(minimums.get("feature_examples", 2))
    module_min = int(minimums.get("module_examples", 2))
    connection_min = int(minimums.get("module_connection_examples", 2))

    features = catalog.get("features")
    modules = catalog.get("modules")
    if not isinstance(features, list) or not features:
        raise PublicHelpError("public help requires feature entries")
    if not isinstance(modules, list) or not modules:
        raise PublicHelpError("public help requires module entries")
    for feature in features:
        if len(feature.get("examples", [])) < feature_min:
            raise PublicHelpError(f"feature {feature.get('id')} has too few examples")

    public_keys: set[str] = set()
    for module in modules:
        if len(module.get("examples", [])) < module_min:
            raise PublicHelpError(f"module {module.get('name')} has too few examples")
        if len(module.get("connection_examples", [])) < connection_min:
            raise PublicHelpError(
                f"module {module.get('name')} has too few combined-module examples"
            )
        key = str(module.get("public_key", ""))
        if not key or key in public_keys:
            raise PublicHelpError("module public keys must be unique")
        public_keys.add(key)
        forbidden_keys = {
            "module_id",
            "source_path",
            "class_name",
            "theorem",
            "implementation",
            "default",
            "description",
            "assumptions",
        }
        if forbidden_keys.intersection(module):
            raise PublicHelpError(f"module {module.get('name')} exposes an internal field")

    text = rendered if rendered is not None else json.dumps(catalog, sort_keys=True, default=str)
    lowered = text.casefold()
    for marker in policy.get("redaction_markers", []):
        if str(marker).casefold() in lowered:
            raise PublicHelpError(f"public help contains forbidden marker: {marker}")


def write_public_help(markdown_path: str | Path, json_path: str | Path) -> tuple[Path, Path]:
    catalog = build_public_help_catalog()
    rendered = render_markdown(catalog)
    validate_public_help(catalog, rendered)
    markdown_target = Path(markdown_path)
    json_target = Path(json_path)
    markdown_target.parent.mkdir(parents=True, exist_ok=True)
    json_target.parent.mkdir(parents=True, exist_ok=True)
    markdown_target.write_text(rendered, encoding="utf-8")
    json_target.write_text(
        json.dumps(catalog, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    return markdown_target, json_target
