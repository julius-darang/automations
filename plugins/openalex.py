"""OpenAlex research papers plugin."""

from __future__ import annotations

from .base import BasePlugin, FetchResult, PluginContext
from .formatting import RankedItem, render_ranked_list, section


OPENALEX_WORKS_URL = (
    "https://api.openalex.org/works?search=artificial%20intelligence"
    "&sort=cited_by_count:desc&per-page=5"
)
OPENALEX_LIMIT = 5


class OpenAlexPlugin(BasePlugin):
    name = "openalex"
    display_name = "OpenAlex papers"

    def fetch(self, context: PluginContext) -> FetchResult:
        try:
            payload = context.fetch_json(
                OPENALEX_WORKS_URL,
                context.max_retries,
                context.retry_delay,
            )
            results = payload.get("results", []) if isinstance(payload, dict) else []
            items: list[RankedItem] = []
            for work in results[:OPENALEX_LIMIT]:
                if not isinstance(work, dict):
                    continue
                title = " ".join(str(work.get("title", "")).split())
                location = work.get("primary_location") or {}
                link = str(work.get("doi") or location.get("landing_page_url") or work.get("id") or "").strip()
                if not title or not link:
                    continue
                authors = [
                    str(author.get("author", {}).get("display_name", ""))
                    for author in work.get("authorships", [])[:3]
                    if author.get("author", {}).get("display_name")
                ]
                details = []
                if authors:
                    details.append(f"Authors: {', '.join(authors)}")
                if work.get("cited_by_count") is not None:
                    details.append(f"Citations: {work['cited_by_count']}")
                items.append(RankedItem(title=title, link=link, details=tuple(details)))
            if not items:
                return FetchResult(ok=False, error="OpenAlex returned no papers")
            return FetchResult(ok=True, data=items)
        except Exception as error:
            print(f"  ⚠ OpenAlex unavailable: {error}")
            return FetchResult(ok=False, error=str(error))

    def render(self, data: list[RankedItem]) -> str:
        return section("🔬  OPENALEX PAPERS", render_ranked_list(data, max_results=OPENALEX_LIMIT))
