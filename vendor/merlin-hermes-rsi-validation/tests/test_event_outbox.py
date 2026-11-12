import tempfile
import unittest
from pathlib import Path
from merlin.event_outbox import MerlinEventOutbox, OutboxConflict, LeaseConflict


class MerlinEventOutboxTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.outbox = MerlinEventOutbox(Path(self.temp.name) / "outbox.sqlite3")

    def tearDown(self):
        self.temp.cleanup()

    def test_idempotency_and_payload_conflict(self):
        a = self.outbox.enqueue("same-key","hermes.event",{"n":1},now=1)
        b = self.outbox.enqueue("same-key","hermes.event",{"n":1},now=2)
        self.assertEqual(a["event_id"],b["event_id"])
        with self.assertRaises(OutboxConflict):
            self.outbox.enqueue("same-key","hermes.event",{"n":2},now=3)

    def test_claim_ack_and_replay(self):
        event = self.outbox.enqueue("ack-key","hermes.event",{"n":2},now=1)
        lease = self.outbox.claim_next("hermes",lease_seconds=10,now=2)
        ack = self.outbox.acknowledge(event["event_id"],"hermes",lease["lease_token"],now=3)
        self.assertEqual(ack["state"],"acknowledged")
        self.assertEqual(self.outbox.acknowledge(event["event_id"],"other","stale",now=4)["state"],"acknowledged")

    def test_expired_lease_redelivery_invalidates_old_token(self):
        event = self.outbox.enqueue("expiry-key","worker.event",{},now=1)
        first = self.outbox.claim_next("worker-a",lease_seconds=2,now=2)
        self.assertEqual(self.outbox.recover_expired(now=5),1)
        second = self.outbox.claim_next("worker-b",lease_seconds=10,now=5)
        self.assertEqual(second["event_id"],event["event_id"])
        with self.assertRaises(LeaseConflict):
            self.outbox.acknowledge(event["event_id"],"worker-a",first["lease_token"],now=6)

    def test_retry_quarantines_after_limit(self):
        event = self.outbox.enqueue("retry-key","avrea.dispatch",{"job":"bounded"},now=1)
        first = self.outbox.claim_next("worker",lease_seconds=10,now=2)
        self.assertEqual(self.outbox.retry(event["event_id"],"worker",first["lease_token"],"retry",max_attempts=2,now=3)["state"],"pending")
        second = self.outbox.claim_next("worker",lease_seconds=10,now=4)
        final = self.outbox.retry(event["event_id"],"worker",second["lease_token"],"failed",max_attempts=2,now=5)
        self.assertEqual(final["state"],"quarantined")

    def test_claim_can_filter_topics_without_leasing_unrelated_events(self):
        outbox = MerlinEventOutbox(Path(self.temp.name) / "topics.sqlite3")
        outbox.enqueue("telemetry:1", "merlin.telemetry.task.progress", {"kind": "task.progress"}, now=1)
        outbox.enqueue("hermes:1", "merlin.hermes.task", {"task": "research"}, now=2)
        claimed = outbox.claim_next("hud", topics=["merlin.telemetry.task.progress"], now=3)
        self.assertEqual(claimed["topic"], "merlin.telemetry.task.progress")
        self.assertEqual(outbox.counts()["pending"], 1)
