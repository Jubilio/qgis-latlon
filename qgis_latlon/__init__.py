"""QGIS plugin entry point."""


def classFactory(iface):
    from .plugin_v126 import GeoClickCapturePluginV126

    return GeoClickCapturePluginV126(iface)
