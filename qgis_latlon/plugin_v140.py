"""Match & Verify extension for GeoClick Capture 1.4.0."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple

from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import QAction
from qgis.core import (
    QgsCoordinateTransform,
    QgsDistanceArea,
    QgsFeature,
    QgsFeatureRequest,
    QgsField,
    QgsGeometry,
    QgsMapLayerType,
    QgsPointXY,
    QgsProject,
    QgsSpatialIndex,
)

from .dock_widget_v126 import plugin_icon
from .dock_widget_v140 import CaptureLogDockV140
from .match_utils import (
    best_name_match,
    duplicate_risk,
    match_confidence,
    sort_candidates,
)
from .plugin_v121 import _right_dock_area
from .plugin_v130_policy import GeoClickCapturePluginV130Policy
from .qgis_latlon import POINT_GEOMETRY, SUCCESS_LEVEL, WGS84

MATCH_FIELDS = (
    ("match_decision", QVariant.String),
    ("matched_layer", QVariant.String),
    ("matched_layer_id", QVariant.String),
    ("matched_feature_id", QVariant.String),
    ("match_distance_m", QVariant.Double),
    ("name_similarity", QVariant.Double),
    ("duplicate_risk", QVariant.String),
    ("confidence_score", QVariant.Double),
    ("review_required", QVariant.Bool),
)
_PREFERRED_NAME_FIELDS = (
    "name",
    "official_name",
    "site_name",
    "facility_name",
    "location",
    "label",
    "title",
    "place",
    "settlement",
    "village",
)


class GeoClickCapturePluginV140(GeoClickCapturePluginV130Policy):
    """Find possible duplicates before using an existing feature or creating a new one."""

    def __init__(self, iface):
        super().__init__(iface)
        self.match_action: Optional[QAction] = None

    def initGui(self):
        parent = self.iface.mainWindow()
        self.match_action = QAction(
            plugin_icon("match_verify.svg"), "Match & verify place", parent
        )
        self.match_action.setToolTip(
            "Compare a searched place with existing point layers and record the decision"
        )
        self.match_action.triggered.connect(self.show_match)
        super().initGui()
        self.iface.addToolBarIcon(self.match_action)

    def _menu_actions(self):
        actions = super()._menu_actions()
        if self.match_action is not None and self.match_action not in actions:
            actions.append(self.match_action)
        return actions

    def _create_dock(self):
        self.dock = CaptureLogDockV140(self.iface.mainWindow())
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
        self.dock.set_preferences(self._load_preferences())

    def unload(self):
        if self.match_action is not None:
            self.iface.removeToolBarIcon(self.match_action)
        super().unload()
        self.match_action = None

    def show_match(self):
        self.show_dock()
        if not isinstance(self.dock, CaptureLogDockV140):
            return
        selected = self.dock.selected_search_result()
        if selected:
            self.dock.prepare_match(selected)
        else:
            self.dock.show_match_tab()
            self.dock.match_status.setText(
                "Search for a place first, select a result, then choose Match & verify."
            )

    def handle_search_action(self, action: str, result: Dict[str, object]):
        if action == "match":
            if isinstance(self.dock, CaptureLogDockV140):
                self.dock.prepare_match(result)
            return
        super().handle_search_action(action, result)

    def _prepare_layer(self) -> bool:
        if not super()._prepare_layer() or self.layer is None:
            return False
        existing = {field.name() for field in self.layer.fields()}
        missing = [
            QgsField(name, field_type)
            for name, field_type in MATCH_FIELDS
            if name not in existing
        ]
        if missing:
            if not self.layer.dataProvider().addAttributes(missing):
                self._critical("The match-verification audit fields could not be added.")
                return False
            self.layer.updateFields()
        return True

    def verify_matches(self, options: Dict[str, object]):
        """Find nearby point features and calculate transparent duplicate evidence."""
        if not isinstance(self.dock, CaptureLogDockV140):
            return
        source = dict(options.get("source", {}) or {})
        try:
            source_point = QgsPointXY(float(source["lon"]), float(source["lat"]))
        except (KeyError, TypeError, ValueError):
            self.dock.set_match_results([], "The selected search result has invalid coordinates.")
            return

        radius_m = max(10.0, float(options.get("radius_m", 500.0) or 500.0))
        minimum_name_score = max(
            0.0, min(1.0, float(options.get("minimum_name_score", 0.4) or 0.0))
        )
        layers = self._candidate_layers(options)
        if not layers:
            self.dock.set_match_results(
                [], "No eligible point layer is available for matching."
            )
            return

        self.dock.set_match_busy(True, f"Analysing {len(layers)} point layer(s)…")
        candidates: List[Dict[str, object]] = []
        query_name = str(source.get("display_name", ""))
        preferred_layer = options.get("layer")
        preferred_field = str(options.get("name_field", "") or "")
        for layer in layers:
            field_name = preferred_field if layer is preferred_layer else ""
            candidates.extend(
                self._layer_candidates(
                    layer,
                    source_point,
                    query_name,
                    radius_m,
                    minimum_name_score,
                    field_name,
                )
            )

        ordered = sort_candidates(candidates)[:100]
        high = sum(1 for item in ordered if item.get("duplicate_risk") == "High")
        medium = sum(1 for item in ordered if item.get("duplicate_risk") == "Medium")
        summary = (
            f"{len(ordered)} candidate(s): {high} high-risk and {medium} medium-risk. "
            "Select a row to compare, or create a new record with the evidence attached."
            if ordered
            else "No nearby feature met the configured distance or name thresholds."
        )
        self.dock.set_match_busy(False)
        self.dock.set_match_results(ordered, summary)

    def _candidate_layers(self, options: Dict[str, object]):
        selected = options.get("layer")
        if not bool(options.get("scan_all_visible", True)):
            return [selected] if self._eligible_point_layer(selected) else []

        project = QgsProject.instance()
        root = project.layerTreeRoot()
        layers = []
        for layer in project.mapLayers().values():
            if not self._eligible_point_layer(layer):
                continue
            node = root.findLayer(layer.id())
            if node is not None and node.isVisible():
                layers.append(layer)
        return layers

    @staticmethod
    def _eligible_point_layer(layer) -> bool:
        return bool(
            layer is not None
            and layer.isValid()
            and layer.type() == QgsMapLayerType.VectorLayer
            and layer.geometryType() == POINT_GEOMETRY
        )

    def _layer_candidates(
        self,
        layer,
        source_wgs84: QgsPointXY,
        query_name: str,
        radius_m: float,
        minimum_name_score: float,
        preferred_field: str,
    ) -> List[Dict[str, object]]:
        try:
            source_layer_point = source_wgs84
            if layer.crs().isValid() and layer.crs() != WGS84:
                source_layer_point = QgsCoordinateTransform(
                    WGS84, layer.crs(), QgsProject.instance()
                ).transform(source_wgs84)
            index = QgsSpatialIndex(layer.getFeatures())
            nearest_ids = index.nearestNeighbor(QgsPointXY(source_layer_point), 200)
        except (RuntimeError, TypeError, ValueError):
            return []
        if not nearest_ids:
            return []

        request = QgsFeatureRequest().setFilterFids(nearest_ids)
        distance_area = QgsDistanceArea()
        distance_area.setSourceCrs(WGS84, QgsProject.instance().transformContext())
        distance_area.setEllipsoid("WGS84")
        candidates = []
        for feature in layer.getFeatures(request):
            point = self._feature_point_wgs84(feature, layer)
            if point is None:
                continue
            distance_m = float(distance_area.measureLine(source_wgs84, point))
            if distance_m > radius_m:
                continue
            name_match = self._feature_name_match(
                query_name, feature, layer, preferred_field
            )
            name_score = float(name_match["score"])
            close_without_name = distance_m <= min(50.0, radius_m * 0.20)
            if name_score < minimum_name_score and not close_without_name:
                continue
            confidence = match_confidence(name_score, distance_m, radius_m)
            risk = duplicate_risk(name_score, distance_m, radius_m)
            candidate_label = str(name_match["value"] or f"Feature {feature.id()}")
            candidates.append(
                {
                    "candidate_label": candidate_label,
                    "layer_name": layer.name(),
                    "layer_id": layer.id(),
                    "feature_id": int(feature.id()),
                    "lat": float(point.y()),
                    "lon": float(point.x()),
                    "distance_m": round(distance_m, 2),
                    "name_similarity": round(name_score, 4),
                    "confidence_score": confidence,
                    "duplicate_risk": risk,
                }
            )
        return candidates

    def _feature_point_wgs84(self, feature: QgsFeature, layer) -> Optional[QgsPointXY]:
        geometry = feature.geometry()
        if geometry is None or geometry.isEmpty():
            return None
        try:
            if geometry.isMultipart():
                points = geometry.asMultiPoint()
                if not points:
                    return None
                point = QgsPointXY(points[0])
            else:
                point = QgsPointXY(geometry.asPoint())
            if layer.crs().isValid() and layer.crs() != WGS84:
                point = QgsCoordinateTransform(
                    layer.crs(), WGS84, QgsProject.instance()
                ).transform(point)
            return QgsPointXY(point)
        except (RuntimeError, TypeError, ValueError):
            return None

    @staticmethod
    def _feature_name_match(
        query_name: str, feature: QgsFeature, layer, preferred_field: str
    ) -> Dict[str, object]:
        fields = layer.fields()
        values: List[object] = []
        if preferred_field and fields.indexOf(preferred_field) >= 0:
            values.append(feature[preferred_field])
        else:
            preferred = []
            remaining = []
            for field in fields:
                if field.type() != QVariant.String:
                    continue
                value = feature[field.name()]
                if value is None or not str(value).strip():
                    continue
                if field.name().casefold() in _PREFERRED_NAME_FIELDS:
                    preferred.append(value)
                else:
                    remaining.append(value)
            values = preferred + remaining
        return best_name_match(query_name, values)

    def handle_verify_action(
        self, action: str, source: Dict[str, object], candidate: Dict[str, object]
    ):
        if action == "zoom_existing" and candidate:
            self.zoom_to_search_result(candidate)
        elif action == "use_existing" and candidate:
            self._record_match_decision(source, candidate, "use_existing")
        elif action == "create_new":
            self._record_match_decision(source, candidate, "create_new")

    def _record_match_decision(
        self,
        source: Dict[str, object],
        candidate: Dict[str, object],
        decision: str,
    ):
        result = dict(source)
        if decision == "use_existing" and candidate:
            result.update(
                {
                    "lat": candidate.get("lat"),
                    "lon": candidate.get("lon"),
                    "display_name": candidate.get("candidate_label", "Existing feature"),
                    "provider": f"Existing QGIS layer: {candidate.get('layer_name', '')}",
                    "provider_result_id": (
                        f"{candidate.get('layer_id', '')}:{candidate.get('feature_id', '')}"
                    ),
                    "result_type": "existing_feature",
                }
            )
        self.capture_search_result(result)
        if self.layer is None or self.last_feature_id is None:
            return

        risk = str(candidate.get("duplicate_risk", "None")) if candidate else "None"
        audit = {
            "match_decision": decision,
            "matched_layer": str(candidate.get("layer_name", "")),
            "matched_layer_id": str(candidate.get("layer_id", "")),
            "matched_feature_id": str(candidate.get("feature_id", "")),
            "match_distance_m": float(candidate.get("distance_m", 0.0) or 0.0),
            "name_similarity": float(candidate.get("name_similarity", 0.0) or 0.0),
            "duplicate_risk": risk,
            "confidence_score": float(candidate.get("confidence_score", 0.0) or 0.0),
            "review_required": bool(decision == "create_new" and risk in {"High", "Medium"}),
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

        label = "Existing feature linked" if decision == "use_existing" else "New place created"
        self.iface.messageBar().pushMessage(
            label,
            f"Decision recorded | duplicate risk: {risk}",
            level=SUCCESS_LEVEL,
            duration=7,
        )
