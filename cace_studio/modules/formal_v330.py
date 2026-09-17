from __future__ import annotations

from typing import Any, Mapping

from cace_studio.core.module import ExecutionContext, Module
from cace_studio.core.proof_contract import ProofContractRegistry
from cace_studio.core.types import (
    EvidenceKind,
    Maturity,
    ModuleMetadata,
    ParameterSpec,
    PortSpec,
    ProofStatus,
)
from cace_studio.core.verification import VerificationRecord, VerificationState


CLAIM_ID = "cace.v330.continuum-proof-strengthening"
MODULE_ID = "formal330.qualified_theorem_endpoint"
DEFAULT_THEOREM = "CACEFormal.Continuum.continuumPragerSynge_of_weakGreen"

_SCOPE_NOTE = (
    "This module certifies membership of a requested theorem in the canonical "
    "v3.30 formally qualified endpoint set and exposes proof provenance. It does "
    "not establish that runtime PDE data satisfy the theorem hypotheses."
)


class FormalV330QualifiedTheoremEndpoint(Module):
    metadata = ModuleMetadata(
        MODULE_ID,
        "Qualified v3.30 Theorem Endpoint",
        "3.40.0",
        "CACE Formal",
        (
            "Expose one theorem endpoint from the canonical v3.30 Lean proof contract; "
            "runtime FORMAL PASS is retained only by the global claim/proof-contract/"
            "proof-ledger/executable-source gate."
        ),
        Maturity.BETA,
        assumptions=(
            "The requested theorem name must exactly match a canonical v3.30 endpoint.",
            "Formal qualification and executable-source identity are checked by the runtime formal gate.",
        ),
    )
    inputs = ()
    outputs = (PortSpec("result", "object"),)
    parameters = (
        ParameterSpec(
            "theorem_name",
            "str",
            DEFAULT_THEOREM,
            "Fully-qualified Lean theorem endpoint to expose.",
        ),
    )
    proof_status = ProofStatus(
        evidence={EvidenceKind.FORMAL},
        unit_tests=True,
        regression_tests=True,
        documentation=True,
        formal_artifact="CACEFormal.V330AxiomAudit",
        limitations=[
            _SCOPE_NOTE,
            "No numerical solution, mesh, boundary condition, Green-pairing hypothesis, or PDE admissibility premise is validated by this module.",
        ],
    )

    @staticmethod
    def _contract():
        return ProofContractRegistry.load_default().for_claim(CLAIM_ID)

    def execute(
        self,
        inputs: Mapping[str, Any],
        params: Mapping[str, Any],
        ctx: ExecutionContext,
    ) -> Mapping[str, Any]:
        theorem_name = str(params["theorem_name"])
        contract = self._contract()
        endpoint_member = bool(
            contract is not None and theorem_name in contract.endpoint_theorems
        )
        return {
            "result": {
                "claim_id": CLAIM_ID,
                "theorem_name": theorem_name,
                "endpoint_member": endpoint_member,
                "proof_contract_id": contract.contract_id if contract else None,
                "proof_contract_sha256": contract.contract_sha256 if contract else None,
                "scope_note": _SCOPE_NOTE,
            }
        }

    def verify(
        self,
        inputs: Mapping[str, Any],
        params: Mapping[str, Any],
        outputs: Mapping[str, Any],
        ctx: ExecutionContext,
    ) -> list[VerificationRecord]:
        theorem_name = str(params["theorem_name"])
        contract = self._contract()
        result = outputs.get("result")
        expected_member = bool(
            contract is not None and theorem_name in contract.endpoint_theorems
        )
        consistent = bool(
            isinstance(result, Mapping)
            and result.get("claim_id") == CLAIM_ID
            and result.get("theorem_name") == theorem_name
            and result.get("endpoint_member") is expected_member
            and result.get("proof_contract_id") == (
                contract.contract_id if contract else None
            )
            and result.get("proof_contract_sha256") == (
                contract.contract_sha256 if contract else None
            )
            and result.get("scope_note") == _SCOPE_NOTE
        )
        passed = bool(expected_member and consistent)
        return [
            VerificationRecord(
                verifier="formal330-qualified-theorem-endpoint",
                kind=EvidenceKind.FORMAL,
                claim=(
                    f"{theorem_name} is an endpoint of the canonical v3.30 "
                    "Lean proof contract."
                ),
                state=VerificationState.PASS if passed else VerificationState.FAIL,
                method=(
                    "exact canonical proof-contract endpoint membership; "
                    "global runtime formal gate supplies qualified provenance "
                    "and executable-source binding"
                ),
                metrics={
                    "claim_id": CLAIM_ID,
                    "theorem_name": theorem_name,
                    "endpoint_member": expected_member,
                    "output_consistent": consistent,
                    "proof_contract_id": contract.contract_id if contract else None,
                    "proof_contract_sha256": (
                        contract.contract_sha256 if contract else None
                    ),
                },
                notes=(
                    _SCOPE_NOTE,
                    "A FORMAL PASS from this verifier is not sufficient by itself; GraphExecutor applies the fail-closed formal qualification gate afterward.",
                ),
            )
        ]


def register_formal_v330(registry) -> None:
    registry.register(FormalV330QualifiedTheoremEndpoint)
