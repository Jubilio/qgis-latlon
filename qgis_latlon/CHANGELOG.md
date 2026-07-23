# Changelog

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
