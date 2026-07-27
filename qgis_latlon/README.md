# GeoClick Capture

**GeoClick Capture** finds, matches, verifies, reviews and records auditable place locations in QGIS.

## Version 1.6.0

The plugin contains five coordinated tabs:

1. **Capture Log** — map-click capture, session metadata, snapping and export;
2. **Search & Capture** — online place search, coordinates and supported map URLs;
3. **Match & Verify** — comparison with existing point features before insertion;
4. **Offline Gazetteer** — local search of institutional names, aliases and P-codes;
5. **Review Queue** — formal approval, rejection, change requests and audit history.

### Review Queue

The fifth tab supports state and text filtering, selection of several records and the following decisions:

- **Approve**;
- **Reject**;
- **Needs changes**;
- **Reset pending**.

A reviewer is required for every decision. Reject and Needs changes also require a comment. Each event is appended to `review_history` with iteration, action, state, reviewer, UTC timestamp and comment. The current state is stored in:

- `review_status`;
- `reviewer`;
- `reviewed_at`;
- `review_comment`;
- `review_history`;
- `review_iteration`.

The queue also includes a history viewer and filtered CSV export.

### Offline Gazetteer

The fourth tab loads UTF-8 CSV files or any point layer already open in QGIS, including GeoPackage and database layers. Common name, alias, P-code, coordinate, place-type and administrative fields are detected automatically. A template is included at `samples/offline_gazetteer_template.csv`.

### Match & Verify

The third tab evaluates geodesic distance, accent-insensitive name similarity, confidence and High/Medium/Low duplicate risk before the user chooses **Use existing** or **Create new**.

### Search & Capture

The online tab accepts OpenStreetMap Nominatim place names and addresses, decimal coordinates, OpenStreetMap URLs and Google Maps URLs containing coordinates. Searches are explicitly triggered; there is no automatic autocomplete traffic.

### Capture Log

Capture Log provides sessions, operator, category, status and notes; destination point-layer selection; map-click capture; snapping; undo, delete and clear actions; CSV, GeoJSON and GeoPackage exports; and optional reverse geocoding.

## Installation

1. Open **QGIS → Plugins → Manage and Install Plugins → Install from ZIP**.
2. Select `geoclick_capture-1.6.0.zip` or the Pull Request test artefact.
3. Restart or reload the plugin after replacing an older installation.

## Review workflow

1. Open **Vector → GeoClick Capture → Open review queue**.
2. Select the destination layer.
3. Filter the records.
4. Enter the reviewer and comment when needed.
5. Select one or several rows and record the decision.
6. Inspect **History** or export the filtered queue.

## Compatibility

- QGIS 3.28 or later
- QGIS 4.x / Qt 6
- Windows, Linux and macOS
- No external Python dependencies

## Licence

MIT License.
