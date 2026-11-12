from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas/merlin/continuum-structure.v1.schema.json"
SAMPLE_PATH = ROOT / "docs/research/paired-state-continuum-triangle.v1.json"


def read_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"{path} must contain a JSON object")
    return value


class ContinuumStructureIRTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = read_object(SCHEMA_PATH)
        cls.sample = read_object(SAMPLE_PATH)

    def test_versioned_schema_and_sample_have_matching_top_level_contract(self):
        schema, sample = self.schema, self.sample
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(schema["$id"], "urn:merlin:schema:continuum-structure:1")
        self.assertEqual(schema["type"], "object")
        self.assertIs(schema["additionalProperties"], False)
        required = set(schema["required"])
        self.assertEqual(required, set(schema["properties"]))
        self.assertEqual(required, set(sample))
        self.assertEqual(sample["schema_version"], 1)
        self.assertEqual(sample["version"], "1.0.0")

    def test_triangle_state_spaces_cells_and_edge_traces_are_consistent(self):
        sample = self.sample
        vertices = {item["id"]: item for item in sample["vertices"]}
        cells = {item["id"]: item for item in sample["cells"]}
        spaces = {item["id"]: item for item in sample["state_spaces"]}
        fields = {item["id"]: item for item in sample["edge_fields"]}
        self.assertEqual(len(vertices), len(sample["vertices"]))
        self.assertEqual(len(vertices), 3)
        self.assertEqual(len(cells), len(sample["cells"]))
        self.assertEqual(len(cells), 4)
        self.assertEqual(len(fields), len(sample["edge_fields"]))
        self.assertEqual(len(fields), 3)
        self.assertEqual(len(spaces), 1)

        for cell in cells.values():
            self.assertLessEqual(cell["dimension"], sample["geometry"]["dimension"])
            self.assertIn(cell["orientation"], (-1, 1))
            self.assertTrue(all(vertex_id in vertices for vertex_id in cell["vertex_ids"]))
            self.assertIn(cell["state_space_id"], spaces)

        for field in fields.values():
            cell = cells[field["cell_id"]]
            space = spaces[field["state_space_id"]]
            self.assertEqual(cell["dimension"], 1)
            self.assertEqual(cell["state_space_id"], field["state_space_id"])
            samples = field["samples"]
            parameters = [point["parameter"] for point in samples]
            self.assertEqual(parameters[0], 0)
            self.assertEqual(parameters[-1], 1)
            self.assertEqual(parameters, sorted(set(parameters)))
            for point in samples:
                self.assertEqual(len(point["value"]), space["dimension"])
            start_vertex, end_vertex = (vertices[key] for key in cell["vertex_ids"])
            self.assertEqual(samples[0]["value"], start_vertex["state"])
            self.assertEqual(samples[-1]["value"], end_vertex["state"])
            for point in samples:
                t = point["parameter"]
                expected = [
                    start + (end - start) * t
                    for start, end in zip(start_vertex["state"], end_vertex["state"])
                ]
                for actual, wanted in zip(point["value"], expected):
                    self.assertAlmostEqual(actual, wanted, delta=1e-9)

        self.assertEqual(fields["F_AB"]["samples"][-1]["value"], fields["F_BC"]["samples"][0]["value"])
        self.assertEqual(fields["F_BC"]["samples"][-1]["value"], fields["F_CA"]["samples"][0]["value"])
        self.assertEqual(fields["F_CA"]["samples"][-1]["value"], fields["F_AB"]["samples"][0]["value"])

    def test_transformations_invariants_and_evidence_keep_epistemic_boundaries(self):
        sample = self.sample
        spaces = {item["id"]: item for item in sample["state_spaces"]}
        for transform in sample["transformations"]:
            source = spaces[transform["source_state_space_id"]]
            target = spaces[transform["target_state_space_id"]]
            matrix = transform["matrix"]
            self.assertEqual(len(matrix), target["dimension"])
            self.assertTrue(all(len(row) == source["dimension"] for row in matrix))

        self.assertTrue(any(
            item["id"] == "boundary-of-boundary-zero" and item["status"] == "finite_tested"
            for item in sample["invariants"]
        ))
        self.assertEqual(sample["epistemic"], {
            "claim_status": "candidate",
            "finite_test_status": "passed",
            "formal_proof_status": "not_formalized",
        })
        provenance = sample["provenance"]
        self.assertRegex(provenance["source_commit"], r"^[0-9a-f]{40}$")
        self.assertTrue(provenance["source_files"])
        self.assertTrue(all(
            re.fullmatch(r"[0-9a-f]{40}", item["git_blob_sha1"])
            for item in provenance["source_files"]
        ))
        self.assertTrue(sample["evidence"])
        self.assertTrue(all(item["proof_implication"] == "none" for item in sample["evidence"]))


if __name__ == "__main__":
    unittest.main()
