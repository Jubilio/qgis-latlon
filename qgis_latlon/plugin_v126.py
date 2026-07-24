"""Function-specific icon integration for GeoClick Capture 1.2.6."""

from __future__ import annotations

import os

from qgis.PyQt.QtGui import QIcon

from .dock_widget_v126 import CaptureLogDockV126
from .plugin_v121 import _right_dock_area
from .plugin_v125 import GeoClickCapturePluginV125


ICON_DIR = os.path.join(os.path.dirname(__file__), "icons")


def plugin_icon(filename: str) -> QIcon:
    """Return an icon bundled with GeoClick Capture."""
    return QIcon(os.path.join(ICON_DIR, filename))


class GeoClickCapturePluginV126(GeoClickCapturePluginV125):
    """GeoClick runtime with coordinated menu and dock icons."""

    def initGui(self):
        super().initGui()
        self.capture_action.setIcon(plugin_icon("capture_point.svg"))
        self.panel_action.setIcon(plugin_icon("open_log.svg"))
        self.copy_action.setIcon(plugin_icon("session.svg"))
        self.reverse_geocode_action.setIcon(plugin_icon("reverse_geocode.svg"))

    def _create_dock(self):
        self.dock = CaptureLogDockV126(self.iface.mainWindow())
        self.iface.addDockWidget(_right_dock_area(), self.dock)
        self.dock.hide()
        self.dock.capture_toggled.connect(self.activate)
        self.dock.destination_changed.connect(self.set_destination_layer)
        self.dock.undo_requested.connect(self.undo_last_capture)
        self.dock.delete_requested.connect(self.delete_features)
        self.dock.clear_requested.connect(self.clear_session)
        self.dock.export_requested.connect(self.export_records)
        self.dock.set_preferences(self._load_preferences())
