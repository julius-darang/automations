"""BBC RSS headlines plugin."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from .base import BasePlugin, FetchResult, PluginContext
from .formatting import RankedItem, render_ranked_list, section


class HeadlinesPlugin(BasePlugin):
    name = "headlines"
    display_name = "Headlines"

    def fetch(self, context: PluginContext) -> FetchResult:
        try:
            xml_text = context.fetch_text(
                "https://feeds.bbci.co.uk/news/rss.xml",
                context.max_retries,
                context.retry_delay,
            )
            root = ET.fromstring(xml_text)
            items: list[RankedItem] = []
            for item in root.findall(".//item"):
                title = " ".join((item.findtext("title") or "").split())
                link = (item.findtext("link") or "").strip()
                if not title:
                    continue
                source_element = item.find("source")
                source = " ".join((source_element.text or "").split()) if source_element is not None else ""
                details = (f"Source: {source}",) if source else ()
                items.append(RankedItem(title=title, link=link, details=details))
                if len(items) == 3:
                    break
            if not items:
                return FetchResult(ok=False, error="feed returned no headlines")
            return FetchResult(ok=True, data=items)
        except Exception as error:
            print(f"  ⚠ Headlines unavailable: {error}")
            return FetchResult(ok=False, error=str(error))

    def render(self, data: list[RankedItem]) -> str:
        return section("📰  HEADLINES", render_ranked_list(data, max_results=3))
