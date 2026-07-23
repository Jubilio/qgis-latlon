# QGIS LatLon

**QGIS LatLon** is a lightweight QGIS plugin for capturing a position on the map, converting it correctly to WGS 84 and storing the result in a point layer.

## Main features

- Captures coordinates from any project CRS and stores latitude/longitude in EPSG:4326.
- Shows decimal coordinates and DMS notation.
- Identifies the first vector layer below the clicked position.
- Copies the most recently captured coordinate to the clipboard.
- Creates a temporary point layer or reuses an existing point layer.
- Transforms the geometry correctly to the CRS of the selected output layer.
- Exports records to CSV, GeoPackage or Shapefile.
- Offers optional, non-blocking reverse geocoding through OpenStreetMap Nominatim.
- Uses `qgis.PyQt`, supporting Qt 5 and Qt 6 environments.

## Installation from ZIP

1. Download `qgis_latlon-1.0.0.zip` from the repository release or build output.
2. Open **QGIS → Plugins → Manage and Install Plugins**.
3. Select **Install from ZIP**.
4. Choose the ZIP and confirm the installation.

The ZIP must contain a single top-level folder named `qgis_latlon`.

## Usage

1. Click **Capture coordinates** in the toolbar or the **QGIS LatLon** plugin menu.
2. Click a position on the map.
3. The plugin creates `Pontos Capturados` when no destination layer has been selected.
4. Use the plugin menu to copy the last coordinate, export the data or select an existing point layer.
5. Reverse geocoding is disabled by default. Enable it only when a location name is required and internet access is available.

## Stored fields

| Field | Purpose |
| --- | --- |
| `id` | Sequential record identifier |
| `lat` | WGS 84 latitude |
| `lon` | WGS 84 longitude |
| `epsg` | CRS used by the map canvas when the click occurred |
| `source_layer` | First vector layer identified below the click |
| `location` | Optional reverse-geocoded place name |

GeoPackage is recommended when long field names and Unicode text must be preserved without Shapefile limitations.

## Compatibility

- QGIS 3.28 or later
- QGIS 4.x / Qt 6 metadata support
- Windows, Linux and macOS

## Privacy and network use

Coordinate capture and export work locally. When reverse geocoding is enabled, the clicked WGS 84 latitude and longitude are sent to the OpenStreetMap Nominatim service.

## Development validation

```bash
python -m compileall qgis_latlon
python -m unittest discover -s tests -v
```

## Licence

MIT License. See [LICENSE](LICENSE).
