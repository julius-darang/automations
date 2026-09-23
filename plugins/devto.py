"""Dev.to popular articles plugin."""

from __future__ import annotations

from .base import BasePlugin, FetchResult, PluginContext
from .formatting import RankedItem, render_ranked_list, section


DEVTO_ARTICLES_URL = "https://dev.to/api/articles?top=1&per_page=5"
DEVTO_LIMIT = 5


class DevToPlugin(BasePlugin):
    name = "devto"
    display_name = "Dev.to"

    def fetch(self, context: PluginContext) -> FetchResult:
        try:
            payload = context.fetch_json(
                DEVTO_ARTICLES_URL,
                context.max_retries,
                context.retry_delay,
            )
            if not isinstance(payload, list):
                raise ValueError("Dev.to response was not a list")
            items: list[RankedItem] = []
            for article in payload[:DEVTO_LIMIT]:
                if not isinstance(article, dict):
                    continue
                title = " ".join(str(article.get("title", "")).split())
                link = str(article.get("url", "")).strip()
                if not title or not link:
                    continue
                tags = [str(tag) for tag in article.get("tag_list", []) if tag]
                details = (f"Tags: {', '.join(tags)}",) if tags else ()
                items.append(RankedItem(title=title, link=link, details=details))
            if not items:
                return FetchResult(ok=False, error="Dev.to returned no articles")
            return FetchResult(ok=True, data=items)
        except Exception as error:
            print(f"  ⚠ Dev.to unavailable: {error}")
            return FetchResult(ok=False, error=str(error))

    def render(self, data: list[RankedItem]) -> str:
        return section("🟣  DEV.TO", render_ranked_list(data, max_results=DEVTO_LIMIT))
