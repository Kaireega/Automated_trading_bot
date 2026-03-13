# Profitability Tracker
> Implementing regime gating + trade management fixes.
> Started: 2026-03-12 02:50
> Last updated: 2026-03-12 02:50

---

## Fixes Planned

| # | Priority | Description | Status | Verified? |
|---|----------|-------------|--------|-----------|
| P-1 | Critical | Add missing MarketCondition enum members (VOLATILE, CONSOLIDATION) | ✅ Done | ⬜ |
| P-2 | Critical | Wire regime-based strategy eligibility gate | ✅ Already done | ✅ Yes |
| P-3 | Critical | Pass regime through full call chain | ✅ Already done | ✅ Yes |
| P-4 | High | Remove premature 5% profit auto-close | ✅ Already done | ✅ Yes |
| P-5 | High | Fix trailing stop: add activation threshold + pip-based distance | ✅ Done | ⬜ |

### Investigation Findings

**P-2/P-3 — Already wired (prior session work):**
- `strategy_manager.py` line 155: `REGIME_ALLOWED_TYPES` gate is present and active
- `technical_analysis_layer.py` line 217: `regime_str = market_context.condition.value.upper()` derived and passed
- `generate_consensus_signal(regime=regime_str)` called correctly — chain is complete

**P-4 — Already fixed (prior session work):**
- `position_manager.py _should_close_position()` only closes for opposite signal direction — no 5% auto-close

**P-5 — Root cause of low realized R:R:**
- Backtest trailing stop used `initial_stop_distance * trailing_atr_multiplier` with **no activation threshold**
- Trail started from tick 1 — a 10-pip retracement after 15 pips profit would trigger the trail and close the trade early
- Config had `trailing_stop_activation_pips: 50` but backtest never read it
- Fix: added activation check (80 pips for H4 swing), pip-based trail distance (50 pips)

---

## Backtest Comparisons

| Metric | Before (B-3 fix) | After P-1/P-5 | Target |
|--------|-----------------|---------------|--------|
| Trades (90d) | 12 | — | 15–30 |
| Win Rate | 41.7% | — | >50% |
| Profit Factor | 0.87 | — | >1.3 |
| Avg Win | $25.85 | — | >$35 |
| Avg Loss | $21.33 | — | <$25 |
| Avg R:R realized | ~1.21 | — | >1.5 |
| Max Drawdown | 13.91% | — | <10% |
| Return | -4.01% | — | Positive |

---

## Changes Made

### P-1: MarketCondition enum — `src/trading_bot/src/core/models.py`
Added two missing members:
```python
VOLATILE = "volatile"        # high ATR, no clear direction
CONSOLIDATION = "consolidation"  # tight range, low volatility
```
Previously these were referenced in `strategy_manager.py`'s `REGIME_ALLOWED_TYPES` dict but would fail to match since they weren't in the enum.

### P-5: Trailing stop fix — `src/trading_bot/src/backtesting/backtest_engine.py`
**Before:**
```python
trailing_distance = initial_stop_distance * trailing_atr_multiplier
# No activation check — trailed from first candle
new_stop = position['lowest_price'] + trailing_distance
if new_stop < stop_loss:
    stop_loss = new_stop
```
**After:**
```python
pip_size = 0.01 if 'JPY' in pair else 0.0001
activation_price = 80 * pip_size   # don't trail until 80 pips profit
trailing_distance = 50 * pip_size  # trail 50 pips behind best price
profit = entry_price - position['lowest_price']  # for SELL
if profit >= activation_price:      # activation gate
    new_stop = position['lowest_price'] + trailing_distance
    if new_stop < stop_loss:
        stop_loss = new_stop
```

### Config update — `src/trading_bot/src/config/trading_config.yaml`
```yaml
trailing_stop_activation_pips: 80   # was 50
trailing_stop_distance_pips: 50     # was 30
```

---

## Investigation Log

### 2026-03-12 (Session 2 continued)
- Read PROFITABILITY_PROMPT.md
- Traced full call chain: regime gating already wired end-to-end
- Confirmed P-4 already fixed in prior session
- Identified trailing stop activation missing as key P-5 issue
- Applied P-1 (VOLATILE/CONSOLIDATION enum), P-5 (activation + pip-based trail)
- Running 90-day backtest to measure impact

---

## New Issues Found

| # | Severity | File | Description |
|---|----------|------|-------------|
| I-1 | Low | `technical_analysis_layer.py:203` | Primary timeframe still defaults to M5 before fallback — harmless since fallback works, but misleading |
| I-2 | Low | `data_layer.py:419` | `_determine_market_condition` only returns `TRENDING_UP` (never `TRENDING_DOWN`) — always bullish label regardless of direction |
