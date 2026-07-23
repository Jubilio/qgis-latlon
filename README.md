# GeoClick Capture

**GeoClick Capture** is a QGIS plugin for creating auditable point logs during field verification, map review and GIS quality-assurance work.

## Version 1.2.1

This version fixes loading under **QGIS 4 / Qt 6** and adds automatic geometry snapping:

- project snapping is used first;
- if no project match is found, visible line and polygon layers are searched;
- nearby vertices are preferred;
- the closest segment is used when no vertex is within tolerance;
- snap tolerance is configurable in screen pixels;
- `snapped`, `snap_type` and `snap_distance` are stored in the output layer.

The Capture Log panel also includes sessions, operator/category/status/notes, point-layer selection, undo/delete/clear actions and CSV, GeoJSON and GeoPackage exports.

## Installation

Download `geoclick_capture-1.2.1.zip`, then open **QGIS → Plugins → Manage and Install Plugins → Install from ZIP**.

After replacing version 1.2.0, restart QGIS or reload the plugin.

## Development

```bash
python -m compileall -q qgis_latlon
python -m unittest discover -s tests -v
```

See the packaged [README](qgis_latlon/README.md), [CHANGELOG](CHANGELOG.md) and [LICENSE](LICENSE).
