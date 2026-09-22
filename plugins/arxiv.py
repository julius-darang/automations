"""Recent arXiv AI papers plugin."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from .base import BasePlugin, FetchResult, PluginContext
from .formatting import RankedItem, render_ranked_list, section


ARXIV_QUERY_URL = (
    "https://export.arxiv.org/api/query?search_query=cat:cs.AI"
    "&start=0&max_results=5&sortBy=submittedDate&sortOrder=descending"
)
ARXIV_NAMESPACE = {"atom": "http://www.w3.org/2005/Atom"}
ARXIV_LIMIT = 5
ABSTRACT_LIMIT = 180


class ArxivPlugin(BasePlugin):
    name = "arxiv"
    display_name = "arXiv AI papers"

    def fetch(self, context: PluginContext) -> FetchResult:
        try:
            xml_text = context.fetch_text(
                ARXIV_QUERY_URL,
                context.max_retries,
                context.retry_delay,
            )
            root = ET.fromstring(xml_text)
            items: list[RankedItem] = []
            for entry in root.findall("atom:entry", ARXIV_NAMESPACE):
                title = " ".join((entry.findtext("atom:title", default="", namespaces=ARXIV_NAMESPACE)).split())
                link = (entry.findtext("atom:id", default="", namespaces=ARXIV_NAMESPACE)).strip()
                if not title or not link:
                    continue
                authors = [
                    " ".join((author.findtext("atom:name", default="", namespaces=ARXIV_NAMESPACE)).split())
                    for author in entry.findall("atom:author", ARXIV_NAMESPACE)
                ]
                summary = " ".join((entry.findtext("atom:summary", default="", namespaces=ARXIV_NAMESPACE)).split())
                details: list[str] = []
                if authors:
                    details.append(f"Authors: {', '.join(authors[:3])}")
                if summary:
                    snippet = summary[:ABSTRACT_LIMIT].rstrip()
                    details.append(f"Abstract: {snippet}{'…' if len(summary) > ABSTRACT_LIMIT else ''}")
                items.append(RankedItem(title=title, link=link, details=tuple(details)))
                if len(items) == ARXIV_LIMIT:
                    break
            if not items:
                return FetchResult(ok=False, error="arXiv returned no papers")
            return FetchResult(ok=True, data=items)
        except Exception as error:
            print(f"  ⚠ arXiv unavailable: {error}")
            return FetchResult(ok=False, error=str(error))

    def render(self, data: list[RankedItem]) -> str:
        return section("📚  ARXIV AI PAPERS", render_ranked_list(data, max_results=ARXIV_LIMIT))
