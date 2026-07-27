"""QGIS plugin entry point."""


def classFactory(iface):
    from .plugin_v200 import GeoClickCapturePluginV200

    return GeoClickCapturePluginV200(iface)
