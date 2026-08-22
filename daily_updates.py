import argparse
import json
import math
import os
import re
import smtplib
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from urllib.parse import quote, quote_plus, urlencode, urlsplit
from zoneinfo import ZoneInfo

import yfinance as yf


CRYPTO_SYMBOLS = [
    ("BTC-USD", "BTC"),
    ("ETH-USD", "ETH"),
    ("SOL-USD", "SOL"),
]

STOCK_SYMBOLS = [
    ("BDO", "BDO"),
    ("SM", "SM"),
    ("TEL", "TEL"),
    ("ALI", "ALI"),
    ("JFC", "JFC"),
]

CRYPTO_ORDER = ["BTC", "ETH", "SOL"]
STOCK_ORDER = ["BDO", "SM", "TEL", "ALI", "JFC"]

TWELVEDATA_BASE = "https://api.twelvedata.com"
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
# Keep the original name available for callers that used the first AI News feed.
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
GOOGLE_NEWS_DECODER_URL = (
    "https://news.google.com/_/DotsSplashUi/data/batchexecute?rpcids=Fbv4je"
)
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
AI_MODEL_INPUT_TOKENS = 1_000_000
AI_MODEL_OUTPUT_TOKENS = 250_000
AI_MODEL_CATALOG = (
    {"label": "OpenAI o3", "ids": ("openai/o3",), "capability_order": 1},
    {
        "label": "Claude Opus",
        "ids": ("anthropic/claude-opus-4.1", "anthropic/claude-opus-4"),
        "capability_order": 2,
    },
    {
        "label": "Gemini 2.5 Pro",
        "ids": ("google/gemini-2.5-pro",),
        "capability_order": 3,
    },
    {"label": "OpenAI GPT-4.1", "ids": ("openai/gpt-4.1",), "capability_order": 4},
    {
        "label": "Claude Sonnet",
        "ids": ("anthropic/claude-sonnet-4",),
        "capability_order": 5,
    },
    {
        "label": "Grok",
        "ids": ("x-ai/grok-4.6", "x-ai/grok-4.5", "x-ai/grok-4", "x-ai/grok-3"),
        "capability_order": 6,
    },
    {
        "label": "DeepSeek R1",
        "ids": ("deepseek/deepseek-r1", "deepseek/deepseek-r1-0528"),
        "capability_order": 7,
    },
    {
        "label": "Qwen 3 235B",
        "ids": ("qwen/qwen3-235b-a22b", "qwen/qwen3-235b-a22b-2507"),
        "capability_order": 8,
    },
    {
        "label": "Llama 4 Maverick",
        "ids": ("meta-llama/llama-4-maverick",),
        "capability_order": 9,
    },
    {
        "label": "Mistral Large",
        "ids": ("mistralai/mistral-large", "mistralai/mistral-large-2512"),
        "capability_order": 10,
    },
    {
        "label": "Gemini 2.5 Flash",
        "ids": ("google/gemini-2.5-flash",),
        "capability_order": 11,
    },
    {
        "label": "DeepSeek V3",
        "ids": ("deepseek/deepseek-chat", "deepseek/deepseek-chat-v3-0324"),
        "capability_order": 12,
    },
    {
        "label": "OpenAI GPT-4.1 mini",
        "ids": ("openai/gpt-4.1-mini",),
        "capability_order": 13,
    },
)
AI_MODEL_CAPABILITY_NOTE = "Curated capability order; not a live benchmark score."
RECIPIENTS_FILE = Path(__file__).with_name("recipients.txt")


@dataclass(frozen=True)
class Config:
    sender_email: str
    sender_password: str
    recipients: tuple[str, ...]
    twelvedata_api_key: str = ""
    timezone: str = "Asia/Manila"
    lat: float = 11.6083
    lon: float = 125.4358
    city: str = "Borongan City, Eastern Samar"
    max_retries: int = 2
    retry_delay: int = 3


def load_env(path: str = ".env") -> None:
    env_file = Path(path)
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip())


