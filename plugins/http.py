"""Small, retrying HTTP helpers shared by data plugins."""

from __future__ import annotations

import json
import time
import urllib.request


USER_AGENT = "daily-brief/1.0 (personal feed reader)"


def fetch_json(url: str, max_retries: int = 2, delay: int = 3) -> dict | list:
    """Fetch and decode JSON, raising the last provider error on failure."""
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=10) as response:
                return json.loads(response.read())
        except Exception as error:  # network/provider errors are intentionally broad
            last_error = error
            if attempt < max_retries:
                time.sleep(delay)
    assert last_error is not None
    raise last_error


def fetch_text(url: str, max_retries: int = 2, delay: int = 3) -> str:
    """Fetch UTF-8 text, raising the last provider error on failure."""
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.read().decode("utf-8")
        except Exception as error:  # network/provider errors are intentionally broad
            last_error = error
            if attempt < max_retries:
                time.sleep(delay)
    assert last_error is not None
    raise last_error
