# Swing Conversion & V-Issue Tracker
> Converting from intraday to swing trading + fixing V-issues.
> Started: 2026-03-11 16:15
> Last updated: 2026-03-12 02:45

---

## Phase 1: V-Issue Fixes

| # | Description | Status | Verified? |
|---|-------------|--------|-----------|
| V-1 | SELL stop losses inverted — root cause was cross-pair trailing stop contamination (EUR_USD candle prices used for GBP_USD position evaluation) | ✅ Fixed | ✅ Yes |
| V-2 | Position sizing capped to nano-lots (~136 units) — root cause: `max_position_size/100 * balance / entry` treated % as fraction | ✅ Fixed | ✅ Yes |

### V-1 Fix Detail
- **Root cause:** `_update_open_positions()` evaluated ALL pairs' positions using the current pair's candles. EUR_USD prices (~1.18) were applied to GBP_USD stops, dragging GBP_USD trailing stops to ~1.18.
- **Fix:** Added `current_pair` parameter — each pair's candles only evaluate that pair's open position.
- **File:** `src/trading_bot/src/backtesting/backtest_engine.py`

### V-2 Fix Detail
- **Root cause:** `max_units = balance * (max_position_size/100) / entry_price = $150/1.33 = 112 units`
- **Fix:** `max_units = max_position_size * 100_000 = 150,000 units` (1.5 standard lots)
- **File:** `src/trading_bot/src/backtesting/backtest_engine.py`

---

## Phase 2: Swing Trading Conversion

| # | Area | Change | Status |
|---|------|--------|--------|
| S-1 | Config: Timeframes | M5/M15 → H1/H4; `default_timeframe: H4` | ✅ Done |
| S-2 | Config: Trading parameters | `risk_percentage: 1.0`, `max_trades_per_day: 2`, 3 major pairs | ✅ Done |
| S-3 | Config: Hold times | `min_hold: 240min`, `max_hold: 14400min (10 days)`, `default: 2880min (2 days)` | ✅ Done |
| S-4 | Config: Risk & position sizing | `max_open_trades: 2`, `max_daily_loss: 2.0`, `max_risk_threshold: 0.5` | ✅ Done |
| S-5 | Main loop / data | `analysis_frequency: 3600`, `update_frequency: 3600` (1hr) | ✅ Done |
| S-6 | Strategies: Disable intraday-only | London_Open_Break, NY_Open_Momentum, all scalping → `enabled: false, allocation: 0` | ✅ Done |
| S-7 | Strategies: Tune swing strategies | EMA 12/26, ADX threshold 25, ATR mult 2.0, all H4/D1 params | ✅ Done |
| S-8 | Strategy manager | `consensus_threshold: 0.60`, `min_signals_required: 2`, `min_confluence_score: 0.40` | ✅ Done |
| S-9 | Risk manager | `risk_reward_ratio_minimum` now reads from config (was hardcoded 1.5) | ✅ Done |
| S-10 | Position manager | Position check loop: 30s → 1800s (30 min, swing pace) | ✅ Done |
| S-11 | Notifications | `notification_cooldown: 14400`, `signal_generated: false`, `interval_hours: 4` | ✅ Done |
| S-12 | Backtest engine | H1/H4 timeframes, 1hr iterations, H4 candle source, H4 fallback in decision layer | ✅ Done |

---

## Phase 3: Backtest Bug Fixes (this session)

| # | Bug | Fix | File |
|---|-----|-----|------|
| B-1 | `_create_market_context` hardcoded `TimeFrame.M5` → always returned UNKNOWN | Use H4 → H1 → M5 fallback chain | `backtest_engine.py:872` |
| B-2 | Duplicate trades — same H4 candle re-analyzed every hour for 4 hours → 4 identical trades | Added `last_trade_time` per-pair cooldown (240 min) in `_run_simulation` | `backtest_engine.py:745` |
| B-3 | Open positions overwritten — new signal replaced existing position dict without closing it → 511 orphaned trades, 0.2% win rate | Added open position guard: skip entry if `pair in self.open_positions` | `backtest_engine.py:799` |

---

## Backtest Results

