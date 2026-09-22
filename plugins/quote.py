"""ZenQuotes daily quote plugin."""

from __future__ import annotations

from .base import BasePlugin, FetchResult, PluginContext
from .formatting import render_quote, section


class QuotePlugin(BasePlugin):
    name = "quote"
    display_name = "Quote"

    def fetch(self, context: PluginContext) -> FetchResult:
        try:
            payload = context.fetch_json(
                "https://zenquotes.io/api/random",
                context.max_retries,
                context.retry_delay,
            )
            record = payload[0]
            return FetchResult(ok=True, data={"quote": record["q"], "author": record["a"]})
        except Exception as error:
            print(f"  ⚠ Quote unavailable: {error}")
            return FetchResult(ok=False, error=str(error))

    def render(self, data: dict) -> str:
        body = render_quote(data["quote"], data["author"])
        return section("💬  QUOTE OF THE DAY", f"{body}\nSource: https://zenquotes.io/")
