import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from qgis_latlon.utils import ensure_extension, to_dms


class UtilsTests(unittest.TestCase):
    def test_to_dms_north(self):
        self.assertEqual(to_dms(10.5, "lat"), "10°30'00.00\"N")

    def test_to_dms_west(self):
        self.assertEqual(to_dms(-40.25, "lon"), "40°15'00.00\"W")

    def test_to_dms_rollover(self):
        self.assertEqual(to_dms(12.999999999, "lat"), "13°00'00.00\"N")

    def test_invalid_coordinate_type(self):
        with self.assertRaises(ValueError):
            to_dms(1, "x")

    def test_ensure_extension(self):
        self.assertEqual(ensure_extension("points", "csv"), "points.csv")
        self.assertEqual(ensure_extension("points.gpkg", ".gpkg"), "points.gpkg")


if __name__ == "__main__":
    unittest.main()
