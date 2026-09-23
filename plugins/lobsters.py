"""Lobsters RSS ranked stories plugin."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from .base import BasePlugin, FetchResult, PluginContext
from .formatting import RankedItem, render_ranked_list, section


LOBSTERS_FEED_URL = "https://lobste.rs/rss"
LOBSTERS_LIMIT = 5


class LobstersPlugin(BasePlugin):
    name = "lobsters"
    display_name = "Lobsters"

    def fetch(self, context: PluginContext) -> FetchResult:
        try:
            xml_text = context.fetch_text(
                LOBSTERS_FEED_URL,
                context.max_retries,
                context.retry_delay,
            )
            root = ET.fromstring(xml_text)
            items: list[RankedItem] = []
            for item in root.findall(".//item"):
                title = " ".join((item.findtext("title") or "").split())
                link = (item.findtext("link") or "").strip()
                if title and link:
                    items.append(RankedItem(title=title, link=link))
                if len(items) == LOBSTERS_LIMIT:
                    break
            if not items:
                return FetchResult(ok=False, error="feed returned no Lobsters stories")
            return FetchResult(ok=True, data=items)
        except Exception as error:
            print(f"  ⚠ Lobsters unavailable: {error}")
            return FetchResult(ok=False, error=str(error))

    def render(self, data: list[RankedItem]) -> str:
        return section("🔴  LOBSTERS", render_ranked_list(data, max_results=LOBSTERS_LIMIT))
