import tempfile
import unittest
from pathlib import Path

from merlin.event_outbox import MerlinEventOutbox
from merlin.hermes_worker import HermesWorker


def task_payload(task_id="task-1"):
    return {
        "schema": "merlin-research-task/1",
        "task_id": task_id, "hypothesis_id": "H-1",
        "objective": "Run a bounded deterministic experiment",
        "stage": "experiment",
        "resource_budget": {"cpu_cores": 1, "memory_bytes": 1024,
                            "max_wall_seconds": 10, "compute_budget_units": 10},
        "approval_ref": "approval:1", "lease_ref": "lease:1",
        "authority": "bounded_execution_only", "promotion_authority": False,
        "experiment_spec": {"seed": 7},
    }


class HermesWorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.outbox = MerlinEventOutbox(Path(self.temp.name) / "outbox.sqlite3")

    def tearDown(self):
        self.temp.cleanup()

    def worker(self, handler, approval=True, lease=True, max_attempts=3):
        return HermesWorker(
            self.outbox, handlers={"experiment": handler},
            approval_validator=lambda ref, task: approval and ref == "approval:1",
            lease_validator=lambda ref, budget: lease and ref == "lease:1",
            max_attempts=max_attempts, retry_delay_seconds=0,
        )

    def test_executes_handler_reports_progress_and_acknowledges_receipt(self):
        events = []
        def handler(task, context):
            self.assertEqual(context.idempotency_key, "hermes-task-handler:task-1")
            self.assertGreater(context.deadline_epoch, 0)
            context.emit_progress("Numerical experiment started", {"seed": 7})
            context.emit_tool_event("agent.tool.started", "python", {"operation": "bounded"})
            context.emit_tool_event("agent.tool.completed", "python", {"status": "ok"})
            return {"summary": "completed", "evidence_refs": ["sha256:abc"]}
        event = self.outbox.enqueue("research-task:task-1", "merlin.hermes.task",
                                    task_payload(), now=1)
        result = self.worker(handler).run_once(now=2)
        stored = self.outbox.get(event["event_id"])
        self.assertEqual(result["status"], "completed")
        self.assertEqual(stored["state"], "acknowledged")
        self.assertFalse(stored["result"]["promotion_authority"])
        self.assertEqual(stored["result"]["evidence_refs"], ["sha256:abc"])
        telemetry = [row for row in self._all_rows() if row["topic"].startswith("merlin.telemetry.")]
        kinds = {row["payload"]["kind"] for row in telemetry}
        self.assertTrue({"task.progress", "agent.tool.started", "agent.tool.completed",
                         "task.completed", "agent.status"}.issubset(kinds))

    def test_revalidates_approval_and_never_calls_handler_when_revoked(self):
        called = []
        event = self.outbox.enqueue("research-task:task-2", "merlin.hermes.task",
                                    task_payload("task-2"), now=1)
        result = self.worker(lambda task, ctx: called.append(True) or {},
                             approval=False).run_once(now=2)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(called, [])
        self.assertEqual(self.outbox.get(event["event_id"])["state"], "acknowledged")

    def test_revalidates_mcfc_lease_before_execution(self):
        called = []
        event = self.outbox.enqueue("research-task:task-3", "merlin.hermes.task",
                                    task_payload("task-3"), now=1)
        result = self.worker(lambda task, ctx: called.append(True) or {},
                             lease=False).run_once(now=2)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(called, [])
        self.assertEqual(self.outbox.get(event["event_id"])["state"], "acknowledged")

    def test_handler_failure_uses_bounded_retry_and_quarantine(self):
        event = self.outbox.enqueue("research-task:task-4", "merlin.hermes.task",
                                    task_payload("task-4"), now=1)
        worker = self.worker(lambda task, ctx: (_ for _ in ()).throw(RuntimeError("simulated failure")),
                             max_attempts=1)
        result = worker.run_once(now=2)
        self.assertEqual(result["status"], "quarantined")
        self.assertEqual(self.outbox.get(event["event_id"])["state"], "quarantined")

    def test_worker_does_not_claim_non_hermes_topics(self):
        self.outbox.enqueue("telemetry:1", "merlin.telemetry.task.progress",
                            {"event_id": "x"}, now=1)
        result = self.worker(lambda task, ctx: {}).run_once(now=2)
        self.assertIsNone(result)
        self.assertEqual(self.outbox.counts()["pending"], 1)

    def _all_rows(self):
        import sqlite3
        with sqlite3.connect(self.outbox.path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute("SELECT topic,payload_json FROM event_outbox").fetchall()
        import json
        return [{"topic": row["topic"], "payload": json.loads(row["payload_json"])}
                for row in rows]


if __name__ == "__main__":
    unittest.main()
