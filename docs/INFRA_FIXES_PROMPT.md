# PROMPT: Infrastructure Fixes — Pre-Live Blockers & Safety Gaps

## Who You Are

You are a **Senior Software Engineer** clearing the last infrastructure blockers before a trading bot goes live. The strategy layer is being overhauled separately — don't touch strategy files. Your job is strictly the plumbing: fix the crash, verify safety features, fix the journal, and ensure nothing breaks when the strategy overhaul lands.

---

## Context

The strategy overhaul (replacing 9-strategy consensus with 2-strategy regime switch) is being done in a separate session. This prompt covers ONLY infrastructure items that were wired in Session 7 but have unresolved issues.

**Read `19_SESSION7_REPORT.md`** for the full current state.

**Items to fix:**
1. Live blocker — `main.py` crashes with `'str' object has no attribute 'value'`
2. Pre-trade cooldown — config says 30s, enforcement not verified
3. MongoDB journal — SSL error, trades not recording, need a fallback
4. `config.env` — may still exist, blocking real credentials
5. News gatekeeper — wired but may be returning stub data
6. Safety feature survival — make sure the strategy overhaul doesn't erase weekend/hour blocks, risk gates, trailing stops

---

## Step 0: Create Tracker

Create `INFRA_FIX_TRACKER.md` in the project root:

```markdown
# Infrastructure Fix Tracker
> Clearing pre-live blockers. Strategy overhaul handled separately.
> Started: [date/time]

| # | Fix | Status | Verified? |
|---|-----|--------|-----------|
| 1 | main.py TimeFrame string/enum crash | ⬜ | ⬜ |
| 2 | Pre-trade cooldown enforcement | ⬜ | ⬜ |
| 3 | Trade journal fallback (file-based if MongoDB fails) | ⬜ | ⬜ |
| 4 | config.env deletion | ⬜ | ⬜ |
| 5 | News gatekeeper data source | ⬜ | ⬜ |
| 6 | Safety feature checklist after overhaul | ⬜ | ⬜ |
```

---

## Fix 1: Live Blocker — TimeFrame String vs Enum

**CRITICAL — bot cannot trade live without this.**

`main.py` crashes because the data layer returns string keys (`"H4"`, `"H1"`) but `main.py` calls `.value` on them expecting `TimeFrame` enums.

```bash
grep -n "\.value" src/trading_bot/main.py | head -20
grep -n "TimeFrame\.M5" src/trading_bot/main.py
```

**Fix: normalize keys at the source.** Find where `main.py` receives candle data and convert once:

```python
from trading_bot.src.core.models import TimeFrame

def _normalize_timeframe_keys(candles_dict):
    normalized = {}
    for key, candles in candles_dict.items():
        if isinstance(key, str):
            try:
                key = TimeFrame(key)
            except ValueError:
                pass
        normalized[key] = candles
    return normalized
```

Call this wherever candle data enters the analysis pipeline. Then replace ALL `TimeFrame.M5` references with the correct timeframe (`TimeFrame.H4` for now — `TimeFrame.D1` after the strategy overhaul adds it):

```bash
grep -n "M5" src/trading_bot/main.py
```

**Verify:** `python3 run.py live` starts and completes at least 3 analysis loops without the `'str' object has no attribute 'value'` error.

---

## Fix 2: Pre-Trade Cooldown Enforcement

Config says `pre_trade_cooldown_seconds: 30` but nobody confirmed the code checks it.

```bash
grep -rn "cooldown\|pre_trade_cool\|last_trade_time" src/trading_bot/main.py src/trading_bot/src/core/position_manager.py
```

If there's no elapsed-time check, add one:

```python
# Before execute_trade in main.py:
cooldown = getattr(self.config.trading, 'pre_trade_cooldown_seconds', 30)
if hasattr(self, '_last_trade_time') and self._last_trade_time:
    elapsed = (datetime.utcnow() - self._last_trade_time).total_seconds()
    if elapsed < cooldown:
        self.logger.debug(f"Cooldown: {cooldown - elapsed:.0f}s remaining")
        continue

# After successful trade execution:
self._last_trade_time = datetime.utcnow()
```

Initialize `self._last_trade_time = None` in `__init__`.

---

## Fix 3: Trade Journal Fallback

MongoDB Atlas fails with `TLSV1_ALERT_INTERNAL_ERROR`. Trades are not being recorded. This blocks future ML training (Phase 4 from the original roadmap needs trade data).

**Add a file-based fallback** that writes when MongoDB is unavailable:

```python
import json
from pathlib import Path
from datetime import datetime

class FileTradeJournal:
    def __init__(self, filepath="results/trade_journal.jsonl"):
        self.filepath = filepath
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

    def record_open(self, trade_data):
        trade_data['recorded_at'] = datetime.utcnow().isoformat()
        trade_data['event'] = 'open'
        with open(self.filepath, 'a') as f:
            f.write(json.dumps(trade_data, default=str) + '\n')

    def record_close(self, trade_id, exit_data):
        exit_data['trade_id'] = trade_id
        exit_data['recorded_at'] = datetime.utcnow().isoformat()
        exit_data['event'] = 'close'
        with open(self.filepath, 'a') as f:
            f.write(json.dumps(exit_data, default=str) + '\n')
```

Wire it in `position_manager.py` as a fallback:

```python
# In __init__:
self._file_journal = FileTradeJournal("results/trade_journal.jsonl")

# On trade open:
if self._mongo_collection:
    try:
        self._mongo_collection.insert_one(trade_data)
    except Exception as e:
        self.logger.warning(f"MongoDB write failed: {e}")
        self._file_journal.record_open(trade_data)
else:
    self._file_journal.record_open(trade_data)

# On trade close:
if self._mongo_collection:
    try:
        self._mongo_collection.update_one(...)
    except Exception:
        self._file_journal.record_close(trade_id, exit_data)
else:
    self._file_journal.record_close(trade_id, exit_data)
```

