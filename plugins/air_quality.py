"""Open-Meteo air quality plugin."""

from __future__ import annotations

from .base import BasePlugin, FetchResult, PluginContext
from .formatting import KeyValue, render_kv, section


AIR_QUALITY_URL = (
    "https://air-quality-api.open-meteo.com/v1/air-quality"
    "?latitude={lat}&longitude={lon}&current=us_aqi,pm2_5&timezone={timezone}"
)


class AirQualityPlugin(BasePlugin):
    name = "air_quality"
    display_name = "Air quality"

    def fetch(self, context: PluginContext) -> FetchResult:
        try:
            timezone = context.timezone.replace("/", "%2F")
            url = AIR_QUALITY_URL.format(lat=context.lat, lon=context.lon, timezone=timezone)
            payload = context.fetch_json(url, context.max_retries, context.retry_delay)
            current = payload["current"]
            values = (
                KeyValue("US AQI", current["us_aqi"]),
                KeyValue("PM2.5", current["pm2_5"], " μg/m³"),
            )
            return FetchResult(ok=True, data=values)
        except Exception as error:
            print(f"  ⚠ Air quality unavailable: {error}")
            return FetchResult(ok=False, error=str(error))

    def render(self, data: tuple[KeyValue, ...]) -> str:
        return section("🌫️  AIR QUALITY", " | ".join(render_kv(item.label, item.value, item.unit) for item in data))
