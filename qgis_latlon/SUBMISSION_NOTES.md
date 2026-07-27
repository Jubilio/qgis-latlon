# QGIS Plugin Repository submission notes

GeoClick Capture 2.0.0 is a location-verification and capture workspace for field verification, map review and GIS quality assurance. It combines online and offline place discovery, source matching, review decisions, evidence management and auditable reporting without replacing general-purpose coordinate-conversion or data-quality frameworks.

The submission package:

- contains one top-level folder: `qgis_latlon`;
- includes `metadata.txt`, `__init__.py`, `LICENSE`, documentation and sample CSV files;
- has no external Python dependencies or binary executables;
- uses `QgsNetworkAccessManager` for optional Nominatim search and reverse geocoding;
- keeps coordinate parsing, Offline Gazetteer, Review Queue and Location Verification Workspace usable without Internet access;
- hashes local evidence files with SHA-256 and copies them only when the user explicitly exports a verification bundle;
- persists the active workspace as a QGIS project custom property;
- supports QGIS 3.28+ and QGIS 4 / Qt 6;
- is compiled, tested and packaged by GitHub Actions.
