"""Offline checks that the demonstration stays aligned with the plugin registry."""

import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

from plugins import discover_plugins

ROOT = Path(__file__).resolve().parents[1]


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.targets = []
        self.assets = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        href = attrs.get('href', '')
        if href.startswith('#') and len(href) > 1:
            self.targets.append(href[1:])
        if tag == 'script':
            self.assets.append(attrs.get('src', ''))
        if tag == 'link' and attrs.get('rel') == 'stylesheet':
            self.assets.append(href)


class LandingPageTests(unittest.TestCase):
    def test_demo_catalog_matches_discovered_plugins(self):
        script = (ROOT / 'assets/plugin-demo.js').read_text()
        ids = re.findall(r'\{ id: "([a-z_]+)"', script)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids), set(discover_plugins()))

    def test_static_page_ids_links_and_local_assets(self):
        page = (ROOT / 'index.html').read_text()
        parser = PageParser()
        parser.feed(page)
        self.assertEqual(len(parser.ids), len(set(parser.ids)))
        self.assertTrue(set(parser.targets).issubset(parser.ids))
        for asset in parser.assets:
            self.assertTrue((ROOT / asset).is_file(), asset)
        self.assertNotIn('github.com/julius-darang/automations', page)
        self.assertIn('<noscript>', page)
        self.assertIn('All 30 plugins', page)

    def test_demo_has_no_network_or_storage_integration(self):
        script = (ROOT / 'assets/plugin-demo.js').read_text()
        for api in ('fetch(', 'XMLHttpRequest', 'WebSocket', 'sendBeacon', 'localStorage', 'sessionStorage', 'document.cookie'):
            self.assertNotIn(api, script)
        self.assertNotIn('innerHTML', script)
        self.assertNotIn('eval(', script)
