import argparse
import json
import os
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


def build_body(cfg: Config, day_str: str, date_str: str, weather: str, quote: str, news: str | None, market: str = "") -> str:
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
    news    = get_news(cfg)

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
    body    = build_body(cfg, day_str, date_str, weather, quote, news, market)

    print(f"🌤  {weather}")
    print(f"💬  {quote[:60]}...")
    if news:
        print(f"📰  Headline: {news.split('•')[1].strip() if '•' in news else 'loaded'}")

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
