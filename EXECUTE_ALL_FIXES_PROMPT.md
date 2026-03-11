# PROMPT: Full Debug Execution — Forex Trading Bot

## Who You Are

You are a **Senior Software Engineer and QA Analyst**. You are methodical, precise, and you verify everything. You never assume a fix works — you prove it. You never skip a file. You fix root causes, not symptoms.

---

## Context

A full audit of this Forex trading bot has already been completed. The results are documented in `DEBUG_JOURNAL.md` at the project root. That file is your **source of truth**. Read it first. It contains:

- 40 catalogued issues (13 critical, 15 warnings, 12 info)
- A prioritized fix list with exact code snippets
- Architecture diagrams showing the broken data flow
- The root cause chain explaining why backtests produce a ~4% win rate
- Config inconsistencies between YAML values and inline comments

**Your job is to execute every fix, verify it, and track your progress.**

---

## Step 0: Create Your Progress Tracker

Before writing a single line of code, create a file called `FIX_TRACKER.md` in the project root. This is your living reference. You will update it after every fix.

```markdown
# Fix Tracker
> Execution log for all fixes applied to the trading bot.
> Started: [date/time]
> Last updated: [date/time]

## Status Summary
- Total fixes planned: 25
- Completed: 0
- Verified: 0
- Blocked: 0

## Fix Log
| Fix # | Target File(s) | Description | Applied? | Verified? | Notes |
|-------|----------------|-------------|----------|-----------|-------|
| 1     | run.py         | bot.run() → bot.start() | ⬜ | ⬜ | — |
| 2     | config.py + YAML | Add max_risk_threshold to RiskManagementConfig | ⬜ | ⬜ | — |
| 3     | models.py      | Add metadata field to TradeRecommendation | ⬜ | ⬜ | — |
| 4     | london_open_break.py, ny_open_momentum.py | candle.time → candle.timestamp | ⬜ | ⬜ | — |
| 5     | register_all.py | Import FastIchimokuStrategy | ⬜ | ⬜ | — |
| 6     | position_manager.py | Initialize scaling_levels/partial_exits in _record_trade() | ⬜ | ⬜ | — |
| 7     | main.py        | Add continue after notification exception | ⬜ | ⬜ | — |
| 8     | backtest_engine.py | Fix detect_regime() call signature | ⬜ | ⬜ | — |
| 9     | technical_analysis_layer.py | Remove hardcoded MarketCondition.BREAKOUT | ⬜ | ⬜ | — |
| 10    | position_manager.py | Call _can_execute_trade() in execute_trade() | ⬜ | ⬜ | — |
| 11    | position_manager.py | Fix daily_pnl vs max_daily_loss type mismatch | ⬜ | ⬜ | — |
| 12    | technical_analysis_layer.py + strategy_manager.py | Read min_confluence_score and consensus_threshold from config | ⬜ | ⬜ | — |
| 13    | data_layer.py  | Implement real market condition detection | ⬜ | ⬜ | — |
| 14    | position_manager.py | Make _adjust_stop_losses() actually call OANDA API | ⬜ | ⬜ | — |
| 15    | position_manager.py | Use OANDA partial close API in _partial_exit() | ⬜ | ⬜ | — |
| 16    | position_manager.py | Add realized P&L to _update_daily_pnl() | ⬜ | ⬜ | — |
| 17    | trading_config.yaml | Add max_risk_threshold: 0.7 | ⬜ | ⬜ | — |
| 18    | config/trading_config.yaml | Delete empty file or add redirect comment | ⬜ | ⬜ | — |
| 19    | register_all.py | Import DonchianBreak, SpreadSqueeze, OrderFlowMomentum | ⬜ | ⬜ | — |
| 20    | .gitignore     | Verify .env is gitignored and not committed | ⬜ | ⬜ | — |
| 21    | run.py or main.py | Add load_dotenv() at startup | ⬜ | ⬜ | — |
| 22    | Dead code files | Remove or document unused modules | ⬜ | ⬜ | — |
| 23    | trading_config.yaml | Fix contradictory comments | ⬜ | ⬜ | — |
| 24    | Project root   | Move backtest reports to results/ | ⬜ | ⬜ | — |
| 25    | main.py        | Fix timeframe gate: < 2 → use config.minimum_timeframes | ⬜ | ⬜ | — |

## Regressions Found
| # | Fix That Caused It | What Broke | Resolution |
|---|-------------------|------------|------------|
| — | — | — | — |

## New Issues Discovered During Fixes
| # | Severity | File | Description |
|---|----------|------|-------------|
| — | — | — | — |

## Verification Tests Run
| # | What Was Tested | Method | Result |
|---|-----------------|--------|--------|
| — | — | — | — |
```

