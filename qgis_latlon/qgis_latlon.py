"""GeoClick Capture plugin implementation."""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional
from urllib.parse import urlencode

from qgis.PyQt.QtCore import QUrl, QVariant
from qgis.PyQt.QtGui import QGuiApplication, QIcon
from qgis.PyQt.QtNetwork import QNetworkRequest
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QInputDialog, QMessageBox
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
    QgsVectorFileWriter,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.gui import QgsMapToolEmitPoint, QgsMapToolIdentify

from .utils import ensure_extension, to_dms


PLUGIN_MENU = "&GeoClick Capture"
WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")
FIELD_DEFINITIONS = (
    ("id", QVariant.Int),
    ("captured_at", QVariant.String),
    ("lat", QVariant.Double),
    ("lon", QVariant.Double),
    ("map_x", QVariant.Double),
    ("map_y", QVariant.Double),
    ("project_crs", QVariant.String),
    ("source_layer", QVariant.String),
    ("location", QVariant.String),
)


class QgisLatLonPlugin:
    """Log map clicks as auditable point records."""

    def __init__(self, iface):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.capture_action: Optional[QAction] = None
        self.copy_action: Optional[QAction] = None
        self.export_csv_action: Optional[QAction] = None
        self.export_vector_action: Optional[QAction] = None
        self.reuse_layer_action: Optional[QAction] = None
        self.reverse_geocode_action: Optional[QAction] = None
        self.tool: Optional[QgsMapToolEmitPoint] = None
        self.layer: Optional[QgsVectorLayer] = None
        self.last_coords: Optional[tuple[float, float]] = None
        self._pending_replies: List[object] = []
        self.id_counter = 1

    def initGui(self):
        icon_path = os.path.join(os.path.dirname(__file__), "icons", "icon.svg")
        parent = self.iface.mainWindow()

        self.capture_action = QAction(
            QIcon(icon_path), "Capture point", parent
        )
        self.capture_action.setCheckable(True)
        self.capture_action.setToolTip("Click the map to record a point")
        self.capture_action.triggered.connect(self.activate)

        self.copy_action = QAction("Copy last coordinate", parent)
        self.copy_action.triggered.connect(self.copy_to_clipboard)

        self.export_csv_action = QAction("Export to CSV", parent)
        self.export_csv_action.triggered.connect(self.export_to_csv)

        self.export_vector_action = QAction(
            "Export to GeoPackage/Shapefile", parent
        )
        self.export_vector_action.triggered.connect(self.export_to_vector_file)

        self.reuse_layer_action = QAction(
            "Use existing point layer", parent
        )
        self.reuse_layer_action.triggered.connect(self.select_existing_layer)

        self.reverse_geocode_action = QAction(
            "Enable reverse geocoding (OpenStreetMap)", parent
        )
        self.reverse_geocode_action.setCheckable(True)
        self.reverse_geocode_action.setChecked(False)
        self.reverse_geocode_action.setToolTip(
            "Sends WGS 84 coordinates to Nominatim to retrieve a place name"
        )

        self.iface.addToolBarIcon(self.capture_action)
        for action in self._menu_actions():
            self.iface.addPluginToVectorMenu(PLUGIN_MENU, action)

    def unload(self):
        if self.tool is not None and self.canvas.mapTool() is self.tool:
            self.canvas.unsetMapTool(self.tool)
        if self.capture_action is not None:
            self.iface.removeToolBarIcon(self.capture_action)
        for action in self._menu_actions():
            self.iface.removePluginVectorMenu(PLUGIN_MENU, action)
        self._pending_replies.clear()

    def _menu_actions(self) -> List[QAction]:
        return [
            action
            for action in (
                self.capture_action,
                self.copy_action,
                self.export_csv_action,
                self.export_vector_action,
                self.reuse_layer_action,
                self.reverse_geocode_action,
            )
            if action is not None
        ]

    def activate(self, checked: bool = True):
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
        self.iface.messageBar().pushMessage(
            "GeoClick Capture",
            "Capture mode is active. Click the map to record a point.",
            level=Qgis.Info,
            duration=4,
        )

    def handle_map_click(self, map_point: QgsPointXY, _button):
        project_crs = self.canvas.mapSettings().destinationCrs()
        if not project_crs.isValid():
            self._critical("The project does not have a valid coordinate reference system.")
            return

        try:
            transform = QgsCoordinateTransform(
                project_crs, WGS84, QgsProject.instance()
            )
            wgs84_point = transform.transform(map_point)
        except Exception as exc:  # QgsCsException differs across QGIS versions
            self._critical(f"The coordinate could not be transformed: {exc}")
            return

        lon = float(wgs84_point.x())
        lat = float(wgs84_point.y())
        source_layer = self._identify_source_layer(map_point)
        self.last_coords = (lat, lon)

        captured_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        feature_id = self.add_point_to_layer(
            map_point=map_point,
            wgs84_point=wgs84_point,
            captured_at=captured_at,
            project_authid=project_crs.authid() or project_crs.description(),
            source_layer=source_layer,
            location="",
        )
        if feature_id is None:
            return

        message = (
            f"{lat:.6f}, {lon:.6f} | "
            f"{to_dms(lat, 'lat')}, {to_dms(lon, 'lon')}"
        )
        if source_layer:
            message += f" | Layer: {source_layer}"
        self.iface.messageBar().pushMessage(
            "Point captured", message, level=Qgis.Success, duration=8
        )

        if self.reverse_geocode_action and self.reverse_geocode_action.isChecked():
            self._request_reverse_geocode(lat, lon, feature_id)

    def _identify_source_layer(self, map_point: QgsPointXY) -> str:
        layers = [
            layer
            for layer in QgsProject.instance().mapLayers().values()
            if layer.type() == QgsMapLayerType.VectorLayer
        ]
        if not layers:
            return ""

        identify = QgsMapToolIdentify(self.canvas)
        try:
            results = identify.identify(
                QgsGeometry.fromPointXY(map_point),
                QgsMapToolIdentify.TopDownStopAtFirst,
                layers,
                QgsMapToolIdentify.VectorLayer,
            )
        except TypeError:
            # Compatibility fallback for older QGIS 3 builds.
            canvas_point = self.canvas.getCoordinateTransform().transform(map_point)
            results = identify.identify(
                int(canvas_point.x()),
                int(canvas_point.y()),
                layers,
                QgsMapToolIdentify.TopDownStopAtFirst,
            )
        return results[0].mLayer.name() if results else ""

    def create_memory_layer(self) -> QgsVectorLayer:
        layer = QgsVectorLayer(
            "Point?crs=EPSG:4326", "Captured Points Log", "memory"
        )
        provider = layer.dataProvider()
        provider.addAttributes(
            [QgsField(name, field_type) for name, field_type in FIELD_DEFINITIONS]
        )
        layer.updateFields()
        QgsProject.instance().addMapLayer(layer)
        return layer

    def _prepare_layer(self) -> bool:
        if self.layer is None or not self.layer.isValid():
            self.layer = self.create_memory_layer()
            self.id_counter = 1
            return True

        if self.layer.geometryType() != QgsWkbTypes.PointGeometry:
            self._critical("The selected layer is not a point layer.")
            return False

        existing_names = {field.name() for field in self.layer.fields()}
        missing = [
            QgsField(name, field_type)
            for name, field_type in FIELD_DEFINITIONS
            if name not in existing_names
        ]
        if missing:
            if not self.layer.dataProvider().addAttributes(missing):
                self._critical(
                    "The required fields could not be added to the selected layer."
                )
                return False
            self.layer.updateFields()
        return True

    def add_point_to_layer(
        self,
        map_point: QgsPointXY,
        wgs84_point: QgsPointXY,
        captured_at: str,
        project_authid: str,
        source_layer: str,
        location: str,
    ) -> Optional[int]:
        if not self._prepare_layer() or self.layer is None:
            return None

        try:
            layer_point = wgs84_point
            if self.layer.crs().isValid() and self.layer.crs() != WGS84:
                transform = QgsCoordinateTransform(
                    WGS84, self.layer.crs(), QgsProject.instance()
                )
                layer_point = transform.transform(wgs84_point)
        except Exception as exc:
            self._critical(f"The point could not be transformed to the layer CRS: {exc}")
            return None

        feature = QgsFeature(self.layer.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(layer_point))
        values: Dict[str, object] = {
            "id": self.id_counter,
            "captured_at": captured_at,
            "lat": float(wgs84_point.y()),
            "lon": float(wgs84_point.x()),
            "map_x": float(map_point.x()),
            "map_y": float(map_point.y()),
            "project_crs": project_authid,
            "source_layer": source_layer,
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

        added_feature = added_features[0]
        self.id_counter += 1
        self.layer.updateExtents()
        self.layer.triggerRepaint()
        return int(added_feature.id())

    def _request_reverse_geocode(self, lat: float, lon: float, feature_id: int):
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
            b"GeoClick-Capture/1.1 (+https://github.com/Jubilio/qgis-latlon)",
        )
        request.setRawHeader(b"Accept", b"application/json")

        reply = QgsNetworkAccessManager.instance().get(request)
        self._pending_replies.append(reply)
        reply.finished.connect(
            lambda r=reply, fid=feature_id: self._finish_reverse_geocode(r, fid)
        )

    def _finish_reverse_geocode(self, reply, feature_id: int):
        try:
            if reply.error():
                self.iface.messageBar().pushWarning(
                    "GeoClick Capture", "Reverse geocoding is currently unavailable."
                )
                return
            payload = json.loads(bytes(reply.readAll()).decode("utf-8"))
            location = str(payload.get("display_name", "")).strip()
            if not location or self.layer is None:
                return
            location_index = self.layer.fields().indexOf("location")
            if location_index >= 0:
                self.layer.dataProvider().changeAttributeValues(
                    {feature_id: {location_index: location}}
                )
                self.layer.triggerRepaint()
                self.iface.messageBar().pushMessage(
                    "Place identified",
                    location,
                    level=Qgis.Info,
                    duration=7,
                )
        except (ValueError, UnicodeDecodeError, RuntimeError) as exc:
            self.iface.messageBar().pushWarning(
                "GeoClick Capture", f"Invalid reverse-geocoding response: {exc}"
            )
        finally:
            if reply in self._pending_replies:
                self._pending_replies.remove(reply)
            reply.deleteLater()

    def copy_to_clipboard(self):
        if self.last_coords is None:
            self._warning("No coordinate has been captured yet.")
            return
        lat, lon = self.last_coords
        text = f"{lat:.6f}, {lon:.6f}"
        QGuiApplication.clipboard().setText(text)
        self.iface.messageBar().pushMessage(
            "Copied", text, level=Qgis.Success, duration=4
        )

    def export_to_csv(self):
        if not self._has_features():
            return
        path, _ = QFileDialog.getSaveFileName(
            self.iface.mainWindow(), "Save as CSV", "", "CSV (*.csv)"
        )
        if not path:
            return
        path = ensure_extension(path, ".csv")

        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as stream:
                writer = csv.writer(stream)
                field_names = [field.name() for field in self.layer.fields()]
                writer.writerow(field_names)
                for feature in self.layer.getFeatures():
                    writer.writerow([feature[name] for name in field_names])
        except OSError as exc:
            self._critical(f"The CSV could not be saved: {exc}")
            return

        self._success(f"CSV saved to: {path}")

    def export_to_vector_file(self):
        if not self._has_features():
            return
        path, selected_filter = QFileDialog.getSaveFileName(
            self.iface.mainWindow(),
            "Save layer",
            "",
            "GeoPackage (*.gpkg);;Shapefile (*.shp)",
        )
        if not path:
            return

        is_gpkg = "GeoPackage" in selected_filter or path.lower().endswith(".gpkg")
        path = ensure_extension(path, ".gpkg" if is_gpkg else ".shp")
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "GPKG" if is_gpkg else "ESRI Shapefile"
        options.fileEncoding = "UTF-8"
        if is_gpkg:
            options.layerName = "captured_points"

        error = QgsVectorFileWriter.writeAsVectorFormatV3(
            self.layer,
            path,
            QgsProject.instance().transformContext(),
            options,
        )
        error_code = error[0] if isinstance(error, tuple) else error
        error_message = error[1] if isinstance(error, tuple) and len(error) > 1 else ""
        if error_code == QgsVectorFileWriter.NoError:
            self._success(f"Layer saved to: {path}")
        else:
            self._critical(f"Layer export failed: {error_message or error_code}")

    def select_existing_layer(self):
        layers = [
            layer
            for layer in QgsProject.instance().mapLayers().values()
            if layer.type() == QgsMapLayerType.VectorLayer
            and layer.geometryType() == QgsWkbTypes.PointGeometry
            and layer.isValid()
        ]
        if not layers:
            self._warning("There are no valid point layers in the project.")
            return

        labels = [f"{layer.name()} — {layer.crs().authid()}" for layer in layers]
        selected, ok = QInputDialog.getItem(
            self.iface.mainWindow(),
            "Select layer",
            "Layer where new points will be added:",
            labels,
            0,
            False,
        )
        if not ok or not selected:
            return

        index = labels.index(selected)
        self.layer = layers[index]
        id_index = self.layer.fields().indexOf("id")
        existing_ids = []
        if id_index >= 0:
            for feature in self.layer.getFeatures():
                value = feature[id_index]
                if value is not None:
                    try:
                        existing_ids.append(int(value))
                    except (TypeError, ValueError):
                        pass
        self.id_counter = max(existing_ids, default=0) + 1
        self._success(f"Selected layer: {self.layer.name()}")

    def _has_features(self) -> bool:
        if self.layer is None or not self.layer.isValid() or self.layer.featureCount() == 0:
            self._warning("There are no captured points to export.")
            return False
        return True

    def _success(self, message: str):
        self.iface.messageBar().pushMessage(
            "GeoClick Capture", message, level=Qgis.Success, duration=6
        )

    def _warning(self, message: str):
        QMessageBox.warning(self.iface.mainWindow(), "GeoClick Capture", message)

    def _critical(self, message: str):
        QMessageBox.critical(self.iface.mainWindow(), "GeoClick Capture", message)
