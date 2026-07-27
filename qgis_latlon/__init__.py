"""QGIS plugin entry point."""


def classFactory(iface):
    from .plugin_v130_policy import GeoClickCapturePluginV130Policy

    return GeoClickCapturePluginV130Policy(iface)
