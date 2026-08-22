---
name: automations
description: Daily brief and market-update email via GitHub Actions
domain: infra
status: active
stack: Python 3.11 · GitHub Actions cron · SMTP
entry: python daily_updates.py  (local test) · push to trigger cron
has_repo: true
updated: 2026-08-22
---

# automations

## State
`daily_updates.py` is the single production entry point for the daily brief and market
update. GitHub Actions runs it at 6am UTC (2pm Philippines time); manual dispatch is
also available. The default location is Borongan City, Eastern Samar and can be
overridden with `CITY`, `LAT`, `LON`, and `TIMEZONE` environment variables. The email
includes focused AI model advances, separate Google AI top stories, and OpenRouter model
pricing with curated capability ranks. Recipients come from the gitignored
`recipients.txt` locally or the `RECIPIENT_EMAILS` secret in CI, with `RECEIVER_EMAIL` as
a fallback.

## Next action
- No other active work unless a new cron need arises.

## Conventions
- none (scripts are self-contained; secrets via repo Secrets, never committed).

## Pointers
- Workflow: `.github/workflows/` · deps `requirements.txt`.
- Own `.git` at this path (origin `github.com/julius-darang/automations`).