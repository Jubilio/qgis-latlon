"""QGIS plugin entry point."""


def classFactory(iface):
    from .plugin_v150 import GeoClickCapturePluginV150

    return GeoClickCapturePluginV150(iface)
