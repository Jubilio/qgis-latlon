"""Review Queue interface for GeoClick Capture 1.6.0."""

from __future__ import annotations

from typing import Dict, List, Optional

from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .dock_widget import _enum
from .dock_widget_v126 import plugin_icon
from .dock_widget_v150 import CaptureLogDockV150


class CaptureLogDockV160(CaptureLogDockV150):
    """Capture, search, matching, gazetteer and review workspace."""

    review_refresh_requested = pyqtSignal(dict)
    review_action_requested = pyqtSignal(str, object, dict)
    review_export_requested = pyqtSignal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._review_records: List[Dict[str, object]] = []

        self.review_page = self._build_review_page()
        self.review_tab_index = self.tabs.addTab(
            self.review_page, plugin_icon("review_queue.svg"), "Review Queue"
        )

    def _build_review_page(self) -> QWidget:
        page = QWidget(self)
        root = QVBoxLayout(page)

        intro = QLabel(
            "Review captured records, document a decision and keep an immutable history. "
            "Rejections and requests for changes require a comment."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        filter_row = QHBoxLayout()
        self.review_status_filter = QComboBox()
        self.review_status_filter.addItem("All review states", "")
        for status in ("Pending", "Needs changes", "Approved", "Rejected"):
            self.review_status_filter.addItem(status, status)
        self.review_status_filter.currentIndexChanged.connect(
            lambda _index: self._emit_review_refresh()
        )

        self.review_search_edit = QLineEdit()
        self.review_search_edit.setPlaceholderText(
            "Filter by place, ID, method, risk, reviewer or comment"
        )
        self.review_search_edit.returnPressed.connect(self._emit_review_refresh)

        self.review_refresh_button = QPushButton("Refresh")
        self.review_refresh_button.setIcon(plugin_icon("review_queue.svg"))
        self.review_refresh_button.clicked.connect(self._emit_review_refresh)
        filter_row.addWidget(self.review_status_filter)
        filter_row.addWidget(self.review_search_edit, 1)
        filter_row.addWidget(self.review_refresh_button)
        root.addLayout(filter_row)

        self.review_summary = QLabel("Open a destination layer to review its records.")
        self.review_summary.setWordWrap(True)
        root.addWidget(self.review_summary)

        self.review_table = QTableWidget(0, 8)
        self.review_table.setHorizontalHeaderLabels(
            [
                "ID",
                "Place",
                "Capture method",
                "Duplicate risk",
                "Review state",
                "Reviewer",
                "Reviewed at",
                "Comment",
            ]
        )
        self.review_table.setSelectionBehavior(
            _enum(QAbstractItemView, "SelectRows", "SelectionBehavior.SelectRows")
        )
        self.review_table.setSelectionMode(
            _enum(
                QAbstractItemView,
                "ExtendedSelection",
                "SelectionMode.ExtendedSelection",
            )
        )
        self.review_table.setEditTriggers(
            _enum(QAbstractItemView, "NoEditTriggers", "EditTrigger.NoEditTriggers")
        )
        self.review_table.itemSelectionChanged.connect(self._update_review_actions)
        self.review_table.cellDoubleClicked.connect(
            lambda _row, _column: self._emit_review_action("zoom")
        )
        root.addWidget(self.review_table, 1)

        form = QFormLayout()
        self.reviewer_edit = QLineEdit()
        self.reviewer_edit.setPlaceholderText("Reviewer name")
        self.review_comment_edit = QPlainTextEdit()
        self.review_comment_edit.setPlaceholderText(
            "Review comment; required for Reject and Needs changes"
        )
        self.review_comment_edit.setMaximumHeight(80)
        form.addRow("Reviewer", self.reviewer_edit)
        form.addRow("Comment", self.review_comment_edit)
        root.addLayout(form)

        decisions = QHBoxLayout()
        self.review_zoom_button = QPushButton("Zoom")
        self.review_zoom_button.setIcon(plugin_icon("zoom_existing.svg"))
        self.review_zoom_button.clicked.connect(
            lambda: self._emit_review_action("zoom")
        )
        self.review_approve_button = QPushButton("Approve")
        self.review_approve_button.setIcon(plugin_icon("review_approve.svg"))
        self.review_approve_button.clicked.connect(
            lambda: self._emit_review_action("approve")
        )
        self.review_changes_button = QPushButton("Needs changes")
        self.review_changes_button.setIcon(plugin_icon("review_changes.svg"))
        self.review_changes_button.clicked.connect(
            lambda: self._emit_review_action("needs_changes")
        )
        self.review_reject_button = QPushButton("Reject")
        self.review_reject_button.setIcon(plugin_icon("review_reject.svg"))
        self.review_reject_button.clicked.connect(
            lambda: self._emit_review_action("reject")
        )
        self.review_pending_button = QPushButton("Reset pending")
        self.review_pending_button.setIcon(plugin_icon("review_queue.svg"))
        self.review_pending_button.clicked.connect(
            lambda: self._emit_review_action("pending")
        )
        for button in (
            self.review_zoom_button,
            self.review_approve_button,
            self.review_changes_button,
            self.review_reject_button,
            self.review_pending_button,
        ):
            decisions.addWidget(button)
        root.addLayout(decisions)

        secondary = QHBoxLayout()
        self.review_history_button = QPushButton("History")
        self.review_history_button.setIcon(plugin_icon("review_history.svg"))
        self.review_history_button.clicked.connect(
            lambda: self._emit_review_action("history")
        )
        self.review_export_button = QPushButton("Export review CSV")
        self.review_export_button.setIcon(plugin_icon("review_export.svg"))
        self.review_export_button.clicked.connect(self._browse_review_export)
        secondary.addWidget(self.review_history_button)
        secondary.addWidget(self.review_export_button)
        secondary.addStretch(1)
        root.addLayout(secondary)

        note = QLabel(
            "Approve and Reject are final states. Needs changes and Reset pending keep the "
            "record in the active review queue. Multiple selected rows can be updated together."
        )
        note.setWordWrap(True)
        root.addWidget(note)

        self._set_review_actions_enabled(False)
        return page

    def review_filters(self) -> Dict[str, str]:
        return {
            "status": str(self.review_status_filter.currentData() or ""),
            "query": self.review_search_edit.text().strip(),
        }

    def review_payload(self) -> Dict[str, str]:
        reviewer = self.reviewer_edit.text().strip()
        if not reviewer and hasattr(self, "operator_edit"):
            reviewer = self.operator_edit.text().strip()
        return {
            "reviewer": reviewer,
            "comment": self.review_comment_edit.toPlainText().strip(),
        }

    def _emit_review_refresh(self):
        self.review_refresh_requested.emit(self.review_filters())

    def _emit_review_action(self, action: str):
        records = self.selected_review_records()
        if records:
            self.review_action_requested.emit(action, records, self.review_payload())

    def _browse_review_export(self):
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export review queue",
            "geoclick_review_queue.csv",
            "CSV files (*.csv);;All files (*.*)",
        )
        if path:
            self.review_export_requested.emit(path, self.review_filters())

    def selected_review_records(self) -> List[Dict[str, object]]:
        selection = self.review_table.selectionModel().selectedRows()
        records: List[Dict[str, object]] = []
        for index in sorted(selection, key=lambda item: item.row()):
            row = index.row()
            if 0 <= row < len(self._review_records):
                records.append(dict(self._review_records[row]))
        return records

    def show_review_tab(self):
        self.tabs.setCurrentIndex(self.review_tab_index)
        if not self.reviewer_edit.text().strip() and hasattr(self, "operator_edit"):
            self.reviewer_edit.setText(self.operator_edit.text().strip())
        self._emit_review_refresh()

    def set_review_busy(self, busy: bool, message: str = ""):
        self.review_refresh_button.setEnabled(not busy)
        self.review_export_button.setEnabled(not busy)
        if message:
            self.review_summary.setText(message)
        if busy:
            self._set_review_actions_enabled(False)

    def set_review_records(
        self,
        records: List[Dict[str, object]],
        counts: Optional[Dict[str, int]] = None,
        message: str = "",
    ):
        self._review_records = [dict(record) for record in records]
        self.review_table.setRowCount(0)
        for record in self._review_records:
            row = self.review_table.rowCount()
            self.review_table.insertRow(row)
            values = (
                str(record.get("record_id", record.get("feature_id", ""))),
                str(record.get("display_label", "")),
                str(record.get("capture_method", "")),
                str(record.get("duplicate_risk", "")),
                str(record.get("review_status", "Pending")),
                str(record.get("reviewer", "")),
                str(record.get("reviewed_at", "")),
                str(record.get("review_comment", "")),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in (1, 7):
                    item.setToolTip(value)
                self.review_table.setItem(row, column, item)
        self.review_table.resizeColumnsToContents()
        if self._review_records:
            self.review_table.selectRow(0)

        if message:
            self.review_summary.setText(message)
        elif counts:
            self.review_summary.setText(
                "{all_count} record(s) — {pending} pending, {changes} needs changes, "
                "{approved} approved, {rejected} rejected. Showing {shown}.".format(
                    all_count=int(counts.get("All", 0)),
                    pending=int(counts.get("Pending", 0)),
                    changes=int(counts.get("Needs changes", 0)),
                    approved=int(counts.get("Approved", 0)),
                    rejected=int(counts.get("Rejected", 0)),
                    shown=len(self._review_records),
                )
            )
        else:
            self.review_summary.setText(
                f"Showing {len(self._review_records)} review record(s)."
            )
        self._update_review_actions()

    def clear_review_comment(self):
        self.review_comment_edit.clear()

    def _set_review_actions_enabled(self, enabled: bool):
        for button in (
            self.review_zoom_button,
            self.review_approve_button,
            self.review_changes_button,
            self.review_reject_button,
            self.review_pending_button,
            self.review_history_button,
        ):
            button.setEnabled(enabled)

    def _update_review_actions(self):
        selected = self.selected_review_records()
        self._set_review_actions_enabled(bool(selected))
        self.review_history_button.setEnabled(len(selected) == 1)
