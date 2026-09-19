from __future__ import annotations

import json
from typing import Any, Mapping

from cace_studio.core.module import ExecutionContext, Module, ValidationError
from cace_studio.core.types import Maturity, ModuleMetadata, ParameterSpec, PortSpec, ProofStatus
from cace_studio.research.open_problems import OpenProblem


def _problem_from_params(params: Mapping[str, Any]) -> OpenProblem:
    try:
        tags = json.loads(str(params.get("tags_json", "[]")))
    except json.JSONDecodeError as exc:
        raise ValueError("tags_json must be valid JSON") from exc
    return OpenProblem(
        problem_id=str(params.get("problem_id", "")),
        title=str(params.get("title", "")),
        domain=str(params.get("domain", "")),
        status=str(params.get("status", "")),
        collection=str(params.get("collection", "")),
        summary=str(params.get("summary", "")),
        authority=str(params.get("authority", "")),
        source_url=str(params.get("source_url", "")),
        last_verified=str(params.get("last_verified", "")),
        tags=tuple(tags) if isinstance(tags, list) else (),
    )


class OpenProblemModule(Module):
    metadata = ModuleMetadata(
        "research.open_problem",
        "Open Scientific Problem",
        "0.1.0",
        "Research Navigation",
        "Source-backed open/solved research question imported from the Open Problems Toolkit.",
        Maturity.EXPERIMENTAL,
        assumptions=(
            "Status is a dated catalog snapshot and may become stale.",
            "The node is research navigation only and generates no proof/verification evidence.",
            "AI or numerical exploration cannot by itself mark an open problem solved.",
        ),
    )
    outputs = (
        PortSpec("problem", "open_problem"),
        PortSpec("research_prompt", "text"),
    )
    parameters = (
        ParameterSpec("problem_id", "string", "custom.problem", "Stable catalog problem ID."),
        ParameterSpec("title", "string", "Custom research problem", "Problem title."),
        ParameterSpec("domain", "string", "Unspecified", "Scientific/mathematical domain."),
        ParameterSpec("status", "string", "unknown", "open / solved / partially-resolved / unknown"),
        ParameterSpec("collection", "string", "Custom", "Catalog/collection name."),
        ParameterSpec("summary", "string", "User-defined research question.", "Short problem summary."),
        ParameterSpec("authority", "string", "User supplied", "Status/source authority."),
        ParameterSpec("source_url", "string", "https://example.invalid/", "Source URL metadata."),
        ParameterSpec("last_verified", "string", "1970-01-01", "Date status was last checked."),
        ParameterSpec("tags_json", "string", "[]", "JSON list of short tags."),
    )
    proof_status = ProofStatus(
        evidence=set(),
        unit_tests=True,
        documentation=True,
        limitations=[
            "This node is research navigation, not evidence that the problem is solved.",
            "Catalog status must be refreshed against the cited authority over time.",
            "AI Play is advisory and cannot mutate verification state.",
        ],
    )

    def validate(self, inputs: Mapping[str, Any], params: Mapping[str, Any]) -> None:
        super().validate(inputs, params)
        resolved = self.resolved_params(params)
        try:
            _problem_from_params(resolved)
        except (TypeError, ValueError) as exc:
            raise ValidationError(str(exc)) from exc

    def execute(
        self,
        inputs: Mapping[str, Any],
        params: Mapping[str, Any],
        ctx: ExecutionContext,
    ) -> Mapping[str, Any]:
        problem = _problem_from_params(params)
        return {
            "problem": problem.to_dict(),
            "research_prompt": problem.play_context(),
        }

    def verify(self, inputs, params, outputs, ctx):
        # Deliberately non-evidentiary. Downstream mathematical/scientific
        # modules must generate their own verification records.
        return []


def register_open_problems(registry) -> None:
    registry.register(OpenProblemModule)
