"""Offline Gazetteer extension for GeoClick Capture 1.5.0."""

from __future__ import annotations

from typing import Dict, List, Optional

from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsField

from .dock_widget_v126 import plugin_icon
from .dock_widget_v150 import CaptureLogDockV150
from .gazetteer_utils import (
    detect_columns,
    gazetteer_metadata,
    load_csv_gazetteer,
    normalise_record,
    search_gazetteer,
)
from .plugin_v121 import _right_dock_area
from .plugin_v140 import GeoClickCapturePluginV140
from .qgis_latlon import SUCCESS_LEVEL

GAZETTEER_FIELDS = (
    ("gazetteer_source", QVariant.String),
    ("gazetteer_record_id", QVariant.String),
    ("gazetteer_pcode", QVariant.String),
    ("gazetteer_name", QVariant.String),
    ("gazetteer_aliases", QVariant.String),
    ("gazetteer_type", QVariant.String),
    ("gazetteer_admin", QVariant.String),
    ("gazetteer_source_date", QVariant.String),
)


class GeoClickCapturePluginV150(GeoClickCapturePluginV140):
    """Search institutional places offline and preserve their source metadata."""

    def __init__(self, iface):
        super().__init__(iface)
        self.gazetteer_action: Optional[QAction] = None
        self._gazetteer_records: List[Dict[str, object]] = []
        self._gazetteer_metadata: Dict[str, object] = {}
        self._last_gazetteer_query = ""

    def initGui(self):
        parent = self.iface.mainWindow()
        self.gazetteer_action = QAction(
            plugin_icon("gazetteer.svg"), "Open offline gazetteer", parent
        )
        self.gazetteer_action.setToolTip(
            "Load a local place gazetteer and search names, aliases or P-codes offline"
        )
        self.gazetteer_action.triggered.connect(self.show_gazetteer)
        super().initGui()
        self.iface.addToolBarIcon(self.gazetteer_action)

    def _menu_actions(self):
        actions = super()._menu_actions()
        if self.gazetteer_action is not None and self.gazetteer_action not in actions:
            actions.append(self.gazetteer_action)
        return actions

    def _create_dock(self):
        self.dock = CaptureLogDockV150(self.iface.mainWindow())
        self.iface.addDockWidget(_right_dock_area(), self.dock)
        self.dock.hide()
        self.dock.capture_toggled.connect(self.activate)
        self.dock.destination_changed.connect(self.set_destination_layer)
        self.dock.undo_requested.connect(self.undo_last_capture)
        self.dock.delete_requested.connect(self.delete_features)
        self.dock.clear_requested.connect(self.clear_session)
        self.dock.export_requested.connect(self.export_records)
        self.dock.search_requested.connect(self.search_place)
        self.dock.search_action_requested.connect(self.handle_search_action)
        self.dock.verify_requested.connect(self.verify_matches)
        self.dock.verify_action_requested.connect(self.handle_verify_action)
        self.dock.gazetteer_csv_requested.connect(self.load_gazetteer_csv)
        self.dock.gazetteer_layer_requested.connect(self.load_gazetteer_layer)
        self.dock.gazetteer_search_requested.connect(self.search_offline_gazetteer)
        self.dock.gazetteer_action_requested.connect(self.handle_gazetteer_action)
        self.dock.set_preferences(self._load_preferences())

    def unload(self):
        if self.gazetteer_action is not None:
            self.iface.removeToolBarIcon(self.gazetteer_action)
        super().unload()
        self.gazetteer_action = None
        self._gazetteer_records.clear()
        self._gazetteer_metadata.clear()

    def show_gazetteer(self):
        self.show_dock()
        if isinstance(self.dock, CaptureLogDockV150):
            self.dock.show_gazetteer_tab()

    def _prepare_layer(self) -> bool:
        if not super()._prepare_layer() or self.layer is None:
            return False
        existing = {field.name() for field in self.layer.fields()}
        missing = [
            QgsField(name, field_type)
            for name, field_type in GAZETTEER_FIELDS
            if name not in existing
        ]
        if missing:
            if not self.layer.dataProvider().addAttributes(missing):
                self._critical("The offline-gazetteer audit fields could not be added.")
                return False
            self.layer.updateFields()
        return True

    def load_gazetteer_csv(self, path: str):
        if not isinstance(self.dock, CaptureLogDockV150):
            return
        self.dock.set_gazetteer_busy(True, "Loading offline CSV gazetteer…")
        try:
            records, metadata = load_csv_gazetteer(path)
        except (OSError, UnicodeError, ValueError) as exc:
            self.dock.set_gazetteer_busy(False, f"Gazetteer could not be loaded: {exc}")
            return
        self._set_gazetteer(records, metadata)

    def load_gazetteer_layer(self, layer):
        if not isinstance(self.dock, CaptureLogDockV150):
            return
        if not self._eligible_point_layer(layer):
            self.dock.set_gazetteer_busy(False, "Select a valid QGIS point layer.")
            return
        self.dock.set_gazetteer_busy(True, f"Reading {layer.name()}…")
        field_names = [field.name() for field in layer.fields()]
        mapping = detect_columns(field_names)
        if "official_name" not in mapping:
            self.dock.set_gazetteer_busy(
                False,
                "The selected layer needs a recognisable name field such as name, official_name or site_name.",
            )
            return
        records: List[Dict[str, object]] = []
        for row_number, feature in enumerate(layer.getFeatures(), start=1):
            point = self._feature_point_wgs84(feature, layer)
            if point is None:
                continue
            row = {field: feature[field] for field in field_names}
            record = normalise_record(
                row,
                mapping,
                layer.name(),
                row_number,
                coordinates=(float(point.y()), float(point.x())),
            )
            if record is not None:
                record["source_layer_id"] = layer.id()
                record["source_feature_id"] = str(feature.id())
                records.append(record)
        metadata = gazetteer_metadata(records, layer.name(), mapping)
        metadata["format"] = "QGIS point layer"
        metadata["layer_id"] = layer.id()
        self._set_gazetteer(records, metadata)

    def _set_gazetteer(
        self, records: List[Dict[str, object]], metadata: Dict[str, object]
    ):
        self._gazetteer_records = [dict(record) for record in records]
        self._gazetteer_metadata = dict(metadata)
        if isinstance(self.dock, CaptureLogDockV150):
            self.dock.set_gazetteer_busy(False)
            self.dock.set_gazetteer_source(self._gazetteer_metadata)
            self.dock.set_gazetteer_results(
                search_gazetteer(self._gazetteer_records, "", limit=100),
                "Showing the first 100 offline gazetteer records.",
            )

    def search_offline_gazetteer(self, options: Dict[str, object]):
        if not isinstance(self.dock, CaptureLogDockV150):
            return
        if not self._gazetteer_records:
            self.dock.set_gazetteer_results([], "Load an offline gazetteer first.")
            return
        query = str(options.get("query", "")).strip()
        self._last_gazetteer_query = query
        place_type = str(options.get("place_type", "")).strip()
        results = search_gazetteer(
            self._gazetteer_records,
            query,
            place_type=place_type,
            limit=100,
        )
        self.dock.set_gazetteer_results(
            results,
            f"{len(results)} offline result(s) for “{query}”."
            if query
            else f"Showing {len(results)} offline gazetteer record(s).",
        )
        if results:
            self.preview_search_result(self._gazetteer_result(results[0]))

    def handle_gazetteer_action(self, action: str, record: Dict[str, object]):
        result = self._gazetteer_result(record)
        if action == "zoom":
            self.zoom_to_search_result(result)
        elif action == "preview":
            self.preview_search_result(result)
        elif action == "match":
            if isinstance(self.dock, CaptureLogDockV150):
                self.dock.prepare_match(result)
        elif action == "capture":
            self.capture_gazetteer_result(record)

    def _gazetteer_result(self, record: Dict[str, object]) -> Dict[str, object]:
        aliases = list(record.get("alternative_names", []) or [])
        return {
            "display_name": str(record.get("official_name", "")),
            "lat": float(record.get("lat", 0.0) or 0.0),
            "lon": float(record.get("lon", 0.0) or 0.0),
            "result_type": str(record.get("place_type", "place")),
            "category": "offline_gazetteer",
            "importance": float(record.get("search_score", 0.0) or 0.0),
            "osm_type": "",
            "osm_id": "",
            "provider_result_id": str(record.get("record_id", "")),
            "boundingbox": [],
            "provider": f"Offline gazetteer: {record.get('source_name', '')}",
            "input_format": "offline_gazetteer",
            "search_query": self._last_gazetteer_query,
            "gazetteer_record": dict(record),
            "alternative_names": aliases,
        }

    def capture_gazetteer_result(self, record: Dict[str, object]):
        result = self._gazetteer_result(record)
        self.capture_search_result(result)
        if self.layer is None or self.last_feature_id is None:
            return
        audit = {
            "gazetteer_source": str(record.get("source_name", record.get("source", ""))),
            "gazetteer_record_id": str(record.get("record_id", "")),
            "gazetteer_pcode": str(record.get("pcode", "")),
            "gazetteer_name": str(record.get("official_name", "")),
            "gazetteer_aliases": "; ".join(record.get("alternative_names", []) or []),
            "gazetteer_type": str(record.get("place_type", "")),
            "gazetteer_admin": str(record.get("admin_label", "")),
            "gazetteer_source_date": str(record.get("source_date", "")),
        }
        changes = {}
        for field_name, value in audit.items():
            index = self.layer.fields().indexOf(field_name)
            if index >= 0:
                changes[index] = value
        if changes:
            self.layer.dataProvider().changeAttributeValues(
                {int(self.last_feature_id): changes}
            )
            self.layer.triggerRepaint()
            self._refresh_dock()
        self.iface.messageBar().pushMessage(
            "Offline gazetteer place added",
            f"{record.get('official_name', '')} | {record.get('pcode', '')}",
            level=SUCCESS_LEVEL,
            duration=7,
        )
