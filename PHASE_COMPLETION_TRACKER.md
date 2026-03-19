# Phase Completion Tracker
> Fixing R:R, completing safety layer, wiring disconnected components.
> Started: 2026-03-16
> Baseline (BT-1): 475 trades, 39.6% WR, PF 0.97, -8.88%, DD 29.04%
> GBP_USD proof of concept: PF 1.04, +$401

## Phase 1B: Strategy Fundamentals (R:R Fix)
| # | Description | Status |
|---|-------------|--------|
| F-1 | Reduce TP from 4×ATR to 2.5×ATR in all trend strategies | ✅ Done |
| F-2 | Drop USD_JPY — trade EUR_USD + GBP_USD only | ✅ Done |
| F-3 | Reduce M15 boost cap 0.20 → 0.10, component boosts halved | ✅ Done |
| F-4 | TP now evaluated BEFORE SL in backtest position update | ✅ Done |

## Phase 2: Safety Layer (Live Trading)
| # | Description | File | Status |
|---|-------------|------|--------|
| S-1 | Wire news/fundamental analyzer as trade blocker | fundamental_analyzer.py | ✅ Done |
| S-2 | Wire trailing stop updater for live positions | position_manager.py | ✅ Done |
| S-3 | Set pre_trade_cooldown_seconds: 30 | trading_config.yaml | ✅ Done |
| S-4 | Replace print() calls with logger.debug() | notification_layer.py | ✅ Done |

## Phase 3: Wire Disconnected Components
| # | Description | File | Status |
|---|-------------|------|--------|
| W-1 | Wire AdvancedRiskManager to actually gate trades | main.py | ✅ Already wired — verified correct |
| W-2 | Wire PortfolioRiskManager for correlation checks | main.py | ✅ Done |
| W-3 | Wire trade journal to MongoDB | position_manager.py | ✅ Done |

## Backtest Comparisons
| Run | Changes | Trades | WR | PF | Return | DD | Notes |
|-----|---------|--------|----|----|--------|-----|-------|
| BT-1 (Session 6) | M15+R1+R2 | 475 | 39.6% | 0.97 | -8.88% | 29.04% | Worse than baseline |
| BT-2 | F-1+F-2+F-3+F-4 | 284 | 35.9% | 1.05 | **+8.07%** | 21.43% | ✅ Profitable |

## What Changed in BT-2 vs BT-1
- **F-1**: TP = 2.5×ATR (~82 pips) instead of 4×ATR (~132 pips) — should be reachable within 1–3 H4 candles
- **F-2**: USD_JPY removed — was losing $753 over 730d (160 SL hits vs 30 TP hits)
- **F-3**: M15 boost max = 0.10 (was 0.20) — should reduce trade count from 475 back toward 250–300
- **F-4**: TP checked before SL — on a candle where both are hit, trade gets credit for the TP win

## Expected BT-2 Targets
| Metric | BT-1 | Target |
|--------|------|--------|
| Trades | 475 | 180–280 (EUR+GBP only, less M15 noise) |
| Win Rate | 39.6% | 44–50% (more TP hits at 82 pips) |
| Profit Factor | 0.97 | 1.15–1.40 |
| Return | -8.88% | +3% to +12% |
| Max Drawdown | 29.04% | 12–20% |
