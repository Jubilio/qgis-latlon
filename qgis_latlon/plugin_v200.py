"""Location Verification Workspace for GeoClick Capture 2.0.0."""

from __future__ import annotations

import json
import os
import zipfile
from typing import Dict, List, Mapping, Optional

from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import QAction
from qgis.core import (
    QgsCoordinateTransform,
    QgsFeature,
    QgsFeatureRequest,
    QgsField,
    QgsGeometry,
    QgsMapLayerType,
    QgsPointXY,
    QgsProject,
    QgsVectorLayer,
    QgsWkbTypes,
)

from .dock_widget_v126 import plugin_icon
from .dock_widget_v200 import CaptureLogDockV200
from .plugin_v121 import _right_dock_area
from .plugin_v160 import GeoClickCapturePluginV160
from .qgis_latlon import SUCCESS_LEVEL, WGS84
from .review_utils import append_review_history
from .workspace_utils import (
    compare_candidates,
    evidence_record,
    export_workspace_bundle,
    import_workspace_file,
    load_candidate_csv,
    new_workspace_payload,
    normalise_candidate,
    source_kind,
    update_workspace_payload,
    upsert_candidate,
    utc_now,
)

WORKSPACE_FIELDS = (
    ("workspace_id", QVariant.String),
    ("verification_status", QVariant.String),
    ("preferred_candidate_id", QVariant.String),
    ("preferred_source", QVariant.String),
    ("preferred_source_id", QVariant.String),
    ("candidate_count", QVariant.Int),
    ("source_count", QVariant.Int),
    ("source_spread_m", QVariant.Double),
    ("consensus_level", QVariant.String),
    ("agreement_score", QVariant.Double),
    ("evidence_count", QVariant.Int),
    ("evidence_manifest", QVariant.String),
    ("verification_rationale", QVariant.String),
    ("verified_by", QVariant.String),
    ("verified_at", QVariant.String),
    ("workspace_snapshot", QVariant.String),
    ("geometry_evidence_types", QVariant.String),
)

_PROJECT_PROPERTY = "GeoClickCapture/locationVerificationWorkspace"
_PREFERRED_NAME_FIELDS = (
    "name",
    "official_name",
    "site_name",
    "facility_name",
    "location",
    "label",
    "title",
    "place",
    "settlement",
    "village",
    "pcode",
)


