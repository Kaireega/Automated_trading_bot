# Trade Pattern Analysis Report
**Generated:** 2026-03-13
**Data Source:** All backtest CSV files in `results/`
**Primary Dataset:** `backtest_trades_20260312_190912.csv` — 270 trades (Dec 2025–Mar 2026)
**Reference Dataset:** `backtest_trades_20260313_013038.csv` — 103 trades (Sep 2025–Mar 2026, 180-day run)

---

## Current Performance Baseline (180-day run)

| Metric | Value | Target |
|--------|-------|--------|
| Return | +1.01% | Positive ✅ |
| Win Rate | 35.0% | >35% 🔶 |
| Profit Factor | 1.02 | >1.3 🔶 |
| Max Drawdown | 9.22% | <10% ✅ |
| Trades | 103 over 180 days | — |

---

## 1. Per-Pair Performance

| Pair | Trades | WR | Avg Win | Avg Loss | Actual R:R | PF | Net P&L |
|------|--------|----|---------|----------|------------|-----|---------|
| EUR_USD | 88 | 25.0% | $6.11 | -$3.41 | 1.79:1 | 0.60 | -$90.40 |
| GBP_USD | 83 | 20.5% | $6.54 | -$3.22 | 2.03:1 | 0.52 | -$101.42 |
| USD_JPY | 99 | 27.3% | $5.80 | -$3.27 | 1.77:1 | 0.67 | -$78.92 |

**Key findings:**
- GBP_USD is the weakest pair (PF 0.52, WR 20.5%) — consider reducing allocation or adding stricter filters
- USD_JPY is the strongest pair overall but has a severe directional bias (see Section 3)
- Actual R:R (1.85:1) vs theoretical (2.0:1) — 8% slippage, not the main problem

---

## 2. Exit Reason Breakdown

| Exit Reason | Count | % | Avg P&L | Avg Duration |
|-------------|-------|---|---------|-------------|
| STOP_LOSS | 207 | 76.7% | -$3.30 | 693 min (11.5h) |
| TAKE_PROFIT | 63 | 23.3% | +$6.15 | 1,904 min (31.7h) |

**Key findings:**
- Trades are binary — almost always either full TP or full SL, very little middle ground
- **65.7% of all stop losses fire within 8 hours of entry** — trades that fail, fail fast
- Winning trades take ~2.8× longer to resolve than losing trades

---

## 3. Directional Bias (BUY vs SELL) ⚠️ CRITICAL

| Pair | Direction | Trades | WR | Net P&L |
|------|-----------|--------|----|---------|
| EUR_USD | buy | 12 | 25.0% | -$9.69 |
| EUR_USD | sell | 76 | 25.0% | -$80.72 |
| GBP_USD | buy | 21 | 19.0% | -$24.46 |
| GBP_USD | sell | 62 | 21.0% | -$77.00 |
| **USD_JPY** | **buy** | **25** | **40.0%** | **+$8.51** ✅ |
| **USD_JPY** | **sell** | **74** | **23.0%** | **-$87.44** ❌ |

**Key finding:** USD_JPY has a massive directional split — BUY is profitable (40% WR) while SELL is losing (23% WR). The bias reverses depending on the market regime (opposite in Sep–Dec vs Jan–Mar). A per-pair regime filter (EMA direction) would address this.

---

## 4. Time-Based Patterns

### 4a. Monthly Performance

| Month | Trades | WR | Net P&L | Notes |
|-------|--------|----|---------|-------|
| Sep–Nov 2025 | — | ~46% | Positive | Trending conditions |
| Dec 2025 | 48 | 20.8% | -$84.41 | Holiday chop |
| Jan 2026 | 114 | 23.7% | -$129.62 | Worst month |
| Feb 2026 | 75 | 22.7% | -$63.07 | Continued chop |
| Mar 2026 | 33 | **36.4%** | **+$6.36** | Recovery begins |

**Pattern:** Dec–Feb is consistently the weakest window for this strategy (holiday-to-year-start choppy period). The system outperforms in Q3/Q4 trending conditions.

### 4b. Duration vs Outcome ⚠️ CRITICAL

