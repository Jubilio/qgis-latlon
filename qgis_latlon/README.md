# GeoClick Capture

**GeoClick Capture 2.0.1** is a QGIS workspace for finding, comparing, verifying, reviewing and recording auditable place locations.

## Verification workflow

1. Collect candidates from online search, institutional gazetteers, QGIS layers or manual coordinates.
2. Compare source trust, spatial agreement and recommendation scores.
3. Explicitly select the preferred location.
4. Attach supporting files, URLs and verification notes.
5. Save the decision and export an auditable verification bundle.

## Location Verification Workspace

The sixth tab combines multiple sources for the same place:

- online Nominatim results and supported map URLs;
- institutional CSV or QGIS-layer gazetteers;
- nearby existing features from **Match & Verify**;
- manual coordinates;
- selected QGIS point, line or polygon features, represented by their point or centroid while preserving the original geometry type and optional WKT evidence.

Each candidate receives transparent values for source trust, spatial agreement, recommendation score and distance to the user-selected preferred source. The recommendation is advisory: the user must explicitly choose **Set preferred**.

## Evidence and reporting

The workspace can attach local files hashed with SHA-256, URLs or external references, evidence notes, author details and UTC timestamps.

**Export bundle** creates a ZIP containing:

```text
workspace.json
report.html
candidates.csv
evidence.csv
manifest.json
attachments/
```

The workspace persists in the QGIS project through the compatible QgsProject entry API and can also be imported from JSON or a previous bundle. A candidate CSV template is packaged at `samples/workspace_candidates_template.csv`.

## Saving to the capture session

After selecting a preferred candidate, the workspace preserves workspace and source identifiers, candidate and source counts, source spread and consensus, agreement score, evidence manifest, verification status, rationale, verifier, UTC timestamp, complete workspace snapshot and geometry evidence types.

Verified or rejected workspaces are integrated with the Review Queue history.

## Other tabs

1. **Capture Log** — map-click capture, snapping, sessions and export.
2. **Search & Capture** — online place/address search, coordinates and map URLs.
3. **Match & Verify** — duplicate-risk analysis against existing point layers.
4. **Offline Gazetteer** — local names, aliases and P-codes without Internet.
5. **Review Queue** — approval, rejection, change requests and immutable review history.
6. **Verification Workspace** — multi-source comparison, evidence and full reporting.

## Installation

The recommended method is **QGIS → Plugins → Manage and Install Plugins**, then search for **GeoClick Capture**.

For manual installation, select `geoclick_capture-2.0.1.zip` under **Install from ZIP**, then restart or reload the plugin after replacing an earlier version.

## Compatibility

- QGIS 3.28 or later
- QGIS 4.x / Qt 6
- Windows, Linux and macOS
- No external Python dependencies

## Feedback

Use the public issue tracker at https://github.com/Jubilio/qgis-latlon/issues. Do not attach sensitive, personal or confidential operational information to public issues.

## Licence

MIT License.
