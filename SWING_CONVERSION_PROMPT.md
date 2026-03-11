# PROMPT: Fix V-Issues + Convert to Swing Trading Bot (Small Account)

## Who You Are

You are a **Senior Software Engineer** specializing in algorithmic FX trading systems. You understand the mechanical differences between intraday and swing trading at the code level — timeframes, hold durations, indicator parameters, position sizing, loop intervals, and how transaction costs affect small accounts differently at each frequency.

---

## Context

This Forex trading bot has been through a full audit (40 issues), 25 fixes applied, and runtime verification. All 25 fixes are confirmed working. However:

1. **Two pre-existing bugs** were found during verification (V-1: inverted SELL stops, V-2: broken position sizing)
2. **The bot needs to be converted from intraday to swing trading** — the owner is starting with a small account and doesn't want spread/slippage eating into profits

**Read these files first — they are your source of truth:**
1. `DEBUG_JOURNAL.md` — original audit (architecture, config, data flow)
2. `FIX_TRACKER.md` — 25 fixes applied
3. `VERIFICATION_LOG.md` — runtime results, V-1 and V-2 evidence

---

## Step 0: Create Your Tracker

Create `SWING_CONVERSION_TRACKER.md` in the project root:

```markdown
# Swing Conversion & V-Issue Tracker
> Converting from intraday to swing trading + fixing V-issues.
> Started: [date/time]
> Last updated: [date/time]

## Phase 1: V-Issue Fixes
| # | Description | Status | Verified? |
|---|-------------|--------|-----------|
| V-1 | SELL stop losses inverted (below entry instead of above) | ⬜ | ⬜ |
| V-2 | Position sizing capped to nano-lots (~136 units) | ⬜ | ⬜ |

## Phase 2: Swing Trading Conversion
| # | Area | Change | Status |
|---|------|--------|--------|
| S-1 | Config: Timeframes | M5/M15 → H1/H4/D1 | ⬜ |
| S-2 | Config: Trading parameters | Swing-appropriate values | ⬜ |
| S-3 | Config: Hold times | Hours → days/weeks | ⬜ |
| S-4 | Config: Risk & position sizing | Small account safe values | ⬜ |
| S-5 | Main loop | 5min polling → 1hr/4hr polling | ⬜ |
| S-6 | Strategies: Disable intraday-only | Scalping + session strategies off | ⬜ |
| S-7 | Strategies: Tune swing strategies | Indicator params for H4/D1 | ⬜ |
| S-8 | Strategy manager | Adjust consensus for fewer signals | ⬜ |
| S-9 | Risk manager | Wider stops, smaller positions | ⬜ |
| S-10 | Position manager | Multi-day hold support | ⬜ |
| S-11 | Notifications | Reduce frequency for swing pace | ⬜ |
| S-12 | Backtest | Update for swing parameters | ⬜ |

## Investigation Log
[Updated as you work]

## Verification
| # | Test | Expected | Actual | Pass? |
|---|------|----------|--------|-------|
```

---

# PHASE 1: FIX V-ISSUES

Fix these first. The swing conversion depends on correct stop losses and position sizing.

---

## V-1: SELL Stop Losses Are Inverted

### The Evidence
Backtest CSV shows SELL trades with stop loss **far below** entry (e.g., entry 1.33695, stop 1.1631 = 17,000+ pips below). For a SELL, the stop must be **above** entry. Because stops never trigger, average loss = $0.04 and profit factor = 42.52 (fake).

### How To Investigate

**Trace the stop loss through the entire chain.** At each stage, check whether BUY vs SELL is handled differently:

```
Strategy.generate_signal()           → initial stop_loss
TechnicalAnalysisLayer               → may modify
AdvancedRiskManager.assess_trade_risk() → modified_stop_loss
PositionManager.execute_trade()       → sent to broker
SimulationBroker (backtest)           → evaluated against candle data
```

**Common bug patterns to look for:**

