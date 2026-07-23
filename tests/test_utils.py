import importlib.util
import pathlib
import unittest

MODULE_PATH = pathlib.Path(__file__).parents[1] / "qgis_latlon" / "utils.py"
spec = importlib.util.spec_from_file_location("geoclick_utils", MODULE_PATH)
utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(utils)


class UtilsTests(unittest.TestCase):
    def test_extension_is_added(self):
        self.assertEqual(utils.ensure_extension("output", ".csv"), "output.csv")

    def test_extension_is_not_duplicated(self):
        self.assertEqual(utils.ensure_extension("output.CSV", ".csv"), "output.CSV")

    def test_dms_latitude(self):
        self.assertEqual(utils.to_dms(-12.5, "lat"), "12°30'0.00\"S")

    def test_dms_longitude(self):
        self.assertEqual(utils.to_dms(40.25, "lon"), "40°15'0.00\"E")

    def test_invalid_coordinate_type(self):
        with self.assertRaises(ValueError):
            utils.to_dms(1, "x")

    def test_session_identifier(self):
        self.assertEqual(utils.normalise_session_id("Water points / Mueda"), "Water-points-Mueda")

    def test_empty_session_identifier(self):
        self.assertTrue(utils.normalise_session_id("").startswith("session-"))

    def test_geocode_cache_key(self):
        self.assertEqual(utils.geocode_cache_key(-12.123456, 40.987654), "-12.12346,40.98765")

    def test_project_name(self):
        self.assertEqual(utils.safe_project_name("/tmp/project.qgz"), "project")


if __name__ == "__main__":
    unittest.main()
