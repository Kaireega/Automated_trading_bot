# Session 4 Improvement Tracker
> Fresh codebase review + signal quality improvements
> Started: 2026-03-13
> Last updated: 2026-03-13

---

## Context

Session 3 fixed two critical structural bugs (B-4, B-5) that made all prior backtest results
meaningless. After those fixes, baseline is:
- 91 trades, 31.9% WR, PF 0.79, -11.31%, 14.45% DD

Session 4 goal: improve win rate from 32% toward 38%+ (breakeven) through signal quality fixes.

---

## Fresh Codebase Review Findings

### Confirmed Working (after session 3)
| Item | Status |
|------|--------|
| B-4: Signal case `'buy'`/`'sell'` — SL/TP fires | ✅ |
| B-5: Primary TF selects H4 → H1 → M5 | ✅ |
| P-6: min_strategies_agreeing=3, min_confluence_score=0.50 | ✅ |
| Candle window: 200 H4 candles (expanded from 100) | ✅ |

### New Issues Found in Review
| # | Severity | Description |
|---|----------|-------------|
| I-4 | ~~Critical~~ Investigated | USD_JPY P&L appeared to be ~150× inflated — investigated and found bugs CANCEL OUT (units 155× too small, no JPY→USD conversion = same result). Fixed anyway for correctness. |
| I-5 | Medium | `min_strategies_agreeing` counted TOTAL signals (BUY+SELL mixed). Fixed to require N same-direction. |
| I-6 | Medium | `NEWS_REACTIONARY` not in `REGIME_ALLOWED_TYPES` → falls back to UNKNOWN (all strategies fire) |
| I-9 | Medium | `ATR_Breakout` SL = 0.5×ATR below breakout high — too tight for H4 |
| Ichimoku chikou | Bug | chikou was always NaN→0 → SELL signals got +0.05 confidence bias. Fixed. |

---

## Changes Made This Session

### Fix 1: USD/JPY P&L Correction (I-4) — `backtest_engine.py`
Both sizing AND P&L were wrong but self-canceling. Fixed both for correctness:
- **Sizing**: `units = risk_amount * entry_price / pip_distance` (JPY pairs)
- **P&L**: `pnl = pnl / exit_price` (JPY pairs)
- **Net impact**: No change to results (bugs canceled out as expected)

### Fix 2: Candle Window 100 → 200 — `backtest_engine.py`
Line ~884: `candles_up_to_date[-200:]` instead of `[-100:]`
- Strategies now see 33 days of H4 history vs 17 days
- Better indicator accuracy (Ichimoku needs senkou+kijun+5 = 83 candles min)
- Enables proper EMA50 warmup in trend filter

### Fix 3: EMA Trend Filter EMA100 → EMA50 — `technical_analysis_layer.py`
- Changed `EMA100_PERIOD=100, warmup=100` → `EMA_PERIOD=50, EMA_WARMUP=150`
- With 200-candle window + 150 warmup: EMA50 has <0.4% residual bias on starting price
- Was EMA100 on 100-candle window: 14% residual bias (poorly converged)

### Fix 4: Ichimoku Chikou Bug — `fast_ichimoku.py`
- **Before**: `chikou = df['chikou_span'].iloc[-1]` → always NaN→0
  - chikou=0 < any price → all SELL signals got +0.05 confidence boost (systematic bias)
  - chikou=0 > no price → BUY signals never got the boost
- **After**: `chikou = current_close`, `chikou_past_price = close_kijun_periods_ago`
  - `chikou_bullish = chikou > chikou_past_price` (price rising over kijun period)
  - `chikou_bearish = chikou < chikou_past_price` (price falling over kijun period)
  - Symmetric confidence boost — no directional bias

### Fix 5: EMA Periods 12/26 → 21/55 — `trading_config.yaml`
- **Before**: 12×4h=2-day fast, 26×4h=4.3-day slow → H4 crossovers extremely frequent
- **After**: 21×4h=3.5-day fast, 55×4h=9.2-day slow → fewer but more meaningful crossovers
- Config change only — strategy code reads `ema_fast`/`ema_slow` parameters

