"""AI news and OpenRouter pricing plugin.

The two RSS feeds intentionally live in one plugin so their title/link
deduplication does not require shared state between independent plugins.
"""

from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo

from .base import BasePlugin, FetchResult, PluginContext
from .formatting import RankedItem, SEPARATOR, combine_sections, render_ranked_list, section


AI_MODEL_NEWS_QUERY = (
    '(OpenAI OR ChatGPT OR GPT OR Anthropic OR Claude OR xAI OR Grok '
    'OR DeepSeek OR Gemini OR "Google AI" OR Llama OR "Meta AI" '
    'OR Mistral OR Qwen OR Alibaba) '
    '(model OR release OR launch OR benchmark OR reasoning OR training '
    'OR inference OR upgrade OR update OR capabilities OR performance) '
    'when:2d'
)
AI_MODEL_NEWS_FEED_URL = (
    "https://news.google.com/rss/search?"
    f"q={quote_plus(AI_MODEL_NEWS_QUERY)}&hl=en-US&gl=US&ceid=US%3Aen"
)
AI_GENERAL_NEWS_FEED_URL = (
    "https://news.google.com/rss/search?"
    "q=artificial+intelligence+OR+generative+AI+when%3A1d&"
    "hl=en-US&gl=US&ceid=US%3Aen"
)
AI_NEWS_FEED_URL = AI_MODEL_NEWS_FEED_URL
AI_NEWS_LIMIT = 3
AI_NEWS_PROVIDER_ALIASES = (
    "openai", "chatgpt", "gpt",
    "anthropic", "claude",
    "xai", "grok",
    "deepseek",
    "gemini", "google ai", "google deepmind", "deepmind",
    "llama", "meta ai",
    "mistral",
    "qwen", "alibaba ai", "alibaba cloud",
)
AI_NEWS_ADVANCE_ALIASES = (
    "model", "models", "release", "released", "releases", "launch", "launched", "launches",
    "introduce", "introduced", "introduces", "benchmark", "benchmarks",
    "reasoning", "training", "trained", "train", "inference", "infer",
    "upgrade", "upgraded", "update", "updated", "capability", "capabilities",
    "performance", "multimodal", "context window", "weight", "weights",
    "fine tuned", "fine tuning", "open source",
)
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
AI_MODEL_INPUT_TOKENS = 1_000_000
AI_MODEL_OUTPUT_TOKENS = 250_000
DEFAULT_MODEL_IDS = (
    "openai/o3", "openai/gpt-4.1-mini", "google/gemini-2.5-flash",
)


def normalize_news_text(text: str) -> str:
    return " ".join(re.findall("[a-z0-9]+", text.casefold()))


def is_ai_model_advance(title: str) -> bool:
    normalized = normalize_news_text(title)
    padded = f" {normalized} "
    has_provider = any(f" {alias} " in padded for alias in AI_NEWS_PROVIDER_ALIASES)
    has_advance_signal = any(f" {alias} " in padded for alias in AI_NEWS_ADVANCE_ALIASES)
    return has_provider and has_advance_signal


def get_google_news_items(
    context: PluginContext,
    feed_url: str,
    model_only: bool = False,
    seen: set[str] | None = None,
) -> list[RankedItem] | None:
    """Fetch and normalize up to three Google RSS stories."""
    try:
        xml_text = context.fetch_text(feed_url, context.max_retries, context.retry_delay)
        root = ET.fromstring(xml_text)
        items: list[RankedItem] = []
        seen = set() if seen is None else seen
        for item in root.findall(".//item"):
            title = " ".join((item.findtext("title") or "").split())
            link = (item.findtext("link") or "").strip()
            source_element = item.find("source")
            source = " ".join((source_element.text or "").split()) if source_element is not None else ""
            if not title or not link:
                continue
            if model_only and not is_ai_model_advance(title):
                continue

            # RSS titles often append the publisher; ignore that suffix for dedupe.
            headline = title.rsplit(" - ", 1)[0] if " - " in title else title
            title_key = "title:" + normalize_news_text(headline)
            link_key = "url:" + link
            if title_key in seen or link_key in seen:
                continue
            seen.update((title_key, link_key))
            details = (f"Source: {source}",) if source else ()
            items.append(RankedItem(title=title, link=link, details=details))
            if len(items) == AI_NEWS_LIMIT:
                break
        return items
    except Exception as error:
        label = "AI model news" if model_only else "Google AI news"
        print(f"  ⚠ {label} unavailable: {error}")
        return None


def _render_news_items(items: list[RankedItem]) -> str:
    return render_ranked_list(items, max_results=AI_NEWS_LIMIT) if items else "  No new matching stories."


def get_google_news(
    context: PluginContext,
    feed_url: str,
    model_only: bool = False,
    seen: set[str] | None = None,
) -> str | None:
    """Compatibility wrapper returning the legacy plain-text story block."""
    items = get_google_news_items(context, feed_url, model_only=model_only, seen=seen)
    if items is None:
        return None
    return _render_news_items(items)


