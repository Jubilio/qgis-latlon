"""Dock widget for GeoClick Capture."""

from __future__ import annotations

from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDockWidget,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qgis.core import QgsMapLayerProxyModel
from qgis.gui import QgsMapLayerComboBox


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
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

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
        self.layer_combo.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.layer_combo.setAllowEmptyLayer(True)
        self.layer_combo.setShowCrs(True)
        self.layer_combo.layerChanged.connect(self.destination_changed.emit)

        form.addRow("Session", self.session_edit)
        form.addRow("Operator", self.operator_edit)
        form.addRow("Category", self.category_combo)
        form.addRow("Status", self.status_combo)
        form.addRow("Note", self.note_edit)
        form.addRow("Destination", self.layer_combo)
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

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["FID", "Time", "Category", "Status", "Latitude", "Longitude", "Note"]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
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
        }

    def set_preferences(self, values):
        self.session_edit.setText(values.get("session_id", ""))
        self.operator_edit.setText(values.get("operator", ""))
        self.category_combo.setCurrentText(values.get("category", "General"))
        self.status_combo.setCurrentText(values.get("status", "Unreviewed"))

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
            rows.append((
                int(feature.id()),
                str(value("captured_at") or ""),
                str(value("category") or ""),
                str(value("status") or ""),
                str(value("lat") or ""),
                str(value("lon") or ""),
                str(value("note") or ""),
            ))
        rows.sort(key=lambda item: item[1])
        for row_values in rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for column, value in enumerate(row_values):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))
        self.table.resizeColumnsToContents()
        self.summary_label.setText(f"{len(rows)} captured point(s)")
