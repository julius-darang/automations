import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import daily_updates  # noqa: E402
from plugins import discover_plugins  # noqa: E402
from plugins.base import BasePlugin, FetchResult, PluginContext  # noqa: E402


class RegistryTests(unittest.TestCase):
    def test_auto_discovery_finds_all_default_plugins(self):
        self.assertEqual(
            set(discover_plugins()),
            {
                "weather", "quote", "headlines", "hackernews", "lobsters", "devto", "arxiv", "openalex", "air_quality",
                "ai_pricing", "crypto", "ph_stocks", "uv_index", "fx", "sunrise",
            },
        )

    def test_yaml_order_and_environment_override(self):
        yaml_text = """
        enabled:
          - quote
          - weather
        settings:
          CITY: YAML City
          LAT: "1"
        schedules:
          ai_pricing: [monday]
        """
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plugins.yaml"
            path.write_text(yaml_text)
            with patch.dict(os.environ, {"CITY": "Environment City"}, clear=True):
                config = daily_updates.load_plugin_config(path)
        self.assertEqual(config.enabled, ("quote", "weather"))
        self.assertEqual(config.settings["CITY"], "Environment City")
        self.assertEqual(config.settings["LAT"], "1")
        self.assertEqual(config.schedules["ai_pricing"], ("monday",))

    def test_unknown_plugin_lists_valid_names(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plugins.yaml"
            path.write_text("enabled: [not_real]\n")
            with self.assertRaisesRegex(ValueError, r"Unknown plugin name.*weather"):
                daily_updates.load_plugin_config(path)

    def test_plugin_failure_does_not_stop_following_plugin(self):
        class BrokenPlugin(BasePlugin):
            name = "broken"
            display_name = "Broken"

            def fetch(self, context):
                raise RuntimeError("offline")

            def render(self, data):
                return "never"

        class WorkingPlugin(BasePlugin):
            name = "working"
            display_name = "Working"

            def fetch(self, context):
                return FetchResult(True, data="loaded")

            def render(self, data):
                return data

        context = PluginContext(
            settings={},
            timezone="UTC",
            lat=0,
            lon=0,
            city="Test",
            now=datetime(2026, 9, 21),
        )
        blocks, missing = daily_updates.run_plugins(
            [BrokenPlugin(), WorkingPlugin()],
            context,
        )
        self.assertEqual([block.name for block in blocks], ["working"])
        self.assertEqual(missing, ["Broken"])

    def test_plugin_body_preserves_order_and_groups_market_sections(self):
        blocks = [
            daily_updates.PluginBlock("quote", "Quote", "QUOTE"),
            daily_updates.PluginBlock("crypto", "Crypto", "CRYPTO", "market"),
            daily_updates.PluginBlock("ph_stocks", "PH stocks", "STOCKS", "market"),
            daily_updates.PluginBlock("headlines", "Headlines", "HEADLINES"),
        ]
        body = daily_updates.build_plugin_body(
            daily_updates.Config("", "", (), city="Test City"),
            "Monday",
            "September 21, 2026",
            blocks,
            ["Weather"],
        )
        self.assertLess(body.index("QUOTE"), body.index("MARKET UPDATE"))
        self.assertLess(body.index("MARKET UPDATE"), body.index("CRYPTO"))
        self.assertLess(body.index("CRYPTO"), body.index("STOCKS"))
        self.assertLess(body.index("STOCKS"), body.index("HEADLINES"))
        self.assertIn("Missing data: Weather", body)

    def test_html_email_is_simple_and_has_no_logo(self):
        body = """Good afternoon!

━━━━━━━━━━━━━━━━━━━━━━━━
📅  Monday, September 21, 2026
━━━━━━━━━━━━━━━━━━━━━━━━

🌤  WEATHER — Test City
Clear sky ☀️ | 27.0°C | Humidity: 80%

━━━━━━━━━━━━━━━━━━━━━━━━

🤖  AI MODEL ADVANCES
  • A model release
    Source: OpenAI
    https://example.com/article

Missing data: Headlines

— Your Agent"""
        html = daily_updates.build_html_email(body, "Daily Brief — Monday")
        self.assertIn('<main class="mail">', html)
        self.assertIn("Daily Brief", html)
        self.assertIn("AI MODEL ADVANCES", html)
        self.assertIn('<a class="story-title" href="https://example.com/article">A model release</a>', html)
        self.assertEqual(html.count("https://example.com/article"), 1)
        self.assertNotIn("avatar", html)
        self.assertNotIn("<svg", html)

    def test_plugin_flag_requires_dry_run(self):
        with patch.object(sys, "argv", ["daily_updates.py", "--plugin", "quote"]):
            with self.assertRaises(SystemExit) as error:
                daily_updates.main()
        self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