```python
# PATTERN 1: Always subtracts (only correct for BUY)
stop_loss = entry_price - (atr * multiplier)
# SELL fix: entry_price + (atr * multiplier)

# PATTERN 2: Wrong min/max
stop_loss = min(original_stop, adjusted_stop)
# For SELL: should be max() because stop is above entry

# PATTERN 3: No direction check at all
# Same formula applied to BUY and SELL
```

**Also check the backtest broker's stop evaluation logic:**

```python
# CORRECT:
if direction == "BUY" and candle.low <= stop_loss:    # price dropped to stop
    close_trade(loss)
if direction == "SELL" and candle.high >= stop_loss:   # price rose to stop
    close_trade(loss)

# BUG: same check for both
if candle.low <= stop_loss:  # only works for BUY
```

### How To Fix

Apply direction-aware logic everywhere stops are calculated or evaluated:

```python
if direction == "BUY":
    stop_loss = entry_price - stop_distance
    take_profit = entry_price + tp_distance
elif direction == "SELL":
    stop_loss = entry_price + stop_distance
    take_profit = entry_price - tp_distance
```

### Verification

Run the backtest, export results, and check:
```python
# Every SELL must have stop > entry, every BUY must have stop < entry
for trade in results:
    if trade.direction == "SELL" and trade.stop_loss < trade.entry_price:
        print(f"❌ SELL stop still inverted: entry={trade.entry_price}, stop={trade.stop_loss}")
    if trade.direction == "BUY" and trade.stop_loss > trade.entry_price:
        print(f"❌ BUY stop inverted: entry={trade.entry_price}, stop={trade.stop_loss}")
```

After fixing: profit factor should drop to a realistic range (0.8–3.0), average loss should be meaningful ($50–$200), and some trades should hit their stops.

---

## V-2: Position Sizing Capped to Nano-Lots

### The Evidence
`max_position_size: 1.5` → interpreted as 1.5% of $10,000 = $150 notional → $150 / 1.10 = ~136 units. Risk-based calc gives ~150,000 units but `min()` always picks 136. P&L is $0.04–$20 per trade.

### How To Investigate

```bash
grep -rn "max_position_size" src/trading_bot/
```

Find where it's defined, where it's read, and what the `min()` comparison looks like. Determine what the developer intended:
- 1.5 standard lots (150,000 units)?
- 1.5x leverage?
- 1.5% of balance as a notional cap?

### How To Fix

Most likely the `min()` is comparing units to dollars. Both sides need to be in the same unit (units):

```python
# If max_position_size means lots:
max_units = max_position_size * 100000

# If max_position_size means leverage multiple:
max_units = (account_balance * max_position_size) / entry_price

# Then:
final_size = min(risk_based_units, max_units)  # both in units
```

For a **small account** (which this will be), position sizing should be purely risk-based:
```python
risk_amount = account_balance * (risk_percentage / 100)   # e.g., $500 * 0.01 = $5
stop_distance = abs(entry - stop_loss)                     # in price
pip_value = get_pip_value(pair, units=1)                   # value of 1 pip for 1 unit
units = risk_amount / (stop_distance / pip_size * pip_value)
```

### Verification

After fix, check that position sizes scale with account and stop distance, and P&L per trade is meaningful relative to account size.

---

# PHASE 2: SWING TRADING CONVERSION

Once V-1 and V-2 are fixed and verified, proceed with the swing conversion. This touches config, strategies, the main loop, risk management, and position management.

---

## Why Swing Trading for a Small Account

Intraday (M5/M15) problems on a small account:
- **Spread kills you.** A 1.5 pip spread on a 15 pip M5 target = 10% cost per trade. On a 150 pip H4 swing target = 1% cost.
- **Slippage on entries/exits.** More trades = more slippage events. Swing means 2–5 trades per week, not 5–15 per day.
- **Overtrading.** More signals = more chances to lose. Small accounts can't absorb drawdown streaks.
- **Emotional load.** Monitoring M5 candles is a full-time job. H4/D1 candles let the bot check in every few hours.

Swing trading targets:
- **Timeframes:** H1 (confirmation), H4 (primary), D1 (trend context)
- **Hold time:** 1–10 days typical
- **Trades per week:** 2–5
- **Stop distance:** 50–200 pips (vs 10–30 pips intraday)
- **Take profit:** 100–500 pips (vs 15–50 pips intraday)
- **Risk per trade:** 1% of account (critical for small accounts — capital preservation is everything)

