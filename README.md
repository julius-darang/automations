# Daily Brief & Market Update

A small Python orchestrator loads independent briefing plugins and sends the result
through Gmail as a clean HTML email with a plain-text fallback. GitHub Actions
schedules it daily for **2:17 PM Philippines time**
(06:17 UTC). Scheduled runs may arrive late; manual dispatch is also available.

## The briefing

- Borongan weather, a quote, and three BBC headlines with article links.
- Up to three AI model advances and three broader AI stories, deduplicated across
  both feeds by article URL and normalized title. Original article URLs are kept.
- **Mondays only:** OpenRouter token prices for a small model watchlist. Exact model
  IDs and the cheapest option within that watchlist are shown; no capability ranking.
- BTC, ETH, SOL and optional BDO, SM, TEL, ALI, JFC quotes. Market rows include the
  source date/time when available; unknown timestamps are explicitly labeled.
- A footer identifies missing data. A missing optional API key or a non-Monday
  pricing section is not treated as a failure.

Crypto percentages compare the latest daily bar with the previous daily close,
not a rolling 24-hour return. The bar timestamp is labeled as such. Stock quotes
may be delayed or from an earlier trading day; always check their source timestamp.

## Sources and cost

| Section | Source | Access |
| --- | --- | --- |
| Weather | [Open-Meteo](https://open-meteo.com/en/pricing) | Free for noncommercial use within limits |
| Quote | [ZenQuotes](https://zenquotes.io/) | Public endpoint |
| Quotable | [Quotable](https://github.com/lukePeavey/quotable) | Optional public quote API |
| Stoic quote | [Stoic Quotes](https://stoic-quotes.com/) | Public endpoint |
| Dad joke | [icanhazdadjoke](https://icanhazdadjoke.com/) | Public JSON endpoint |
| Word of the day | [Merriam-Webster RSS](https://www.merriam-webster.com/wotd/feed/rss2) | Public feed |
| Bible verse | [Bible API](https://bible-api.com/) | Public-domain WEB translation |
| Headlines | [BBC RSS](https://feeds.bbci.co.uk/news/rss.xml) | Public feed |
| AI news | [Google News RSS](https://news.google.com/) | Public feeds |
| Weekly model prices | [OpenRouter catalog](https://openrouter.ai/models) | Public catalog; no model inference calls |
| Crypto | [yfinance](https://pypi.org/project/yfinance/) | Public Yahoo data access |
| PH stocks | [Twelve Data](https://twelvedata.com/pricing) | Optional key; verify PSE entitlement on your plan |
| Reddit tech | [Reddit RSS](https://www.reddit.com/dev/api/) | Public RSS feed; configurable subreddits |
| Papers With Code | [Papers With Code](https://paperswithcode.com/) | Public web feed |
| Semantic Scholar | [Academic Graph API](https://www.semanticscholar.org/product/api) | Public API; optional `SEMANTIC_SCHOLAR_API_KEY` |
| GitHub Trending | [GitHub Trending](https://github.com/trending) | Public web page |
| Product Hunt | [Product Hunt Atom feed](https://www.producthunt.com/feed) | Public feed |

A free Twelve Data key does not guarantee access to every exchange. Keep PH stocks
optional if your account does not include them; this project does not require an
upgrade. API availability and terms can change.

Standard GitHub-hosted runners are [free for public repositories](https://docs.github.com/en/billing/concepts/product-billing/github-actions).
Private repositories have usage allowances. This setup needs no server, database,
paid AI calls, or automation platform.

## Setup

Use Python 3.11 or newer. Create an environment and install the pinned dependencies:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

For Gmail, enable two-step verification and create an
[App Password](https://myaccount.google.com/apppasswords).
Add these GitHub repository secrets:

| Secret | Purpose |
| --- | --- |
| `SENDER_EMAIL` | Gmail sender address |
| `SENDER_PASSWORD` | Gmail app password |
| `RECIPIENT_EMAILS` | One recipient per line |
| `RECEIVER_EMAIL` | Optional legacy single-recipient fallback |
| `TWELVEDATA_API_KEY` | Optional PH stock access |
| `SEMANTIC_SCHOLAR_API_KEY` | Optional higher/reliable Semantic Scholar API access |
| `NTFY_TOPIC` | Optional random ntfy topic for workflow failure alerts |
| `HEALTHCHECKS_PING_URL` | Optional missing-run monitor ping URL |

Recipients currently appear together in the email's To header. Use this for a
personal/trusted group. Locally, a gitignored `recipients.txt` (one address per
line; comments and blanks ignored) takes priority over environment variables.

The workflow uses a read-only repository token, prevents overlapping runs, and
has a ten-minute limit. Concurrency is not a once-per-day delivery guarantee:
manual dispatch or a rerun can send another email.

### Choose the plugins

Edit the tracked `plugins.yaml` file. The `enabled` list controls which sections
run and its order controls the email order:

```yaml
enabled:
  - weather
  - quote
  - headlines
  - ai_pricing
  - crypto
  # - ph_stocks
```

Additional optional plugins are available but disabled by default: `quotable`,
`stoic`, `dad_joke`, `word_of_day`, `bible_verse`, `hackernews`, `reddit`,
`papers_with_code`, `semantic_scholar`, `github_trending`, `product_hunt`, `lobsters`,
`devto`, `arxiv`, `openalex`, `air_quality`, `uv_index`, `fx`, `sunrise`, and
`public_holiday`. Enable them one at a time as you decide what belongs in your brief.
Reddit, Semantic Scholar, GitHub Trending, and Product Hunt expose settings for
source queries/limits in `plugins.yaml`; environment variables with the same names
override those defaults.

The committed `settings` are fork-safe defaults for location and timezone.
Environment variables override them at runtime. `TWELVEDATA_API_KEY` remains an
optional secret and is required only when `ph_stocks` is enabled. `ai_pricing`
contains both daily AI feeds and the scheduled pricing subsection. The optional
`schedules` mapping controls pricing cadence; pricing defaults to Monday, and
`--pricing` forces it for a preview.

For plugin authors, see [`plugins/README.md`](plugins/README.md).

## Local preview and tests

```bash
python daily_updates.py --dry-run                 # Fetch live data; print only
python daily_updates.py --plugin quote --dry-run   # Preview one plugin
python daily_updates.py --dry-run --pricing        # Include pricing on any day
python -m unittest discover -s tests -p 'test_*.py' -v
```

For local sending, put credentials in the ignored `.env` file and run
`python daily_updates.py --local`. A dry run never sends mail. Manual GitHub
workflow dispatch also has a `dry_run` checkbox; it fetches and prints the brief
without sending or pinging the delivery monitor.

Location defaults live in `plugins.yaml`. Environment overrides (workflow
variables or local `.env`) are still supported:

```text
CITY=Borongan City, Eastern Samar
LAT=11.6083
LON=125.4358
TIMEZONE=Asia/Manila
REDDIT_SUBREDDITS=technology,programming
SEMANTIC_SCHOLAR_QUERY=artificial intelligence
GITHUB_TRENDING_LANGUAGE=Python
```

Set the optional **repository variable** `AI_MODEL_IDS` (or the same environment
variable locally) to comma-separated exact OpenRouter IDs. The default watchlist
is `openai/o3,openai/gpt-4.1-mini,google/gemini-2.5-flash`. These are explicit
watchlist choices, not a claim that they are the latest or best models. Unknown
or unpriced IDs are reported. Costs show input/output USD per million tokens and
an example total for 1M input + 250K output.

## Failures and monitoring

Data requests use bounded timeouts and retries. A failed plugin does not stop
other sections. The email footer and GitHub Actions job summary identify missing
data; the summary also records delivery status. A feed with no new matching
stories is reported as empty, not as a delivery failure.

SMTP has a 30-second timeout. A send failure saves the email to
`email_fallback_*.txt`, fails the run, and retains that file as a 30-day artifact.
Partial recipient rejection also fails the run and records refused addresses in
the fallback. **Do not blindly rerun a partial or ambiguous send:** some recipients
may already have received it. Check the fallback and logs first.

If `NTFY_TOPIC` is set, failed runs notify that topic. This cannot detect a job
that never starts. For that, optionally create one free
[Healthchecks.io](https://healthchecks.io/) check, set a daily 06:17 UTC schedule
with a two-hour grace period, and save its ping URL as `HEALTHCHECKS_PING_URL`.
The workflow pings it only after the script reports successful delivery. Missing
data does not suppress a successful-delivery ping. A ping failure produces a
warning and does not trigger another email send.

GitHub warns that [scheduled runs can be delayed or dropped, and public-repository
schedules disable after 60 days without repository activity](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows).
The off-hour-minute schedule reduces contention; an external check catches missed
runs. Creating/configuring the optional monitor is a separate account setup step.

## Files

- `daily_updates.py`: configuration, orchestration, preview, send, and reporting.
- `plugins.yaml`: enabled plugin order and fork-specific defaults.
- `plugins/`: discovered data plugins and their contract documentation.
- `.github/workflows/daily-email.yml`: daily schedule and optional notifications.
- `.github/workflows/ci.yml`: unit tests on pushes and pull requests.
- `tests/`: regression and plugin-isolation tests without live email delivery.
- `index.html`: static project page.
