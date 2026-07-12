# Security Policy

## Reporting a vulnerability

If you discover a security issue, please open a private report via GitHub Security Advisories or contact the maintainer directly. Do not open public issues for undisclosed vulnerabilities.

## Credential management

This project uses environment variables for all secrets. **Never commit:**

- `config.env`, `.env`, or any file containing real API keys
- OANDA API keys or account IDs
- OpenAI, Telegram, email, or MongoDB credentials

Use `.env.example` as a template only.

## If credentials were ever exposed

The following services should be **rotated immediately** if keys were previously committed to git:

| Service | Where to rotate |
|---------|-----------------|
| OANDA | [OANDA account settings](https://www.oanda.com/) → Manage API Access |
| OpenAI | [OpenAI API keys](https://platform.openai.com/api-keys) |
| Telegram | [@BotFather](https://t.me/BotFather) → revoke and regenerate token |
| Gmail app password | [Google Account security](https://myaccount.google.com/apppasswords) |
| MongoDB Atlas | Atlas → Database Access → rotate password |

Git history has been scrubbed of known leaked values, but rotation is still required because keys may have been cached or accessed before removal.

## Prevention

- CI runs secret scanning on every push (see `.github/workflows/secret-scan.yml`)
- Smoke tests verify `.env.example` contains no real credentials
- Runtime config loads from environment variables only
