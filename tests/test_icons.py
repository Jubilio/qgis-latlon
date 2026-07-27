import pathlib
import xml.etree.ElementTree as ET
import unittest

ROOT = pathlib.Path(__file__).parents[1]
PLUGIN = ROOT / "qgis_latlon"
ICONS = (
    "capture_point.svg", "open_log.svg", "snap.svg",
    "reverse_geocode.svg", "export.svg", "undo.svg",
    "delete.svg", "session.svg", "search_place.svg",
    "zoom_result.svg", "preview_result.svg", "capture_search.svg",
    "copy_coordinates.svg", "open_osm.svg", "open_google_maps.svg",
    "match_verify.svg", "scan_candidates.svg", "zoom_existing.svg",
    "use_existing.svg", "create_new.svg", "duplicate_warning.svg",
)


class IconTests(unittest.TestCase):
    def test_icons_are_small_valid_svgs(self):
        for name in ICONS:
            path = PLUGIN / "icons" / name
            self.assertTrue(path.exists(), name)
            self.assertLess(path.stat().st_size, 20_000, name)
            root = ET.parse(path).getroot()
            self.assertTrue(root.tag.endswith("svg"), name)
            self.assertEqual(root.attrib.get("viewBox"), "0 0 64 64", name)

    def test_runtime_references_function_icons(self):
        search_source = (PLUGIN / "plugin_v130.py").read_text(encoding="utf-8")
        search_dock = (PLUGIN / "dock_widget_v130.py").read_text(encoding="utf-8")
        match_source = (PLUGIN / "plugin_v140.py").read_text(encoding="utf-8")
        match_dock = (PLUGIN / "dock_widget_v140.py").read_text(encoding="utf-8")
        for name in ("search_place.svg", "capture_point.svg"):
            self.assertIn(name, search_source + search_dock)
        for name in (
            "zoom_result.svg", "preview_result.svg", "capture_search.svg",
            "copy_coordinates.svg", "open_osm.svg", "open_google_maps.svg",
        ):
            self.assertIn(name, search_dock)
        for name in (
            "match_verify.svg", "scan_candidates.svg", "zoom_existing.svg",
            "use_existing.svg", "create_new.svg", "duplicate_warning.svg",
        ):
            self.assertIn(name, match_source + match_dock)


if __name__ == "__main__":
    unittest.main()
