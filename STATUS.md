---
name: automations
description: Daily brief and market-update email via GitHub Actions
domain: infra
status: active
stack: Python 3.11 · GitHub Actions cron · SMTP
entry: python daily_updates.py --dry-run · GitHub Actions daily schedule
has_repo: true
updated: 2026-09-12
---

# automations

## State
`daily_updates.py` is the single production entry point for the daily brief and market
update. The workflow schedules it for 06:17 UTC (2:17pm Philippines time); manual dispatch is
also available. The default location is Borongan City, Eastern Samar and can be
overridden with `CITY`, `LAT`, `LON`, and `TIMEZONE` environment variables. The email
includes focused AI model advances, separate Google AI top stories, and OpenRouter model
pricing on Mondays for a configurable three-model watchlist, without capability ranks.
News links are preserved and deduplicated across AI feeds. Market rows include
source timestamps. Missing data appears in the email and Actions summary. SMTP
timeouts and partial-recipient failure handling protect delivery reporting. Recipients come from the gitignored
`recipients.txt` locally or the `RECIPIENT_EMAILS` secret in CI, with `RECEIVER_EMAIL` as
a fallback.

## Next action
- Deploy the reviewed local changes to GitHub to activate the updated workflow.
- Optional: set `HEALTHCHECKS_PING_URL` after creating a free daily monitor.
- Verify Twelve Data PSE entitlement before relying on the optional stock section.

## Conventions
- none (scripts are self-contained; secrets via repo Secrets, never committed).

## Pointers
- Workflow: `.github/workflows/` · deps `requirements.txt`.
- Own `.git` at this path (origin `github.com/julius-darang/automations`).
