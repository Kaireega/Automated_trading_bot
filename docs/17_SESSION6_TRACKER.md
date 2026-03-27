# Session 6 Tracker — M15 Integration + Risk Management
> Started: 2026-03-14
> Last updated: 2026-03-15
> Baseline: 298 trades, 36.2% WR, PF 0.98, -2.79% return, 24.62% DD (730d)

## Changes Planned
| # | Description | Status |
|---|-------------|--------|
| M-1 | Add M15 to config timeframes + weights (H4:50/H1:30/M15:20) | ✅ Done |
| M-2 | Fetch M15 candles in backtest engine (400-candle window) | ✅ Done |
| M-3 | M15 confidence boost in technical analysis (additive 0–0.20, never override H4 gates) | ✅ Done |
| M-4 | Verified all gates (EMA, ADX, ATR contraction) stay on H4 primary candles | ✅ Done |
| R-1 | Consecutive loss limit: 3 losses → 24h cooldown per pair | ✅ Done |
| R-2 | Scale risk 1% → 0.5% when ADX 25–30 (borderline trend) | ✅ Done |

## Backtest Comparisons
| Run | Changes | Trades | WR | Breakeven WR | PF | Return | DD | Notes |
|-----|---------|--------|----|--------------|----|--------|-----|-------|
| Baseline | Session 5 | 298 | 36.2% | 36.6% | 0.98 | -2.79% | 24.62% | Reference |
| BT-1 | M15 + R-1 + R-2 | 475 | 39.6% | 40.4% | 0.97 | -8.88% | 29.04% | ❌ Worse |

### BT-1 Per-Pair Breakdown
| Pair | Trades | WR | Breakeven WR | PF | Net P&L | DD | TP Hits | SL Hits |
|------|--------|----|--------------|----|---------|-----|---------|---------|
| EUR_USD | 133 | 34.6% | 36.2% | 0.93 | -$535.87 | 17.61% | 36 | 92 |
| GBP_USD | 151 | 37.1% | 36.1% | 1.04 | +$401.10 | 16.84% | 46 | 103 |
| USD_JPY | 191 | 45.0% | 47.1% | 0.92 | -$752.94 | 14.98% | 30 | 160 |

### BT-1 Root Cause Analysis

**Problem 1 — Trade count exploded (298 → 475, +59%)**
M15 confidence boost is passing too many borderline signals through the consensus gate. More trades = more exposure = more losses in a ranging/adverse market. The M15 boost may be too permissive (0–0.20 additive range allows weak signals to cross the 0.60 threshold).

**Problem 2 — USD_JPY: wrong R:R structure**
- 160 SL hits vs only 30 TP hits out of 191 trades
- Avg win $100.64, avg loss $89.60 → actual R:R only 1.12:1
- 4×ATR TP on JPY is unreachable. JPY is a mean-reverting, range-bound pair — price returns to SL before reaching TP 84% of the time
- **Fix:** Reduce USD_JPY TP from 4×ATR to 2×ATR (1:1 R:R requires WR > 50% to break even, but at least TP gets hit more often)
- OR: disable USD_JPY and focus only on EUR/GBP

**Problem 3 — EUR_USD WR 1.6% below breakeven**
34.6% vs 36.2% breakeven. EMA100 filter is not tight enough — still allowing counter-trend entries during EUR/USD's long whipsaw periods.

**What's Working**
- GBP_USD is profitable: PF 1.04, +$401 over 2 years ✅
- Avg win > avg loss on all 3 pairs (correct R:R direction, unlike Session 5)
- SL/TP mechanics confirmed working (SL/TP exit reasons dominate, no unexplained closures)

## Next Steps — BT-2 Plan
| # | Fix | Target |
|---|-----|--------|
| N-1 | Cap M15 boost at 0.10 (not 0.20) to reduce trade count | Trades back to ~320-350 |
| N-2 | USD_JPY: reduce TP from 4×ATR to 2×ATR | More TP hits, better R:R |
| N-3 | USD_JPY: tighten ADX gate to > 30 (vs 25 globally) | Filter JPY ranging periods |
| N-4 | EUR_USD: tighten EMA filter (require 2 consecutive candles above EMA) | Reduce counter-trend entries |

## Investigation Log
- 2026-03-15: Confirmed all M-1 through R-2 are in code. Tracker was stale — updated.
- M15 EMA8/EMA21 alignment check implemented (contradicting M15 → 0 boost, no penalty)
- R-1: consecutive_losses tracked per pair, 24h cooldown enforced in simulation loop
- R-2: ADX value stored in metadata at analysis time, read at trade execution
- H4 EMA100 additional filter added (above M-3 in Session 6)
- Pair isolation fix: each pair's position only evaluated with that pair's candles
- 2026-03-16: BT-1 completed. Results: 475 trades, 39.6% WR, PF 0.97, -8.88%, DD 29.04% — WORSE than baseline
- Root cause: M15 boost adding too many trades, USD_JPY TP unreachable (30/191 hits), EUR_USD still counter-trend
- Action: BT-2 will target trade count reduction, USD_JPY TP adjustment, tighter EUR_USD filter
