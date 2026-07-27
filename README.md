# GeoClick Capture

**GeoClick Capture 2.0.0** is a QGIS plugin for finding, comparing, verifying, reviewing and recording auditable place locations.

## Location Verification Workspace

Version 2.0.0 adds a sixth **Verification Workspace** tab that combines:

- online Nominatim results and supported map URLs;
- institutional CSV or QGIS-layer gazetteers;
- nearby existing features from **Match & Verify**;
- manual coordinates;
- selected QGIS point, line or polygon features, using the geometry point or centroid while preserving its original geometry type.

The workspace calculates transparent source-trust, spatial-agreement and recommendation scores. It reports the maximum distance between sources and classifies consensus as **Strong**, **Moderate**, **Weak**, **Divergent** or **Single source**. Recommendations remain advisory: the user explicitly chooses the preferred source.

### Evidence and verification bundles

Users can attach local files or URLs. Files are hashed with SHA-256. **Export bundle** creates:

```text
workspace.json
report.html
candidates.csv
evidence.csv
manifest.json
attachments/
```

The workspace persists inside the QGIS project and can be exchanged through JSON or ZIP files. Candidate lists can be imported from CSV using the packaged template:

`qgis_latlon/samples/workspace_candidates_template.csv`

### Auditable output

Saving the preferred candidate to the session records the workspace ID, preferred source, source count, candidate count, maximum spread, consensus, agreement, evidence manifest, rationale, verifier, UTC timestamp, geometry evidence types and complete workspace snapshot. Verified and rejected workspaces also update Review Queue history.

## Existing workflows

1. **Capture Log** — map-click capture, snapping, sessions and export.
2. **Search & Capture** — place/address search, coordinates and map URLs.
3. **Match & Verify** — nearby-feature comparison and duplicate-risk evidence.
4. **Offline Gazetteer** — names, aliases and P-codes without Internet.
5. **Review Queue** — approvals, rejections, change requests and immutable history.
6. **Verification Workspace** — multi-source comparison, evidence and complete reports.

## Installation

Open **QGIS → Plugins → Manage and Install Plugins → Install from ZIP**, select `geoclick_capture-2.0.0.zip`, then restart or reload the plugin.

## Compatibility

- QGIS 3.28 or later
- QGIS 4.x / Qt 6
- Windows, Linux and macOS
- No external Python dependencies

## Development

```bash
python -m compileall -q qgis_latlon
python -m unittest discover -s tests -v
```

See the packaged [README](qgis_latlon/README.md), [CHANGELOG](CHANGELOG.md) and [LICENSE](LICENSE).
