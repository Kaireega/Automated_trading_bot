# Backtest Performance Tracker
> Tracking backtest speed and parallelization improvements.
> Started: 2026-03-15

## Timing
| Run | Config | Wall Clock Time | CPU Usage | Notes |
|-----|--------|----------------|-----------|-------|
| Before (single-threaded) | 730d, 3 pairs, H4+H1+M15, 1h loop | >5 min (killed) | ~95% 1 core | Baseline — killed by user |
| Session 7 BT-2 (parallel) | 730d, 2 pairs, H4+M15, 1h loop | ~8–10 min/pair | 2 cores | Option C — 2 separate processes |
| Session 8 BT-3 (parallel) | 730d, 2 pairs, D1+H4+M15, 4h loop | ~9 min/pair | 2 cores | 4× faster loop (4h step vs 1h) |
| Session 8 FTMO sim (parallel) | 730d, 2 pairs, D1+H4+M15, 4h loop | ~9 min/pair | 2 cores | Same speed as BT-3 |

## Speedup Sources

| Change | Speedup | Session |
|--------|---------|---------|
| Parallel by pair (3 processes) | ~3× | 7 |
| 4h loop step (was 1h) | ~4× | 8 |
| debug_tracker silenced | Significant (M15 load) | 8 |
| Combined (parallel + 4h loop) | ~12× vs baseline | 8 |

## Approach: Option C — Separate Script Invocations

No engine changes needed. `--pairs` flag already supported. Each pair runs in its own process:
```bash
python3 run.py backtest --pairs EUR_USD --days 730 > /tmp/eur.log 2>&1 &
python3 run.py backtest --pairs GBP_USD --days 730 > /tmp/gbp.log 2>&1 &
```

## Key Flags Added

| Flag | Purpose | Example |
|------|---------|---------|
| `--pairs PAIR` | Run single pair only | `--pairs EUR_USD` |
| `--ftmo` | FTMO mode: 0.5% risk, drawdown limits | `--ftmo` |
| `--end-offset N` | Shift end date back N days (train/test split) | `--end-offset 230` |
| `--balance N` | Initial balance | `--balance 10000` |

## Train/Test Split Usage (Phase 3)

```bash
# Train (500d ending 230d ago — 2024-03-19 to 2025-08-02):
python3 run.py backtest --days 500 --end-offset 230 --pairs EUR_USD --balance 10000 --ftmo &
python3 run.py backtest --days 500 --end-offset 230 --pairs GBP_USD --balance 10000 --ftmo &

# Test (230d ending today — 2025-08-02 to 2026-03-19, UNCHANGED system):
python3 run.py backtest --days 230 --pairs EUR_USD --balance 10000 --ftmo &
python3 run.py backtest --days 230 --pairs GBP_USD --balance 10000 --ftmo &
```
