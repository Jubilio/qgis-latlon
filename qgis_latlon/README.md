# GeoClick Capture

**GeoClick Capture** finds, matches, verifies and records auditable place locations in QGIS.

## Version 1.5.0

The plugin contains four coordinated tabs:

1. **Capture Log** — map-click capture, session metadata, snapping, review and export;
2. **Search & Capture** — online address/place search, coordinates and supported map URLs;
3. **Match & Verify** — comparison with existing point features before insertion;
4. **Offline Gazetteer** — local search of institutional names, aliases and P-codes.

### Offline Gazetteer

The fourth tab can load:

- UTF-8 or UTF-8-BOM CSV files;
- any point layer already open in QGIS, including GeoPackage and database layers.

Common columns are detected automatically, including `official_name`, `alternative_names`, `pcode`, `latitude`, `longitude`, `place_type`, administrative names, source and source date. A compatible example is packaged at `samples/offline_gazetteer_template.csv`.

Offline results can be previewed, zoomed to, passed to **Match & Verify**, or added directly to the active session. Captured records preserve:

- `gazetteer_source`;
- `gazetteer_record_id`;
- `gazetteer_pcode`;
- `gazetteer_name`;
- `gazetteer_aliases`;
- `gazetteer_type`;
- `gazetteer_admin`;
- `gazetteer_source_date`.

### Match & Verify

The third tab scans one point layer or all visible point layers and evaluates geodesic distance, accent-insensitive name similarity, confidence from 0 to 100 and High/Medium/Low duplicate risk. The user explicitly chooses **Use existing** or **Create new**.

### Search & Capture

The online tab accepts place names and addresses through OpenStreetMap Nominatim, decimal latitude/longitude pairs, OpenStreetMap URLs and Google Maps URLs containing coordinates. Searches are triggered explicitly; there is no automatic autocomplete traffic.

### Capture Log

Capture Log provides sessions, operator, category, status and notes; destination point-layer selection; map-click capture; vertex-first and segment fallback snapping; undo, delete and clear actions; CSV, GeoJSON and GeoPackage exports; and optional reverse geocoding.

## Installation

1. Open **QGIS → Plugins → Manage and Install Plugins → Install from ZIP**.
2. Select `geoclick_capture-1.5.0.zip` or the Pull Request test artefact.
3. Restart or reload the plugin after replacing an older installation.

## Offline workflow

1. Open **Vector → GeoClick Capture → Open offline gazetteer**.
2. Load a CSV or select a QGIS point layer.
3. Search an official name, variant or P-code.
4. Review the result and use **Preview** or **Zoom**.
5. Choose **Match & verify** or **Add to session**.

## Compatibility

- QGIS 3.28 or later
- QGIS 4.x / Qt 6
- Windows, Linux and macOS
- No external Python dependencies

## Licence

MIT License.
