import configparser
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "qgis_latlon"


class MetadataTests(unittest.TestCase):
    def setUp(self):
        self.parser = configparser.ConfigParser()
        self.parser.read(PLUGIN / "metadata.txt", encoding="utf-8")
        self.general = self.parser["general"]

    def test_required_submission_fields(self):
        required = {
            "name", "description", "about", "version", "author", "email",
            "qgisminimumversion", "repository", "homepage", "tracker", "license",
        }
        self.assertTrue(required.issubset(set(self.general.keys())))

    def test_submission_files_are_packaged(self):
        for filename in ("__init__.py", "metadata.txt", "LICENSE", "README.md"):
            self.assertTrue((PLUGIN / filename).is_file(), filename)

    def test_links_are_public_github_links(self):
        for key in ("homepage", "repository", "tracker"):
            self.assertTrue(self.general[key].startswith("https://github.com/Jubilio/qgis-latlon"))


if __name__ == "__main__":
    unittest.main()
