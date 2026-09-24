"""Small, shape-based plain-text renderers shared by plugins."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence
from urllib.parse import urlsplit

SEPARATOR = "━━━━━━━━━━━━━━━━━━━━━━━━"


@dataclass(frozen=True)
class RankedItem:
    """One item in a title/link list."""

    title: str
    link: str = ""
    details: tuple[str, ...] = ()


@dataclass(frozen=True)
class KeyValue:
    """A compact label/value row."""

    label: str
    value: object
    unit: str = ""


@dataclass(frozen=True)
class EmailSection:
    """Explicit email structure for one titled section and optional children."""

    title: str
    body: str = ""
    children: tuple["EmailSection", ...] = ()


class SectionText(str):
    """Plain-text section with structured email metadata attached."""

    sections: tuple[EmailSection, ...]

    def __new__(cls, value: str, sections: tuple[EmailSection, ...]):
        instance = super().__new__(cls, value)
        instance.sections = sections
        return instance


def render_ranked_list(items: Sequence[RankedItem], max_results: int = 5) -> str:
    """Render a bounded list of title, metadata, and link items."""
    lines: list[str] = []
    for item in items[:max_results]:
        lines.append(f"  • {item.title}")
        lines.extend(f"    {detail}" for detail in item.details if detail)
        if item.link:
            lines.append(f"    {item.link}")
    return "\n".join(lines) if lines else "  No items."


def render_kv(label: str, value: object, unit: str = "") -> str:
    """Render one label/value row."""
    value_text = f"{value}{unit}"
    return value_text if not label else f"{label}: {value_text}"


def render_quote(text: str, author: str = "") -> str:
    """Render quoted text with optional attribution."""
    lines = [f'"{text}"']
    if author:
        lines.append(f"— {author}")
    return "\n".join(lines)


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


def section(title: str, body: str) -> SectionText:
    """Render plain text and preserve title/body boundaries for HTML email."""
    return SectionText(f"{title}\n{body}", (EmailSection(title=title, body=body),))


def combine_sections(*parts: SectionText) -> SectionText:
    """Combine titled sections without losing their HTML structure."""
    sections = tuple(section for part in parts for section in part.sections)
    return SectionText("\n\n".join(str(part) for part in parts), sections)
