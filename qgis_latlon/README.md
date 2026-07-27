# GeoClick Capture

**GeoClick Capture** finds, verifies and records auditable place locations in QGIS.

## Version 1.3.0

The **Search & Capture** tab accepts:

- place names and addresses through OpenStreetMap Nominatim;
- decimal latitude/longitude pairs;
- OpenStreetMap URLs;
- Google Maps URLs containing coordinates.

Returned results can be zoomed to, previewed, copied, opened in external maps and added to the active capture session. Searches are triggered explicitly by Enter or the Search button; there is no automatic autocomplete traffic.

Search captures add the following provenance fields:

- `capture_method`;
- `search_query`;
- `search_provider`;
- `provider_result_id`;
- `result_label`;
- `result_type`;
- `result_importance`;
- `osm_type`;
- `osm_id`;
- `input_format`.

The existing **Capture Log** tab continues to provide:

- sessions, operator, category, status and note fields;
- destination point-layer selection;
- map-click capture, undo, delete and clear actions;
- project snapping with automatic vertex-first and segment fallback;
- CSV, GeoJSON and GeoPackage exports;
- optional reverse geocoding through `QgsNetworkAccessManager`.

Captured records include UTC time, WGS 84 coordinates, project coordinates, project information, source-feature context and snapping audit fields.

## Installation

1. Open **QGIS → Plugins → Manage and Install Plugins → Install from ZIP**.
2. Select `geoclick_capture-1.3.0.zip`.
3. Restart or reload the plugin after replacing an older installation.

## Search workflow

1. Open **Vector → GeoClick Capture → Search & capture place**.
2. Enter a place, coordinate pair or map URL.
3. Optionally change the country code or restrict a text search to the visible map extent.
4. Select a result.
5. Use **Zoom**, **Preview** or **Copy coordinates** to verify it.
6. Click **Add to session**.

## Compatibility

- QGIS 3.28 or later
- QGIS 4.x / Qt 6
- Windows, Linux and macOS
- No external Python dependencies

## Licence

MIT License.
