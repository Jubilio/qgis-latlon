# GeoClick Capture

**GeoClick Capture** builds auditable point logs for field verification, map review and GIS quality assurance.

## Version 1.2.5

Reverse geocoding now treats `Unable to geocode` as a valid no-result response rather than a connection failure. The plugin first requests a detailed address and then tries broader OpenStreetMap levels: settlement, city, state or province, and country.

If a broader result is found, it is stored as an approximate place name. When OpenStreetMap has no suitable address or administrative object, the point remains saved without a place name and a clear message is shown.

The QGIS 4 / Qt 6 correction and automatic snapping remain active. The plugin respects project snapping first, then searches visible line and polygon layers, preferring the nearest vertex and falling back to the nearest segment within the configured pixel tolerance.

The **Capture Log** panel provides:

- session, operator, category, status and note fields;
- a destination point-layer selector;
- start/stop capture, undo, delete and clear actions;
- snapping enable/disable and pixel tolerance controls;
- CSV, GeoJSON and GeoPackage exports;
- optional reverse geocoding through `QgsNetworkAccessManager`.

Captured records include UTC time, WGS 84 coordinates, project coordinates, project information, source-feature context and the snapping audit fields `snapped`, `snap_type` and `snap_distance`.

## Installation

1. Open **QGIS → Plugins → Manage and Install Plugins → Install from ZIP**.
2. Select `geoclick_capture-1.2.5.zip`.
3. Restart or reload the plugin after replacing an older installation.

## Usage

1. Open **Vector → GeoClick Capture → Open capture log**.
2. Define the session information and destination point layer.
3. Keep **Snap to line/polygon vertices and segments** enabled.
4. Set the snap tolerance in screen pixels; 12 px is the default.
5. Start capture and click near a line or polygon vertex or edge.

## Compatibility

- QGIS 3.28 or later
- QGIS 4.x / Qt 6
- Windows, Linux and macOS
- No external Python dependencies

## Licence

MIT License.
