"""Icon-enhanced Capture Log dock for GeoClick Capture 1.2.6."""

from __future__ import annotations

import os

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from .dock_widget import CaptureLogDock


ICON_DIR = os.path.join(os.path.dirname(__file__), "icons")


def plugin_icon(filename: str) -> QIcon:
    """Return a bundled transparent SVG icon."""
    return QIcon(os.path.join(ICON_DIR, filename))


class CaptureLogDockV126(CaptureLogDock):
    """Capture Log dock with function-specific icons."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowIcon(plugin_icon("session.svg"))
        self.capture_button.setIcon(plugin_icon("capture_point.svg"))
        self.undo_button.setIcon(plugin_icon("undo.svg"))
        self.delete_button.setIcon(plugin_icon("delete.svg"))
        self.clear_button.setIcon(plugin_icon("delete.svg"))

        self._add_snapping_icon()

        for button in self.findChildren(QPushButton):
            if button.text() in {"CSV", "GeoJSON", "GeoPackage"}:
                button.setIcon(plugin_icon("export.svg"))

    def _add_snapping_icon(self):
        """Place the snapping artwork beside the existing checkbox."""
        container = self.widget()
        root_layout = container.layout() if container is not None else None
        form_layout = root_layout.itemAt(0).layout() if root_layout is not None else None
        if form_layout is None or not hasattr(form_layout, "getWidgetPosition"):
            return
        row, role = form_layout.getWidgetPosition(self.snapping_check)
        if row < 0:
            return
        form_layout.removeWidget(self.snapping_check)
        wrapper = QWidget(container)
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        icon_label = QLabel(wrapper)
        icon_label.setPixmap(plugin_icon("snap.svg").pixmap(20, 20))
        icon_label.setToolTip(self.snapping_check.toolTip())
        layout.addWidget(icon_label)
        layout.addWidget(self.snapping_check, 1)
        form_layout.setWidget(row, role, wrapper)
