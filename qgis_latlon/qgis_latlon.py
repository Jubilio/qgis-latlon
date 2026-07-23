"""GeoClick Capture plugin implementation."""

from __future__ import annotations

import csv
import json
import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlencode

from qgis.PyQt.QtCore import QTimer, Qt, QUrl, QVariant
from qgis.PyQt.QtGui import QGuiApplication, QIcon
from qgis.PyQt.QtNetwork import QNetworkRequest
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QMessageBox
from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsMapLayerType,
    QgsNetworkAccessManager,
    QgsPointXY,
    QgsProject,
    QgsSettings,
    QgsVectorFileWriter,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.gui import QgsMapToolEmitPoint, QgsMapToolIdentify

from .dock_widget import CaptureLogDock
from .utils import (
    ensure_extension,
    geocode_cache_key,
    normalise_session_id,
    safe_project_name,
    to_dms,
)

PLUGIN_MENU = "&GeoClick Capture"
SETTINGS_PREFIX = "geoclick_capture"
WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")
FIELD_DEFINITIONS = (
    ("id", QVariant.Int),
    ("session_id", QVariant.String),
    ("captured_at", QVariant.String),
    ("operator", QVariant.String),
    ("category", QVariant.String),
    ("status", QVariant.String),
    ("note", QVariant.String),
    ("lat", QVariant.Double),
    ("lon", QVariant.Double),
    ("map_x", QVariant.Double),
    ("map_y", QVariant.Double),
    ("project_crs", QVariant.String),
    ("project_name", QVariant.String),
    ("map_scale", QVariant.Double),
    ("source_layer", QVariant.String),
    ("source_layer_id", QVariant.String),
    ("source_feature_id", QVariant.String),
    ("location", QVariant.String),
)


def _compat_enum(container, scoped_container_name: str, member_name: str, legacy_name: str):
    """Return a scoped Qt/QGIS enum with a PyQt5 fallback."""
    scoped_container = getattr(container, scoped_container_name, None)
    if scoped_container is not None:
        return getattr(scoped_container, member_name)
    return getattr(container, legacy_name)


RIGHT_DOCK_AREA = _compat_enum(
    Qt, "DockWidgetArea", "RightDockWidgetArea", "RightDockWidgetArea"
)
INFO_LEVEL = _compat_enum(Qgis, "MessageLevel", "Info", "Info")
SUCCESS_LEVEL = _compat_enum(Qgis, "MessageLevel", "Success", "Success")
IDENTIFY_TOP_DOWN = _compat_enum(
    QgsMapToolIdentify,
    "IdentifyMode",
    "TopDownStopAtFirst",
    "TopDownStopAtFirst",
)
IDENTIFY_VECTOR_LAYER = _compat_enum(
    QgsMapToolIdentify, "Type", "VectorLayer", "VectorLayer"
)
POINT_GEOMETRY = _compat_enum(
    QgsWkbTypes, "GeometryType", "PointGeometry", "PointGeometry"
)
YES_BUTTON = _compat_enum(QMessageBox, "StandardButton", "Yes", "Yes")
WRITER_NO_ERROR = _compat_enum(
    QgsVectorFileWriter, "WriterError", "NoError", "NoError"
)


