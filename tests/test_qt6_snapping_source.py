from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "qgis_latlon"


class Qt6AndSnappingSourceTests(unittest.TestCase):
    def test_qt5_only_dock_enums_are_not_used(self):
        source = (PLUGIN / "dock_widget.py").read_text(encoding="utf-8")
        self.assertNotIn("Qt.LeftDockWidgetArea", source)
        self.assertNotIn("Qt.RightDockWidgetArea", source)

    def test_snapping_extension_contains_vertex_and_edge_fallback(self):
        source = (PLUGIN / "plugin_v121.py").read_text(encoding="utf-8")
        self.assertIn("nearestVertex", source)
        self.assertIn("nearestEdge", source)
        self.assertIn("Qt.DockWidgetArea.RightDockWidgetArea", source)


if __name__ == "__main__":
    unittest.main()
