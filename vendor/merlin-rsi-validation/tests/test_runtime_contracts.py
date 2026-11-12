import unittest
from dataclasses import replace

from merlin.runtime_contracts import (
    ApprovalRecord, RunRecord, append_event, authorize_side_effect,
    check_idempotency, verify_event_chain,
)


class RuntimeContractTests(unittest.TestCase):
    def setUp(self):
        self.run = RunRecord(
            run_id="run-1", conversation_id="conv-1", request_id="req-1",
            idempotency_key="idem-1", capability_id="research.search",
            capability_version="1.0.0", policy_hash="policy-sha256",
            state="queued", created_at="2026-11-06T12:00:00Z",
            max_steps=12, max_runtime_seconds=300, max_cost_units=100,
        )

    def test_run_record_requires_timezone_and_positive_budgets(self):
        with self.assertRaises(ValueError):
            replace(self.run, created_at="2026-11-06T12:00:00")
        with self.assertRaises(ValueError):
            replace(self.run, max_steps=0)

    def test_event_chain_is_ordered_and_verifiable(self):
        first = append_event([], run_id="run-1", event_type="run.created",
                             occurred_at="2026-11-06T12:00:00Z", actor="system",
                             payload={"request": "req-1"})
        second = append_event([first], run_id="run-1", event_type="run.started",
                              occurred_at="2026-11-06T12:00:01Z", actor="worker-1",
                              payload={"worker": "avrea"})
        self.assertEqual(second.sequence, 2)
        self.assertTrue(verify_event_chain([first, second]))

    def test_event_chain_detects_payload_tampering(self):
        event = append_event([], run_id="run-1", event_type="run.created",
                             occurred_at="2026-11-06T12:00:00Z", actor="system",
                             payload={"safe": True})
        tampered = replace(event, payload={"safe": False})
        with self.assertRaises(ValueError):
            verify_event_chain([tampered])

    def test_event_chain_rejects_cross_run_append(self):
        event = append_event([], run_id="run-1", event_type="run.created",
                             occurred_at="2026-11-06T12:00:00Z", actor="system",
                             payload={})
        with self.assertRaises(ValueError):
            append_event([event], run_id="run-2", event_type="run.started",
                         occurred_at="2026-11-06T12:00:01Z", actor="worker",
                         payload={})

    def test_event_rejects_naive_timestamp(self):
        with self.assertRaises(ValueError):
            append_event([], run_id="run-1", event_type="run.created",
                         occurred_at="2026-11-06T12:00:00", actor="system",
                         payload={})

    def test_pending_approval_never_authorizes_side_effect(self):
        approval = ApprovalRecord(
            approval_id="a-1", run_id="run-1", step_id="step-1",
            action_digest="action-hash", policy_hash="policy-hash",
            status="pending", requested_at="2026-11-06T12:00:00Z",
        )
        self.assertFalse(authorize_side_effect(
            approval, run_id="run-1", step_id="step-1",
            action_digest="action-hash", policy_hash="policy-hash"))

    def test_approval_is_bound_to_exact_action_and_policy(self):
        approval = ApprovalRecord(
            approval_id="a-2", run_id="run-1", step_id="step-1",
            action_digest="action-hash", policy_hash="policy-hash",
            status="approved", requested_at="2026-11-06T12:00:00Z",
            decided_at="2026-11-06T12:01:00Z", approver_id="human-1",
        )
        self.assertTrue(authorize_side_effect(
            approval, run_id="run-1", step_id="step-1",
            action_digest="action-hash", policy_hash="policy-hash"))
        self.assertFalse(authorize_side_effect(
            approval, run_id="run-1", step_id="step-1",
            action_digest="different-action", policy_hash="policy-hash"))
        self.assertFalse(authorize_side_effect(
            approval, run_id="run-1", step_id="step-1",
            action_digest="action-hash", policy_hash="changed-policy"))

    def test_idempotency_allows_exact_replay(self):
        self.assertEqual(check_idempotency({"idem-1": "request-hash"},
                                           idempotency_key="idem-1",
                                           request_digest="request-hash"), "replay")

    def test_idempotency_rejects_key_reuse_for_different_request(self):
        with self.assertRaises(ValueError):
            check_idempotency({"idem-1": "old-hash"}, idempotency_key="idem-1",
                              request_digest="new-hash")


if __name__ == "__main__":
    unittest.main()
