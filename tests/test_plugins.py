import io
import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from plugins.ai_pricing import AIPricingPlugin, AI_GENERAL_NEWS_FEED_URL, AI_MODEL_NEWS_FEED_URL  # noqa: E402
from plugins.air_quality import AirQualityPlugin  # noqa: E402
from plugins.arxiv import ArxivPlugin  # noqa: E402
from plugins.base import PluginContext  # noqa: E402
from plugins.crypto import CryptoPlugin, MarketQuote  # noqa: E402
from plugins.formatting import shorten_url  # noqa: E402
from plugins.hackernews import HackerNewsPlugin, HN_ITEM_URL, HN_TOP_STORIES_URL  # noqa: E402
from plugins.fx import FXPlugin  # noqa: E402
from plugins.devto import DEVTO_ARTICLES_URL, DevToPlugin  # noqa: E402
from plugins.lobsters import LOBSTERS_FEED_URL, LobstersPlugin  # noqa: E402
from plugins.openalex import OpenAlexPlugin  # noqa: E402
from plugins.headlines import HeadlinesPlugin  # noqa: E402
from plugins.ph_stocks import PHStocksPlugin  # noqa: E402
from plugins.quote import QuotePlugin  # noqa: E402
from plugins.weather import WeatherPlugin  # noqa: E402
from plugins.uv_index import UVIndexPlugin  # noqa: E402
from plugins.sunrise import SunrisePlugin  # noqa: E402
from plugins.public_holiday import PublicHolidayPlugin  # noqa: E402


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

    def test_public_holiday_finds_today(self):
        result = PublicHolidayPlugin().fetch(self.context(
            json_response=[{"date": "2026-09-21", "localName": "A Holiday"}],
            settings={"HOLIDAY_COUNTRY": "PH"},
            now=datetime(2026, 9, 21, 8, 0),
        ))
        self.assertTrue(result.ok)
        self.assertEqual(result.data.value, "A Holiday")
        self.assertIn("A Holiday", PublicHolidayPlugin().render(result.data))

    def test_sunrise_normalizes_daily_values(self):
        result = SunrisePlugin().fetch(self.context(json_response={
            "daily": {
                "sunrise": ["2026-09-23T05:30"],
                "sunset": ["2026-09-23T17:45"],
            },
        }))
        self.assertTrue(result.ok)
        self.assertEqual(result.data[0].label, "Sunrise")
        self.assertIn("Sunset: 2026-09-23T17:45", SunrisePlugin().render(result.data))

    def test_fx_normalizes_configured_rate(self):
        result = FXPlugin().fetch(self.context(
            json_response={"rates": {"PHP": 58.25}},
            settings={"FX_BASE": "USD", "FX_QUOTE": "PHP"},
        ))
        self.assertTrue(result.ok)
        self.assertEqual(result.data.label, "USD/PHP")
        self.assertIn("58.25", FXPlugin().render(result.data))

    def test_uv_index_normalizes_key_value(self):
        result = UVIndexPlugin().fetch(self.context(json_response={"current": {"uv_index": 6.2}}))
        self.assertTrue(result.ok)
        self.assertEqual(result.data.value, 6.2)
        self.assertIn("UV index: 6.2", UVIndexPlugin().render(result.data))

    def test_air_quality_normalizes_key_values(self):
        result = AirQualityPlugin().fetch(self.context(json_response={
            "current": {"us_aqi": 22, "pm2_5": 4.5},
        }))
        self.assertTrue(result.ok)
        self.assertEqual(result.data[0].label, "US AQI")
        self.assertIn("PM2.5: 4.5", AirQualityPlugin().render(result.data))

    def test_openalex_normalizes_authors_and_citations(self):
        payload = {"results": [{
            "title": "A research paper",
            "doi": "https://doi.org/10.1234/example",
            "authorships": [{"author": {"display_name": "Researcher"}}],
            "cited_by_count": 12,
        }]}
        result = OpenAlexPlugin().fetch(self.context(json_response=payload))
        self.assertTrue(result.ok)
        self.assertEqual(result.data[0].title, "A research paper")
        self.assertIn("Authors: Researcher", result.data[0].details)
        self.assertIn("Citations: 12", result.data[0].details)

    def test_arxiv_normalizes_authors_and_abstract(self):
        xml = """<feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <id>https://arxiv.org/abs/1234.5678</id>
            <title>A useful paper</title>
            <author><name>First Author</name></author>
            <author><name>Second Author</name></author>
            <summary>A short abstract for the paper.</summary>
          </entry>
        </feed>"""
        result = ArxivPlugin().fetch(self.context(text_response=xml))
        self.assertTrue(result.ok)
        self.assertEqual(result.data[0].title, "A useful paper")
        self.assertIn("Authors: First Author, Second Author", result.data[0].details)
        self.assertIn("Abstract: A short abstract", result.data[0].details[1])
        self.assertIn("https://arxiv.org/abs/1234.5678", ArxivPlugin().render(result.data))

    def test_lobsters_normalizes_ranked_items(self):
        context = self.context(text_response=(
            "<rss><channel>"
            "<item><title>One</title><link>https://lobste.rs/s/one</link></item>"
            "<item><title>Two</title><link>https://lobste.rs/s/two</link></item>"
            "</channel></rss>"
        ))
        result = LobstersPlugin().fetch(context)
        self.assertTrue(result.ok)
        self.assertEqual(result.data[0].title, "One")
        self.assertIn("LOBSTERS", LobstersPlugin().render(result.data))

    def test_devto_normalizes_tags_and_links(self):
        context = self.context(json_response=[{
            "title": "A Dev article",
            "url": "https://dev.to/example/article",
            "tag_list": ["python", "webdev"],
        }])
        result = DevToPlugin().fetch(context)
        self.assertTrue(result.ok)
        self.assertEqual(result.data[0].details, ("Tags: python, webdev",))
        self.assertIn("https://dev.to/example/article", DevToPlugin().render(result.data))

    def test_hackernews_normalizes_ranked_items(self):
        payloads = {
            HN_TOP_STORIES_URL: [101, 102],
            HN_ITEM_URL.format(story_id=101): {
                "type": "story",
                "title": "First story",
                "url": "https://example.com/first",
                "score": 42,
            },
            HN_ITEM_URL.format(story_id=102): {
                "type": "story",
                "title": "Second story",
                "score": 10,
            },
        }
        context = self.context(json_response=lambda url: payloads[url])
        result = HackerNewsPlugin().fetch(context)
        self.assertTrue(result.ok)
        self.assertEqual(result.data[0].title, "First story")
        self.assertEqual(result.data[0].details, ("Score: 42",))
        self.assertIn("HACKER NEWS", HackerNewsPlugin().render(result.data))
        self.assertIn("news.ycombinator.com/item?id=102", result.data[1].link)

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

    def test_ai_links_are_shortened_for_readable_email(self):
        long_url = "https://news.google.com/rss/articles/" + ("token" * 30) + "?oc=5"
        shortened = shorten_url(long_url)
        self.assertLessEqual(len(shortened), 72)
        self.assertTrue(shortened.startswith("https://news.google.com/"))
        self.assertTrue(shortened.endswith("…?oc=5"))

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
        self.assertTrue(any(item.title == "OpenAI releases a new GPT model" for item in result.data["model_news"]))
        self.assertFalse(any(item.title == "OpenAI releases a new GPT model" for item in result.data["general_news"]))
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
