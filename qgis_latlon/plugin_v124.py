"""Robust reverse geocoding for GeoClick Capture 1.2.4."""

from __future__ import annotations

import json
import time
from typing import Dict, List
from urllib.parse import urlencode

from qgis.PyQt.QtCore import QLocale, QTimer, QUrl
from qgis.PyQt.QtNetwork import QNetworkReply, QNetworkRequest
from qgis.core import Qgis, QgsMessageLog, QgsNetworkAccessManager

from .plugin_v121 import GeoClickCapturePlugin


def _compat_enum(container, scoped_container_name: str, member_name: str, legacy_name: str):
    """Return a scoped Qt enum with a Qt 5 fallback."""
    scoped_container = getattr(container, scoped_container_name, None)
    if scoped_container is not None:
        return getattr(scoped_container, member_name)
    return getattr(container, legacy_name)


WARNING_LEVEL = _compat_enum(Qgis, "MessageLevel", "Warning", "Warning")
INFO_LEVEL = _compat_enum(Qgis, "MessageLevel", "Info", "Info")
HTTP_STATUS_ATTRIBUTE = _compat_enum(
    QNetworkRequest, "Attribute", "HttpStatusCodeAttribute", "HttpStatusCodeAttribute"
)
REDIRECT_POLICY_ATTRIBUTE = _compat_enum(
    QNetworkRequest, "Attribute", "RedirectPolicyAttribute", "RedirectPolicyAttribute"
)
NO_LESS_SAFE_REDIRECT_POLICY = _compat_enum(
    QNetworkRequest,
    "RedirectPolicy",
    "NoLessSafeRedirectPolicy",
    "NoLessSafeRedirectPolicy",
)
USER_AGENT_HEADER = _compat_enum(
    QNetworkRequest, "KnownHeaders", "UserAgentHeader", "UserAgentHeader"
)
NETWORK_NO_ERROR = _compat_enum(
    QNetworkReply, "NetworkError", "NoError", "NoError"
)


class GeoClickCapturePluginV124(GeoClickCapturePlugin):
    """GeoClick Capture runtime with diagnostic reverse geocoding."""

    def __init__(self, iface):
        super().__init__(iface)
        self._ssl_errors: Dict[int, List[str]] = {}

    def unload(self):
        self._ssl_errors.clear()
        super().unload()

    def _request_reverse_geocode(
        self,
        lat: float,
        lon: float,
        feature_id: int,
        key: str,
        attempt: int = 0,
    ):
        """Request an address through QGIS networking with one safe retry."""
        self._last_geocode_request = time.monotonic()
        language = (QLocale.system().name() or "en").split("_", 1)[0]
        parameters = urlencode(
            {
                "lat": f"{lat:.8f}",
                "lon": f"{lon:.8f}",
                "format": "jsonv2",
                "zoom": 18,
                "addressdetails": 0,
                "accept-language": language,
            }
        )
        request = QNetworkRequest(
            QUrl(f"https://nominatim.openstreetmap.org/reverse?{parameters}")
        )
        request.setHeader(
            USER_AGENT_HEADER,
            "GeoClick-Capture/1.2.4 "
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
            longitude=lon, retry_attempt=attempt: self._finish_reverse_geocode(
                r,
                fid,
                cache_key,
                latitude,
                longitude,
                retry_attempt,
            )
        )

    def _record_ssl_errors(self, reply, errors):
        """Store SSL diagnostics without bypassing certificate validation."""
        self._ssl_errors[id(reply)] = [
            str(error.errorString()) for error in errors
        ]

    @staticmethod
    def _http_status(reply) -> int:
        value = reply.attribute(HTTP_STATUS_ATTRIBUTE)
        try:
            return int(value) if value is not None else 0
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _short_response(text: str, limit: int = 180) -> str:
        cleaned = " ".join((text or "").split())
        return cleaned[:limit] + ("…" if len(cleaned) > limit else "")

    def _geocode_failure_message(
        self,
        status: int,
        error_text: str,
        ssl_errors: List[str],
        response_text: str,
    ) -> str:
        if ssl_errors:
            return "SSL/TLS error: " + "; ".join(ssl_errors[:2])
        if status == 403:
            return "The geocoding service rejected the request (HTTP 403)."
        if status == 429:
            return "The geocoding service rate limit was reached (HTTP 429)."
        if status:
            detail = self._short_response(response_text)
            return f"HTTP {status}: {detail or error_text or 'request failed'}"
        return error_text or "network connection failed"

    def _finish_reverse_geocode(
        self,
        reply,
        feature_id: int,
        cache_key: str,
        lat: float,
        lon: float,
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
                self.iface.messageBar().pushMessage(
                    "GeoClick Capture",
                    "Reverse geocoding failed temporarily; retrying once…",
                    level=INFO_LEVEL,
                    duration=4,
                )
                QTimer.singleShot(
                    2000,
                    lambda: self._request_reverse_geocode(
                        lat, lon, feature_id, cache_key, attempt + 1
                    ),
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
            if not location:
                provider_error = str(payload.get("error", "")).strip()
                self.iface.messageBar().pushWarning(
                    "GeoClick Capture",
                    provider_error or "No address was found for this coordinate.",
                )
                return

            self._geocode_cache[cache_key] = location
            self._apply_location(feature_id, location)
            self.iface.messageBar().pushMessage(
                "Place identified",
                f"{location} — © OpenStreetMap contributors",
                level=INFO_LEVEL,
                duration=7,
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
