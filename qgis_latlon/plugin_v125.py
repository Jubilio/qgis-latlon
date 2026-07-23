"""Broader-area reverse geocoding fallback for GeoClick Capture 1.2.5."""

from __future__ import annotations

import json
import time
from urllib.parse import urlencode

from qgis.PyQt.QtCore import QLocale, QTimer, QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest
from qgis.core import QgsMessageLog, QgsNetworkAccessManager

from .plugin_v124 import (
    GeoClickCapturePluginV124,
    INFO_LEVEL,
    NETWORK_NO_ERROR,
    NO_LESS_SAFE_REDIRECT_POLICY,
    REDIRECT_POLICY_ATTRIBUTE,
    USER_AGENT_HEADER,
    WARNING_LEVEL,
)


ZOOM_LEVELS = (18, 15, 10, 5, 3)
ZOOM_LABELS = {
    18: "building or street",
    15: "settlement",
    10: "city",
    5: "state or province",
    3: "country",
}
NO_RESULT_MESSAGES = {
    "unable to geocode",
    "no result found",
    "not found",
}


class GeoClickCapturePluginV125(GeoClickCapturePluginV124):
    """Reverse geocoding with progressive administrative-area fallback."""

    def _request_reverse_geocode(
        self,
        lat: float,
        lon: float,
        feature_id: int,
        key: str,
        attempt: int = 0,
        zoom_index: int = 0,
    ):
        """Request the best available OSM place, from detailed to broad."""
        self._last_geocode_request = time.monotonic()
        zoom_index = max(0, min(zoom_index, len(ZOOM_LEVELS) - 1))
        zoom = ZOOM_LEVELS[zoom_index]
        language = (QLocale.system().name() or "en").split("_", 1)[0]
        parameters = urlencode(
            {
                "lat": f"{lat:.8f}",
                "lon": f"{lon:.8f}",
                "format": "jsonv2",
                "zoom": zoom,
                "layer": "address",
                "addressdetails": 0,
                "accept-language": language,
                "email": "jubiliomausse5@gmail.com",
            }
        )
        request = QNetworkRequest(
            QUrl(f"https://nominatim.openstreetmap.org/reverse?{parameters}")
        )
        request.setHeader(
            USER_AGENT_HEADER,
            "GeoClick-Capture/1.2.5 "
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
            lambda r=reply, fid=feature_id, cache_key=key, latitude=lat,
            longitude=lon, retry_attempt=attempt, level_index=zoom_index:
            self._finish_reverse_geocode(
                r,
                fid,
                cache_key,
                latitude,
                longitude,
                retry_attempt,
                level_index,
            )
        )

    def _schedule_reverse_geocode(
        self,
        lat: float,
        lon: float,
        feature_id: int,
        key: str,
        attempt: int,
        zoom_index: int,
    ):
        """Schedule the next request without exceeding one request per second."""
        elapsed = time.monotonic() - self._last_geocode_request
        wait_ms = max(0, int((1.1 - elapsed) * 1000))
        QTimer.singleShot(
            wait_ms,
            lambda: self._request_reverse_geocode(
                lat, lon, feature_id, key, attempt, zoom_index
            ),
        )

    @staticmethod
    def _provider_has_no_result(payload) -> bool:
        """Return True for Nominatim's valid no-coverage responses."""
        if not isinstance(payload, dict):
            return False
        if str(payload.get("display_name", "")).strip():
            return False
        message = str(payload.get("error", "")).strip().lower()
        return message in NO_RESULT_MESSAGES or "unable to geocode" in message

    def _finish_reverse_geocode(
        self,
        reply,
        feature_id: int,
        cache_key: str,
        lat: float,
        lon: float,
        attempt: int,
        zoom_index: int,
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
                self.iface.messageBar().pushMessage(
                    "GeoClick Capture",
                    "Reverse geocoding failed temporarily; retrying once…",
                    level=INFO_LEVEL,
                    duration=4,
                )
                self._schedule_reverse_geocode(
                    lat, lon, feature_id, cache_key, attempt + 1, zoom_index
                )
                return

            if failed:
                detail = self._geocode_failure_message(
                    status, error_text, ssl_errors, response_text
                )
                QgsMessageLog.logMessage(
                    f"Reverse geocoding failed: {detail}",
                    "GeoClick Capture",
                    level=WARNING_LEVEL,
                )
                self.iface.messageBar().pushWarning(
                    "GeoClick Capture", f"Reverse geocoding failed: {detail}"
                )
                return

            payload = json.loads(response_text)
            location = str(payload.get("display_name", "")).strip()

            if not location and self._provider_has_no_result(payload):
                next_index = zoom_index + 1
                if next_index < len(ZOOM_LEVELS):
                    if zoom_index == 0:
                        self.iface.messageBar().pushMessage(
                            "GeoClick Capture",
                            "No detailed address was found; searching for a broader area…",
                            level=INFO_LEVEL,
                            duration=5,
                        )
                    self._schedule_reverse_geocode(
                        lat, lon, feature_id, cache_key, 0, next_index
                    )
                    return

                message = (
                    "No OpenStreetMap address or administrative area was found "
                    "near this coordinate. The point was saved without a place name."
                )
                QgsMessageLog.logMessage(
                    message, "GeoClick Capture", level=INFO_LEVEL
                )
                self.iface.messageBar().pushMessage(
                    "GeoClick Capture", message, level=INFO_LEVEL, duration=8
                )
                return

            if not location:
                provider_error = str(payload.get("error", "")).strip()
                self.iface.messageBar().pushWarning(
                    "GeoClick Capture",
                    provider_error or "No place name was returned for this coordinate.",
                )
                return

            self._geocode_cache[cache_key] = location
            self._apply_location(feature_id, location)
            zoom = ZOOM_LEVELS[zoom_index]
            precision = ZOOM_LABELS.get(zoom, "area")
            title = "Place identified" if zoom_index == 0 else "Approximate area identified"
            self.iface.messageBar().pushMessage(
                title,
                f"{location} ({precision} level) — © OpenStreetMap contributors",
                level=INFO_LEVEL,
                duration=8,
            )
        except (ValueError, UnicodeDecodeError, RuntimeError, TypeError) as exc:
            QgsMessageLog.logMessage(
                f"Invalid reverse-geocoding response: {exc}",
                "GeoClick Capture",
                level=WARNING_LEVEL,
            )
            self.iface.messageBar().pushWarning(
                "GeoClick Capture", f"Invalid geocoding response: {exc}"
            )
        finally:
            self._ssl_errors.pop(id(reply), None)
            if reply in self._pending_replies:
                self._pending_replies.remove(reply)
            reply.deleteLater()