This way trades are always recorded somewhere — MongoDB if it works, JSONL file if it doesn't.

---

## Fix 4: Delete config.env

```bash
ls -la config.env 2>/dev/null && echo "⚠️ DELETE THIS FILE" || echo "✅ Already gone"
```

If it exists, delete it. It has placeholder credentials that override the real ones in `.env`:

```bash
rm config.env
```

Also verify `.env` points to practice, not live:
```bash
grep "OANDA_URL" .env
# Must be: https://api-fxpractice.oanda.com/v3
# NOT: https://api-fxtrade.oanda.com/v3
```

---

## Fix 5: News Gatekeeper Data Source

Session 7 wired `should_block_trading()` in `main.py`, but the debug journal originally flagged `fundamental_analyzer.py` as "returns stub data." Check if it's actually pulling real events:

```bash
grep -n "should_block_trading\|get_upcoming\|fetch.*event\|def analyze" src/trading_bot/src/core/fundamental_analyzer.py
```

**If it always returns False or has no real data source**, add a static high-impact schedule as a minimum:

```python
# In fundamental_analyzer.py:

# Known recurring high-impact USD events (UTC)
RECURRING_HIGH_IMPACT = [
    # (weekday, hour, minute, description)
    # Wednesday FOMC / Fed minutes (not every week, but block the window)
    (2, 18, 0, "FOMC announcement window"),
    (2, 19, 0, "FOMC press conference window"),
    # Friday NFP — first Friday of each month, 13:30 UTC
    (4, 13, 0, "NFP / employment data window"),
    (4, 13, 30, "NFP / employment data window"),
    (4, 14, 0, "NFP aftermath"),
]

async def should_block_trading(self, pair: str) -> bool:
    """Block trading 30 min before and after high-impact events."""
    now = datetime.utcnow()

    # Check recurring schedule
    for weekday, hour, minute, desc in RECURRING_HIGH_IMPACT:
        if now.weekday() == weekday:
            event_time_today = now.replace(hour=hour, minute=minute, second=0)
            minutes_diff = abs((now - event_time_today).total_seconds()) / 60
            if minutes_diff <= 30:
                self.logger.info(f"News block: {desc} for {pair}")
                return True

    # If external API is connected, also check dynamic events
    try:
        if self._has_external_calendar:
            return await self._check_external_calendar(pair, now)
    except Exception:
        pass  # fail open — don't block on API errors

    return False
```

This is a stopgap — it blocks trading around FOMC and NFP windows, which are the two events most likely to cause flash moves that blow through stops. A proper API integration can replace it later.

**For EUR-specific events**, add ECB rate decisions (typically Thursday, every 6 weeks) and for GBP, add BOE decisions. These are less frequent so a static list updated monthly is fine.

---

## Fix 6: Safety Feature Survival Checklist

The strategy overhaul rewrites `strategy_manager.py` and may touch `main.py` and `technical_analysis_layer.py`. After the overhaul lands, run this checklist to verify nothing was erased:

```bash
# Weekend block — must exist in new strategy_manager.py generate_signal()
grep -n "weekday\|weekend\|saturday\|sunday" src/trading_bot/src/strategies/strategy_manager.py

# Hour block — must exist in new generate_signal()
grep -n "BLOCKED_HOURS\|hour.*block\|blocked.*hour" src/trading_bot/src/strategies/strategy_manager.py

# News gatekeeper — must still be called in main.py
grep -n "should_block_trading\|fundamental\|news" src/trading_bot/main.py

# AdvancedRiskManager gate — must still be checked before execute_trade
grep -n "assess.*risk\|risk.*approved\|risk_result" src/trading_bot/main.py

# PortfolioRiskManager gate — must still be checked
grep -n "portfolio.*risk\|assess_portfolio\|correlation" src/trading_bot/main.py

# Trailing stop monitor — must still be in position_manager
grep -n "trailing\|_update_trailing\|_monitor" src/trading_bot/src/core/position_manager.py

# Consecutive loss limit — must still be in backtest
grep -n "consecutive.*loss\|loss_limit\|cooldown" src/trading_bot/src/backtesting/backtest_engine.py

# Telegram notifications — must still fire on trade events
grep -n "send.*notification\|notify\|telegram" src/trading_bot/src/core/position_manager.py src/trading_bot/main.py

# Trade journal — must still record (file or MongoDB)
grep -n "journal\|record_trade\|mongo\|jsonl" src/trading_bot/src/core/position_manager.py
```

**If any of these return nothing after the overhaul**, the feature was erased and must be re-added. Create a list of what's missing and add it back into the new code.

**The weekend block and hour blocks are the most likely to be lost** because they were inside `strategy_manager.py` which is being rewritten. Make sure the new `generate_signal()` method includes them before the regime detection logic.

---

## Rules

1. **Don't touch strategy files.** The overhaul is handling those separately.
2. **Fix 1 (live blocker) is the highest priority.** Do it first.
3. **Fix 3 (journal fallback) ensures you collect trade data** even if MongoDB never works. You need this data for Phase 4 ML.
4. **Fix 6 (safety checklist) should be run AFTER the strategy overhaul completes**, not before. It's a post-merge verification.
5. **Update `INFRA_FIX_TRACKER.md` after each fix.**
6. **Verify the bot can start and run 3 analysis loops after Fix 1** before moving to the other fixes.

**Begin now. Create `INFRA_FIX_TRACKER.md`, then fix the live blocker (Fix 1).**