class QgisLatLonPlugin:
    """Log map clicks as auditable point records."""

    def __init__(self, iface):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.capture_action: Optional[QAction] = None
        self.panel_action: Optional[QAction] = None
        self.copy_action: Optional[QAction] = None
        self.reverse_geocode_action: Optional[QAction] = None
        self.dock: Optional[CaptureLogDock] = None
        self.tool: Optional[QgsMapToolEmitPoint] = None
        self.layer: Optional[QgsVectorLayer] = None
        self.last_coords: Optional[Tuple[float, float]] = None
        self.last_feature_id: Optional[int] = None
        self._pending_replies: List[object] = []
        self._geocode_cache: Dict[str, str] = {}
        self._last_geocode_request = 0.0
        self.id_counter = 1
        self.settings = QgsSettings()

    def initGui(self):
        icon_path = os.path.join(os.path.dirname(__file__), "icons", "icon.svg")
        parent = self.iface.mainWindow()

        self.capture_action = QAction(QIcon(icon_path), "Capture point", parent)
        self.capture_action.setCheckable(True)
        self.capture_action.setToolTip("Click the map to record a point")
        self.capture_action.triggered.connect(self.activate)

        self.panel_action = QAction("Open capture log", parent)
        self.panel_action.triggered.connect(self.show_dock)

        self.copy_action = QAction("Copy last coordinate", parent)
        self.copy_action.triggered.connect(self.copy_to_clipboard)

        self.reverse_geocode_action = QAction(
            "Enable reverse geocoding (OpenStreetMap)", parent
        )
        self.reverse_geocode_action.setCheckable(True)
        self.reverse_geocode_action.setChecked(
            self.settings.value(f"{SETTINGS_PREFIX}/reverse_geocode", False, type=bool)
        )
        self.reverse_geocode_action.toggled.connect(
            lambda enabled: self.settings.setValue(
                f"{SETTINGS_PREFIX}/reverse_geocode", enabled
            )
        )

        self.iface.addToolBarIcon(self.capture_action)
        for action in self._menu_actions():
            self.iface.addPluginToVectorMenu(PLUGIN_MENU, action)

        self._create_dock()

    def _create_dock(self):
        self.dock = CaptureLogDock(self.iface.mainWindow())
        self.iface.addDockWidget(RIGHT_DOCK_AREA, self.dock)
        self.dock.hide()
        self.dock.capture_toggled.connect(self.activate)
        self.dock.destination_changed.connect(self.set_destination_layer)
        self.dock.undo_requested.connect(self.undo_last_capture)
        self.dock.delete_requested.connect(self.delete_features)
        self.dock.clear_requested.connect(self.clear_session)
        self.dock.export_requested.connect(self.export_records)
        self.dock.set_preferences(self._load_preferences())

    def unload(self):
        self._save_preferences()
        if self.tool is not None and self.canvas.mapTool() is self.tool:
            self.canvas.unsetMapTool(self.tool)
        if self.capture_action is not None:
            self.iface.removeToolBarIcon(self.capture_action)
        for action in self._menu_actions():
            self.iface.removePluginVectorMenu(PLUGIN_MENU, action)
        for reply in list(self._pending_replies):
            try:
                reply.abort()
                reply.deleteLater()
            except RuntimeError:
                pass
        self._pending_replies.clear()
        if self.dock is not None:
            self.iface.removeDockWidget(self.dock)
            self.dock.deleteLater()
            self.dock = None

    def _menu_actions(self) -> List[QAction]:
        return [
            action
            for action in (
                self.capture_action,
                self.panel_action,
                self.copy_action,
                self.reverse_geocode_action,
            )
            if action is not None
        ]

    def show_dock(self):
        if self.dock is not None:
            self.dock.show()
            self.dock.raise_()
            self.dock.refresh(self.layer)

    def activate(self, checked: bool = True):
        if self.capture_action is not None and self.capture_action.isChecked() != checked:
            self.capture_action.blockSignals(True)
            self.capture_action.setChecked(checked)
            self.capture_action.blockSignals(False)
        if self.dock is not None:
            self.dock.set_capture_checked(checked)

        if not checked:
            if self.tool is not None and self.canvas.mapTool() is self.tool:
                self.canvas.unsetMapTool(self.tool)
            return

        if self.tool is None:
            self.tool = QgsMapToolEmitPoint(self.canvas)
            self.tool.canvasClicked.connect(self.handle_map_click)
            if self.capture_action is not None:
                self.tool.setAction(self.capture_action)
        self.canvas.setMapTool(self.tool)
        self.show_dock()
        self.iface.messageBar().pushMessage(
            "GeoClick Capture",
            "Capture mode is active. Click the map to record a point.",
            level=INFO_LEVEL,
            duration=4,
        )

    def handle_map_click(self, map_point: QgsPointXY, _button):
        project_crs = self.canvas.mapSettings().destinationCrs()
        if not project_crs.isValid():
            self._critical("The project does not have a valid coordinate reference system.")
            return
        try:
            transform = QgsCoordinateTransform(project_crs, WGS84, QgsProject.instance())
            wgs84_point = transform.transform(map_point)
        except Exception as exc:
            self._critical(f"The coordinate could not be transformed: {exc}")
            return

        lon, lat = float(wgs84_point.x()), float(wgs84_point.y())
        source_layer, source_layer_id, source_feature_id = self._identify_source(map_point)
        context = self.dock.capture_context() if self.dock is not None else {}
        context["session_id"] = normalise_session_id(context.get("session_id", ""))
        self.last_coords = (lat, lon)

        project = QgsProject.instance()
        captured_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
            "+00:00", "Z"
        )
        feature_id = self.add_point_to_layer(
            map_point=map_point,
            wgs84_point=wgs84_point,
            captured_at=captured_at,
            project_authid=project_crs.authid() or project_crs.description(),
            project_name=safe_project_name(
                project.fileName(), project.title() or "Untitled project"
            ),
            map_scale=float(self.canvas.scale()),
            source_layer=source_layer,
            source_layer_id=source_layer_id,
            source_feature_id=source_feature_id,
            location="",
            context=context,
        )
        if feature_id is None:
            return

        self.last_feature_id = feature_id
        self._save_preferences()
        self._refresh_dock()
        self.iface.messageBar().pushMessage(
            "Point captured",
            f"{lat:.6f}, {lon:.6f} | {to_dms(lat, 'lat')}, {to_dms(lon, 'lon')}",
            level=SUCCESS_LEVEL,
            duration=6,
        )

        if self.reverse_geocode_action and self.reverse_geocode_action.isChecked():
            self._queue_reverse_geocode(lat, lon, feature_id)

    def _identify_source(self, map_point: QgsPointXY) -> Tuple[str, str, str]:
        layers = [
            layer
            for layer in QgsProject.instance().mapLayers().values()
            if layer.type() == QgsMapLayerType.VectorLayer
        ]
        if not layers:
            return "", "", ""
        identify = QgsMapToolIdentify(self.canvas)
        try:
            results = identify.identify(
                QgsGeometry.fromPointXY(map_point),
                IDENTIFY_TOP_DOWN,
                layers,
                IDENTIFY_VECTOR_LAYER,
            )
        except TypeError:
            canvas_point = self.canvas.getCoordinateTransform().transform(map_point)
            results = identify.identify(
                int(canvas_point.x()),
                int(canvas_point.y()),
                layers,
                IDENTIFY_TOP_DOWN,
            )
        if not results:
            return "", "", ""
        result = results[0]
        feature_id = str(result.mFeature.id()) if result.mFeature.isValid() else ""
        return result.mLayer.name(), result.mLayer.id(), feature_id

    def create_memory_layer(self) -> QgsVectorLayer:
        layer = QgsVectorLayer("Point?crs=EPSG:4326", "Captured Points Log", "memory")
        layer.dataProvider().addAttributes(
            [QgsField(name, field_type) for name, field_type in FIELD_DEFINITIONS]
        )
        layer.updateFields()
        QgsProject.instance().addMapLayer(layer)
        return layer

    def set_destination_layer(self, layer):
        self.layer = layer if layer is not None and layer.isValid() else None
        if self.layer is not None:
            self._set_next_id()
        self._refresh_dock()

    def _prepare_layer(self) -> bool:
        if self.layer is None or not self.layer.isValid():
            self.layer = self.create_memory_layer()
            self.id_counter = 1
            if self.dock is not None:
                self.dock.layer_combo.setLayer(self.layer)
            return True
        if self.layer.geometryType() != POINT_GEOMETRY:
            self._critical("The selected layer is not a point layer.")
            return False
        existing_names = {field.name() for field in self.layer.fields()}
        missing = [
            QgsField(name, field_type)
            for name, field_type in FIELD_DEFINITIONS
            if name not in existing_names
        ]
        if missing and not self.layer.dataProvider().addAttributes(missing):
            self._critical("The required fields could not be added to the selected layer.")
            return False
        if missing:
            self.layer.updateFields()
        return True

    def add_point_to_layer(
        self,
        map_point: QgsPointXY,
        wgs84_point: QgsPointXY,
        captured_at: str,
        project_authid: str,
        project_name: str,
        map_scale: float,
        source_layer: str,
        source_layer_id: str,
        source_feature_id: str,
        location: str,
        context: Dict[str, str],
    ) -> Optional[int]:
        if not self._prepare_layer() or self.layer is None:
            return None
        try:
            layer_point = wgs84_point
            if self.layer.crs().isValid() and self.layer.crs() != WGS84:
                layer_point = QgsCoordinateTransform(
                    WGS84, self.layer.crs(), QgsProject.instance()
                ).transform(wgs84_point)
        except Exception as exc:
            self._critical(f"The point could not be transformed to the layer CRS: {exc}")
            return None

        feature = QgsFeature(self.layer.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(layer_point))
        values: Dict[str, object] = {
            "id": self.id_counter,
            "session_id": context.get("session_id", ""),
            "captured_at": captured_at,
            "operator": context.get("operator", ""),
            "category": context.get("category", "General"),
            "status": context.get("status", "Unreviewed"),
            "note": context.get("note", ""),
            "lat": float(wgs84_point.y()),
            "lon": float(wgs84_point.x()),
            "map_x": float(map_point.x()),
            "map_y": float(map_point.y()),
            "project_crs": project_authid,
            "project_name": project_name,
            "map_scale": map_scale,
            "source_layer": source_layer,
            "source_layer_id": source_layer_id,
            "source_feature_id": source_feature_id,
            "location": location,
        }
        for name, value in values.items():
            index = self.layer.fields().indexOf(name)
            if index >= 0:
                feature.setAttribute(index, value)
        success, added_features = self.layer.dataProvider().addFeatures([feature])
        if not success or not added_features:
            self._critical("The point could not be added to the selected layer.")
            return None
        added_id = int(added_features[0].id())
        self.id_counter += 1
        self.layer.updateExtents()
        self.layer.triggerRepaint()
        return added_id

    def undo_last_capture(self):
        if self.last_feature_id is None:
            self._warning("There is no capture to undo.")
            return
        self.delete_features([self.last_feature_id])
        self.last_feature_id = None

    def delete_features(self, feature_ids: List[int]):
        if self.layer is None or not feature_ids:
            return
        if not self.layer.dataProvider().deleteFeatures(feature_ids):
            self._critical("The selected records could not be deleted.")
            return
        self.layer.updateExtents()
        self.layer.triggerRepaint()
        self._set_next_id()
        self._refresh_dock()

    def clear_session(self):
        if self.layer is None or self.layer.featureCount() == 0:
            return
        answer = QMessageBox.question(
            self.iface.mainWindow(),
            "GeoClick Capture",
            "Delete all records from the current destination layer?",
        )
        if answer != YES_BUTTON:
            return
        self.delete_features([feature.id() for feature in self.layer.getFeatures()])

    def _set_next_id(self):
        if self.layer is None:
            self.id_counter = 1
            return
        index = self.layer.fields().indexOf("id")
        ids = []
        if index >= 0:
            for feature in self.layer.getFeatures():
                try:
                    ids.append(int(feature[index]))
                except (TypeError, ValueError):
                    pass
        self.id_counter = max(ids, default=0) + 1

    def _queue_reverse_geocode(self, lat: float, lon: float, feature_id: int):
        key = geocode_cache_key(lat, lon)
        if key in self._geocode_cache:
            self._apply_location(feature_id, self._geocode_cache[key])
            return
        wait_ms = max(
            0,
            int((1.0 - (time.monotonic() - self._last_geocode_request)) * 1000),
        )
        QTimer.singleShot(
            wait_ms,
            lambda: self._request_reverse_geocode(lat, lon, feature_id, key),
        )

    def _request_reverse_geocode(
        self, lat: float, lon: float, feature_id: int, key: str
    ):
        self._last_geocode_request = time.monotonic()
        parameters = urlencode(
            {
                "lat": f"{lat:.8f}",
                "lon": f"{lon:.8f}",
                "format": "jsonv2",
                "zoom": 18,
                "addressdetails": 0,
            }
        )
        request = QNetworkRequest(
            QUrl(f"https://nominatim.openstreetmap.org/reverse?{parameters}")
        )
        request.setRawHeader(
            b"User-Agent",
            b"GeoClick-Capture/1.2.3 (+https://github.com/Jubilio/qgis-latlon)",
        )
        request.setRawHeader(b"Accept", b"application/json")
        reply = QgsNetworkAccessManager.instance().get(request)
        self._pending_replies.append(reply)
        timeout = QTimer(reply)
        timeout.setSingleShot(True)
        timeout.timeout.connect(reply.abort)
        timeout.start(15000)
        reply.finished.connect(
            lambda r=reply, fid=feature_id, cache_key=key: self._finish_reverse_geocode(
                r, fid, cache_key
            )
        )

    def _finish_reverse_geocode(self, reply, feature_id: int, cache_key: str):
        try:
            if reply.error():
                self.iface.messageBar().pushWarning(
                    "GeoClick Capture", "Reverse geocoding is unavailable."
                )
                return
            payload = json.loads(bytes(reply.readAll()).decode("utf-8"))
            location = str(payload.get("display_name", "")).strip()
            if location:
                self._geocode_cache[cache_key] = location
                self._apply_location(feature_id, location)
                self.iface.messageBar().pushMessage(
                    "Place identified",
                    f"{location} — © OpenStreetMap contributors",
                    level=INFO_LEVEL,
                    duration=7,
                )
        except (ValueError, UnicodeDecodeError, RuntimeError) as exc:
            self.iface.messageBar().pushWarning(
                "GeoClick Capture", f"Invalid geocoding response: {exc}"
            )
        finally:
            if reply in self._pending_replies:
                self._pending_replies.remove(reply)
            reply.deleteLater()

    def _apply_location(self, feature_id: int, location: str):
        if self.layer is None:
            return
        index = self.layer.fields().indexOf("location")
        if index >= 0:
            self.layer.dataProvider().changeAttributeValues(
                {feature_id: {index: location}}
            )
            self.layer.triggerRepaint()
            self._refresh_dock()

    def copy_to_clipboard(self):
        if self.last_coords is None:
            self._warning("No coordinate has been captured yet.")
            return
        lat, lon = self.last_coords
        text = f"{lat:.6f}, {lon:.6f}"
        QGuiApplication.clipboard().setText(text)
        self.iface.messageBar().pushMessage(
            "Copied", text, level=SUCCESS_LEVEL, duration=4
        )

    def export_records(self, output_format: str):
        if not self._has_features():
            return
        if output_format == "csv":
            self._export_csv()
        elif output_format == "geojson":
            self._export_vector("GeoJSON", ".geojson", "GeoJSON (*.geojson)")
        elif output_format == "gpkg":
            self._export_vector("GPKG", ".gpkg", "GeoPackage (*.gpkg)")

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self.iface.mainWindow(), "Save as CSV", "", "CSV (*.csv)"
        )
        if not path:
            return
        path = ensure_extension(path, ".csv")
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as stream:
                writer = csv.writer(stream)
                fields = [field.name() for field in self.layer.fields()]
                writer.writerow(fields)
                for feature in self.layer.getFeatures():
                    writer.writerow([feature[name] for name in fields])
        except OSError as exc:
            self._critical(f"The CSV could not be saved: {exc}")
            return
        self._success(f"CSV saved to: {path}")

    def _export_vector(self, driver: str, extension: str, file_filter: str):
        path, _ = QFileDialog.getSaveFileName(
            self.iface.mainWindow(), "Save layer", "", file_filter
        )
        if not path:
            return
        path = ensure_extension(path, extension)
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = driver
        options.fileEncoding = "UTF-8"
        if driver == "GPKG":
            options.layerName = "capture_log"
        result = QgsVectorFileWriter.writeAsVectorFormatV3(
            self.layer, path, QgsProject.instance().transformContext(), options
        )
        code = result[0] if isinstance(result, tuple) else result
        message = result[1] if isinstance(result, tuple) and len(result) > 1 else ""
        if code == WRITER_NO_ERROR:
            self._success(f"Layer saved to: {path}")
        else:
            self._critical(f"Layer export failed: {message or code}")

    def _load_preferences(self):
        return {
            key: self.settings.value(f"{SETTINGS_PREFIX}/{key}", default)
            for key, default in (
                ("session_id", ""),
                ("operator", ""),
                ("category", "General"),
                ("status", "Unreviewed"),
            )
        }

    def _save_preferences(self):
        if self.dock is None:
            return
        for key, value in self.dock.preference_values().items():
            if key != "note":
                self.settings.setValue(f"{SETTINGS_PREFIX}/{key}", value)

    def _refresh_dock(self):
        if self.dock is not None:
            self.dock.refresh(self.layer)

    def _has_features(self) -> bool:
        if (
            self.layer is None
            or not self.layer.isValid()
            or self.layer.featureCount() == 0
        ):
            self._warning("There are no captured points to export.")
            return False
        return True

    def _success(self, message: str):
        self.iface.messageBar().pushMessage(
            "GeoClick Capture", message, level=SUCCESS_LEVEL, duration=6
        )

    def _warning(self, message: str):
        QMessageBox.warning(self.iface.mainWindow(), "GeoClick Capture", message)

    def _critical(self, message: str):
        QMessageBox.critical(self.iface.mainWindow(), "GeoClick Capture", message)