def parse_model_pricing(data: dict, model_ids: tuple[str, ...] = DEFAULT_MODEL_IDS) -> list[dict]:
    raw_models = data.get("data", []) if isinstance(data, dict) else []
    models_by_id = {
        model.get("id"): model
        for model in raw_models
        if isinstance(model, dict) and model.get("id")
    }
    records: list[dict] = []
    for model_id in model_ids:
        model = models_by_id.get(model_id)
        if not model:
            continue
        pricing = model.get("pricing") or {}
        try:
            input_per_million = float(pricing["prompt"]) * AI_MODEL_INPUT_TOKENS
            output_per_million = float(pricing["completion"]) * AI_MODEL_INPUT_TOKENS
        except (KeyError, TypeError, ValueError):
            continue
        if (
            input_per_million < 0
            or output_per_million < 0
            or not math.isfinite(input_per_million)
            or not math.isfinite(output_per_million)
        ):
            continue

        comparison_cost = input_per_million + (
            output_per_million * AI_MODEL_OUTPUT_TOKENS / AI_MODEL_INPUT_TOKENS
        )
        records.append(
            {
                "display_name": model["id"],
                "model_id": model["id"],
                "input_per_million": input_per_million,
                "output_per_million": output_per_million,
                "comparison_cost": comparison_cost,
            }
        )

    for rank, record in enumerate(
        sorted(records, key=lambda item: (item["comparison_cost"], item["model_id"])),
        start=1,
    ):
        record["cost_rank"] = rank
    return records


def format_token_price(value: float) -> str:
    if value == 0:
        return "$0"
    if value < 0.01:
        return f"${value:,.4f}"
    return f"${value:,.2f}"


def format_model_pricing(records: list[dict]) -> str | None:
    if not records:
        return None

    lines: list[str] = []
    for record in sorted(records, key=lambda item: item["cost_rank"]):
        lines += [
            f"  {record['model_id']}",
            f"    Input/M: {format_token_price(record['input_per_million'])} | "
            f"Output/M: {format_token_price(record['output_per_million'])} | "
            f"Mix: {format_token_price(record['comparison_cost'])}",
        ]
    cheapest = min(records, key=lambda item: item["cost_rank"])
    lines += [
        "",
        f"  Cheapest in watchlist: {cheapest['model_id']} — {format_token_price(cheapest['comparison_cost'])} mix",
        "  Mix = 1M input + 250K output tokens; input/output rates are USD per 1M tokens.",
        "  Source: https://openrouter.ai/models",
    ]
    return "\n".join(lines)


def pricing_due(tz: str, now: datetime | None = None) -> bool:
    local_now = datetime.now(ZoneInfo(tz)) if now is None else now.astimezone(ZoneInfo(tz))
    return local_now.weekday() == 0


def _model_ids(context: PluginContext) -> tuple[str, ...]:
    configured = str(context.setting("AI_MODEL_IDS", ""))
    return tuple(dict.fromkeys(item.strip() for item in configured.split(",") if item.strip())) or DEFAULT_MODEL_IDS


def fetch_model_pricing(context: PluginContext) -> tuple[str | None, tuple[str, ...], str | None]:
    """Return formatted prices, item-level missing labels, and an error label."""
    try:
        payload = context.fetch_json(
            OPENROUTER_MODELS_URL,
            context.max_retries,
            context.retry_delay,
        )
        model_ids = _model_ids(context)
        records = parse_model_pricing(payload, model_ids)
        available = {record["model_id"] for record in records}
        missing = tuple(f"Model price: {model_id}" for model_id in model_ids if model_id not in available)
        return format_model_pricing(records), missing, None
    except Exception as error:
        print(f"  ⚠ AI model pricing unavailable: {error}")
        return None, (), str(error)


class AIPricingPlugin(BasePlugin):
    name = "ai_pricing"
    display_name = "AI updates"

    def fetch(self, context: PluginContext) -> FetchResult:
        data: dict[str, object] = {}
        missing: list[str] = []
        errors: list[str] = []
        seen: set[str] = set()

        model_news = get_google_news_items(context, AI_MODEL_NEWS_FEED_URL, model_only=True, seen=seen)
        if model_news is None:
            missing.append("AI model news")
        else:
            data["model_news"] = model_news

        general_news = get_google_news_items(context, AI_GENERAL_NEWS_FEED_URL, seen=seen)
        if general_news is None:
            missing.append("AI top stories")
        else:
            data["general_news"] = general_news

        try:
            now = context.now
            schedule = context.schedule_for(self.name)
            if schedule and ("always" in schedule or "daily" in schedule):
                scheduled_pricing = True
            elif schedule:
                local_now = datetime.now(ZoneInfo(context.timezone)) if now is None else now.astimezone(ZoneInfo(context.timezone))
                scheduled_pricing = local_now.strftime("%A").casefold() in schedule
            else:
                pricing_checker = context.pricing_due or pricing_due
                scheduled_pricing = pricing_checker(context.timezone, now)
            include_pricing = context.force_pricing or scheduled_pricing
        except Exception as error:
            print(f"  ⚠ AI model pricing schedule unavailable: {error}")
            include_pricing = False
            missing.append("Model pricing")
            errors.append(str(error))
        if include_pricing:
            pricing, pricing_missing, pricing_error = fetch_model_pricing(context)
            missing.extend(pricing_missing)
            if pricing:
                data["pricing"] = pricing
            elif not pricing_missing:
                missing.append("Model pricing")
            if pricing_error:
                errors.append(pricing_error)

        if not data:
            error = "; ".join(errors) if errors else "all AI sources unavailable"
            return FetchResult(False, error=error, missing=tuple(missing))
        return FetchResult(True, data=data, error="; ".join(errors) or None, missing=tuple(missing))

    def render(self, data: dict[str, object]) -> str:
        parts = []
        if "model_news" in data:
            parts.append(section(
                "🤖  AI MODEL ADVANCES",
                f"{SEPARATOR}\n\n{_render_news_items(data['model_news'])}",
            ))
        if "general_news" in data:
            parts.append(section(
                "🗞️  AI TOP STORIES",
                f"{SEPARATOR}\n\n{_render_news_items(data['general_news'])}",
            ))
        if data.get("pricing"):
            parts.append(section(
                "💵  AI MODEL PRICING",
                f"{SEPARATOR}\n\n{data['pricing']}",
            ))
        return combine_sections(*parts)
