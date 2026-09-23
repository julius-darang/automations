"""Papers With Code paper/repository list plugin."""

from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import urljoin

from .base import BasePlugin, FetchResult, PluginContext
from .formatting import RankedItem, render_ranked_list, section


PWC_URL = "https://paperswithcode.com/"
PWC_LIMIT = 5
PWC_BASE_URL = "https://paperswithcode.com"


class _PapersParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.current: dict[str, str] | None = None
        self.items: list[dict[str, str]] = []
        self.capture: str | None = None
        self.buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "article":
            self.current = {}
        if self.current is None:
            return
        href = attributes.get("href") or ""
        classes = (attributes.get("class") or "").split()
        if tag == "a" and href.startswith("/papers/"):
            self.capture = "title"
            self.buffer = []
            self.current["link"] = urljoin(PWC_BASE_URL, href)
        elif tag == "a" and href.startswith("https://github.com/"):
            self.current["repo"] = href
        elif tag == "p" and "line-clamp-2" in classes and "description" not in self.current:
            self.capture = "description"
            self.buffer = []

    def handle_data(self, data: str) -> None:
        if self.capture is not None:
            self.buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.capture is not None and tag in {"a", "p"}:
            value = " ".join("".join(self.buffer).split())
            if self.current is not None and value:
                self.current[self.capture] = value
            self.capture = None
            self.buffer = []
        if tag == "article" and self.current:
            if self.current.get("title") and self.current.get("link"):
                self.items.append(self.current)
            self.current = None


class PapersWithCodePlugin(BasePlugin):
    name = "papers_with_code"
    display_name = "Papers With Code"

    def fetch(self, context: PluginContext) -> FetchResult:
        try:
            html_text = context.fetch_text(PWC_URL, context.max_retries, context.retry_delay)
            parser = _PapersParser()
            parser.feed(html_text)
            items: list[RankedItem] = []
            for paper in parser.items[:PWC_LIMIT]:
                details: list[str] = []
                if paper.get("repo"):
                    details.append(f"Repo: {paper['repo']}")
                if paper.get("description"):
                    details.append(f"Abstract: {paper['description']}")
                items.append(RankedItem(paper["title"], paper["link"], tuple(details)))
            if not items:
                return FetchResult(ok=False, error="Papers With Code returned no papers")
            return FetchResult(ok=True, data=items)
        except Exception as error:
            print(f"  ⚠ Papers With Code unavailable: {error}")
            return FetchResult(ok=False, error=str(error))

    def render(self, data: list[RankedItem]) -> str:
        return section("📄  PAPERS WITH CODE", render_ranked_list(data, max_results=PWC_LIMIT))
