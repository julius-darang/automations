"""Small, retrying HTTP helpers shared by data plugins."""

from __future__ import annotations

import json
import time
import urllib.request
from typing import Mapping


USER_AGENT = "daily-brief/1.0 (personal feed reader)"


def fetch_json(
    url: str,
    max_retries: int = 2,
    delay: int = 3,
    headers: Mapping[str, str] | None = None,
) -> dict | list:
    """Fetch and decode JSON, raising the last provider error on failure."""
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            request_headers = {"User-Agent": USER_AGENT, **(dict(headers) if headers else {})}
            request = urllib.request.Request(url, headers=request_headers)
            with urllib.request.urlopen(request, timeout=10) as response:
                return json.loads(response.read())
        except Exception as error:  # network/provider errors are intentionally broad
            last_error = error
            if attempt < max_retries:
                time.sleep(delay)
    assert last_error is not None
    raise last_error


def fetch_text(
    url: str,
    max_retries: int = 2,
    delay: int = 3,
    headers: Mapping[str, str] | None = None,
) -> str:
    """Fetch UTF-8 text, raising the last provider error on failure."""
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            request_headers = {"User-Agent": USER_AGENT, **(dict(headers) if headers else {})}
            request = urllib.request.Request(url, headers=request_headers)
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.read().decode("utf-8")
        except Exception as error:  # network/provider errors are intentionally broad
            last_error = error
            if attempt < max_retries:
                time.sleep(delay)
    assert last_error is not None
    raise last_error
