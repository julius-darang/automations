# Daily Brief & Market Update Automation

A fully automated daily email briefing that delivers weather, a motivational quote, news headlines, **crypto prices**, and **PH stock prices** to your inbox every afternoon — scheduled via GitHub Actions.

## What You Get

Each day at **2:00 PM PH time (UTC+8)**, the automation sends an email like this:

```
📅  Sunday, June 14, 2026

🌤  WEATHER — Borongan City, Eastern Samar
Clear sky ☀️ | 26.9°C | Humidity: 85% | Wind: 2.3 km/h

💬  QUOTE OF THE DAY
"To belittle, you have to be little."
— Kahlil Gibran

📰  HEADLINES
  • Royal Marines board Russian shadow fleet oil tanker in English Channel
  • Watch: MOD video shows Russian shadow fleet tanker interception
  • Why Haiti v Scotland was antidote to the ills of world football

📈  MARKET UPDATE

🪙  CRYPTO
  BTC  •  $67,890.12  (▲2.3%)
  ETH  •  $3,456.78  (▼1.2%)
  SOL  •  $145.67  (▲0.8%)

🇵🇭  PSE STOCKS
  BDO  •  ₱145.50  (▲0.5%)
  SM  •  ₱890.00  (▼0.3%)
  TEL  •  ₱235.00  (▲1.1%)
  ALI  •  ₱32.50  (▼0.8%)
  JFC  •  ₱250.00  (▲0.2%)
```

### Data Sources

| Section | Source | Key Required |
|---------|--------|-------------|
| Weather | [Open-Meteo](https://open-meteo.com/) | None |
| Quote | [ZenQuotes](https://zenquotes.io/) | None |
| News | [BBC RSS Feed](https://feeds.bbci.co.uk/news/rss.xml) | None |
| Crypto | [yfinance](https://pypi.org/project/yfinance/) | None |
| PH Stocks | [Twelve Data](https://twelvedata.com/) | TWELVEDATA_API_KEY |
| Schedule | GitHub Actions cron | None |

Weather, quotes, news, and crypto are free with no registration. PH stocks require a free Twelve Data API key.

## Project Structure

```
automations/
├── .github/workflows/daily-email.yml   # GitHub Actions schedule
├── .gitignore
├── requirements.txt                    # yfinance
├── send_email.py                       # Core automation script
├── index.html                          # Landing page (GitHub Pages)
└── README.md
```

## Setup

### 1. Gmail App Password

This script sends email via Gmail's SMTP server. You need a Gmail account with an **App Password**:

1. Enable [2-Step Verification](https://myaccount.google.com/security) on your Google Account
2. Go to [App Passwords](https://myaccount.google.com/apppasswords)
3. Select **Mail** as the app and your device, then click **Generate**
4. Copy the 16-character password

### 2. (Optional) Twelve Data API Key

For PH stock prices, sign up for a free account at [Twelve Data](https://twelvedata.com/) and get an API key.

### 3. GitHub Secrets

In your GitHub repository, go to **Settings → Secrets and variables → Actions** and add:

| Secret | Value |
|--------|-------|
| `SENDER_EMAIL` | Your Gmail address |
| `SENDER_PASSWORD` | The 16-character app password |
| `RECEIVER_EMAIL` | Where you want the email delivered |
| `TWELVEDATA_API_KEY` | (Optional) Twelve Data API key for PH stocks |

### 4. Enable the Workflow

Push the repo to GitHub. The workflow is already configured to run daily at 2PM PH time. You can also trigger it manually from the Actions tab.

## Local Development

### Preview the email without sending

```bash
pip install -r requirements.txt
python send_email.py --dry-run
```

This fetches live data and prints the email to your terminal.

### Run with a .env file

Create a `.env` file (it's gitignored by default):

```
SENDER_EMAIL=your.email@gmail.com
SENDER_PASSWORD=your-app-password
RECEIVER_EMAIL=you@example.com
TWELVEDATA_API_KEY=your-twelve-data-key
```

Then run:

```bash
python send_email.py --local
```

This loads variables from `.env` and sends the email.

### Change city / coordinates

Edit the default values in the `Config` dataclass at the top of `send_email.py`:

```python
@dataclass(frozen=True)
class Config:
    ...
    lat: float = 11.6083       # Borongan City latitude
    lon: float = 125.4358      # Borongan City longitude
    city: str = "Borongan City, Eastern Samar"
```

## How It Works

```
┌─────────────┐    ┌──────────────────┐    ┌──────────────┐
│  GitHub      │    │  send_email.py   │    │  External    │
│  Actions     │───▶│                  │───▶│  APIs        │
│  (cron:      │    │  1. Load config  │    │              │
│   2PM PH)    │    │  2. Fetch data   │    │  • Open-Meteo│
└─────────────┘    │  3. Build email  │    │  • ZenQuotes │
                   │  4. Send via     │    │  • BBC RSS   │
                   │     Gmail SMTP   │    │  • yfinance  │
                   └────────┬─────────┘    │  • TwelveData│
                            │              └──────────────┘
                   ┌────────▼─────────┐
                   │  Your Inbox      │
                   └──────────────────┘
```

### Error Handling

- **API failures**: Each external API call retries up to 2 times with a 3-second delay before falling back to an error message in the email.
- **SMTP failures**: If sending fails, the email is saved to a local file (`email_fallback_YYYYMMDD_HHMMSS.txt`) instead of being lost.
- **Workflow failures**: If the entire GitHub Actions run fails, a push notification is sent via [ntfy.sh](https://ntfy.sh/daily-brief-julius).

## Requirements

- Python 3.9+
- [yfinance](https://pypi.org/project/yfinance/) (for crypto prices)

## Failure Notifications

On workflow failure, a push notification is sent to **ntfy.sh/daily-brief-julius**. Subscribe on your phone via the [ntfy app](https://ntfy.sh/) or use any ntfy-compatible client.
