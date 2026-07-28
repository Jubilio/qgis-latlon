import configparser
import pathlib
import unittest

ROOT = pathlib.Path(__file__).parents[1]
PLUGIN = ROOT / "qgis_latlon"


class MetadataTests(unittest.TestCase):
    def setUp(self):
        self.parser = configparser.ConfigParser()
        self.parser.read(PLUGIN / "metadata.txt", encoding="utf-8")
        self.general = self.parser["general"]

    def test_required_metadata(self):
        for key in (
            "name", "description", "version", "author", "homepage",
            "repository", "tracker", "license",
        ):
            self.assertTrue(self.general.get(key))

    def test_version(self):
        self.assertEqual(self.general["version"], "2.0.1")

    def test_packaged_version_is_synchronised(self):
        version = (PLUGIN / "VERSION").read_text(encoding="utf-8").strip()
        changelog = (PLUGIN / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertEqual(version, self.general["version"])
        self.assertIn(f"## {version}", changelog)

    def test_submission_files(self):
        for path in (
            "__init__.py", "metadata.txt", "LICENSE", "README.md",
            "CHANGELOG.md", "VERSION", "dock_widget.py", "plugin_v121.py",
            "plugin_v124.py", "plugin_v125.py", "plugin_v126.py",
            "dock_widget_v126.py", "plugin_v130.py", "plugin_v130_policy.py",
            "dock_widget_v130.py", "search_utils.py", "plugin_v140.py",
            "dock_widget_v140.py", "match_utils.py", "plugin_v150.py",
            "dock_widget_v150.py", "gazetteer_utils.py", "plugin_v160.py",
            "dock_widget_v160.py", "review_utils.py", "plugin_v200.py",
            "plugin_v201.py", "dock_widget_v200.py", "workspace_utils.py",
            "qgis_latlon.py", "samples/offline_gazetteer_template.csv",
            "samples/workspace_candidates_template.csv",
        ):
            self.assertTrue((PLUGIN / path).exists(), path)

    def test_qgis4_project_persistence_compatibility(self):
        entrypoint = (PLUGIN / "__init__.py").read_text(encoding="utf-8")
        compatibility = (PLUGIN / "plugin_v201.py").read_text(encoding="utf-8")
        self.assertIn("GeoClickCapturePluginV201", entrypoint)
        self.assertIn("readEntry", compatibility)
        self.assertIn("writeEntry", compatibility)
        self.assertNotIn("customProperty", compatibility)
        self.assertNotIn("setCustomProperty", compatibility)

    def test_no_external_dependency_declared(self):
        self.assertIn("no external python dependencies", self.general["about"].lower())


if __name__ == "__main__":
    unittest.main()
