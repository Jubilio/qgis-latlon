import unittest

from qgis_latlon.match_utils import (
    best_name_match,
    duplicate_risk,
    match_confidence,
    normalise_name,
    sort_candidates,
    token_similarity,
)


class MatchUtilityTests(unittest.TestCase):
    def test_name_normalisation_removes_accents_and_punctuation(self):
        self.assertEqual(normalise_name("Hospital Provincial de Pémba"), "hospital provincial de pemba")
        self.assertEqual(normalise_name("  Centro--de Saúde! "), "centro de saude")

    def test_token_similarity_handles_word_order_and_abbreviated_labels(self):
        reordered = token_similarity("Pemba Provincial Hospital", "Hospital Provincial de Pemba")
        unrelated = token_similarity("Hospital Provincial de Pemba", "Escola Secundária de Mueda")
        self.assertGreater(reordered, 0.70)
        self.assertLess(unrelated, 0.45)

    def test_best_name_match_uses_the_strongest_attribute(self):
        result = best_name_match(
            "Hospital Provincial de Pemba",
            ["HP Pemba", "Hospital Provincial de Pemba", "health_0042"],
        )
        self.assertEqual(result["value"], "Hospital Provincial de Pemba")
        self.assertGreaterEqual(result["score"], 0.99)

    def test_confidence_is_explainable_and_bounded(self):
        strong = match_confidence(0.90, 10.0, 500.0)
        weak = match_confidence(0.30, 450.0, 500.0)
        self.assertGreater(strong, weak)
        self.assertGreaterEqual(strong, 0.0)
        self.assertLessEqual(strong, 100.0)

    def test_duplicate_risk_thresholds(self):
        self.assertEqual(duplicate_risk(0.90, 10.0, 500.0), "High")
        self.assertEqual(duplicate_risk(0.65, 150.0, 500.0), "Medium")
        self.assertEqual(duplicate_risk(0.20, 400.0, 500.0), "Low")

    def test_candidate_sorting_prioritises_risk_then_confidence(self):
        ordered = sort_candidates(
            [
                {"candidate_label": "Low", "duplicate_risk": "Low", "confidence_score": 90, "distance_m": 5},
                {"candidate_label": "Medium", "duplicate_risk": "Medium", "confidence_score": 60, "distance_m": 20},
                {"candidate_label": "High", "duplicate_risk": "High", "confidence_score": 80, "distance_m": 15},
            ]
        )
        self.assertEqual([item["candidate_label"] for item in ordered], ["High", "Medium", "Low"])


if __name__ == "__main__":
    unittest.main()
