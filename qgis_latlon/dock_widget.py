"""Dock widget for GeoClick Capture.

The UI deliberately avoids Qt 5-only enum aliases so it works with both
QGIS 3 / PyQt5 and QGIS 4 / PyQt6.
"""

from __future__ import annotations

from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDockWidget,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qgis.core import Qgis, QgsMapLayerProxyModel
from qgis.gui import QgsMapLayerComboBox


def _enum(container, legacy_name: str, scoped_name: str):
    """Return a Qt/QGIS enum value across PyQt5 and PyQt6."""
    value = getattr(container, legacy_name, None)
    if value is not None:
        return value
    scoped_container_name, member_name = scoped_name.split(".", 1)
    return getattr(getattr(container, scoped_container_name), member_name)


class CaptureLogDock(QDockWidget):
    """User interface for capture sessions and captured records."""

    capture_toggled = pyqtSignal(bool)
    destination_changed = pyqtSignal(object)
    undo_requested = pyqtSignal()
    delete_requested = pyqtSignal(list)
    clear_requested = pyqtSignal()
    export_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__("GeoClick Capture Log", parent)
        self.setObjectName("GeoClickCaptureDock")
        # QDockWidget already allows every area by default. Avoid direct use of
        # Qt.LeftDockWidgetArea/RightDockWidgetArea, which moved in PyQt6.

        container = QWidget(self)
        root = QVBoxLayout(container)

        form = QFormLayout()
        self.session_edit = QLineEdit()
        self.session_edit.setPlaceholderText("e.g. Water points verification")
        self.operator_edit = QLineEdit()
        self.operator_edit.setPlaceholderText("Operator name")
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.addItems(
            ["General", "Infrastructure", "Water point", "Road", "Settlement", "Other"]
        )
        self.status_combo = QComboBox()
        self.status_combo.addItems(
            ["Unreviewed", "Verified", "Needs verification", "Rejected"]
        )
        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText("Optional note applied to the next capture")

        self.layer_combo = QgsMapLayerComboBox()
        point_filter = getattr(QgsMapLayerProxyModel, "PointLayer", None)
        if point_filter is None:
            point_filter = Qgis.LayerFilter.PointLayer
        self.layer_combo.setFilters(point_filter)
        self.layer_combo.setAllowEmptyLayer(True)
        self.layer_combo.setShowCrs(True)
        self.layer_combo.layerChanged.connect(self.destination_changed.emit)

        self.snapping_check = QCheckBox("Snap to line/polygon vertices and segments")
        self.snapping_check.setChecked(True)
        self.snapping_check.setToolTip(
            "Uses the project snapping configuration first. When it finds no "
            "match, GeoClick searches visible line and polygon layers and "
            "prefers a nearby vertex before a segment."
        )
        self.snap_tolerance_spin = QSpinBox()
        self.snap_tolerance_spin.setRange(2, 50)
        self.snap_tolerance_spin.setValue(12)
        self.snap_tolerance_spin.setSuffix(" px")
        self.snap_tolerance_spin.setToolTip(
            "Maximum screen distance used for automatic snapping."
        )

        form.addRow("Session", self.session_edit)
        form.addRow("Operator", self.operator_edit)
        form.addRow("Category", self.category_combo)
        form.addRow("Status", self.status_combo)
        form.addRow("Note", self.note_edit)
        form.addRow("Destination", self.layer_combo)
        form.addRow("Snapping", self.snapping_check)
        form.addRow("Snap tolerance", self.snap_tolerance_spin)
        root.addLayout(form)

        capture_row = QHBoxLayout()
        self.capture_button = QPushButton("Start capture")
        self.capture_button.setCheckable(True)
        self.capture_button.toggled.connect(self._capture_state_changed)
        self.undo_button = QPushButton("Undo last")
        self.undo_button.clicked.connect(self.undo_requested.emit)
        capture_row.addWidget(self.capture_button)
        capture_row.addWidget(self.undo_button)
        root.addLayout(capture_row)

        self.summary_label = QLabel("No points captured")
        root.addWidget(self.summary_label)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            [
                "FID",
                "Time",
                "Category",
                "Status",
                "Latitude",
                "Longitude",
                "Snap",
                "Note",
            ]
        )
        self.table.setSelectionBehavior(
            _enum(QAbstractItemView, "SelectRows", "SelectionBehavior.SelectRows")
        )
        self.table.setSelectionMode(
            _enum(
                QAbstractItemView,
                "ExtendedSelection",
                "SelectionMode.ExtendedSelection",
            )
        )
        self.table.setEditTriggers(
            _enum(QAbstractItemView, "NoEditTriggers", "EditTrigger.NoEditTriggers")
        )
        self.table.hideColumn(0)
        root.addWidget(self.table)

        edit_row = QHBoxLayout()
        self.delete_button = QPushButton("Delete selected")
        self.delete_button.clicked.connect(self._emit_delete)
        self.clear_button = QPushButton("Clear session")
        self.clear_button.clicked.connect(self.clear_requested.emit)
        edit_row.addWidget(self.delete_button)
        edit_row.addWidget(self.clear_button)
        root.addLayout(edit_row)

        export_row = QHBoxLayout()
        for label, output_format in (
            ("CSV", "csv"),
            ("GeoJSON", "geojson"),
            ("GeoPackage", "gpkg"),
        ):
            button = QPushButton(label)
            button.clicked.connect(
                lambda _checked=False, fmt=output_format: self.export_requested.emit(fmt)
            )
            export_row.addWidget(button)
        root.addLayout(export_row)
        self.setWidget(container)

    def _capture_state_changed(self, enabled: bool):
        self.capture_button.setText("Stop capture" if enabled else "Start capture")
        self.capture_toggled.emit(enabled)

    def set_capture_checked(self, enabled: bool):
        self.capture_button.blockSignals(True)
        self.capture_button.setChecked(enabled)
        self.capture_button.setText("Stop capture" if enabled else "Start capture")
        self.capture_button.blockSignals(False)

    def _emit_delete(self):
        feature_ids = []
        for index in self.table.selectionModel().selectedRows():
            item = self.table.item(index.row(), 0)
            if item is not None:
                feature_ids.append(int(item.text()))
        if feature_ids:
            self.delete_requested.emit(feature_ids)

    def capture_context(self):
        return {
            "session_id": self.session_edit.text().strip(),
            "operator": self.operator_edit.text().strip(),
            "category": self.category_combo.currentText().strip() or "General",
            "status": self.status_combo.currentText().strip() or "Unreviewed",
            "note": self.note_edit.text().strip(),
            "use_snapping": self.snapping_check.isChecked(),
            "snap_tolerance_px": self.snap_tolerance_spin.value(),
        }

    def set_preferences(self, values):
        self.session_edit.setText(str(values.get("session_id", "")))
        self.operator_edit.setText(str(values.get("operator", "")))
        self.category_combo.setCurrentText(str(values.get("category", "General")))
        self.status_combo.setCurrentText(str(values.get("status", "Unreviewed")))
        self.snapping_check.setChecked(bool(values.get("use_snapping", True)))
        self.snap_tolerance_spin.setValue(int(values.get("snap_tolerance_px", 12) or 12))

    def preference_values(self):
        return self.capture_context()

    def refresh(self, layer):
        self.table.setRowCount(0)
        if layer is None or not layer.isValid():
            self.summary_label.setText("No points captured")
            return

        field_names = {field.name() for field in layer.fields()}
        rows = []
        for feature in layer.getFeatures():
            def value(name):
                return feature[name] if name in field_names else ""

            rows.append(
                (
                    int(feature.id()),
                    str(value("captured_at") or ""),
                    str(value("category") or ""),
                    str(value("status") or ""),
                    str(value("lat") or ""),
                    str(value("lon") or ""),
                    str(value("snap_type") or ""),
                    str(value("note") or ""),
                )
            )

        rows.sort(key=lambda item: item[1])
        for row_values in rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for column, value in enumerate(row_values):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))

        self.table.resizeColumnsToContents()
        self.summary_label.setText(f"{len(rows)} captured point(s)")
