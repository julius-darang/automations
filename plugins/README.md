# Daily Brief plugins

Each plugin is a self-contained Python module implementing `BasePlugin`.
Adding a plugin does not require editing the orchestrator or the registry: add a
module under this directory, then add its `name` to the root `plugins.yaml`.

## Contract

```python
from plugins.base import BasePlugin, FetchResult, PluginContext


class ExamplePlugin(BasePlugin):
    name = "example"
    display_name = "Example"

    def should_run(self, context: PluginContext) -> bool:
        return True

    def fetch(self, context: PluginContext) -> FetchResult:
        try:
            data = context.fetch_json("https://example.com/data", context.max_retries, context.retry_delay)
            return FetchResult(ok=True, data=data)
        except Exception as error:
            return FetchResult(ok=False, error=str(error))

    def render(self, data) -> str:
        return f"EXAMPLE\n{data}"
```

Required class attributes:

- `name`: stable key used in `plugins.yaml`.
- `display_name`: label used in logs and missing-data summaries.

Required methods:

- `should_run(context)`: pure applicability/schedule decision; no network I/O.
- `fetch(context)`: fetch and normalize provider data. It must return
  `FetchResult` and catch provider errors internally.
- `render(data)`: turn a successful payload into a plain-text block. It is not
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
