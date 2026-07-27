# Changelog

## 2.0.0 — 2026-07-27

- Added a unified **Location Verification Workspace** for online, offline, manual and QGIS source candidates.
- Added transparent source-trust, spatial-agreement and recommendation scores with explicit preferred-source selection.
- Added point, line and polygon evidence from selected QGIS features through their point or centroid.
- Added file and URL evidence, SHA-256 hashes, project persistence and shareable workspace import.
- Added candidate CSV import, temporary comparison layers and auditable workspace fields.
- Added ZIP verification bundles with JSON, HTML, CSV tables, manifest and copied attachments.
- Added seven coordinated SVG icons and pure-Python tests for comparison, hashing, import and bundle export.

## 1.6.0 — 2026-07-27

- Added a fifth **Review Queue** tab and a dedicated toolbar/menu action.
- Added state and text filters plus multi-record review decisions.
- Added **Approve**, **Reject**, **Needs changes** and **Reset pending** actions with reviewer attribution.
- Required comments for rejection and change requests.
- Added immutable JSON history, review iterations, UTC timestamps and synchronisation with operational status fields.
- Added a review-history viewer, filtered CSV export and six coordinated SVG icons.
- Added pure-Python tests for status normalisation, history, filtering and counts.

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
- Added scanning of one point layer or all visible point layers within a configurable distance.
- Added accent-insensitive place-name comparison across preferred or automatically detected text fields.
- Added explainable confidence scoring based on 65% name similarity and 35% spatial proximity.
- Added High, Medium and Low duplicate-risk classifications with documented thresholds.
- Added decisions to zoom to an existing feature, use the existing feature or create a new point.
- Added audit fields for the selected decision, matched layer/feature, distance, name similarity, confidence, risk and review requirement.
- Added six coordinated SVG icons for matching, scanning, duplicate warnings and decisions.
- Added pure-Python tests for name normalisation, similarity, confidence, risk and candidate ordering.

## 1.3.0 — 2026-07-27

- Added a new **Search & Capture** tab alongside the Capture Log.
- Added place and address search through OpenStreetMap Nominatim with optional country and current-map-extent restrictions.
- Added local recognition of decimal coordinates and common OpenStreetMap and Google Maps URLs.
- Added result review actions for zoom, preview, coordinate copying and opening results in external maps.
- Added auditable insertion of selected search results into the active capture session.
- Added provenance fields for capture method, query, provider, provider ID, label, type, importance, OSM identifiers and input format.
- Added in-memory search caching, explicit attribution, safe redirects, timeout and one transient retry.
- Added seven coordinated SVG icons for the new functions.
- Added pure-Python unit tests for coordinate parsing, map URL parsing and Nominatim response normalisation.

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
- Expanded AST tests to scan the complete plugin package for the reported legacy enum accesses.
- Updated metadata, documentation and the installable ZIP version.

## 1.2.2 — 2026-07-23

- Fixed false failures in Qt compatibility and cache checks.

## 1.2.1 — 2026-07-23

- Added QGIS 4 / Qt 6 compatibility and automatic snapping to vertices and segments.

## 1.2.0 — 2026-07-23

- Added the Capture Log panel, sessions, metadata fields, record management, persistent preferences and GeoJSON export.

## 1.1.0 — 2026-07-23

- Repositioned the plugin as GeoClick Capture and added submission-ready documentation and licence files.

## 1.0.0 — 2026-07-23

- Corrected CRS handling, layer writing, exports, Qt compatibility and asynchronous reverse geocoding.
