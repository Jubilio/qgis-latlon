def classFactory(iface):
    from .qgis_latlon import QgisLatLonPlugin
    return QgisLatLonPlugin(iface)