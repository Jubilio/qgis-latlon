import unittest

from qgis_latlon.search_utils import (
    classify_search_input,
    normalise_nominatim_results,
    parse_coordinate_pair,
    parse_map_url,
)


class SearchInputTests(unittest.TestCase):
    def test_decimal_coordinates(self):
        self.assertEqual(parse_coordinate_pair("-12.9742, 40.5178"), (-12.9742, 40.5178))
        self.assertEqual(parse_coordinate_pair("-12.9742 40.5178"), (-12.9742, 40.5178))
        self.assertIsNone(parse_coordinate_pair("95, 40"))

    def test_openstreetmap_url(self):
        parsed = parse_map_url(
            "https://www.openstreetmap.org/?mlat=-12.9742&mlon=40.5178#map=18/-12.9742/40.5178"
        )
        self.assertEqual(parsed, (-12.9742, 40.5178, "openstreetmap_url"))

    def test_google_maps_url(self):
        parsed = parse_map_url(
            "https://www.google.com/maps/place/Pemba/@-12.9742,40.5178,16z"
        )
        self.assertEqual(parsed, (-12.9742, 40.5178, "google_maps_url"))

    def test_input_classification(self):
        coordinate = classify_search_input("-12.97, 40.52")
        self.assertEqual(coordinate["kind"], "coordinate")
        self.assertEqual(coordinate["input_format"], "decimal_coordinates")

        text = classify_search_input("Hospital Provincial de Pemba")
        self.assertEqual(text["kind"], "text")
        self.assertEqual(text["query"], "Hospital Provincial de Pemba")

    def test_nominatim_normalisation(self):
        results = normalise_nominatim_results(
            [
                {
                    "display_name": "Pemba, Mozambique",
                    "lat": "-12.97395",
                    "lon": "40.51775",
                    "type": "city",
                    "class": "place",
                    "importance": 0.61,
                    "osm_type": "relation",
                    "osm_id": 123,
                    "boundingbox": ["-13.1", "-12.8", "40.4", "40.7"],
                },
                {"display_name": "Invalid", "lat": "x", "lon": "40"},
            ]
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["provider"], "OpenStreetMap Nominatim")
        self.assertEqual(results[0]["provider_result_id"], "relation:123")
        self.assertEqual(results[0]["boundingbox"], [-13.1, -12.8, 40.4, 40.7])


if __name__ == "__main__":
    unittest.main()
