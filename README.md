# GeoClick Capture

**GeoClick Capture** is a QGIS plugin for finding, matching, verifying and recording auditable place locations during field verification, map review and GIS quality-assurance work.

## Version 1.4.0 — Match & Verify

Version 1.4.0 adds a third **Match & Verify** tab. A selected Search & Capture result can be compared with existing point features before the user decides whether to link an existing record or create a new one.

The analysis supports:

- one selected point layer or all visible point layers;
- a configurable search radius from 10 m to 50 km;
- a preferred name field or automatic matching across text fields;
- accent-insensitive name comparison;
- geodesic distance in metres;
- an explainable confidence score from 0 to 100;
- High, Medium and Low duplicate-risk classes;
- explicit **Use existing** and **Create new** decisions.

The decision and supporting evidence are stored in the capture log through fields for matched layer/feature, distance, name similarity, confidence, duplicate risk and review requirement. The plugin never resolves a possible duplicate automatically.

## Search & Capture

Supported inputs:

- place names and addresses through OpenStreetMap Nominatim;
- decimal coordinates such as `-12.9742, 40.5178`;
- OpenStreetMap URLs;
- Google Maps URLs containing coordinates.

Search results can be reviewed, zoomed, previewed, copied, opened in external maps, matched against existing layers or added directly to the active session.

## Existing capabilities

- project snapping with vertex-first and segment fallback;
- session, operator, category, status and note fields;
- UTC, project, map-scale and source-feature context;
- reverse geocoding with broader administrative fallback;
- CSV, GeoJSON and GeoPackage export;
- undo, selected-record deletion and clear session;
- QGIS 3.28+ and QGIS 4 / Qt 6 compatibility;
- no external Python dependencies.

## Installation

For phase-one testing, install the stable release `geoclick_capture-1.3.0.zip`.

The Match & Verify implementation is developed as version 1.4.0 and its Pull Request artefact can be installed separately for testing.

Open:

**QGIS → Plugins → Manage and Install Plugins → Install from ZIP**

Restart QGIS or reload the plugin after replacing an older installation.

## Match & Verify workflow

1. Open **Vector → GeoClick Capture → Search & capture place**.
2. Enter an address, place, coordinate pair or map URL.
3. Select a result and click **Match & verify**.
4. Choose the visible-layer scope, radius and minimum name match.
5. Click **Analyse nearby features**.
6. Review distance, name match, confidence and risk.
7. Select **Use existing** or **Create new**.
8. Review the recorded decision in the Capture Log attributes.

Text searches use the public OpenStreetMap Nominatim service and require Internet access. Coordinate and supported URL inputs are parsed locally. Requests are sent only after Enter or **Search**; the plugin does not perform automatic autocomplete traffic.

## Development

```bash
python -m compileall -q qgis_latlon
python -m unittest discover -s tests -v
```

See the packaged [README](qgis_latlon/README.md), [CHANGELOG](CHANGELOG.md) and [LICENSE](LICENSE).
