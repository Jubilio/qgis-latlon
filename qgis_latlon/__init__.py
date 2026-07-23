"""QGIS plugin entry point."""


def classFactory(iface):
    from .plugin_v125 import GeoClickCapturePluginV125

    return GeoClickCapturePluginV125(iface)
