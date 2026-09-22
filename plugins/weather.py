"""Open-Meteo weather plugin."""

from __future__ import annotations

from .base import BasePlugin, FetchResult, PluginContext
from .formatting import KeyValue, render_kv, section


WEATHER_MAP = {
    0: "Clear sky ☀️", 1: "Mainly clear 🌤️", 2: "Partly cloudy ⛅",
    3: "Overcast ☁️", 45: "Foggy 🌫️", 48: "Foggy 🌫️",
    51: "Light drizzle 🌦️", 53: "Drizzle 🌦️", 55: "Heavy drizzle 🌧️",
    61: "Light rain 🌧️", 63: "Rain 🌧️", 65: "Heavy rain 🌧️",
    80: "Rain showers 🌦️", 81: "Rain showers 🌦️", 82: "Heavy showers ⛈️",
    95: "Thunderstorm ⛈️", 96: "Thunderstorm ⛈️", 99: "Thunderstorm ⛈️",
}


class WeatherPlugin(BasePlugin):
    name = "weather"
    display_name = "Weather"

    def fetch(self, context: PluginContext) -> FetchResult:
        try:
            url = (
                "https://api.open-meteo.com/v1/forecast"
                f"?latitude={context.lat}&longitude={context.lon}"
                "&current=temperature_2m,weathercode,windspeed_10m,relative_humidity_2m"
                f"&timezone={context.timezone.replace('/', '%2F')}"
            )
            payload = context.fetch_json(url, context.max_retries, context.retry_delay)
            current = payload["current"]
            code = current["weathercode"]
            data = {
                "city": context.city,
                "condition": WEATHER_MAP.get(code, "Unknown"),
                "values": (
                    KeyValue("", current["temperature_2m"], "°C"),
                    KeyValue("Humidity", current["relative_humidity_2m"], "%"),
                    KeyValue("Wind", current["windspeed_10m"], " km/h"),
                ),
            }
            return FetchResult(ok=True, data=data)
        except Exception as error:
            print(f"  ⚠ Weather unavailable: {error}")
            return FetchResult(ok=False, error=str(error))

    def render(self, data: dict) -> str:
        values = " | ".join(render_kv(item.label, item.value, item.unit) for item in data["values"])
        return section(f"🌤  WEATHER — {data['city']}", f"{data['condition']} | {values}")
