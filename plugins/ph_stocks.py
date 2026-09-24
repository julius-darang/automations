"""Optional Twelve Data PSE stock plugin."""

from __future__ import annotations

import math

from .base import BasePlugin, FetchResult, PluginContext
from .crypto import MarketQuote, render_market_rows
from .formatting import section


STOCK_SYMBOLS = [
    ("BDO", "BDO"),
    ("SM", "SM"),
    ("TEL", "TEL"),
    ("ALI", "ALI"),
    ("JFC", "JFC"),
]
STOCK_ORDER = ["BDO", "SM", "TEL", "ALI", "JFC"]
TWELVEDATA_BASE = "https://api.twelvedata.com"


def fetch_stock_prices(context: PluginContext) -> dict[str, MarketQuote]:
    prices: dict[str, MarketQuote] = {}
    api_key = context.secret("TWELVEDATA_API_KEY")
    if not api_key:
        return prices

    for symbol, display_name in STOCK_SYMBOLS:
        try:
            url = f"{TWELVEDATA_BASE}/quote?symbol={symbol}&exchange=PSE&apikey={api_key}"
            payload = context.fetch_json(url, context.max_retries, context.retry_delay)
            if payload.get("status") == "error":
                raise ValueError(payload.get("message", "unknown error"))
            price = float(payload["close"])
            if not math.isfinite(price) or price <= 0:
                raise ValueError("invalid price")
            raw_change = payload.get("percent_change")
            change = float(raw_change) if raw_change is not None else None
            if change is not None and not math.isfinite(change):
                change = None
            as_of = payload.get("datetime")
            if as_of:
                as_of = f"{as_of} {payload.get('exchange_timezone') or 'timezone unknown'}"
            else:
                as_of = "timestamp unavailable"
            prices[display_name] = MarketQuote(price, change, as_of)
        except Exception as error:
            redacted = str(error).replace(api_key, "[redacted]")
            print(f"  ⚠ Failed to fetch {display_name}: {redacted}")
    return prices


def render_stock_section(prices: dict[str, MarketQuote]) -> str:
    rows = render_market_rows("🇵🇭  PSE STOCKS", prices, STOCK_ORDER, "₱", "As of")
    return section(rows[0], "\n".join(rows[1:])) if rows else ""


class PHStocksPlugin(BasePlugin):
    name = "ph_stocks"
    display_name = "PH stocks"
    section_group = "market"

    def should_run(self, context: PluginContext) -> bool:
        return bool(context.secret("TWELVEDATA_API_KEY"))

    def fetch(self, context: PluginContext) -> FetchResult:
        try:
            prices = fetch_stock_prices(context)
        except Exception as error:
            return FetchResult(False, error=str(error))
        missing = tuple(f"PH stocks: {name}" for name in STOCK_ORDER if name not in prices)
        if not prices:
            return FetchResult(False, error="no PSE stock prices returned", missing=missing)
        return FetchResult(True, data=prices, missing=missing)

    def render(self, data: dict[str, MarketQuote]) -> str:
        return render_stock_section(data)
