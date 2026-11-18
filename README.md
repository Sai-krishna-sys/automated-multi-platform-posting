# Automated Multi-Platform Posting System

FastAPI service for posting a validated message to multiple platforms.

## Setup

1. Create a virtual environment and install dependencies:

```bash
python -m venv venv
venv\Scripts\pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and fill in platform credentials.

3. Run the API:

```bash
venv\Scripts\uvicorn app.main:app --reload --port 4000
```

4. Run tests:

```bash
venv\Scripts\pytest
```

## Environment variables

- `BLUESKY_HANDLE`, `BLUESKY_APP_PASSWORD`, `BLUESKY_SERVICE`
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- `MASTODON_BASE_URL`, `MASTODON_ACCESS_TOKEN`
- `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`
- `LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_PERSON_URN`

## Sample request

```bash
curl -X POST http://127.0.0.1:4000/posting \
  -H "Content-Type: application/json" \
  -d '{"message": "Testing my automated multi-platform posting system https://example.com"}'
```

## Sample response

```json
{
  "results": [
    {
      "platform": "bluesky",
      "status": "not_configured",
      "posted_url": null,
      "public_access": null,
      "date": null,
      "time": null,
      "error": "missing Bluesky credentials"
    },
    {
      "platform": "telegram",
      "status": "not_configured",
      "posted_url": null,
      "public_access": null,
      "date": null,
      "time": null,
      "error": "missing Telegram credentials"
    },
    {
      "platform": "mastodon",
      "status": "not_configured",
      "posted_url": null,
      "public_access": null,
      "date": null,
      "time": null,
      "error": "missing Mastodon credentials"
    },
    {
      "platform": "x",
      "status": "not_configured",
      "posted_url": null,
      "public_access": null,
      "date": null,
      "time": null,
      "error": "missing X credentials"
    },
    {
      "platform": "linkedin",
      "status": "not_configured",
      "posted_url": null,
      "public_access": null,
      "date": null,
      "time": null,
      "error": "missing LinkedIn credentials"
    }
  ]
}
```

## Known limitations

- Confirmed real posting: Bluesky, Telegram, Mastodon, and LinkedIn.
- X real posting is not verified because API credits are depleted.
- Platform behavior depends on valid credentials and external API availability.
