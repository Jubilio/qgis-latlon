import json
import pathlib
import tempfile
import unittest
import zipfile

from qgis_latlon.workspace_utils import (
    candidates_are_duplicate,
    compare_candidates,
    evidence_record,
    export_workspace_bundle,
    import_workspace_file,
    load_candidate_csv,
    new_workspace_payload,
    normalise_candidate,
    update_workspace_payload,
    upsert_candidate,
)


class WorkspaceUtilsTests(unittest.TestCase):
    def test_candidate_normalisation_and_comparison(self):
        first = normalise_candidate(
            {
                "label": "Hospital Provincial de Pemba",
                "source": "Institutional health registry",
                "source_id": "H001",
                "lat": -12.9730,
                "lon": 40.5170,
            }
        )
        second = normalise_candidate(
            {
                "label": "Pemba Provincial Hospital",
                "source": "OpenStreetMap Nominatim",
                "source_id": "OSM22",
                "lat": -12.9732,
                "lon": 40.5172,
            }
        )
        scored, summary = compare_candidates([first, second], first["candidate_id"])
        self.assertEqual(summary["candidate_count"], 2)
        self.assertEqual(summary["source_count"], 2)
        self.assertLess(summary["source_spread_m"], 50)
        self.assertEqual(summary["consensus_level"], "Strong")
        self.assertTrue(scored[0]["is_preferred"])
        self.assertGreater(scored[0]["recommendation_score"], scored[1]["recommendation_score"])

    def test_candidate_upsert(self):
        first = normalise_candidate(
            {"label": "Mueda", "source": "Official", "source_id": "MZ001", "lat": -11.67, "lon": 39.56}
        )
        updated = dict(first)
        updated["label"] = "Mueda Sede"
        values, outcome = upsert_candidate([first], updated)
        self.assertEqual(outcome, "updated")
        self.assertEqual(len(values), 1)
        self.assertEqual(values[0]["label"], "Mueda Sede")
        self.assertTrue(candidates_are_duplicate(first, updated))

    def test_evidence_hash_and_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence_path = pathlib.Path(tmp) / "photo.txt"
            evidence_path.write_text("evidence", encoding="utf-8")
            evidence = evidence_record("file", str(evidence_path), added_by="Reviewer")
            self.assertTrue(evidence["exists"])
            self.assertEqual(len(evidence["sha256"]), 64)

            workspace = new_workspace_payload()
            candidate = normalise_candidate(
                {"label": "Test", "source": "Official", "lat": -12.0, "lon": 40.0}
            )
            workspace["candidates"] = [candidate]
            workspace["evidence"] = [evidence]
            workspace["metadata"]["preferred_candidate_id"] = candidate["candidate_id"]
            workspace["metadata"]["place_name"] = "Test"
            workspace = update_workspace_payload(workspace)
            bundle_path = pathlib.Path(tmp) / "bundle.zip"
            result = export_workspace_bundle(str(bundle_path), workspace)
            self.assertEqual(result["candidate_count"], 1)
            self.assertTrue(bundle_path.exists())
            with zipfile.ZipFile(bundle_path) as archive:
                self.assertIn("workspace.json", archive.namelist())
                self.assertIn("report.html", archive.namelist())
                self.assertIn("attachments/photo.txt", archive.namelist())
            imported = import_workspace_file(str(bundle_path))
            self.assertEqual(imported["metadata"]["place_name"], "Test")
            self.assertEqual(len(imported["candidates"]), 1)

    def test_load_candidate_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "candidates.csv"
            path.write_text(
                "label,latitude,longitude,source,source_id\n"
                "Mocimboa,-11.35,40.35,Official,MZ02\n"
                "Invalid,abc,40.0,Other,X\n",
                encoding="utf-8",
            )
            records, metadata = load_candidate_csv(str(path))
            self.assertEqual(len(records), 1)
            self.assertEqual(metadata["invalid_rows"], [3])

    def test_payload_is_json_safe(self):
        workspace = update_workspace_payload(new_workspace_payload())
        text = json.dumps(workspace)
        self.assertIn("schema_version", text)


if __name__ == "__main__":
    unittest.main()