| Duration Bucket | Trades | WR | Avg P&L |
|----------------|--------|----|---------|
| <1 hour | 17 | 23.5% | -$0.62 |
| **1–4 hours** | **20** | **10.0%** | **-$2.56** ❌ |
| 4–8 hours | 26 | 30.8% | -$0.75 |
| **8–16 hours** | **54** | **42.6%** | **+$0.53** ✅ |
| 16–24 hours | 20 | 30.0% | -$0.20 |
| **>24 hours** | **48** | **47.9%** | **+$1.50** ✅ |

**Avg winning trade duration:** 1,867 min (31.1 hours)
**Avg losing trade duration:** 687 min (11.5 hours)

**Most actionable finding:** Trades exiting in 1–4 hours have 10% WR (catastrophic). Trades surviving past 8 hours have 42–48% WR — nearly double. If a trade is still alive after one H4 candle, it becomes a much better trade. A 2-candle confirmation rule would eliminate the worst entries.

### 4c. Entry Hour (UTC) Patterns

**Best entry hours (>40% WR):**

| Hour UTC | EUR_USD WR | GBP_USD WR | USD_JPY WR | Notes |
|----------|-----------|-----------|-----------|-------|
| 00–02 UTC | **60%** | **60%** | — | Asian open, low volatility, smooth trends |
| 13 UTC | — | — | **67%** | NY open |
| 17–18 UTC | 44% | 40% | **75%** | NY mid-session |

**Worst entry hours (0% WR, 5+ trades):**

| Hour UTC | Pair | Trades | Net P&L | Notes |
|----------|------|--------|---------|-------|
| 08, 12, 20 UTC | EUR_USD | 18 total | -$53 | London open spike, London PM |
| 11, 12, 15 UTC | GBP_USD | 18 total | -$61 | London mid-session |
| 09, 16 UTC | USD_JPY | 15 total | -$49 | London/NY overlap |

**Saving from blocking bad hours:** -$163 avoided on 51 trades

### 4d. Day of Week

| Day | Trades | WR | Net P&L |
|-----|--------|----|---------|
| Monday | 54 | 33.3% | -$4.01 |
| **Tuesday** | **49** | **16.3%** | **-$91.25** ❌ |
| Wednesday | 54 | 29.6% | -$30.97 |
| **Thursday** | **48** | **18.8%** | **-$64.64** ❌ |
| Friday | 50 | 28.0% | -$38.44 |
| Saturday | 6 | 0.0% | -$19.55 ❌ |
| Sunday | 9 | 11.1% | -$21.87 ❌ |

**Key finding:** Tuesday and Thursday account for -$156 (57.6% of all losses). Mon/Wed/Fri are far better. Weekends are near-zero-win.

---

## 5. P&L Distribution

| Bucket | Count | % | Notes |
|--------|-------|---|-------|
| -$4 to -$6 (full stop) | 53 | 19.6% | Max loss hit |
| -$2 to -$4 (partial stop) | 151 | 55.9% | Stopped below max |
| $0 to $2 (near breakeven) | 2 | 0.7% | Rare |
| $4 to $6 (near TP) | 36 | 13.3% | |
| $6 to $8 (full TP) | 17 | 6.3% | |
| $8+ (TP + trail) | 11 | 4.1% | Trailing stop extended |

**Finding:** Losses are NOT gapped/spiked through the stop — average loss ($3.30) is below the theoretical max ($5), meaning the stop is working as designed. Wins cleanly reach TP when direction is right.

---

## 6. Streak Analysis

| Metric | Value |
|--------|-------|
| Max winning streak | 5 |
| Max losing streak | 17 |
| Avg winning streak | 1.6 |
| Avg losing streak | 5.0 |

**Loss streak distribution:** 2-in-a-row = common, 9–17-in-a-row = occurs multiple times

**EUR_USD max losing streak:** 21 consecutive losses
**GBP_USD:** 4+ consecutive loss runs happen every ~9 trades

**No mean-reversion after losses:** Win rate after 3+ loss streak = 22.8%. After 5+ loss streak = 21.3%. Do NOT use martingale sizing — losing streaks are not self-correcting.

---

## 7. Breakeven Analysis

Actual R:R = 1.85:1 → breakeven WR = 35.1%
Current WR = 24.4% (primary dataset) / 35.0% (180-day)
**Gap:** 10.7 ppts below breakeven in adverse Dec–Mar market

