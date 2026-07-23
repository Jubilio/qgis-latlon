# GeoClick Capture

**GeoClick Capture** is a lightweight QGIS plugin for logging map clicks as auditable point records. It is designed for field verification, map review and GIS quality-assurance workflows rather than general coordinate-format conversion.

## Main features

- Captures a map click from any project CRS.
- Stores WGS 84 latitude and longitude.
- Stores the original project coordinates and project CRS.
- Adds a UTC capture timestamp to every record.
- Identifies the first vector layer below the clicked position.
- Creates a temporary point layer or appends to an existing point layer.
- Copies the most recently captured coordinate to the clipboard.
- Exports records to CSV, GeoPackage or Shapefile.
- Provides optional, non-blocking reverse geocoding through OpenStreetMap Nominatim.
- Uses `qgis.PyQt` and supports Qt 5 and Qt 6 environments.

## Why this plugin

QGIS already has comprehensive coordinate-conversion plugins. GeoClick Capture intentionally focuses on a smaller operational workflow: accumulating a structured log of clicked locations with timestamps, original project coordinates, WGS 84 coordinates, source-layer context and optional place names.

## Installation from ZIP

1. Download `geoclick_capture-1.1.0.zip` from the GitHub Actions build artifact or release.
2. Open **QGIS → Plugins → Manage and Install Plugins**.
3. Select **Install from ZIP**.
4. Choose the ZIP and confirm the installation.

The ZIP contains one top-level folder named `qgis_latlon`, which is the stable Python package identifier.

## Usage

1. Open **Vector → GeoClick Capture → Capture point**, or click the toolbar button.
2. Click a position on the map.
3. The plugin creates a temporary layer named **Captured Points Log** when no destination layer has been selected.
4. Use the Vector menu to copy the latest coordinate, export the data or select an existing point layer.
5. Reverse geocoding is disabled by default. Enable it only when a place name is needed and internet access is available.

## Stored fields

| Field | Purpose |
| --- | --- |
| `id` | Sequential record identifier |
| `captured_at` | Capture time in UTC (ISO 8601) |
| `lat` | WGS 84 latitude |
| `lon` | WGS 84 longitude |
| `map_x` | Original X coordinate in the project CRS |
| `map_y` | Original Y coordinate in the project CRS |
| `project_crs` | CRS used by the map canvas at capture time |
| `source_layer` | First vector layer identified below the click |
| `location` | Optional reverse-geocoded place name |

GeoPackage is recommended when long field names and Unicode text must be preserved without Shapefile limitations.

## Compatibility and dependencies

- QGIS 3.28 or later
- QGIS 4.x / Qt 6 metadata support
- Windows, Linux and macOS
- No external Python dependencies

## Privacy and network use

Coordinate capture and export work locally. When reverse geocoding is enabled, the clicked WGS 84 latitude and longitude are sent to the OpenStreetMap Nominatim service through `QgsNetworkAccessManager`.

## Test data

A minimal example is available in `examples/sample_capture_log.geojson`.

## Development validation

```bash
python -m compileall -q qgis_latlon
python -m unittest discover -s tests -v
```

## Licence

MIT License. The licence is included both at the repository root and inside the installable plugin package.