**Update this file after EVERY fix. This is non-negotiable.**

---

## Step 1: Read the Audit

1. Read `DEBUG_JOURNAL.md` completely. Understand every issue.
2. Read the architecture flow diagrams. Understand why the bot fails end-to-end.
3. Read the "Root Cause of 4% Win Rate" section. This is the chain you are breaking.

---

## Step 2: Apply Fixes In Order

Follow this exact order. The grouping matters — later fixes depend on earlier ones.

### Group A — Bot Cannot Start (Fixes 1–8)
These must be applied first. Without them the bot crashes on startup or within seconds.

**Fix 1 — `run.py` line ~318**
Change `await bot.run()` to `await bot.start()`. The `TradingBot` class has no `run()` method.

**Fix 2 — `src/trading_bot/src/utils/config.py` + active YAML**
Add `max_risk_threshold: float = 0.7` to the `RiskManagementConfig` dataclass. Also add `max_risk_threshold: 0.7` under the `risk_management:` section in `src/trading_bot/src/config/trading_config.yaml`.

**Fix 3 — `src/trading_bot/src/core/models.py`**
Add `metadata: Dict[str, Any] = field(default_factory=dict)` to the `TradeRecommendation` dataclass. Add the necessary imports (`Dict`, `Any`, `field`).

**Fix 4 — Session strategies**
In `src/trading_bot/src/strategies/session_based/london_open_break.py` (~line 72) and `ny_open_momentum.py` (~line 79): change every `candle.time` to `candle.timestamp`. Use safe access:
```python
candle_time = candle.timestamp.time() if hasattr(candle.timestamp, 'time') else candle.timestamp
```

**Fix 5 — `src/trading_bot/src/strategies/register_all.py`**
Add import: `from .trend_momentum.fast_ichimoku import FastIchimokuStrategy`

**Fix 6 — `src/trading_bot/src/core/position_manager.py`**
In `_record_trade()`, add these keys to the active_positions dict:
```python
'scaling_levels': [],
'partial_exits': [],
```
Look at `_track_new_position()` (which already has these) for reference — it exists but is never called. Consider whether to call it instead of `_record_trade()`, or merge the missing fields into `_record_trade()`.

**Fix 7 — `src/trading_bot/main.py` ~line 426**
In the `except` block after `_send_pre_trade_notification()` fails, add `continue` so the loop does not fall through to `execute_trade()`:
```python
except Exception as e:
    self.logger.error(f"Pre-trade notification failed: {e}")
    continue   # CRITICAL: prevent trade executing without approval
```

**Fix 8 — `src/trading_bot/src/backtesting/backtest_engine.py`**
Find the call to `market_regime_detector.detect_regime(pair, candles_by_tf)` (2 args). The actual method signature requires 4 args: `detect_regime(pair, candles, market_context, technical_indicators)`. Pass the correct arguments. Check what `market_context` and `technical_indicators` are available at the call site and pass them in.

**After Group A**: Run `python -c "from src.trading_bot.main import TradingBot; print('Import OK')"` or equivalent syntax check to verify no import errors or immediate crashes.

---

### Group B — Bot Trades But Incorrectly (Fixes 9–13)
These fix the logic so the bot makes correct decisions.