With hour + day filters applied (simulation):
- 111 trades remaining → **WR 45.9%, Net +$128** vs original -$271
- Combined with USD_JPY sell exclusion: **83 trades, WR 47.0%**

---

## 8. Recommended Fixes (Priority Order)

### P1 — Hour Filter (Highest Impact)
**Block entries during confirmed zero-WR hours:**
```yaml
# In trading_config.yaml or session filter
blocked_hours_utc:
  EUR_USD: [8, 12, 20]
  GBP_USD: [11, 12, 15]
  USD_JPY: [9, 16]
```
**Expected impact:** Eliminate -$163 in losses, ~51 fewer trades, WR lift ~5–8 ppts

### P2 — Disable Weekend Trading
```yaml
avoid_sessions: ["SATURDAY", "SUNDAY"]
```
**Expected impact:** Eliminate -$41 in losses, 15 fewer trades

### P3 — 2-Candle Entry Confirmation
Don't execute a signal until it's confirmed on the NEXT H4 candle close. Eliminates the 1–4 hour WR=10% bucket.
**Expected impact:** ~20 fewer early-exit losers, WR lift ~3–5 ppts
**Trade-off:** Some late entries, slightly wider spread between signal and execution

### P4 — USD_JPY Direction Regime Filter
Only take USD_JPY SELL signals when price is below H4 EMA20. Only take BUY when above.
**Expected impact:** Eliminate -$87 in USD_JPY sell losses while preserving +$8 buy profits

### P5 — Avoid Tuesday and Thursday
```yaml
trading_days: [MONDAY, WEDNESDAY, FRIDAY]
```
**Expected impact:** Eliminate -$156, ~97 fewer trades, significant WR improvement

### P6 — USD_JPY Mid-Range Price Zone Exclusion
USD_JPY entries in the 155.60–156.66 range have only 12% WR vs 32%+ elsewhere. Add ATR contraction check — skip if ATR < 0.6× its 20-period average (consolidation signal).

---

## 9. Combined Filter Simulation

| Filter Combination | Trades | WR | Net P&L | vs Baseline |
|-------------------|--------|----|---------|-------------|
| No filters (baseline) | 270 | 24.4% | -$271 | — |
| P2 only (no weekends) | 255 | 25.5% | -$230 | +$41 |
| P1 + P2 (hours + weekends) | 204 | 30.9% | -$108 | +$163 |
| P1 + P2 + duration >8h proxy | 111 | 45.9% | +$128 | +$399 |
| All filters (P1–P4) | 83 | 47.0% | +$107 | +$378 |

> Note: The duration >8h proxy approximates the effect of 2-candle confirmation (P3). Actual implementation via code will vary.

---

## 10. Implementation Notes

These filters should be implemented in:
- **Hour filter:** `src/trading_bot/src/strategies/strategy_manager.py` — add UTC hour check in `generate_consensus_signal()`
- **Weekend filter:** `trading_config.yaml` → `trading.avoid_sessions` or backtest engine loop
- **2-candle confirmation:** `src/trading_bot/src/backtesting/backtest_engine.py` — defer execution by 1 H4 candle
- **USD_JPY direction filter:** `src/trading_bot/src/ai/technical_analysis_layer.py` — add per-pair EMA direction check (currently the EMA filter uses a single EMA50 for all pairs)

---

## Backtest Progression Log

| Date | Run | Trades | WR | PF | Return | DD | Notes |
|------|-----|--------|----|-----|--------|-----|-------|
| 2026-03-13 | Session 3 baseline | 91 | 31.9% | 0.79 | -11.31% | 14.45% | Before session 4 fixes |
| 2026-03-13 | EMA50+200c+Ichimoku | 90 | 32.2% | 0.81 | -10.44% | 14.40% | B-6, B-7, chikou fix |
| 2026-03-13 | EMA 21/55 + I-5 | 87 | 33.3% | 0.83 | -8.69% | 14.39% | Direction consensus fix |
| 2026-03-13 | I-3 + I-9 wider stops | 55 | 34.6% | 0.95 | -1.47% | 8.91% | 90-day, $10k |
| 2026-03-13 | All fixes (180-day) | 103 | 35.0% | 1.02 | +1.01% | 9.22% | **Current best** |

---

*Next steps: Implement P1 (hour filter) and P2 (weekend disable) as they are low-risk, high-impact config changes. Then re-run 180-day backtest to validate.*
