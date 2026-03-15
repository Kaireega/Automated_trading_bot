# Session 6 Report — M15 Integration + Risk Management
**Date:** 2026-03-15
**Started from:** Session 5 baseline — 298 trades, 36.2% WR, PF 0.98, -2.79%, DD 24.62% (730-day)

---

## What Changed Since Session 5 Report

The following items were NOT in the Session 5 report and have been implemented since then:

### New Filters & Features Added

| ID | Description | File | Location |
|----|-------------|------|----------|
| M-1 | M15 added to config timeframes, weights H4:50/H1:30/M15:20 | `trading_config.yaml` | `multi_timeframe.timeframes` |
| M-2 | M15 candles fetched in backtest engine (400-candle window) | `backtest_engine.py` | line 572, 905 |
| M-3 | `_calculate_m15_confidence_boost()` — additive 0.0–0.20, never overrides H4 | `technical_analysis_layer.py` | line 416 |
| M-4 | All gates (EMA, ADX, ATR) confirmed to use H4 primary candles | `technical_analysis_layer.py` | lines 235–325 |
| R-1 | Consecutive loss limit: 3 losses → 24h cooldown per pair | `backtest_engine.py` | lines 1253–1267 |
| R-2 | ADX risk scaling: 1% → 0.5% when ADX 25–30 (borderline trend) | `backtest_engine.py` | lines 1001–1011 |
| H4 EMA100 | Additional EMA100 trend gate on H4 (block BUY below EMA100, SELL above) | `technical_analysis_layer.py` | lines 229–261 |
| Pair isolation | `_update_open_positions()` only evaluates each pair with its own candles | `backtest_engine.py` | line 1068 |
| Trailing stop | Pip-based activation (80 pips) + trailing distance (50 pips) — swing-appropriate | `backtest_engine.py` | lines 1094–1124 |
| Signal case fix | SL/TP checks now use lowercase `'buy'`/`'sell'` consistently | `backtest_engine.py` | lines 1144–1170 |

### Architecture Change: Timeframe Stack

**Before Session 6:**
```
H4 (65%) + H1 (35%)
Backtest loop: every 1 hour
```

**After Session 6:**
```
H4 (50%) + H1 (30%) + M15 (20%)
Backtest loop: every 1 hour (unchanged — M15 used for signal quality, not loop frequency)
M15 window: 400 candles (~100 hours lookback)
```

### M15 Confidence Boost Logic (M-3)

M15 is additive-only. It never rejects a signal — only boosts confidence when aligned:

| Condition | Boost |
|-----------|-------|
| M15 EMA8 > EMA21 (for BUY) or EMA8 < EMA21 (for SELL) | +0.08 |
| M15 RSI < 65 (for BUY) or RSI > 35 (for SELL) — room to run | +0.06 |
| Last 3 M15 candles moving in signal direction | +0.06 |
| **Max total boost** | **0.20** |

If M15 EMA contradicts the H4 signal direction → returns 0.0 immediately (no boost, no penalty).

### Risk Management: R-1 Consecutive Loss Limit

- After 3 consecutive losses on any pair, that pair is paused for 24 hours
- On any win, the consecutive loss counter resets to 0
- Cooldown expires automatically — pair resumes after 24h
- Tracked per-pair in `self.consecutive_losses` dict

### Risk Management: R-2 ADX Scaling

- ADX stored in recommendation metadata during analysis (`recommendation.metadata['adx_value']`)
- At trade execution: if `25 ≤ ADX < 30` → risk_pct = 0.5% (half position)
- If `ADX ≥ 30` → full 1% risk

### What Did NOT Change (confirmed still active)

| Filter | Status | Notes |
|--------|--------|-------|
| UTC hour block (P1) | ✅ Active | EUR: 8,12,20 / GBP: 11,12,15 / JPY: 9,16 |
| Weekend block (P2) | ✅ Active | Sat/Sun → return None |
| Per-pair EMA20 filter (F-1) | ✅ Active | All 3 pairs use EMA20 |
| ADX > 25 hard gate (F-2) | ✅ Active | Wilder smoothing, inline computation |
| USD/JPY ATR contraction (P5) | ✅ Active | Skips when ATR < 60% of 20-candle avg |
| Same-direction consensus (I-5) | ✅ Active | 3+ strategies same direction required |
| 2×ATR stops, 4×ATR TP (I-3) | ✅ Active | All strategies |
| B-7 same-candle SL guard | ✅ Active | No exit on entry candle |

---

## Backtest Results Pending

The session 6 changes are all implemented. A 730-day backtest comparing to Session 5 baseline needs to be run:

| Run | Changes | Trades | WR | PF | Return | DD | Notes |
|-----|---------|--------|----|----|--------|-----|-------|
| Session 5 baseline | H4+H1 only, no R-1/R-2 | 298 | 36.2% | 0.98 | -2.79% | 24.62% | Reference |
| BT-1 (Session 6) | +M15 +R-1 +R-2 +EMA100 +pair isolation | — | — | — | — | — | **Pending** |

---

## Why M15 Was Added

**User request:** "why are you not using the 15 min candles"

The original swing conversion (Session 2) removed M15 because the bot was rebuilt from intraday (M5/M15) to swing (H4/D1). The assumption was: M15 is too granular for a swing trading system.

The Session 6 rationale for adding M15 back:
- H4+H1 agree on direction, but entry timing within a 4-hour candle is still imprecise
- M15 provides 4× finer entry resolution without changing the swing timeframe anchor
- M15 only adds to confidence when aligned — it cannot trigger a trade that H4+H1 blocked
- Expected effect: better entry price within the H4 trend move → slightly fewer SL hits → WR improvement

---

## Outstanding Issues (Not Yet Addressed)

| Issue | Priority | Status |
|-------|----------|--------|
| 2024 monthly sub-period DD breakdown | Low | Not done |
| Backtest BT-1 result | High | **Pending — run next** |

---

## Session Progression Summary

| Session | Key Additions | Best 730d Result |
|---------|--------------|-----------------|
| 1 | Initial setup, V-1/V-2 (inverted SL, sizing) | — |
| 2 | Swing conversion H4/D1, S-1 to S-12 configs | Baseline |
| 3 | B-4 (signal case), B-5 (primary TF) | -11.31% |
| 4 | I-3/I-5/I-6, EMA 21/55, Ichimoku chikou | +1.01% (180d) |
| 5 | CSV analysis, P1/P2/P4/P5 filters, ADX gate, EMA20 | -2.79% (730d) |
| **6** | **M15 entry trigger, R-1 loss limit, R-2 ADX scaling** | **Pending BT-1** |
