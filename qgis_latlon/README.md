# GeoClick Capture

**GeoClick Capture** builds auditable point logs for field verification, map review and GIS quality assurance.

## Version 1.2.1

This release fixes QGIS 4 / Qt 6 dock-widget compatibility and adds automatic snapping. The plugin first respects the QGIS project snapping configuration. When no project match is returned, it searches visible line and polygon layers, preferring the nearest vertex and falling back to the nearest segment within a configurable pixel tolerance.

The **Capture Log** panel provides:

- session, operator, category, status and note fields;
- a destination point-layer selector;
- start/stop capture, undo, delete and clear actions;
- CSV, GeoJSON and GeoPackage exports;
- optional reverse geocoding through `QgsNetworkAccessManager`.

Captured records include UTC time, WGS 84 coordinates, project coordinates, project information, source-feature context and the snapping audit fields `snapped`, `snap_type` and `snap_distance`.

## Installation

1. Open **QGIS → Plugins → Manage and Install Plugins → Install from ZIP**.
2. Select `geoclick_capture-1.2.1.zip`.
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