class GeoClickCapturePluginV200(GeoClickCapturePluginV160):
    """Compare location sources, preserve evidence and export verification bundles."""

    def __init__(self, iface):
        super().__init__(iface)
        self.workspace_action: Optional[QAction] = None
        self._workspace: Dict[str, object] = new_workspace_payload()
        self._comparison_layer_id = ""

    def initGui(self):
        parent = self.iface.mainWindow()
        self.workspace_action = QAction(
            plugin_icon("workspace.svg"), "Open location verification workspace", parent
        )
        self.workspace_action.setToolTip(
            "Compare multiple location sources, attach evidence and export an auditable bundle"
        )
        self.workspace_action.triggered.connect(self.show_workspace)
        super().initGui()
        self.iface.addToolBarIcon(self.workspace_action)

    def _menu_actions(self):
        actions = super()._menu_actions()
        if self.workspace_action is not None and self.workspace_action not in actions:
            actions.append(self.workspace_action)
        return actions

    def _create_dock(self):
        self.dock = CaptureLogDockV200(self.iface.mainWindow())
        self.iface.addDockWidget(_right_dock_area(), self.dock)
        self.dock.hide()
        self.dock.capture_toggled.connect(self.activate)
        self.dock.destination_changed.connect(self.set_destination_layer)
        self.dock.undo_requested.connect(self.undo_last_capture)
        self.dock.delete_requested.connect(self.delete_features)
        self.dock.clear_requested.connect(self.clear_session)
        self.dock.export_requested.connect(self.export_records)
        self.dock.search_requested.connect(self.search_place)
        self.dock.search_action_requested.connect(self.handle_search_action)
        self.dock.verify_requested.connect(self.verify_matches)
        self.dock.verify_action_requested.connect(self.handle_verify_action)
        self.dock.gazetteer_csv_requested.connect(self.load_gazetteer_csv)
        self.dock.gazetteer_layer_requested.connect(self.load_gazetteer_layer)
        self.dock.gazetteer_search_requested.connect(self.search_offline_gazetteer)
        self.dock.gazetteer_action_requested.connect(self.handle_gazetteer_action)
        self.dock.review_refresh_requested.connect(self.refresh_review_queue)
        self.dock.review_action_requested.connect(self.handle_review_action)
        self.dock.review_export_requested.connect(self.export_review_queue)
        self.dock.workspace_action_requested.connect(self.handle_workspace_action)
        self.dock.set_preferences(self._load_preferences())
        self._restore_workspace()
        self._update_workspace_dock()

    def unload(self):
        self._persist_workspace()
        if self.workspace_action is not None:
            self.iface.removeToolBarIcon(self.workspace_action)
        super().unload()
        self.workspace_action = None
        self._comparison_layer_id = ""

    def show_workspace(self):
        self.show_dock()
        if isinstance(self.dock, CaptureLogDockV200):
            self.dock.show_workspace_tab()

    def _prepare_layer(self) -> bool:
        if not super()._prepare_layer() or self.layer is None:
            return False
        existing = {field.name() for field in self.layer.fields()}
        missing = [
            QgsField(name, field_type)
            for name, field_type in WORKSPACE_FIELDS
            if name not in existing
        ]
        if missing:
            if not self.layer.dataProvider().addAttributes(missing):
                self._critical("The verification-workspace audit fields could not be added.")
                return False
            self.layer.updateFields()
        return True

    def _restore_workspace(self):
        raw = QgsProject.instance().customProperty(_PROJECT_PROPERTY, "")
        if raw:
            try:
                self._workspace = update_workspace_payload(json.loads(str(raw)))
                return
            except (TypeError, ValueError, json.JSONDecodeError):
                pass
        self._workspace = update_workspace_payload(new_workspace_payload())

    def _persist_workspace(self):
        self._workspace = update_workspace_payload(self._workspace)
        QgsProject.instance().setCustomProperty(
            _PROJECT_PROPERTY,
            json.dumps(self._workspace, ensure_ascii=False, separators=(",", ":")),
        )

    def _sync_workspace_metadata(self, metadata: Optional[Mapping[str, object]] = None):
        if metadata is None and isinstance(self.dock, CaptureLogDockV200):
            metadata = self.dock.workspace_metadata()
        current = dict(self._workspace.get("metadata", {}) or {})
        for key, value in dict(metadata or {}).items():
            if key == "workspace_id" and not str(value or "").strip():
                continue
            if key == "created_at" and not str(value or "").strip():
                continue
            current[key] = value
        self._workspace["metadata"] = current
        self._workspace = update_workspace_payload(self._workspace)

    def _update_workspace_dock(self):
        self._workspace = update_workspace_payload(self._workspace)
        if isinstance(self.dock, CaptureLogDockV200):
            self.dock.set_workspace_state(self._workspace)
        self._persist_workspace()

    def handle_workspace_action(self, action: str, payload: object):
        if action not in {"new_workspace", "import_workspace"}:
            self._sync_workspace_metadata()

        if action == "refresh_workspace":
            self._sync_workspace_metadata(payload if isinstance(payload, Mapping) else {})
            self._update_workspace_dock()
        elif action == "new_workspace":
            self._workspace = update_workspace_payload(new_workspace_payload())
            self._update_workspace_dock()
        elif action == "add_online" and isinstance(payload, Mapping):
            self._add_online_candidate(payload)
        elif action == "add_gazetteer" and isinstance(payload, Mapping):
            self._add_gazetteer_candidate(payload)
        elif action == "add_match" and isinstance(payload, Mapping):
            self._add_match_candidate(payload)
        elif action == "add_manual" and isinstance(payload, Mapping):
            self._add_candidate(payload)
        elif action == "add_layer":
            self._add_selected_layer_features(payload)
        elif action == "import_candidates":
            self._import_candidates(str(payload or ""))
        elif action in {"zoom", "preview", "set_preferred", "remove_candidates"}:
            self._handle_candidate_action(action, payload)
        elif action == "comparison_layer":
            self._create_comparison_layer()
        elif action == "add_evidence_file" and isinstance(payload, Mapping):
            self._add_evidence_file(payload)
        elif action == "add_evidence_url" and isinstance(payload, Mapping):
            self._add_evidence_url(payload)
        elif action == "remove_evidence":
            self._remove_evidence(payload)
        elif action == "import_workspace":
            self._import_workspace(str(payload or ""))
        elif action == "export_bundle" and isinstance(payload, Mapping):
            self._export_workspace_bundle(payload)
        elif action == "save_to_session":
            self._save_workspace_to_session(
                payload if isinstance(payload, Mapping) else {}
            )

    def _add_candidate(self, raw: Mapping[str, object]):
        try:
            candidate = normalise_candidate(raw)
        except ValueError as exc:
            self._warning(str(exc))
            return
        candidates, outcome = upsert_candidate(
            self._workspace.get("candidates", []) or [], candidate
        )
        self._workspace["candidates"] = candidates
        metadata = dict(self._workspace.get("metadata", {}) or {})
        if not str(metadata.get("place_name", "")).strip():
            metadata["place_name"] = candidate["label"]
        self._workspace["metadata"] = metadata
        self._update_workspace_dock()
        if isinstance(self.dock, CaptureLogDockV200):
            self.dock.clear_workspace_inputs()
        self.iface.messageBar().pushMessage(
            "Verification candidate",
            f"{candidate['label']} was {outcome} in the workspace.",
            level=SUCCESS_LEVEL,
            duration=5,
        )

    def _add_online_candidate(self, result: Mapping[str, object]):
        provider = str(result.get("provider", "OpenStreetMap Nominatim"))
        raw = {
            "label": result.get("display_name", "Online result"),
            "source": provider,
            "source_kind": source_kind(provider, result.get("input_format", "")),
            "source_id": result.get("provider_result_id", ""),
            "source_url": result.get("source_url", ""),
            "lat": result.get("lat"),
            "lon": result.get("lon"),
            "geometry_type": "Point",
            "input_format": result.get("input_format", "online_search"),
            "attributes": {
                "result_type": result.get("result_type", ""),
                "importance": result.get("importance", 0.0),
                "osm_type": result.get("osm_type", ""),
                "osm_id": result.get("osm_id", ""),
                "search_query": result.get("search_query", ""),
            },
        }
        self._add_candidate(raw)

    def _add_gazetteer_candidate(self, record: Mapping[str, object]):
        source_name = str(record.get("source_name", record.get("source", "Gazetteer")))
        raw = {
            "label": record.get("official_name", "Gazetteer record"),
            "source": f"Offline gazetteer: {source_name}",
            "source_kind": "gazetteer",
            "source_id": record.get("record_id", record.get("pcode", "")),
            "source_date": record.get("source_date", ""),
            "lat": record.get("lat"),
            "lon": record.get("lon"),
            "geometry_type": "Point",
            "admin": record.get("admin_label", ""),
            "notes": "; ".join(record.get("alternative_names", []) or []),
            "input_format": "offline_gazetteer",
            "attributes": {
                "pcode": record.get("pcode", ""),
                "place_type": record.get("place_type", ""),
            },
        }
        self._add_candidate(raw)

    def _add_match_candidate(self, candidate: Mapping[str, object]):
        raw = {
            "label": candidate.get("candidate_label", "Existing feature"),
            "source": f"Existing QGIS layer: {candidate.get('layer_name', '')}",
            "source_kind": "existing_qgis",
            "source_id": f"{candidate.get('layer_id', '')}:{candidate.get('feature_id', '')}",
            "lat": candidate.get("lat"),
            "lon": candidate.get("lon"),
            "geometry_type": "Point",
            "input_format": "existing_feature",
            "attributes": {
                "distance_m": candidate.get("distance_m", 0.0),
                "name_similarity": candidate.get("name_similarity", 0.0),
                "duplicate_risk": candidate.get("duplicate_risk", ""),
                "confidence_score": candidate.get("confidence_score", 0.0),
            },
        }
        self._add_candidate(raw)

    def _feature_label(self, feature, layer) -> str:
        field_names = [field.name() for field in layer.fields()]
        lookup = {name.casefold(): name for name in field_names}
        for preferred in _PREFERRED_NAME_FIELDS:
            actual = lookup.get(preferred)
            if actual is not None:
                value = feature[actual]
                if str(value or "").strip():
                    return str(value).strip()
        for field in layer.fields():
            if field.type() == QVariant.String:
                value = feature[field.name()]
                if str(value or "").strip():
                    return str(value).strip()
        return f"{layer.name()} feature {feature.id()}"

    def _add_selected_layer_features(self, layer):
        if (
            layer is None
            or not layer.isValid()
            or layer.type() != QgsMapLayerType.VectorLayer
        ):
            self._warning("Select a valid QGIS vector layer.")
            return
        features = list(layer.selectedFeatures())
        if not features:
            self._warning("Select one or more features in the chosen QGIS layer first.")
            return
        if len(features) > 100:
            self._warning("A maximum of 100 selected features can be added at once.")
            features = features[:100]

        transform = None
        if layer.crs().isValid() and layer.crs() != WGS84:
            transform = QgsCoordinateTransform(
                layer.crs(), WGS84, QgsProject.instance()
            )
        added = 0
        candidates = list(self._workspace.get("candidates", []) or [])
        for feature in features:
            geometry = feature.geometry()
            if geometry is None or geometry.isEmpty():
                continue
            try:
                centre_geometry = geometry.centroid()
                point = QgsPointXY(centre_geometry.asPoint())
                if transform is not None:
                    point = transform.transform(point)
            except (RuntimeError, TypeError, ValueError):
                continue
            try:
                geometry_type = QgsWkbTypes.displayString(geometry.wkbType())
            except (AttributeError, TypeError):
                geometry_type = "Geometry"
            try:
                wkt = geometry.asWkt(6)
            except (AttributeError, RuntimeError, TypeError):
                wkt = ""
            if len(wkt) > 10000:
                wkt = ""
            raw = {
                "label": self._feature_label(feature, layer),
                "source": f"QGIS layer: {layer.name()}",
                "source_kind": "qgis_layer",
                "source_id": f"{layer.id()}:{feature.id()}",
                "lat": float(point.y()),
                "lon": float(point.x()),
                "geometry_type": geometry_type,
                "geometry_wkt": wkt,
                "input_format": "selected_qgis_feature",
                "attributes": {
                    "layer_id": layer.id(),
                    "feature_id": int(feature.id()),
                    "area_layer_units": float(geometry.area()),
                    "length_layer_units": float(geometry.length()),
                },
            }
            try:
                normalised = normalise_candidate(raw)
                candidates, _outcome = upsert_candidate(candidates, normalised)
                added += 1
            except ValueError:
                continue
        self._workspace["candidates"] = candidates
        self._update_workspace_dock()
        self.iface.messageBar().pushMessage(
            "QGIS source candidates",
            f"{added} selected feature(s) added using their point or centroid location.",
            level=SUCCESS_LEVEL,
            duration=6,
        )

    def _import_candidates(self, path: str):
        if not path:
            return
        try:
            records, metadata = load_candidate_csv(path)
        except (OSError, UnicodeError, ValueError) as exc:
            self._critical(f"Candidate CSV could not be imported: {exc}")
            return
        candidates = list(self._workspace.get("candidates", []) or [])
        for record in records:
            candidates, _outcome = upsert_candidate(candidates, record)
        self._workspace["candidates"] = candidates
        self._update_workspace_dock()
        invalid = len(metadata.get("invalid_rows", []) or [])
        self.iface.messageBar().pushMessage(
            "Candidate CSV imported",
            f"{len(records)} valid candidate(s) added; {invalid} invalid row(s) skipped.",
            level=SUCCESS_LEVEL,
            duration=7,
        )

    def _handle_candidate_action(self, action: str, payload: object):
        selected = [dict(item) for item in (payload or []) if isinstance(item, Mapping)]
        if not selected:
            return
        if action in {"zoom", "preview"} and len(selected) == 1:
            result = self._candidate_result(selected[0])
            if action == "zoom":
                self.zoom_to_search_result(result)
            else:
                self.preview_search_result(result)
        elif action == "set_preferred" and len(selected) == 1:
            metadata = dict(self._workspace.get("metadata", {}) or {})
            metadata["preferred_candidate_id"] = str(selected[0].get("candidate_id", ""))
            self._workspace["metadata"] = metadata
            self._update_workspace_dock()
        elif action == "remove_candidates":
            remove_ids = {str(item.get("candidate_id", "")) for item in selected}
            self._workspace["candidates"] = [
                item
                for item in self._workspace.get("candidates", []) or []
                if str(item.get("candidate_id", "")) not in remove_ids
            ]
            metadata = dict(self._workspace.get("metadata", {}) or {})
            if str(metadata.get("preferred_candidate_id", "")) in remove_ids:
                metadata["preferred_candidate_id"] = ""
            self._workspace["metadata"] = metadata
            self._update_workspace_dock()

    @staticmethod
    def _candidate_result(candidate: Mapping[str, object]) -> Dict[str, object]:
        return {
            "display_name": str(candidate.get("label", "Verification candidate")),
            "lat": float(candidate.get("lat", 0.0) or 0.0),
            "lon": float(candidate.get("lon", 0.0) or 0.0),
            "result_type": str(candidate.get("geometry_type", "Point")),
            "provider": str(candidate.get("source", "Verification workspace")),
            "provider_result_id": str(candidate.get("source_id", "")),
            "importance": float(candidate.get("recommendation_score", 0.0) or 0.0) / 100.0,
            "input_format": "verification_workspace",
            "search_query": "",
            "boundingbox": [],
            "osm_type": "",
            "osm_id": "",
        }

    def _add_evidence_file(self, payload: Mapping[str, object]):
        path = str(payload.get("path", ""))
        try:
            record = evidence_record(
                "file",
                path,
                note=str(payload.get("note", "")),
                added_by=str(payload.get("added_by", "")),
            )
        except (OSError, ValueError) as exc:
            self._critical(f"Evidence file could not be added: {exc}")
            return
        self._workspace.setdefault("evidence", []).append(record)
        self._update_workspace_dock()

    def _add_evidence_url(self, payload: Mapping[str, object]):
        try:
            record = evidence_record(
                "url",
                str(payload.get("value", "")),
                note=str(payload.get("note", "")),
                added_by=str(payload.get("added_by", "")),
            )
        except ValueError as exc:
            self._warning(str(exc))
            return
        self._workspace.setdefault("evidence", []).append(record)
        self._update_workspace_dock()

    def _remove_evidence(self, payload: object):
        remove_ids = {
            str(item.get("evidence_id", ""))
            for item in (payload or [])
            if isinstance(item, Mapping)
        }
        self._workspace["evidence"] = [
            item
            for item in self._workspace.get("evidence", []) or []
            if str(item.get("evidence_id", "")) not in remove_ids
        ]
        self._update_workspace_dock()

    def _import_workspace(self, path: str):
        if not path:
            return
        try:
            self._workspace = import_workspace_file(path)
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            self._critical(f"Verification workspace could not be imported: {exc}")
            return
        self._update_workspace_dock()
        self.iface.messageBar().pushMessage(
            "Workspace imported",
            str(self._workspace.get("metadata", {}).get("workspace_id", "")),
            level=SUCCESS_LEVEL,
            duration=6,
        )

    def _export_workspace_bundle(self, payload: Mapping[str, object]):
        metadata = payload.get("metadata")
        if isinstance(metadata, Mapping):
            self._sync_workspace_metadata(metadata)
        path = str(payload.get("path", ""))
        if not path:
            return
        try:
            result = export_workspace_bundle(path, self._workspace)
        except (OSError, ValueError, zipfile.BadZipFile) as exc:  # type: ignore[name-defined]
            self._critical(f"Verification bundle could not be exported: {exc}")
            return
        missing = len(result.get("missing_attachments", []) or [])
        self.iface.messageBar().pushMessage(
            "Verification bundle exported",
            f"{result['candidate_count']} candidate(s), {result['evidence_count']} evidence item(s); "
            f"{missing} missing attachment(s).",
            level=SUCCESS_LEVEL,
            duration=8,
        )

    def _create_comparison_layer(self):
        self._workspace = update_workspace_payload(self._workspace)
        candidates = list(self._workspace.get("candidates", []) or [])
        if not candidates:
            self._warning("Add at least one candidate before creating a comparison layer.")
            return
        old = QgsProject.instance().mapLayer(self._comparison_layer_id)
        if old is not None:
            QgsProject.instance().removeMapLayer(old.id())

        workspace_name = str(
            self._workspace.get("metadata", {}).get("workspace_id", "Workspace")
        )
        layer = QgsVectorLayer(
            "Point?crs=EPSG:4326",
            f"GeoClick sources — {workspace_name}",
            "memory",
        )
        provider = layer.dataProvider()
        provider.addAttributes(
            [
                QgsField("candidate_id", QVariant.String),
                QgsField("label", QVariant.String),
                QgsField("source", QVariant.String),
                QgsField("source_id", QVariant.String),
                QgsField("preferred", QVariant.Bool),
                QgsField("agreement", QVariant.Double),
                QgsField("recommend", QVariant.Double),
                QgsField("geometry_type", QVariant.String),
            ]
        )
        layer.updateFields()
        features: List[QgsFeature] = []
        for candidate in candidates:
            feature = QgsFeature(layer.fields())
            feature.setGeometry(
                QgsGeometry.fromPointXY(
                    QgsPointXY(float(candidate["lon"]), float(candidate["lat"]))
                )
            )
            feature.setAttributes(
                [
                    str(candidate.get("candidate_id", "")),
                    str(candidate.get("label", "")),
                    str(candidate.get("source", "")),
                    str(candidate.get("source_id", "")),
                    bool(candidate.get("is_preferred", False)),
                    float(candidate.get("agreement_score", 0.0)),
                    float(candidate.get("recommendation_score", 0.0)),
                    str(candidate.get("geometry_type", "Point")),
                ]
            )
            features.append(feature)
        provider.addFeatures(features)
        layer.updateExtents()
        QgsProject.instance().addMapLayer(layer)
        self._comparison_layer_id = layer.id()
        self.iface.setActiveLayer(layer)
        preferred = next(
            (item for item in candidates if item.get("is_preferred")), candidates[0]
        )
        self.zoom_to_search_result(self._candidate_result(preferred))
        self.iface.messageBar().pushMessage(
            "Comparison layer created",
            f"{len(features)} source candidate(s) added as a temporary WGS84 layer.",
            level=SUCCESS_LEVEL,
            duration=6,
        )

    def _save_workspace_to_session(self, metadata: Mapping[str, object]):
        self._sync_workspace_metadata(metadata)
        self._workspace = update_workspace_payload(self._workspace)
        workspace_metadata = dict(self._workspace.get("metadata", {}) or {})
        candidates = list(self._workspace.get("candidates", []) or [])
        preferred_id = str(workspace_metadata.get("preferred_candidate_id", ""))
        preferred = next(
            (item for item in candidates if str(item.get("candidate_id", "")) == preferred_id),
            None,
        )
        if preferred is None:
            self._warning("Select one candidate as the preferred source before saving.")
            return
        verifier = str(workspace_metadata.get("verifier", "")).strip()
        status = str(workspace_metadata.get("status", "Draft"))
        rationale = str(workspace_metadata.get("rationale", "")).strip()
        if not verifier:
            self._warning("Enter the verifier name before saving the workspace.")
            return
        if status in {"Verified", "Rejected"} and not rationale:
            self._warning("A rationale is required for a Verified or Rejected workspace.")
            return

        result = self._candidate_result(preferred)
        result["search_query"] = str(workspace_metadata.get("place_name", ""))
        self.capture_search_result(result)
        if self.layer is None or self.last_feature_id is None:
            return
        if not self._prepare_layer():
            return

        timestamp = utc_now()
        summary = dict(self._workspace.get("summary", {}) or {})
        evidence = list(self._workspace.get("evidence", []) or [])
        fields = {field.name(): index for index, field in enumerate(self.layer.fields())}
        values: Dict[str, object] = {
            "capture_method": "verification_workspace",
            "workspace_id": str(workspace_metadata.get("workspace_id", "")),
            "verification_status": status,
            "preferred_candidate_id": preferred_id,
            "preferred_source": str(preferred.get("source", "")),
            "preferred_source_id": str(preferred.get("source_id", "")),
            "candidate_count": int(summary.get("candidate_count", len(candidates)) or 0),
            "source_count": int(summary.get("source_count", 0) or 0),
            "source_spread_m": float(summary.get("source_spread_m", 0.0) or 0.0),
            "consensus_level": str(summary.get("consensus_level", "")),
            "agreement_score": float(preferred.get("agreement_score", 0.0) or 0.0),
            "evidence_count": len(evidence),
            "evidence_manifest": json.dumps(evidence, ensure_ascii=False, separators=(",", ":")),
            "verification_rationale": rationale,
            "verified_by": verifier,
            "verified_at": timestamp,
            "workspace_snapshot": json.dumps(
                self._workspace, ensure_ascii=False, separators=(",", ":")
            ),
            "geometry_evidence_types": "; ".join(summary.get("geometry_types", []) or []),
        }

        review_status = {
            "Verified": "Approved",
            "Rejected": "Rejected",
            "In review": "Pending",
            "Draft": "Pending",
        }.get(status, "Pending")
        values.update(
            {
                "review_status": review_status,
                "reviewer": verifier,
                "reviewed_at": timestamp,
                "review_comment": rationale,
                "review_required": status != "Verified",
                "status": {
                    "Verified": "Verified",
                    "Rejected": "Rejected",
                    "In review": "Needs verification",
                    "Draft": "Unreviewed",
                }.get(status, "Unreviewed"),
            }
        )

        request = QgsFeatureRequest().setFilterFid(int(self.last_feature_id))
        feature = next(self.layer.getFeatures(request), None)
        if feature is not None and status in {"Verified", "Rejected"}:
            history_index = fields.get("review_history", -1)
            current_history = feature[history_index] if history_index >= 0 else ""
            history_json, iteration = append_review_history(
                current_history,
                action="workspace_verified" if status == "Verified" else "workspace_rejected",
                status=review_status,
                reviewer=verifier,
                comment=rationale,
                timestamp=timestamp,
            )
            values["review_history"] = history_json
            values["review_iteration"] = iteration

        changes = {
            fields[name]: value
            for name, value in values.items()
            if name in fields and fields[name] >= 0
        }
        if changes:
            self.layer.dataProvider().changeAttributeValues(
                {int(self.last_feature_id): changes}
            )
            self.layer.triggerRepaint()
            self._refresh_dock()
        self._persist_workspace()
        self.iface.messageBar().pushMessage(
            "Verification workspace saved",
            f"{preferred.get('label', '')} saved as {status} with {len(candidates)} source candidate(s).",
            level=SUCCESS_LEVEL,
            duration=8,
        )
