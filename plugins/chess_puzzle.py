"""Lichess daily chess puzzle plugin."""

from __future__ import annotations

from .base import BasePlugin, FetchResult, PluginContext
from .formatting import KeyValue, render_kv, section


CHESS_PUZZLE_URL = "https://lichess.org/api/puzzle/daily"
CHESS_PUZZLE_PAGE = "https://lichess.org/training/{puzzle_id}"


class ChessPuzzlePlugin(BasePlugin):
    name = "chess_puzzle"
    display_name = "Chess puzzle"

    def fetch(self, context: PluginContext) -> FetchResult:
        try:
            payload = context.fetch_json(
                CHESS_PUZZLE_URL,
                context.max_retries,
                context.retry_delay,
            )
            puzzle = payload["puzzle"]
            puzzle_id = str(puzzle["id"]).strip()
            rating = puzzle.get("rating")
            themes = puzzle.get("themes") or []
            fen = str(puzzle.get("fen") or "").strip()
            if not puzzle_id or not fen:
                raise ValueError("Lichess returned incomplete puzzle data")
            rows = [KeyValue("Rating", rating), KeyValue("Themes", ", ".join(themes))]
            return FetchResult(
                ok=True,
                data={
                    "rows": rows,
                    "fen": fen,
                    "link": CHESS_PUZZLE_PAGE.format(puzzle_id=puzzle_id),
                },
            )
        except Exception as error:
            print(f"  ⚠ Chess puzzle unavailable: {error}")
            return FetchResult(ok=False, error=str(error))

    def render(self, data: dict) -> str:
        rows = [render_kv(row.label, row.value) for row in data["rows"]]
        rows.append(render_kv("FEN", data["fen"]))
        rows.append(f"Solve: {data['link']}")
        return section("♟️  CHESS PUZZLE OF THE DAY", "\n".join(rows))
