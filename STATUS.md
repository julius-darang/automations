---
name: automations
description: Daily brief and market-update email via GitHub Actions
domain: infra
status: active
stack: Python 3.11 · GitHub Actions cron · SMTP
entry: python daily_updates.py --dry-run · GitHub Actions daily schedule
has_repo: true
updated: 2026-09-23
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
deduplicated inside the AI plugin. Optional ranked-list sources include Reddit, Papers With
Code, Semantic Scholar, GitHub Trending, and Product Hunt. Market rows include source
timestamps. Missing data appears
in the email and Actions summary. SMTP timeouts and partial-recipient failure handling protect
delivery reporting. Recipients come from the gitignored `recipients.txt` locally or the
`RECIPIENT_EMAILS` secret in CI, with `RECEIVER_EMAIL` as a fallback.

## Next action
- Review and merge the optional ranked-list source plugins and safe workflow preview.
- Run the manual workflow once with `dry_run=true` before any real production send.
- Migrate `crypto` and `ph_stocks` to the shared key/value renderer.
- Verify Twelve Data PSE entitlement before relying on the optional stock section.

## Conventions
- Plugins are self-contained; shared transport/contract code lives under `plugins/`.
- Secrets come from local `.env`/recipient files or repo Secrets and are never committed.

## Pointers
- Workflow: `.github/workflows/` · deps `requirements.txt` · config `plugins.yaml` · plugin contract `plugins/README.md`.
- Own `.git` at this path (origin `github.com/julius-darang/automations`).