### Before fixes (previous session — broken)
- 28 trades / 90 days but duplicates contaminating results
- Profit Factor 1.94 (misleading — V-1 trailing stop contamination inflating wins)
- Win Rate 3.6%

### After all fixes (this session — clean run)
| Metric | Result | Target | Status |
|--------|--------|--------|--------|
| Period | 90 days | 90 days | ✅ |
| Trade count | 12 | 25–45 (2–5/week) | ⚠️ Low |
| Win Rate | 41.7% | 45–55% | ⚠️ Close |
| Profit Factor | 0.87 | >1.3 | ❌ Below target |
| Avg Win | $25.85 | $50–300 | ⚠️ Small (small account) |
| Avg Loss | $21.33 | $25–150 | ✅ |
| Max Drawdown | 13.91% | <10% | ❌ High |
| Return | -4.01% | Positive | ❌ |
| Sharpe | -0.31 | >0.5 | ❌ |

---

## Remaining Work (to reach profitable bot)

| Priority | Fix | File | Impact |
|----------|-----|------|--------|
| P-1 | Fix `MarketCondition` enum — add `TRENDING_UP`, `TRENDING_DOWN`, `VOLATILE`, `CONSOLIDATION` | `src/core/models.py` | Unlocks regime gating |
| P-2 | Wire regime-based strategy eligibility gate in `generate_consensus_signal()` | `src/strategies/strategy_manager.py` | Prevents mean-reversion strategies firing in trends (and vice versa) |
| P-3 | Pass `regime` from `_create_market_context` into strategy manager call chain | `backtest_engine.py` → `technical_analysis_layer.py` → `strategy_manager.py` | Required for P-2 to work |
| P-4 | Remove premature 5% unrealized profit auto-close in `_should_close_position` | `src/core/position_manager.py` | Stops killing winning trades early in live trading |
| P-5 | Review trailing stop settings — 1.5x ATR trailing is closing winners before TP | `trading_config.yaml` | Improve realized R:R from ~1.2:1 to target 2:1 |
| P-6 | Phase 2 (post 300 trades): Wire SmartExecutionEngine, PortfolioRiskManager, AdvancedRiskManager | `main.py` | Execution quality + full risk management |

---

## Investigation Log

### 2026-03-11 — Session 1
- Read `SWING_CONVERSION_PROMPT.md` and `RUNTIME_VERIFICATION_PROMPT.md`
- Applied all S-1 through S-12 config and code changes
- Fixed V-1 (cross-pair contamination) and V-2 (nano-lot sizing)
- Ran initial backtest: too few signals (5 trades / 90 days) — lowered `min_confluence_score` to 0.40
- Discovered duplicate trades issue (same H4 candle analyzed 4×/hour)

### 2026-03-12 — Session 2 (this session)
- Fixed `_create_market_context` (B-1): was always returning UNKNOWN due to hardcoded M5
- Fixed duplicate trades (B-2): added per-pair 240-min trade cooldown
- Fixed open position overwriting (B-3): added `pair in self.open_positions` guard
- Ran clean 90-day backtest: 12 trades, 41.7% win rate, PF 0.87
- Read `trading_bot_handoff_report.md` — confirmed regime gating is the #1 remaining fix
- Identified P-1 through P-6 as next steps

---

## Verification

| # | Test | Expected | Actual | Pass? |
|---|------|----------|--------|-------|
| T-1 | V-2: Position size for EUR_USD, $500, 1% risk, 50-pip SL | ~1,000 units | 987 units | ✅ |
| T-2 | V-1: GBP_USD SELL stop above entry | stop > entry_price | ✅ Confirmed in logs | ✅ |
| T-3 | No duplicate trades on same H4 candle | 1 trade per 4hr cooldown | ✅ Confirmed | ✅ |
| T-4 | No open position overwrite | Position held, new signal blocked | 500 "risk_management" rejections | ✅ |
| T-5 | EUR_USD and GBP_USD both trade | Signals on all 3 pairs | EUR_USD BUY + GBP_USD SELL seen | ✅ |
| T-6 | Profit factor > 1.3 | >1.3 | 0.87 | ❌ Needs regime gating |
