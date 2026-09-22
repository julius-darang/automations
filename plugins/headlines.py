"""BBC RSS headlines plugin."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from .base import BasePlugin, FetchResult, PluginContext
from .formatting import section


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
            items = root.findall(".//item")[:3]
            if not items:
                return FetchResult(ok=False, error="feed returned no headlines")

            lines: list[str] = []
            for item in items:
                title = item.findtext("title", "")
                lines.append(f"  • {title}")
                link = (item.findtext("link") or "").strip()
                if link:
                    lines.append(f"    {link}")
            return FetchResult(ok=True, data="\n" + "\n".join(lines))
        except Exception as error:
            print(f"  ⚠ Headlines unavailable: {error}")
            return FetchResult(ok=False, error=str(error))

    def render(self, data: str) -> str:
        return section("📰  HEADLINES", data)
