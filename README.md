# GeoClick Capture

**GeoClick Capture** is a QGIS plugin for finding, matching, verifying, reviewing and recording auditable place locations during field verification, map review and GIS quality-assurance work.

## Version 1.6.0 — Review Workflow

Version 1.6.0 adds a fifth **Review Queue** tab for formal quality-control decisions after capture.

The review workspace provides:

- filters for Pending, Needs changes, Approved and Rejected records;
- free-text search across IDs, places, methods, duplicate risk, reviewer and comments;
- multi-record **Approve**, **Reject**, **Needs changes** and **Reset pending** actions;
- required reviewer attribution for every decision;
- required comments for rejection and change requests;
- immutable JSON history with iteration, action, state, reviewer, UTC timestamp and comment;
- one-record history display and filtered review CSV export.

Review decisions synchronise `review_required` and the existing operational `status` field. The following audit fields are added automatically:

`review_status`, `reviewer`, `reviewed_at`, `review_comment`, `review_history`, `review_iteration`.

## Offline Gazetteer

Version 1.5.0 loads UTF-8 CSV files or any point layer already open in QGIS, including GeoPackage and database-backed layers. It searches official names, aliases and P-codes without Internet access and preserves source metadata. A compatible template is packaged at:

`qgis_latlon/samples/offline_gazetteer_template.csv`

## Match & Verify

Version 1.4.0 compares searched or offline places with one point layer or all visible point layers. It evaluates geodesic distance, accent-insensitive name similarity, confidence from 0 to 100 and High/Medium/Low duplicate risk. The user explicitly chooses **Use existing** or **Create new**.

## Search & Capture

Supported inputs include place names and addresses through OpenStreetMap Nominatim, decimal coordinates, OpenStreetMap URLs and Google Maps URLs containing coordinates. Results can be reviewed, zoomed, previewed, copied, matched or added directly to the session.

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

Select `geoclick_capture-1.6.0.zip` or the Pull Request test artefact, then restart QGIS or reload the plugin.

## Review workflow

1. Open **Vector → GeoClick Capture → Open review queue**.
2. Select the destination layer containing captured records.
3. Filter the queue by state or search text.
4. Enter the reviewer name and, where required, a comment.
5. Select one or several records.
6. Choose **Approve**, **Reject**, **Needs changes** or **Reset pending**.
7. Use **History** to inspect one record's complete audit trail.
8. Use **Export review CSV** to export the currently filtered queue.

Text searches through Nominatim require Internet access. Review Workflow, Offline Gazetteer, coordinate inputs and supported URL parsing work locally.

## Development

```bash
python -m compileall -q qgis_latlon
python -m unittest discover -s tests -v
```

See the packaged [README](qgis_latlon/README.md), [CHANGELOG](CHANGELOG.md) and [LICENSE](LICENSE).
