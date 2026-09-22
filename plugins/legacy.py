"""Compatibility helpers for callers of the pre-plugin module API.

Production orchestration does not use this module. It exists temporarily so
local scripts and older integrations can continue importing the former helper
functions while their implementations live in the real plugins.
"""

from __future__ import annotations

from .ai_pricing import (
    AI_GENERAL_NEWS_FEED_URL,
    AI_MODEL_INPUT_TOKENS,
    AI_MODEL_NEWS_FEED_URL,
    AI_MODEL_OUTPUT_TOKENS,
    AI_NEWS_ADVANCE_ALIASES,
    AI_NEWS_FEED_URL,
    AI_NEWS_LIMIT,
    AI_NEWS_PROVIDER_ALIASES,
    DEFAULT_MODEL_IDS,
    OPENROUTER_MODELS_URL,
    fetch_model_pricing,
    format_model_pricing,
    format_token_price,
    get_google_news,
    is_ai_model_advance,
    normalize_news_text,
    parse_model_pricing,
    pricing_due,
)
from .crypto import (
    CRYPTO_ORDER,
    CRYPTO_SYMBOLS,
    MarketQuote,
    build_market_section,
    fetch_crypto_prices,
    yf,
)
from .headlines import HeadlinesPlugin
from .ph_stocks import (
    STOCK_ORDER,
    STOCK_SYMBOLS,
    TWELVEDATA_BASE,
    fetch_stock_prices,
)
from .quote import QuotePlugin
from .weather import WeatherPlugin
from .base import PluginContext


def get_weather(context: PluginContext) -> str:
    plugin = WeatherPlugin()
    result = plugin.fetch(context)
    if result.ok:
        return result.data["text"]
    return f"Weather unavailable ({result.error})"


def get_quote(context: PluginContext) -> str:
    plugin = QuotePlugin()
    result = plugin.fetch(context)
    if result.ok:
        data = result.data
        return f'"{data["quote"]}"\n— {data["author"]}\nSource: https://zenquotes.io/'
    return f"Quote unavailable ({result.error})"


def get_news(context: PluginContext) -> str | None:
    result = HeadlinesPlugin().fetch(context)
    return result.data if result.ok else None


def get_ai_news(context: PluginContext, seen: set[str] | None = None) -> str | None:
    return get_google_news(context, AI_MODEL_NEWS_FEED_URL, model_only=True, seen=seen)


def get_google_ai_news(context: PluginContext, seen: set[str] | None = None) -> str | None:
    return get_google_news(context, AI_GENERAL_NEWS_FEED_URL, seen=seen)


def get_model_pricing(context: PluginContext, missing: list[str] | None = None) -> str | None:
    pricing, missing_items, _ = fetch_model_pricing(context)
    if missing is not None:
        missing.extend(missing_items)
    return pricing
