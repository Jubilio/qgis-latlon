"""QGIS plugin entry point."""


def classFactory(iface):
    from .plugin_v201 import GeoClickCapturePluginV201

    return GeoClickCapturePluginV201(iface)
