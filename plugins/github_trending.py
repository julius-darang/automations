"""GitHub Trending repositories plugin."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import quote

from .base import BasePlugin, FetchResult, PluginContext
from .formatting import RankedItem, render_ranked_list, section


GITHUB_TRENDING_URL = "https://github.com/trending"
GITHUB_TRENDING_LIMIT = 5
GITHUB_TRENDING_SINCE = "daily"


class _TrendingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.current: dict[str, str] | None = None
        self.items: list[dict[str, str]] = []
        self.capture: str | None = None
        self.buffer: list[str] = []
        self.in_heading = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "article":
            self.current = {}
        if self.current is None:
            return
        classes = (attributes.get("class") or "").split()
        href = attributes.get("href") or ""
        if tag == "h2":
            self.in_heading = True
        elif tag == "a" and self.in_heading and re.fullmatch(r"/[^/]+/[^/]+", href):
            self.current["link"] = f"https://github.com{href}"
            self.capture = "title"
            self.buffer = []
        elif tag == "p" and "col-9" in classes and "description" not in self.current:
            self.capture = "description"
            self.buffer = []
        elif tag == "span" and attributes.get("itemprop") == "programmingLanguage":
            self.capture = "language"
            self.buffer = []
        elif tag == "span" and "stars today" in (attributes.get("class") or ""):
            self.capture = "stars_today"
            self.buffer = []

    def handle_data(self, data: str) -> None:
        cleaned = " ".join(data.split())
        if cleaned and "stars today" in cleaned and self.current is not None:
            self.current["stars_today"] = cleaned
        if self.capture is not None:
            self.buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.capture is not None and tag in {"a", "p", "span"}:
            value = " ".join("".join(self.buffer).split())
            if self.current is not None and value:
                self.current[self.capture] = value
            self.capture = None
            self.buffer = []
        if tag == "h2":
            self.in_heading = False
        if tag == "article" and self.current:
            if self.current.get("link"):
                self.items.append(self.current)
            self.current = None


class GitHubTrendingPlugin(BasePlugin):
    name = "github_trending"
    display_name = "GitHub Trending"

    def fetch(self, context: PluginContext) -> FetchResult:
        try:
            since = str(context.setting("GITHUB_TRENDING_SINCE", GITHUB_TRENDING_SINCE)).strip().casefold()
            if since not in {"daily", "weekly", "monthly"}:
                raise ValueError("GITHUB_TRENDING_SINCE must be daily, weekly, or monthly")
            language = str(context.setting("GITHUB_TRENDING_LANGUAGE", "")).strip()
            url = f"{GITHUB_TRENDING_URL}/{quote(language, safe='+#.-')}" if language else GITHUB_TRENDING_URL
            url = f"{url}?since={since}&spoken_language_code=en"
            html_text = context.fetch_text(url, context.max_retries, context.retry_delay)
            parser = _TrendingParser()
            parser.feed(html_text)
            limit = int(context.setting("GITHUB_TRENDING_LIMIT", GITHUB_TRENDING_LIMIT))
            if not 1 <= limit <= 25:
                raise ValueError("GITHUB_TRENDING_LIMIT must be between 1 and 25")
            items: list[RankedItem] = []
            for repository in parser.items[:limit]:
                details: list[str] = []
                if repository.get("description"):
                    details.append(repository["description"])
                if repository.get("language"):
                    details.append(f"Language: {repository['language']}")
                if repository.get("stars_today"):
                    details.append(repository["stars_today"])
                title = repository["link"].removeprefix("https://github.com/")
                items.append(RankedItem(title=title, link=repository["link"], details=tuple(details)))
            if not items:
                return FetchResult(ok=False, error="GitHub Trending returned no repositories")
            return FetchResult(ok=True, data=items)
        except Exception as error:
            print(f"  ⚠ GitHub Trending unavailable: {error}")
            return FetchResult(ok=False, error=str(error))

    def render(self, data: list[RankedItem]) -> str:
        return section("🐙  GITHUB TRENDING", render_ranked_list(data, max_results=GITHUB_TRENDING_LIMIT))
