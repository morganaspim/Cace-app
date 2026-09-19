from __future__ import annotations

from cace_studio.core.module import Module, ValidationError
from cace_studio.core.types import Maturity, ModuleMetadata, ParameterSpec, PortSpec, ProofStatus
from cace_studio.research.open_problems import OpenProblem


class ResearchOpenProblem(Module):
    metadata = ModuleMetadata(
        "research.open_problem",
        "Open Research Problem",
        "0.1.0",
        "Research Navigation",
        "Source-backed open-problem card for canvas exploration; never proof evidence.",
        Maturity.EXPERIMENTAL,
        assumptions=(
            "Status is a date-stamped catalog claim and may change.",
            "AI/numerical exploration cannot itself mark an open problem solved.",
        ),
    )
    outputs = (
        PortSpec("problem", "research_problem"),
        PortSpec("research_prompt", "string"),
    )
    parameters = (
        ParameterSpec("problem_id", "string", "custom.problem"),
        ParameterSpec("title", "string", "Custom open problem"),
        ParameterSpec("domain", "string", "unknown"),
        ParameterSpec("status", "string", "unknown"),
        ParameterSpec("collection", "string", "custom"),
        ParameterSpec("authority", "string", "user"),
        ParameterSpec("summary", "string", "No summary supplied."),
        ParameterSpec("source_url", "string", "https://example.invalid/"),
        ParameterSpec("last_verified", "string", "1970-01-01"),
        ParameterSpec("tags", "string", ""),
        ParameterSpec("status_note", "string", ""),
    )
    proof_status = ProofStatus(
        documentation=True,
        limitations=[
            "This module is research navigation only and generates no verification evidence.",
            "Problem status must be refreshed from authoritative sources independently.",
        ],
    )

    def _problem(self, params) -> OpenProblem:
        try:
            return OpenProblem.from_mapping(self.resolved_params(params))
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

    def validate(self, inputs, params):
        super().validate(inputs, params)
        self._problem(params)

    def execute(self, inputs, params, ctx):
        problem = self._problem(params)
        return {"problem": problem.to_dict(), "research_prompt": problem.ai_context()}

    def verify(self, inputs, params, outputs, ctx):
        return []


def register_open_problem_module(registry) -> None:
    registry.register(ResearchOpenProblem)