def parse_recipient_lines(lines: list[str]) -> tuple[str, ...]:
    recipients = []
    seen = set()
    for line in lines:
        recipient = line.strip()
        if not recipient or recipient.startswith("#") or recipient in seen:
            continue
        recipients.append(recipient)
        seen.add(recipient)
    return tuple(recipients)


def load_recipients(path: Path | None = None) -> tuple[str, ...]:
    path = RECIPIENTS_FILE if path is None else Path(path)
    if path.exists():
        recipients = parse_recipient_lines(path.read_text().splitlines())
        if recipients:
            return recipients

    recipients = parse_recipient_lines(os.environ.get("RECIPIENT_EMAILS", "").splitlines())
    if recipients:
        return recipients

    return parse_recipient_lines([os.environ.get("RECEIVER_EMAIL", "")])


def load_config(require_credentials: bool = True) -> Config:
    recipients = load_recipients()
    missing = [
        key for key in ("SENDER_EMAIL", "SENDER_PASSWORD") if not os.environ.get(key)
    ]
    if not recipients:
        missing.append("recipients.txt/RECIPIENT_EMAILS/RECEIVER_EMAIL")
    if require_credentials and missing:
        print(f"FATAL: Missing environment variables or recipient file: {', '.join(missing)}")
        sys.exit(1)
    return Config(
        sender_email=os.environ.get("SENDER_EMAIL", ""),
        sender_password=os.environ.get("SENDER_PASSWORD", ""),
        recipients=recipients,
        twelvedata_api_key=os.environ.get("TWELVEDATA_API_KEY", ""),
        timezone=os.environ.get("TIMEZONE", "Asia/Manila"),
        lat=float(os.environ.get("LAT", "11.6083")),
        lon=float(os.environ.get("LON", "125.4358")),
        city=os.environ.get("CITY", "Borongan City, Eastern Samar"),
    )


def fetch_json(url: str, max_retries: int = 2, delay: int = 3) -> dict | list:
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as res:
                return json.loads(res.read())
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                time.sleep(delay)
    raise last_error


def fetch_text(url: str, max_retries: int = 2, delay: int = 3) -> str:
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as res:
                return res.read().decode("utf-8")
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                time.sleep(delay)
    raise last_error


def get_date_info(tz: str) -> tuple[str, str]:
    now = datetime.now(ZoneInfo(tz))
    return now.strftime("%A"), now.strftime("%B %d, %Y")


def get_weather(cfg: Config) -> str:
    try:
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={cfg.lat}&longitude={cfg.lon}"
            "&current=temperature_2m,weathercode,windspeed_10m,relative_humidity_2m"
            f"&timezone={cfg.timezone.replace('/', '%2F')}"
        )
        data = fetch_json(url, cfg.max_retries, cfg.retry_delay)
        current  = data["current"]
        temp     = current["temperature_2m"]
        humidity = current["relative_humidity_2m"]
        wind     = current["windspeed_10m"]
        code     = current["weathercode"]

        weather_map = {
            0: "Clear sky ☀️", 1: "Mainly clear 🌤️", 2: "Partly cloudy ⛅",
            3: "Overcast ☁️", 45: "Foggy 🌫️", 48: "Foggy 🌫️",
            51: "Light drizzle 🌦️", 53: "Drizzle 🌦️", 55: "Heavy drizzle 🌧️",
            61: "Light rain 🌧️", 63: "Rain 🌧️", 65: "Heavy rain 🌧️",
            80: "Rain showers 🌦️", 81: "Rain showers 🌦️", 82: "Heavy showers ⛈️",
            95: "Thunderstorm ⛈️", 96: "Thunderstorm ⛈️", 99: "Thunderstorm ⛈️",
        }
        description = weather_map.get(code, "Unknown")
        return f"{description} | {temp}°C | Humidity: {humidity}% | Wind: {wind} km/h"
    except Exception as e:
        return f"Weather unavailable ({e})"


