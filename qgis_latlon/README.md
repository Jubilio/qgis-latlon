# GeoClick Capture

**GeoClick Capture** is a focused QGIS plugin for building auditable point logs during field verification, map review and GIS quality-assurance work.

## Version 1.2.0

The dockable **Capture Log** panel manages capture sessions, operator details, category, verification status, notes and the destination point layer. A table displays captured records and provides undo, delete-selected and clear-session actions.

Every point records:

- UTC capture time;
- session, operator, category, status and note;
- WGS 84 latitude and longitude;
- original project X/Y coordinates;
- project name, CRS and map scale;
- source layer and source feature identifiers;
- optional reverse-geocoded place name.

## Usage

1. Open **Vector → GeoClick Capture → Open capture log**.
2. Complete the session fields.
3. Choose a destination point layer or leave it empty to create **Captured Points Log**.
4. Press **Start capture** and click the map.
5. Review, undo, delete or export records from the panel.

## Exports

The panel exports CSV, GeoJSON and GeoPackage. GeoPackage is recommended for production use.

## Network and privacy

Capture and export work locally. Reverse geocoding is disabled by default. When enabled, WGS 84 coordinates are sent to OpenStreetMap Nominatim through `QgsNetworkAccessManager`. The plugin applies caching, a one-request-per-second interval, a timeout and visible attribution.

## Compatibility

- QGIS 3.28 or later
- QGIS 4.x / Qt 6 metadata support
- Windows, Linux and macOS
- No external Python dependencies

## Licence

MIT License.
