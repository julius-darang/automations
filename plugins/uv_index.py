"""Open-Meteo current UV index plugin."""

from __future__ import annotations

from .base import BasePlugin, FetchResult, PluginContext
from .formatting import KeyValue, render_kv, section


UV_INDEX_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude={lat}&longitude={lon}&current=uv_index&timezone={timezone}"
)


class UVIndexPlugin(BasePlugin):
    name = "uv_index"
    display_name = "UV index"

    def fetch(self, context: PluginContext) -> FetchResult:
        try:
            timezone = context.timezone.replace("/", "%2F")
            url = UV_INDEX_URL.format(lat=context.lat, lon=context.lon, timezone=timezone)
            payload = context.fetch_json(url, context.max_retries, context.retry_delay)
            value = payload["current"]["uv_index"]
            return FetchResult(ok=True, data=KeyValue("UV index", value))
        except Exception as error:
            print(f"  ⚠ UV index unavailable: {error}")
            return FetchResult(ok=False, error=str(error))

    def render(self, data: KeyValue) -> str:
        return section("☀️  UV INDEX", render_kv(data.label, data.value))