---

## S-1: Config — Timeframes

**File:** `src/trading_bot/src/config/trading_config.yaml`

Find the timeframes section and change from intraday to swing:

```yaml
# BEFORE (intraday):
timeframes:
  - M5
  - M15
  - H1

# AFTER (swing):
timeframes:
  - H1      # confirmation / entry timing
  - H4      # primary analysis timeframe
  - D1      # trend direction / context
```

Also update any `primary_timeframe` or `default_timeframe` settings to `H4`.

Check `config.py` dataclass defaults too — make sure the YAML values override them.

---

## S-2: Config — Trading Parameters

```yaml
trading:
  # Risk per trade — 1% for small account capital preservation
  risk_percentage: 1.0

  # Fewer pairs = more focus, less margin usage
  # Pick the most liquid, lowest spread pairs
  pairs:
    - EUR_USD
    - GBP_USD
    - USD_JPY
  # Remove exotic/volatile pairs that have wide spreads

  # Minimum pips profit to justify the spread cost
  # On H4/D1, targets are big enough that spread is negligible
  min_take_profit_pips: 80
  min_stop_loss_pips: 30
```

---

## S-3: Config — Hold Times

Find the hold time settings and update for multi-day holds:

```yaml
trading:
  hold_time_settings:
    # Swing trades can last days to weeks
    max_hold_hours: 240          # 10 days max (was probably 4-24 hours)
    min_hold_hours: 4            # don't close too early on noise
    force_close_enabled: true    # close stale trades after max_hold
    
    # Weekend handling — close or hold over weekend
    close_before_weekend: false  # swing traders often hold over weekends
    # Set to true if you want to avoid weekend gap risk on small account
```

---

## S-4: Config — Risk & Position Sizing (Small Account)

```yaml
risk_management:
  # Max simultaneous open trades — keep low for small account
  max_open_trades: 2           # was 3 — reduce to limit exposure

  # Max risk across all open positions
  max_total_risk_percentage: 3.0   # never risk more than 3% of account at once

  # Daily loss limit — stop trading if you lose 2% in a day
  max_daily_loss_percentage: 2.0

  # Max risk per single trade
  max_risk_threshold: 0.5      # was 0.7 — tighter for small account

  # Trail stop to protect profits on swing trades
  trailing_stop:
    enabled: true
    activation_pips: 50         # start trailing after 50 pips profit
    trail_distance_pips: 30     # trail 30 pips behind price

position_sizing:
  # Pure risk-based sizing — let stop distance determine position size
  method: risk_based            # not fixed_lots or percentage_of_balance
  risk_percentage: 1.0          # 1% of account per trade
  
  # For a $500 account trading EUR/USD with 100 pip stop:
  # Risk = $5, pip value ≈ $0.10/pip for 1000 units
  # Units = $5 / (100 * $0.0001) = 5000 units (0.05 lots)
  # This is appropriate for a small account
  
  # Remove or raise the max_position_size cap that was causing V-2
  # max_position_size should not artificially cap below risk-based sizing
  max_position_size: 50000      # units cap — safety net, not the primary limiter
```

---

## S-5: Main Loop — Polling Interval

**File:** `src/trading_bot/main.py`

Find the main trading loop (`_enhanced_trading_loop` or similar) and change the sleep/polling interval:

```python
# BEFORE (intraday — checks every 1-5 minutes):
await asyncio.sleep(300)  # 5 minutes
# or
await asyncio.sleep(60)   # 1 minute

# AFTER (swing — checks every 1-4 hours):
await asyncio.sleep(3600)  # 1 hour — aligns with H1 candle close
# Alternative: 14400 (4 hours) to align with H4 candle close
```

**Why this matters:** Checking M5 candles every minute is necessary for intraday. Checking H4 candles every minute wastes CPU and API calls while producing identical analysis 239 out of 240 times. Match the loop to the smallest timeframe (H1 = check hourly).

