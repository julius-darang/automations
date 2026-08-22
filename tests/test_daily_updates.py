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
            "receiver_email": "receiver@example.com",
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
        with patch.dict(os.environ, environment, clear=True):
            config = daily_updates.load_config(require_credentials=False)

        self.assertEqual(config.city, "Test City")
        self.assertEqual(config.lat, 12.34)
        self.assertEqual(config.lon, 123.45)
        self.assertEqual(config.timezone, "UTC")
        self.assertEqual(config.sender_email, "")

    def test_load_config_requires_credentials_when_sending(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit):
                daily_updates.load_config()

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

    def test_build_body_contains_brief_and_market_sections(self):
        config = self.make_config()
        market = daily_updates.build_market_section(
            {"BTC": (100.0, 2.5)}, {"BDO": (145.5, -0.5)}
        )
        body = daily_updates.build_body(
            config,
            "Sunday",
            "June 14, 2026",
            "Clear sky ☀️ | 26.9°C",
            '"Keep going"\n— Author',
            "\n  • Headline one",
            market,
        )

        self.assertIn("WEATHER — Borongan City, Eastern Samar", body)
        self.assertIn("QUOTE OF THE DAY", body)
        self.assertIn("HEADLINES", body)
        self.assertIn("BTC", body)
        self.assertIn("BDO", body)

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
                 patch.object(daily_updates, "get_date_info", return_value=("Sunday", "June 14, 2026")), \
                 patch.object(daily_updates, "get_weather", return_value="Weather"), \
                 patch.object(daily_updates, "get_quote", return_value="Quote"), \
                 patch.object(daily_updates, "get_news", return_value=None), \
                 patch.object(daily_updates, "get_crypto_prices", return_value={}), \
                 patch.object(daily_updates, "get_stock_prices", return_value={}), \
                 patch.object(daily_updates, "send_email", return_value=False):
                with self.assertRaises(SystemExit) as error:
                    daily_updates.main()

        self.assertEqual(error.exception.code, 1)

    def test_dry_run_does_not_require_or_send_with_credentials(self):
        config = self.make_config(sender_email="", sender_password="", receiver_email="")
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(sys, "argv", ["daily_updates.py", "--dry-run"]):
                with patch.object(daily_updates, "get_date_info", return_value=("Sunday", "June 14, 2026")), \
                     patch.object(daily_updates, "get_weather", return_value="Weather"), \
                     patch.object(daily_updates, "get_quote", return_value="Quote"), \
                     patch.object(daily_updates, "get_news", return_value=None), \
                     patch.object(daily_updates, "get_crypto_prices", return_value={}), \
                     patch.object(daily_updates, "get_stock_prices", return_value={}), \
                     patch.object(daily_updates, "send_email") as send:
                    with patch.object(daily_updates, "load_config", return_value=config) as load:
                        daily_updates.main()

        load.assert_called_once_with(require_credentials=False)
        send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
