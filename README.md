# GeoClick Capture

**GeoClick Capture** is a focused QGIS plugin for building auditable point logs during field verification, map review and GIS quality-assurance work.

## Version 1.2.0

The plugin now includes a dockable **Capture Log** panel with:

- capture sessions and operator details;
- category, verification status and notes;
- QGIS point-layer selector;
- table of captured records;
- undo, delete-selected and clear-session actions;
- persistent user preferences;
- CSV, GeoJSON and GeoPackage exports.

Every point records UTC capture time, WGS 84 coordinates, original project coordinates, project name, project CRS, map scale and source-feature context. Optional reverse geocoding is disabled by default and uses `QgsNetworkAccessManager` with caching, a one-request-per-second limit, timeout and OpenStreetMap attribution.

## Installation

Download `geoclick_capture-1.2.0.zip`, then open **QGIS → Plugins → Manage and Install Plugins → Install from ZIP**.

## Usage

1. Open **Vector → GeoClick Capture → Open capture log**.
2. Define the session, operator, category, status and optional note.
3. Select an existing point layer or leave the destination empty to create **Captured Points Log**.
4. Click **Start capture** and click positions on the map.
5. Review, delete, undo or export records from the panel.

## Development

```bash
python -m compileall -q qgis_latlon
python -m unittest discover -s tests -v
```

See the packaged [README](qgis_latlon/README.md), [CHANGELOG](CHANGELOG.md) and [LICENSE](LICENSE).
