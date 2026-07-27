"""QGIS plugin entry point."""


def classFactory(iface):
    from .plugin_v130 import GeoClickCapturePluginV130

    return GeoClickCapturePluginV130(iface)
