# Session 6 Plan — M15 Timeframe Integration
**Date:** 2026-03-14
**Started from:** Session 5 baseline — 298 trades, 36.2% WR, PF 0.98, -2.79%, DD 24.62% (730-day)

---

## What Changed Since Session 5 Report

All Session 5 fixes are confirmed in code. No new changes have been made since the last report.

### Confirmed Active in Code

| Fix ID | Description | File | Status |
|--------|-------------|------|--------|
| P1 | UTC hour block per pair (EUR: 8,12,20 / GBP: 11,12,15 / JPY: 9,16) | `strategy_manager.py:190` | ✅ In code |
| P2 | Weekend block (Sat/Sun → return None) | `strategy_manager.py:183` | ✅ In code |
| P4/F-1 | Per-pair EMA20 trend filter (all 3 pairs now EMA20) | `technical_analysis_layer.py:239` | ✅ In code |
| P5 | USD/JPY ATR contraction filter (< 60% of 20-period avg → skip) | `technical_analysis_layer.py:309` | ✅ In code |
| F-2 | ADX > 25 hard gate (Wilder smoothing, inline computation) | `technical_analysis_layer.py:268` | ✅ In code |
| P3 | Tue/Thu block | — | ❌ Reverted (user trades every day) |
| P6 | 2-candle H4 confirmation | — | ❌ Reverted (caused late entries) |

### Current Timeframe Setup (before this session)

```yaml
multi_timeframe:
  timeframes: [H1, H4]
  weights:
    H1: 0.35
    H4: 0.65
```

Backtest engine loops every 1 hour (H1 candle close). Primary TF = H4. No M15.

---

## Session 6 Goal — Add M15 as Entry Trigger Layer

User request: add M15 candles back as a third confirmation layer.

### Architecture Plan

| Layer | Timeframe | Weight | Role |
|-------|-----------|--------|------|
| Trend direction | H4 | 50% | Primary — trend + EMA + ADX gate |
| Entry timing | H1 | 30% | Intermediate — narrows entry window |
| Entry trigger | M15 | 20% | Precise — final entry signal trigger |

M15 does NOT replace H4 as the trend anchor. H4 still drives the EMA filter and ADX gate. M15 only adds a finer entry signal on top of H4+H1 agreement.

### Expected Effect

| Metric | Current (H4+H1) | Expected (H4+H1+M15) |
|--------|-----------------|----------------------|
| Signals per day | 0–2 | 2–5 |
| Trade count (730d) | 298 | ~350–450 |
| Win rate | 36.2% | Similar or slightly lower |
| Entry precision | H1 close | M15 close (4× finer) |

More trades + finer entries = more data to converge toward breakeven (36.6%).

---

## Files to Change

| # | File | Change |
|---|------|--------|
| 1 | `trading_config.yaml` | Add M15 to `timeframes`, set weights H4:50/H1:30/M15:20, update `minimum_timeframes` |
| 2 | `backtest_engine.py` | Fetch M15 candles alongside H1+H4, step every 15 min (or keep 1h step and use M15 for signal only) |
| 3 | `technical_analysis_layer.py` | Pass M15 candles into analysis; EMA/ADX gate stays on H4 (primary); M15 used for signal confidence boost |
| 4 | `strategy_manager.py` | Pass M15 candles as a secondary input or keep M15 weight in confidence scoring |

### Key Decision: Backtest Step Size

Two options:
- **Option A — 15-min step**: Loop every 15 minutes → 4× more iterations → slower backtest but more precise entry timing
- **Option B — 1-hour step + M15 as signal layer**: Keep 1-hour loop, fetch M15 candles for the window, use them in technical analysis but don't change the loop cadence

**Recommended: Option B** — keeps backtest fast, M15 used purely for signal quality (confirms H1 signal is aligned with shorter-term momentum). No need to loop at M15 frequency for a swing bot.

---

## Outstanding Issues from Session 5 (still open)

| Issue | Priority | Notes |
|-------|----------|-------|
| `consecutive_loss_limit: 3` not verified in backtest engine | Medium | Config says 3, but no enforcement found in code scan |
| 24.62% DD reduction | Medium | Reduce risk 1%→0.5% in borderline ADX (25–30) conditions |
| 2024 monthly sub-period analysis | Low | Identify which months drove most of the DD |

---

## Session 6 Sequence

1. ✅ Write this plan (done)
2. Update `trading_config.yaml` — add M15 timeframe + weights
3. Update `backtest_engine.py` — fetch M15 data, pass into analysis
4. Update `technical_analysis_layer.py` — use M15 in confidence scoring, keep H4 as primary for all gates
5. Run 730-day backtest — compare to Session 5 baseline (298 trades, 36.2% WR, -2.79%)
6. Record results in session report
