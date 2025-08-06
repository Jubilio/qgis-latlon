from qgis.PyQt.QtCore import QObject, pyqtSignal, QMimeData
from qgis.PyQt.QtWidgets import QAction, QMessageBox, QFileDialog, QInputDialog
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsPointXY, QgsFeature, QgsGeometry,
    QgsFields, QgsField, QgsWkbTypes, QgsMapLayerType, QgsMapToolIdentify, QgsVectorFileWriter,
    QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsCoordinateTransformContext
)
from qgis.gui import QgsMapToolEmitPoint
from PyQt5.QtGui import QIcon, QGuiApplication
from PyQt5.QtCore import QVariant
import os
import csv


class QgisLatLonPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.action = None
        self.tool = None
        self.layer = None
        self.copy_action = None
        self.export_action = None
        self.export_gpkg_action = None
        self.reuse_layer_action = None
        self.id_counter = 1

    def initGui(self):
        icon_path = os.path.join(
            os.path.dirname(__file__), 'icons', 'icon.png')
        self.action = QAction(
            QIcon(icon_path), "LatLon Click Capture", self.iface.mainWindow())
        self.action.triggered.connect(self.activate)

        self.copy_action = QAction(
            "Copiar Última Coordenada", self.iface.mainWindow())
        self.copy_action.triggered.connect(self.copy_to_clipboard)

        self.export_action = QAction(
            "Exportar para CSV", self.iface.mainWindow())
        self.export_action.triggered.connect(self.export_to_csv)

        self.export_gpkg_action = QAction(
            "Exportar para Shapefile/GeoPackage", self.iface.mainWindow())
        self.export_gpkg_action.triggered.connect(self.export_to_vector_file)

        self.reuse_layer_action = QAction(
            "Selecionar camada existente para adicionar pontos", self.iface.mainWindow())
        self.reuse_layer_action.triggered.connect(self.select_existing_layer)

        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&LatLon Plugin", self.action)
        self.iface.addPluginToMenu("&LatLon Plugin", self.copy_action)
        self.iface.addPluginToMenu("&LatLon Plugin", self.export_action)
        self.iface.addPluginToMenu("&LatLon Plugin", self.export_gpkg_action)
        self.iface.addPluginToMenu("&LatLon Plugin", self.reuse_layer_action)

    def unload(self):
        self.iface.removeToolBarIcon(self.action)
        self.iface.removePluginMenu("&LatLon Plugin", self.action)
        self.iface.removePluginMenu("&LatLon Plugin", self.copy_action)
        self.iface.removePluginMenu("&LatLon Plugin", self.export_action)
        self.iface.removePluginMenu("&LatLon Plugin", self.export_gpkg_action)
        self.iface.removePluginMenu("&LatLon Plugin", self.reuse_layer_action)

    def activate(self):
        self.tool = QgsMapToolEmitPoint(self.canvas)
        self.tool.canvasClicked.connect(self.handle_map_click)
        self.canvas.setMapTool(self.tool)

    def to_dms(self, value, coord_type):
        is_positive = value >= 0
        abs_value = abs(value)
        degrees = int(abs_value)
        minutes_float = (abs_value - degrees) * 60
        minutes = int(minutes_float)
        seconds = (minutes_float - minutes) * 60
        direction = {'lat': ('N', 'S'), 'lon': ('E', 'W')}
        suffix = direction[coord_type][0 if is_positive else 1]
        return f"{degrees}°{minutes}'{seconds:.2f}\"{suffix}"

    def handle_map_click(self, point, button):
        lon = point.x()
        lat = point.y()
        epsg = self.canvas.mapSettings().destinationCrs().authid()

        layer_name = ""
        identify = QgsMapToolIdentify(self.canvas)
        results = identify.identify(point, QgsMapToolIdentify.TopDownStopAtFirst, [
                                    layer for layer in QgsProject.instance().mapLayers().values() if layer.type() == QgsMapLayerType.VectorLayer])
        if results:
            layer_name = results[0].mLayer.name()

        lat_dms = self.to_dms(lat, 'lat')
        lon_dms = self.to_dms(lon, 'lon')

        reverse_geocode = self.reverse_lookup(lat, lon)

        QMessageBox.information(self.iface.mainWindow(), "Coordenadas Capturadas",
                                f"Latitude: {lat} ({lat_dms})\nLongitude: {lon} ({lon_dms})\nEPSG: {epsg}\nCamada: {layer_name if layer_name else 'nenhuma'}\nLocal: {reverse_geocode}")

        self.last_coords = (lat, lon)
        self.add_point_to_layer(lon, lat, epsg, layer_name, reverse_geocode)

    def create_memory_layer(self):
        layer = QgsVectorLayer("Point?crs=EPSG:4326",
                               "Pontos Capturados", "memory")
        prov = layer.dataProvider()
        fields = [
            QgsField("id", QVariant.Int),
            QgsField("lat", QVariant.Double),
            QgsField("lon", QVariant.Double),
            QgsField("epsg", QVariant.String),
            QgsField("source_layer", QVariant.String),
            QgsField("location", QVariant.String)
        ]
        prov.addAttributes(fields)
        layer.updateFields()
        QgsProject.instance().addMapLayer(layer)
        return layer

    def add_point_to_layer(self, lon, lat, epsg, layer_name, location):
        if self.layer is None:
            self.layer = self.create_memory_layer()

        prov = self.layer.dataProvider()
        feat = QgsFeature(self.layer.fields())
        feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(lon, lat)))
        feat.setAttributes([
            self.id_counter,
            lat,
            lon,
            epsg,
            layer_name,
            location
        ])
        self.id_counter += 1

        prov.addFeatures([feat])
        self.layer.updateExtents()
        self.layer.triggerRepaint()
        self.layer.updateFields()

    def reverse_lookup(self, lat, lon):
        try:
            import requests
            url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
            headers = {'User-Agent': 'QGIS LatLon Plugin'}
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                return data.get('display_name', 'desconhecido')
            else:
                return 'falha na consulta'
        except Exception as e:
            return 'erro: ' + str(e)

    def copy_to_clipboard(self):
        if hasattr(self, 'last_coords'):
            lat, lon = self.last_coords
            text = f"{lat}, {lon}"
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(text)
            QMessageBox.information(self.iface.mainWindow(
            ), "Copiado", f"Coordenadas copiadas: {text}")
        else:
            QMessageBox.warning(self.iface.mainWindow(
            ), "Sem coordenadas", "Nenhuma coordenada capturada ainda.")

    def export_to_csv(self):
        if self.layer is None or self.layer.featureCount() == 0:
            QMessageBox.warning(self.iface.mainWindow(
            ), "Nada para exportar", "Nenhum ponto capturado para exportar.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self.iface.mainWindow(), "Salvar como CSV", "", "CSV Files (*.csv)")
        if not path:
            return

        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([field.name() for field in self.layer.fields()])
            for feat in self.layer.getFeatures():
                writer.writerow([feat[field.name()]
                                for field in self.layer.fields()])

        QMessageBox.information(self.iface.mainWindow(),
                                "Exportação", f"Exportado para: {path}")

    def export_to_vector_file(self):
        if self.layer is None or self.layer.featureCount() == 0:
            QMessageBox.warning(self.iface.mainWindow(
            ), "Nada para exportar", "Nenhum ponto capturado para exportar.")
            return

        path, _ = QFileDialog.getSaveFileName(self.iface.mainWindow(
        ), "Salvar como", "", "GeoPackage (*.gpkg);;Shapefile (*.shp)")
        if not path:
            return

        ext = os.path.splitext(path)[1].lower()
        driver = "GPKG" if ext == ".gpkg" else "ESRI Shapefile"

        error = QgsVectorFileWriter.writeAsVectorFormat(
            self.layer, path, "utf-8", self.layer.crs(), driver)
        if error[0] == QgsVectorFileWriter.NoError:
            QMessageBox.information(self.iface.mainWindow(
            ), "Exportação", f"Arquivo salvo em: {path}")
        else:
            QMessageBox.critical(self.iface.mainWindow(),
                                 "Erro", f"Erro ao exportar: {error[1]}")

    def select_existing_layer(self):
        layers = [layer for layer in QgsProject.instance().mapLayers().values() if layer.type(
        ) == QgsMapLayerType.VectorLayer and layer.geometryType() == QgsWkbTypes.PointGeometry]
        if not layers:
            QMessageBox.warning(self.iface.mainWindow(
            ), "Sem camadas", "Nenhuma camada vetorial de pontos disponível.")
            return

        items = [layer.name() for layer in layers]
        item, ok = QInputDialog.getItem(self.iface.mainWindow(
        ), "Selecionar camada", "Escolha uma camada para adicionar os pontos:", items, 0, False)

        if ok and item:
            for layer in layers:
                if layer.name() == item:
                    self.layer = layer
                    QMessageBox.information(self.iface.mainWindow(
                    ), "Camada Selecionada", f"Agora adicionando pontos na camada: {item}")
                    return
