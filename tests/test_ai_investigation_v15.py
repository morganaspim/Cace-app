"""Advisory-only regression cases: no model, network, canonical verifier or physical device."""
from __future__ import annotations

from dataclasses import replace
import unittest

from cace_studio.ai.investigation import (
    Blockage, BlockageKind, ClaimStatus, EngineeringSpec, Evidence, Hypothesis,
    Investigator, Outcome, PlanState, ResearchError, Tool, IterationLedger,
    evaluate_hypotheses, audit_blockage, choose_lenses,
)


class SpecAndEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.spec = EngineeringSpec(
            goal="Distinguish a source artifact from an actual signal",
            domain="signal", acceptance=("Independently check a second measurement",),
            inputs=("observation set A",), permissions=("local_read",),
            max_steps=4, max_cost=4.0)

    def test_spec_requires_goal_acceptance_and_bounded_budget(self):
        for changes in ({"goal": " "}, {"acceptance": ()}, {"max_steps": 0},
                        {"max_steps": 200}, {"max_cost": -1}, {"domain": ""}):
            with self.assertRaises(ResearchError):
                Investigator().plan(replace(self.spec, **changes), ("analyze",))

    def test_unsupported_permission_does_not_grant_external_action(self):
        with self.assertRaises(ResearchError):
            Tool("send", "message", "external_send", 0.1, lambda d: "sent")

    def test_hypothesis_comparison_preserves_unmodeled_and_source_dependence(self):
        observations = [
            Evidence("e1", "peak20", True, "s1", "instrument-A", "observed"),
            Evidence("e2", "peak20", True, "s2", "instrument-A", "reported"),
            Evidence("e3", "peak20", False, "s3", "instrument-B", "observed"),
        ]
        models = [
            Hypothesis("h-real", "A persistent 20 Hz oscillator", {"peak20": True}),
            Hypothesis("h-noise", "A periodic artifact", {"peak20": False}),
        ]
        ratings = evaluate_hypotheses(observations, models)
        self.assertEqual([x.hypothesis_id for x in ratings][-1], "OTHER_UNMODELED")
        self.assertEqual(ratings[0].ranking_kind, "HEURISTIC_NOT_PROBABILITY")
        self.assertEqual(ratings[0].support, 1)
        self.assertEqual(ratings[0].contradiction, 1)
        self.assertEqual(ratings[0].unresolved, 0)
        self.assertTrue(all(x.claim_status != ClaimStatus.VERIFIED for x in ratings))

    def test_duplicate_source_id_with_conflicting_contents_is_rejected(self):
        rows = [Evidence("e1", "peak", True, "src1", "family1", "observed"),
                Evidence("e1", "peak", False, "src1", "family1", "observed")]
        with self.assertRaises(ResearchError):
            evaluate_hypotheses(rows, [Hypothesis("h1", "A", {"peak": True})])

    def test_mandatory_lenses_cannot_be_opted_out(self):
        lenses = choose_lenses("history", preferred=("causal",))
        self.assertTrue({"source_audit", "counterexample", "consent_privacy", "historical", "causal"}.issubset(lenses))
        self.assertEqual(len(lenses), len(set(lenses)))
        with self.assertRaises(ResearchError): choose_lenses("physics", preferred=("clairvoyance",))


class ToolRoutingTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.agent = Investigator()
        self.agent.register(Tool("slow", "analyze", "read_only", 2.0, lambda d: self.calls.append("slow") or {"ok": True}))
        self.agent.register(Tool("fast", "analyze", "read_only", 0.5, lambda d: self.calls.append("fast") or {"ok": True}))
        self.spec = EngineeringSpec(goal="Investigate anomaly", domain="physics",
                                    acceptance=("Source check",),permissions=("local_read",),max_steps=3,max_cost=3.0)

    def test_picks_lowest_cost_registered_tool(self):
        plan = self.agent.plan(self.spec, ("analyze",))
        self.assertEqual(plan.state, PlanState.READY)
        self.assertEqual(plan.steps[0].tool_id, "fast")
        self.assertFalse(plan.evidence_authority)
        self.assertEqual(plan.proof_status, "NOT_RUN")
        result = self.agent.execute(plan, {"input": "x"})
        self.assertEqual(result.outcome, Outcome.COMPLETED_ADVISORY)
        self.assertEqual(self.calls, ["fast"])
        self.assertEqual(result.receipts[0].tool_id, "fast")

    def test_missing_tool_blocks_entire_plan_without_running_partial_work(self):
        plan = self.agent.plan(self.spec, ("analyze", "nonexistent"))
        self.assertEqual(plan.state, PlanState.BLOCKED)
        result = self.agent.execute(plan, {"input": 1})
        self.assertEqual(result.outcome, Outcome.BLOCKED)
        self.assertEqual(self.calls, [])
        self.assertEqual(result.blockages[0].kind, BlockageKind.TOOL_UNAVAILABLE)

    def test_budget_block_prevents_tool_execution(self):
        plan = self.agent.plan(replace(self.spec, max_cost=0.1), ("analyze",))
        self.assertEqual(plan.state, PlanState.BLOCKED)
        self.assertEqual(self.agent.execute(plan, {}).outcome, Outcome.BLOCKED)
        self.assertFalse(self.calls)

    def test_tampered_plan_is_not_executed(self):
        from dataclasses import replace as dc_replace
        p = self.agent.plan(self.spec, ("analyze",))
        tampered = dc_replace(p, intent="Send email")
        result = self.agent.execute(tampered, {})
        self.assertEqual(result.outcome, Outcome.BLOCKED)
        self.assertEqual(result.blockages[0].kind, BlockageKind.PLAN_TAMPERED)
        self.assertFalse(self.calls)

    def test_tool_exception_captured_as_a_failure_without_automatic_retry(self):
        agent = Investigator()
        agent.register(Tool("bad", "analyze", "read_only", 0.1, lambda x: 1 / 0))
        p = agent.plan(self.spec, ("analyze",))
        res = agent.execute(p, {})
        self.assertEqual(res.outcome, Outcome.FAILED)
        self.assertEqual(res.blockages[0].kind, BlockageKind.TOOL_ERROR)
        self.assertNotIn("ZeroDivisionError", str(res.receipts))

    def test_repeated_execution_is_blocked_to_prevent_loops(self):
        p = self.agent.plan(self.spec, ("analyze",))
        self.assertEqual(self.agent.execute(p, {}).outcome, Outcome.COMPLETED_ADVISORY)
        second = self.agent.execute(p, {})
        self.assertEqual(second.outcome, Outcome.BLOCKED)
        self.assertEqual(second.blockages[0].kind, BlockageKind.REPEATED_PLAN)
        self.assertEqual(self.calls, ["fast"])

    def test_bad_tool_ids_duplicate_and_cost_invalid(self):
        with self.assertRaises(ResearchError):
            self.agent.register(Tool("fast", "same", "read_only", 2, lambda d: None))
        with self.assertRaises(ResearchError):
            Tool("bad", "analyze", "read_only", float("nan"), lambda d: None)
        with self.assertRaises(ResearchError):
            self.agent.plan(self.spec, ("analyze",) * 5)


class BlockageTransparencyTests(unittest.TestCase):
    def test_no_inference_of_censorship_from_failure(self):
        for kind in (BlockageKind.TOOL_UNAVAILABLE, BlockageKind.TOOL_ERROR,
                     BlockageKind.SOURCE_UNREACHABLE, BlockageKind.EVIDENCE_INSUFFICIENT):
            report = audit_blockage(Blockage(kind, "tool unavailable", "source-abc"))
            self.assertFalse(report["content_restriction_confirmed"])
            self.assertEqual(report["interpretation"], "CAUSE_NOT_ESTABLISHED")

    def test_explicit_content_restriction_receipt_is_required(self):
        with self.assertRaises(ResearchError):
            audit_blockage(Blockage(BlockageKind.CONTENT_RESTRICTION, "denied", ""))
        blockage = Blockage(BlockageKind.CONTENT_RESTRICTION,
                 "Documented provider restriction", "provider-policy-receipt-17")
        unverified = audit_blockage(blockage)
        self.assertFalse(unverified["content_restriction_confirmed"])
        self.assertEqual(unverified["interpretation"], "EXPLICIT_RESTRICTION_REPORTED_NOT_AUTHENTICATED")
        report = audit_blockage(blockage, trusted_receipts=frozenset({"provider-policy-receipt-17"}))
        self.assertTrue(report["content_restriction_confirmed"])
        self.assertEqual(report["interpretation"], "EXPLICIT_RESTRICTION_OBSERVED_SCOPE_LIMITED")

    def test_blockage_audit_never_infers_deliberate_motive(self):
        report = audit_blockage(Blockage(BlockageKind.CONTENT_RESTRICTION,
                 "Explicit classification", "policy-42"))
        self.assertFalse(report["intent_or_motive_established"])


