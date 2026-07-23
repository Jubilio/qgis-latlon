from pathlib import Path
import ast
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "qgis_latlon"


def attribute_name(node):
    """Return a dotted name for a Python attribute expression."""
    parts = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return ".".join(reversed(parts))


class Qt6AndSnappingSourceTests(unittest.TestCase):
    def test_unscoped_dock_enums_are_not_executed(self):
        source = (PLUGIN / "dock_widget.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        attributes = {
            attribute_name(node)
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
        }
        self.assertNotIn("Qt." + "LeftDockWidgetArea", attributes)
        self.assertNotIn("Qt." + "RightDockWidgetArea", attributes)

    def test_snapping_extension_contains_vertex_and_edge_fallback(self):
        source = (PLUGIN / "plugin_v121.py").read_text(encoding="utf-8")
        self.assertIn("nearestVertex", source)
        self.assertIn("nearestEdge", source)
        self.assertIn("Qt.DockWidgetArea.RightDockWidgetArea", source)


if __name__ == "__main__":
    unittest.main()