**Fix 9 — `src/trading_bot/src/ai/technical_analysis_layer.py` ~line 591**
Replace the hardcoded `market_condition=MarketCondition.BREAKOUT` with the actual market condition from the analysis context. Use:
```python
market_condition=market_context.condition if market_context else MarketCondition.UNKNOWN
```
If `MarketCondition.UNKNOWN` doesn't exist, add it to the enum, or use a sensible default.

**Fix 10 — `src/trading_bot/src/core/position_manager.py`**
Add `_can_execute_trade()` as the first check in `execute_trade()`:
```python
async def execute_trade(self, decision):
    if not await self._can_execute_trade(decision):
        self.logger.warning("Trade blocked by safety checks")
        return None
    # ... rest of existing code
```
If `_can_execute_trade` is not async, remove the `await`.

**Fix 11 — `src/trading_bot/src/core/position_manager.py` ~line 380**
Fix the daily P&L comparison. `daily_pnl` is in dollars, `max_daily_loss` is a percentage. Convert:
```python
max_daily_loss_dollars = self.account_balance * (self.max_daily_loss / 100)
if self.daily_pnl <= -max_daily_loss_dollars:
    return False  # daily loss limit hit
```
Find where `account_balance` is accessible. If it's not on `self`, trace it through the config or add it.

**Fix 12 — Read from config, not hardcoded**
In `technical_analysis_layer.py`: replace hardcoded `min_confluence_score = 0.2` with `self.config.technical_analysis.min_confluence_score` (should be 0.6 from YAML). Replace `min_signals_required = 1` similarly if config has a different value.

In `strategy_manager.py`: replace hardcoded `consensus_threshold = 0.30` with `self.config.multi_timeframe.consensus_threshold` (should be 0.75 from YAML).

**Fix 13 — `src/trading_bot/src/data/data_layer.py`**
In `_create_market_context_from_candles()`, implement real market condition detection instead of always returning `RANGING`. Use the candle data to compute:
- ATR or volatility measure to detect HIGH_VOLATILITY vs LOW_VOLATILITY
- Trend detection (moving average slope or ADX) to detect TRENDING vs RANGING
- Breakout detection (price vs recent highs/lows) to detect BREAKOUT

At minimum, use a simple ADX-based approach:
```python
# If ADX > 25: TRENDING
# If ADX < 20 and volatility low: RANGING
# If price breaks 20-period high/low: BREAKOUT
# Else: NORMAL
```

**After Group B**: Run the backtest with the same parameters as before. The win rate should be dramatically different from 4%. Log the results in `FIX_TRACKER.md`.

---

### Group C — Safety & Quality (Fixes 14–25)

**Fix 14** — `position_manager.py _adjust_stop_losses()`: After calculating `new_stop_loss`, actually call the OANDA API to update the trade's stop-loss. Look at existing OANDA API calls in the codebase for the correct method/syntax.

**Fix 15** — `position_manager.py _partial_exit()`: Use OANDA's partial close API (units parameter) instead of `close_trade()` which closes 100%. The OANDA v20 API supports partial closes by specifying units.

**Fix 16** — `position_manager.py _update_daily_pnl()`: Include realized P&L from closed trades, not just unrealized from open positions.

**Fix 17** — Add `max_risk_threshold: 0.7` to the active YAML under `risk_management:` (may already be done in Fix 2 — verify).

**Fix 18** — Delete the empty `src/trading_bot/config/trading_config.yaml` or add a comment redirecting to the real config path.

**Fix 19** — In `register_all.py`, add imports for:
```python
from .breakout.donchian_break import DonchianBreakStrategy
from .scalping.spread_squeeze import SpreadSqueezeStrategy
from .scalping.order_flow_momentum import OrderFlowMomentumStrategy
```
Verify these classes exist in their files and have the `@register_strategy` decorator.

**Fix 20** — Run `git log --all -- .env` to verify .env hasn't been committed. If it has, note this as a security issue in `FIX_TRACKER.md` (requires `git filter-branch` or BFG to remove from history). Verify `.env` is in `.gitignore`.

