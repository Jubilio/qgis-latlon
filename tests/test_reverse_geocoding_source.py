from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE_124 = (ROOT / "qgis_latlon" / "plugin_v124.py").read_text(encoding="utf-8")
SOURCE_125 = (ROOT / "qgis_latlon" / "plugin_v125.py").read_text(encoding="utf-8")


class ReverseGeocodingSourceTests(unittest.TestCase):
    def test_request_has_policy_and_timeout_controls(self):
        for token in (
            "RedirectPolicyAttribute",
            "NoLessSafeRedirectPolicy",
            "UserAgentHeader",
            "setTransferTimeout",
            "accept-language",
        ):
            self.assertIn(token, SOURCE_124 + SOURCE_125)

    def test_failures_are_diagnostic_and_retry_once(self):
        for token in (
            "sslErrors",
            "HTTP 403",
            "HTTP 429",
            "retrying once",
            "QgsMessageLog.logMessage",
        ):
            self.assertIn(token, SOURCE_124 + SOURCE_125)

    def test_no_result_uses_broader_osm_levels(self):
        for token in (
            "Unable to geocode",
            "ZOOM_LEVELS = (18, 15, 10, 5, 3)",
            '"layer": "address"',
            "searching for a broader area",
            "Approximate area identified",
            "saved without a place name",
        ):
            self.assertIn(token, SOURCE_125)

    def test_request_spacing_is_preserved(self):
        self.assertIn("1.1 - elapsed", SOURCE_125)

    def test_ssl_validation_is_not_bypassed(self):
        self.assertNotIn("ignoreSslErrors", SOURCE_124 + SOURCE_125)


if __name__ == "__main__":
    unittest.main()
