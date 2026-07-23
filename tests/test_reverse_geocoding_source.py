from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "qgis_latlon" / "plugin_v124.py").read_text(encoding="utf-8")


class ReverseGeocodingSourceTests(unittest.TestCase):
    def test_request_has_policy_and_timeout_controls(self):
        for token in (
            "RedirectPolicyAttribute",
            "NoLessSafeRedirectPolicy",
            "UserAgentHeader",
            "setTransferTimeout",
            "accept-language",
        ):
            self.assertIn(token, SOURCE)

    def test_failures_are_diagnostic_and_retry_once(self):
        for token in (
            "sslErrors",
            "HTTP 403",
            "HTTP 429",
            "retrying once",
            "QgsMessageLog.logMessage",
        ):
            self.assertIn(token, SOURCE)

    def test_ssl_validation_is_not_bypassed(self):
        self.assertNotIn("ignoreSslErrors", SOURCE)


if __name__ == "__main__":
    unittest.main()
