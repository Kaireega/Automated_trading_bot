# Backtest Performance Tracker
> Parallelizing the 730-day backtest.
> Started: 2026-03-15

## Timing
| Run | Config | Wall Clock Time | CPU Usage | Notes |
|-----|--------|----------------|-----------|-------|
| Before (single-threaded) | 730d, 3 pairs, H4+H1+M15 | >5 min (killed) | ~95% 1 core | Baseline — killed by user |
| After (parallel by pair) | Same | — | 3 cores | Option C — 3 separate processes |

## Approach: Option C — Separate Script Invocations

No engine changes needed. `--pairs` flag already supported. Each pair runs in its own process:
- `python3 run.py backtest --pairs EUR_USD` → Process 1
- `python3 run.py backtest --pairs GBP_USD` → Process 2
- `python3 run.py backtest --pairs USD_JPY` → Process 3

All 3 launched simultaneously with `&` → 3 cores used in parallel.

## Changes
| # | Description | File | Status |
|---|-------------|------|--------|
| 1 | Confirmed --pairs flag already exists (single pair supported) | run.py | ✅ No change needed |
| 2 | Launch 3 processes in parallel via shell & operator | shell | ✅ |
| 3 | Merge per-pair results into combined report | 19_SESSION6_RESULTS.md | ⬜ After runs complete |
