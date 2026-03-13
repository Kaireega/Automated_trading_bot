# PROMPT: Fix Regime Detection Gaps + Run Verification Backtest

## Who You Are

You are a **Senior Quantitative Developer** finalizing a swing trading bot. You're in the tuning phase — the architecture is sound, the major bugs are fixed, and now you're hunting the subtle issues that separate a losing bot from a profitable one. Small details in regime detection directly determine which strategies fire and which don't, so precision matters here.

---

## Context

**Read these files — they are your source of truth:**
1. `PROFITABILITY_TRACKER.md` — current state (P-1 through P-5 applied, two new issues found)
2. `SWING_CONVERSION_TRACKER.md` — swing conversion details
3. `DEBUG_JOURNAL.md` — original architecture and data flow

**Current state:**
- P-1 (enum), P-2/P-3 (regime gate wired), P-4 (5% auto-close removed), P-5 (trailing stop fixed) — all applied
- Backtest not yet run after P-1/P-5 changes
- Two new issues discovered:
  - **I-1 (Low):** `technical_analysis_layer.py:203` — primary timeframe defaults to M5 before fallback
  - **I-2 (Medium — upgrading from Low):** `data_layer.py:419` — `_determine_market_condition` never returns `TRENDING_DOWN`. Always labels trends as bullish regardless of direction.

**Why I-2 matters more than "Low":**
The regime gate maps `TRENDING_DOWN` → trend-following strategies eligible for SELL signals. If `TRENDING_DOWN` is never returned, the gate sees downtrends as something else (`RANGING`, `UNKNOWN`, or `TRENDING_UP`). This means:
- In a downtrend labeled `RANGING`: only mean-reversion strategies fire → they try to buy the dip in a downtrend → losses
- In a downtrend labeled `UNKNOWN`: no strategies fire → missed opportunities
- In a downtrend labeled `TRENDING_UP`: trend strategies fire but look for BUY signals → wrong direction
- Any of these explains suppressed trade count and poor win rate on short trades

---

## Step 0: Update Your Tracker

Open `PROFITABILITY_TRACKER.md` and add:

```markdown
## Phase 2: Regime Detection Fixes + Verification

| # | Description | Status |
|---|-------------|--------|
| I-2 | Fix _determine_market_condition to return TRENDING_DOWN | ⬜ |
| I-1 | Fix primary timeframe default from M5 to H4 | ⬜ |
| DIAG | Add per-trade regime + strategy diagnostic logging | ⬜ |
| BT-1 | Run 90-day verification backtest | ⬜ |
| BT-2 | Run 180-day extended backtest if BT-1 is promising | ⬜ |
```

---

## Fix I-2: TRENDING_DOWN Never Returned

### Step 1: Read the current detection logic

```bash
# Find the market condition detection function
grep -n "_determine_market_condition\|_create_market_context\|market_condition" src/trading_bot/src/data/data_layer.py
```

Read the full function. Look for where it decides between `TRENDING_UP` and `TRENDING_DOWN`. Common bugs:

```python
# BUG PATTERN 1: Only checks for uptrend
if adx > 25 and ema_fast > ema_slow:
    return MarketCondition.TRENDING_UP
# Missing: elif adx > 25 and ema_fast < ema_slow: return MarketCondition.TRENDING_DOWN

# BUG PATTERN 2: Uses "TRENDING" without direction suffix
if adx > 25:
    return MarketCondition.TRENDING  # This member might not exist in enum

# BUG PATTERN 3: Checks direction but uses wrong comparison
if slope > 0:
    return MarketCondition.TRENDING_UP
elif slope > 0:   # copy-paste bug — should be slope < 0
    return MarketCondition.TRENDING_DOWN
```

### Step 2: Also check the backtest engine's market context

The backtest engine has its own `_create_market_context()` (this was fixed in B-1). Check if IT also has the same TRENDING_DOWN gap:

```bash
grep -n "TRENDING\|market_condition\|determine.*condition\|regime" src/trading_bot/src/backtesting/backtest_engine.py
```

### Step 3: Fix both locations

The logic should use price direction relative to a trend indicator:

