"""Product Hunt Atom feed plugin."""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET

from .base import BasePlugin, FetchResult, PluginContext
from .formatting import RankedItem, render_ranked_list, section


PRODUCT_HUNT_FEED_URL = "https://www.producthunt.com/feed"
PRODUCT_HUNT_LIMIT = 5
ATOM_NAMESPACE = {"atom": "http://www.w3.org/2005/Atom"}


def _description(content: str) -> str:
    decoded = html.unescape(content)
    paragraph = re.search(r"<p[^>]*>(.*?)</p>", decoded, flags=re.IGNORECASE | re.DOTALL)
    value = paragraph.group(1) if paragraph else decoded
    return " ".join(re.sub(r"<[^>]+>", " ", value).split())


class ProductHuntPlugin(BasePlugin):
    name = "product_hunt"
    display_name = "Product Hunt"

    def fetch(self, context: PluginContext) -> FetchResult:
        try:
            xml_text = context.fetch_text(
                PRODUCT_HUNT_FEED_URL,
                context.max_retries,
                context.retry_delay,
            )
            root = ET.fromstring(xml_text)
            limit = int(context.setting("PRODUCT_HUNT_LIMIT", PRODUCT_HUNT_LIMIT))
            if not 1 <= limit <= 25:
                raise ValueError("PRODUCT_HUNT_LIMIT must be between 1 and 25")
            items: list[RankedItem] = []
            for entry in root.findall("atom:entry", ATOM_NAMESPACE):
                title = " ".join((entry.findtext("atom:title", default="", namespaces=ATOM_NAMESPACE)).split())
                link = ""
                for link_element in entry.findall("atom:link", ATOM_NAMESPACE):
                    if link_element.get("rel", "alternate") == "alternate":
                        link = str(link_element.get("href", "")).strip()
                        break
                if not link:
                    continue
                details: list[str] = []
                summary = _description(entry.findtext("atom:content", default="", namespaces=ATOM_NAMESPACE))
                if summary:
                    details.append(summary)
                author = entry.findtext("atom:author/atom:name", default="", namespaces=ATOM_NAMESPACE)
                if author:
                    details.append(f"Maker: {' '.join(author.split())}")
                published = entry.findtext("atom:published", default="", namespaces=ATOM_NAMESPACE)
                if published:
                    details.append(f"Published: {published[:10]}")
                if title:
                    items.append(RankedItem(title=title, link=link, details=tuple(details)))
                if len(items) == limit:
                    break
            if not items:
                return FetchResult(ok=False, error="Product Hunt returned no products")
            return FetchResult(ok=True, data=items)
        except Exception as error:
            print(f"  ⚠ Product Hunt unavailable: {error}")
            return FetchResult(ok=False, error=str(error))

    def render(self, data: list[RankedItem]) -> str:
        return section("🚀  PRODUCT HUNT", render_ranked_list(data, max_results=PRODUCT_HUNT_LIMIT))
