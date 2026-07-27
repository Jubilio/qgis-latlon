"""Nominatim policy guard for GeoClick Capture 1.3.0."""

from __future__ import annotations

import time
from typing import Dict

from .dock_widget_v130 import CaptureLogDockV130
from .plugin_v130 import GeoClickCapturePluginV130
from .search_utils import parse_map_url


class GeoClickCapturePluginV130Policy(GeoClickCapturePluginV130):
    """Share one Nominatim rate limit and reject opaque map short-links."""

    def search_place(self, options: Dict[str, object]):
        raw = str(options.get("query", "")).strip()
        if raw.lower().startswith(("http://", "https://")) and parse_map_url(raw) is None:
            if isinstance(self.dock, CaptureLogDockV130):
                self.dock.set_search_message(
                    "This URL does not expose coordinates. Open the full map link and "
                    "copy a URL containing latitude and longitude."
                )
            return

        self._last_search_request = max(
            self._last_search_request, self._last_geocode_request
        )
        super().search_place(options)

    def _request_place_search(
        self,
        query: str,
        countrycodes: str,
        viewbox: str,
        cache_key: str,
        attempt: int,
    ):
        self._last_geocode_request = time.monotonic()
        super()._request_place_search(
            query, countrycodes, viewbox, cache_key, attempt
        )