### Fix 6: I-5 — Same-Direction Strategy Count — `strategy_manager.py`
- **Before**: `len(strategy_signals) < min_strategies_agreeing` counted ALL signals
  - 2 BUY + 1 SELL = 3 total → would pass the "3 agreeing" gate
- **After**: `max(buy_count, sell_count) < min_strategies_agreeing`
  - 2 BUY + 1 SELL → buy_count=2 < 3 → blocked
  - Requires N strategies agreeing on the SAME direction

---

## Backtest Progression

| Run | Trades | Win Rate | PF | Return | DD | What changed |
|-----|--------|----------|----|--------|----|--------------|
| Session 3 baseline (B-4+B-5) | 91 | 31.9% | 0.79 | -11.31% | 14.45% | Fixed SL/TP + H4 primary TF |
| EMA100 filter added | 91 | 30.8% | 0.75 | -13.86% | 14.45% | Only filtered already-rejected signals |
| I-4 fix only | 91 | 30.8% | 0.75 | -13.76% | 14.41% | Self-canceling bugs confirmed |
| 200-candle + EMA50 + Ichimoku fix | 90 | 32.2% | 0.81 | -10.44% | 14.40% | Better filter convergence |
| EMA 21/55 + I-5 direction fix | **87** | **33.3%** | **0.83** | **-8.69%** | 14.39% | Fewer, better signals |

**Target**: WR >50%, PF >1.3, DD <10%, Return positive

---

## Root Cause Analysis: Why Win Rate is 32-33%

### Market conditions during test period (Dec 2025 – Mar 2026)
- EUR/USD: -224 pips overall but major reversal within period
  - Q1: -24 pips | Q2: +300 pips (big rally) | Q3: -340 pips (reversal) | Q4: -200 pips (down)
- GBP/USD: -49 pips overall, similar chop pattern
- USD/JPY: +346 pips overall but with big Q2 drop then recovery

**This is a choppy, reversing market — the hardest environment for trend-following strategies.**

### Structural limitations of current strategies
1. EMA crossover: state-based (fires every candle EMAs are aligned), not just on actual crossover
   - Enters during trend continuation phases but also at late/exhausted phases
2. All strategies look at H4 only — no higher-TF (D1) trend filter
3. UNKNOWN regime allows all strategy types → potential mixed signals
4. In RANGING regime: only 2 mean_reversion strategies eligible but need 3 → NO trades in ranging

---

## Remaining Known Issues

| # | Priority | Description | File |
|---|----------|-------------|------|
| I-3 | Medium | Strategies hardcode 1.5x ATR for SL instead of config's 2.0x | strategy files |
| I-6 | Medium | `NEWS_REACTIONARY` not in REGIME_ALLOWED_TYPES → all strategies fire | strategy_manager.py |
| I-9 | Medium | ATR_Breakout SL = 0.5×ATR below breakout level — too tight on H4 | breakout/atr_breakout.py |
| I-2 | Low | data_layer `_determine_market_condition` never returns TRENDING_DOWN | data_layer.py |

---

## Next Investigation Areas

1. **Fix I-9**: ATR_Breakout stop too tight (0.5×ATR → 1.5×ATR stop distance)
2. **Fix I-6**: Add NEWS_REACTIONARY to REGIME_ALLOWED_TYPES (or restrict to breakout only)
3. **Fix I-3**: Strategy SL multipliers to 2.0×ATR per config (wider stops = fewer false SL hits)
4. **Investigate**: Are strategies generating more BUY or SELL signals? If 70% BUY but market went down, that explains 30% WR.
5. **Consider**: Adding min_atr_age filter — only enter if ATR trend (momentum expanding) is confirmed

---

## Breakeven Analysis

With current avg win $7.34 and avg loss $4.42:
- Breakeven WR = loss / (win + loss) = 4.42 / (7.34 + 4.42) = **37.6%**
- Current WR: 33.3% → gap of **4.3%** below breakeven
- Need ~4 more wins out of every 100 trades, OR R:R improvement to 2.0:1+
