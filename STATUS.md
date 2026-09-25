---
name: automations
description: Daily brief and market-update email via GitHub Actions
domain: infra
status: active
stack: Python 3.11 · GitHub Actions cron · SMTP
entry: python daily_updates.py --dry-run · GitHub Actions daily schedule
has_repo: true
updated: 2026-09-25
---

# automations

## State
`daily_updates.py` is the production orchestrator for the daily brief and market update;
its data sections are discovered from `plugins/` and selected in `plugins.yaml`. The workflow
schedules it for 06:17 UTC (2:17pm Philippines time); manual dispatch is also available,
with a safe `dry_run` input that skips SMTP delivery and the delivery-monitor ping. The
default location is Borongan City, Eastern Samar and can be overridden in `plugins.yaml` or
with `CITY`, `LAT`, `LON`, and `TIMEZONE` environment variables. The email includes focused AI
model advances, separate Google AI top stories, and OpenRouter model pricing on Mondays for a
configurable three-model watchlist, without capability ranks. News links are preserved and
deduplicated inside the AI plugin. Optional quote/text sources include Quotable, Stoic Quotes, dad jokes, Word of the Day,
Bible verses, chess puzzles, trivia, recipes, and cocktails; ranked-list sources include
Reddit, Papers With Code, Semantic Scholar,
GitHub Trending, and Product Hunt. Market rows include source
timestamps. Missing data appears
in the email and Actions summary. SMTP timeouts and partial-recipient failure handling protect
delivery reporting. Recipients come from the gitignored `recipients.txt` locally or the
`RECIPIENT_EMAILS` secret in CI, with `RECEIVER_EMAIL` as a fallback.

The root `index.html` now includes a browser-only builder for all 30 plugins, with
sample content, toggles, search/category filters, pointer drag ordering, keyboard
controls, and an email preview. It does not fetch providers or change delivery or
configuration. Static CSS/JS live in `assets/`; no build step is required.

## Next action
- Review and deploy the landing-page demo; catalog parity is checked by Python tests,
  reorder logic by Node tests, and interactions by the optional Playwright script.
- SMTP reliability fix is merged. Run 36113489275 reached authentication but failed
  with Gmail 535; correct the sender's App Password before testing delivery again.
- Continue provider reliability work (Quotable TLS failure, research API rate limits,
  and Papers With Code redirect/attribution).
- Verify Twelve Data PSE entitlement before relying on the optional stock section.

## Conventions
- Plugins are self-contained; shared transport/contract code lives under `plugins/`.
- Secrets come from local `.env`/recipient files or repo Secrets and are never committed.

## Pointers
- Workflow: `.github/workflows/` · deps `requirements.txt` · config `plugins.yaml` · plugin contract `plugins/README.md`.
- Own `.git` at this path (origin `github.com/julius-darang/email-brief`).