```python
def _determine_market_condition(self, candles):
    # Calculate indicators
    closes = [c.close for c in candles]
    
    # ADX for trend strength
    adx = calculate_adx(candles, period=14)
    
    # Direction: compare fast EMA vs slow EMA, or use price vs SMA
    ema_fast = calculate_ema(closes, period=12)
    ema_slow = calculate_ema(closes, period=26)
    
    # ATR for volatility
    atr = calculate_atr(candles, period=14)
    atr_pct = atr / closes[-1]  # ATR as % of price
    
    # Recent price range for consolidation/breakout
    recent_high = max(c.high for c in candles[-20:])
    recent_low = min(c.low for c in candles[-20:])
    range_pct = (recent_high - recent_low) / closes[-1]
    
    # Decision tree
    if adx > 25:
        if ema_fast > ema_slow:       # ← MUST CHECK DIRECTION
            return MarketCondition.TRENDING_UP
        else:
            return MarketCondition.TRENDING_DOWN   # ← THIS IS THE FIX
    
    if atr_pct > 0.015:  # high volatility threshold (tune for H4)
        return MarketCondition.VOLATILE
    
    if range_pct < 0.005:  # tight range (tune for H4)
        return MarketCondition.CONSOLIDATION
    
    # Check for breakout
    if closes[-1] > recent_high * 0.998 or closes[-1] < recent_low * 1.002:
        return MarketCondition.BREAKOUT
    
    return MarketCondition.RANGING
```

**Adapt this to the actual code structure.** The function may use different indicators or have different organization. The critical fix is: **add a direction check for TRENDING_DOWN wherever TRENDING_UP is returned.**

### Step 4: Verify TRENDING_DOWN appears in output

After fixing, add a temporary log statement and run a quick test:

```python
# Temporary diagnostic — remove after verification
logger.info(f"Regime detected: {condition.value} for {pair}")
```

Run the backtest and check logs:
```bash
grep "Regime detected" backtest.log | sort | uniq -c | sort -rn
```

Expected output should show a mix including TRENDING_DOWN:
```
  45 Regime detected: trending_up for EUR_USD
  38 Regime detected: trending_down for GBP_USD
  22 Regime detected: ranging for USD_JPY
  15 Regime detected: volatile for EUR_USD
  ...
```

If TRENDING_DOWN is still 0, the fix didn't take. If it's roughly similar count to TRENDING_UP, the fix is working.

---

## Fix I-1: Primary Timeframe Default

### Step 1: Find and fix

```bash
grep -n "M5\|primary.*timeframe\|default.*timeframe" src/trading_bot/src/ai/technical_analysis_layer.py
```

Line 203 should have a default or fallback that references M5. Change it to H4:

```python
# BEFORE:
primary_timeframe = TimeFrame.M5  # or "M5"

# AFTER:
primary_timeframe = TimeFrame.H4  # swing default
```

This is cosmetic since the fallback chain works, but it prevents confusion and ensures the first choice is the right one.

---

## DIAG: Add Per-Trade Diagnostic Logging

This is critical for ongoing tuning. Every trade that the backtest executes should log:

```python
logger.info(
    f"TRADE: {pair} {direction} | "
    f"regime={regime} | "
    f"strategies_agreed={strategy_names} | "
    f"confidence={confidence:.2f} | "
    f"entry={entry_price} | "
    f"stop={stop_loss} | "
    f"tp={take_profit} | "
    f"R:R={reward_risk_ratio:.1f} | "
    f"size={units} units"
)
```

And when a trade closes:

```python
logger.info(
    f"CLOSE: {pair} {direction} | "
    f"regime_at_entry={regime} | "
    f"exit_reason={reason} | "  # stop_loss, take_profit, trailing_stop, max_hold, signal_reversal
    f"pnl=${pnl:.2f} | "
    f"held={hold_duration_hours:.1f}h | "
    f"pips={pips_gained:.1f}"
)
```

**Where to add:** In the backtest engine's trade execution and trade closing logic. Also check `simulation_broker.py` if that handles execution.

This logging lets you diagnose patterns like:
- "All TRENDING_DOWN trades lose money" → trend detection is wrong
- "BB_Bounce in RANGING has 70% win rate but ATR_Breakout in BREAKOUT has 20%" → breakout detection is too loose
- "Most trades close at trailing stop, not TP" → trail may still be too tight
- "Average hold is 6 hours" → trades closing too fast for swing

---

## BT-1: Run 90-Day Verification Backtest

After I-2, I-1, and DIAG are applied, run the same 90-day backtest:

