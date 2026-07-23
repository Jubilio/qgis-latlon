"""QGIS plugin entry point."""


def classFactory(iface):
    from .plugin_v124 import GeoClickCapturePluginV124

    return GeoClickCapturePluginV124(iface)
