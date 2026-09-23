"""Quotable quote plugin."""

from __future__ import annotations

from .base import BasePlugin, FetchResult, PluginContext
from .formatting import render_quote, section


QUOTABLE_URL = "https://api.quotable.io/random"


class QuotablePlugin(BasePlugin):
    name = "quotable"
    display_name = "Quotable quote"

    def fetch(self, context: PluginContext) -> FetchResult:
        try:
            payload = context.fetch_json(QUOTABLE_URL, context.max_retries, context.retry_delay)
            quote = str(payload["content"]).strip()
            author = str(payload.get("author") or "Unknown").strip()
            if not quote:
                raise ValueError("Quotable returned an empty quote")
            return FetchResult(ok=True, data={"quote": quote, "author": author})
        except Exception as error:
            print(f"  ⚠ Quotable unavailable: {error}")
            return FetchResult(ok=False, error=str(error))

    def render(self, data: dict[str, str]) -> str:
        return section(
            "🗣️  QUOTABLE",
            f"{render_quote(data['quote'], data['author'])}\nSource: {QUOTABLE_URL}",
        )
