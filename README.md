# GeoClick Capture

**GeoClick Capture** is a QGIS plugin for finding, matching, verifying and recording auditable place locations during field verification, map review and GIS quality-assurance work.

## Version 1.5.0 — Offline Gazetteer

Version 1.5.0 adds a fourth **Offline Gazetteer** tab for institutional and project-specific place lists.

The gazetteer can use:

- UTF-8 or UTF-8-BOM CSV files;
- any point layer already open in QGIS, including GeoPackage and database-backed layers.

The plugin automatically detects common fields for official names, aliases, P-codes, coordinates, place types, administrative names, source and source date. Searches run locally across official names, alternative spellings and P-codes and can be filtered by place type.

Offline results can be previewed, zoomed to, passed to **Match & Verify**, or added directly to the active capture session. Source, record ID, P-code, name, aliases, place type, administrative hierarchy and source date are preserved in audit fields.

A compatible template is packaged at:

`qgis_latlon/samples/offline_gazetteer_template.csv`

## Match & Verify

Version 1.4.0 compares searched or offline places with one point layer or all visible point layers. It evaluates geodesic distance, accent-insensitive name similarity, confidence from 0 to 100 and High/Medium/Low duplicate risk. The user explicitly chooses **Use existing** or **Create new**.

## Search & Capture

Supported online/direct inputs include:

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

Open:

**QGIS → Plugins → Manage and Install Plugins → Install from ZIP**

Select `geoclick_capture-1.5.0.zip` or the Pull Request test artefact, then restart QGIS or reload the plugin.

## Offline Gazetteer workflow

1. Open **Vector → GeoClick Capture → Open offline gazetteer**.
2. Load a CSV or select a QGIS point layer.
3. Search an official name, alternative spelling or P-code.
4. Review the result and use **Preview** or **Zoom**.
5. Select **Match & verify** or **Add to session**.
6. Review the gazetteer source fields in the Capture Log attributes.

Text searches through Nominatim require Internet access. Offline gazetteer, coordinate and supported URL inputs do not.

## Development

```bash
python -m compileall -q qgis_latlon
python -m unittest discover -s tests -v
```

See the packaged [README](qgis_latlon/README.md), [CHANGELOG](CHANGELOG.md) and [LICENSE](LICENSE).
