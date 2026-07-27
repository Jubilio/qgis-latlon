"""Tabbed Search & Capture interface for GeoClick Capture 1.3.0."""

from __future__ import annotations

from typing import Dict, List, Optional

from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .dock_widget import _enum
from .dock_widget_v126 import CaptureLogDockV126, plugin_icon


class CaptureLogDockV130(CaptureLogDockV126):
    """Capture Log with a dedicated Search & Capture tab."""

    search_requested = pyqtSignal(dict)
    search_action_requested = pyqtSignal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._search_results: List[Dict[str, object]] = []

        capture_page = self.widget()
        if capture_page is not None:
            capture_page.setParent(None)

        self.tabs = QTabWidget(self)
        self.tabs.setDocumentMode(True)
        self.capture_tab_index = self.tabs.addTab(
            capture_page, plugin_icon("capture_point.svg"), "Capture Log"
        )
        self.search_page = self._build_search_page()
        self.search_tab_index = self.tabs.addTab(
            self.search_page, plugin_icon("search_place.svg"), "Search & Capture"
        )
        self.setWidget(self.tabs)
        self.setWindowIcon(plugin_icon("session.svg"))

    def _build_search_page(self) -> QWidget:
        page = QWidget(self)
        root = QVBoxLayout(page)

        intro = QLabel(
            "Find a place by address or name, paste decimal coordinates, or paste "
            "an OpenStreetMap/Google Maps URL. Review the result before adding it "
            "to the active capture session."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        query_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(
            "e.g. Hospital Provincial de Pemba, -12.97, 40.52, or a map URL"
        )
        self.search_edit.returnPressed.connect(self._emit_search)
        self.search_button = QPushButton("Search")
        self.search_button.setIcon(plugin_icon("search_place.svg"))
        self.search_button.clicked.connect(self._emit_search)
        query_row.addWidget(self.search_edit, 1)
        query_row.addWidget(self.search_button)
        root.addLayout(query_row)

        options = QFormLayout()
        self.country_edit = QLineEdit("mz")
        self.country_edit.setMaxLength(8)
        self.country_edit.setPlaceholderText("ISO country code, e.g. mz")
        self.country_edit.setToolTip(
            "Optional comma-separated ISO 3166-1 alpha-2 country codes. "
            "Clear this field to search worldwide."
        )
        self.extent_check = QCheckBox("Restrict text search to the current map extent")
        self.extent_check.setChecked(False)
        self.extent_check.setToolTip(
            "Adds a bounded Nominatim viewbox based on the visible QGIS map extent."
        )
        options.addRow("Country", self.country_edit)
        options.addRow("Map extent", self.extent_check)
        root.addLayout(options)

        self.search_status = QLabel("Enter a place, coordinate pair or map URL.")
        self.search_status.setWordWrap(True)
        root.addWidget(self.search_status)

        self.results_table = QTableWidget(0, 5)
        self.results_table.setHorizontalHeaderLabels(
            ["Place", "Type", "Latitude", "Longitude", "Confidence"]
        )
        self.results_table.setSelectionBehavior(
            _enum(QAbstractItemView, "SelectRows", "SelectionBehavior.SelectRows")
        )
        self.results_table.setSelectionMode(
            _enum(QAbstractItemView, "SingleSelection", "SelectionMode.SingleSelection")
        )
        self.results_table.setEditTriggers(
            _enum(QAbstractItemView, "NoEditTriggers", "EditTrigger.NoEditTriggers")
        )
        self.results_table.cellDoubleClicked.connect(
            lambda _row, _column: self._emit_result_action("zoom")
        )
        root.addWidget(self.results_table, 1)

        primary_actions = QHBoxLayout()
        self.zoom_button = QPushButton("Zoom")
        self.zoom_button.setIcon(plugin_icon("zoom_result.svg"))
        self.zoom_button.clicked.connect(lambda: self._emit_result_action("zoom"))
        self.preview_button = QPushButton("Preview")
        self.preview_button.setIcon(plugin_icon("preview_result.svg"))
        self.preview_button.clicked.connect(lambda: self._emit_result_action("preview"))
        self.capture_result_button = QPushButton("Add to session")
        self.capture_result_button.setIcon(plugin_icon("capture_search.svg"))
        self.capture_result_button.clicked.connect(
            lambda: self._emit_result_action("capture")
        )
        primary_actions.addWidget(self.zoom_button)
        primary_actions.addWidget(self.preview_button)
        primary_actions.addWidget(self.capture_result_button)
        root.addLayout(primary_actions)

        secondary_actions = QHBoxLayout()
        self.copy_result_button = QPushButton("Copy coordinates")
        self.copy_result_button.setIcon(plugin_icon("copy_coordinates.svg"))
        self.copy_result_button.clicked.connect(
            lambda: self._emit_result_action("copy")
        )
        self.osm_button = QPushButton("Open OSM")
        self.osm_button.setIcon(plugin_icon("open_osm.svg"))
        self.osm_button.clicked.connect(lambda: self._emit_result_action("open_osm"))
        self.google_button = QPushButton("Open Google Maps")
        self.google_button.setIcon(plugin_icon("open_google_maps.svg"))
        self.google_button.clicked.connect(
            lambda: self._emit_result_action("open_google")
        )
        secondary_actions.addWidget(self.copy_result_button)
        secondary_actions.addWidget(self.osm_button)
        secondary_actions.addWidget(self.google_button)
        root.addLayout(secondary_actions)

        attribution = QLabel("Search provider: © OpenStreetMap contributors / Nominatim")
        attribution.setWordWrap(True)
        root.addWidget(attribution)

        self._set_result_actions_enabled(False)
        return page

    def show_search_tab(self):
        """Open the search tab and focus its input."""
        self.tabs.setCurrentIndex(self.search_tab_index)
        self.search_edit.setFocus()
        self.search_edit.selectAll()

    def _emit_search(self):
        query = self.search_edit.text().strip()
        self.search_requested.emit(
            {
                "query": query,
                "countrycodes": self.country_edit.text().strip().lower(),
                "restrict_to_extent": self.extent_check.isChecked(),
            }
        )

    def _emit_result_action(self, action: str):
        result = self.selected_search_result()
        if result is not None:
            self.search_action_requested.emit(action, result)

    def selected_search_result(self) -> Optional[Dict[str, object]]:
        selection = self.results_table.selectionModel().selectedRows()
        if not selection:
            return None
        row = selection[0].row()
        if 0 <= row < len(self._search_results):
            return dict(self._search_results[row])
        return None

    def set_search_busy(self, busy: bool, message: str = ""):
        self.search_button.setEnabled(not busy)
        self.search_edit.setEnabled(not busy)
        if message:
            self.search_status.setText(message)
        if busy:
            self._set_result_actions_enabled(False)

    def set_search_message(self, message: str):
        self.search_status.setText(message)

    def set_search_results(self, results: List[Dict[str, object]], message: str = ""):
        self._search_results = [dict(result) for result in results]
        self.results_table.setRowCount(0)
        for result in self._search_results:
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)
            importance = float(result.get("importance", 0.0) or 0.0)
            values = (
                str(result.get("display_name", "")),
                str(result.get("result_type", "")),
                f"{float(result.get('lat', 0.0)):.6f}",
                f"{float(result.get('lon', 0.0)):.6f}",
                f"{importance * 100:.0f}%" if importance > 0 else "Direct input",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setToolTip(value)
                self.results_table.setItem(row, column, item)

        self.results_table.resizeColumnsToContents()
        if self._search_results:
            self.results_table.selectRow(0)
        self._set_result_actions_enabled(bool(self._search_results))
        self.search_status.setText(
            message
            or (
                f"{len(self._search_results)} result(s). Select one to zoom, preview "
                "or add it to the capture session."
                if self._search_results
                else "No matching place was found."
            )
        )

    def _set_result_actions_enabled(self, enabled: bool):
        for button in (
            self.zoom_button,
            self.preview_button,
            self.capture_result_button,
            self.copy_result_button,
            self.osm_button,
            self.google_button,
        ):
            button.setEnabled(enabled)
