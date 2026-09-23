import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from plugins.formatting import (  # noqa: E402
    KeyValue,
    RankedItem,
    render_kv,
    render_quote,
    render_ranked_list,
)


class FormattingTests(unittest.TestCase):
    def test_ranked_list_renders_items_and_respects_limit(self):
        items = [
            RankedItem("First", "https://example.com/1", ("Score: 10",)),
            RankedItem("Second", "https://example.com/2"),
        ]
        rendered = render_ranked_list(items, max_results=1)
        self.assertIn("First", rendered)
        self.assertIn("Score: 10", rendered)
        self.assertIn("https://example.com/1", rendered)
        self.assertNotIn("Second", rendered)

    def test_key_value_and_quote_renderers(self):
        value = KeyValue("Temperature", 27, "°C")
        self.assertEqual(render_kv(value.label, value.value, value.unit), "Temperature: 27°C")
        self.assertEqual(render_kv("", 27, "°C"), "27°C")
        self.assertEqual(render_quote("Keep going", "Author"), '"Keep going"\n— Author')


if __name__ == "__main__":
    unittest.main()
