"""Merriam-Webster Word of the Day RSS plugin."""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET

from .base import BasePlugin, FetchResult, PluginContext
from .formatting import KeyValue, render_kv, section


WORD_OF_DAY_FEED_URL = "https://www.merriam-webster.com/wotd/feed/rss2"


def _definition(description: str, word: str) -> str:
    decoded = html.unescape(description)
    match = re.search(
        rf"<strong>\s*{re.escape(word)}\s*</strong>.*?<br\s*/?>\s*(?:<p>)?(.*?)</p>",
        decoded,
        flags=re.IGNORECASE | re.DOTALL,
    )
    value = match.group(1) if match else decoded
    return " ".join(re.sub(r"<[^>]+>", " ", value).split())


class WordOfDayPlugin(BasePlugin):
    name = "word_of_day"
    display_name = "Word of the day"

    def fetch(self, context: PluginContext) -> FetchResult:
        try:
            xml_text = context.fetch_text(
                WORD_OF_DAY_FEED_URL,
                context.max_retries,
                context.retry_delay,
            )
            root = ET.fromstring(xml_text)
            item = root.find("./channel/item")
            if item is None:
                raise ValueError("word-of-day feed returned no item")
            word = " ".join((item.findtext("title") or "").split())
            link = (item.findtext("link") or "").strip()
            description = item.findtext("description") or ""
            definition = _definition(description, word)
            if not word or not definition:
                raise ValueError("word-of-day feed returned incomplete data")
            return FetchResult(
                ok=True,
                data={"word": word, "definition": definition, "link": link},
            )
        except Exception as error:
            print(f"  ⚠ Word of the day unavailable: {error}")
            return FetchResult(ok=False, error=str(error))

    def render(self, data: dict[str, str]) -> str:
        rows = [
            KeyValue("Word", data["word"]),
            KeyValue("Definition", data["definition"]),
        ]
        body = "\n".join(render_kv(row.label, row.value) for row in rows)
        if data.get("link"):
            body += f"\nSource: {data['link']}"
        return section("📖  WORD OF THE DAY", body)
