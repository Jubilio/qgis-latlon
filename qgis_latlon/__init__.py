"""QGIS plugin entry point."""


def classFactory(iface):
    from .qgis_latlon import QgisLatLonPlugin

    return QgisLatLonPlugin(iface)
