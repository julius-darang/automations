"""Hacker News top stories plugin."""

from __future__ import annotations

from .base import BasePlugin, FetchResult, PluginContext
from .formatting import RankedItem, render_ranked_list, section


HN_TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
HN_LIMIT = 5
HN_SCAN_LIMIT = 15


class HackerNewsPlugin(BasePlugin):
    name = "hackernews"
    display_name = "Hacker News"

    def fetch(self, context: PluginContext) -> FetchResult:
        try:
            story_ids = context.fetch_json(
                HN_TOP_STORIES_URL,
                context.max_retries,
                context.retry_delay,
            )
            if not isinstance(story_ids, list):
                raise ValueError("top stories response was not a list")

            items: list[RankedItem] = []
            failed = 0
            for story_id in story_ids[:HN_SCAN_LIMIT]:
                try:
                    story = context.fetch_json(
                        HN_ITEM_URL.format(story_id=story_id),
                        context.max_retries,
                        context.retry_delay,
                    )
                    if not isinstance(story, dict) or story.get("type") != "story":
                        continue
                    title = " ".join(str(story.get("title", "")).split())
                    if not title:
                        continue
                    link = str(story.get("url") or f"https://news.ycombinator.com/item?id={story_id}")
                    score = story.get("score")
                    details = (f"Score: {score}",) if score is not None else ()
                    items.append(RankedItem(title=title, link=link, details=details))
                    if len(items) == HN_LIMIT:
                        break
                except Exception:
                    failed += 1

            if not items:
                return FetchResult(ok=False, error="no Hacker News stories returned")
            missing = ("Hacker News: some stories",) if failed else ()
            return FetchResult(ok=True, data=items, missing=missing)
        except Exception as error:
            print(f"  ⚠ Hacker News unavailable: {error}")
            return FetchResult(ok=False, error=str(error))

    def render(self, data: list[RankedItem]) -> str:
        return section("🟠  HACKER NEWS", render_ranked_list(data, max_results=HN_LIMIT))
