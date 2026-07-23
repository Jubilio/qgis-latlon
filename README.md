# GeoClick Capture

**GeoClick Capture** is a QGIS plugin for creating auditable point logs during field verification, map review and GIS quality-assurance work.

## Version 1.2.2

This maintenance release corrects the automated Qt compatibility test. Version 1.2.1 already removed executable use of the Qt 5-only dock-area aliases, but the previous test also searched comments and therefore produced a false failure in GitHub Actions.

The test now parses the Python source and inspects executable attribute access only. QGIS 4 / Qt 6 compatibility and automatic geometry snapping remain unchanged:

- project snapping is used first;
- if no project match is found, visible line and polygon layers are searched;
- nearby vertices are preferred;
- the closest segment is used when no vertex is within tolerance;
- snap tolerance is configurable in screen pixels;
- `snapped`, `snap_type` and `snap_distance` are stored in the output layer.

The Capture Log panel also includes sessions, operator/category/status/notes, point-layer selection, undo/delete/clear actions and CSV, GeoJSON and GeoPackage exports.

## Installation

Download `geoclick_capture-1.2.2.zip`, then open **QGIS → Plugins → Manage and Install Plugins → Install from ZIP**.

After replacing an older version, restart QGIS or reload the plugin.

## Development

```bash
python -m compileall -q qgis_latlon
python -m unittest discover -s tests -v
```

See the packaged [README](qgis_latlon/README.md), [CHANGELOG](CHANGELOG.md) and [LICENSE](LICENSE).
