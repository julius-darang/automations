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
from urllib.parse import quote_plus
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
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
AI_MODEL_INPUT_TOKENS = 1_000_000
AI_MODEL_OUTPUT_TOKENS = 250_000
DEFAULT_MODEL_IDS = (
    "openai/o3", "openai/gpt-4.1-mini", "google/gemini-2.5-flash",
)
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
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        os.environ.setdefault(key.strip(), val)


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
        return f'"{quote}"\n— {author}\nSource: https://zenquotes.io/'
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
            link = item.findtext("link", "").strip()
            if link:
                lines.append(f"    {link}")
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


def get_google_news(
    cfg: Config,
    feed_url: str,
    model_only: bool = False,
    seen: set[str] | None = None,
) -> str | None:
    try:
        xml_text = fetch_text(feed_url, cfg.max_retries, cfg.retry_delay)
        root = ET.fromstring(xml_text)
        blocks = []
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

            block = [f"  • {title}"]
            if source:
                block.append(f"    Source: {source}")
            block.append(f"    {link}")
            blocks.append("\n".join(block))
            if len(blocks) == AI_NEWS_LIMIT:
                break

        return "\n\n".join(blocks) if blocks else "  No new matching stories."
    except Exception as e:
        label = "AI model news" if model_only else "Google AI news"
        print(f"  ⚠ {label} unavailable: {e}")
        return None


def get_ai_news(cfg: Config, seen: set[str] | None = None) -> str | None:
    return get_google_news(cfg, AI_NEWS_FEED_URL, model_only=True, seen=seen)


def get_google_ai_news(cfg: Config, seen: set[str] | None = None) -> str | None:
    return get_google_news(cfg, AI_GENERAL_NEWS_FEED_URL, seen=seen)


def parse_model_pricing(data: dict, model_ids: tuple[str, ...] = DEFAULT_MODEL_IDS) -> list[dict]:
    raw_models = data.get("data", []) if isinstance(data, dict) else []
    models_by_id = {
        model.get("id"): model
        for model in raw_models
        if isinstance(model, dict) and model.get("id")
    }
    records = []
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

    lines = []
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


def get_model_pricing(cfg: Config, missing: list[str] | None = None) -> str | None:
    try:
        data = fetch_json(OPENROUTER_MODELS_URL, cfg.max_retries, cfg.retry_delay)
        model_ids = tuple(dict.fromkeys(
            item.strip() for item in os.environ.get("AI_MODEL_IDS", "").split(",") if item.strip()
        )) or DEFAULT_MODEL_IDS
        records = parse_model_pricing(data, model_ids)
        available = {record["model_id"] for record in records}
        if missing is not None:
            missing.extend(f"Model price: {model_id}" for model_id in model_ids if model_id not in available)
        return format_model_pricing(records)
    except Exception as e:
        print(f"  ⚠ AI model pricing unavailable: {e}")
        return None


@dataclass(frozen=True)
class MarketQuote:
    price: float
    change: float | None
    as_of: str


def get_crypto_prices() -> dict[str, MarketQuote]:
    prices = {}
    for symbol, display_name in CRYPTO_SYMBOLS:
        try:
            hist = yf.Ticker(symbol).history(period="5d", timeout=10)
            if hist.empty:
                continue
            price = float(hist["Close"].iloc[-1])
            if not math.isfinite(price) or price <= 0:
                continue
            change = None
            if len(hist) >= 2:
                previous = float(hist["Close"].iloc[-2])
                if math.isfinite(previous) and previous > 0:
                    change = (price - previous) / previous * 100
            prices[display_name] = MarketQuote(price, change, hist.index[-1].isoformat())
        except Exception as e:
            print(f"  ⚠ Failed to fetch {display_name}: {e}")
    return prices


def get_stock_prices(cfg: Config) -> dict[str, MarketQuote]:
    prices = {}
    if not cfg.twelvedata_api_key:
        print("  PH stocks disabled: TWELVEDATA_API_KEY not set")
        return prices
    for symbol, display_name in STOCK_SYMBOLS:
        try:
            url = f"{TWELVEDATA_BASE}/quote?symbol={symbol}&exchange=PSE&apikey={cfg.twelvedata_api_key}"
            data = fetch_json(url, cfg.max_retries, cfg.retry_delay)
            if data.get("status") == "error":
                raise ValueError(data.get("message", "unknown error"))
            price = float(data["close"])
            if not math.isfinite(price) or price <= 0:
                raise ValueError("invalid price")
            raw_change = data.get("percent_change")
            change = float(raw_change) if raw_change is not None else None
            if change is not None and not math.isfinite(change):
                change = None
            as_of = data.get("datetime")
            if as_of:
                as_of = f"{as_of} {data.get('exchange_timezone') or 'timezone unknown'}"
            else:
                as_of = "timestamp unavailable"
            prices[display_name] = MarketQuote(price, change, as_of)
        except Exception as e:
            # Never include the API key in log output if a provider echoes the URL.
            print(f"  ⚠ Failed to fetch {display_name}: {str(e).replace(cfg.twelvedata_api_key, '[redacted]')}")
    return prices


