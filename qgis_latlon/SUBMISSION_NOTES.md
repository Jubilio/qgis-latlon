# QGIS Plugin Repository submission notes

GeoClick Capture is intentionally scoped as a lightweight point-logging tool for field verification, map review and GIS quality assurance. It does not aim to replace comprehensive coordinate conversion, zooming or grid-reference plugins.

The submission package:

- contains one top-level folder: `qgis_latlon`;
- includes `metadata.txt`, `__init__.py`, `LICENSE` and `README.md`;
- has no external Python dependencies or binary executables;
- uses `QgsNetworkAccessManager` for optional reverse geocoding;
- works locally when reverse geocoding is disabled;
- is built and tested by GitHub Actions;
- includes a minimal GeoJSON dataset for testing.
