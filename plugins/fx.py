"""Frankfurter exchange-rate plugin."""

from __future__ import annotations

from .base import BasePlugin, FetchResult, PluginContext
from .formatting import KeyValue, render_kv, section


FX_URL = "https://api.frankfurter.app/latest?from={base}&to={quote}"


class FXPlugin(BasePlugin):
    name = "fx"
    display_name = "FX rate"

    def fetch(self, context: PluginContext) -> FetchResult:
        try:
            base = str(context.setting("FX_BASE", "USD")).upper()
            quote = str(context.setting("FX_QUOTE", "PHP")).upper()
            payload = context.fetch_json(
                FX_URL.format(base=base, quote=quote),
                context.max_retries,
                context.retry_delay,
            )
            value = payload["rates"][quote]
            return FetchResult(ok=True, data=KeyValue(f"{base}/{quote}", value))
        except Exception as error:
            print(f"  ⚠ FX rate unavailable: {error}")
            return FetchResult(ok=False, error=str(error))

    def render(self, data: KeyValue) -> str:
        return section("💱  FX RATE", render_kv(data.label, data.value))
