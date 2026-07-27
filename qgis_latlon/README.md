# GeoClick Capture

**GeoClick Capture** finds, matches, verifies and records auditable place locations in QGIS.

## Version 1.4.0

The plugin contains three coordinated tabs:

1. **Capture Log** — map-click capture, session metadata, snapping, review and export;
2. **Search & Capture** — address/place search, coordinates and supported map URLs;
3. **Match & Verify** — comparison with existing point features before insertion.

### Match & Verify

The third tab can scan a selected point layer or all visible point layers. It evaluates:

- distance in metres using geodesic measurement;
- accent-insensitive similarity between the searched label and candidate text fields;
- confidence from 0 to 100;
- High, Medium or Low duplicate risk.

The user explicitly chooses **Use existing** or **Create new**. The following audit fields are added when required:

- `match_decision`;
- `matched_layer`;
- `matched_layer_id`;
- `matched_feature_id`;
- `match_distance_m`;
- `name_similarity`;
- `duplicate_risk`;
- `confidence_score`;
- `review_required`.

### Search & Capture

The Search & Capture tab accepts place names and addresses through OpenStreetMap Nominatim, decimal latitude/longitude pairs, OpenStreetMap URLs and Google Maps URLs containing coordinates. Searches are triggered explicitly by Enter or the Search button; there is no automatic autocomplete traffic.

Search captures preserve provenance fields for capture method, query, provider, provider result ID, label, type, importance, OSM identifiers and input format.

### Capture Log

The existing Capture Log provides sessions, operator, category, status and notes; destination point-layer selection; map-click capture; vertex-first and segment fallback snapping; undo, delete and clear actions; CSV, GeoJSON and GeoPackage exports; and optional reverse geocoding.

## Installation

1. Open **QGIS → Plugins → Manage and Install Plugins → Install from ZIP**.
2. Select `geoclick_capture-1.4.0.zip` or the Pull Request test artefact.
3. Restart or reload the plugin after replacing an older installation.

## Match workflow

1. Search for a place and select a result.
2. Click **Match & verify**.
3. Configure the layer scope, radius and minimum name match.
4. Click **Analyse nearby features**.
5. Review distance, name match, confidence and risk.
6. Zoom to a candidate when necessary.
7. Choose **Use existing** or **Create new**.

## Compatibility

- QGIS 3.28 or later
- QGIS 4.x / Qt 6
- Windows, Linux and macOS
- No external Python dependencies

## Licence

MIT License.
