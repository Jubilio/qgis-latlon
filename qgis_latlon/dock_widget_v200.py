"""Location Verification Workspace interface for GeoClick Capture 2.0.0."""

from __future__ import annotations

from typing import Dict, List, Optional

from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
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
from .dock_widget_v160 import CaptureLogDockV160
from .workspace_utils import WORKSPACE_STATUSES


class CaptureLogDockV200(CaptureLogDockV160):
    """Unified location-verification and evidence workspace."""

    workspace_action_requested = pyqtSignal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._workspace_candidates: List[Dict[str, object]] = []
        self._workspace_evidence: List[Dict[str, object]] = []
        self._workspace_metadata: Dict[str, object] = {}

        self.workspace_page = self._build_workspace_page()
        self.workspace_tab_index = self.tabs.addTab(
            self.workspace_page, plugin_icon("workspace.svg"), "Verification Workspace"
        )

    def _build_workspace_page(self) -> QWidget:
        page = QWidget(self)
        root = QVBoxLayout(page)

        intro = QLabel(
            "Combine online results, institutional gazetteers, existing QGIS features, "
            "coordinates and evidence in one auditable verification workspace. The plugin "
            "recommends a source but never selects the preferred location automatically."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        workspace_form = QFormLayout()
        self.workspace_id_edit = QLineEdit()
        self.workspace_id_edit.setReadOnly(True)
        self.workspace_place_edit = QLineEdit()
        self.workspace_place_edit.setPlaceholderText("Place or facility being verified")
        self.workspace_verifier_edit = QLineEdit()
        self.workspace_verifier_edit.setPlaceholderText("Verifier name")
        self.workspace_status_combo = QComboBox()
        for status in WORKSPACE_STATUSES:
            self.workspace_status_combo.addItem(status, status)
        self.workspace_rationale_edit = QPlainTextEdit()
        self.workspace_rationale_edit.setPlaceholderText(
            "Explain why the preferred source was selected and any remaining uncertainty"
        )
        self.workspace_rationale_edit.setMaximumHeight(72)
        workspace_form.addRow("Workspace ID", self.workspace_id_edit)
        workspace_form.addRow("Place", self.workspace_place_edit)
        workspace_form.addRow("Verifier", self.workspace_verifier_edit)
        workspace_form.addRow("Status", self.workspace_status_combo)
        workspace_form.addRow("Rationale", self.workspace_rationale_edit)
        root.addLayout(workspace_form)

        self.workspace_summary = QLabel("Create or import a workspace to begin.")
        self.workspace_summary.setWordWrap(True)
        root.addWidget(self.workspace_summary)

        quick_sources = QHBoxLayout()
        self.workspace_add_online_button = QPushButton("Add online result")
        self.workspace_add_online_button.setIcon(plugin_icon("add_candidate.svg"))
        self.workspace_add_online_button.clicked.connect(self._add_selected_online)
        self.workspace_add_gazetteer_button = QPushButton("Add gazetteer result")
        self.workspace_add_gazetteer_button.setIcon(plugin_icon("gazetteer.svg"))
        self.workspace_add_gazetteer_button.clicked.connect(self._add_selected_gazetteer)
        self.workspace_add_match_button = QPushButton("Add match candidate")
        self.workspace_add_match_button.setIcon(plugin_icon("match_verify.svg"))
        self.workspace_add_match_button.clicked.connect(self._add_selected_match)
        quick_sources.addWidget(self.workspace_add_online_button)
        quick_sources.addWidget(self.workspace_add_gazetteer_button)
        quick_sources.addWidget(self.workspace_add_match_button)
        root.addLayout(quick_sources)

        layer_row = QHBoxLayout()
        self.workspace_layer_combo = QgsMapLayerComboBox()
        vector_filter = getattr(QgsMapLayerProxyModel, "VectorLayer", None)
        if vector_filter is None:
            vector_filter = Qgis.LayerFilter.VectorLayer
        self.workspace_layer_combo.setFilters(vector_filter)
        self.workspace_layer_combo.setAllowEmptyLayer(True)
        self.workspace_layer_combo.setShowCrs(True)
        self.workspace_add_layer_button = QPushButton("Add selected feature(s)")
        self.workspace_add_layer_button.setIcon(plugin_icon("add_candidate.svg"))
        self.workspace_add_layer_button.clicked.connect(
            lambda: self.workspace_action_requested.emit(
                "add_layer", self.workspace_layer_combo.currentLayer()
            )
        )
        self.workspace_import_csv_button = QPushButton("Import candidate CSV")
        self.workspace_import_csv_button.setIcon(plugin_icon("import_workspace.svg"))
        self.workspace_import_csv_button.clicked.connect(self._browse_candidate_csv)
        layer_row.addWidget(self.workspace_layer_combo, 1)
        layer_row.addWidget(self.workspace_add_layer_button)
        layer_row.addWidget(self.workspace_import_csv_button)
        root.addLayout(layer_row)

        manual_form = QFormLayout()
        self.workspace_manual_label = QLineEdit()
        self.workspace_manual_label.setPlaceholderText("Candidate label")
        self.workspace_manual_source = QLineEdit()
        self.workspace_manual_source.setPlaceholderText("Source name")
        coordinate_row = QHBoxLayout()
        self.workspace_manual_lat = QDoubleSpinBox()
        self.workspace_manual_lat.setRange(-90.0, 90.0)
        self.workspace_manual_lat.setDecimals(8)
        self.workspace_manual_lat.setPrefix("Lat ")
        self.workspace_manual_lon = QDoubleSpinBox()
        self.workspace_manual_lon.setRange(-180.0, 180.0)
        self.workspace_manual_lon.setDecimals(8)
        self.workspace_manual_lon.setPrefix("Lon ")
        self.workspace_add_manual_button = QPushButton("Add manual")
        self.workspace_add_manual_button.setIcon(plugin_icon("add_candidate.svg"))
        self.workspace_add_manual_button.clicked.connect(self._add_manual_candidate)
        coordinate_row.addWidget(self.workspace_manual_lat)
        coordinate_row.addWidget(self.workspace_manual_lon)
        coordinate_row.addWidget(self.workspace_add_manual_button)
        manual_form.addRow("Manual label", self.workspace_manual_label)
        manual_form.addRow("Manual source", self.workspace_manual_source)
        manual_form.addRow("Coordinates", coordinate_row)
        root.addLayout(manual_form)

        self.workspace_candidate_table = QTableWidget(0, 10)
        self.workspace_candidate_table.setHorizontalHeaderLabels(
            [
                "Preferred",
                "Candidate",
                "Source",
                "Source ID",
                "Latitude",
                "Longitude",
                "To preferred",
                "Agreement",
                "Recommendation",
                "Geometry",
            ]
        )
        self.workspace_candidate_table.setSelectionBehavior(
            _enum(QAbstractItemView, "SelectRows", "SelectionBehavior.SelectRows")
        )
        self.workspace_candidate_table.setSelectionMode(
            _enum(QAbstractItemView, "ExtendedSelection", "SelectionMode.ExtendedSelection")
        )
        self.workspace_candidate_table.setEditTriggers(
            _enum(QAbstractItemView, "NoEditTriggers", "EditTrigger.NoEditTriggers")
        )
        self.workspace_candidate_table.itemSelectionChanged.connect(
            self._update_workspace_actions
        )
        self.workspace_candidate_table.cellDoubleClicked.connect(
            lambda _row, _column: self._emit_candidate_action("zoom")
        )
        root.addWidget(self.workspace_candidate_table, 1)

        candidate_actions = QHBoxLayout()
        self.workspace_zoom_button = QPushButton("Zoom")
        self.workspace_zoom_button.setIcon(plugin_icon("zoom_result.svg"))
        self.workspace_zoom_button.clicked.connect(
            lambda: self._emit_candidate_action("zoom")
        )
        self.workspace_preview_button = QPushButton("Preview")
        self.workspace_preview_button.setIcon(plugin_icon("preview_result.svg"))
        self.workspace_preview_button.clicked.connect(
            lambda: self._emit_candidate_action("preview")
        )
        self.workspace_preferred_button = QPushButton("Set preferred")
        self.workspace_preferred_button.setIcon(plugin_icon("preferred_source.svg"))
        self.workspace_preferred_button.clicked.connect(
            lambda: self._emit_candidate_action("set_preferred")
        )
        self.workspace_remove_candidate_button = QPushButton("Remove")
        self.workspace_remove_candidate_button.setIcon(plugin_icon("delete.svg"))
        self.workspace_remove_candidate_button.clicked.connect(
            lambda: self._emit_candidate_action("remove_candidates")
        )
        self.workspace_comparison_layer_button = QPushButton("Comparison layer")
        self.workspace_comparison_layer_button.setIcon(
            plugin_icon("comparison_layer.svg")
        )
        self.workspace_comparison_layer_button.clicked.connect(
            lambda: self.workspace_action_requested.emit("comparison_layer", {})
        )
        for button in (
            self.workspace_zoom_button,
            self.workspace_preview_button,
            self.workspace_preferred_button,
            self.workspace_remove_candidate_button,
            self.workspace_comparison_layer_button,
        ):
            candidate_actions.addWidget(button)
        root.addLayout(candidate_actions)

        evidence_header = QLabel("<b>Evidence</b>")
        root.addWidget(evidence_header)
        evidence_input = QHBoxLayout()
        self.workspace_evidence_note = QLineEdit()
        self.workspace_evidence_note.setPlaceholderText("Evidence note")
        self.workspace_evidence_url = QLineEdit()
        self.workspace_evidence_url.setPlaceholderText("URL or reference")
        self.workspace_add_file_button = QPushButton("Add file")
        self.workspace_add_file_button.setIcon(plugin_icon("add_evidence.svg"))
        self.workspace_add_file_button.clicked.connect(self._browse_evidence_file)
        self.workspace_add_url_button = QPushButton("Add URL")
        self.workspace_add_url_button.setIcon(plugin_icon("add_evidence.svg"))
        self.workspace_add_url_button.clicked.connect(self._add_evidence_url)
        evidence_input.addWidget(self.workspace_evidence_note)
        evidence_input.addWidget(self.workspace_evidence_url, 1)
        evidence_input.addWidget(self.workspace_add_file_button)
        evidence_input.addWidget(self.workspace_add_url_button)
        root.addLayout(evidence_input)

        self.workspace_evidence_table = QTableWidget(0, 6)
        self.workspace_evidence_table.setHorizontalHeaderLabels(
            ["Type", "Label", "Reference", "SHA-256", "Added by", "Note"]
        )
        self.workspace_evidence_table.setSelectionBehavior(
            _enum(QAbstractItemView, "SelectRows", "SelectionBehavior.SelectRows")
        )
        self.workspace_evidence_table.setSelectionMode(
            _enum(QAbstractItemView, "ExtendedSelection", "SelectionMode.ExtendedSelection")
        )
        self.workspace_evidence_table.setEditTriggers(
            _enum(QAbstractItemView, "NoEditTriggers", "EditTrigger.NoEditTriggers")
        )
        self.workspace_evidence_table.setMaximumHeight(140)
        self.workspace_evidence_table.itemSelectionChanged.connect(
            self._update_workspace_actions
        )
        root.addWidget(self.workspace_evidence_table)

        evidence_actions = QHBoxLayout()
        self.workspace_remove_evidence_button = QPushButton("Remove evidence")
        self.workspace_remove_evidence_button.setIcon(plugin_icon("delete.svg"))
        self.workspace_remove_evidence_button.clicked.connect(
            lambda: self.workspace_action_requested.emit(
                "remove_evidence", self.selected_workspace_evidence()
            )
        )
        evidence_actions.addWidget(self.workspace_remove_evidence_button)
        evidence_actions.addStretch(1)
        root.addLayout(evidence_actions)

        footer = QHBoxLayout()
        self.workspace_new_button = QPushButton("New workspace")
        self.workspace_new_button.setIcon(plugin_icon("workspace.svg"))
        self.workspace_new_button.clicked.connect(
            lambda: self.workspace_action_requested.emit("new_workspace", {})
        )
        self.workspace_import_button = QPushButton("Import workspace")
        self.workspace_import_button.setIcon(plugin_icon("import_workspace.svg"))
        self.workspace_import_button.clicked.connect(self._browse_workspace_import)
        self.workspace_export_button = QPushButton("Export bundle")
        self.workspace_export_button.setIcon(plugin_icon("workspace_bundle.svg"))
        self.workspace_export_button.clicked.connect(self._browse_workspace_export)
        self.workspace_save_button = QPushButton("Save preferred to session")
        self.workspace_save_button.setIcon(plugin_icon("capture_point.svg"))
        self.workspace_save_button.clicked.connect(
            lambda: self.workspace_action_requested.emit(
                "save_to_session", self.workspace_metadata()
            )
        )
        footer.addWidget(self.workspace_new_button)
        footer.addWidget(self.workspace_import_button)
        footer.addWidget(self.workspace_export_button)
        footer.addWidget(self.workspace_save_button)
        root.addLayout(footer)

        self._update_workspace_actions()
        return page

    def workspace_metadata(self) -> Dict[str, object]:
        verifier = self.workspace_verifier_edit.text().strip()
        if not verifier and hasattr(self, "operator_edit"):
            verifier = self.operator_edit.text().strip()
        return {
            "workspace_id": self.workspace_id_edit.text().strip(),
            "place_name": self.workspace_place_edit.text().strip(),
            "verifier": verifier,
            "status": str(self.workspace_status_combo.currentData() or "Draft"),
            "rationale": self.workspace_rationale_edit.toPlainText().strip(),
            "preferred_candidate_id": str(
                self._workspace_metadata.get("preferred_candidate_id", "")
            ),
            "created_at": str(self._workspace_metadata.get("created_at", "")),
        }

    def _add_selected_online(self):
        result = self.selected_search_result()
        if result:
            self.workspace_action_requested.emit("add_online", result)

    def _add_selected_gazetteer(self):
        result = self.selected_gazetteer_result()
        if result:
            self.workspace_action_requested.emit("add_gazetteer", result)

    def _add_selected_match(self):
        result = self.selected_match_candidate()
        if result:
            self.workspace_action_requested.emit("add_match", result)

    def _add_manual_candidate(self):
        payload = {
            "label": self.workspace_manual_label.text().strip() or "Manual coordinate",
            "source": self.workspace_manual_source.text().strip() or "Manual entry",
            "source_kind": "manual",
            "lat": float(self.workspace_manual_lat.value()),
            "lon": float(self.workspace_manual_lon.value()),
            "geometry_type": "Point",
            "input_format": "manual_coordinate",
        }
        self.workspace_action_requested.emit("add_manual", payload)

    def _browse_candidate_csv(self):
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Import workspace candidates",
            "",
            "CSV files (*.csv);;All files (*.*)",
        )
        if path:
            self.workspace_action_requested.emit("import_candidates", path)

    def _browse_evidence_file(self):
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Add verification evidence",
            "",
            "All files (*.*)",
        )
        if path:
            self.workspace_action_requested.emit(
                "add_evidence_file",
                {
                    "path": path,
                    "note": self.workspace_evidence_note.text().strip(),
                    "added_by": self.workspace_verifier_edit.text().strip(),
                },
            )

    def _add_evidence_url(self):
        value = self.workspace_evidence_url.text().strip()
        if value:
            self.workspace_action_requested.emit(
                "add_evidence_url",
                {
                    "value": value,
                    "note": self.workspace_evidence_note.text().strip(),
                    "added_by": self.workspace_verifier_edit.text().strip(),
                },
            )

    def _browse_workspace_import(self):
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Import verification workspace",
            "",
            "Workspace files (*.json *.zip);;All files (*.*)",
        )
        if path:
            self.workspace_action_requested.emit("import_workspace", path)

    def _browse_workspace_export(self):
        default_name = self.workspace_id_edit.text().strip() or "geoclick_workspace"
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export verification bundle",
            f"{default_name}.zip",
            "ZIP archives (*.zip)",
        )
        if path:
            self.workspace_action_requested.emit(
                "export_bundle", {"path": path, "metadata": self.workspace_metadata()}
            )

    def selected_workspace_candidates(self) -> List[Dict[str, object]]:
        records: List[Dict[str, object]] = []
        for index in sorted(
            self.workspace_candidate_table.selectionModel().selectedRows(),
            key=lambda item: item.row(),
        ):
            row = index.row()
            if 0 <= row < len(self._workspace_candidates):
                records.append(dict(self._workspace_candidates[row]))
        return records

    def selected_workspace_evidence(self) -> List[Dict[str, object]]:
        records: List[Dict[str, object]] = []
        for index in sorted(
            self.workspace_evidence_table.selectionModel().selectedRows(),
            key=lambda item: item.row(),
        ):
            row = index.row()
            if 0 <= row < len(self._workspace_evidence):
                records.append(dict(self._workspace_evidence[row]))
        return records

    def _emit_candidate_action(self, action: str):
        selected = self.selected_workspace_candidates()
        if selected:
            self.workspace_action_requested.emit(action, selected)

    def show_workspace_tab(self):
        self.tabs.setCurrentIndex(self.workspace_tab_index)
        if not self.workspace_verifier_edit.text().strip() and hasattr(self, "operator_edit"):
            self.workspace_verifier_edit.setText(self.operator_edit.text().strip())
        self.workspace_action_requested.emit("refresh_workspace", self.workspace_metadata())

    def set_workspace_state(self, workspace: Dict[str, object]):
        metadata = dict(workspace.get("metadata", {}) or {})
        candidates = [dict(item) for item in workspace.get("candidates", []) or []]
        evidence = [dict(item) for item in workspace.get("evidence", []) or []]
        summary = dict(workspace.get("summary", {}) or {})
        self._workspace_metadata = metadata
        self._workspace_candidates = candidates
        self._workspace_evidence = evidence

        self.workspace_id_edit.setText(str(metadata.get("workspace_id", "")))
        self.workspace_place_edit.setText(str(metadata.get("place_name", "")))
        self.workspace_verifier_edit.setText(str(metadata.get("verifier", "")))
        status = str(metadata.get("status", "Draft"))
        status_index = self.workspace_status_combo.findData(status)
        self.workspace_status_combo.setCurrentIndex(max(0, status_index))
        self.workspace_rationale_edit.setPlainText(str(metadata.get("rationale", "")))

        self.workspace_candidate_table.setRowCount(0)
        for item in candidates:
            row = self.workspace_candidate_table.rowCount()
            self.workspace_candidate_table.insertRow(row)
            distance = item.get("distance_to_preferred_m")
            values = (
                "✓" if item.get("is_preferred") else "",
                str(item.get("label", "")),
                str(item.get("source", "")),
                str(item.get("source_id", "")),
                f"{float(item.get('lat', 0.0)):.7f}",
                f"{float(item.get('lon', 0.0)):.7f}",
                "—" if distance is None else f"{float(distance):.1f} m",
                f"{float(item.get('agreement_score', 0.0)):.0f}/100",
                f"{float(item.get('recommendation_score', 0.0)):.0f}/100",
                str(item.get("geometry_type", "Point")),
            )
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if column in (1, 2, 3):
                    cell.setToolTip(value)
                self.workspace_candidate_table.setItem(row, column, cell)
        self.workspace_candidate_table.resizeColumnsToContents()
        if candidates:
            preferred_row = next(
                (index for index, item in enumerate(candidates) if item.get("is_preferred")),
                0,
            )
            self.workspace_candidate_table.selectRow(preferred_row)

        self.workspace_evidence_table.setRowCount(0)
        for item in evidence:
            row = self.workspace_evidence_table.rowCount()
            self.workspace_evidence_table.insertRow(row)
            values = (
                str(item.get("kind", "")),
                str(item.get("label", "")),
                str(item.get("value", "")),
                str(item.get("sha256", "")),
                str(item.get("added_by", "")),
                str(item.get("note", "")),
            )
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if column in (2, 3, 5):
                    cell.setToolTip(value)
                self.workspace_evidence_table.setItem(row, column, cell)
        self.workspace_evidence_table.resizeColumnsToContents()

        candidate_count = int(summary.get("candidate_count", len(candidates)) or 0)
        source_count = int(summary.get("source_count", 0) or 0)
        spread = float(summary.get("source_spread_m", 0.0) or 0.0)
        consensus = str(summary.get("consensus_level", "Single source"))
        recommendation = str(summary.get("recommended_label", ""))
        self.workspace_summary.setText(
            f"{candidate_count} candidate(s) from {source_count} source(s) — maximum "
            f"spread {spread:.1f} m — consensus: <b>{consensus}</b>. "
            + (f"Recommended for review: <b>{recommendation}</b>." if recommendation else "")
        )
        self._update_workspace_actions()

    def clear_workspace_inputs(self):
        self.workspace_evidence_url.clear()
        self.workspace_evidence_note.clear()
        self.workspace_manual_label.clear()

    def _update_workspace_actions(self):
        selected_candidates = self.selected_workspace_candidates()
        has_candidates = bool(self._workspace_candidates)
        for button in (
            self.workspace_zoom_button,
            self.workspace_preview_button,
            self.workspace_preferred_button,
        ):
            button.setEnabled(len(selected_candidates) == 1)
        self.workspace_remove_candidate_button.setEnabled(bool(selected_candidates))
        self.workspace_comparison_layer_button.setEnabled(has_candidates)
        self.workspace_save_button.setEnabled(has_candidates)
        self.workspace_remove_evidence_button.setEnabled(
            bool(self.selected_workspace_evidence())
        )
