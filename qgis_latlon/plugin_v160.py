"""Review Workflow extension for GeoClick Capture 1.6.0."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from typing import Dict, List, Optional

from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.core import QgsFeatureRequest, QgsField

from .dock_widget_v126 import plugin_icon
from .dock_widget_v160 import CaptureLogDockV160
from .plugin_v121 import _right_dock_area
from .plugin_v150 import GeoClickCapturePluginV150
from .qgis_latlon import SUCCESS_LEVEL
from .review_utils import (
    append_review_history,
    normalise_review_status,
    parse_review_history,
    record_matches_review_filter,
    review_status_counts,
)

REVIEW_FIELDS = (
    ("review_status", QVariant.String),
    ("reviewer", QVariant.String),
    ("reviewed_at", QVariant.String),
    ("review_comment", QVariant.String),
    ("review_history", QVariant.String),
    ("review_iteration", QVariant.Int),
)

_ACTION_STATUS = {
    "approve": "Approved",
    "reject": "Rejected",
    "needs_changes": "Needs changes",
    "pending": "Pending",
}

_OPERATIONAL_STATUS = {
    "Approved": "Verified",
    "Rejected": "Rejected",
    "Needs changes": "Needs verification",
    "Pending": "Unreviewed",
}


class GeoClickCapturePluginV160(GeoClickCapturePluginV150):
    """Review captured records and preserve every decision in an audit history."""

    def __init__(self, iface):
        super().__init__(iface)
        self.review_action: Optional[QAction] = None

    def initGui(self):
        parent = self.iface.mainWindow()
        self.review_action = QAction(
            plugin_icon("review_queue.svg"), "Open review queue", parent
        )
        self.review_action.setToolTip(
            "Approve, reject or return captured records while preserving review history"
        )
        self.review_action.triggered.connect(self.show_review)
        super().initGui()
        self.iface.addToolBarIcon(self.review_action)

    def _menu_actions(self):
        actions = super()._menu_actions()
        if self.review_action is not None and self.review_action not in actions:
            actions.append(self.review_action)
        return actions

    def _create_dock(self):
        self.dock = CaptureLogDockV160(self.iface.mainWindow())
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
        self.dock.set_preferences(self._load_preferences())

    def unload(self):
        if self.review_action is not None:
            self.iface.removeToolBarIcon(self.review_action)
        super().unload()
        self.review_action = None

    def show_review(self):
        self.show_dock()
        if isinstance(self.dock, CaptureLogDockV160):
            self.dock.show_review_tab()

    def set_destination_layer(self, layer):
        super().set_destination_layer(layer)
        if isinstance(self.dock, CaptureLogDockV160):
            self.refresh_review_queue(self.dock.review_filters())

    def _prepare_layer(self) -> bool:
        if not super()._prepare_layer() or self.layer is None:
            return False
        existing = {field.name() for field in self.layer.fields()}
        missing = [
            QgsField(name, field_type)
            for name, field_type in REVIEW_FIELDS
            if name not in existing
        ]
        if missing:
            if not self.layer.dataProvider().addAttributes(missing):
                self._critical("The review-workflow audit fields could not be added.")
                return False
            self.layer.updateFields()
        return True

    def refresh_review_queue(self, filters: Optional[Dict[str, object]] = None):
        if not isinstance(self.dock, CaptureLogDockV160):
            return
        filters = dict(filters or {})
        if self.layer is None or not self.layer.isValid():
            self.dock.set_review_records(
                [],
                message="Select or create a destination point layer to review its records.",
            )
            return
        if not self._prepare_layer() or self.layer is None:
            return

        self.dock.set_review_busy(True, "Reading review records…")
        all_records = [self._review_record(feature) for feature in self.layer.getFeatures()]
        all_records = [record for record in all_records if record is not None]
        counts = review_status_counts(all_records)
        status_filter = str(filters.get("status", "") or "")
        query = str(filters.get("query", "") or "")
        records = [
            record
            for record in all_records
            if record_matches_review_filter(record, status_filter, query)
        ]
        records.sort(
            key=lambda item: (
                {"Pending": 0, "Needs changes": 1, "Rejected": 2, "Approved": 3}.get(
                    str(item.get("review_status", "Pending")), 4
                ),
                str(item.get("reviewed_at", "")),
                str(item.get("display_label", "")).casefold(),
            )
        )
        self.dock.set_review_busy(False)
        self.dock.set_review_records(records, counts)

    def _review_record(self, feature) -> Optional[Dict[str, object]]:
        if self.layer is None:
            return None
        point = self._feature_point_wgs84(feature, self.layer)
        field_names = {field.name() for field in self.layer.fields()}

        def value(name: str, default: object = "") -> object:
            return feature[name] if name in field_names else default

        display_label = next(
            (
                str(candidate).strip()
                for candidate in (
                    value("result_label"),
                    value("gazetteer_name"),
                    value("location"),
                    value("note"),
                )
                if str(candidate or "").strip()
            ),
            f"Record {feature.id()}",
        )
        review_status = normalise_review_status(
            value("review_status"), value("review_required", True)
        )
        record_id = value("id", feature.id())
        return {
            "feature_id": int(feature.id()),
            "record_id": record_id,
            "display_label": display_label,
            "location": str(value("location", "")),
            "result_label": str(value("result_label", "")),
            "gazetteer_name": str(value("gazetteer_name", "")),
            "capture_method": str(value("capture_method", "map_click") or "map_click"),
            "duplicate_risk": str(value("duplicate_risk", "")),
            "review_required": bool(value("review_required", True)),
            "review_status": review_status,
            "reviewer": str(value("reviewer", "")),
            "reviewed_at": str(value("reviewed_at", "")),
            "review_comment": str(value("review_comment", "")),
            "review_history": str(value("review_history", "")),
            "review_iteration": int(value("review_iteration", 0) or 0),
            "lat": float(point.y()) if point is not None else None,
            "lon": float(point.x()) if point is not None else None,
        }

    def handle_review_action(
        self, action: str, records: object, payload: Dict[str, object]
    ):
        selected = [dict(record) for record in (records or [])]
        if not selected:
            return
        if action == "zoom":
            self._zoom_review_record(selected[0])
        elif action == "history":
            self._show_review_history(selected[0])
        elif action in _ACTION_STATUS:
            self._apply_review_decision(action, selected, payload)

    def _zoom_review_record(self, record: Dict[str, object]):
        try:
            lat = float(record["lat"])
            lon = float(record["lon"])
        except (KeyError, TypeError, ValueError):
            self._warning("The selected review record has no valid point geometry.")
            return
        self.zoom_to_search_result(
            {
                "lat": lat,
                "lon": lon,
                "display_name": str(record.get("display_label", "Review record")),
                "boundingbox": [],
            }
        )

    def _show_review_history(self, record: Dict[str, object]):
        history = parse_review_history(record.get("review_history"))
        if history:
            lines: List[str] = []
            for item in history:
                header = (
                    f"#{item.get('iteration', '')} — {item.get('status', '')} — "
                    f"{item.get('timestamp', '')}"
                )
                reviewer = str(item.get("reviewer", ""))
                comment = str(item.get("comment", ""))
                lines.append(header)
                if reviewer:
                    lines.append(f"Reviewer: {reviewer}")
                if comment:
                    lines.append(f"Comment: {comment}")
                lines.append("")
            text = "\n".join(lines).strip()
        else:
            text = "No review decision has been recorded for this feature."
        QMessageBox.information(
            self.iface.mainWindow(),
            f"Review history — {record.get('display_label', '')}",
            text,
        )

    def _apply_review_decision(
        self,
        action: str,
        records: List[Dict[str, object]],
        payload: Dict[str, object],
    ):
        if self.layer is None or not self._prepare_layer():
            return
        reviewer = str(payload.get("reviewer", "") or "").strip()
        comment = str(payload.get("comment", "") or "").strip()
        if not reviewer:
            self._warning("Enter the reviewer name before recording a decision.")
            return
        if action in {"reject", "needs_changes"} and not comment:
            self._warning("A review comment is required for Reject and Needs changes.")
            return

        status = _ACTION_STATUS[action]
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
            "+00:00", "Z"
        )
        field_indexes = {
            name: self.layer.fields().indexOf(name)
            for name, _field_type in REVIEW_FIELDS
        }
        review_required_index = self.layer.fields().indexOf("review_required")
        operational_status_index = self.layer.fields().indexOf("status")
        changes_by_feature: Dict[int, Dict[int, object]] = {}
        updated = 0

        for record in records:
            try:
                feature_id = int(record["feature_id"])
            except (KeyError, TypeError, ValueError):
                continue
            request = QgsFeatureRequest().setFilterFid(feature_id)
            feature = next(self.layer.getFeatures(request), None)
            if feature is None:
                continue
            history_index = field_indexes.get("review_history", -1)
            current_history = feature[history_index] if history_index >= 0 else ""
            history_json, iteration = append_review_history(
                current_history,
                action=action,
                status=status,
                reviewer=reviewer,
                comment=comment,
                timestamp=timestamp,
            )
            values = {
                "review_status": status,
                "reviewer": reviewer,
                "reviewed_at": timestamp,
                "review_comment": comment,
                "review_history": history_json,
                "review_iteration": iteration,
            }
            changes: Dict[int, object] = {}
            for name, value in values.items():
                index = field_indexes.get(name, -1)
                if index >= 0:
                    changes[index] = value
            if review_required_index >= 0:
                changes[review_required_index] = status in {"Pending", "Needs changes"}
            if operational_status_index >= 0:
                changes[operational_status_index] = _OPERATIONAL_STATUS[status]
            if changes:
                changes_by_feature[feature_id] = changes
                updated += 1

        if not changes_by_feature:
            self._warning("No selected record could be updated.")
            return
        if not self.layer.dataProvider().changeAttributeValues(changes_by_feature):
            self._critical("The review decisions could not be saved to the destination layer.")
            return
        self.layer.triggerRepaint()
        self._refresh_dock()
        if isinstance(self.dock, CaptureLogDockV160):
            self.dock.clear_review_comment()
            self.refresh_review_queue(self.dock.review_filters())
        self.iface.messageBar().pushMessage(
            "Review decision recorded",
            f"{updated} record(s) set to {status} by {reviewer}.",
            level=SUCCESS_LEVEL,
            duration=7,
        )

    def export_review_queue(self, path: str, filters: Dict[str, object]):
        if self.layer is None or not self.layer.isValid():
            self._warning("There is no destination layer to export.")
            return
        if not path.lower().endswith(".csv"):
            path = f"{path}.csv"
        all_records = [self._review_record(feature) for feature in self.layer.getFeatures()]
        status_filter = str(filters.get("status", "") or "")
        query = str(filters.get("query", "") or "")
        records = [
            record
            for record in all_records
            if record is not None
            and record_matches_review_filter(record, status_filter, query)
        ]
        columns = (
            "record_id",
            "feature_id",
            "display_label",
            "capture_method",
            "duplicate_risk",
            "review_status",
            "reviewer",
            "reviewed_at",
            "review_comment",
            "review_iteration",
            "review_required",
            "lat",
            "lon",
        )
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(records)
        except OSError as exc:
            self._critical(f"The review CSV could not be written: {exc}")
            return
        self.iface.messageBar().pushMessage(
            "Review queue exported",
            f"{len(records)} record(s) written to {path}",
            level=SUCCESS_LEVEL,
            duration=7,
        )
