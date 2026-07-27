"""Search & Capture extension for GeoClick Capture 1.3.0."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlencode

from qgis.PyQt.QtCore import QLocale, QTimer, QUrl, QVariant
from qgis.PyQt.QtGui import QColor, QDesktopServices, QGuiApplication
from qgis.PyQt.QtNetwork import QNetworkRequest
from qgis.PyQt.QtWidgets import QAction
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsField,
    QgsMessageLog,
    QgsNetworkAccessManager,
    QgsPointXY,
    QgsProject,
    QgsRectangle,
)
from qgis.gui import QgsVertexMarker

from .dock_widget_v130 import CaptureLogDockV130
from .plugin_v121 import _right_dock_area
from .plugin_v124 import (
    INFO_LEVEL,
    NETWORK_NO_ERROR,
    NO_LESS_SAFE_REDIRECT_POLICY,
    REDIRECT_POLICY_ATTRIBUTE,
    USER_AGENT_HEADER,
    WARNING_LEVEL,
)
from .plugin_v126 import GeoClickCapturePluginV126, plugin_icon
from .qgis_latlon import PLUGIN_MENU, SUCCESS_LEVEL, WGS84
from .search_utils import classify_search_input, normalise_nominatim_results
from .utils import normalise_session_id, safe_project_name, to_dms

SEARCH_FIELDS = (
    ("capture_method", QVariant.String),
    ("search_query", QVariant.String),
    ("search_provider", QVariant.String),
    ("provider_result_id", QVariant.String),
    ("result_label", QVariant.String),
    ("result_type", QVariant.String),
    ("result_importance", QVariant.Double),
    ("osm_type", QVariant.String),
    ("osm_id", QVariant.String),
    ("input_format", QVariant.String),
)
SEARCH_ENDPOINT = "https://nominatim.openstreetmap.org/search"


class GeoClickCapturePluginV130(GeoClickCapturePluginV126):
    """Find, review and add places to an auditable capture session."""

    def __init__(self, iface):
        super().__init__(iface)
        self.search_action: Optional[QAction] = None
        self._search_cache: Dict[str, List[Dict[str, object]]] = {}
        self._last_search_request = 0.0
        self._preview_marker: Optional[QgsVertexMarker] = None

    def initGui(self):
        parent = self.iface.mainWindow()
        self.search_action = QAction(
            plugin_icon("search_place.svg"), "Search & capture place", parent
        )
        self.search_action.setToolTip(
            "Find an address, place, coordinate pair or map URL and add it to the capture log"
        )
        self.search_action.triggered.connect(self.show_search)
        super().initGui()
        self.iface.addToolBarIcon(self.search_action)

    def _menu_actions(self):
        actions = super()._menu_actions()
        if self.search_action is not None and self.search_action not in actions:
            actions.append(self.search_action)
        return actions

    def _create_dock(self):
        self.dock = CaptureLogDockV130(self.iface.mainWindow())
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
        self.dock.set_preferences(self._load_preferences())

    def unload(self):
        self._clear_preview()
        if self.search_action is not None:
            self.iface.removeToolBarIcon(self.search_action)
        super().unload()
        self.search_action = None
        self._search_cache.clear()

    def show_search(self):
        self.show_dock()
        if isinstance(self.dock, CaptureLogDockV130):
            self.dock.show_search_tab()

    def _prepare_layer(self) -> bool:
        if not super()._prepare_layer() or self.layer is None:
            return False
        existing = {field.name() for field in self.layer.fields()}
        missing = [
            QgsField(name, field_type)
            for name, field_type in SEARCH_FIELDS
            if name not in existing
        ]
        if missing:
            if not self.layer.dataProvider().addAttributes(missing):
                self._critical("The search audit fields could not be added.")
                return False
            self.layer.updateFields()
        return True

    def search_place(self, options: Dict[str, object]):
        """Classify an input and search Nominatim only when text lookup is needed."""
        if not isinstance(self.dock, CaptureLogDockV130):
            return
        classified = classify_search_input(str(options.get("query", "")))
        if classified.get("kind") == "empty":
            self.dock.set_search_message("Enter a place, coordinate pair or map URL.")
            return

        if classified.get("kind") == "coordinate":
            lat = float(classified["lat"])
            lon = float(classified["lon"])
            result = {
                "display_name": f"Coordinates {lat:.6f}, {lon:.6f}",
                "lat": lat,
                "lon": lon,
                "result_type": "coordinate",
                "category": "coordinate",
                "importance": 0.0,
                "osm_type": "",
                "osm_id": "",
                "provider_result_id": "",
                "boundingbox": [],
                "provider": "Direct input",
                "input_format": str(classified.get("input_format", "coordinate")),
                "search_query": str(classified.get("raw", "")),
            }
            self.dock.set_search_results(
                [result],
                "Coordinate recognised locally. No external request was required.",
            )
            self.preview_search_result(result)
            return

        query = str(classified.get("query", "")).strip()
        countrycodes = str(options.get("countrycodes", "")).strip().lower()
        viewbox = ""
        if bool(options.get("restrict_to_extent", False)):
            viewbox = self._current_extent_viewbox()
            if not viewbox:
                self.dock.set_search_message(
                    "The current map extent could not be converted to WGS 84."
                )
                return

        cache_key = json.dumps(
            {"q": query.casefold(), "countrycodes": countrycodes, "viewbox": viewbox},
            sort_keys=True,
        )
        if cache_key in self._search_cache:
            self.dock.set_search_results(
                self._search_cache[cache_key], "Results loaded from the local search cache."
            )
            return

        self.dock.set_search_busy(True, f"Searching OpenStreetMap for “{query}”…")
        elapsed = time.monotonic() - self._last_search_request
        wait_ms = max(0, int((1.1 - elapsed) * 1000))
        QTimer.singleShot(
            wait_ms,
            lambda: self._request_place_search(
                query, countrycodes, viewbox, cache_key, attempt=0
            ),
        )

    def _current_extent_viewbox(self) -> str:
        try:
            project_crs = self.canvas.mapSettings().destinationCrs()
            if not project_crs.isValid():
                return ""
            extent = self.canvas.extent()
            transform = QgsCoordinateTransform(project_crs, WGS84, QgsProject.instance())
            lower_left = transform.transform(QgsPointXY(extent.xMinimum(), extent.yMinimum()))
            upper_right = transform.transform(QgsPointXY(extent.xMaximum(), extent.yMaximum()))
            west, east = sorted((float(lower_left.x()), float(upper_right.x())))
            south, north = sorted((float(lower_left.y()), float(upper_right.y())))
            return f"{west:.8f},{north:.8f},{east:.8f},{south:.8f}"
        except (RuntimeError, TypeError, ValueError):
            return ""

    def _request_place_search(
        self,
        query: str,
        countrycodes: str,
        viewbox: str,
        cache_key: str,
        attempt: int,
    ):
        self._last_search_request = time.monotonic()
        language = (QLocale.system().name() or "en").split("_", 1)[0]
        parameters = {
            "q": query,
            "format": "jsonv2",
            "addressdetails": 1,
            "limit": 8,
            "accept-language": language,
            "email": "jubiliomausse5@gmail.com",
        }
        if countrycodes:
            parameters["countrycodes"] = countrycodes
        if viewbox:
            parameters["viewbox"] = viewbox
            parameters["bounded"] = 1

        request = QNetworkRequest(QUrl(f"{SEARCH_ENDPOINT}?{urlencode(parameters)}"))
        request.setHeader(
            USER_AGENT_HEADER,
            "GeoClick-Capture/1.3.0 "
            "(+https://github.com/Jubilio/qgis-latlon; contact=jubiliomausse5@gmail.com)",
        )
        request.setRawHeader(b"Accept", b"application/json")
        request.setAttribute(
            REDIRECT_POLICY_ATTRIBUTE, NO_LESS_SAFE_REDIRECT_POLICY
        )
        if hasattr(request, "setTransferTimeout"):
            try:
                request.setTransferTimeout(15000)
            except (TypeError, RuntimeError):
                pass

        reply = QgsNetworkAccessManager.instance().get(request)
        self._pending_replies.append(reply)
        self._ssl_errors[id(reply)] = []
        if hasattr(reply, "sslErrors"):
            reply.sslErrors.connect(
                lambda errors, r=reply: self._record_ssl_errors(r, errors)
            )
        timeout = QTimer(reply)
        timeout.setSingleShot(True)
        timeout.timeout.connect(reply.abort)
        timeout.start(20000)
        reply.finished.connect(
            lambda r=reply: self._finish_place_search(
                r, query, countrycodes, viewbox, cache_key, attempt
            )
        )

    def _finish_place_search(
        self,
        reply,
        query: str,
        countrycodes: str,
        viewbox: str,
        cache_key: str,
        attempt: int,
    ):
        try:
            status = self._http_status(reply)
            error_value = reply.error()
            error_text = str(reply.errorString() or "").strip()
            ssl_errors = self._ssl_errors.pop(id(reply), [])
            response_text = bytes(reply.readAll()).decode("utf-8", errors="replace")
            failed = error_value != NETWORK_NO_ERROR or status >= 400

            transient_statuses = {408, 425, 429, 500, 502, 503, 504}
            transient_network_error = failed and not status and not ssl_errors
            if (
                failed
                and attempt < 1
                and (status in transient_statuses or transient_network_error)
            ):
                if isinstance(self.dock, CaptureLogDockV130):
                    self.dock.set_search_message(
                        "The place search failed temporarily; retrying once…"
                    )
                QTimer.singleShot(
                    2000,
                    lambda: self._request_place_search(
                        query, countrycodes, viewbox, cache_key, attempt + 1
                    ),
                )
                return

            if failed:
                detail = self._geocode_failure_message(
                    status, error_text, ssl_errors, response_text
                )
                QgsMessageLog.logMessage(
                    f"Place search failed: {detail}",
                    "GeoClick Capture",
                    level=WARNING_LEVEL,
                )
                if isinstance(self.dock, CaptureLogDockV130):
                    self.dock.set_search_busy(False, f"Place search failed: {detail}")
                return

            payload = json.loads(response_text)
            results = normalise_nominatim_results(payload)
            for result in results:
                result["search_query"] = query
            self._search_cache[cache_key] = results
            if isinstance(self.dock, CaptureLogDockV130):
                self.dock.set_search_busy(False)
                self.dock.set_search_results(results)
            if results:
                self.preview_search_result(results[0])
        except (ValueError, UnicodeDecodeError, RuntimeError, TypeError) as exc:
            QgsMessageLog.logMessage(
                f"Invalid place-search response: {exc}",
                "GeoClick Capture",
                level=WARNING_LEVEL,
            )
            if isinstance(self.dock, CaptureLogDockV130):
                self.dock.set_search_busy(False, f"Invalid search response: {exc}")
        finally:
            self._ssl_errors.pop(id(reply), None)
            if reply in self._pending_replies:
                self._pending_replies.remove(reply)
            reply.deleteLater()

    def handle_search_action(self, action: str, result: Dict[str, object]):
        if action == "zoom":
            self.zoom_to_search_result(result)
        elif action == "preview":
            self.preview_search_result(result)
        elif action == "capture":
            self.capture_search_result(result)
        elif action == "copy":
            self.copy_search_coordinates(result)
        elif action == "open_osm":
            self.open_search_result(result, "osm")
        elif action == "open_google":
            self.open_search_result(result, "google")

    def _result_project_point(self, result: Dict[str, object]) -> QgsPointXY:
        point = QgsPointXY(float(result["lon"]), float(result["lat"]))
        project_crs = self.canvas.mapSettings().destinationCrs()
        if project_crs.isValid() and project_crs != WGS84:
            point = QgsCoordinateTransform(
                WGS84, project_crs, QgsProject.instance()
            ).transform(point)
        return QgsPointXY(point)

    def zoom_to_search_result(self, result: Dict[str, object]):
        try:
            project_point = self._result_project_point(result)
            bounds = result.get("boundingbox", [])
            if isinstance(bounds, list) and len(bounds) == 4:
                south, north, west, east = [float(value) for value in bounds]
                project_crs = self.canvas.mapSettings().destinationCrs()
                transform = QgsCoordinateTransform(WGS84, project_crs, QgsProject.instance())
                lower_left = transform.transform(QgsPointXY(west, south))
                upper_right = transform.transform(QgsPointXY(east, north))
                extent = QgsRectangle(lower_left, upper_right)
                if not extent.isEmpty():
                    extent.scale(1.15)
                    self.canvas.setExtent(extent)
                else:
                    self.canvas.setCenter(project_point)
                    self.canvas.zoomScale(5000)
            else:
                self.canvas.setCenter(project_point)
                self.canvas.zoomScale(5000)
            self.canvas.refresh()
            self.preview_search_result(result)
        except (KeyError, RuntimeError, TypeError, ValueError) as exc:
            self._warning(f"The search result could not be displayed: {exc}")

    def preview_search_result(self, result: Dict[str, object]):
        try:
            point = self._result_project_point(result)
            self._clear_preview()
            marker = QgsVertexMarker(self.canvas)
            marker.setCenter(point)
            marker.setColor(QColor(231, 122, 34))
            marker.setIconSize(18)
            marker.setPenWidth(3)
            self._preview_marker = marker
        except (KeyError, RuntimeError, TypeError, ValueError):
            self._clear_preview()

    def _clear_preview(self):
        if self._preview_marker is None:
            return
        try:
            self.canvas.scene().removeItem(self._preview_marker)
        except RuntimeError:
            pass
        self._preview_marker = None

    def capture_search_result(self, result: Dict[str, object]):
        try:
            lat = float(result["lat"])
            lon = float(result["lon"])
            wgs84_point = QgsPointXY(lon, lat)
            map_point = self._result_project_point(result)
        except (KeyError, RuntimeError, TypeError, ValueError) as exc:
            self._warning(f"The selected result has invalid coordinates: {exc}")
            return

        context = self.dock.capture_context() if self.dock is not None else {}
        context["session_id"] = normalise_session_id(context.get("session_id", ""))
        project = QgsProject.instance()
        project_crs = self.canvas.mapSettings().destinationCrs()
        captured_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
            "+00:00", "Z"
        )
        self._current_snap = {
            "snapped": False,
            "snap_type": "",
            "snap_distance": 0.0,
        }
        feature_id = self.add_point_to_layer(
            map_point=map_point,
            wgs84_point=wgs84_point,
            captured_at=captured_at,
            project_authid=project_crs.authid() or project_crs.description(),
            project_name=safe_project_name(
                project.fileName(), project.title() or "Untitled project"
            ),
            map_scale=float(self.canvas.scale()),
            source_layer="",
            source_layer_id="",
            source_feature_id="",
            location=str(result.get("display_name", "")),
            context=context,
        )
        if feature_id is None or self.layer is None:
            return

        input_format = str(result.get("input_format", "text"))
        capture_method = (
            "map_url"
            if input_format in {"openstreetmap_url", "google_maps_url"}
            else "coordinate"
            if input_format == "decimal_coordinates"
            else "search"
        )
        audit = {
            "capture_method": capture_method,
            "search_query": str(result.get("search_query", "")),
            "search_provider": str(result.get("provider", "")),
            "provider_result_id": str(result.get("provider_result_id", "")),
            "result_label": str(result.get("display_name", "")),
            "result_type": str(result.get("result_type", "")),
            "result_importance": float(result.get("importance", 0.0) or 0.0),
            "osm_type": str(result.get("osm_type", "")),
            "osm_id": str(result.get("osm_id", "")),
            "input_format": input_format,
        }
        changes = {}
        for field_name, value in audit.items():
            index = self.layer.fields().indexOf(field_name)
            if index >= 0:
                changes[index] = value
        if changes:
            self.layer.dataProvider().changeAttributeValues({feature_id: changes})

        self.last_coords = (lat, lon)
        self.last_feature_id = feature_id
        self._save_preferences()
        self._refresh_dock()
        self.layer.triggerRepaint()
        self.iface.messageBar().pushMessage(
            "Place added to session",
            f"{result.get('display_name', '')} | {lat:.6f}, {lon:.6f}",
            level=SUCCESS_LEVEL,
            duration=7,
        )

        if (
            capture_method in {"coordinate", "map_url"}
            and self.reverse_geocode_action
            and self.reverse_geocode_action.isChecked()
        ):
            self._queue_reverse_geocode(lat, lon, feature_id)

    def copy_search_coordinates(self, result: Dict[str, object]):
        try:
            lat = float(result["lat"])
            lon = float(result["lon"])
        except (KeyError, TypeError, ValueError):
            return
        text = f"{lat:.6f}, {lon:.6f}"
        QGuiApplication.clipboard().setText(text)
        self.iface.messageBar().pushMessage(
            "Coordinates copied",
            f"{text} | {to_dms(lat, 'lat')}, {to_dms(lon, 'lon')}",
            level=INFO_LEVEL,
            duration=5,
        )

    @staticmethod
    def open_search_result(result: Dict[str, object], provider: str):
        try:
            lat = float(result["lat"])
            lon = float(result["lon"])
        except (KeyError, TypeError, ValueError):
            return
        if provider == "google":
            url = f"https://www.google.com/maps/search/?api=1&query={lat:.8f},{lon:.8f}"
        else:
            url = f"https://www.openstreetmap.org/?mlat={lat:.8f}&mlon={lon:.8f}#map=18/{lat:.8f}/{lon:.8f}"
        QDesktopServices.openUrl(QUrl(url))
