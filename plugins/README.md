# Daily Brief plugins

Each plugin is a self-contained Python module implementing `BasePlugin`.
Adding a plugin does not require editing the orchestrator or the registry: add a
module under this directory, then add its `name` to the root `plugins.yaml`.

## Optional source catalog

The ranked-list and text sources are intentionally opt-in in `plugins.yaml`:

- `quotable` and `stoic`: independent quote providers.
- `dad_joke`: JSON dad-joke provider.
- `word_of_day`: Merriam-Webster Word of the Day RSS.
- `bible_verse`: random verse from the public-domain World English Bible.
- `chess_puzzle`, `trivia`, `recipe`, and `cocktail`: bespoke daily challenge and
  food/drink outputs.
- `reddit`: technology/programming RSS; configure `REDDIT_SUBREDDITS`.
- `papers_with_code`: public Papers With Code paper cards.
- `semantic_scholar`: Academic Graph search; configure
  `SEMANTIC_SCHOLAR_QUERY` and optionally provide the
  `SEMANTIC_SCHOLAR_API_KEY` environment secret.
- `github_trending`: public repository trend page; configure
  `GITHUB_TRENDING_SINCE`, `GITHUB_TRENDING_LANGUAGE`, and
  `GITHUB_TRENDING_LIMIT`.
- `product_hunt`: public Product Hunt Atom feed; configure
  `PRODUCT_HUNT_LIMIT`.

These providers are isolated: an unavailable optional source is reported in the
missing-data footer without preventing the rest of the brief from rendering.

## Contract

```python
from plugins.base import BasePlugin, FetchResult, PluginContext
from plugins.formatting import RankedItem, render_ranked_list, section


class ExamplePlugin(BasePlugin):
    name = "example"
    display_name = "Example"

    def should_run(self, context: PluginContext) -> bool:
        return True

    def fetch(self, context: PluginContext) -> FetchResult:
        try:
            payload = context.fetch_json("https://example.com/data", context.max_retries, context.retry_delay)
            items = [RankedItem(row["title"], row.get("url", "")) for row in payload]
            return FetchResult(ok=True, data=items)
        except Exception as error:
            return FetchResult(ok=False, error=str(error))

    def render(self, data: list[RankedItem]) -> str:
        return section("EXAMPLE", render_ranked_list(data))
```

Required class attributes:

- `name`: stable key used in `plugins.yaml`.
- `display_name`: label used in logs and missing-data summaries.

Required methods:

- `should_run(context)`: pure applicability/schedule decision; no network I/O.
- `fetch(context)`: fetch and normalize provider data. It must return
  `FetchResult` and catch provider errors internally.
- `render(data)`: return a plain-text section. Use `section(title, body)` so the
  title/body boundary is also available as explicit email metadata. For a plugin
  with multiple subsections, combine `section(...)` values with `combine_sections()`.
  Prefer the shape-based helpers in `plugins.formatting` for ranked lists,
  key/value rows, and quotes. The section helpers remain `str`-compatible, so
  plain-text output and existing callers continue to work. `render()` is not
  called when `fetch()` returns `ok=False`.

A successful partial result can report individual missing items:

```python
return FetchResult(
    ok=True,
    data=available_rows,
    missing=("Example: row 2",),
)
```

Unexpected errors are still caught by the orchestrator as a final safety net.
Do not put credentials in plugin code or `plugins.yaml`; use environment
variables/GitHub secrets and read them through `context.secret("SECRET_NAME")`.
The base context exposes only generic settings, schedules, and secrets; provider-
specific credentials do not become part of the plugin contract.

## Local testing

Run one plugin without sending email:

```bash
python daily_updates.py --plugin quote --dry-run
```

Run the complete configured brief without sending:

```bash
python daily_updates.py --dry-run
```