def build_market_section(crypto: dict, stocks: dict) -> str:
    if not crypto and not stocks:
        return ""
    parts = ["", "━━━━━━━━━━━━━━━━━━━━━━━━", "📈  MARKET UPDATE", "━━━━━━━━━━━━━━━━━━━━━━━━"]
    for title, prices, order, currency, timestamp_label in (
        ("🪙  CRYPTO — change vs previous daily close", crypto, CRYPTO_ORDER, "$", "Daily bar"),
        ("🇵🇭  PSE STOCKS", stocks, STOCK_ORDER, "₱", "As of"),
    ):
        if not prices:
            continue
        parts += ["", title]
        for name in order:
            if name not in prices:
                continue
            record = prices[name]
            change = "change unavailable" if record.change is None else (
                f"{'▲' if record.change >= 0 else '▼'}{abs(record.change):.1f}%"
            )
            parts.append(f"  {name}  •  {currency}{record.price:,.2f}  ({change})")
            parts.append(f"    {timestamp_label}: {record.as_of}")
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
    missing: list[str] | None = None,
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

    if missing:
        parts += ["", "Missing data: " + "; ".join(missing)]

    parts += [
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
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
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
            server.login(cfg.sender_email, cfg.sender_password)
            refused = server.sendmail(cfg.sender_email, list(cfg.recipients), msg.as_string())
            if refused:
                raise RuntimeError(
                    "Email partially accepted; refused recipients: " + ", ".join(refused)
                    + ". Do not resend to all recipients."
                )
        print(f"✅ Email sent to {', '.join(cfg.recipients)}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        fallback_path = f"email_fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(fallback_path, "w", encoding="utf-8") as f:
            f.write(f"Subject: {subject}\n\n{body}")
            if "partially accepted" in str(e):
                f.write(f"\n\nDelivery warning: {e}\n")
        print(f"📝 Email saved to {fallback_path}")
        return False


def write_run_summary(missing: list[str], delivery: str) -> None:
    summary = f"Daily brief — {delivery}\n\n"
    summary += "Missing data: " + ("; ".join(missing) if missing else "none") + "\n"
    print(summary)
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        try:
            with open(path, "a", encoding="utf-8") as output:
                output.write(summary)
        except OSError as e:
            print(f"Warning: could not write job summary: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Send daily brief email")
    parser.add_argument("--dry-run", action="store_true", help="Print email to stdout instead of sending")
    parser.add_argument("--local", action="store_true", help="Load .env file from current directory")
    parser.add_argument("--pricing", action="store_true", help="Include model prices on any day")
    args = parser.parse_args()

    if args.local:
        load_env()

    cfg = load_config(require_credentials=not args.dry_run)
    day_str, date_str = get_date_info(cfg.timezone)
    weather = get_weather(cfg)
    quote   = get_quote(cfg)
    news            = get_news(cfg)
    seen_news: set[str] = set()
    ai_news         = get_ai_news(cfg, seen_news)
    google_ai_news  = get_google_ai_news(cfg, seen_news)
    missing = []
    include_pricing = args.pricing or pricing_due(cfg.timezone)
    model_pricing = get_model_pricing(cfg, missing) if include_pricing else None
    for label, available in (
        ("Weather", not weather.startswith("Weather unavailable")),
        ("Quote", not quote.startswith("Quote unavailable")),
        ("Headlines", news),
        ("AI model news", ai_news),
        ("AI top stories", google_ai_news),
    ):
        if not available:
            missing.append(label)
    if include_pricing and not model_pricing and not any(item.startswith("Model price:") for item in missing):
        missing.append("Model pricing")

    print("Fetching crypto prices...")
    crypto = get_crypto_prices()
    print(f"  fetched {len(crypto)}")
    print("Fetching PH stock prices...")
    stocks = get_stock_prices(cfg)
    print(f"  fetched {len(stocks)}")
    missing.extend(f"Crypto: {name}" for name in CRYPTO_ORDER if name not in crypto)
    if cfg.twelvedata_api_key:
        missing.extend(f"PH stocks: {name}" for name in STOCK_ORDER if name not in stocks)

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
        missing,
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
        write_run_summary(missing, "Preview — not sent")
        return

    delivered = send_email(cfg, subject, body)
    write_run_summary(missing, "Sent (SMTP accepted all recipients)" if delivered else "Delivery failed or partial; inspect fallback before resending")
    if not delivered:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
