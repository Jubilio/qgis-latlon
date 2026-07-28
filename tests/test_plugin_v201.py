import importlib.util
import json
import pathlib
import sys
import types
import unittest

ROOT = pathlib.Path(__file__).parents[1]
MODULE_PATH = ROOT / "qgis_latlon" / "plugin_v201.py"


class FakeProject:
    current = None

    def __init__(self):
        self.entries = {}

    @classmethod
    def instance(cls):
        return cls.current

    def readEntry(self, scope, key, default):
        pair = (scope, key)
        if pair in self.entries:
            return self.entries[pair], True
        return default, False

    def writeEntry(self, scope, key, value):
        self.entries[(scope, key)] = value
        return True


def load_compatibility_module():
    module_names = (
        "qgis",
        "qgis.core",
        "qgis_latlon",
        "qgis_latlon.plugin_v200",
        "qgis_latlon.workspace_utils",
        "qgis_latlon.plugin_v201_under_test",
    )
    previous = {name: sys.modules.get(name) for name in module_names}

    try:
        qgis = types.ModuleType("qgis")
        qgis_core = types.ModuleType("qgis.core")
        qgis_core.QgsProject = FakeProject
        qgis.core = qgis_core
        sys.modules["qgis"] = qgis
        sys.modules["qgis.core"] = qgis_core

        package = types.ModuleType("qgis_latlon")
        package.__path__ = [str(ROOT / "qgis_latlon")]
        sys.modules["qgis_latlon"] = package

        parent = types.ModuleType("qgis_latlon.plugin_v200")
        parent.GeoClickCapturePluginV200 = type("GeoClickCapturePluginV200", (), {})
        sys.modules[parent.__name__] = parent

        workspace_utils = types.ModuleType("qgis_latlon.workspace_utils")
        workspace_utils.new_workspace_payload = lambda: {
            "metadata": {},
            "candidates": [],
        }
        workspace_utils.update_workspace_payload = lambda payload: dict(payload)
        sys.modules[workspace_utils.__name__] = workspace_utils

        spec = importlib.util.spec_from_file_location(
            "qgis_latlon.plugin_v201_under_test",
            MODULE_PATH,
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        for name, original in previous.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


class ProjectPersistenceCompatibilityTests(unittest.TestCase):
    def setUp(self):
        FakeProject.current = FakeProject()
        module = load_compatibility_module()
        self.plugin = module.GeoClickCapturePluginV201()

    def test_persist_workspace_uses_project_entry_api(self):
        self.plugin._workspace = {
            "metadata": {"workspace_id": "workspace-1"},
            "candidates": [{"lat": -12.3, "lon": 40.5}],
        }

        self.plugin._persist_workspace()

        raw = FakeProject.current.entries[
            ("GeoClickCapture", "locationVerificationWorkspace")
        ]
        self.assertEqual(json.loads(raw), self.plugin._workspace)

    def test_restore_workspace_uses_stored_json(self):
        expected = {
            "metadata": {"workspace_id": "workspace-2"},
            "candidates": [],
        }
        FakeProject.current.entries[
            ("GeoClickCapture", "locationVerificationWorkspace")
        ] = json.dumps(expected)

        self.plugin._restore_workspace()

        self.assertEqual(self.plugin._workspace, expected)

    def test_restore_workspace_falls_back_for_invalid_json(self):
        FakeProject.current.entries[
            ("GeoClickCapture", "locationVerificationWorkspace")
        ] = "{invalid-json"

        self.plugin._restore_workspace()

        self.assertEqual(
            self.plugin._workspace,
            {"metadata": {}, "candidates": []},
        )


if __name__ == "__main__":
    unittest.main()
