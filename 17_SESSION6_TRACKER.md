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
| Run | Changes | Trades | WR | PF | Return | DD | Notes |
|-----|---------|--------|----|----|--------|-----|-------|
| Baseline | Session 5 | 298 | 36.2% | 0.98 | -2.79% | 24.62% | Reference |
| BT-1 | All Session 6 changes | — | — | — | — | — | **Run next** |

## Investigation Log
- 2026-03-15: Confirmed all M-1 through R-2 are in code. Tracker was stale — updated.
- M15 EMA8/EMA21 alignment check implemented (contradicting M15 → 0 boost, no penalty)
- R-1: consecutive_losses tracked per pair, 24h cooldown enforced in simulation loop
- R-2: ADX value stored in metadata at analysis time, read at trade execution
- H4 EMA100 additional filter added (above M-3 in Session 6)
- Pair isolation fix: each pair's position only evaluated with that pair's candles