Also look for any loop that monitors positions (the one that was crashing every 30 seconds with the scaling_levels KeyError). Change its interval too:

```python
# Position monitoring for swing trades
await asyncio.sleep(1800)  # every 30 minutes is plenty for swing
# was probably 30 seconds for intraday
```

---

## S-6: Strategies — Disable Intraday-Only

Some strategies are fundamentally intraday and don't work on H4/D1:

**DISABLE these (they depend on session timing or micro-structure):**
- `london_open_break.py` — trades the London session open. Meaningless on H4/D1.
- `ny_open_momentum.py` — trades the NY session open. Same issue.
- `price_action_scalp.py` — scalping strategy. Needs M1/M5 data.
- `order_flow_momentum.py` — order flow on micro timeframes.
- `spread_squeeze.py` — exploits tight spreads on micro timeframes.

**KEEP and TUNE these (they work on any timeframe):**
- `ema_crossover.py` — works on H4/D1 with longer periods
- `adx_trend.py` — ADX is timeframe-agnostic
- `macd_momentum.py` — MACD works well on H4/D1
- `fast_ichimoku.py` — Ichimoku is designed for D1/Weekly
- `bollinger_bounce.py` — mean reversion works on H4
- `rsi_extremes.py` — RSI works on any timeframe
- `stochastic_reversal.py` — works on H4
- `atr_breakout.py` — breakout on H4/D1 is classic swing
- `support_resistance.py` — S/R is timeframe-agnostic
- `donchian_break.py` — Donchian channel breakout is a classic swing strategy

**How to disable:** In `trading_config.yaml`, set the strategy allocation to 0 or remove from the strategy list. Do NOT delete the files — they may be useful later.

```yaml
strategy_portfolio:
  # Swing strategies (active)
  EMA_Crossover_H4:
    enabled: true
    weight: 0.12
  ADX_Trend_H4:
    enabled: true
    weight: 0.12
  MACD_Momentum_H4:
    enabled: true
    weight: 0.12
  Fast_Ichimoku_D1:
    enabled: true
    weight: 0.15          # Ichimoku is strong on D1
  BB_Bounce_H4:
    enabled: true
    weight: 0.10
  RSI_Extremes_H4:
    enabled: true
    weight: 0.08
  ATR_Breakout_H4:
    enabled: true
    weight: 0.12
  Support_Resistance_H4:
    enabled: true
    weight: 0.10
  Donchian_Break_H4:
    enabled: true
    weight: 0.09

  # Intraday strategies (disabled for swing)
  London_Open_Break:
    enabled: false
  NY_Open_Momentum:
    enabled: false
  Price_Action_Scalp:
    enabled: false
  Order_Flow_Momentum:
    enabled: false
  Spread_Squeeze:
    enabled: false
```

**IMPORTANT:** Check how `strategy_manager.py` reads this config. Does it check an `enabled` flag? Or does it load everything in the list? You may need to add `enabled` flag support if it doesn't exist. If it just loads by name, remove the disabled strategies from the list entirely.

---

## S-7: Strategies — Tune Indicator Parameters for Swing

Indicator parameters that work on M5 are wrong for H4/D1. Each strategy needs its parameters adjusted.

**EMA Crossover:**
```yaml
# M5 intraday: fast=9, slow=21
# H4 swing:
fast_ema: 12
slow_ema: 26
signal_ema: 9
```

**ADX Trend:**
```yaml
# M5: adx_period=14, threshold=20
# H4 swing:
adx_period: 14      # standard, works on any TF
adx_threshold: 25   # higher threshold = stronger trend requirement on H4
```

**MACD:**
```yaml
# Standard MACD works on H4 with default 12/26/9
fast_period: 12
slow_period: 26
signal_period: 9
```

**RSI:**
```yaml
# H4 swing — wider bands because H4 RSI is less extreme
rsi_period: 14
rsi_oversold: 30
rsi_overbought: 70
```

**Bollinger Bands:**
```yaml
# H4 swing — standard 20/2 works well
bb_period: 20
bb_std: 2.0
```

