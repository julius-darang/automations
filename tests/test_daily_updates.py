import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import daily_updates  # noqa: E402


class DailyUpdatesTests(unittest.TestCase):
    def make_config(self, **overrides):
        values = {
            "sender_email": "sender@example.com",
            "sender_password": "app-password",
            "recipients": ("receiver@example.com",),
            "timezone": "Asia/Manila",
            "lat": 11.6083,
            "lon": 125.4358,
            "city": "Borongan City, Eastern Samar",
            "max_retries": 0,
            "retry_delay": 0,
        }
        values.update(overrides)
        return daily_updates.Config(**values)

    def test_load_config_reads_location_environment(self):
        environment = {
            "CITY": "Test City",
            "LAT": "12.34",
            "LON": "123.45",
            "TIMEZONE": "UTC",
        }
        with tempfile.TemporaryDirectory() as directory:
            missing_file = Path(directory) / "recipients.txt"
            with patch.object(daily_updates, "RECIPIENTS_FILE", missing_file):
                with patch.dict(os.environ, environment, clear=True):
                    config = daily_updates.load_config(require_credentials=False)

        self.assertEqual(config.city, "Test City")
        self.assertEqual(config.lat, 12.34)
        self.assertEqual(config.lon, 123.45)
        self.assertEqual(config.timezone, "UTC")
        self.assertEqual(config.sender_email, "")
        self.assertEqual(config.recipients, ())

    def test_parse_recipient_lines_ignores_comments_blanks_and_duplicates(self):
        lines = [
            "first@example.com",
            "",
            "# comment",
            " second@example.com ",
            "first@example.com",
        ]

        self.assertEqual(
            daily_updates.parse_recipient_lines(lines),
            ("first@example.com", "second@example.com"),
        )

    def test_load_recipients_prefers_file_over_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            recipient_file = Path(directory) / "recipients.txt"
            recipient_file.write_text("file@example.com\n")
            with patch.dict(
                os.environ,
                {
                    "RECIPIENT_EMAILS": "secret@example.com",
                    "RECEIVER_EMAIL": "legacy@example.com",
                },
                clear=True,
            ):
                recipients = daily_updates.load_recipients(recipient_file)

        self.assertEqual(recipients, ("file@example.com",))

    def test_load_recipients_falls_back_to_environment(self):
        missing_file = Path(tempfile.gettempdir()) / "missing-automations-recipients.txt"
        with patch.dict(
            os.environ,
            {
                "RECIPIENT_EMAILS": "first@example.com\nsecond@example.com",
                "RECEIVER_EMAIL": "legacy@example.com",
            },
            clear=True,
        ):
            recipients = daily_updates.load_recipients(missing_file)

        self.assertEqual(recipients, ("first@example.com", "second@example.com"))

    def test_load_config_requires_credentials_when_sending(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit):
                daily_updates.load_config()

    def test_load_config_rejects_invalid_timezone(self):
        with patch.dict(os.environ, {"TIMEZONE": "Not/A_Timezone"}, clear=True):
            with self.assertRaisesRegex(ValueError, "Invalid TIMEZONE"):
                daily_updates.load_config(require_credentials=False)

    def test_get_weather_formats_open_meteo_response(self):
        config = self.make_config()
        response = {
            "current": {
                "temperature_2m": 26.9,
                "relative_humidity_2m": 85,
                "windspeed_10m": 2.3,
                "weathercode": 0,
            }
        }
        with patch.object(daily_updates, "fetch_json", return_value=response) as fetch:
            result = daily_updates.get_weather(config)

        self.assertIn("Clear sky", result)
        self.assertIn("26.9°C", result)
        self.assertIn("Humidity: 85%", result)
        url = fetch.call_args.args[0]
        self.assertIn("latitude=11.6083", url)
        self.assertIn("longitude=125.4358", url)
        self.assertIn("timezone=Asia%2FManila", url)

    def test_get_news_limits_output_to_three_headlines(self):
        xml = """\
        <rss><channel>
          <item><title>Headline one</title></item>
          <item><title>Headline two</title></item>
          <item><title>Headline three</title></item>
          <item><title>Headline four</title></item>
        </channel></rss>
        """
        with patch.object(daily_updates, "fetch_text", return_value=xml):
            result = daily_updates.get_news(self.make_config())

        self.assertIsNotNone(result)
        self.assertIn("Headline one", result)
        self.assertIn("Headline three", result)
        self.assertNotIn("Headline four", result)

    def test_is_ai_model_advance_covers_provider_watchlist(self):
        relevant_titles = [
            "OpenAI releases a new GPT model",
            "Anthropic updates Claude reasoning capabilities",
            "xAI launches a Grok benchmark update",
            "DeepSeek improves model inference",
            "Google Gemini model performance update",
            "Meta Llama model release",
            "Mistral introduces a new model",
            "Qwen model benchmark results",
        ]
        irrelevant_titles = [
            "UN discusses the future of artificial intelligence",
            "OpenAI announces a new office location",
            "AI policy debate expands across governments",
        ]

        for title in relevant_titles:
            with self.subTest(title=title):
                self.assertTrue(daily_updates.is_ai_model_advance(title))
        for title in irrelevant_titles:
            with self.subTest(title=title):
                self.assertFalse(daily_updates.is_ai_model_advance(title))

    def test_get_ai_news_filters_model_advances_and_limits_items(self):
        xml = """\
        <rss><channel>
          <item>
            <title>OpenAI releases a new GPT model</title>
            <link>https://example.com/openai</link>
            <source>OpenAI News</source>
          </item>
          <item>
            <title>UN discusses the future of artificial intelligence</title>
            <link>https://example.com/un</link>
            <source>World News</source>
          </item>
          <item>
            <title>Anthropic updates Claude reasoning capabilities</title>
            <link>https://example.com/anthropic</link>
            <source>Model News</source>
          </item>
          <item>
            <title>openai releases a new gpt model</title>
            <link>https://example.com/duplicate</link>
            <source>Duplicate News</source>
          </item>
          <item>
            <title>DeepSeek improves model inference</title>
            <link>https://example.com/deepseek</link>
            <source>DeepSeek News</source>
          </item>
          <item>
            <title>Google Gemini model benchmark results</title>
            <link>https://example.com/google</link>
            <source>Google News</source>
          </item>
        </channel></rss>
        """
        with patch.object(daily_updates, "fetch_text", return_value=xml) as fetch:
            result = daily_updates.get_ai_news(self.make_config())

        self.assertIsNotNone(result)
        self.assertIn("OpenAI releases a new GPT model", result)
        self.assertIn("Source: OpenAI News", result)
        self.assertIn("https://example.com/deepseek", result)
        self.assertNotIn("future of artificial intelligence", result)
        self.assertNotIn("duplicate", result)
        self.assertNotIn("Google Gemini model benchmark", result)
        fetch.assert_called_once_with(daily_updates.AI_NEWS_FEED_URL, 0, 0)

    def test_get_google_ai_news_returns_top_three(self):
        xml = """\
        <rss><channel>
          <item><title>AI story one</title><link>https://example.com/one</link><source>One News</source></item>
          <item><title>AI story two</title><link>https://example.com/two</link><source>Two News</source></item>
          <item><title>AI story three</title><link>https://example.com/three</link><source>Three News</source></item>
          <item><title>AI story four</title><link>https://example.com/four</link><source>Four News</source></item>
        </channel></rss>
        """
        with patch.object(daily_updates, "fetch_text", return_value=xml) as fetch:
            result = daily_updates.get_google_ai_news(self.make_config())

        self.assertIsNotNone(result)
        self.assertIn("AI story one", result)
        self.assertIn("AI story three", result)
        self.assertNotIn("AI story four", result)
        fetch.assert_called_once_with(daily_updates.AI_GENERAL_NEWS_FEED_URL, 0, 0)

    def test_get_ai_news_failure_is_nonfatal(self):
        with patch.object(daily_updates, "fetch_text", side_effect=RuntimeError("offline")):
            result = daily_updates.get_ai_news(self.make_config())

        self.assertIsNone(result)

    def test_get_google_ai_news_failure_is_nonfatal(self):
        with patch.object(daily_updates, "fetch_text", side_effect=RuntimeError("offline")):
            result = daily_updates.get_google_ai_news(self.make_config())

        self.assertIsNone(result)

    def test_news_preserves_article_query_and_deduplicates_across_feeds(self):
        xml = """<rss><channel>
        <item><title>OpenAI releases a model - Publisher One</title><link>https://news.google.com/rss/articles/id?oc=5</link><source url="https://publisher.com">Publisher One</source></item>
        <item><title>OpenAI releases a model - Publisher Two</title><link>https://publisher.com/read?id=42</link><source>Publisher Two</source></item>
        <item><title>AI policy discussion</title><link>https://publisher.com/read?id=43</link></item>
        </channel></rss>"""
        seen = set()
        with patch.object(daily_updates, "fetch_text", return_value=xml):
            model_news = daily_updates.get_ai_news(self.make_config(), seen)
            general_news = daily_updates.get_google_ai_news(self.make_config(), seen)
        self.assertIn("https://news.google.com/rss/articles/id?oc=5", model_news)
        self.assertNotIn("Publisher Two", model_news)
        self.assertNotIn("OpenAI releases", general_news)
        self.assertIn("https://publisher.com/read?id=43", general_news)

    def test_bbc_headlines_include_article_links(self):
        with patch.object(daily_updates, "fetch_text", return_value=
                          '<rss><channel><item><title>Headline</title><link>https://example.com/read?id=1</link></item></channel></rss>'):
            result = daily_updates.get_news(self.make_config())
        self.assertIn("https://example.com/read?id=1", result)

    def test_partial_delivery_fails_and_saves_fallback(self):
        config = self.make_config(recipients=("ok@example.com", "refused@example.com"))
        with tempfile.TemporaryDirectory() as directory, patch.object(daily_updates.smtplib, "SMTP_SSL") as smtp:
            smtp.return_value.__enter__.return_value.sendmail.return_value = {
                "refused@example.com": (550, b"Rejected")}
            original_directory = os.getcwd()
            try:
                os.chdir(directory)
                self.assertFalse(daily_updates.send_email(config, "Subject", "Body"))
                saved = next(Path(directory).glob("email_fallback_*.txt")).read_text()
                self.assertIn("Body", saved)
                self.assertIn("refused@example.com", saved)
                self.assertIn("partially", saved.lower())
            finally:
                os.chdir(original_directory)
        self.assertEqual(smtp.call_args.kwargs["timeout"], 30)

    def test_pricing_schedule_uses_local_monday(self):
        from datetime import datetime, timezone
        sunday_utc = datetime(2026, 9, 13, 16, 30, tzinfo=timezone.utc)
        self.assertTrue(daily_updates.pricing_due("Asia/Manila", sunday_utc))
        self.assertFalse(daily_updates.pricing_due("UTC", sunday_utc))

    def test_missing_sections_are_visible_in_body_and_summary(self):
        body = daily_updates.build_body(self.make_config(), "Monday", "September 14, 2026",
                                       "Weather", "Quote", None,
                                       missing=["Headlines", "Crypto: ETH"])
        self.assertIn("Headlines", body)
        self.assertIn("Crypto: ETH", body)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "summary.md"
            with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(path)}):
                daily_updates.write_run_summary(["Headlines", "Crypto: ETH"], "Sent")
            self.assertIn("Crypto: ETH", path.read_text())
            self.assertIn("Sent", path.read_text())

    def test_stock_quotes_preserve_timestamp_and_reject_invalid_price(self):
        payload = {"close": "145.50", "percent_change": "0.5",
                   "datetime": "2026-09-11", "exchange_timezone": "Asia/Manila"}
        with patch.object(daily_updates, "fetch_json", side_effect=[payload] + [{"close": "nan"}] * 4):
            stocks = daily_updates.get_stock_prices(self.make_config(twelvedata_api_key="test"))
        self.assertEqual(list(stocks), ["BDO"])
        result = daily_updates.build_market_section({}, stocks)
        self.assertIn("2026-09-11", result)
        self.assertIn("Asia/Manila", result)

    def test_parse_model_pricing_converts_prices_and_ranks(self):
        payload = {
            "data": [
                {"id": "openai/o3", "pricing": {"prompt": "0.000002", "completion": "0.000008"}},
                {"id": "anthropic/claude-opus-4", "pricing": {"prompt": "0.000005", "completion": "0.000025"}},
                {"id": "google/gemini-2.5-flash", "pricing": {"prompt": "0.0000003", "completion": "0.0000025"}},
                {"id": "deepseek/deepseek-chat", "pricing": {"prompt": "0.0000002574", "completion": "0.0000010287"}},
                {"id": "openai/gpt-4.1-mini", "pricing": {"prompt": "0.0000004", "completion": "0.0000016"}},
            ]
        }

        records = daily_updates.parse_model_pricing(payload)
        by_id = {record["model_id"]: record for record in records}

        self.assertEqual(len(records), 3)
        self.assertEqual(by_id["openai/o3"]["input_per_million"], 2.0)
        self.assertEqual(by_id["openai/o3"]["output_per_million"], 8.0)
        self.assertEqual(by_id["openai/o3"]["comparison_cost"], 4.0)
        self.assertEqual(by_id["openai/gpt-4.1-mini"]["cost_rank"], 1)

        formatted = daily_updates.format_model_pricing(records)
        self.assertIn("Cheapest in watchlist: openai/gpt-4.1-mini", formatted)
        self.assertNotIn("Most capable", formatted)
        self.assertIn("1M input + 250K output", formatted)

    def test_crypto_daily_bar_timestamp_and_missing_previous_close(self):
        import pandas as pd
        history = pd.DataFrame({"Close": [100.0]},
                               index=pd.to_datetime(["2026-09-12T00:00:00Z"]))
        with patch.object(daily_updates.yf, "Ticker") as ticker:
            ticker.return_value.history.return_value = history
            result = daily_updates.build_market_section(daily_updates.get_crypto_prices(), {})
        self.assertIn("Daily bar: 2026-09-12T00:00:00+00:00", result)
        self.assertIn("change unavailable", result)
        self.assertNotIn("▲0.0%", result)

    def test_main_preview_handles_weekly_pricing_and_disabled_stocks(self):
        import io
        import pandas as pd
        from contextlib import redirect_stdout
        history = pd.DataFrame({"Close": [100.0, 110.0]},
                               index=pd.to_datetime(["2026-09-11T00:00:00Z", "2026-09-12T00:00:00Z"]))
        def json_response(url, *args):
            if "open-meteo" in url:
                return {"current": {"temperature_2m": 27, "relative_humidity_2m": 80,
                                    "windspeed_10m": 3, "weathercode": 0}}
            if "zenquotes" in url:
                return [{"q": "Keep going", "a": "Author"}]
            if "openrouter" in url:
                return {"data": [{"id": model_id, "pricing": {"prompt": "0.000002", "completion": "0.000008"}}
                                 for model_id in daily_updates.DEFAULT_MODEL_IDS]}
            raise AssertionError("Unexpected data request")
        def text_response(url, *args):
            if "bbci" in url:
                raise OSError("offline")
            return '<rss><channel><item><title>OpenAI releases a model</title><link>https://example.com/read?id=1</link></item></channel></rss>'
        for due, force in ((False, False), (True, False), (False, True)):
            with self.subTest(due=due, force=force), tempfile.TemporaryDirectory() as directory:
                summary_path = Path(directory) / "summary.md"
                output = io.StringIO()
                with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary_path)}, clear=True), \
                     patch.object(daily_updates, "RECIPIENTS_FILE", Path(directory) / "absent"), \
                     patch.object(
                         daily_updates,
                         "load_plugin_config",
                         return_value=daily_updates.PluginFileConfig(
                             enabled=("weather", "quote", "headlines", "ai_pricing", "crypto"),
                             settings={},
                             schedules={},
                         ),
                     ), \
                     patch.object(daily_updates, "pricing_due", return_value=due), \
                     patch.object(daily_updates, "fetch_json", side_effect=json_response), \
                     patch.object(daily_updates, "fetch_text", side_effect=text_response), \
                     patch.object(daily_updates.yf, "Ticker") as ticker, \
                     patch.object(daily_updates.smtplib, "SMTP_SSL", side_effect=AssertionError("Preview must not send")), \
                     patch.object(sys, "argv", ["daily_updates.py", "--dry-run"] + (["--pricing"] if force else [])), \
                     redirect_stdout(output):
                    ticker.return_value.history.return_value = history
                    daily_updates.main()
                rendered = output.getvalue()
                summary = summary_path.read_text()
                self.assertEqual("AI MODEL PRICING" in rendered, due or force)
                self.assertIn("No new matching stories", rendered)
                self.assertIn("Daily bar: 2026-09-12T00:00:00+00:00", rendered)
                self.assertIn("▲10.0%", rendered)
                self.assertIn("Preview", summary)
                self.assertIn("Missing data: Headlines", summary)
                self.assertNotIn("PH stocks", summary)
                self.assertNotIn("Model pricing", summary)
                self.assertNotIn("AI top stories", summary)

    def test_custom_watchlist_reports_unpriced_ids(self):
        payload = {"data": [{"id": "example/model-v1", "pricing": {"prompt": "0", "completion": "0"}}]}
        missing = []
        with patch.dict(os.environ, {"AI_MODEL_IDS": "example/model-v1,absent/model,example/model-v1"}), \
             patch.object(daily_updates, "fetch_json", return_value=payload):
            result = daily_updates.get_model_pricing(self.make_config(), missing)
        self.assertEqual(missing, ["Model price: absent/model"])
        self.assertIn("example/model-v1", result)
        self.assertIn("Mix: $0", result)
        self.assertNotIn("openai/o3", result)

    def test_get_model_pricing_failure_is_nonfatal(self):
        with patch.object(daily_updates, "fetch_json", side_effect=RuntimeError("offline")):
            result = daily_updates.get_model_pricing(self.make_config())

        self.assertIsNone(result)

    def test_build_body_contains_brief_and_market_sections(self):
        config = self.make_config()
        market = daily_updates.build_market_section(
            {"BTC": daily_updates.MarketQuote(100.0, 2.5, "2026-09-12 UTC")},
            {"BDO": daily_updates.MarketQuote(145.5, -0.5, "2026-09-11 Asia/Manila")}
        )
        body = daily_updates.build_body(
            config,
            "Sunday",
            "June 14, 2026",
            "Clear sky ☀️ | 26.9°C",
            '"Keep going"\n— Author',
            "\n  • Headline one",
            market,
            "  • OpenAI releases a new GPT model\n    Source: Example News\n    https://example.com/one",
            "  • AI story one\n    Source: Google News\n    https://example.com/two",
            "  Cheapest: DeepSeek V3 — $0.50 mix",
        )

        self.assertIn("WEATHER — Borongan City, Eastern Samar", body)
        self.assertIn("QUOTE OF THE DAY", body)
        self.assertIn("HEADLINES", body)
        self.assertIn("AI MODEL ADVANCES", body)
        self.assertIn("AI TOP STORIES", body)
        self.assertIn("AI MODEL PRICING", body)
        self.assertIn("https://example.com/one", body)
        self.assertLess(body.index("AI MODEL ADVANCES"), body.index("AI TOP STORIES"))
        self.assertLess(body.index("AI TOP STORIES"), body.index("AI MODEL PRICING"))
        self.assertLess(body.index("AI MODEL PRICING"), body.index("MARKET UPDATE"))
        self.assertTrue(body.rstrip().endswith("— Your Agent"))
        self.assertIn("BTC", body)
        self.assertIn("BDO", body)

    def test_send_email_includes_clean_html_and_plain_alternatives(self):
        config = self.make_config()
        with patch.object(daily_updates.smtplib, "SMTP_SSL") as smtp:
            smtp.return_value.__enter__.return_value.sendmail.return_value = {}
            self.assertTrue(daily_updates.send_email(config, "Subject", "Plain body", "<p>Clean body</p>"))
        message = smtp.return_value.__enter__.return_value.sendmail.call_args.args[2]
        self.assertIn("multipart/alternative", message)
        from email import message_from_string
        parsed = message_from_string(message)
        parts = parsed.get_payload()
        self.assertEqual(parts[0].get_payload(decode=True).decode(), "Plain body")
        self.assertIn("Clean body", parts[1].get_payload(decode=True).decode())

    def test_smtp_failure_writes_fallback_and_returns_false(self):
        config = self.make_config()
        original_directory = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as directory:
                os.chdir(directory)
                with patch.object(daily_updates.smtplib, "SMTP_SSL", side_effect=OSError("offline")):
                    result = daily_updates.send_email(config, "Subject", "Body")

                fallback_files = list(Path(directory).glob("email_fallback_*.txt"))
                self.assertFalse(result)
                self.assertEqual(len(fallback_files), 1)
                self.assertEqual(fallback_files[0].read_text(), "Subject: Subject\n\nBody")
        finally:
            os.chdir(original_directory)

    def test_main_exits_nonzero_when_email_delivery_fails(self):
        config = self.make_config()
        with patch.object(sys, "argv", ["daily_updates.py"]):
            with patch.object(daily_updates, "load_config", return_value=config), \
                 patch.object(
                     daily_updates,
                     "load_plugin_config",
                     return_value=daily_updates.PluginFileConfig(enabled=(), settings={}, schedules={}),
                 ), \
                 patch.object(daily_updates, "run_plugins", return_value=([], [])), \
                 patch.object(daily_updates, "get_date_info", return_value=("Sunday", "June 14, 2026")), \
                 patch.object(daily_updates, "get_weather", return_value="Weather"), \
                 patch.object(daily_updates, "get_quote", return_value="Quote"), \
                 patch.object(daily_updates, "get_news", return_value=None), \
                 patch.object(daily_updates, "get_ai_news", return_value=None), \
                 patch.object(daily_updates, "get_google_ai_news", return_value=None), \
                 patch.object(daily_updates, "get_model_pricing", return_value=None), \
                 patch.object(daily_updates, "get_crypto_prices", return_value={}), \
                 patch.object(daily_updates, "get_stock_prices", return_value={}), \
                 patch.object(daily_updates, "send_email", return_value=False):
                with self.assertRaises(SystemExit) as error:
                    daily_updates.main()

        self.assertEqual(error.exception.code, 1)

    def test_dry_run_does_not_require_or_send_with_credentials(self):
        config = self.make_config(sender_email="", sender_password="", recipients=())
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(sys, "argv", ["daily_updates.py", "--dry-run"]):
                with patch.object(
                         daily_updates,
                         "load_plugin_config",
                         return_value=daily_updates.PluginFileConfig(enabled=(), settings={}, schedules={}),
                     ), \
                     patch.object(daily_updates, "run_plugins", return_value=([], [])), \
                     patch.object(daily_updates, "get_date_info", return_value=("Sunday", "June 14, 2026")), \
                     patch.object(daily_updates, "get_weather", return_value="Weather"), \
                     patch.object(daily_updates, "get_quote", return_value="Quote"), \
                     patch.object(daily_updates, "get_news", return_value=None), \
                     patch.object(daily_updates, "get_ai_news", return_value=None), \
                     patch.object(daily_updates, "get_google_ai_news", return_value=None), \
                     patch.object(daily_updates, "get_model_pricing", return_value=None), \
                     patch.object(daily_updates, "get_crypto_prices", return_value={}), \
                     patch.object(daily_updates, "get_stock_prices", return_value={}), \
                     patch.object(daily_updates, "send_email") as send:
                    with patch.object(daily_updates, "load_config", return_value=config) as load:
                        daily_updates.main()

        load.assert_called_once_with(require_credentials=False)
        send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