```bash
# Same pairs, same period, same starting balance as previous runs
python run.py --backtest  # or however it's invoked
```

**Record in the tracker:**

| Metric | Before P-1/P-5 | After I-2 Fix | Change |
|--------|----------------|---------------|--------|
| Trades (90d) | 12 | ? | ? |
| Win Rate | 41.7% | ? | ? |
| Profit Factor | 0.87 | ? | ? |
| Avg Win | $25.85 | ? | ? |
| Avg Loss | $21.33 | ? | ? |
| Max Drawdown | 13.91% | ? | ? |
| Return | -4.01% | ? | ? |

**Also record from diagnostic logs:**

| Regime | Trade Count | Win Rate | Avg P&L |
|--------|-------------|----------|---------|
| TRENDING_UP | ? | ? | ? |
| TRENDING_DOWN | ? | ? | ? |
| RANGING | ? | ? | ? |
| BREAKOUT | ? | ? | ? |
| VOLATILE | ? | ? | ? |
| CONSOLIDATION | ? | ? | ? |

**What to look for:**
1. **Trade count should increase** — TRENDING_DOWN trades were previously suppressed. Expect 15–25+ trades.
2. **TRENDING_DOWN trades should appear** — if they don't, the fix didn't propagate through the call chain.
3. **Win rate per regime** — trend strategies in trends should win more than mean reversion in chop. If not, the regime detection thresholds need tuning.
4. **Exit reasons** — if >80% of trades close at trailing stop and <5% at take profit, the trail is still too tight or TPs are too ambitious.
5. **Hold duration** — swing trades should average 12–96 hours. If average is <4 hours, something is closing trades early.

---

## BT-2: Extended Backtest (If BT-1 Is Promising)

If BT-1 shows profit factor > 1.0 and positive return, run a 180-day backtest for statistical confidence:

```yaml
backtesting:
  period_days: 180
  initial_balance: 500     # match real starting capital
```

12 trades in 90 days is not enough data to draw conclusions. 25–50 trades over 180 days gives a clearer picture.

---

## Tuning Guide (If Results Are Still Suboptimal)

**If profit factor is 0.9–1.1 (close but not profitable):**
- Check regime distribution — if >40% of candles are `UNKNOWN`, the detection thresholds are too strict. Lower ADX trending threshold from 25 to 20.
- Check if CONSOLIDATION and VOLATILE are firing — if they're 0%, the ATR thresholds need calibrating for H4 data.

**If win rate drops below 35%:**
- Regime detection may be misclassifying. Add logging to show what ADX/EMA/ATR values produce each classification. Compare against the chart — is the bot calling a trend when it's actually ranging?

**If trade count is still <10 over 90 days:**
- Lower `min_strategies_agreeing` from 2 to 1 temporarily to see if signals exist but aren't reaching consensus.
- Lower `consensus_threshold` from 0.60 to 0.50.
- Check `min_confluence_score` — 0.40 might still be too high for H4 where indicators move slower.

**If average hold is <4 hours:**
- Something is still closing trades early. Check for any remaining auto-close logic, signal reversal exits, or time-based exits with low thresholds.

**If SELL trades consistently lose more than BUY trades:**
- V-1 fix may be incomplete. Re-check stop loss placement for SELL direction at every stage.

---

## Rules

1. **Fix I-2 first — it directly impacts regime gating and trade count.**
2. **Check BOTH data_layer.py AND backtest_engine.py** for the TRENDING_DOWN gap. They may have independent detection logic.
3. **The diagnostic logging is not optional.** You need per-trade regime data to tune further. Without it you're guessing.
4. **Don't change regime gate mappings or strategy parameters yet.** Measure first with I-2 fixed, tune later based on per-regime win rates.
5. **Update `PROFITABILITY_TRACKER.md` after every change and after the backtest.**
6. **If trade count doubles but win rate stays the same**, that's progress — it means TRENDING_DOWN trades are now firing and performing similarly to TRENDING_UP trades.
7. **Compare the regime distribution** between backtest and your expectations. In a 90-day forex period, you'd expect roughly 40% trending (up + down combined), 30% ranging/consolidation, 20% volatile, 10% breakout. If one regime dominates (>60%), the thresholds are miscalibrated.

**Begin now. Read `PROFITABILITY_TRACKER.md`, fix I-2, fix I-1, add diagnostic logging, then run BT-1.**