**ATR Breakout:**
```yaml
# H4 swing — wider multiplier for bigger moves
atr_period: 14
atr_multiplier: 2.0    # was probably 1.0-1.5 for intraday
```

**Ichimoku:**
```yaml
# D1 — use standard settings (Ichimoku was designed for D1)
tenkan: 9
kijun: 26
senkou_b: 52
```

**Donchian Channel:**
```yaml
# H4 swing — 20 period = 80 hours ≈ 3.3 trading days
donchian_period: 20
```

**Where to apply:** Check if these parameters live in the YAML config or are hardcoded in each strategy file. If hardcoded, move them to config. If in config, update the YAML values. The debug journal noted a pattern of hardcoded values overriding config — check each strategy.

---

## S-8: Strategy Manager — Adjust Consensus

**File:** `src/trading_bot/src/strategies/strategy_manager.py`

With swing trading, signals are rarer. The consensus mechanism needs adjustment:

```yaml
multi_timeframe:
  consensus_threshold: 0.60      # was 0.75 — slightly lower for swing since signals are rarer
  minimum_timeframes: 2          # require H4 + D1 agreement (or H1 + H4)
  min_strategies_agreeing: 2     # 2 strategies must agree (reasonable for swing)
```

**Why lower consensus_threshold:** On H4/D1, you get far fewer signals than M5. If the threshold is too high, the bot will never trade. 0.60 means 60% of eligible strategies must agree — still selective, but achievable with swing frequency.

**Why min_strategies_agreeing stays at 2:** Even on swing, you want confirmation from at least 2 independent methods. One trend strategy + one momentum confirmation = solid swing entry.

---

## S-9: Risk Manager — Wider Stops, Tighter Risk

**File:** `src/trading_bot/src/core/advanced_risk_manager.py`

Swing trades have wider stops (50–200 pips vs 10–30 pips intraday). The risk manager needs to accept this:

1. **Check if there's a max stop distance** that rejects trades with "too wide" stops. On H4/D1, 150 pip stops are normal. If the risk manager caps at 50 pips (intraday logic), valid swing trades get rejected.

2. **Check the reward:risk ratio requirements.** Swing trades often target 2:1 or 3:1. If the risk manager requires specific R:R, make sure it's achievable with swing-sized moves.

3. **Check ATR-based validations.** ATR on H4 is much larger than ATR on M5. Any hardcoded ATR thresholds need updating.

```bash
grep -rn "max_stop\|min_stop\|atr.*threshold\|reward.*risk\|risk.*reward" src/trading_bot/src/core/
```

---

## S-10: Position Manager — Multi-Day Holds

**File:** `src/trading_bot/src/core/position_manager.py`

Check for anything that assumes short hold times:

1. **Force close timer:** If there's logic that closes positions after X hours, update it for swing (240+ hours).
2. **Trailing stop:** If the trailing stop starts too tight (e.g., 10 pips), it'll get stopped out on normal H4 noise. Set activation to 50+ pips and trail distance to 30+ pips.
3. **Swap/rollover handling:** Swing positions held overnight incur swap fees. The bot should log swap costs if OANDA reports them. This isn't a code change — just awareness for the P&L tracking.
4. **Weekend gap protection (optional):** Add a flag to close positions before Friday close if the user wants to avoid weekend gaps. On a small account, a 100-pip gap against you can be painful.

```yaml
# Optional: weekend protection for small accounts
weekend_protection:
  enabled: true                # close positions before weekend
  close_time_utc: "20:55"     # Friday 8:55 PM UTC (just before markets close)
  reopen_on_monday: false      # don't automatically re-enter — wait for fresh signal
```

---

## S-11: Notifications — Swing Pace

**File:** `src/trading_bot/src/notifications/notification_layer.py` + config

Intraday bots send constant updates. Swing bots should be quieter:

