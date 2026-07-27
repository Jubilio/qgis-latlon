import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

from qgis_latlon.review_utils import (  # noqa: E402
    append_review_history,
    normalise_review_status,
    parse_review_history,
    record_matches_review_filter,
    review_status_counts,
)


class ReviewUtilsTests(unittest.TestCase):
    def test_status_normalisation(self):
        self.assertEqual(normalise_review_status("unreviewed"), "Pending")
        self.assertEqual(normalise_review_status("changes_requested"), "Needs changes")
        self.assertEqual(normalise_review_status("verified"), "Approved")
        self.assertEqual(normalise_review_status("reject"), "Rejected")

    def test_history_is_appended_without_losing_unicode(self):
        history, iteration = append_review_history(
            "",
            action="needs_changes",
            status="Needs changes",
            reviewer="Jubílio Maússe",
            comment="Confirmar a localização de Mueda.",
            timestamp="2026-07-27T13:00:00Z",
        )
        self.assertEqual(iteration, 1)
        payload = json.loads(history)
        self.assertEqual(payload[0]["reviewer"], "Jubílio Maússe")
        self.assertEqual(payload[0]["status"], "Needs changes")

        updated, iteration = append_review_history(
            history,
            action="approve",
            status="Approved",
            reviewer="Supervisor",
            comment="Corrigido.",
            timestamp="2026-07-27T14:00:00Z",
        )
        self.assertEqual(iteration, 2)
        self.assertEqual(len(parse_review_history(updated)), 2)

    def test_invalid_history_is_tolerated(self):
        self.assertEqual(parse_review_history("not-json"), [])
        self.assertEqual(parse_review_history('{"status":"Approved"}'), [])

    def test_record_filtering(self):
        record = {
            "feature_id": 7,
            "display_label": "Hospital Provincial de Pemba",
            "capture_method": "search",
            "duplicate_risk": "High",
            "review_status": "Needs changes",
            "reviewer": "Ana",
            "review_comment": "Confirmar entrada principal",
        }
        self.assertTrue(record_matches_review_filter(record, "Needs changes", "pemba"))
        self.assertTrue(record_matches_review_filter(record, "", "entrada"))
        self.assertFalse(record_matches_review_filter(record, "Approved", ""))

    def test_status_counts_include_legacy_pending(self):
        counts = review_status_counts(
            [
                {"review_status": ""},
                {"review_status": "Approved"},
                {"review_status": "Rejected"},
                {"review_status": "Needs changes"},
            ]
        )
        self.assertEqual(counts["All"], 4)
        self.assertEqual(counts["Pending"], 1)
        self.assertEqual(counts["Approved"], 1)
        self.assertEqual(counts["Rejected"], 1)
        self.assertEqual(counts["Needs changes"], 1)


if __name__ == "__main__":
    unittest.main()
