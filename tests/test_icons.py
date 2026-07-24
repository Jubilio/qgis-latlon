import pathlib
import xml.etree.ElementTree as ET
import unittest

ROOT = pathlib.Path(__file__).parents[1]
PLUGIN = ROOT / "qgis_latlon"
ICONS = (
    "capture_point.svg", "open_log.svg", "snap.svg",
    "reverse_geocode.svg", "export.svg", "undo.svg",
    "delete.svg", "session.svg",
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
        source = (PLUGIN / "plugin_v126.py").read_text(encoding="utf-8")
        dock = (PLUGIN / "dock_widget_v126.py").read_text(encoding="utf-8")
        for name in (
            "capture_point.svg", "open_log.svg", "reverse_geocode.svg",
            "session.svg",
        ):
            self.assertIn(name, source)
        for name in (
            "capture_point.svg", "snap.svg", "export.svg", "undo.svg",
            "delete.svg", "session.svg",
        ):
            self.assertIn(name, dock)


if __name__ == "__main__":
    unittest.main()
