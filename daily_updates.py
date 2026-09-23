from __future__ import annotations

import argparse
import html as html_lib
import re
import os
import smtplib
import sys
from dataclasses import dataclass
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Mapping
from zoneinfo import ZoneInfo

import yaml

from plugins import PluginRegistryError, discover_plugins, instantiate_plugins
from plugins.base import BasePlugin, FetchResult, PluginBlock, PluginContext
from plugins.formatting import SEPARATOR, shorten_url
from plugins.http import fetch_json as _http_fetch_json
from plugins.http import fetch_text as _http_fetch_text
from plugins.legacy import (
    AI_GENERAL_NEWS_FEED_URL,
    AI_MODEL_INPUT_TOKENS,
    AI_MODEL_NEWS_FEED_URL,
    AI_MODEL_OUTPUT_TOKENS,
    AI_NEWS_ADVANCE_ALIASES,
    AI_NEWS_FEED_URL,
    AI_NEWS_LIMIT,
    AI_NEWS_PROVIDER_ALIASES,
    CRYPTO_ORDER,
    CRYPTO_SYMBOLS,
    DEFAULT_MODEL_IDS,
    MarketQuote,
    OPENROUTER_MODELS_URL,
    STOCK_ORDER,
    STOCK_SYMBOLS,
    TWELVEDATA_BASE,
    build_market_section,
    fetch_crypto_prices,
    fetch_model_pricing,
    fetch_stock_prices,
    format_model_pricing,
    format_token_price,
    get_ai_news as legacy_get_ai_news,
    get_google_ai_news as legacy_get_google_ai_news,
    get_google_news as legacy_get_google_news,
    get_model_pricing as legacy_get_model_pricing,
    get_news as legacy_get_news,
    get_quote as legacy_get_quote,
    get_weather as legacy_get_weather,
    is_ai_model_advance,
    normalize_news_text,
    parse_model_pricing,
    pricing_due,
    yf,
)


RECIPIENTS_FILE = Path(__file__).with_name("recipients.txt")
PLUGIN_CONFIG_FILE = Path(__file__).with_name("plugins.yaml")


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


@dataclass(frozen=True)
class PluginFileConfig:
    enabled: tuple[str, ...]
    settings: Mapping[str, Any]
    schedules: Mapping[str, tuple[str, ...]]


# These wrappers keep the old import surface available while the implementation
# lives in plugins. They also make transport calls straightforward to patch in
# compatibility tests and local development.
def fetch_json(url: str, max_retries: int = 2, delay: int = 3) -> dict | list:
    return _http_fetch_json(url, max_retries, delay)


def fetch_text(url: str, max_retries: int = 2, delay: int = 3) -> str:
    return _http_fetch_text(url, max_retries, delay)


def load_env(path: str = ".env") -> None:
    env_file = Path(path)
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(key.strip(), value)


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


def _setting(settings: Mapping[str, Any] | None, name: str, default: Any) -> Any:
    if name in os.environ:
        return os.environ[name]
    if settings is not None and name in settings:
        return settings[name]
    return default


def load_config(
    require_credentials: bool = True,
    settings: Mapping[str, Any] | None = None,
) -> Config:
    recipients = load_recipients()
    missing = [
        key for key in ("SENDER_EMAIL", "SENDER_PASSWORD") if not os.environ.get(key)
    ]
    if not recipients:
        missing.append("recipients.txt/RECIPIENT_EMAILS/RECEIVER_EMAIL")
    if require_credentials and missing:
        print(f"FATAL: Missing environment variables or recipient file: {', '.join(missing)}")
        sys.exit(1)

    try:
        lat = float(_setting(settings, "LAT", "11.6083"))
        lon = float(_setting(settings, "LON", "125.4358"))
        max_retries = int(_setting(settings, "MAX_RETRIES", 2))
        retry_delay = int(_setting(settings, "RETRY_DELAY", 3))
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid numeric settings: {error}") from error

    timezone = str(_setting(settings, "TIMEZONE", "Asia/Manila"))
    try:
        ZoneInfo(timezone)
    except Exception as error:
        raise ValueError(f"Invalid TIMEZONE setting: {timezone}") from error

    return Config(
        sender_email=os.environ.get("SENDER_EMAIL", ""),
        sender_password=os.environ.get("SENDER_PASSWORD", ""),
        recipients=recipients,
        twelvedata_api_key=os.environ.get("TWELVEDATA_API_KEY", ""),
        timezone=timezone,
        lat=lat,
        lon=lon,
        city=str(_setting(settings, "CITY", "Borongan City, Eastern Samar")),
        max_retries=max_retries,
        retry_delay=retry_delay,
    )


