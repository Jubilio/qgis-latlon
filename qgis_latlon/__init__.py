"""QGIS plugin entry point."""


def classFactory(iface):
    from .plugin_v160 import GeoClickCapturePluginV160

    return GeoClickCapturePluginV160(iface)