class IterationLearningTests(unittest.TestCase):
    def test_continue_only_when_new_observation_or_reframed_action(self):
        ledger = IterationLedger(max_attempts=3)
        a = ledger.propose("source-check", "a" * 64, "Initial 404 observed")
        self.assertEqual(a.status, "CONTINUE_WITH_REVIEW")
        self.assertFalse(a.evidence_authority)
        stale = ledger.propose("source-check", "a" * 64, "Same observation, new words")
        self.assertEqual(stale.status, "HOLD_NO_NEW_OBSERVATION")
        self.assertEqual(len(ledger.records), 1)
        b = ledger.propose("alternate-archive", "a" * 64, "Different authorized source checked")
        self.assertEqual(b.status, "CONTINUE_WITH_REVIEW")
        c = ledger.propose("source-check", "b" * 64, "New screenshot from independent archive")
        self.assertEqual(c.status, "CONTINUE_WITH_REVIEW")
        self.assertEqual(len(ledger.records), 3)
        exhausted = ledger.propose("third-source", "c" * 64, "Fourth test proposed")
        self.assertEqual(exhausted.status, "STOP_BUDGET")

    def test_invalid_or_nontraceable_iteration_record_rejected(self):
        ledger = IterationLedger(max_attempts=1)
        for action, digest, note in ((" ", "a" * 64, "progress"),
                                     ("check", "not-a-hash", "progress"),
                                     ("check", "b" * 64, " ")):
            with self.assertRaises(ResearchError):
                ledger.propose(action, digest, note)
        with self.assertRaises(ResearchError): IterationLedger(max_attempts=0)

    def test_an_attempt_is_never_a_proof_or_an_execution_authority(self):
        ledger = IterationLedger(max_attempts=2)
        r = ledger.propose("local-test", "0" * 64, "Hypothesis rejected by negative control")
        self.assertEqual(r.proof_status, "NOT_RUN")
        self.assertEqual(r.hardware_status, "NOT_MEASURED")
        self.assertEqual(r.authorization_status, "NONE_GRANTED")


class PermissionGateTests(unittest.TestCase):
    def test_read_tool_requires_explicit_permission_in_spec(self):
        calls = []
        agent = Investigator()
        agent.register(Tool("r", "read_records", "read_only", 0.1,
                            lambda ctx: calls.append("called")))
        missing = EngineeringSpec("Inspect records", "history", ("Compare sources",),
                                  permissions=())
        p = agent.plan(missing, ("read_records",))
        self.assertEqual(p.state, PlanState.BLOCKED)
        self.assertEqual(p.blockages[0].kind, BlockageKind.AUTHORIZATION_REQUIRED)
        self.assertEqual(agent.execute(p, {}).outcome, Outcome.BLOCKED)
        self.assertEqual(calls, [])

    def test_named_tool_permission_cannot_be_inferred_from_other_permission(self):
        calls = []
        agent = Investigator()
        agent.register(Tool("db", "records", "read_only", 0.1,
                            lambda ctx: calls.append("read"), required_permission="project_dataset_read"))
        wrong = EngineeringSpec("Inspect records", "history", ("Compare sources",),
                                permissions=("local_read",))
        self.assertEqual(agent.plan(wrong, ("records",)).state, PlanState.BLOCKED)
        correct = EngineeringSpec("Inspect records", "history", ("Compare sources",),
                                  permissions=("project_dataset_read",))
        p = agent.plan(correct, ("records",))
        self.assertEqual(p.state, PlanState.READY)
        self.assertEqual(agent.execute(p, {}).outcome, Outcome.COMPLETED_ADVISORY)
        self.assertEqual(calls, ["read"])


    def test_authorized_tool_over_cheaper_unapproved_option(self):
        calls = []
        agent = Investigator()
        agent.register(Tool("cheap-but-not-authorized", "summary", "read_only", 0.01,
                            lambda ctx: calls.append("unapproved"),
                            required_permission="project_dataset_read"))
        agent.register(Tool("permitted", "summary", "read_only", 0.2,
                            lambda ctx: calls.append("permitted")))
        spec = EngineeringSpec("Summarize local data", "ai", ("Local comparison",),
                               permissions=("local_read",), max_cost=1)
        plan = agent.plan(spec, ("summary",))
        self.assertEqual(plan.steps[0].tool_id, "permitted")
        self.assertEqual(agent.execute(plan, {}).outcome, Outcome.COMPLETED_ADVISORY)
        self.assertEqual(calls, ["permitted"])

    def test_unrecognized_tool_permission_is_not_accepted(self):
        with self.assertRaises(ResearchError):
            Tool("bad", "fetch", "read_only", 0.1, lambda d: None,
                 required_permission="unspecified_external_network")


if __name__ == '__main__': unittest.main()