def _normalise_schedule(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, list | tuple):
        values = value
    else:
        raise ValueError("schedule values must be a weekday string or list")
    result = tuple(str(item).strip().casefold() for item in values if str(item).strip())
    if not result:
        raise ValueError("schedule values cannot be empty")
    valid = {"always", "daily", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
    invalid = sorted(set(result) - valid)
    if invalid:
        raise ValueError(f"invalid schedule day(s): {', '.join(invalid)}")
    return result


def load_plugin_config(path: Path | str = PLUGIN_CONFIG_FILE) -> PluginFileConfig:
    path = Path(path)
    try:
        raw = yaml.safe_load(path.read_text()) or {}
    except FileNotFoundError as error:
        raise ValueError(f"Plugin config not found: {path}") from error
    except yaml.YAMLError as error:
        raise ValueError(f"Invalid YAML in {path}: {error}") from error

    if not isinstance(raw, dict):
        raise ValueError("Plugin config must contain a mapping")
    enabled_raw = raw.get("enabled")
    if not isinstance(enabled_raw, list) or not all(isinstance(name, str) for name in enabled_raw):
        raise ValueError("plugins.yaml 'enabled' must be a list of plugin names")
    enabled = tuple(name.strip() for name in enabled_raw)
    if not all(enabled):
        raise ValueError("plugins.yaml 'enabled' cannot contain blank names")
    if len(enabled) != len(set(enabled)):
        raise ValueError("plugins.yaml 'enabled' cannot contain duplicates")

    settings_raw = raw.get("settings", {})
    if not isinstance(settings_raw, dict):
        raise ValueError("plugins.yaml 'settings' must be a mapping")
    settings = dict(settings_raw)
    # Environment variables are the runtime override. Include known optional
    # values even when a fork has not listed them in its YAML file.
    for name in (
        "CITY", "LAT", "LON", "TIMEZONE", "AI_MODEL_IDS",
        "FX_BASE", "FX_QUOTE", "HOLIDAY_COUNTRY", "MAX_RETRIES", "RETRY_DELAY",
    ):
        if name in os.environ:
            settings[name] = os.environ[name]

    schedules_raw = raw.get("schedules", {})
    if not isinstance(schedules_raw, dict):
        raise ValueError("plugins.yaml 'schedules' must be a mapping")
    schedules = {str(name): _normalise_schedule(value) for name, value in schedules_raw.items()}

    try:
        available = discover_plugins()
    except (ImportError, PluginRegistryError) as error:
        raise ValueError(f"Could not discover plugins: {error}") from error
    unknown = sorted(set(enabled) - set(available))
    if unknown:
        valid = ", ".join(sorted(available))
        raise ValueError(f"Unknown plugin name(s): {', '.join(unknown)}. Valid names: {valid}")
    unknown_schedules = sorted(set(schedules) - set(available))
    if unknown_schedules:
        valid = ", ".join(sorted(available))
        raise ValueError(f"Unknown schedule plugin(s): {', '.join(unknown_schedules)}. Valid names: {valid}")

    return PluginFileConfig(enabled=enabled, settings=settings, schedules=schedules)


def get_date_info(tz: str) -> tuple[str, str]:
    now = datetime.now(ZoneInfo(tz))
    return now.strftime("%A"), now.strftime("%B %d, %Y")


def _plugin_context(
    cfg: Config,
    settings: Mapping[str, Any] | None = None,
    schedules: Mapping[str, tuple[str, ...]] | None = None,
    force_pricing: bool = False,
    now: datetime | None = None,
) -> PluginContext:
    merged_settings = dict(settings or {})
    for name in (
        "CITY", "LAT", "LON", "TIMEZONE", "AI_MODEL_IDS",
        "FX_BASE", "FX_QUOTE", "HOLIDAY_COUNTRY", "MAX_RETRIES", "RETRY_DELAY",
    ):
        if name in os.environ:
            merged_settings[name] = os.environ[name]
    return PluginContext(
        settings=merged_settings,
        schedules=dict(schedules or {}),
        timezone=cfg.timezone,
        lat=cfg.lat,
        lon=cfg.lon,
        city=cfg.city,
        max_retries=cfg.max_retries,
        retry_delay=cfg.retry_delay,
        now=now or datetime.now(ZoneInfo(cfg.timezone)),
        force_pricing=force_pricing,
        fetch_json=fetch_json,
        fetch_text=fetch_text,
        pricing_due=pricing_due,
        secrets={"TWELVEDATA_API_KEY": cfg.twelvedata_api_key},
    )


# Compatibility helpers for callers that imported the former monolithic API.
def get_weather(cfg: Config) -> str:
    return legacy_get_weather(_plugin_context(cfg))


def get_quote(cfg: Config) -> str:
    return legacy_get_quote(_plugin_context(cfg))


def get_news(cfg: Config) -> str | None:
    return legacy_get_news(_plugin_context(cfg))


def get_ai_news(cfg: Config, seen: set[str] | None = None) -> str | None:
    return legacy_get_ai_news(_plugin_context(cfg), seen)


def get_google_ai_news(cfg: Config, seen: set[str] | None = None) -> str | None:
    return legacy_get_google_ai_news(_plugin_context(cfg), seen)


def get_google_news(
    cfg: Config,
    feed_url: str,
    model_only: bool = False,
    seen: set[str] | None = None,
) -> str | None:
    return legacy_get_google_news(_plugin_context(cfg), feed_url, model_only=model_only, seen=seen)


def get_model_pricing(cfg: Config, missing: list[str] | None = None) -> str | None:
    return legacy_get_model_pricing(_plugin_context(cfg), missing)


def get_crypto_prices() -> dict[str, MarketQuote]:
    return fetch_crypto_prices()


def get_stock_prices(cfg: Config) -> dict[str, MarketQuote]:
    return fetch_stock_prices(_plugin_context(cfg))


def run_plugins(
    plugins: list[BasePlugin],
    context: PluginContext,
) -> tuple[list[PluginBlock], list[str]]:
    blocks: list[PluginBlock] = []
    missing: list[str] = []

    def add_missing(labels: tuple[str, ...] | list[str]) -> None:
        for label in labels:
            if label and label not in missing:
                missing.append(label)

    for plugin in plugins:
        try:
            if not plugin.should_run(context):
                print(f"  - {plugin.display_name} skipped")
                continue
        except Exception as error:
            print(f"  ⚠ {plugin.display_name} schedule check failed: {error}")
            add_missing([plugin.display_name])
            continue

        try:
            result = plugin.fetch(context)
        except Exception as error:  # the contract forbids this, but isolate bad plugins anyway
            print(f"  ⚠ {plugin.display_name} failed unexpectedly: {error}")
            add_missing([plugin.display_name])
            continue

        if not isinstance(result, FetchResult):
            print(f"  ⚠ {plugin.display_name} returned an invalid fetch result")
            add_missing([plugin.display_name])
            continue

        add_missing(result.missing)
        if result.ok and result.error:
            print(f"  ⚠ {plugin.display_name} partial: {result.error}")
        if not result.ok:
            if result.error:
                print(f"  ⚠ {plugin.display_name} unavailable: {result.error}")
            add_missing(result.missing or [plugin.display_name])
            continue

        try:
            text = plugin.render(result.data)
        except Exception as error:
            print(f"  ⚠ {plugin.display_name} render failed: {error}")
            add_missing([plugin.display_name])
            continue
        if not isinstance(text, str) or not text.strip():
            print(f"  ⚠ {plugin.display_name} rendered no content")
            add_missing([plugin.display_name])
            continue

        blocks.append(PluginBlock(
            name=plugin.name,
            display_name=plugin.display_name,
            text=text,
            group=plugin.section_group,
        ))
        print(f"  ✓ {plugin.display_name} loaded")

    return blocks, missing


def resolve_plugins(config: PluginFileConfig, selected: str | None = None) -> list[BasePlugin]:
    instances = instantiate_plugins()
    if selected is not None:
        if selected not in instances:
            valid = ", ".join(sorted(instances))
            raise ValueError(f"Unknown plugin name: {selected}. Valid names: {valid}")
        return [instances[selected]]
    return [instances[name] for name in config.enabled]


_URL_PATTERN = re.compile(r"https?://[^\s<>]+")


def _shorten_urls(text: str) -> str:
    return _URL_PATTERN.sub(lambda match: shorten_url(match.group(0)), text)


_EMAIL_HEADING_PREFIXES = (
    "🌤", "💬", "📰", "🤖", "🗞", "💵", "🪙", "📈", "📊",
    "🟠", "🔴", "🟣", "📚", "🔬", "🌫", "☀", "💱", "🌅", "🎉", "🇵🇭",
)
_EMAIL_CSS = """
body { margin:0; padding:24px 12px; background:#eaf1f8; color:#142c49; font:16px/1.6 Arial, Helvetica, sans-serif; }
a { color:#244ec9; }
.mail { max-width:620px; margin:0 auto; background:#fff; border:1px solid #c5d3e2; border-radius:16px; overflow:hidden; }
.mail-header { padding:28px 32px 22px; border-bottom:1px solid #e0e7ef; }
.mail-header h1 { margin:0; font-size:26px; line-height:1.2; letter-spacing:-.6px; }
.mail-date { margin:6px 0 0; color:#52677e; font-size:12px; }
.mail-content { padding:4px 32px 28px; }
.greeting { margin:20px 0 4px; font-size:17px; }
.mail-section { padding:20px 0; border-bottom:1px solid #e0e7ef; }
.mail-section h2 { margin:0 0 10px; color:#52677e; font-size:12px; font-weight:700; letter-spacing:.04em; text-transform:uppercase; }
.detail { margin:6px 0; }
.story-list { margin:0; padding-left:20px; }
.story-list li { margin:0 0 12px; padding-left:2px; }
.story-title { font-weight:600; text-decoration:none; }
.story-source { display:block; margin:2px 0 0; color:#52677e; font-size:11px; }
.story-link { display:inline-block; max-width:100%; overflow:hidden; text-overflow:ellipsis; vertical-align:bottom; white-space:nowrap; }
.market-row { margin:7px 0; font-size:14px; }
.mail-note { margin:20px 0 0; padding-top:14px; color:#52677e; font-size:11px; }
.mail-footer { padding:0 32px 28px; color:#52677e; font-size:12px; }
@media only screen and (max-width:640px) { body { padding:0; } .mail { border:0; border-radius:0; } .mail-header, .mail-content { padding-left:24px; padding-right:24px; } .mail-footer { padding-left:24px; padding-right:24px; } }
"""


def _linkify_html(text: str) -> str:
    parts: list[str] = []
    cursor = 0
    for match in _URL_PATTERN.finditer(text):
        raw_url = match.group(0)
        url = raw_url.rstrip(".,;:)")
        trailing = raw_url[len(url):]
        parts.append(html_lib.escape(text[cursor:match.start()]))
        if "…" in url:
            parts.append(html_lib.escape(url))
        else:
            escaped_url = html_lib.escape(url, quote=True)
            parts.append(f'<a class="story-link" href="{escaped_url}">{html_lib.escape(url)}</a>')
        parts.append(html_lib.escape(trailing))
        cursor = match.end()
    parts.append(html_lib.escape(text[cursor:]))
    return "".join(parts)


def _render_html_content(text: str) -> str:
    parts: list[str] = []
    list_open = False
    section_open = False
    story_title: str | None = None
    story_link: str | None = None
    story_details: list[str] = []

    def close_list() -> None:
        nonlocal list_open
        if list_open:
            parts.append("</ul>")
            list_open = False

    def flush_story() -> None:
        nonlocal list_open, story_title, story_link, story_details
        if story_title is None:
            return
        if not list_open:
            parts.append('<ul class="story-list">')
            list_open = True
        title_html = _linkify_html(story_title)
        if story_link and "…" not in story_link:
            title_html = (
                f'<a class="story-title" href="{html_lib.escape(story_link, quote=True)}">'
                f"{html_lib.escape(story_title)}</a>"
            )
        story_html = f"<li>{title_html}"
        for detail in story_details:
            story_html += f'<span class="story-source">{_linkify_html(detail)}</span>'
        parts.append(story_html + "</li>")
        story_title = None
        story_link = None
        story_details = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped == SEPARATOR:
            flush_story()
            continue
        if stripped.startswith("• "):
            flush_story()
            story_title = stripped[2:]
            continue
        if story_title is not None:
            if _URL_PATTERN.fullmatch(stripped):
                story_link = stripped
                continue
            if stripped.startswith(_EMAIL_HEADING_PREFIXES):
                flush_story()
            else:
                story_details.append(stripped)
                continue
        if stripped.startswith(_EMAIL_HEADING_PREFIXES):
            close_list()
            if section_open:
                parts.append("</section>")
            parts.append('<section class="mail-section">')
            parts.append(f"<h2>{_linkify_html(stripped)}</h2>")
            section_open = True
        else:
            close_list()
            if stripped.startswith("Source:") or _URL_PATTERN.fullmatch(stripped):
                parts.append(f'<span class="story-source">{_linkify_html(stripped)}</span>')
            elif " • " in stripped:
                parts.append(f'<p class="market-row">{_linkify_html(stripped)}</p>')
            else:
                parts.append(f'<p class="detail">{_linkify_html(stripped)}</p>')
    flush_story()
    close_list()
    if section_open:
        parts.append("</section>")
    return "\n".join(parts)


def _email_document(
    subject: str,
    date_text: str,
    content: str,
    missing: list[str] | tuple[str, ...] | None = None,
) -> str:
    missing_html = ""
    if missing:
        labels = html_lib.escape("; ".join(missing))
        missing_html = f'<p class="mail-note"><strong>Missing data:</strong> {labels}</p>'
    date_html = f'<p class="mail-date">{html_lib.escape(date_text)}</p>' if date_text else ""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html_lib.escape(subject or "Daily Brief")}</title>
  <style>{_EMAIL_CSS}</style>
