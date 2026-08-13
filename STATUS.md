---
name: automations
description: Daily brief + market-alert email crons via GitHub Actions
domain: infra
status: active
stack: Python · GitHub Actions cron · SMTP
entry: python send_email.py  (local test) · push to trigger cron
has_repo: true
updated: 2026-07-31
---

# automations

## State
Two scripts now (not one): `send_email.py` (daily brief) + `market_alert.py` (market
update), both fired by GitHub Actions cron (6am UTC = 2pm PH). Deployed and working.
Location hard-coded to Catbalogan, Samar (minor debt).

## Next action
- Parameterize the Catbalogan location (env var / secrets) so other cities work.
- No other active work unless a new cron need arises.

## Conventions
- none (scripts are self-contained; secrets via repo Secrets, never committed).

## Pointers
- Workflow: `.github/workflows/` · deps `requirements.txt`.
- Own `.git` at this path (origin `github.com/julius-darang/automations`).