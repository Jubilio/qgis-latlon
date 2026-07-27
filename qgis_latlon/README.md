# GeoClick Capture

**GeoClick Capture 2.0.0** is a QGIS workspace for finding, comparing, verifying, reviewing and recording auditable place locations.

## Location Verification Workspace

The sixth tab combines multiple sources for the same place:

- online Nominatim results and supported map URLs;
- institutional CSV or QGIS-layer gazetteers;
- nearby existing features from **Match & Verify**;
- manual coordinates;
- selected QGIS point, line or polygon features, represented by their point or centroid while preserving the original geometry type and optional WKT evidence.

Each candidate receives transparent values for:

- source trust;
- spatial agreement with other candidates;
- recommendation score;
- distance to the user-selected preferred source.

The recommendation is advisory. The user must explicitly choose **Set preferred**.

## Evidence and reporting

The workspace can attach:

- local files, hashed with SHA-256;
- URLs or external references;
- evidence notes, author and UTC timestamp.

**Export bundle** creates a ZIP containing:

```text
workspace.json
report.html
candidates.csv
evidence.csv
manifest.json
attachments/
```

The workspace is persisted as a QGIS project custom property and can also be imported from a JSON file or a previous bundle. A candidate CSV template is packaged at `samples/workspace_candidates_template.csv` and can contain fields such as `label`, `latitude`, `longitude`, `source`, `source_id`, `source_url`, `source_date`, `geometry_type`, `admin` and `notes`.

## Saving to the capture session

After selecting a preferred candidate, the workspace writes an auditable point record and preserves:

- workspace and preferred-source identifiers;
- candidate and source counts;
- maximum source spread and consensus level;
- agreement score;
- evidence count and manifest;
- verification status, rationale, verifier and UTC timestamp;
- complete workspace snapshot;
- geometry evidence types.

Verified or rejected workspaces are integrated with the existing Review Queue history.

## Other tabs

1. **Capture Log** — map-click capture, snapping, sessions and export.
2. **Search & Capture** — online place/address search, coordinates and map URLs.
3. **Match & Verify** — duplicate-risk analysis against existing point layers.
4. **Offline Gazetteer** — local names, aliases and P-codes without Internet.
5. **Review Queue** — approval, rejection, change requests and immutable review history.
6. **Verification Workspace** — multi-source comparison, evidence and full reporting.

## Installation

1. Open **QGIS → Plugins → Manage and Install Plugins → Install from ZIP**.
2. Select `geoclick_capture-2.0.0.zip`.
3. Restart or reload the plugin after replacing an earlier version.

## Compatibility

- QGIS 3.28 or later
- QGIS 4.x / Qt 6
- Windows, Linux and macOS
- No external Python dependencies

## Licence

MIT License.
