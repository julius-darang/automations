"""Reddit technology/programming RSS plugin."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from .base import BasePlugin, FetchResult, PluginContext
from .formatting import RankedItem, render_ranked_list, section


REDDIT_RSS_URL = "https://www.reddit.com/r/{subreddits}/.rss?limit=10"
REDDIT_NAMESPACE = {"atom": "http://www.w3.org/2005/Atom"}
REDDIT_LIMIT = 5
DEFAULT_SUBREDDITS = "technology,programming"


class RedditPlugin(BasePlugin):
    name = "reddit"
    display_name = "Reddit tech"

    def fetch(self, context: PluginContext) -> FetchResult:
        try:
            configured = str(context.setting("REDDIT_SUBREDDITS", DEFAULT_SUBREDDITS))
            subreddits = [
                item.strip().strip("/")
                for item in configured.split(",")
                if re.fullmatch(r"[A-Za-z0-9_+-]+", item.strip().strip("/"))
            ]
            if not subreddits:
                raise ValueError("REDDIT_SUBREDDITS contained no valid subreddits")
            url = REDDIT_RSS_URL.format(subreddits="+".join(subreddits))
            xml_text = context.fetch_text(url, context.max_retries, context.retry_delay)
            root = ET.fromstring(xml_text)
            items: list[RankedItem] = []
            for entry in root.findall("atom:entry", REDDIT_NAMESPACE):
                title = " ".join((entry.findtext("atom:title", default="", namespaces=REDDIT_NAMESPACE)).split())
                link_element = entry.find("atom:link", REDDIT_NAMESPACE)
                link = str(link_element.get("href", "")).strip() if link_element is not None else ""
                if not title or not link:
                    continue
                items.append(RankedItem(title=title, link=link, details=("Source: Reddit",)))
                if len(items) == REDDIT_LIMIT:
                    break
            if not items:
                return FetchResult(ok=False, error="Reddit returned no stories")
            return FetchResult(ok=True, data=items)
        except Exception as error:
            print(f"  ⚠ Reddit unavailable: {error}")
            return FetchResult(ok=False, error=str(error))

    def render(self, data: list[RankedItem]) -> str:
        return section("🔵  REDDIT TECH", render_ranked_list(data, max_results=REDDIT_LIMIT))
