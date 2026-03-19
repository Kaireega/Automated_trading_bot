# Strategy Overhaul Tracker
> Replacing 9-indicator consensus with 2-strategy regime-switched system.
> Started: 2026-03-18
> Baseline: 284 trades, 35.9% WR, PF 1.045, +8.07%, DD 21.43% (730d)

## Phase 1: New Strategy Architecture
| # | Description | Status |
|---|-------------|--------|
| A-1 | Add D1 timeframe to data pipeline | ✅ Done |
| A-2 | Build Daily Breakout strategy (trend regime) | ✅ Done |
| A-3 | Build Structure Reversal strategy (ranging regime) | ✅ Done |
| A-4 | Rebuild regime detector (replace ADX threshold with proper detection) | ✅ Done |
| A-5 | Replace consensus voting with hard regime switch | ✅ Done |
| A-6 | M15 pullback entry (replace confidence boost) | ✅ Done |

## Phase 2: Risk & Sizing for FTMO
| # | Description | Status |
|---|-------------|--------|
| R-1 | FTMO drawdown rules in backtest (5% daily, 10% total) | 🔄 In Progress |
| R-2 | Position sizing for $10K FTMO account | 🔄 In Progress |
| R-3 | Kill switch: halt trading if 4% total drawdown reached | 🔄 In Progress |

## Phase 3: Out-of-Sample Testing
| # | Description | Status |
|---|-------------|--------|
| T-1 | Split 730 days: 500 train / 230 test | ⬜ |
| T-2 | Optimize on train period only | ⬜ |
| T-3 | Run UNCHANGED on test period | ⬜ |
| T-4 | Compare train vs test results | ⬜ |

## Backtest Comparisons
| Run | System | Trades | WR | PF | Return | DD | Notes |
|-----|--------|--------|----|----|--------|-----|-------|
| Old system (BT-2) | 9-strategy consensus | 284 | 35.9% | 1.045 | +8.07% | 21.43% | Baseline |
| BT-3 EUR_USD | New 2-strategy | 36 | 44.4% | 1.49 | +9.77% | 2.96% | ✅ Big DD improvement |
| BT-3 GBP_USD | New 2-strategy | 51 | 47.0% | 1.70 | +20.43% | 9.58% | ✅ Best result yet |
| Train (500d) | New 2-strategy | — | — | — | — | — | — |
| Test (230d) | New 2-strategy (unchanged) | — | — | — | — | — | — |
| FTMO sim | New + FTMO rules | — | — | — | — | — | — |
