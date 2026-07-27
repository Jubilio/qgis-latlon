"""QGIS plugin entry point."""


def classFactory(iface):
    from .plugin_v140 import GeoClickCapturePluginV140

    return GeoClickCapturePluginV140(iface)
