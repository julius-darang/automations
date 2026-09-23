"""Nager.Date public holiday plugin."""

from __future__ import annotations

from datetime import datetime

from .base import BasePlugin, FetchResult, PluginContext
from .formatting import KeyValue, render_kv, section


HOLIDAY_URL = "https://date.nager.at/api/v3/PublicHolidays/{year}/{country}"


class PublicHolidayPlugin(BasePlugin):
    name = "public_holiday"
    display_name = "Public holiday"

    def fetch(self, context: PluginContext) -> FetchResult:
        try:
            now = context.now or datetime.now()
            country = str(context.setting("HOLIDAY_COUNTRY", "PH")).upper()
            payload = context.fetch_json(
                HOLIDAY_URL.format(year=now.year, country=country),
                context.max_retries,
                context.retry_delay,
            )
            today = now.date().isoformat()
            holiday = next((item for item in payload if item.get("date") == today), None)
            value = "None" if holiday is None else str(holiday.get("localName") or holiday.get("name"))
            return FetchResult(ok=True, data=KeyValue("Today", value))
        except Exception as error:
            print(f"  ⚠ Public holiday unavailable: {error}")
            return FetchResult(ok=False, error=str(error))

    def render(self, data: KeyValue) -> str:
        return section("🎉  PUBLIC HOLIDAY", render_kv(data.label, data.value))
