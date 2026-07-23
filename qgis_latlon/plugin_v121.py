"""QGIS 4 compatibility and automatic snapping extension for GeoClick Capture."""

from __future__ import annotations

from typing import List, Tuple

from qgis.PyQt.QtCore import Qt, QVariant
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.core import (
    QgsCoordinateTransform,
    QgsField,
    QgsPointXY,
    QgsProject,
    QgsVectorLayer,
    QgsWkbTypes,
)

from .dock_widget import CaptureLogDock
from .qgis_latlon import QgisLatLonPlugin


SNAP_FIELDS = (
    ("snapped", QVariant.Bool),
    ("snap_type", QVariant.String),
    ("snap_distance", QVariant.Double),
)


def _right_dock_area():
    """Return the right dock area for PyQt5 or PyQt6."""
    value = getattr(Qt, "RightDockWidgetArea", None)
    if value is not None:
        return value
    return Qt.DockWidgetArea.RightDockWidgetArea


class GeoClickCapturePlugin(QgisLatLonPlugin):
    """GeoClick Capture 1.2.1 runtime implementation."""

    def __init__(self, iface):
        super().__init__(iface)
        self._current_snap = {
            "snapped": False,
            "snap_type": "",
            "snap_distance": 0.0,
        }

    def _create_dock(self):
        """Create the panel without Qt 5-only enum aliases."""
        self.dock = CaptureLogDock(self.iface.mainWindow())
        self.iface.addDockWidget(_right_dock_area(), self.dock)
        self.dock.hide()
        self.dock.capture_toggled.connect(self.activate)
        self.dock.destination_changed.connect(self.set_destination_layer)
        self.dock.undo_requested.connect(self.undo_last_capture)
        self.dock.delete_requested.connect(self.delete_features)
        self.dock.clear_requested.connect(self.clear_session)
        self.dock.export_requested.connect(self.export_records)
        self.dock.set_preferences(self._load_preferences())

    def _load_preferences(self):
        values = super()._load_preferences()
        values["use_snapping"] = self.settings.value(
            "geoclick_capture/use_snapping", True, type=bool
        )
        values["snap_tolerance_px"] = int(
            self.settings.value("geoclick_capture/snap_tolerance_px", 12) or 12
        )
        return values

    def _save_preferences(self):
        super()._save_preferences()
        if self.dock is None:
            return
        values = self.dock.preference_values()
        self.settings.setValue(
            "geoclick_capture/use_snapping", bool(values.get("use_snapping", True))
        )
        self.settings.setValue(
            "geoclick_capture/snap_tolerance_px",
            int(values.get("snap_tolerance_px", 12) or 12),
        )

    def handle_map_click(self, map_point: QgsPointXY, button):
        """Snap the click before the base implementation records it."""
        context = self.dock.capture_context() if self.dock is not None else {}
        snapped_point = QgsPointXY(map_point)
        self._current_snap = {
            "snapped": False,
            "snap_type": "",
            "snap_distance": 0.0,
        }

        if bool(context.get("use_snapping", True)):
            snapped_point, snap_info = self._snap_point(
                map_point, int(context.get("snap_tolerance_px", 12) or 12)
            )
            self._current_snap = snap_info

        super().handle_map_click(snapped_point, button)

        if self._current_snap["snapped"]:
            self.iface.messageBar().pushMessage(
                "GeoClick Capture",
                f"Snapped to {self._current_snap['snap_type']}",
                duration=4,
            )

    def _prepare_layer(self) -> bool:
        if not super()._prepare_layer() or self.layer is None:
            return False
        existing = {field.name() for field in self.layer.fields()}
        missing = [
            QgsField(name, field_type)
            for name, field_type in SNAP_FIELDS
            if name not in existing
        ]
        if missing:
            if not self.layer.dataProvider().addAttributes(missing):
                self._critical("The snapping audit fields could not be added.")
                return False
            self.layer.updateFields()
        return True

    def add_point_to_layer(
        self,
        map_point,
        wgs84_point,
        captured_at,
        project_authid,
        project_name,
        map_scale,
        source_layer,
        source_layer_id,
        source_feature_id,
        location,
        context,
    ):
        feature_id = super().add_point_to_layer(
            map_point,
            wgs84_point,
            captured_at,
            project_authid,
            project_name,
            map_scale,
            source_layer,
            source_layer_id,
            source_feature_id,
            location,
            context,
        )
        if feature_id is None or self.layer is None:
            return feature_id

        changes = {}
        for field_name, value in self._current_snap.items():
            index = self.layer.fields().indexOf(field_name)
            if index >= 0:
                changes[index] = value
        if changes:
            self.layer.dataProvider().changeAttributeValues({feature_id: changes})
            self.layer.triggerRepaint()
        return feature_id

    def clear_session(self):
        """Qt 5/6-safe confirmation dialog."""
        if self.layer is None or self.layer.featureCount() == 0:
            return
        yes = getattr(QMessageBox, "Yes", None)
        no = getattr(QMessageBox, "No", None)
        if yes is None:
            yes = QMessageBox.StandardButton.Yes
            no = QMessageBox.StandardButton.No
        answer = QMessageBox.question(
            self.iface.mainWindow(),
            "GeoClick Capture",
            "Delete all records from the current destination layer?",
            yes | no,
            no,
        )
        if answer == yes:
            self.delete_features([feature.id() for feature in self.layer.getFeatures()])

    def _snap_point(self, map_point: QgsPointXY, tolerance_pixels: int):
        """Use project snapping, then automatic vertex/segment fallback."""
        snapping_utils = self.canvas.snappingUtils()
        try:
            match = snapping_utils.snapToMap(map_point)
            if match.isValid():
                point = QgsPointXY(match.point())
                snap_type = self._match_type(match)
                return point, {
                    "snapped": True,
                    "snap_type": snap_type,
                    "snap_distance": float(map_point.distance(point)),
                }
        except (AttributeError, RuntimeError, TypeError):
            pass

        return self._fallback_snap(map_point, tolerance_pixels)

    @staticmethod
    def _match_type(match) -> str:
        try:
            if match.hasVertex():
                return "vertex"
            if match.hasEdge():
                return "segment"
            if match.hasLineEndpoint():
                return "line endpoint"
        except AttributeError:
            pass
        return "project snapping"

    def _fallback_snap(self, map_point: QgsPointXY, tolerance_pixels: int):
        """Snap to visible line/polygon vertices, then segments."""
        project = QgsProject.instance()
        project_crs = self.canvas.mapSettings().destinationCrs()
        tolerance_map = max(2, tolerance_pixels) * float(self.canvas.mapUnitsPerPixel())
        vertex_candidates: List[Tuple] = []
        segment_candidates: List[Tuple] = []

        line_type = getattr(QgsWkbTypes, "LineGeometry", None)
        polygon_type = getattr(QgsWkbTypes, "PolygonGeometry", None)
        eligible_types = {line_type, polygon_type}

        for layer in self.canvas.layers():
            if not isinstance(layer, QgsVectorLayer) or not layer.isValid():
                continue
            if layer is self.layer or layer.geometryType() not in eligible_types:
                continue

            try:
                to_layer = QgsCoordinateTransform(project_crs, layer.crs(), project)
                from_layer = QgsCoordinateTransform(layer.crs(), project_crs, project)
                layer_point = to_layer.transform(map_point)
                offset_map = QgsPointXY(map_point.x() + tolerance_map, map_point.y())
                offset_layer = to_layer.transform(offset_map)
                tolerance_layer = max(layer_point.distance(offset_layer), 1e-12)
                locator = self.canvas.snappingUtils().locatorForLayer(layer)

                vertex = locator.nearestVertex(layer_point, tolerance_layer)
                if vertex.isValid():
                    project_point = QgsPointXY(from_layer.transform(vertex.point()))
                    vertex_candidates.append(
                        (float(map_point.distance(project_point)), project_point)
                    )

                edge = locator.nearestEdge(layer_point, tolerance_layer)
                if edge.isValid():
                    project_point = QgsPointXY(from_layer.transform(edge.point()))
                    segment_candidates.append(
                        (float(map_point.distance(project_point)), project_point)
                    )
            except (AttributeError, RuntimeError, TypeError, ValueError):
                continue

        candidates = vertex_candidates or segment_candidates
        if not candidates:
            return QgsPointXY(map_point), {
                "snapped": False,
                "snap_type": "",
                "snap_distance": 0.0,
            }

        distance, point = min(candidates, key=lambda candidate: candidate[0])
        return point, {
            "snapped": True,
            "snap_type": "vertex" if vertex_candidates else "segment",
            "snap_distance": distance,
        }
