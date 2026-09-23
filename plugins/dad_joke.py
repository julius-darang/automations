"""Dad joke plugin."""

from __future__ import annotations

from .base import BasePlugin, FetchResult, PluginContext
from .formatting import section


DAD_JOKE_URL = "https://icanhazdadjoke.com/"


class DadJokePlugin(BasePlugin):
    name = "dad_joke"
    display_name = "Dad joke"

    def fetch(self, context: PluginContext) -> FetchResult:
        try:
            payload = context.fetch_json(
                DAD_JOKE_URL,
                context.max_retries,
                context.retry_delay,
                {"Accept": "application/json"},
            )
            joke = str(payload["joke"]).strip()
            if not joke:
                raise ValueError("dad-joke provider returned an empty joke")
            return FetchResult(ok=True, data=joke)
        except Exception as error:
            print(f"  ⚠ Dad joke unavailable: {error}")
            return FetchResult(ok=False, error=str(error))

    def render(self, data: str) -> str:
        return section("😄  DAD JOKE", f"{data}\nSource: {DAD_JOKE_URL}")
