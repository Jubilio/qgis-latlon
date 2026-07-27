# Changelog

## 1.5.0 — 2026-07-27

- Added a fourth **Offline Gazetteer** tab and a dedicated toolbar/menu action.
- Added UTF-8/UTF-8-BOM CSV loading with automatic detection of names, aliases, P-codes, coordinates, place types and administrative fields.
- Added support for using any loaded QGIS point layer as an offline gazetteer, including GeoPackage and database-backed layers.
- Added local search across official names, alternative spellings and P-codes, with optional place-type filtering.
- Added preview, zoom, Match & Verify and auditable Add to session actions for offline results.
- Added gazetteer audit fields for source, record ID, P-code, name, aliases, type, administration and source date.
- Added a packaged CSV template, four coordinated SVG icons and pure-Python gazetteer tests.

## 1.4.0 — 2026-07-27

- Added a third **Match & Verify** tab and a dedicated toolbar/menu action.
- Added nearby-feature scanning for a selected point layer or all visible point layers.
- Added accent-insensitive name similarity, geodesic distance, explainable confidence scores and High/Medium/Low duplicate-risk classes.
- Added explicit **Use existing** and **Create new** decisions; the plugin never resolves a duplicate automatically.
- Added audit fields: `match_decision`, `matched_layer`, `matched_layer_id`, `matched_feature_id`, `match_distance_m`, `name_similarity`, `duplicate_risk`, `confidence_score` and `review_required`.
- Added six coordinated SVG icons for match analysis and decisions.
- Added pure-Python tests for normalisation, similarity, confidence, risk and candidate ordering.

## 1.3.0 — 2026-07-27

- Added a tabbed **Search & Capture** workflow beside the existing Capture Log.
- Added text search through OpenStreetMap Nominatim with optional country and current-map-extent restrictions.
- Added local recognition of decimal latitude/longitude pairs and common OpenStreetMap and Google Maps URLs.
- Added result review actions for zoom, preview, copy coordinates, open in OpenStreetMap, open in Google Maps and add to the active capture session.
- Added search provenance fields: `capture_method`, `search_query`, `search_provider`, `provider_result_id`, `result_label`, `result_type`, `result_importance`, `osm_type`, `osm_id` and `input_format`.
- Added in-memory search caching, explicit OpenStreetMap attribution, safe redirects, timeout and one retry for transient failures.
- Added seven coordinated SVG icons for place search, zoom, preview, search capture, coordinate copying and external map links.
- Added pure-Python tests for coordinate parsing, map URL parsing and Nominatim result normalisation.

## 1.2.6 — 2026-07-24

- Added eight coordinated transparent SVG icons for capture, capture log, snapping, reverse geocoding, export, undo, deletion and sessions.
- Assigned icons to all plugin menu actions and the main Capture Log controls.
- Added a snapping icon beside the snapping control and a session icon to the dock window.
- Changed the plugin repository icon to the new capture-point artwork.
- Optimised every icon to a 64 × 64 viewBox and kept the combined icon payload below 20 KB.

## 1.2.5 — 2026-07-23

- Treats Nominatim's `Unable to geocode` response as a valid no-result condition.
- Adds progressive fallback from detailed address to settlement, city, state/province and country levels.
- Adds `layer=address` and an identifying email parameter to reverse requests.
- Preserves one-request-per-second spacing between fallback requests.
- Stores broader successful results as approximate place names.
- Keeps the point saved without a place name when OpenStreetMap has no suitable object.

## 1.2.4 — 2026-07-23

- Added safe HTTPS redirect handling to reverse-geocoding requests.
- Added an explicit transfer timeout and a valid application User-Agent.
- Added one retry for transient network failures, HTTP 429 and selected HTTP 5xx responses.
- Added detailed HTTP status, network and SSL/TLS diagnostics to the QGIS message log.
- Added clearer messages for provider rejection, rate limiting and coordinates with no address result.
- Kept point capture independent from the availability of the external geocoding service.

## 1.2.3 — 2026-07-23

- Replaced all 12 unscoped Qt 5/QGIS enum accesses reported by the QGIS Qt 6 validator.
- Added scoped enum resolution for dock areas, message levels, identify modes, identify types, geometry types, standard buttons and writer errors.
- Preserved QGIS 3 / PyQt 5 support through runtime fallbacks.

## 1.2.2 — 2026-07-23

- Fixed false GitHub Actions failures in Qt compatibility and cache checks.

## 1.2.1 — 2026-07-23

- Added QGIS 4 / Qt 6 compatibility and automatic snapping to vertices and segments.

## 1.2.0 — 2026-07-23

- Added the Capture Log panel, sessions, metadata fields, record management, persistent preferences and GeoJSON export.

## 1.1.0 — 2026-07-23

- Repositioned the plugin as GeoClick Capture and added submission-ready documentation and licence files.

## 1.0.0 — 2026-07-23

- Corrected CRS handling, layer writing, exports, Qt compatibility and asynchronous reverse geocoding.