```yaml
notifications:
  # Trade notifications — keep these
  trade_opened: true
  trade_closed: true
  stop_loss_updated: true

  # Loop reports — reduce frequency
  loop_reports:
    enabled: true
    interval_hours: 4          # was probably every loop iteration (5 min)
    # For swing: report every 4 hours, not every 5 minutes

  # Daily summary — add if not present
  daily_summary:
    enabled: true
    time_utc: "21:00"          # after NY close
    include_open_positions: true
    include_daily_pnl: true

  # Disable noisy intraday notifications
  signal_generated: false       # don't notify on every signal — only on trades
  analysis_complete: false      # not needed for swing
```

---

## S-12: Backtest — Update for Swing Parameters

**File:** `src/trading_bot/src/backtesting/backtest_engine.py` + config

1. **Backtest period:** Swing trading needs longer backtests. 7 days is meaningless — you'd get maybe 3–5 trades. Use at least **3–6 months** for statistically meaningful results.

2. **Backtest timeframe data:** Make sure the data feed fetches H1/H4/D1 candles, not M5/M15.

3. **Spread modeling:** Even though swing reduces spread impact, the backtest should still account for it. Check if `simulation_broker.py` applies spread. If using OANDA's historical data, spreads are usually not included — add a configurable spread:

```yaml
backtesting:
  period_days: 180              # 6 months (was 7 days)
  pairs:
    - EUR_USD
    - GBP_USD
    - USD_JPY
  initial_balance: 500          # match your real starting capital
  spread_pips: 1.5              # average spread for major pairs
  commission_per_lot: 0         # OANDA doesn't charge commission on standard
```

4. **Verify the backtest uses the same swing config** — timeframes, strategy list, hold times, risk settings. If the backtest has its own config section, update it to match.

---

## Execution Order

1. **Fix V-1 (inverted SELL stops)** — verify with backtest
2. **Fix V-2 (position sizing)** — verify with backtest
3. **Run a baseline backtest** with current intraday config but working stops/sizing — record metrics
4. **Apply S-1 through S-12** (swing conversion)
5. **Run a swing backtest** (3–6 months) — record metrics
6. **Compare intraday vs swing** results in the tracker
7. **Tune** — if win rate is too low, loosen consensus. If too few trades, check strategy parameters.

---

## Expected Results After Full Conversion

| Metric | Intraday (broken) | Intraday (fixed) | Swing (target) |
|--------|-------------------|------------------|----------------|
| Trades per week | N/A (crashing) | ~40–80 | 2–5 |
| Win rate | ~4% (fake) | ~40–55% | 45–55% |
| Avg win | N/A | $5–$20 (nano-lots) | $50–$300 |
| Avg loss | $0.04 (broken stops) | $5–$20 | $25–$150 |
| Profit factor | 42.52 (fake) | 1.0–2.0 | 1.3–2.5 |
| Spread cost as % of target | 5–15% | 5–15% | 0.5–2% |
| Max drawdown | Unknown | Unknown | <10% of account |

**The key number for a small account: spread cost as % of target.** Going from M5 (10%+ of profit eaten by spread) to H4/D1 (1–2%) is the single biggest improvement for profitability on a small account.

---

## Rules

1. **Fix V-1 and V-2 before starting the swing conversion.** Correct stops and sizing are prerequisites.
2. **Update `SWING_CONVERSION_TRACKER.md` after every change.**
3. **Don't delete intraday strategy files.** Disable them in config. They might be useful when the account grows.
4. **Every config change must match between YAML, dataclass defaults, and code that reads it.** The debug journal documented a pattern of configs being ignored — don't repeat it.
5. **Test with a realistic starting balance.** If the account starts at $500, backtest with $500. Position sizes should be micro-lots (1,000–10,000 units), not standard lots.
6. **If a strategy has hardcoded M5/M15 parameters inside the .py file, move them to config.** The debug journal found this pattern repeatedly. Swing parameters must be configurable, not buried in code.
7. **After conversion, run a 3–6 month backtest and verify:**
   - Trades are held for hours/days, not minutes
   - Stop distances are 50–200 pips, not 10–30
   - Position sizes produce meaningful P&L relative to account
   - Spread cost is <2% of average trade target
   - The bot polls at hourly intervals, not every minute

**Begin now. Read the three reference files, create `SWING_CONVERSION_TRACKER.md`, then start with V-1.**
