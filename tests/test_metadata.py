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
        self.assertEqual(self.general["version"], "1.2.3")

    def test_submission_files(self):
        for path in (
            "__init__.py", "metadata.txt", "LICENSE", "README.md",
            "dock_widget.py", "plugin_v121.py", "qgis_latlon.py",
        ):
            self.assertTrue((PLUGIN / path).exists(), path)

    def test_no_external_dependency_declared(self):
        self.assertIn("no external python dependencies", self.general["about"].lower())


if __name__ == "__main__":
    unittest.main()