def get_quote(cfg: Config) -> str:
    try:
        url = "https://zenquotes.io/api/random"
        data = fetch_json(url, cfg.max_retries, cfg.retry_delay)
        quote  = data[0]["q"]
        author = data[0]["a"]
        return f'"{quote}"\n— {author}'
    except Exception as e:
        return f"Quote unavailable ({e})"


def get_news(cfg: Config) -> str | None:
    try:
        xml_text = fetch_text("https://feeds.bbci.co.uk/news/rss.xml", cfg.max_retries, cfg.retry_delay)
        root = ET.fromstring(xml_text)
        items = root.findall(".//item")[:3]
        if not items:
            return None
        lines = []
        for item in items:
            title = item.findtext("title", "")
            lines.append(f"  • {title}")
        return "\n" + "\n".join(lines)
    except Exception:
        return None


def normalize_news_text(text: str) -> str:
    return " ".join(re.findall("[a-z0-9]+", text.casefold()))


def is_ai_model_advance(title: str) -> bool:
    normalized = normalize_news_text(title)
    padded = f" {normalized} "
    has_provider = any(f" {alias} " in padded for alias in AI_NEWS_PROVIDER_ALIASES)
    has_advance_signal = any(f" {alias} " in padded for alias in AI_NEWS_ADVANCE_ALIASES)
    return has_provider and has_advance_signal


def parse_google_news_article_id(url: str) -> str | None:
    parsed = urlsplit(url)
    if parsed.hostname != "news.google.com":
        return None
    path_parts = [part for part in parsed.path.split("/") if part]
    if len(path_parts) < 2 or path_parts[-2] not in {"articles", "read"}:
        return None
    return path_parts[-1]


