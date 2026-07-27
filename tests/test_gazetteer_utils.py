import csv
import pathlib
import tempfile
import unittest

from qgis_latlon.gazetteer_utils import (
    detect_columns,
    load_csv_gazetteer,
    normalise_record,
    parse_aliases,
    search_gazetteer,
)


class GazetteerUtilityTests(unittest.TestCase):
    def test_detect_columns(self):
        mapping = detect_columns(["Site_ID", "Official_Name", "Aliases", "P_CODE", "Lat", "Lon"])
        self.assertEqual(mapping["record_id"], "Site_ID")
        self.assertEqual(mapping["official_name"], "Official_Name")
        self.assertEqual(mapping["alternative_names"], "Aliases")
        self.assertEqual(mapping["pcode"], "P_CODE")

    def test_parse_aliases(self):
        self.assertEqual(parse_aliases("Mbau; Mbaw | MBAU"), ["Mbau", "Mbaw"])

    def test_normalise_and_search(self):
        mapping = detect_columns(
            ["id", "name", "aliases", "pcode", "lat", "lon", "type", "district"]
        )
        record = normalise_record(
            {
                "id": "1",
                "name": "Hospital Provincial de Pemba",
                "aliases": "Pemba Provincial Hospital; HPP",
                "pcode": "MZ-H-001",
                "lat": "-12.9742",
                "lon": "40.5178",
                "type": "health facility",
                "district": "Pemba",
            },
            mapping,
            "test.csv",
            2,
        )
        self.assertIsNotNone(record)
        results = search_gazetteer([record], "Pemba Provincial Hospital")
        self.assertEqual(results[0]["record_id"], "1")
        self.assertGreater(results[0]["search_score"], 0.8)
        pcode = search_gazetteer([record], "MZ-H-001")
        self.assertEqual(pcode[0]["search_score"], 1.0)

    def test_load_csv(self):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "gazetteer.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["name", "lat", "lon", "pcode"])
                writer.writeheader()
                writer.writerow({"name": "Mueda", "lat": "-11.67", "lon": "39.56", "pcode": "MZ0101"})
            records, metadata = load_csv_gazetteer(str(path))
        self.assertEqual(len(records), 1)
        self.assertEqual(metadata["format"], "CSV")
        self.assertEqual(records[0]["official_name"], "Mueda")

    def test_invalid_coordinates_are_skipped(self):
        mapping = detect_columns(["name", "lat", "lon"])
        record = normalise_record(
            {"name": "Invalid", "lat": "95", "lon": "40"}, mapping, "test", 2
        )
        self.assertIsNone(record)


if __name__ == "__main__":
    unittest.main()
