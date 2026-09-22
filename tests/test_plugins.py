import io
import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from plugins.ai_pricing import AIPricingPlugin, AI_GENERAL_NEWS_FEED_URL, AI_MODEL_NEWS_FEED_URL  # noqa: E402
from plugins.base import PluginContext  # noqa: E402
from plugins.crypto import CryptoPlugin, MarketQuote  # noqa: E402
from plugins.headlines import HeadlinesPlugin  # noqa: E402
from plugins.ph_stocks import PHStocksPlugin  # noqa: E402
from plugins.quote import QuotePlugin  # noqa: E402
from plugins.weather import WeatherPlugin  # noqa: E402


class PluginTests(unittest.TestCase):
    def context(self, *, json_response=None, text_response=None, settings=None, schedules=None, now=None, api_key=""):
        def fetch_json(url, *_):
            if callable(json_response):
                return json_response(url)
            return json_response

        def fetch_text(url, *_):
            if callable(text_response):
                return text_response(url)
            return text_response

        return PluginContext(
            settings=settings or {},
            schedules=schedules or {},
            timezone="Asia/Manila",
            lat=11.6083,
            lon=125.4358,
            city="Borongan City, Eastern Samar",
            max_retries=0,
            retry_delay=0,
            now=now or datetime(2026, 9, 21, 8, 0),
            fetch_json=fetch_json,
            fetch_text=fetch_text,
            secrets={"TWELVEDATA_API_KEY": api_key},
        )

    def test_weather_fetch_and_render(self):
        context = self.context(json_response={
            "current": {
                "temperature_2m": 26.9,
                "relative_humidity_2m": 85,
                "windspeed_10m": 2.3,
                "weathercode": 0,
            }
        })
        result = WeatherPlugin().fetch(context)
        self.assertTrue(result.ok)
        rendered = WeatherPlugin().render(result.data)
        self.assertIn("WEATHER — Borongan City, Eastern Samar", rendered)
        self.assertIn("Clear sky", rendered)
        self.assertIn("26.9°C", rendered)

    def test_quote_and_headlines_render_as_sections(self):
        quote_context = self.context(json_response=[{"q": "Keep going", "a": "Author"}])
        quote = QuotePlugin()
        quote_result = quote.fetch(quote_context)
        self.assertTrue(quote_result.ok)
        self.assertIn("QUOTE OF THE DAY", quote.render(quote_result.data))

        headlines_context = self.context(text_response=(
            "<rss><channel>"
            "<item><title>One</title><link>https://example.com/1</link></item>"
            "<item><title>Two</title><link>https://example.com/2</link></item>"
            "</channel></rss>"
        ))
        headlines = HeadlinesPlugin()
        headlines_result = headlines.fetch(headlines_context)
        self.assertTrue(headlines_result.ok)
        self.assertIn("https://example.com/1", headlines.render(headlines_result.data))

    def test_ai_plugin_deduplicates_feeds_and_honors_schedule(self):
        rss = {
            AI_MODEL_NEWS_FEED_URL: (
                "<rss><channel><item>"
                "<title>OpenAI releases a new GPT model</title>"
                "<link>https://example.com/model</link><source>Model News</source>"
                "</item></channel></rss>"
            ),
            AI_GENERAL_NEWS_FEED_URL: (
                "<rss><channel>"
                "<item><title>OpenAI releases a new GPT model</title>"
                "<link>https://example.com/duplicate</link></item>"
                "<item><title>AI policy discussion</title>"
                "<link>https://example.com/policy</link></item>"
                "</channel></rss>"
            ),
        }
        pricing = {"data": [{
            "id": "openai/o3",
            "pricing": {"prompt": "0.000002", "completion": "0.000008"},
        }]}
        context = self.context(
            text_response=lambda url: rss[url],
            json_response=pricing,
            settings={"AI_MODEL_IDS": "openai/o3"},
            schedules={"ai_pricing": ("monday",)},
        )
        result = AIPricingPlugin().fetch(context)
        self.assertTrue(result.ok)
        self.assertIn("pricing", result.data)
        self.assertIn("OpenAI releases a new GPT model", result.data["model_news"] or "")
        self.assertNotIn("OpenAI releases a new GPT model", result.data["general_news"])
        self.assertIn("AI MODEL PRICING", AIPricingPlugin().render(result.data))

    def test_ai_plugin_skips_pricing_off_schedule(self):
        calls = []
        context = self.context(
            text_response="<rss><channel><item><title>AI story</title><link>https://example.com</link></item></channel></rss>",
            json_response=lambda url: calls.append(url),
            schedules={"ai_pricing": ("monday",)},
            now=datetime(2026, 9, 20, 8, 0),
        )
        result = AIPricingPlugin().fetch(context)
        self.assertTrue(result.ok)
        self.assertNotIn("pricing", result.data)
        self.assertEqual(calls, [])

    def test_market_plugins_return_partial_missing_data(self):
        crypto = CryptoPlugin()
        with patch("plugins.crypto.fetch_crypto_prices", return_value={
            "BTC": MarketQuote(100.0, 1.0, "2026-09-21T00:00:00+00:00")
        }):
            result = crypto.fetch(self.context())
        self.assertTrue(result.ok)
        self.assertIn("Crypto: ETH", result.missing)
        self.assertIn("BTC", crypto.render(result.data))

        stock = PHStocksPlugin()
        stock_context = self.context(api_key="secret", json_response={
            "close": "145.50",
            "percent_change": "0.5",
            "datetime": "2026-09-21",
            "exchange_timezone": "Asia/Manila",
        })
        with patch("plugins.ph_stocks.STOCK_SYMBOLS", [("BDO", "BDO")]), \
             patch("plugins.ph_stocks.STOCK_ORDER", ["BDO"]):
            result = stock.fetch(stock_context)
        self.assertTrue(result.ok)
        self.assertIn("PSE STOCKS", stock.render(result.data))


if __name__ == "__main__":
    unittest.main()
