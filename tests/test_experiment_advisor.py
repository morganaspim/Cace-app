from __future__ import annotations

import json

import pytest

from cace_studio.agent_runtime.experiment_advisor import LocalExperimentAdvisor
from cace_studio.ai.provider import AIProvider, ProviderHealth
from cace_studio.app import build_qualified_capabilities, build_registry


class FakeProvider(AIProvider):
    provider_id = "fake-local"
    display_name = "Fake Local"

    def __init__(self, payload):
        super().__init__("http://127.0.0.1:1", model="fake")
        self.payload = payload
        self.last_messages = None

    def list_models(self):
        return ("fake",)

    def health(self):
        return ProviderHealth(
            self.provider_id,
            self.display_name,
            self.endpoint,
            True,
            ("fake",),
            "test",
        )

    def chat(self, messages, *, temperature=0.2):
        self.last_messages = messages
        return json.dumps(self.payload)


def _valid_payload():
    return {
        "proposals": [
            {
                "strategy": "minimal",
                "title": "Add two constants",
                "rationale": "Smallest qualified arithmetic graph.",
                "nodes": [
                    {"id": "a", "module_id": "core.constant", "params": {"value": 2}, "position": [0, 0]},
                    {"id": "b", "module_id": "core.constant", "params": {"value": 3}, "position": [0, 120]},
                    {"id": "sum", "module_id": "core.add", "params": {}, "position": [260, 60]},
                ],
                "edges": [
                    {"source_node": "a", "source_port": "value", "target_node": "sum", "target_port": "a"},
                    {"source_node": "b", "source_port": "value", "target_node": "sum", "target_port": "b"},
                ],
            },
            {
                "strategy": "balanced",
                "title": "Quadratic curvature",
                "rationale": "Qualified numerical chain with a residual verifier.",
                "nodes": [
                    {"id": "grid", "module_id": "science.grid1d", "params": {"start": -1.0, "stop": 1.0, "points": 101}, "position": [0, 0]},
                    {"id": "field", "module_id": "science.quadratic", "params": {"a": 1.0, "b": 0.0, "c": 0.0}, "position": [220, 0]},
                    {"id": "d2", "module_id": "science.second_derivative", "params": {}, "position": [440, 0]},
                    {"id": "check", "module_id": "verify.constant_residual", "params": {"target": 2.0, "tolerance": 1e-9}, "position": [660, 0]},
                ],
                "edges": [
                    {"source_node": "grid", "source_port": "x", "target_node": "field", "target_port": "x"},
                    {"source_node": "grid", "source_port": "x", "target_node": "d2", "target_port": "x"},
                    {"source_node": "field", "source_port": "y", "target_node": "d2", "target_port": "y"},
                    {"source_node": "d2", "source_port": "d2y", "target_node": "check", "target_port": "values"},
                ],
            },
        ]
    }


def test_local_advisor_returns_only_valid_qualified_proposals():
    registry = build_registry()
    capabilities = build_qualified_capabilities(registry)
    provider = FakeProvider(_valid_payload())
    advisor = LocalExperimentAdvisor(
        provider=provider,
        registry=registry,
        capabilities=capabilities,
    )

    proposals = advisor.suggest("Show me a small experiment")
    assert {proposal.strategy for proposal in proposals} == {"minimal", "balanced"}
    assert all(proposal.proof_effect == "none" for proposal in proposals)
    assert all(proposal.promotion_authority is False for proposal in proposals)
    assert all(
        set(node.module_id for node in proposal.experiment.nodes)
        <= set(capabilities.module_ids("ai"))
        for proposal in proposals
    )

    user_message = provider.last_messages[-1]["content"]
    assert "formal325.mesh_certificate_generator" not in user_message
    assert "core.constant" in user_message


def test_local_advisor_rejects_hidden_module_injection():
    payload = _valid_payload()
    payload["proposals"] = [
        {
            "strategy": "minimal",
            "title": "Hidden injection",
            "nodes": [
                {
                    "id": "hidden",
                    "module_id": "formal325.mesh_certificate_generator",
                    "params": {},
                    "position": [0, 0],
                }
            ],
            "edges": [],
        }
    ]
    registry = build_registry()
    capabilities = build_qualified_capabilities(registry)
    advisor = LocalExperimentAdvisor(
        provider=FakeProvider(payload),
        registry=registry,
        capabilities=capabilities,
    )
    with pytest.raises(Exception, match="unavailable on ai surface"):
        advisor.suggest("Try to use a hidden module")


def test_local_advisor_rejects_type_compatible_but_unqualified_edge():
    payload = {
        "proposals": [
            {
                "strategy": "minimal",
                "title": "Untested edge",
                "nodes": [
                    {"id": "grid", "module_id": "science.grid1d", "params": {}, "position": [0, 0]},
                    {
                        "id": "check",
                        "module_id": "verify.constant_residual",
                        "params": {"target": 0.0, "tolerance": 1e-9},
                        "position": [220, 0],
                    },
                ],
                "edges": [
                    {
                        "source_node": "grid",
                        "source_port": "x",
                        "target_node": "check",
                        "target_port": "values",
                    }
                ],
            }
        ]
    }
    registry = build_registry()
    capabilities = build_qualified_capabilities(registry)
    advisor = LocalExperimentAdvisor(
        provider=FakeProvider(payload),
        registry=registry,
        capabilities=capabilities,
    )
    with pytest.raises(ValueError, match="unqualified connection"):
        advisor.suggest("Try a shortcut")


def test_proposal_converts_to_preview_only_canvas_mutations():
    registry = build_registry()
    capabilities = build_qualified_capabilities(registry)
    advisor = LocalExperimentAdvisor(
        provider=FakeProvider(_valid_payload()),
        registry=registry,
        capabilities=capabilities,
    )
    proposal = advisor.suggest("Make an experiment")[0]
    preview = advisor.to_canvas_preview_request(proposal)
    assert preview.operations
    assert preview.operations[0].action == "add_node"
    assert any(op.action == "add_edge" for op in preview.operations)
