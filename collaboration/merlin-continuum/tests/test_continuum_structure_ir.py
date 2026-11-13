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
        self.assertTrue(required.issubset(schema["properties"]))
        self.assertTrue(required.issubset(sample))
        self.assertTrue(set(sample).issubset(schema["properties"]))
        self.assertEqual(sample["schema_version"], 1)
        self.assertEqual(sample["version"], "1.0.0")


    def test_n_ality_axes_are_independent_and_geometric_axis_is_consistent(self):
        signature = self.sample["n_ality"]
        self.assertEqual(set(signature), {
            "geometric_dimension",
            "state_dimension",
            "logical_dimension",
            "temporal_dimension",
        })
        self.assertEqual(
            signature["geometric_dimension"],
            self.sample["geometry"]["dimension"],
        )
        self.assertEqual(
            signature["state_dimension"],
            self.sample["state_spaces"][0]["dimension"],
        )
        self.assertGreaterEqual(signature["logical_dimension"], 1)
        self.assertGreaterEqual(signature["temporal_dimension"], 0)

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


    def test_explicit_endpoint_gluing_is_typed_and_provenance_bound(self):
        sample = self.sample
        fields = {item["id"]: item for item in sample["edge_fields"]}
        cells = {item["id"]: item for item in sample["cells"]}
        endpoint_ids = set()
        for gluing in sample["endpoint_gluing"]:
            self.assertNotIn(gluing["endpoint_id"], endpoint_ids)
            endpoint_ids.add(gluing["endpoint_id"])
            self.assertGreaterEqual(len(gluing["bindings"]), 2)
            self.assertGreaterEqual(gluing["tolerance"], 0)
            self.assertEqual(gluing["compatibility"], "componentwise_absolute")
            self.assertTrue(gluing["provenance"])
            for binding in gluing["bindings"]:
                field = fields[binding["edge_field_id"]]
                points = [p for p in field["samples"] if p.get("sample_id") == binding["sample_id"]]
                self.assertEqual(len(points), 1)
                point = points[0]
                self.assertEqual(point["parameter"], binding["parameter"])
                self.assertEqual(point["value"], binding["value"])
                cell = cells[field["cell_id"]]
                expected_vertex = cell["vertex_ids"][0 if binding["parameter"] == 0 else -1]
                self.assertEqual(expected_vertex, gluing["endpoint_id"])
        self.assertEqual(endpoint_ids, {"A", "B", "C"})



    def test_cells_can_attach_heterogeneous_state_spaces(self):
        sample = json.loads(json.dumps(self.sample))
        sample["state_spaces"].append({
            "id": "R3-face",
            "kind": "real_vector",
            "dimension": 3,
            "scalar_field": "R",
            "semantics": "Three independent real channels on the 2-cell."
        })
        cells = {item["id"]: item for item in sample["cells"]}
        cells["ABC"]["state_space_id"] = "R3-face"

        spaces = {item["id"]: item for item in sample["state_spaces"]}
        self.assertEqual(len(spaces), 2)
        for cell in cells.values():
            self.assertIn(cell["state_space_id"], spaces)
        for edge_field in sample["edge_fields"]:
            cell = cells[edge_field["cell_id"]]
            self.assertEqual(edge_field["state_space_id"], cell["state_space_id"])
            dimension = spaces[edge_field["state_space_id"]]["dimension"]
            self.assertTrue(all(len(point["value"]) == dimension
                                for point in edge_field["samples"]))

        # The face may use a different carrier from its boundary edges.
        self.assertEqual(spaces[cells["AB"]["state_space_id"]]["dimension"], 2)
        self.assertEqual(spaces[cells["ABC"]["state_space_id"]]["dimension"], 3)

    def test_transformations_allow_dimension_changing_maps_but_check_shape(self):
        spaces = {
            "R2": {"dimension": 2},
            "R3": {"dimension": 3},
        }
        transform = {
            "source_state_space_id": "R2",
            "target_state_space_id": "R3",
            "matrix": [[1, 0], [0, 1], [1, 1]],
        }
        source = spaces[transform["source_state_space_id"]]
        target = spaces[transform["target_state_space_id"]]
        matrix = transform["matrix"]
        self.assertEqual(len(matrix), target["dimension"])
        self.assertTrue(all(len(row) == source["dimension"] for row in matrix))

        malformed = [[1, 0], [0, 1], [1]]
        self.assertEqual(len(malformed), target["dimension"])
        self.assertFalse(all(len(row) == source["dimension"] for row in malformed))

    def test_unknown_cell_state_space_reference_is_rejected(self):
        sample = json.loads(json.dumps(self.sample))
        known = {item["id"] for item in sample["state_spaces"]}
        sample["cells"][0]["state_space_id"] = "missing-space"
        self.assertNotIn(sample["cells"][0]["state_space_id"], known)


if __name__ == "__main__":
    unittest.main()
