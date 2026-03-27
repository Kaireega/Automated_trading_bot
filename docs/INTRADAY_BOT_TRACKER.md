# Intraday Bot Build Tracker
> Session-based intraday strategies for FTMO.
> Started: 2026-03-19
> Separate system from swing bot. Different strategies, different timeframes, different edge.

## Build Progress
| # | Component | Status |
|---|-----------|--------|
| 1 | Session clock (trading window manager) | ✅ Done |
| 2 | Asian Range Breakout strategy | ✅ Done |
| 3 | London Open ORB strategy | ✅ Done |
| 4 | NY Overlap Momentum strategy | ✅ Done |
| 5 | FTMO risk manager | ✅ Done |
| 6 | Intraday manager (orchestrator) | ✅ Done |
| 7 | Backtest engine (M5/M15 loop) | ✅ Done |
| 8 | 365-day backtest | ⬜ |
| 9 | Out-of-sample validation (250d train / 115d test) | ⬜ |
| 10 | FTMO challenge simulation (30-day windows) | ⬜ |

## Backtest Results
| Run | Strategies | Trades | WR | PF | Monthly Return | Max DD | FTMO Pass? |
|-----|-----------|--------|----|----|---------------|--------|------------|
