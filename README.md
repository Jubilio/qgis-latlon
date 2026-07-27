# GeoClick Capture

**GeoClick Capture** is a QGIS plugin for finding, reviewing and recording auditable place locations during field verification, map review and GIS quality-assurance work.

## Version 1.3.0 — Search & Capture

Version 1.3.0 adds a dedicated **Search & Capture** tab alongside the existing Capture Log.

Supported inputs:

- place names and addresses through OpenStreetMap Nominatim;
- decimal coordinates such as `-12.9742, 40.5178`;
- OpenStreetMap URLs;
- Google Maps URLs containing coordinates.

Search results can be:

- reviewed in a results table;
- zoomed to in QGIS;
- previewed with a temporary map marker;
- copied as coordinates;
- opened in OpenStreetMap or Google Maps;
- added to the active capture session.

Each search capture records the input method, original query, provider, provider result ID, label, type, importance and OpenStreetMap identifiers. Text searches can be limited to a country and optionally to the current map extent.

Existing capabilities remain active:

- project snapping with vertex-first and segment fallback;
- session, operator, category, status and note fields;
- UTC, project, map-scale and source-feature context;
- reverse geocoding with broader administrative fallback;
- CSV, GeoJSON and GeoPackage export;
- undo, selected-record deletion and clear session;
- QGIS 3.28+ and QGIS 4 / Qt 6 compatibility;
- no external Python dependencies.

## Installation

Download `geoclick_capture-1.3.0.zip`, then open:

**QGIS → Plugins → Manage and Install Plugins → Install from ZIP**

Restart QGIS or reload the plugin after replacing an older installation.

## Basic use

1. Open **Vector → GeoClick Capture → Search & capture place**.
2. Enter an address, place, coordinate pair or map URL.
3. Review the returned result.
4. Use **Zoom** or **Preview** to verify it on the map.
5. Click **Add to session** to create an auditable point record.
6. Open the **Capture Log** tab to review or export the session.

Text searches use the public OpenStreetMap Nominatim service and therefore require Internet access. Coordinate and supported URL inputs are parsed locally. The plugin sends searches only after the user presses Enter or clicks **Search**; it does not perform automatic autocomplete requests.

## Development

```bash
python -m compileall -q qgis_latlon
python -m unittest discover -s tests -v
```

See the packaged [README](qgis_latlon/README.md), [CHANGELOG](CHANGELOG.md) and [LICENSE](LICENSE).
