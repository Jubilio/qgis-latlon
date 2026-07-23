"""QGIS plugin entry point."""


def classFactory(iface):
    from .plugin_v121 import GeoClickCapturePlugin

    return GeoClickCapturePlugin(iface)
