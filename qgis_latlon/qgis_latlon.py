"""QGIS LatLon plugin implementation."""

from __future__ import annotations

import csv
import json
import os
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


PLUGIN_MENU = "&QGIS LatLon"
WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")
FIELD_DEFINITIONS = (
    ("id", QVariant.Int),
    ("lat", QVariant.Double),
    ("lon", QVariant.Double),
    ("epsg", QVariant.String),
    ("source_layer", QVariant.String),
    ("location", QVariant.String),
)


class QgisLatLonPlugin:
    """Capture map clicks and store their WGS84 coordinates."""

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
            QIcon(icon_path), "Capturar coordenadas", parent
        )
        self.capture_action.setCheckable(True)
        self.capture_action.setToolTip("Clique no mapa para capturar coordenadas")
        self.capture_action.triggered.connect(self.activate)

        self.copy_action = QAction("Copiar última coordenada", parent)
        self.copy_action.triggered.connect(self.copy_to_clipboard)

        self.export_csv_action = QAction("Exportar para CSV", parent)
        self.export_csv_action.triggered.connect(self.export_to_csv)

        self.export_vector_action = QAction(
            "Exportar para GeoPackage/Shapefile", parent
        )
        self.export_vector_action.triggered.connect(self.export_to_vector_file)

        self.reuse_layer_action = QAction(
            "Usar camada de pontos existente", parent
        )
        self.reuse_layer_action.triggered.connect(self.select_existing_layer)

        self.reverse_geocode_action = QAction(
            "Activar geocodificação reversa (OpenStreetMap)", parent
        )
        self.reverse_geocode_action.setCheckable(True)
        self.reverse_geocode_action.setChecked(False)
        self.reverse_geocode_action.setToolTip(
            "Envia latitude e longitude ao serviço Nominatim para obter um nome de local"
        )

        self.iface.addToolBarIcon(self.capture_action)
        for action in self._menu_actions():
            self.iface.addPluginToMenu(PLUGIN_MENU, action)

    def unload(self):
        if self.tool is not None and self.canvas.mapTool() is self.tool:
            self.canvas.unsetMapTool(self.tool)
        if self.capture_action is not None:
            self.iface.removeToolBarIcon(self.capture_action)
        for action in self._menu_actions():
            self.iface.removePluginMenu(PLUGIN_MENU, action)
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
            "QGIS LatLon",
            "Ferramenta activa: clique no mapa para capturar uma coordenada.",
            level=Qgis.Info,
            duration=4,
        )

    def handle_map_click(self, map_point: QgsPointXY, _button):
        project_crs = self.canvas.mapSettings().destinationCrs()
        if not project_crs.isValid():
            self._critical("O projecto não possui um sistema de coordenadas válido.")
            return

        try:
            transform = QgsCoordinateTransform(
                project_crs, WGS84, QgsProject.instance()
            )
            wgs84_point = transform.transform(map_point)
        except Exception as exc:
            self._critical(f"Não foi possível transformar a coordenada: {exc}")
            return

        lon = float(wgs84_point.x())
        lat = float(wgs84_point.y())
        source_layer = self._identify_source_layer(map_point)
        self.last_coords = (lat, lon)

        feature_id = self.add_point_to_layer(
            wgs84_point=wgs84_point,
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
            message += f" | Camada: {source_layer}"
        self.iface.messageBar().pushMessage(
            "Coordenada capturada", message, level=Qgis.Success, duration=8
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
        results = identify.identify(
            QgsGeometry.fromPointXY(map_point),
            QgsMapToolIdentify.TopDownStopAtFirst,
            layers,
            QgsMapToolIdentify.VectorLayer,
        )
        return results[0].mLayer.name() if results else ""

    def create_memory_layer(self) -> QgsVectorLayer:
        layer = QgsVectorLayer(
            "Point?crs=EPSG:4326", "Pontos Capturados", "memory"
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
            self._critical("A camada seleccionada não é uma camada de pontos.")
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
                    "Não foi possível adicionar os campos necessários à camada seleccionada."
                )
                return False
            self.layer.updateFields()
        return True

    def add_point_to_layer(
        self,
        wgs84_point: QgsPointXY,
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
            self._critical(f"Erro ao transformar o ponto para a camada: {exc}")
            return None

        feature = QgsFeature(self.layer.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(layer_point))
        values: Dict[str, object] = {
            "id": self.id_counter,
            "lat": float(wgs84_point.y()),
            "lon": float(wgs84_point.x()),
            "epsg": project_authid,
            "source_layer": source_layer,
            "location": location,
        }
        for name, value in values.items():
            index = self.layer.fields().indexOf(name)
            if index >= 0:
                feature.setAttribute(index, value)

        success, added_features = self.layer.dataProvider().addFeatures([feature])
        if not success or not added_features:
            self._critical("Não foi possível adicionar o ponto à camada seleccionada.")
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
            b"QGIS-LatLon/1.0 (+https://github.com/Jubilio/qgis-latlon)",
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
                    "QGIS LatLon", "A geocodificação reversa não ficou disponível."
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
                    "Local identificado",
                    location,
                    level=Qgis.Info,
                    duration=7,
                )
        except (ValueError, UnicodeDecodeError, RuntimeError) as exc:
            self.iface.messageBar().pushWarning(
                "QGIS LatLon", f"Resposta de geocodificação inválida: {exc}"
            )
        finally:
            if reply in self._pending_replies:
                self._pending_replies.remove(reply)
            reply.deleteLater()

    def copy_to_clipboard(self):
        if self.last_coords is None:
            self._warning("Nenhuma coordenada foi capturada ainda.")
            return
        lat, lon = self.last_coords
        text = f"{lat:.6f}, {lon:.6f}"
        QGuiApplication.clipboard().setText(text)
        self.iface.messageBar().pushMessage(
            "Copiado", text, level=Qgis.Success, duration=4
        )

    def export_to_csv(self):
        if not self._has_features():
            return
        path, _ = QFileDialog.getSaveFileName(
            self.iface.mainWindow(), "Guardar como CSV", "", "CSV (*.csv)"
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
            self._critical(f"Não foi possível guardar o CSV: {exc}")
            return

        self._success(f"CSV guardado em: {path}")

    def export_to_vector_file(self):
        if not self._has_features():
            return
        path, selected_filter = QFileDialog.getSaveFileName(
            self.iface.mainWindow(),
            "Guardar camada",
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
            self._success(f"Camada guardada em: {path}")
        else:
            self._critical(f"Erro ao exportar a camada: {error_message or error_code}")

    def select_existing_layer(self):
        layers = [
            layer
            for layer in QgsProject.instance().mapLayers().values()
            if layer.type() == QgsMapLayerType.VectorLayer
            and layer.geometryType() == QgsWkbTypes.PointGeometry
            and layer.isValid()
        ]
        if not layers:
            self._warning("Não existem camadas de pontos disponíveis no projecto.")
            return

        labels = [f"{layer.name()} — {layer.crs().authid()}" for layer in layers]
        selected, ok = QInputDialog.getItem(
            self.iface.mainWindow(),
            "Seleccionar camada",
            "Camada onde os novos pontos serão adicionados:",
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
        self._success(f"Camada seleccionada: {self.layer.name()}")

    def _has_features(self) -> bool:
        if self.layer is None or not self.layer.isValid() or self.layer.featureCount() == 0:
            self._warning("Não existem pontos capturados para exportar.")
            return False
        return True

    def _success(self, message: str):
        self.iface.messageBar().pushMessage(
            "QGIS LatLon", message, level=Qgis.Success, duration=6
        )

    def _warning(self, message: str):
        QMessageBox.warning(self.iface.mainWindow(), "QGIS LatLon", message)

    def _critical(self, message: str):
        QMessageBox.critical(self.iface.mainWindow(), "QGIS LatLon", message)
