# Changelog

## 1.0.0 — 2026-07-23

- Fixed the invalid `QgsMapToolIdentify` import.
- Replaced direct PyQt5 imports with `qgis.PyQt` for Qt 5/Qt 6 compatibility.
- Added correct transformation from the project CRS to WGS 84.
- Added correct transformation when writing to an existing layer in another CRS.
- Added missing-field validation for reused point layers.
- Prevented duplicate IDs when an existing layer is selected.
- Replaced the deprecated vector export call with `writeAsVectorFormatV3`.
- Improved file-extension handling and CSV Unicode compatibility.
- Replaced blocking `requests` geocoding with optional asynchronous QGIS networking.
- Replaced modal capture popups with QGIS message-bar notifications.
- Corrected plugin package naming to `qgis_latlon`.
- Added metadata, tests, documentation and a new SVG icon.
