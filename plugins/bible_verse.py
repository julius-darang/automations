"""Random Bible verse plugin using the public-domain WEB translation."""

from __future__ import annotations

from .base import BasePlugin, FetchResult, PluginContext
from .formatting import KeyValue, render_kv, section


BIBLE_RANDOM_URL = "https://bible-api.com/data/web/random"


class BibleVersePlugin(BasePlugin):
    name = "bible_verse"
    display_name = "Bible verse"

    def fetch(self, context: PluginContext) -> FetchResult:
        try:
            payload = context.fetch_json(
                BIBLE_RANDOM_URL,
                context.max_retries,
                context.retry_delay,
            )
            verse = payload["random_verse"]
            reference = f"{verse['book']} {verse['chapter']}:{verse['verse']}"
            text = " ".join(str(verse["text"]).split())
            if not text:
                raise ValueError("Bible API returned an empty verse")
            return FetchResult(ok=True, data={"reference": reference, "text": text})
        except Exception as error:
            print(f"  ⚠ Bible verse unavailable: {error}")
            return FetchResult(ok=False, error=str(error))

    def render(self, data: dict[str, str]) -> str:
        body = "\n".join((
            render_kv("Reference", data["reference"]),
            render_kv("Text", data["text"]),
            "Translation: World English Bible (public domain)",
            f"Source: {BIBLE_RANDOM_URL}",
        ))
        return section("📜  BIBLE VERSE", body)
