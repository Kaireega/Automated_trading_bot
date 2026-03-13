# Swing Conversion & V-Issue Tracker
> Converting from intraday to swing trading + fixing V-issues.
> Started: 2026-03-11 16:15
> Last updated: 2026-03-11 16:15

## Phase 1: V-Issue Fixes
| # | Description | Status | Verified? |
|---|-------------|--------|-----------|
| V-1 | SELL stop losses inverted (below entry instead of above) | ⬜ | ⬜ |
| V-2 | Position sizing capped to nano-lots (~136 units) | ⬜ | ⬜ |

## Phase 2: Swing Trading Conversion
| # | Area | Change | Status |
|---|------|--------|--------|
| S-1 | Config: Timeframes | M5/M15 → H1/H4/D1 | ⬜ |
| S-2 | Config: Trading parameters | Swing-appropriate values | ⬜ |
| S-3 | Config: Hold times | Hours → days/weeks | ⬜ |
| S-4 | Config: Risk & position sizing | Small account safe values | ⬜ |
| S-5 | Main loop | 5min polling → 1hr polling | ⬜ |
| S-6 | Strategies: Disable intraday-only | Scalping + session strategies off | ⬜ |
| S-7 | Strategies: Tune swing strategies | Indicator params for H4/D1 | ⬜ |
| S-8 | Strategy manager | Adjust consensus for fewer signals | ⬜ |
| S-9 | Risk manager | Wider stops, smaller positions | ⬜ |
| S-10 | Position manager | Multi-day hold support | ⬜ |
| S-11 | Notifications | Reduce frequency for swing pace | ⬜ |
| S-12 | Backtest | Update for swing parameters | ⬜ |

## Investigation Log
[Updated as work progresses]

## Verification
| # | Test | Expected | Actual | Pass? |
|---|------|----------|--------|-------|