</head>
<body>
  <main class="mail">
    <header class="mail-header">
      <h1>Daily Brief</h1>
      {date_html}
    </header>
    <div class="mail-content">
      <p class="greeting">Good afternoon!</p>
      {content}
      {missing_html}
    </div>
    <footer class="mail-footer">— Your Agent</footer>
  </main>
</body>
</html>"""


def build_html_email(body: str, subject: str = "Daily Brief") -> str:
    date_text = ""
    missing: list[str] = []
    content_lines: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if stripped in {"Good afternoon!", "— Your Agent", SEPARATOR}:
            continue
        if stripped.startswith("📅"):
            date_text = stripped.removeprefix("📅").strip()
        elif stripped.startswith("Missing data:"):
            missing = [item.strip() for item in stripped.removeprefix("Missing data:").split(";") if item.strip()]
        else:
            content_lines.append(line)
    return _email_document(subject, date_text, _render_html_content("\n".join(content_lines)), missing)


def build_plugin_body(
    cfg: Config,
    day_str: str,
    date_str: str,
    blocks: list[PluginBlock],
    missing: list[str] | None = None,
) -> str:
    parts = [
        "Good afternoon!",
        "",
        SEPARATOR,
        f"📅  {day_str}, {date_str}",
        SEPARATOR,
    ]
    index = 0
    has_content = False
    while index < len(blocks):
        block = blocks[index]
        if block.group == "market":
            market_blocks = []
            while index < len(blocks) and blocks[index].group == "market":
                market_blocks.append(blocks[index])
                index += 1
            if has_content:
                parts += ["", SEPARATOR, "", "📈  MARKET UPDATE", SEPARATOR]
            else:
                parts += ["", "📈  MARKET UPDATE", SEPARATOR]
            for market_block in market_blocks:
                parts += ["", market_block.text]
            has_content = True
            continue
        if has_content:
            parts += ["", SEPARATOR, "", block.text]
        else:
            parts += ["", block.text]
        has_content = True
        index += 1

    if missing:
        parts += ["", "Missing data: " + "; ".join(missing)]
    parts += ["", SEPARATOR, "", "— Your Agent"]
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
    """Compatibility renderer for the pre-plugin function signature."""
    parts = [
        "Good afternoon!",
        "",
        SEPARATOR,
        f"📅  {day_str}, {date_str}",
        SEPARATOR,
        "",
        f"🌤  WEATHER — {cfg.city}",
        weather,
        "",
        SEPARATOR,
        "",
        "💬  QUOTE OF THE DAY",
        quote,
    ]

    if news:
        parts += ["", SEPARATOR, "", "📰  HEADLINES", news]
    if ai_news:
        parts += ["", SEPARATOR, "", "🤖  AI MODEL ADVANCES", SEPARATOR, ai_news]
    if google_ai_news:
        parts += ["", SEPARATOR, "", "🗞️  AI TOP STORIES", SEPARATOR, google_ai_news]
    if model_pricing:
        parts += ["", SEPARATOR, "", "💵  AI MODEL PRICING", SEPARATOR, model_pricing]
    if market:
        parts += ["", market]
    if missing:
        parts += ["", "Missing data: " + "; ".join(missing)]
    parts += ["", SEPARATOR, "", "— Your Agent"]
    return "\n".join(parts)


def send_email(
    cfg: Config,
    subject: str,
    body: str,
    html_body: str | None = None,
) -> bool:
    msg = MIMEMultipart("alternative")
    msg["From"] = cfg.sender_email
    msg["To"] = ", ".join(cfg.recipients)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body or build_html_email(body, subject), "html", "utf-8"))

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
    except Exception as error:
        print(f"❌ Failed to send email: {error}")
        fallback_path = f"email_fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(fallback_path, "w", encoding="utf-8") as output:
            output.write(f"Subject: {subject}\n\n{body}")
            if "partially accepted" in str(error):
                output.write(f"\n\nDelivery warning: {error}\n")
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
        except OSError as error:
            print(f"Warning: could not write job summary: {error}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Send daily brief email")
    parser.add_argument("--dry-run", action="store_true", help="Print email to stdout instead of sending")
    parser.add_argument("--local", action="store_true", help="Load .env file from current directory")
    parser.add_argument("--pricing", action="store_true", help="Include model prices on any day")
    parser.add_argument("--plugin", help="Run one discovered plugin; requires --dry-run")
    parser.add_argument("--config", default=str(PLUGIN_CONFIG_FILE), help="Path to plugins.yaml")
    args = parser.parse_args()

    if args.plugin and not args.dry_run:
        parser.error("--plugin requires --dry-run")
    if args.local:
        load_env()

    try:
        plugin_config = load_plugin_config(args.config)
        plugins = resolve_plugins(plugin_config, args.plugin)
        if plugin_config.settings:
            cfg = load_config(
                require_credentials=not args.dry_run,
                settings=plugin_config.settings,
            )
        else:
            # Preserve the old call shape for callers that supply no YAML settings.
            cfg = load_config(require_credentials=not args.dry_run)
    except (ValueError, PluginRegistryError) as error:
        print(f"FATAL: {error}")
        raise SystemExit(2) from error

    day_str, date_str = get_date_info(cfg.timezone)
    context = _plugin_context(
        cfg,
        settings=plugin_config.settings,
        schedules=plugin_config.schedules,
        force_pricing=args.pricing,
    )
    blocks, missing = run_plugins(plugins, context)
    raw_body = build_plugin_body(cfg, day_str, date_str, blocks, missing)
    subject = f"Daily Brief & Market Update — {day_str}, {date_str}"
    body = _shorten_urls(raw_body)
    html_body = build_html_email(raw_body, subject)

    if args.dry_run:
        print(f"\n{'=' * 60}")
        print(f"Subject: {subject}")
        print(f"{'=' * 60}")
        print(body)
        write_run_summary(missing, "Preview — not sent")
        return

    delivered = send_email(cfg, subject, body, html_body)
    write_run_summary(
        missing,
        "Sent (SMTP accepted all recipients)" if delivered
        else "Delivery failed or partial; inspect fallback before resending",
    )
    if not delivered:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
