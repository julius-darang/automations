"""Semantic Scholar research-paper search plugin."""

from __future__ import annotations

from urllib.parse import urlencode

from .base import BasePlugin, FetchResult, PluginContext
from .formatting import RankedItem, render_ranked_list, section


SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
SEMANTIC_SCHOLAR_QUERY = "artificial intelligence"
SEMANTIC_SCHOLAR_LIMIT = 5
SEMANTIC_SCHOLAR_FIELDS = "title,url,year,authors,citationCount,paperId"


class SemanticScholarPlugin(BasePlugin):
    name = "semantic_scholar"
    display_name = "Semantic Scholar"

    def fetch(self, context: PluginContext) -> FetchResult:
        try:
            query = str(context.setting("SEMANTIC_SCHOLAR_QUERY", SEMANTIC_SCHOLAR_QUERY)).strip()
            if not query:
                raise ValueError("SEMANTIC_SCHOLAR_QUERY cannot be empty")
            limit = int(context.setting("SEMANTIC_SCHOLAR_LIMIT", SEMANTIC_SCHOLAR_LIMIT))
            if not 1 <= limit <= 100:
                raise ValueError("SEMANTIC_SCHOLAR_LIMIT must be between 1 and 100")
            url = f"{SEMANTIC_SCHOLAR_URL}?{urlencode({'query': query, 'limit': limit, 'fields': SEMANTIC_SCHOLAR_FIELDS})}"
            api_key = context.secret("SEMANTIC_SCHOLAR_API_KEY")
            if api_key:
                payload = context.fetch_json(
                    url,
                    context.max_retries,
                    context.retry_delay,
                    {"x-api-key": api_key},
                )
            else:
                payload = context.fetch_json(url, context.max_retries, context.retry_delay)
            papers = payload.get("data", []) if isinstance(payload, dict) else []
            items: list[RankedItem] = []
            for paper in papers:
                if not isinstance(paper, dict):
                    continue
                title = str(paper.get("title") or "").strip()
                paper_id = str(paper.get("paperId") or "").strip()
                link = str(paper.get("url") or "").strip()
                if not link and paper_id:
                    link = f"https://www.semanticscholar.org/paper/{paper_id}"
                if not title or not link:
                    continue
                details: list[str] = []
                authors = paper.get("authors") or []
                author_names = [
                    str(author.get("name") or "").strip()
                    for author in authors[:3]
                    if isinstance(author, dict) and author.get("name")
                ]
                if author_names:
                    details.append(f"Authors: {', '.join(author_names)}")
                if paper.get("year"):
                    details.append(f"Year: {paper['year']}")
                if paper.get("citationCount") is not None:
                    details.append(f"Citations: {paper['citationCount']}")
                items.append(RankedItem(title=title, link=link, details=tuple(details)))
            if not items:
                return FetchResult(ok=False, error="Semantic Scholar returned no papers")
            return FetchResult(ok=True, data=items)
        except Exception as error:
            print(f"  ⚠ Semantic Scholar unavailable: {error}")
            return FetchResult(ok=False, error=str(error))

    def render(self, data: list[RankedItem]) -> str:
        return section("🧪  SEMANTIC SCHOLAR", render_ranked_list(data, max_results=SEMANTIC_SCHOLAR_LIMIT))
