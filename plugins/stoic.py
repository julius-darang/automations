"""Stoic quote plugin."""

from __future__ import annotations

from .base import BasePlugin, FetchResult, PluginContext
from .formatting import render_quote, section


STOIC_QUOTE_URL = "https://stoic-quotes.com/api/quote"


class StoicPlugin(BasePlugin):
    name = "stoic"
    display_name = "Stoic quote"

    def fetch(self, context: PluginContext) -> FetchResult:
        try:
            payload = context.fetch_json(STOIC_QUOTE_URL, context.max_retries, context.retry_delay)
            quote = str(payload["text"]).strip()
            author = str(payload.get("author") or "Unknown").strip()
            if not quote:
                raise ValueError("Stoic Quotes returned an empty quote")
            return FetchResult(ok=True, data={"quote": quote, "author": author})
        except Exception as error:
            print(f"  ⚠ Stoic quote unavailable: {error}")
            return FetchResult(ok=False, error=str(error))

    def render(self, data: dict[str, str]) -> str:
        return section(
            "🏛️  STOIC QUOTE",
            f"{render_quote(data['quote'], data['author'])}\nSource: {STOIC_QUOTE_URL}",
        )
