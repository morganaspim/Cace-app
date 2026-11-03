from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any, Mapping

from .graph import Experiment
from .registry import ModuleRegistry
from .reproducibility import registry_contract_fingerprint, sha256_identity
from .types import port_connection_error


_DEFAULT_POLICY = Path(__file__).resolve().parents[2] / "ops" / "qualified_capabilities.json"


class CapabilityRegistryError(ValueError):
    pass


class QualifiedCapabilityRegistry:
    """Fail-closed production exposure registry over the engineering module registry.

    The ordinary ModuleRegistry answers "what code is registered?".  This registry
    answers the narrower product question "what is explicitly allowed to be shown,
    linked, executed through the browser, or offered to the local AI?".

    Capability qualification is engineering/product evidence only.  It cannot
    create mathematical proof status or promote a canonical formal claim.
    """

    _SURFACE_FLAG = {
        "ui": "ui_visible",
        "link": "link_enabled",
        "ai": "ai_callable",
        "api": "api_runnable",
    }

    def __init__(
        self,
        registry: ModuleRegistry,
        *,
        policy_path: Path | str = _DEFAULT_POLICY,
    ) -> None:
        self.registry = registry
        self.policy_path = Path(policy_path)
        try:
            raw = json.loads(self.policy_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise CapabilityRegistryError(
                f"cannot load capability policy {self.policy_path}: {exc}"
            ) from exc
        if not isinstance(raw, dict):
            raise CapabilityRegistryError("capability policy must be an object")
        if raw.get("schema") != "cace-qualified-capability-registry-v1":
            raise CapabilityRegistryError("unsupported capability policy schema")
        if raw.get("default") != "HIDDEN_DENY":
            raise CapabilityRegistryError("capability policy must fail closed by default")

        self._raw = raw
        self._policy_sha256 = sha256_identity(raw)
        self._classes = {cls.metadata.module_id: cls for cls in registry.classes()}
        self._records: dict[str, dict[str, Any]] = {}
        self._tested_connections: dict[tuple[str, str, str, str], str] = {}
        self._validate_and_index()
        self._validate_tested_connections()

    @property
    def policy_sha256(self) -> str:
        return self._policy_sha256

    @property
    def full_registry_contract_sha256(self) -> str:
        return registry_contract_fingerprint(self.registry)

    def _validate_and_index(self) -> None:
        required_ui = tuple(self._raw.get("required_gates_for_ui", ()))
        required_link = tuple(self._raw.get("required_gates_for_link", ()))
        required_ai = tuple(self._raw.get("required_gates_for_ai", ()))
        modules = self._raw.get("modules")
        if not isinstance(modules, list):
            raise CapabilityRegistryError("capability policy modules must be an array")

        seen: set[str] = set()
        for index, item in enumerate(modules):
            if not isinstance(item, dict):
                raise CapabilityRegistryError(f"modules[{index}] must be an object")
            module_id = item.get("module_id")
            version = item.get("version")
            gates = item.get("gates")
            workflows = item.get("workflow_ids")
            public_help = item.get("public_help")

            if not isinstance(module_id, str) or not module_id or module_id != module_id.strip():
                raise CapabilityRegistryError(f"modules[{index}] has invalid module_id")
            if module_id in seen:
                raise CapabilityRegistryError(f"duplicate capability module_id: {module_id}")
            seen.add(module_id)

            cls = self._classes.get(module_id)
            if cls is None:
                raise CapabilityRegistryError(
                    f"capability module is not registered in canonical ModuleRegistry: {module_id}"
                )
            if not isinstance(version, str) or version != cls.metadata.version:
                raise CapabilityRegistryError(
                    f"capability version drift for {module_id}: policy={version!r} "
                    f"runtime={cls.metadata.version!r}"
                )
            if not isinstance(gates, dict):
                raise CapabilityRegistryError(f"{module_id}: gates must be an object")
            required_gate_names = {
                "implemented",
                "tested",
                "qualified_engineering",
                "registered",
                "ui_visible",
                "link_enabled",
                "ai_callable",
                "api_runnable",
            }
            if set(gates) != required_gate_names:
                missing = sorted(required_gate_names - set(gates))
                extra = sorted(set(gates) - required_gate_names)
                raise CapabilityRegistryError(
                    f"{module_id}: gate keys mismatch missing={missing} extra={extra}"
                )
            if any(type(gates[name]) is not bool for name in required_gate_names):
                raise CapabilityRegistryError(f"{module_id}: every gate must be boolean")

            if gates["ui_visible"]:
                self._require_gate_set(module_id, gates, required_ui, "ui_visible")
            if gates["link_enabled"]:
                self._require_gate_set(module_id, gates, required_link, "link_enabled")
            if gates["ai_callable"]:
                self._require_gate_set(module_id, gates, required_ai, "ai_callable")
            if gates["link_enabled"] and not gates["api_runnable"]:
                raise CapabilityRegistryError(
                    f"{module_id}: link-enabled modules must be runnable through the typed API"
                )
            if gates["ai_callable"] and not gates["api_runnable"]:
                raise CapabilityRegistryError(
                    f"{module_id}: AI-callable modules must be API-runnable"
                )

            if not isinstance(workflows, list) or any(
                not isinstance(value, str) or not value for value in workflows
            ):
                raise CapabilityRegistryError(f"{module_id}: workflow_ids must be strings")
            if (
                gates["ui_visible"]
                or gates["link_enabled"]
                or gates["ai_callable"]
                or gates["api_runnable"]
            ) and not workflows:
                raise CapabilityRegistryError(
                    f"{module_id}: exposed capability requires at least one tested workflow"
                )

            if not isinstance(public_help, dict):
                raise CapabilityRegistryError(f"{module_id}: public_help must be an object")
            summary = public_help.get("summary")
            if not isinstance(summary, str) or not summary.strip():
                raise CapabilityRegistryError(f"{module_id}: public_help.summary is required")

            # Declared module metadata is not proof, but an exposed product primitive
            # must at least claim direct unit testing + documentation. CI executes the
            # real workflow tests separately and produces the release manifest.
            proof = cls.proof_status
            if gates["ui_visible"] and not proof.unit_tests:
                raise CapabilityRegistryError(
                    f"{module_id}: UI-visible capability does not declare unit-test coverage"
                )
            if gates["ui_visible"] and not proof.documentation:
                raise CapabilityRegistryError(
                    f"{module_id}: UI-visible capability does not declare documentation"
                )

            self._records[module_id] = item

    def _validate_tested_connections(self) -> None:
        raw_connections = self._raw.get("tested_connections")
        if not isinstance(raw_connections, list):
            raise CapabilityRegistryError("tested_connections must be an array")
        seen: set[tuple[str, str, str, str]] = set()
        for index, item in enumerate(raw_connections):
            if not isinstance(item, dict):
                raise CapabilityRegistryError(
                    f"tested_connections[{index}] must be an object"
                )
            required = {
                "source_module_id",
                "source_port",
                "target_module_id",
                "target_port",
                "workflow_id",
            }
            if set(item) != required:
                missing = sorted(required - set(item))
                extra = sorted(set(item) - required)
                raise CapabilityRegistryError(
                    f"tested_connections[{index}] keys mismatch "
                    f"missing={missing} extra={extra}"
                )
            source_module_id = str(item["source_module_id"])
            source_port = str(item["source_port"])
            target_module_id = str(item["target_module_id"])
            target_port = str(item["target_port"])
            workflow_id = str(item["workflow_id"])
            key = (source_module_id, source_port, target_module_id, target_port)
            if key in seen:
                raise CapabilityRegistryError(
                    f"duplicate tested connection: {key}"
                )
            seen.add(key)

            self.require(source_module_id, "link")
            self.require(target_module_id, "link")
            source_cls = self._classes[source_module_id]
            target_cls = self._classes[target_module_id]
            source_ports = {port.name: port for port in source_cls.outputs}
            target_ports = {port.name: port for port in target_cls.inputs}
            if source_port not in source_ports:
                raise CapabilityRegistryError(
                    f"tested connection references unknown output "
                    f"{source_module_id}.{source_port}"
                )
            if target_port not in target_ports:
                raise CapabilityRegistryError(
                    f"tested connection references unknown input "
                    f"{target_module_id}.{target_port}"
                )
            incompatibility = port_connection_error(
                source_ports[source_port],
                target_ports[target_port],
            )
            if incompatibility is not None:
                raise CapabilityRegistryError(
                    f"tested connection {key} is incompatible: {incompatibility}"
                )
            source_workflows = set(self._records[source_module_id]["workflow_ids"])
            target_workflows = set(self._records[target_module_id]["workflow_ids"])
            if workflow_id not in source_workflows or workflow_id not in target_workflows:
                raise CapabilityRegistryError(
                    f"tested connection {key} cites workflow {workflow_id!r} "
                    "not declared by both modules"
                )
            self._tested_connections[key] = workflow_id

    @staticmethod
    def _require_gate_set(
        module_id: str,
        gates: Mapping[str, bool],
        names: tuple[str, ...],
        surface: str,
    ) -> None:
        missing = [name for name in names if not bool(gates.get(name, False))]
        if missing:
            raise CapabilityRegistryError(
                f"{module_id}: {surface} requires gates {missing}"
            )

    def contains(self, module_id: str) -> bool:
        return module_id in self._records

    def record(self, module_id: str) -> Mapping[str, Any]:
        try:
            return self._records[module_id]
        except KeyError as exc:
            raise KeyError(f"module is hidden/unqualified for production exposure: {module_id}") from exc

    def allowed(self, module_id: str, surface: str) -> bool:
        if surface not in self._SURFACE_FLAG:
            raise ValueError(f"unknown capability surface: {surface}")
        record = self._records.get(module_id)
        if record is None:
            return False
        return bool(record["gates"][self._SURFACE_FLAG[surface]])

    def require(self, module_id: str, surface: str) -> None:
        if not self.allowed(module_id, surface):
            raise CapabilityRegistryError(
                f"module is unavailable on {surface} surface: {module_id}"
            )

    def module_ids(self, surface: str = "ui") -> tuple[str, ...]:
        return tuple(
            module_id
            for module_id in sorted(self._records)
            if self.allowed(module_id, surface)
        )

    def classes(self, surface: str = "ui") -> list[type]:
        return [self._classes[module_id] for module_id in self.module_ids(surface)]

    def validate_experiment(self, experiment: Experiment, *, surface: str = "api") -> None:
        for node in experiment.nodes:
            self.require(node.module_id, surface)

    def connection_error(
        self,
        source_module_id: str,
        source_port_name: str,
        target_module_id: str,
        target_port_name: str,
    ) -> str | None:
        self.require(source_module_id, "link")
        self.require(target_module_id, "link")
        source_cls = self._classes[source_module_id]
        target_cls = self._classes[target_module_id]
        source_ports = {port.name: port for port in source_cls.outputs}
        target_ports = {port.name: port for port in target_cls.inputs}
        if source_port_name not in source_ports:
            return f"unknown output port: {source_port_name}"
        if target_port_name not in target_ports:
            return f"unknown input port: {target_port_name}"
        incompatibility = port_connection_error(
            source_ports[source_port_name],
            target_ports[target_port_name],
        )
        if incompatibility is not None:
            return incompatibility
        key = (
            source_module_id,
            source_port_name,
            target_module_id,
            target_port_name,
        )
        if key not in self._tested_connections:
            return "connection path is not qualified by a tested workflow"
        return None

    def compatible_targets(self, module_id: str) -> list[dict[str, str]]:
        self.require(module_id, "link")
        targets: list[dict[str, str]] = []
        for (
            source_module_id,
            source_port,
            target_module_id,
            target_port,
        ), workflow_id in sorted(self._tested_connections.items()):
            if source_module_id != module_id:
                continue
            targets.append(
                {
                    "source_port": source_port,
                    "target_module_id": target_module_id,
                    "target_port": target_port,
                    "qualified_by_workflow": workflow_id,
                }
            )
        return targets

    def module_payload(self, module_id: str) -> dict[str, Any]:
        record = dict(self.record(module_id))
        cls = self._classes[module_id]
        metadata = asdict(cls.metadata)
        metadata["maturity"] = cls.metadata.maturity.value
        return {
            "module_id": module_id,
            "module_version": cls.metadata.version,
            "metadata": metadata,
            "inputs": [asdict(port) for port in cls.inputs],
            "outputs": [asdict(port) for port in cls.outputs],
            "parameters": [asdict(parameter) for parameter in cls.parameters],
            "supports_gpu": bool(cls.supports_gpu),
            "declared_proof_status": cls.proof_status.to_dict(),
            "capability_gates": dict(record["gates"]),
            "workflow_ids": list(record["workflow_ids"]),
            "public_help": dict(record["public_help"]),
            "compatible_targets": self.compatible_targets(module_id)
            if record["gates"]["link_enabled"]
            else [],
            "metadata_is_verification_evidence": False,
            "capability_qualification_class": "engineering",
            "proof_effect": "none",
            "promotion_authority": False,
        }

    def payload(self, surface: str = "ui") -> dict[str, Any]:
        ids = self.module_ids(surface)
        return {
            "schema": "cace-qualified-capabilities-v1",
            "surface": surface,
            "default_hidden": True,
            "capability_policy_sha256": self.policy_sha256,
            "full_registry_contract_sha256": self.full_registry_contract_sha256,
            "metadata_is_verification_evidence": False,
            "qualification_class": "engineering",
            "proof_effect": "none",
            "promotion_authority": False,
            "modules": [self.module_payload(module_id) for module_id in ids],
        }

    def release_manifest_payload(self, *, source_commit: str) -> dict[str, Any]:
        if not isinstance(source_commit, str) or not source_commit.strip():
            raise ValueError("source_commit must be non-empty")
        payload = self.payload("ui")
        return {
            "schema": "cace-qualified-capability-release-manifest-v1",
            "source_commit": source_commit.strip(),
            "capability_policy_sha256": self.policy_sha256,
            "full_registry_contract_sha256": self.full_registry_contract_sha256,
            "ui_module_ids": list(self.module_ids("ui")),
            "link_module_ids": list(self.module_ids("link")),
            "ai_module_ids": list(self.module_ids("ai")),
            "api_module_ids": list(self.module_ids("api")),
            "modules": payload["modules"],
            "qualification_class": "engineering",
            "proof_effect": "none",
            "promotion_authority": False,
            "note": (
                "Manifest proves only that the configured engineering capability "
                "gates/workflow tests passed for this source state; it does not "
                "promote mathematical proof status."
            ),
        }
