"""Open-Meteo sunrise and sunset plugin."""

from __future__ import annotations

from .base import BasePlugin, FetchResult, PluginContext
from .formatting import KeyValue, render_kv, section


SUNRISE_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude={lat}&longitude={lon}&daily=sunrise,sunset&forecast_days=1&timezone={timezone}"
)


class SunrisePlugin(BasePlugin):
    name = "sunrise"
    display_name = "Sunrise and sunset"

    def fetch(self, context: PluginContext) -> FetchResult:
        try:
            timezone = context.timezone.replace("/", "%2F")
            url = SUNRISE_URL.format(lat=context.lat, lon=context.lon, timezone=timezone)
            payload = context.fetch_json(url, context.max_retries, context.retry_delay)
            daily = payload["daily"]
            values = (
                KeyValue("Sunrise", daily["sunrise"][0]),
                KeyValue("Sunset", daily["sunset"][0]),
            )
            return FetchResult(ok=True, data=values)
        except Exception as error:
            print(f"  ⚠ Sunrise/sunset unavailable: {error}")
            return FetchResult(ok=False, error=str(error))

    def render(self, data: tuple[KeyValue, ...]) -> str:
        return section("🌅  SUNRISE / SUNSET", " | ".join(render_kv(item.label, item.value) for item in data))
