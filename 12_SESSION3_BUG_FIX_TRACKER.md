# Session 3 Bug Fix Tracker
> Critical backtest bug discovery and fixes.
> Started: 2026-03-12 19:00
> Last updated: 2026-03-12 19:30

---

## Summary

All prior backtest results (P-1 through P-6) were meaningless because of two structural bugs:
1. **B-4** — stop losses and take profits NEVER fired (signal case mismatch)
2. **B-5** — wrong timeframe used for ATR/indicator calculation (H1 instead of H4)

With these bugs, every trade either:
- Ran to MAX_HOLD_TIME and exited at market (B-4 bug)
- Got stopped out immediately on the first H4 candle with a 15-pip stop (after B-4 was fixed, before B-5 was fixed)

---

## Bugs Fixed This Session

| # | Severity | Description | File | Status |
|---|----------|-------------|------|--------|
| P-6 | High | Raise consensus bar: min_strategies_agreeing=3, min_signals_required=3, min_confluence_score=0.50 | `trading_config.yaml` | ✅ Done |
| B-4 | **CRITICAL** | Signal case mismatch: stored `"buy"`/`"sell"` but checked `'BUY'`/`'SELL'` → SL/TP never fired | `backtest_engine.py` | ✅ Fixed |
| B-5 | **CRITICAL** | Primary timeframe defaulted to H1 instead of H4 → ATR 10 pips instead of 33 pips → 15-pip stops on H4 candles | `technical_analysis_layer.py` | ✅ Fixed |

---

## Bug Details

### B-4: Signal Case Mismatch — `src/trading_bot/src/backtesting/backtest_engine.py`

**Root cause:** `position['signal']` stored as `"buy"`/`"sell"` (TradeSignal enum `.value`), but all stop/TP/trailing/PnL checks compared against `'BUY'`/`'SELL'`. In Python, `'sell' == 'SELL'` is `False`.

**Evidence:** All 27 trades in every backtest before this fix exited via `MAX_HOLD_TIME`. Stops set at 14-34 pips should have been hit within 1-2 H4 candles (which span 30-100 pips each).

**Fix:** Changed 7 comparisons in `_update_open_positions` and `_process_closed_position` from `'BUY'`/`'SELL'` to `'buy'`/`'sell'`.

**Impact:** Stop losses and take profits now function for the first time. Max loss per trade capped at ~$5 (1% of balance). Verified via Largest Loss = $5.00 in backtest.

### B-5: Wrong Primary Timeframe for Indicators — `src/trading_bot/src/ai/technical_analysis_layer.py`

**Root cause:** Primary timeframe fallback logic was:
```python
primary_timeframe = TimeFrame.M5  # Not available in swing
primary_indicators = technical_indicators.get(primary_timeframe)
if not primary_indicators:
    # Fallback to FIRST key — which is H1 (inserted before H4 in the dict)
    primary_timeframe = list(technical_indicators.keys())[0]  # → H1!
```

Since historical data is loaded `[TimeFrame.H1, TimeFrame.H4]` in that order, H1 was always first.

**Impact:**
- H1 ATR ≈ 0.001058 (10.6 pips)
- H4 ATR ≈ 0.003286 (32.9 pips)
- Strategies set stop at `1.5 × ATR`: 1.5 × 10.6 pips = **16-pip stop**
- H4 candles average **27-pip range** → stop hit on virtually every candle
- Result: 273 trades in 90 days, 24% win rate, -54% return

**Fix:**
```python
# Changed to prefer H4 → H1 → M5 (swing priority order)
for preferred_tf in [TimeFrame.H4, TimeFrame.H1, TimeFrame.M5]:
    if preferred_tf in technical_indicators:
        primary_timeframe = preferred_tf
        break
```

**Expected impact:** H4 ATR (33 pips) × 1.5 = **50-pip stops**. H4 candle average 27-pip range → stops should survive most normal candles.

---

## Backtest History (Session 3)

| Run | Config | Trades | Win Rate | PF | Return | Drawdown | Key Finding |
|-----|--------|--------|----------|----|--------|----------|-------------|
| B-3 clean | After V-1/V-2/B-1/B-2/B-3 | 12 | 41.7% | 0.87 | -4.01% | 13.91% | All MAX_HOLD_TIME — B-4 bug |
| P-6 raise | After strategy name fix + P-6 | 27 | 48.1% | 1.09 | +5.19% | 25.06% | Still all MAX_HOLD_TIME — B-4 bug |
| After B-4 fix | SL/TP now fires | 273 | 24.2% | 0.60 | -54.15% | 55.51% | 16-pip stops, H1 ATR — B-5 bug |
| After B-5 fix | H4 primary TF | ⬜ pending | ⬜ | ⬜ | ⬜ | ⬜ | Running... |

---

## What the B-5 Fix Changes

With H4 as primary:
- ATR used for stops: ~0.0033 (33 pips)
- Strategy stop distance: 1.5 × 33 = **50 pips**
- Strategy TP distance: 2.5 × 33 = **82 pips** (EMA), others vary
- Expected R:R: ~82/50 = **1.64** (reasonable for swing)
- Expected trade count: Much lower — stops survive multiple H4 candles
- Expected win rate: Higher — signals held long enough to reach TP

---

## Remaining Known Issues

| # | Severity | Description |
|---|----------|-------------|
| I-1 | Low | `technical_analysis_layer.py` primary_timeframe defaulted to M5 in log comment (cosmetic, fixed by B-5 fix) |
| I-2 | Low | `data_layer.py:419` — `_determine_market_condition` only returns `TRENDING_UP` (never `TRENDING_DOWN`) |
| I-3 | Medium | Strategies hardcode `1.5x ATR` for stops instead of reading `config.risk_management.stop_loss_atr_multiplier` (2.0) — may still be too tight |
| I-4 | Low | USD_JPY P&L not converted from JPY to USD — results inflated by ~155x for JPY trades |

---

## Next Steps (if targets not met after B-5 fix)

1. If win rate still <45%: Check if strategy multipliers need raising (1.5x → 2.0x ATR)
2. If trade count still >50/90d: Consensus thresholds already tightened (P-6) — check signal quality
3. If drawdown still >15%: Consider max_daily_loss enforcement in backtest
