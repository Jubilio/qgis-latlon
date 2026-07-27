"""Match & Verify interface for GeoClick Capture 1.4.0."""

from __future__ import annotations

from typing import Dict, List, Optional

from qgis.PyQt.QtCore import QVariant, pyqtSignal
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qgis.core import Qgis, QgsMapLayerProxyModel
from qgis.gui import QgsMapLayerComboBox

from .dock_widget import _enum
from .dock_widget_v126 import plugin_icon
from .dock_widget_v130 import CaptureLogDockV130


class CaptureLogDockV140(CaptureLogDockV130):
    """Capture, search and duplicate-verification workspace."""

    verify_requested = pyqtSignal(dict)
    verify_action_requested = pyqtSignal(str, dict, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._match_source_result: Dict[str, object] = {}
        self._match_candidates: List[Dict[str, object]] = []

        self.match_result_button = QPushButton("Match & verify")
        self.match_result_button.setIcon(plugin_icon("match_verify.svg"))
        self.match_result_button.setToolTip(
            "Compare the selected search result with existing point features before capture"
        )
        self.match_result_button.clicked.connect(
            lambda: self._emit_result_action("match")
        )
        self.match_result_button.setEnabled(False)
        self.search_page.layout().insertWidget(
            max(0, self.search_page.layout().count() - 1), self.match_result_button
        )

        self.match_page = self._build_match_page()
        self.match_tab_index = self.tabs.addTab(
            self.match_page, plugin_icon("match_verify.svg"), "Match & Verify"
        )

    def _build_match_page(self) -> QWidget:
        page = QWidget(self)
        root = QVBoxLayout(page)

        intro = QLabel(
            "Compare a searched place with existing point layers. The analysis combines "
            "name similarity and distance, then records the final decision in the audit log."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        self.match_source_label = QLabel("No search result selected.")
        self.match_source_label.setWordWrap(True)
        root.addWidget(self.match_source_label)

        options = QFormLayout()
        self.scan_all_check = QCheckBox("Scan all visible point layers")
        self.scan_all_check.setChecked(True)
        self.scan_all_check.toggled.connect(self._toggle_layer_controls)

        self.match_layer_combo = QgsMapLayerComboBox()
        point_filter = getattr(QgsMapLayerProxyModel, "PointLayer", None)
        if point_filter is None:
            point_filter = Qgis.LayerFilter.PointLayer
        self.match_layer_combo.setFilters(point_filter)
        self.match_layer_combo.setAllowEmptyLayer(True)
        self.match_layer_combo.setShowCrs(True)
        self.match_layer_combo.layerChanged.connect(self._populate_name_fields)

        self.name_field_combo = QComboBox()
        self.name_field_combo.addItem("Automatic text-field matching", "")

        self.match_radius_spin = QDoubleSpinBox()
        self.match_radius_spin.setRange(10.0, 50000.0)
        self.match_radius_spin.setDecimals(0)
        self.match_radius_spin.setValue(500.0)
        self.match_radius_spin.setSuffix(" m")

        self.minimum_name_spin = QSpinBox()
        self.minimum_name_spin.setRange(0, 100)
        self.minimum_name_spin.setValue(40)
        self.minimum_name_spin.setSuffix("%")

        options.addRow("Scope", self.scan_all_check)
        options.addRow("Candidate layer", self.match_layer_combo)
        options.addRow("Name field", self.name_field_combo)
        options.addRow("Search radius", self.match_radius_spin)
        options.addRow("Minimum name match", self.minimum_name_spin)
        root.addLayout(options)

        self.scan_candidates_button = QPushButton("Analyse nearby features")
        self.scan_candidates_button.setIcon(plugin_icon("scan_candidates.svg"))
        self.scan_candidates_button.clicked.connect(self._emit_verify)
        self.scan_candidates_button.setEnabled(False)
        root.addWidget(self.scan_candidates_button)

        self.match_status = QLabel(
            "Choose Match & verify from a search result to begin."
        )
        self.match_status.setWordWrap(True)
        root.addWidget(self.match_status)

        self.match_table = QTableWidget(0, 7)
        self.match_table.setHorizontalHeaderLabels(
            [
                "Candidate",
                "Layer",
                "Feature ID",
                "Distance",
                "Name match",
                "Confidence",
                "Risk",
            ]
        )
        self.match_table.setSelectionBehavior(
            _enum(QAbstractItemView, "SelectRows", "SelectionBehavior.SelectRows")
        )
        self.match_table.setSelectionMode(
            _enum(QAbstractItemView, "SingleSelection", "SelectionMode.SingleSelection")
        )
        self.match_table.setEditTriggers(
            _enum(QAbstractItemView, "NoEditTriggers", "EditTrigger.NoEditTriggers")
        )
        self.match_table.itemSelectionChanged.connect(self._update_match_actions)
        self.match_table.cellDoubleClicked.connect(
            lambda _row, _column: self._emit_match_action("zoom_existing")
        )
        root.addWidget(self.match_table, 1)

        actions = QHBoxLayout()
        self.zoom_existing_button = QPushButton("Zoom existing")
        self.zoom_existing_button.setIcon(plugin_icon("zoom_existing.svg"))
        self.zoom_existing_button.clicked.connect(
            lambda: self._emit_match_action("zoom_existing")
        )
        self.use_existing_button = QPushButton("Use existing")
        self.use_existing_button.setIcon(plugin_icon("use_existing.svg"))
        self.use_existing_button.clicked.connect(
            lambda: self._emit_match_action("use_existing")
        )
        self.create_new_button = QPushButton("Create new")
        self.create_new_button.setIcon(plugin_icon("create_new.svg"))
        self.create_new_button.clicked.connect(
            lambda: self._emit_match_action("create_new")
        )
        actions.addWidget(self.zoom_existing_button)
        actions.addWidget(self.use_existing_button)
        actions.addWidget(self.create_new_button)
        root.addLayout(actions)

        warning_row = QHBoxLayout()
        warning_icon = QLabel()
        warning_icon.setPixmap(plugin_icon("duplicate_warning.svg").pixmap(22, 22))
        warning_icon.setToolTip("Possible duplicate warning")
        self.duplicate_note = QLabel(
            "High-risk matches are spatially very close and have strongly similar "
            "names. The plugin never chooses automatically; the user records the decision."
        )
        self.duplicate_note.setWordWrap(True)
        self.duplicate_note.setToolTip(
            "Duplicate risk combines distance and name similarity using documented thresholds."
        )
        warning_row.addWidget(warning_icon)
        warning_row.addWidget(self.duplicate_note, 1)
        root.addLayout(warning_row)

        self._toggle_layer_controls(True)
        self._update_match_actions()
        return page

    def set_search_results(self, results: List[Dict[str, object]], message: str = ""):
        super().set_search_results(results, message)
        self.match_result_button.setEnabled(bool(results))

    def prepare_match(self, result: Dict[str, object]):
        self._match_source_result = dict(result)
        self._match_candidates = []
        label = str(result.get("display_name", "Selected place"))
        lat = float(result.get("lat", 0.0) or 0.0)
        lon = float(result.get("lon", 0.0) or 0.0)
        self.match_source_label.setText(
            f"Source: {label}<br><b>{lat:.6f}, {lon:.6f}</b>"
        )
        self.match_table.setRowCount(0)
        self.match_status.setText(
            "Configure the radius and candidate scope, then analyse nearby features."
        )
        self.scan_candidates_button.setEnabled(True)
        self.tabs.setCurrentIndex(self.match_tab_index)
        self._update_match_actions()

    def show_match_tab(self):
        self.tabs.setCurrentIndex(self.match_tab_index)

    def _toggle_layer_controls(self, scan_all: bool):
        self.match_layer_combo.setEnabled(not scan_all)
        self.name_field_combo.setEnabled(not scan_all)
        if not scan_all:
            self._populate_name_fields(self.match_layer_combo.currentLayer())

    def _populate_name_fields(self, layer):
        self.name_field_combo.clear()
        self.name_field_combo.addItem("Automatic text-field matching", "")
        if layer is None or not layer.isValid():
            return
        for field in layer.fields():
            if field.type() != QVariant.String:
                continue
            self.name_field_combo.addItem(field.name(), field.name())

    def _emit_verify(self):
        if not self._match_source_result:
            return
        self.verify_requested.emit(
            {
                "source": dict(self._match_source_result),
                "scan_all_visible": self.scan_all_check.isChecked(),
                "layer": self.match_layer_combo.currentLayer(),
                "name_field": str(self.name_field_combo.currentData() or ""),
                "radius_m": float(self.match_radius_spin.value()),
                "minimum_name_score": float(self.minimum_name_spin.value()) / 100.0,
            }
        )

    def _emit_match_action(self, action: str):
        source = dict(self._match_source_result)
        candidate = self.selected_match_candidate() or {}
        if source:
            self.verify_action_requested.emit(action, source, candidate)

    def selected_match_candidate(self) -> Optional[Dict[str, object]]:
        rows = self.match_table.selectionModel().selectedRows()
        if not rows:
            return None
        row = rows[0].row()
        if 0 <= row < len(self._match_candidates):
            return dict(self._match_candidates[row])
        return None

    def set_match_busy(self, busy: bool, message: str = ""):
        self.scan_candidates_button.setEnabled(not busy and bool(self._match_source_result))
        if message:
            self.match_status.setText(message)
        if busy:
            self.zoom_existing_button.setEnabled(False)
            self.use_existing_button.setEnabled(False)

    def set_match_results(self, candidates: List[Dict[str, object]], message: str = ""):
        self._match_candidates = [dict(candidate) for candidate in candidates]
        self.match_table.setRowCount(0)
        for candidate in self._match_candidates:
            row = self.match_table.rowCount()
            self.match_table.insertRow(row)
            values = (
                str(candidate.get("candidate_label", "")),
                str(candidate.get("layer_name", "")),
                str(candidate.get("feature_id", "")),
                f"{float(candidate.get('distance_m', 0.0) or 0.0):.1f} m",
                f"{float(candidate.get('name_similarity', 0.0) or 0.0) * 100:.0f}%",
                f"{float(candidate.get('confidence_score', 0.0) or 0.0):.0f}/100",
                str(candidate.get("duplicate_risk", "Low")),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setToolTip(value)
                self.match_table.setItem(row, column, item)
        self.match_table.resizeColumnsToContents()
        if self._match_candidates:
            self.match_table.selectRow(0)
        self.match_status.setText(
            message
            or (
                f"{len(self._match_candidates)} possible match(es). Review the evidence "
                "before choosing Use existing or Create new."
                if self._match_candidates
                else "No candidate met the configured spatial and name thresholds."
            )
        )
        self._update_match_actions()

    def _update_match_actions(self):
        has_source = bool(getattr(self, "_match_source_result", {}))
        has_candidate = self.selected_match_candidate() is not None
        self.zoom_existing_button.setEnabled(has_candidate)
        self.use_existing_button.setEnabled(has_candidate)
        self.create_new_button.setEnabled(has_source)
