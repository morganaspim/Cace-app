import unittest
from merlin.telemetry import agent_event_sink, loader_event_sink, normalize_event, telemetry_view

class TelemetryTests(unittest.TestCase):
    def test_normalizes_source_labeled_event(self):
        event = normalize_event({"source":"runtime","kind":"task.progress","run_id":"r1",
            "task_id":"t1","payload":{"step":2},"cpu_percent":12.5,
            "memory_bytes":1024,"evidence_refs":["sha256:abc"]})
        self.assertEqual(event["schema"], "merlin-telemetry/1")
        self.assertEqual(event["source"], "runtime")
        self.assertEqual(event["memory_bytes"], 1024)

    def test_rejects_source_confusion_and_bad_metrics(self):
        with self.assertRaises(ValueError):
            normalize_event({"source":"simulation_and_runtime","kind":"task.progress","run_id":"r"})
        with self.assertRaises(ValueError):
            normalize_event({"source":"runtime","kind":"resource.sample","run_id":"r","cpu_percent":120})


    def test_loader_sink_normalizes_into_runtime_resource_stream(self):
        class Store:
            def __init__(self):
                self.rows = []
            def append(self, *args):
                self.rows.append(args)
        store = Store()
        sink = loader_event_sink(store)
        sink({"source":"runtime","kind":"resource.sample","run_id":"loader-run",
              "task_id":"module-a","duration_ms":2.5,"memory_bytes":4096,
              "payload":{"component":"module_loader","operation":"load",
                         "artifact_bytes":1024,"outcome":"succeeded"}})
        event = store.rows[0][2]["event"]
        self.assertEqual(event["source"], "runtime")
        self.assertEqual(event["kind"], "resource.sample")
        self.assertEqual(event["payload"]["component"], "module_loader")

    def test_resource_payload_metrics_are_bounded(self):
        valid = normalize_event({
            "source": "avrea", "kind": "resource.sample", "run_id": "runner-1",
            "payload": {"measurement_kind": "observed", "gpu_percent": 72.5,
                        "memory_bytes": 2048, "wall_seconds": 3.2},
        })
        self.assertEqual(valid["payload"]["gpu_percent"], 72.5)
        with self.assertRaises(ValueError):
            normalize_event({
                "source": "avrea", "kind": "resource.sample", "run_id": "runner-1",
                "payload": {"gpu_percent": 120},
            })

    def test_service_bound_agent_sink_preserves_real_service_identity(self):
        class Outbox:
            def __init__(self):
                self.rows = []
            def enqueue(self, **kwargs):
                self.rows.append(kwargs)
                return kwargs
        outbox = Outbox()
        publish = agent_event_sink(outbox, "cace")
        publish(kind="verification.completed", run_id="commit-1", task_id="artifact-1",
                payload={"status": "verified", "independent": True})
        self.assertEqual(outbox.rows[0]["topic"], "merlin.telemetry.verification.completed")
        self.assertEqual(outbox.rows[0]["payload"]["source"], "cace")
        self.assertEqual(outbox.rows[0]["payload"]["task_id"], "artifact-1")

    def test_view_keeps_sources_separate(self):
        events = [normalize_event({"source":s,"kind":"task.progress","run_id":"r"})
                  for s in ("simulation","runtime")]
        view = telemetry_view(events)
        self.assertEqual(view["source_counts"]["simulation"], 1)
        self.assertEqual(view["source_counts"]["runtime"], 1)
        self.assertTrue(view["simulation_is_not_runtime"])

if __name__ == "__main__":
    unittest.main()
