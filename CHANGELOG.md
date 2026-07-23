# Changelog

## 1.2.1 — 2026-07-23

- Fixed `Qt.LeftDockWidgetArea` and `Qt.RightDockWidgetArea` compatibility under QGIS 4 / PyQt 6.
- Added Qt 5/Qt 6-safe table selection enums and point-layer filtering.
- Added automatic snapping to visible line and polygon layers.
- Project snapping is respected first; automatic fallback prefers vertices and then segments.
- Added configurable snap tolerance in pixels.
- Added `snapped`, `snap_type` and `snap_distance` audit fields.
- Added a Qt 5/Qt 6-safe clear-session confirmation dialog.

## 1.2.0 — 2026-07-23

- Added the dockable Capture Log panel.
- Added sessions, operator, category, status and notes.
- Added a QGIS point-layer selector and record table.
- Added undo, delete-selected and clear-session actions.
- Added persistent user preferences.
- Added project name, map scale and source feature identifiers.
- Added GeoJSON export.
- Added reverse-geocoding cache, rate limiting, timeout and attribution.
- Expanded metadata and utility tests.

## 1.1.0 — 2026-07-23

- Renamed the public plugin identity to **GeoClick Capture**.
- Repositioned the tool around point logging for field verification and GIS quality assurance.
- Added UTC capture timestamps and original project coordinates.
- Added submission-ready metadata, packaged licence, documentation and sample data.

## 1.0.0 — 2026-07-23

- Corrected CRS handling, layer writing, exports, Qt compatibility and asynchronous reverse geocoding.
