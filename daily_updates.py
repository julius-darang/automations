import argparse
import json
import os
import smtplib
import sys
import time
import urllib.request
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


@dataclass(frozen=True)
class Config:
    sender_email: str
    sender_password: str
    receiver_email: str
    twelvedata_api_key: str = ""
    timezone: str = "Asia/Manila"


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


def load_config() -> Config:
    missing = [k for k in ("SENDER_EMAIL", "SENDER_PASSWORD", "RECEIVER_EMAIL") if k not in os.environ]
    if missing:
        print(f"FATAL: Missing environment variables: {', '.join(missing)}")
        sys.exit(1)
    return Config(
        sender_email=os.environ["SENDER_EMAIL"],
        sender_password=os.environ["SENDER_PASSWORD"],
        receiver_email=os.environ["RECEIVER_EMAIL"],
        twelvedata_api_key=os.environ.get("TWELVEDATA_API_KEY", ""),
    )


TWELVEDATA_BASE = "https://api.twelvedata.com"


def get_retry_json(url: str, max_retries: int = 2, delay: int = 3) -> dict:
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
            data = get_retry_json(url)
            if "status" in data and data["status"] == "error":
                raise Exception(data.get("message", "unknown error"))
            price = float(data["close"])
            change_pct = float(data.get("percent_change", 0))
            prices[display_name] = (price, change_pct)
        except Exception as e:
            print(f"  ⚠ Failed to fetch {display_name}: {e}")
    return prices


def build_body(prices: dict, day_str: str, date_str: str) -> str:
    parts = [
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📈  MARKET UPDATE — {day_str}, {date_str}",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    crypto = prices.get("crypto", {})
    if crypto:
        parts += ["", "🪙  CRYPTO"]
        for name in CRYPTO_ORDER:
            if name not in crypto:
                continue
            price, change = crypto[name]
            arrow = "▲" if change >= 0 else "▼"
            parts.append(f"  {name}  •  ${price:,.2f}  ({arrow}{abs(change):.1f}%)")

    stocks = prices.get("stocks", {})
    if stocks:
        parts += ["", "━━━━━━━━━━━━━━━━━━━━━━━━", "", "🇵🇭  PSE STOCKS"]
        for name in STOCK_ORDER:
            if name not in stocks:
                continue
            price, change = stocks[name]
            arrow = "▲" if change >= 0 else "▼"
            parts.append(f"  {name}  •  ₱{price:,.2f}  ({arrow}{abs(change):.1f}%)")

    parts += ["", "━━━━━━━━━━━━━━━━━━━━━━━━", "", "— Your Market Agent"]

    return "\n".join(parts)


def send_email(cfg: Config, subject: str, body: str) -> bool:
    msg = MIMEMultipart()
    msg["From"] = cfg.sender_email
    msg["To"] = cfg.receiver_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(cfg.sender_email, cfg.sender_password)
            server.sendmail(cfg.sender_email, cfg.receiver_email, msg.as_string())
        print(f"✅ Email sent to {cfg.receiver_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        fallback_path = f"market_fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(fallback_path, "w") as f:
            f.write(f"Subject: {subject}\n\n{body}")
        print(f"📝 Email saved to {fallback_path}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Send market update email")
    parser.add_argument("--dry-run", action="store_true", help="Print email to stdout instead of sending")
    parser.add_argument("--local", action="store_true", help="Load .env file from current directory")
    args = parser.parse_args()

    if args.local:
        load_env()

    cfg = load_config()
    now = datetime.now(ZoneInfo(cfg.timezone))
    day_str = now.strftime("%A")
    date_str = now.strftime("%B %d, %Y")

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

    prices = {"crypto": crypto, "stocks": stocks}

    subject = f"Market Update — {day_str}, {date_str}"
    body = build_body(prices, day_str, date_str)

    if args.dry_run:
        print(f"\n{'=' * 60}")
        print(f"Subject: {subject}")
        print(f"{'=' * 60}")
        print(body)
        return

    send_email(cfg, subject, body)


if __name__ == "__main__":
    main()
