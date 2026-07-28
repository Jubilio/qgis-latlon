"""QGIS 4 project-persistence compatibility for GeoClick Capture 2.0.1."""

from __future__ import annotations

import json

from qgis.core import QgsProject

from .plugin_v200 import GeoClickCapturePluginV200
from .workspace_utils import new_workspace_payload, update_workspace_payload

_PROJECT_SCOPE = "GeoClickCapture"
_PROJECT_KEY = "locationVerificationWorkspace"


class GeoClickCapturePluginV201(GeoClickCapturePluginV200):
    """Use the QgsProject entry API for verification-workspace persistence."""

    def _restore_workspace(self):
        raw, ok = QgsProject.instance().readEntry(
            _PROJECT_SCOPE,
            _PROJECT_KEY,
            "",
        )
        if ok and raw:
            try:
                self._workspace = update_workspace_payload(json.loads(str(raw)))
                return
            except (TypeError, ValueError, json.JSONDecodeError):
                pass
        self._workspace = update_workspace_payload(new_workspace_payload())

    def _persist_workspace(self):
        self._workspace = update_workspace_payload(self._workspace)
        QgsProject.instance().writeEntry(
            _PROJECT_SCOPE,
            _PROJECT_KEY,
            json.dumps(self._workspace, ensure_ascii=False, separators=(",", ":")),
        )
