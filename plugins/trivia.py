"""Open Trivia Database plugin."""

from __future__ import annotations

import html

from .base import BasePlugin, FetchResult, PluginContext
from .formatting import section


TRIVIA_URL = "https://opentdb.com/api.php?amount=1&type=multiple"


class TriviaPlugin(BasePlugin):
    name = "trivia"
    display_name = "Trivia"

    def fetch(self, context: PluginContext) -> FetchResult:
        try:
            payload = context.fetch_json(TRIVIA_URL, context.max_retries, context.retry_delay)
            results = payload.get("results") or []
            question = results[0]
            choices = [question["correct_answer"], *question.get("incorrect_answers", [])]
            return FetchResult(
                ok=True,
                data={
                    "category": html.unescape(str(question.get("category", ""))),
                    "difficulty": str(question.get("difficulty", "")).title(),
                    "question": html.unescape(str(question["question"])),
                    "answer": html.unescape(str(question["correct_answer"])),
                    "choices": [html.unescape(str(choice)) for choice in choices],
                },
            )
        except Exception as error:
            print(f"  ⚠ Trivia unavailable: {error}")
            return FetchResult(ok=False, error=str(error))

    def render(self, data: dict) -> str:
        lines = [
            data["question"],
            f"Category: {data['category']} · Difficulty: {data['difficulty']}",
            "Choices:",
        ]
        lines.extend(f"  - {choice}" for choice in data["choices"])
        lines.append(f"Answer: {data['answer']}")
        lines.append(f"Source: {TRIVIA_URL}")
        return section("🧠  TRIVIA", "\n".join(lines))
