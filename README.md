# GeoClick Capture

**GeoClick Capture** is a QGIS plugin for creating auditable point logs during field verification, map review and GIS quality-assurance work.

## Version 1.2.6

This release introduces a coordinated set of transparent toolbar and panel icons for capture, capture log, snapping, reverse geocoding, export, undo, deletion and session management. The new artwork is optimised for QGIS toolbar sizes and is used consistently in the Vector menu and Capture Log dock.

Existing capabilities remain active:

- project snapping with vertex-first and segment fallback;
- session, operator, category, status and note fields;
- CSV, GeoJSON and GeoPackage export;
- reverse-geocoding fallback from detailed address to broader administrative levels;
- QGIS 3.28+ and QGIS 4 / Qt 6 compatibility.

## Installation

Download `geoclick_capture-1.2.6.zip`, then open **QGIS → Plugins → Manage and Install Plugins → Install from ZIP**.

After replacing an older version, restart QGIS or reload the plugin.

## Development

```bash
python -m compileall -q qgis_latlon
python -m unittest discover -s tests -v
```

See the packaged [README](qgis_latlon/README.md), [CHANGELOG](CHANGELOG.md) and [LICENSE](LICENSE).
