# Changelog

## 1.1.0 — 2026-07-23

- Renamed the public plugin identity to **GeoClick Capture** to avoid confusion with broad coordinate-conversion suites.
- Repositioned the tool around point logging for field verification and GIS quality assurance.
- Added UTC capture timestamps.
- Added original project X/Y coordinates and project CRS to each record.
- Moved plugin actions to the QGIS **Vector** menu.
- Added `license` and multiline `changelog` metadata.
- Added the licence and README inside the installable plugin folder.
- Added a minimal GeoJSON dataset for testing.
- Updated the build artifact name and submission documentation.

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
