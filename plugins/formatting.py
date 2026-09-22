"""Plain-text formatting shared by plugins."""

from __future__ import annotations

SEPARATOR = "━━━━━━━━━━━━━━━━━━━━━━━━"


def section(title: str, body: str) -> str:
    return f"{title}\n{body}"
