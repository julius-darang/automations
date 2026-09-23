"""Yahoo Finance crypto plugin and market formatting helpers."""

from __future__ import annotations

import math
from dataclasses import dataclass

import yfinance as yf

from .base import BasePlugin, FetchResult, PluginContext
from .formatting import KeyValue, render_kv


CRYPTO_SYMBOLS = [
    ("BTC-USD", "BTC"),
    ("ETH-USD", "ETH"),
    ("SOL-USD", "SOL"),
]
CRYPTO_ORDER = ["BTC", "ETH", "SOL"]


@dataclass(frozen=True)
class MarketQuote:
    price: float
    change: float | None
    as_of: str


def fetch_crypto_prices() -> dict[str, MarketQuote]:
    prices: dict[str, MarketQuote] = {}
    for symbol, display_name in CRYPTO_SYMBOLS:
        try:
            history = yf.Ticker(symbol).history(period="5d", timeout=10)
            if history.empty:
                continue
            price = float(history["Close"].iloc[-1])
            if not math.isfinite(price) or price <= 0:
                continue
            change = None
            if len(history) >= 2:
                previous = float(history["Close"].iloc[-2])
                if math.isfinite(previous) and previous > 0:
                    change = (price - previous) / previous * 100
            prices[display_name] = MarketQuote(price, change, history.index[-1].isoformat())
        except Exception as error:
            print(f"  ⚠ Failed to fetch {display_name}: {error}")
    return prices


def render_market_rows(
    title: str,
    prices: dict[str, MarketQuote],
    order: list[str],
    currency: str,
    timestamp_label: str,
) -> list[str]:
    if not prices:
        return []
    lines = [title]
    for name in order:
        if name not in prices:
            continue
        record = prices[name]
        change = "change unavailable" if record.change is None else (
            f"{'▲' if record.change >= 0 else '▼'}{abs(record.change):.1f}%"
        )
        price_row = KeyValue(name, f"{currency}{record.price:,.2f} ({change})")
        timestamp_row = KeyValue(timestamp_label, record.as_of)
        lines.append(f"  {render_kv(price_row.label, price_row.value)}")
        lines.append(f"    {render_kv(timestamp_row.label, timestamp_row.value)}")
    return lines


def render_crypto_section(prices: dict[str, MarketQuote]) -> str:
    return "\n".join(render_market_rows(
        "🪙  CRYPTO — change vs previous daily close",
        prices,
        CRYPTO_ORDER,
        "$",
        "Daily bar",
    ))


def build_market_section(crypto: dict, stocks: dict) -> str:
    """Legacy complete market renderer retained for callers during migration."""
    if not crypto and not stocks:
        return ""
    parts = ["", "━━━━━━━━━━━━━━━━━━━━━━━━", "📈  MARKET UPDATE", "━━━━━━━━━━━━━━━━━━━━━━━━"]
    if crypto:
        parts += ["", render_crypto_section(crypto)]
    if stocks:
        parts += ["", "\n".join(render_market_rows("🇵🇭  PSE STOCKS", stocks, ["BDO", "SM", "TEL", "ALI", "JFC"], "₱", "As of"))]
    return "\n".join(parts)


class CryptoPlugin(BasePlugin):
    name = "crypto"
    display_name = "Crypto"
    section_group = "market"

    def fetch(self, context: PluginContext) -> FetchResult:
        try:
            prices = fetch_crypto_prices()
        except Exception as error:  # defensive boundary around the provider module
            return FetchResult(False, error=str(error))
        missing = tuple(f"Crypto: {name}" for name in CRYPTO_ORDER if name not in prices)
        if not prices:
            return FetchResult(False, error="no crypto prices returned", missing=missing)
        return FetchResult(True, data=prices, missing=missing)

    def render(self, data: dict[str, MarketQuote]) -> str:
        return render_crypto_section(data)
