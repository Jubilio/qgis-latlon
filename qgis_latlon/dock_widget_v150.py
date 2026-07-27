"""Offline Gazetteer interface for GeoClick Capture 1.5.0."""

from __future__ import annotations

from typing import Dict, List, Optional

from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
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
from qgis.core import Qgis, QgsMapLayerProxyModel
from qgis.gui import QgsMapLayerComboBox

from .dock_widget import _enum
from .dock_widget_v126 import plugin_icon
from .dock_widget_v140 import CaptureLogDockV140


class CaptureLogDockV150(CaptureLogDockV140):
    """Capture, online search, matching and offline gazetteer workspace."""

    gazetteer_csv_requested = pyqtSignal(str)
    gazetteer_layer_requested = pyqtSignal(object)
    gazetteer_search_requested = pyqtSignal(dict)
    gazetteer_action_requested = pyqtSignal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._gazetteer_results: List[Dict[str, object]] = []

        self.gazetteer_page = self._build_gazetteer_page()
        self.gazetteer_tab_index = self.tabs.addTab(
            self.gazetteer_page, plugin_icon("gazetteer.svg"), "Offline Gazetteer"
        )

    def _build_gazetteer_page(self) -> QWidget:
        page = QWidget(self)
        root = QVBoxLayout(page)

        intro = QLabel(
            "Load a local CSV or use a point layer already open in QGIS. Search official "
            "names, alternative names and P-codes without an Internet connection."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        csv_row = QHBoxLayout()
        self.gazetteer_path_edit = QLineEdit()
        self.gazetteer_path_edit.setPlaceholderText("Select an offline gazetteer CSV")
        self.gazetteer_browse_button = QPushButton("Load CSV")
        self.gazetteer_browse_button.setIcon(plugin_icon("load_gazetteer.svg"))
        self.gazetteer_browse_button.clicked.connect(self._browse_gazetteer)
        csv_row.addWidget(self.gazetteer_path_edit, 1)
        csv_row.addWidget(self.gazetteer_browse_button)
        root.addLayout(csv_row)

        layer_form = QFormLayout()
        self.gazetteer_layer_combo = QgsMapLayerComboBox()
        point_filter = getattr(QgsMapLayerProxyModel, "PointLayer", None)
        if point_filter is None:
            point_filter = Qgis.LayerFilter.PointLayer
        self.gazetteer_layer_combo.setFilters(point_filter)
        self.gazetteer_layer_combo.setAllowEmptyLayer(True)
        self.gazetteer_layer_combo.setShowCrs(True)
        self.gazetteer_use_layer_button = QPushButton("Use selected layer")
        self.gazetteer_use_layer_button.setIcon(plugin_icon("load_gazetteer.svg"))
        self.gazetteer_use_layer_button.clicked.connect(self._emit_layer_load)
        layer_form.addRow("QGIS point layer", self.gazetteer_layer_combo)
        layer_form.addRow("", self.gazetteer_use_layer_button)
        root.addLayout(layer_form)

        self.gazetteer_source_label = QLabel("No offline gazetteer is loaded.")
        self.gazetteer_source_label.setWordWrap(True)
        root.addWidget(self.gazetteer_source_label)

        search_row = QHBoxLayout()
        self.gazetteer_search_edit = QLineEdit()
        self.gazetteer_search_edit.setPlaceholderText(
            "Search a name, alternative spelling or P-code"
        )
        self.gazetteer_search_edit.returnPressed.connect(self._emit_gazetteer_search)
        self.gazetteer_search_button = QPushButton("Search offline")
        self.gazetteer_search_button.setIcon(plugin_icon("offline_search.svg"))
        self.gazetteer_search_button.clicked.connect(self._emit_gazetteer_search)
        search_row.addWidget(self.gazetteer_search_edit, 1)
        search_row.addWidget(self.gazetteer_search_button)
        root.addLayout(search_row)

        filter_form = QFormLayout()
        self.gazetteer_type_combo = QComboBox()
        self.gazetteer_type_combo.addItem("All place types", "")
        filter_form.addRow("Place type", self.gazetteer_type_combo)
        root.addLayout(filter_form)

        self.gazetteer_status = QLabel(
            "Load a CSV or QGIS point layer to enable offline search."
        )
        self.gazetteer_status.setWordWrap(True)
        root.addWidget(self.gazetteer_status)

        self.gazetteer_table = QTableWidget(0, 7)
        self.gazetteer_table.setHorizontalHeaderLabels(
            ["Name", "Type", "P-code", "Administration", "Latitude", "Longitude", "Match"]
        )
        self.gazetteer_table.setSelectionBehavior(
            _enum(QAbstractItemView, "SelectRows", "SelectionBehavior.SelectRows")
        )
        self.gazetteer_table.setSelectionMode(
            _enum(QAbstractItemView, "SingleSelection", "SelectionMode.SingleSelection")
        )
        self.gazetteer_table.setEditTriggers(
            _enum(QAbstractItemView, "NoEditTriggers", "EditTrigger.NoEditTriggers")
        )
        self.gazetteer_table.itemSelectionChanged.connect(self._update_gazetteer_actions)
        self.gazetteer_table.cellDoubleClicked.connect(
            lambda _row, _column: self._emit_gazetteer_action("zoom")
        )
        root.addWidget(self.gazetteer_table, 1)

        primary = QHBoxLayout()
        self.gazetteer_zoom_button = QPushButton("Zoom")
        self.gazetteer_zoom_button.setIcon(plugin_icon("zoom_result.svg"))
        self.gazetteer_zoom_button.clicked.connect(
            lambda: self._emit_gazetteer_action("zoom")
        )
        self.gazetteer_preview_button = QPushButton("Preview")
        self.gazetteer_preview_button.setIcon(plugin_icon("preview_result.svg"))
        self.gazetteer_preview_button.clicked.connect(
            lambda: self._emit_gazetteer_action("preview")
        )
        self.gazetteer_match_button = QPushButton("Match & verify")
        self.gazetteer_match_button.setIcon(plugin_icon("match_verify.svg"))
        self.gazetteer_match_button.clicked.connect(
            lambda: self._emit_gazetteer_action("match")
        )
        self.gazetteer_capture_button = QPushButton("Add to session")
        self.gazetteer_capture_button.setIcon(plugin_icon("gazetteer_capture.svg"))
        self.gazetteer_capture_button.clicked.connect(
            lambda: self._emit_gazetteer_action("capture")
        )
        primary.addWidget(self.gazetteer_zoom_button)
        primary.addWidget(self.gazetteer_preview_button)
        primary.addWidget(self.gazetteer_match_button)
        primary.addWidget(self.gazetteer_capture_button)
        root.addLayout(primary)

        note = QLabel(
            "Recommended CSV fields: place_id, official_name, alternative_names, "
            "place_type, pcode, latitude, longitude and administrative names."
        )
        note.setWordWrap(True)
        root.addWidget(note)

        self._set_gazetteer_controls_enabled(False)
        return page

    def _browse_gazetteer(self):
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Load offline gazetteer",
            self.gazetteer_path_edit.text().strip(),
            "CSV files (*.csv);;All files (*.*)",
        )
        if path:
            self.gazetteer_path_edit.setText(path)
            self.gazetteer_csv_requested.emit(path)

    def _emit_layer_load(self):
        layer = self.gazetteer_layer_combo.currentLayer()
        if layer is not None:
            self.gazetteer_layer_requested.emit(layer)

    def _emit_gazetteer_search(self):
        self.gazetteer_search_requested.emit(
            {
                "query": self.gazetteer_search_edit.text().strip(),
                "place_type": str(self.gazetteer_type_combo.currentData() or ""),
            }
        )

    def _emit_gazetteer_action(self, action: str):
        result = self.selected_gazetteer_result()
        if result is not None:
            self.gazetteer_action_requested.emit(action, result)

    def selected_gazetteer_result(self) -> Optional[Dict[str, object]]:
        rows = self.gazetteer_table.selectionModel().selectedRows()
        if not rows:
            return None
        row = rows[0].row()
        if 0 <= row < len(self._gazetteer_results):
            return dict(self._gazetteer_results[row])
        return None

    def show_gazetteer_tab(self):
        self.tabs.setCurrentIndex(self.gazetteer_tab_index)
        self.gazetteer_search_edit.setFocus()

    def set_gazetteer_busy(self, busy: bool, message: str = ""):
        self.gazetteer_browse_button.setEnabled(not busy)
        self.gazetteer_use_layer_button.setEnabled(not busy)
        self.gazetteer_search_button.setEnabled(not busy)
        if message:
            self.gazetteer_status.setText(message)
        if busy:
            self._set_gazetteer_actions_enabled(False)

    def set_gazetteer_source(self, metadata: Dict[str, object]):
        count = int(metadata.get("record_count", 0) or 0)
        source = str(metadata.get("source_name", "Offline gazetteer"))
        fmt = str(metadata.get("format", "QGIS layer"))
        self.gazetteer_source_label.setText(
            f"Loaded: <b>{source}</b> — {count} valid record(s) — {fmt}"
        )
        self.gazetteer_type_combo.clear()
        self.gazetteer_type_combo.addItem("All place types", "")
        for place_type in metadata.get("types", []) or []:
            text = str(place_type)
            self.gazetteer_type_combo.addItem(text, text)
        self.gazetteer_status.setText(
            "Offline gazetteer ready. Search by official name, alternative name or P-code."
        )
        self._set_gazetteer_controls_enabled(count > 0)

    def set_gazetteer_results(self, results: List[Dict[str, object]], message: str = ""):
        self._gazetteer_results = [dict(result) for result in results]
        self.gazetteer_table.setRowCount(0)
        for result in self._gazetteer_results:
            row = self.gazetteer_table.rowCount()
            self.gazetteer_table.insertRow(row)
            values = (
                str(result.get("official_name", "")),
                str(result.get("place_type", "")),
                str(result.get("pcode", "")),
                str(result.get("admin_label", "")),
                f"{float(result.get('lat', 0.0) or 0.0):.6f}",
                f"{float(result.get('lon', 0.0) or 0.0):.6f}",
                f"{float(result.get('search_score', 0.0) or 0.0) * 100:.0f}%",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in (0, 3):
                    item.setToolTip(value)
                self.gazetteer_table.setItem(row, column, item)
        self.gazetteer_table.resizeColumnsToContents()
        if self._gazetteer_results:
            self.gazetteer_table.selectRow(0)
        self.gazetteer_status.setText(
            message
            or (
                f"{len(self._gazetteer_results)} offline result(s)."
                if self._gazetteer_results
                else "No offline gazetteer result matched the query."
            )
        )
        self._update_gazetteer_actions()

    def _set_gazetteer_controls_enabled(self, enabled: bool):
        self.gazetteer_search_edit.setEnabled(enabled)
        self.gazetteer_search_button.setEnabled(enabled)
        self.gazetteer_type_combo.setEnabled(enabled)
        if not enabled:
            self._set_gazetteer_actions_enabled(False)

    def _set_gazetteer_actions_enabled(self, enabled: bool):
        for button in (
            self.gazetteer_zoom_button,
            self.gazetteer_preview_button,
            self.gazetteer_match_button,
            self.gazetteer_capture_button,
        ):
            button.setEnabled(enabled)

    def _update_gazetteer_actions(self):
        self._set_gazetteer_actions_enabled(self.selected_gazetteer_result() is not None)