**Fix 21** — Add `from dotenv import load_dotenv; load_dotenv()` at the top of `run.py` (or wherever the entry point is), before any config is read. If `python-dotenv` is not in requirements, add it.

**Fix 22** — For each dead code file (`smart_execution_engine.py`, `portfolio_risk_manager.py`, `order_flow_analyzer.py`, `performance_attribution.py`), either:
- Delete it and remove any imports, OR
- Add a `# TODO: Not connected to main flow` comment at the top

**Fix 23** — Go through `trading_config.yaml` and fix every comment that contradicts its value. The journal lists these in the "Config Inconsistencies" table.

**Fix 24** — Create a `results/` directory, move all `backtest_report_*.txt` files into it, and add `results/` to `.gitignore`.

**Fix 25** — In `main.py` ~line 232, change `if len(candles_by_timeframe) < 2` to read from config: `if len(candles_by_timeframe) < self.config.multi_timeframe.minimum_timeframes`.

---

## Step 3: Verification Protocol

After ALL fixes are applied, run these checks:

### Syntax & Import Check
```bash
# Check every Python file compiles
find . -name "*.py" -exec python -m py_compile {} \;

# Check for circular imports
python -c "from src.trading_bot.main import TradingBot"
python -c "from src.trading_bot.src.backtesting.backtest_engine import BacktestEngine"
```

### Trace the Critical Path
Mentally (or via test script) trace the two main flows after fixes:

**Live trading flow:**
```
run.py → bot.start() [Fix 1]
  → get_market_context() → real condition [Fix 13], not always RANGING
  → strategy_manager with all strategies registered [Fixes 5, 19]
  → session strategies use candle.timestamp [Fix 4]
  → consensus_threshold read from config (0.75) [Fix 12]
  → _create_consensus_recommendation() with metadata field [Fix 3]
  → AdvancedRiskManager.assess_trade_risk() with max_risk_threshold [Fix 2]
  → _can_execute_trade() called [Fix 10] with correct daily loss calc [Fix 11]
  → notification failure doesn't bypass approval [Fix 7]
  → position recorded with scaling_levels/partial_exits [Fix 6]
```

**Backtest flow:**
```
run.py → BacktestEngine
  → detect_regime() called with 4 args [Fix 8]
  → same strategy/analysis fixes apply
```

### Regression Check
- Does the bot still start without errors?
- Does the backtest complete without TypeError/AttributeError?
- Are config values being read (not hardcoded)?
- Do session strategies (London Open, NY Open) produce signals?
- Does the consensus mechanism produce recommendations without TypeError?
- Does the risk manager approve valid trades?

---

## Rules You Must Follow

1. **Read `DEBUG_JOURNAL.md` before doing anything.** It has all the context.
2. **Update `FIX_TRACKER.md` after every fix.** Mark applied and verified status.
3. **One fix at a time.** Apply → verify → log → next.
4. **If a fix reveals a new issue, log it** in the "New Issues" section of `FIX_TRACKER.md`.
5. **If a fix breaks something else, log it** in the "Regressions" section and fix the regression before moving on.
6. **Never assume — always verify.** After changing a file, confirm the change doesn't break imports or logic.
7. **Fix root causes, not symptoms.** The journal explains the root cause chain. Follow it.
8. **Read the actual code before applying each fix.** Line numbers may have shifted. Find the right location by code context, not just line number.
9. **Preserve existing behavior for things that work.** Don't refactor working code. Only change what's broken.
10. **If you're unsure about a fix, explain your uncertainty** in `FIX_TRACKER.md` and apply the safest version.

---

## When You Are Done

Your `FIX_TRACKER.md` should show:
- All 25 fixes applied and verified
- Any regressions found and resolved
- Any new issues discovered
- Verification test results
- A brief summary of the bot's state after all fixes

**Begin now. Read `DEBUG_JOURNAL.md`, create `FIX_TRACKER.md`, then start with Fix 1.**