def post_text(url: str, data: bytes, max_retries: int = 2, delay: int = 3) -> str:
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(
                url,
                data=data,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                    "Referer": "https://news.google.com/",
                    "User-Agent": "Mozilla/5.0",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as res:
                return res.read().decode("utf-8")
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                time.sleep(delay)
    raise last_error


def parse_google_news_decoder_response(response_text: str) -> str | None:
    for chunk in response_text.split("\n\n")[1:]:
        try:
            outer = json.loads(chunk)
        except (TypeError, json.JSONDecodeError):
            continue
        if not isinstance(outer, list):
            continue
        for entry in outer:
            if not isinstance(entry, list) or len(entry) < 3 or entry[0] != "wrb.fr":
                continue
            try:
                decoded = json.loads(entry[2])
            except (TypeError, json.JSONDecodeError):
                continue
            if (
                isinstance(decoded, list)
                and len(decoded) > 1
                and decoded[0] == "garturlres"
                and isinstance(decoded[1], str)
                and decoded[1].startswith(("http://", "https://"))
            ):
                return decoded[1]
    return None


def resolve_google_news_url(url: str, max_retries: int = 2, delay: int = 3) -> str:
    article_id = parse_google_news_article_id(url)
    if not article_id:
        return url

    page_urls = (
        f"https://news.google.com/articles/{quote(article_id, safe='')}",
        f"https://news.google.com/rss/articles/{quote(article_id, safe='')}",
    )
    for page_url in page_urls:
        try:
            page_html = fetch_text(page_url, max_retries, delay)
            signature_match = re.search('data-n-a-sg="([^"]+)"', page_html)
            timestamp_match = re.search('data-n-a-ts="([^"]+)"', page_html)
            if not signature_match or not timestamp_match:
                continue

            request_payload = [
                "garturlreq",
                [
                    [
                        "X",
                        "X",
                        ["X", "X"],
                        None,
                        None,
                        1,
                        1,
                        "US:en",
                        None,
                        1,
                        None,
                        None,
                        None,
                        None,
                        None,
                        0,
                        1,
                    ],
                    "X",
                    "X",
                    1,
                    [1, 1, 1],
                    1,
                    1,
                    None,
                    0,
                    0,
                    None,
                    0,
                ],
                article_id,
                int(timestamp_match.group(1)),
                signature_match.group(1),
            ]
            rpc_payload = [
                "Fbv4je",
                json.dumps(request_payload, separators=(",", ":")),
            ]
            request_body = urlencode(
                {"f.req": json.dumps([[rpc_payload]], separators=(",", ":"))}
            ).encode("utf-8")
            resolved = parse_google_news_decoder_response(
                post_text(GOOGLE_NEWS_DECODER_URL, request_body, max_retries, delay)
            )
            if resolved:
                return resolved
        except Exception:
            continue

    return url


def compact_url(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return url

    hostname = parsed.hostname
    if hostname.startswith("www."):
        hostname = hostname[4:]
    netloc = hostname
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{netloc}{path}"


def format_google_news_link(link: str, source_url: str, cfg: Config) -> str:
    resolved = resolve_google_news_url(link, cfg.max_retries, cfg.retry_delay)
    if resolved == link and parse_google_news_article_id(link) and source_url:
        return compact_url(source_url)
    return compact_url(resolved)


def get_google_news(
    cfg: Config,
    feed_url: str,
    model_only: bool = False,
) -> str | None:
    try:
        xml_text = fetch_text(feed_url, cfg.max_retries, cfg.retry_delay)
        root = ET.fromstring(xml_text)
        blocks = []
        seen_titles = set()
        for item in root.findall(".//item"):
            title = " ".join((item.findtext("title") or "").split())
            link = (item.findtext("link") or "").strip()
            source_element = item.find("source")
            source = " ".join((source_element.text or "").split()) if source_element is not None else ""
            source_url = source_element.attrib.get("url", "").strip() if source_element is not None else ""
            if not title or not link:
                continue
            if model_only and not is_ai_model_advance(title):
                continue

            title_key = normalize_news_text(title)
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)

            block = [f"  • {title}"]
            if source:
                block.append(f"    Source: {source}")
            block.append(f"    {format_google_news_link(link, source_url, cfg)}")
            blocks.append("\n".join(block))
            if len(blocks) == AI_NEWS_LIMIT:
                break

        return "\n\n".join(blocks) if blocks else None
    except Exception as e:
        label = "AI model news" if model_only else "Google AI news"
        print(f"  ⚠ {label} unavailable: {e}")
        return None


def get_ai_news(cfg: Config) -> str | None:
    return get_google_news(cfg, AI_NEWS_FEED_URL, model_only=True)


def get_google_ai_news(cfg: Config) -> str | None:
    return get_google_news(cfg, AI_GENERAL_NEWS_FEED_URL)


def parse_model_pricing(data: dict) -> list[dict]:
    raw_models = data.get("data", []) if isinstance(data, dict) else []
    models_by_id = {
        model.get("id"): model
        for model in raw_models
        if isinstance(model, dict) and model.get("id")
    }
    records = []
    for spec in AI_MODEL_CATALOG:
        model = next(
            (models_by_id[model_id] for model_id in spec["ids"] if model_id in models_by_id),
            None,
        )
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
                "display_name": spec["label"],
                "model_id": model["id"],
                "input_per_million": input_per_million,
                "output_per_million": output_per_million,
                "comparison_cost": comparison_cost,
                "capability_order": spec["capability_order"],
            }
        )

    for rank, record in enumerate(
        sorted(records, key=lambda item: item["capability_order"]),
        start=1,
    ):
        record["capability_rank"] = rank
    for rank, record in enumerate(
        sorted(records, key=lambda item: (item["comparison_cost"], item["capability_order"])),
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

    lines = [
        "  MODEL                         IN/M     OUT/M     MIX*   CHEAP  CAP",
        "  ---------------------------  -------  -------  -------  -----  ---",
    ]
    for record in sorted(records, key=lambda item: item["capability_rank"]):
        name = record["display_name"][:27]
        lines.append(
            f"  {name:<27}  "
            f"{format_token_price(record['input_per_million']):>7}  "
            f"{format_token_price(record['output_per_million']):>7}  "
            f"{format_token_price(record['comparison_cost']):>7}  "
            f"#{record['cost_rank']:<5}  #{record['capability_rank']}"
        )

    cheapest = min(records, key=lambda item: item["cost_rank"])
    most_capable = min(records, key=lambda item: item["capability_rank"])
    lines += [
        "",
        f"  Cheapest: {cheapest['display_name']} — {format_token_price(cheapest['comparison_cost'])} mix",
        f"  Most capable: {most_capable['display_name']} — curated rank #1",
        f"  Capability note: {AI_MODEL_CAPABILITY_NOTE}",
        "  * Mix = 1M input + 250K output tokens; prices are USD per 1M tokens.",
        "  Source: https://openrouter.ai/models",
    ]
    return "\n".join(lines)


def get_model_pricing(cfg: Config) -> str | None:
    try:
        data = fetch_json(OPENROUTER_MODELS_URL, cfg.max_retries, cfg.retry_delay)
        return format_model_pricing(parse_model_pricing(data))
    except Exception as e:
        print(f"  ⚠ AI model pricing unavailable: {e}")
        return None


def get_crypto_prices() -> dict:
    prices = {}
    for symbol, display_name in CRYPTO_SYMBOLS:
        try:
            t = yf.Ticker(symbol)
            hist = t.history(period="5d")
            if hist.empty:
                print(f"  ⚠ No data for {display_name}")
                continue
            price = hist["Close"].iloc[-1]
            change_pct = 0.0
            if len(hist) >= 2:
                prev_close = hist["Close"].iloc[-2]
                change_pct = ((price - prev_close) / prev_close) * 100
            prices[display_name] = (price, change_pct)
        except Exception as e:
            print(f"  ⚠ Failed to fetch {display_name}: {e}")
    return prices


def get_stock_prices(cfg: Config) -> dict:
    prices = {}
    if not cfg.twelvedata_api_key:
        print("  ⚠ TWELVEDATA_API_KEY not set, skipping PH stocks")
        return prices
    for symbol, display_name in STOCK_SYMBOLS:
        try:
            url = f"{TWELVEDATA_BASE}/quote?symbol={symbol}&exchange=PSE&apikey={cfg.twelvedata_api_key}"
            data = fetch_json(url, cfg.max_retries, cfg.retry_delay)
            if "status" in data and data["status"] == "error":
                raise Exception(data.get("message", "unknown error"))
            price = float(data["close"])
            change_pct = float(data.get("percent_change", 0))
            prices[display_name] = (price, change_pct)
        except Exception as e:
            print(f"  ⚠ Failed to fetch {display_name}: {e}")
    return prices


def build_market_section(crypto: dict, stocks: dict) -> str:
    parts = [
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "📈  MARKET UPDATE",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    if crypto:
        parts += ["", "🪙  CRYPTO"]
        for name in CRYPTO_ORDER:
            if name not in crypto:
                continue
            price, change = crypto[name]
            arrow = "▲" if change >= 0 else "▼"
            parts.append(f"  {name}  •  ${price:,.2f}  ({arrow}{abs(change):.1f}%)")

    if stocks:
        parts += ["", "━━━━━━━━━━━━━━━━━━━━━━━━", "", "🇵🇭  PSE STOCKS"]
        for name in STOCK_ORDER:
            if name not in stocks:
                continue
            price, change = stocks[name]
            arrow = "▲" if change >= 0 else "▼"
            parts.append(f"  {name}  •  ₱{price:,.2f}  ({arrow}{abs(change):.1f}%)")

    return "\n".join(parts)


def build_body(
    cfg: Config,
    day_str: str,
    date_str: str,
    weather: str,
    quote: str,
    news: str | None,
    market: str = "",
    ai_news: str | None = None,
    google_ai_news: str | None = None,
    model_pricing: str | None = None,
) -> str:
    parts = [
        "Good afternoon!",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📅  {day_str}, {date_str}",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        f"🌤  WEATHER — {cfg.city}",
        weather,
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        "💬  QUOTE OF THE DAY",
        quote,
    ]

    if news:
        parts += [
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            "📰  HEADLINES",
            news,
        ]

    if ai_news:
        parts += [
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            "🤖  AI MODEL ADVANCES",
            "━━━━━━━━━━━━━━━━━━━━━━━━",
            ai_news,
        ]

    if google_ai_news:
        parts += [
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            "🗞️  AI TOP STORIES",
            "━━━━━━━━━━━━━━━━━━━━━━━━",
            google_ai_news,
        ]

    if model_pricing:
        parts += [
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            "💵  AI MODEL PRICING",
            "━━━━━━━━━━━━━━━━━━━━━━━━",
            model_pricing,
        ]

    if market:
        parts += [
            "",
            market,
        ]

    parts += [
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        "More upgrades coming soon.",
        "",
        "— Your Agent",
    ]

    return "\n".join(parts)


def send_email(cfg: Config, subject: str, body: str) -> bool:
    msg = MIMEMultipart()
    msg["From"]    = cfg.sender_email
    msg["To"]      = ", ".join(cfg.recipients)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(cfg.sender_email, cfg.sender_password)
            server.sendmail(cfg.sender_email, list(cfg.recipients), msg.as_string())
        print(f"✅ Email sent to {', '.join(cfg.recipients)}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        fallback_path = f"email_fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(fallback_path, "w") as f:
            f.write(f"Subject: {subject}\n\n{body}")
        print(f"📝 Email saved to {fallback_path}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Send daily brief email")
    parser.add_argument("--dry-run", action="store_true", help="Print email to stdout instead of sending")
    parser.add_argument("--local", action="store_true", help="Load .env file from current directory")
    args = parser.parse_args()

    if args.local:
        load_env()

    cfg = load_config(require_credentials=not args.dry_run)
    day_str, date_str = get_date_info(cfg.timezone)
    weather = get_weather(cfg)
    quote   = get_quote(cfg)
    news            = get_news(cfg)
    ai_news         = get_ai_news(cfg)
    google_ai_news  = get_google_ai_news(cfg)
    model_pricing   = get_model_pricing(cfg)

    print("Fetching crypto prices...")
    crypto = get_crypto_prices()
    print(f"  fetched {len(crypto)}")
    for name, (price, change) in crypto.items():
        arrow = "▲" if change >= 0 else "▼"
        print(f"    {name}: {price:.2f} ({arrow}{abs(change):.1f}%)")

    print("Fetching PH stock prices...")
    stocks = get_stock_prices(cfg)
    print(f"  fetched {len(stocks)}")
    for name, (price, change) in stocks.items():
        arrow = "▲" if change >= 0 else "▼"
        print(f"    {name}: {price:.2f} ({arrow}{abs(change):.1f}%)")

    market = build_market_section(crypto, stocks)

    subject = f"Daily Brief & Market Update — {day_str}, {date_str}"
    body    = build_body(
        cfg,
        day_str,
        date_str,
        weather,
        quote,
        news,
        market,
        ai_news,
        google_ai_news,
        model_pricing,
    )

    print(f"🌤  {weather}")
    print(f"💬  {quote[:60]}...")
    if news:
        print(f"📰  Headline: {news.split('•')[1].strip() if '•' in news else 'loaded'}")
    if ai_news:
        print(f"🤖  AI model headline: {ai_news.split('•')[1].strip() if '•' in ai_news else 'loaded'}")
    if google_ai_news:
        print(f"🗞️  AI top headline: {google_ai_news.split('•')[1].strip() if '•' in google_ai_news else 'loaded'}")
    if model_pricing:
        print("💵  AI model pricing: loaded")

    if args.dry_run:
        print(f"\n{'='*60}")
        print(f"Subject: {subject}")
        print(f"{'='*60}")
        print(body)
        return

    if not send_email(cfg, subject, body):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
