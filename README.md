# Automated Trading Bot

Multi-strategy OANDA forex trading bot with backtesting, risk management, and live execution. Evolved from the [swing-trader](https://github.com/Kaireega/swing-trader) codebase.

**Current mode:** Swing trading on H1/H4/D1 timeframes (converted from intraday in March 2026).

---

## Quick start

### 1. Install

```bash
git clone https://github.com/Kaireega/Automated_trading_bot.git
cd Automated_trading_bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Add your OANDA practice account credentials
```

| Variable | Required | Description |
|----------|----------|-------------|
| `OANDA_API_KEY` | Yes | OANDA API bearer token |
| `OANDA_ACCOUNT_ID` | Yes | OANDA account ID |
| `OANDA_URL` | No | Default: practice API |
| `OPENAI_API_KEY` | No | AI analysis (optional) |
| `TELEGRAM_BOT_TOKEN` | No | Trade alerts |
| `TELEGRAM_CHAT_ID` | No | Alert destination |

Active strategy config: `src/trading_bot/src/config/trading_config.yaml`

### 3. Run

```bash
# Backtest (30 days)
python run.py backtest --days 30

# Backtest specific pairs
python run.py backtest --days 90 --pairs EUR_USD GBP_USD

# Validate configuration
python run.py validate

# Live trading (paper account recommended)
python run.py live
```

---

## Features

- **Multi-strategy framework** — trend, mean reversion, breakout, session-based strategies with weighted consensus
- **Swing trading** — H1/H4/D1 timeframes, 4-hour to 10-day hold windows
- **Backtesting engine** — historical simulation with configurable pairs and date ranges
- **Risk management** — per-trade risk %, daily loss limits, cooldown between entries
- **Notifications** — optional Telegram and email alerts
- **Market adaptation** — strategy selection based on detected market conditions

---

## Project structure

```
Automated_trading_bot/
├── run.py                          # Unified CLI entry point
├── requirements.txt                # Python dependencies
├── src/trading_bot/
│   ├── main.py                     # Live bot orchestrator
│   ├── src/
│   │   ├── config/trading_config.yaml   # Active strategy config
│   │   ├── strategies/             # Trading strategy implementations
│   │   ├── backtesting/            # Backtest engine
│   │   ├── core/                   # Models and managers
│   │   ├── decision/               # Risk management
│   │   ├── ai/                     # Technical analysis
│   │   └── notifications/          # Alert integrations
│   └── requirements.txt            # Detailed dependency list
├── src/technicals/                 # Shared indicators (from swing-trader)
├── src/infrastructure/             # OANDA helpers
└── docs/                           # Development session notes
```

---

## Configuration

Strategy parameters live in `src/trading_bot/src/config/trading_config.yaml`:

- **Risk:** 1% per trade, max 2 trades/day
- **Timeframes:** H4 primary, H1/D1 confirmation
- **Pairs:** EUR_USD, GBP_USD (configurable)
- **Hold times:** 4 hours minimum, 10 days maximum

> **Note:** A legacy config stub exists at `src/trading_bot/config/trading_config.yaml` — do not edit it. Use the `src/config/` path above.

---

## Deep-dive documentation

See [`docs/`](docs/) for development session notes and handoff reports, including `08_trading_bot_handoff_report.md`.

---

## Disclaimer

Forex trading carries significant financial risk. This bot defaults to OANDA's **practice** API. Validate all strategies with backtesting before live deployment. The author is not responsible for financial losses.

---

## Related projects

- [swing-trader](https://github.com/Kaireega/swing-trader) — ancestor codebase with Bollinger Band streaming bot
- [notificactionn-bot](https://github.com/Kaireega/notificactionn-bot) — AI-assisted trading with Telegram notifications
- [full_forex_box](https://github.com/Kaireega/full_forex_box) — full-stack platform with dashboards

---

## Author

**Kai'ree Gay** — [GitHub](https://github.com/Kaireega)
