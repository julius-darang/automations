"""Plain-text formatting shared by plugins."""

from __future__ import annotations

from urllib.parse import urlsplit

SEPARATOR = "━━━━━━━━━━━━━━━━━━━━━━━━"


def shorten_url(url: str, max_length: int = 72) -> str:
    """Keep long URLs readable while retaining their host and tail query."""
    if len(url) <= max_length:
        return url

    parsed = urlsplit(url)
    prefix = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else ""
    suffix = f"?{parsed.query}" if parsed.query and len(parsed.query) <= 12 else ""
    path = parsed.path or "/"
    available = max_length - len(prefix) - len(suffix) - 1
    if not prefix or available <= 0:
        return url[: max_length - 1] + "…"
    return f"{prefix}{path[:available]}…{suffix}"


def section(title: str, body: str) -> str:
    return f"{title}\n{body}"
