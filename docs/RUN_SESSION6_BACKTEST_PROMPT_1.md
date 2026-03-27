# PROMPT: Run Session 6 Backtest + Analyze Results

## Who You Are

You are a **Senior Quantitative Developer** evaluating whether a swing trading bot has crossed from losing to breakeven/profitable. You are rigorous with data — you don't celebrate until the numbers prove it, and you don't panic until you've diagnosed why. Every decision from here is driven by backtest evidence, not intuition.

---

## Context

**Read `18_SESSION6_REPORT.md` first** — it lists every change made in Session 6.

**Session 6 changes (all implemented, not yet tested):**
- M15 confidence boost layer (additive 0.0–0.20, H4 gates unchanged)
- R-1: Consecutive loss limit (3 losses → 24h cooldown per pair)
- R-2: ADX risk scaling (1% → 0.5% when ADX 25–30)
- H4 EMA100 trend gate
- 400-candle M15 window

**Baseline to beat (Session 5, 730-day):**

| Metric | Value |
|--------|-------|
| Trades | 298 |
| Win Rate | 36.2% (breakeven = 36.6%) |
| Profit Factor | 0.98 |
| Return | -2.79% |
| Max Drawdown | 24.62% |
| Avg Win | $91.89 |
| Avg Loss | $159.07 |

---

## Step 0: Create Tracker

Create `19_SESSION6_RESULTS.md` in the project root:

```markdown
# Session 6 Results
> 730-day backtest after M15 + R-1 + R-2 + EMA100 integration.
> Date: [date/time]

## BT-1 Results (vs Session 5 Baseline)
| Metric | Session 5 | Session 6 | Change | Better? |
|--------|-----------|-----------|--------|---------|
| Trades | 298 | — | — | — |
| Win Rate | 36.2% | — | — | — |
| Breakeven WR | 36.6% | — | — | — |
| Profit Factor | 0.98 | — | — | — |
| Return | -2.79% | — | — | — |
| Max Drawdown | 24.62% | — | — | — |
| Avg Win | $91.89 | — | — | — |
| Avg Loss | $159.07 | — | — | — |
| Sharpe | — | — | — | — |

## Per-Regime Breakdown
| Regime | Trades | Wins | Losses | Win% | Avg P&L |
|--------|--------|------|--------|------|---------|

## Per-Exit-Reason Breakdown
| Exit Reason | Count | % of Total | Avg P&L | Avg Hold (hrs) |
|-------------|-------|-----------|---------|----------------|

## Per-Pair Breakdown
| Pair | Trades | Win% | PF | Net P&L | Notes |
|------|--------|------|----|---------|-------|

## M15 Boost Analysis
| M15 Boost Given | Trades | Win% | Avg P&L | Notes |
|-----------------|--------|------|---------|-------|
| No boost (0.0) | — | — | — | H4+H1 alone |
| Partial (0.01–0.14) | — | — | — | Some M15 alignment |
| Full (0.15–0.20) | — | — | — | Strong M15 alignment |

## R-1 Impact (Consecutive Loss Limit)
- Pairs paused: — times across 730 days
- Trades avoided by cooldown: —
- Estimated P&L saved: —

## R-2 Impact (ADX Risk Scaling)
- Trades at half risk (ADX 25–30): —
- Trades at full risk (ADX 30+): —
- Avg P&L at half risk: —
- Avg P&L at full risk: —

## Diagnosis & Next Steps
[Filled after analyzing results]
```

---

## Step 1: Run the 730-Day Backtest

```bash
python run.py --backtest 2>&1 | tee session6_backtest.log
```

Use the same parameters as Session 5's 730-day run (Mar 2024 – Mar 2026, 3 pairs, $500 or $10,000 starting balance — match whatever Session 5 used).

---

## Step 2: Record Top-Line Results

Fill in the BT-1 results table. The critical numbers to compare:

| Question | How To Judge |
|----------|-------------|
| Did WR cross breakeven (36.6%)? | WR > 36.6% = profitable on expectancy |
| Did PF cross 1.0? | PF > 1.0 = gross profit exceeds gross loss |
| Did return go positive? | Return > 0% = net profitable |
| Did drawdown decrease? | DD < 24.62% = risk improved |
| Did trade count change significantly? | ±20% is expected; >50% change means a filter is too aggressive or too loose |

---

## Step 3: Build the Breakdowns

Parse the backtest output or CSV to build per-regime, per-exit, per-pair, and M15 boost breakdowns. These tell you WHERE improvement came from (or didn't).

### Per-Regime

```bash
# If diagnostic logging was added in a prior session:
grep "OPEN:" session6_backtest.log | grep -oP 'regime=\K\w+' | sort | uniq -c | sort -rn
grep "CLOSE:" session6_backtest.log | grep "regime=trending_up" | grep -oP 'pnl=.\K[-0-9.]+' | awk '{sum+=$1; n++; if($1>0) w++} END {printf "N=%d Win%%=%.1f%% AvgPnL=$%.2f\n", n, w/n*100, sum/n}'
```

If diagnostic logging isn't in place yet, add it now (see prior session prompts for the exact logging format), run the backtest again, then parse.

### Per-Pair

```bash
# From CSV or log:
for pair in EUR_USD GBP_USD USD_JPY; do
    echo "=== $pair ==="
    grep "$pair" results.csv | awk -F',' '{trades++; pnl+=$PNL_COL; if($PNL_COL>0) wins++} END {printf "Trades=%d Win%%=%.1f%% Net=$%.2f\n", trades, wins/trades*100, pnl}'
done
```

### M15 Boost Impact

If the M15 boost value is logged or stored in the trade record:
```bash
# Trades where M15 gave no boost vs trades where it gave full boost
# Compare win rates — if M15-boosted trades don't win more often, M15 isn't helping
```

If M15 boost isn't recorded per trade, add `recommendation.metadata['m15_boost'] = boost_value` in the M15 calculation and store it in the trade record. Then re-run.

---

## Step 4: Diagnose and Decide

Use this decision tree based on BT-1 results:

### Outcome A: PF > 1.05 and Return Positive
**The bot is profitable.** Next steps:
1. Run a 180-day sub-period analysis to check consistency (are profits concentrated in one month, or spread out?)
2. If consistent: move to paper trading on OANDA demo for 2–4 weeks
3. Monitor for live-vs-backtest divergence (slippage, spread, execution delay)
4. If paper trading confirms: go live with the small account at current risk settings

### Outcome B: PF 1.00–1.05 (Breakeven Zone)
**Almost there — needs targeted tuning.** Use the breakdowns to find the weakest link:
- If one pair is dragging results down (negative net P&L while others are positive): consider removing it
- If one regime has <25% WR: tighten entry criteria for that regime or disable trading in it
- If trailing stop exits average negative P&L: widen trail distance from 50 to 60 pips
- If M15 boost doesn't correlate with higher WR: remove M15 (simplify back to H4+H1)
- If >40% of trades exit at MAX_HOLD_TIME: the TP target may be too ambitious — try 3.5x ATR instead of 4x

### Outcome C: PF 0.95–1.00 (Still Slightly Losing — Similar to Session 5)
**M15 + risk management didn't move the needle enough.** Investigate:
1. Is M15 adding noise? Compare WR of M15-boosted trades vs non-boosted. If no difference or worse, remove M15.
2. Is R-1 (loss limit) too aggressive? If >15% of trades were blocked by cooldown, try raising the limit from 3 to 4, or shortening cooldown from 24h to 12h.
3. Is EMA100 too restrictive? If trade count dropped >20% vs baseline, the EMA100 gate may be filtering good trades. Try removing it and compare.
4. Check the R:R ratio — if avg win dropped (smaller than $91.89) while avg loss stayed the same, M15 might be causing earlier entries that get worse fills.

### Outcome D: PF < 0.95 (Worse Than Baseline)
**Something regressed.** Likely causes:
1. **EMA100 gate is too restrictive** — blocking trades that would have won. This is the most likely culprit since it's the most aggressive new filter. Try removing it first.
2. **M15 is boosting bad signals over the consensus threshold** — borderline signals that H4+H1 would have rejected are now passing because M15 gave +0.15 confidence. Check if trades that had M15 boost > 0.10 have lower WR than trades with boost = 0.0.
3. **R-2 (half risk) is reducing winners more than losers** — if borderline ADX trades actually had decent WR, halving their size reduces total profit more than it reduces total loss.
4. **Bug in M15 candle fetching** — wrong candles, misaligned timestamps, or insufficient data causing the boost calculation to produce incorrect values.

To isolate: run the backtest with ONLY the Session 5 filters active (disable M15, R-1, R-2, EMA100). If that matches the Session 5 baseline, the regression is in the new code. Then re-enable one feature at a time.

---

## Step 5: Record Everything

Update `19_SESSION6_RESULTS.md` with:
1. All table data filled in
2. The diagnosis section explaining what worked and what didn't
3. A clear "next action" — either paper trading (Outcome A), targeted tuning (B/C), or regression fix (D)
4. If any new bugs were found, document them

Also update `18_SESSION6_REPORT.md`'s pending backtest row with the actual results.

---

## Rules

1. **Run the backtest before analyzing anything.** No guessing at results.
2. **Compare to Session 5's 730-day numbers**, not 180-day. The 730-day period is the honest measure.
3. **If diagnostic logging isn't already in the backtest, add it before running.** You need per-trade regime, exit reason, and M15 boost data. Without it, you can't diagnose.
4. **Don't change any code between running and analyzing.** Record the results of what's currently implemented.
5. **If BT-1 shows regression, isolate by disabling new features one at a time** rather than guessing which one caused it.
6. **The M15 boost analysis is critical.** If M15-boosted trades don't win at a higher rate than non-boosted trades, M15 is adding complexity without value. Remove it.
7. **Update both `19_SESSION6_RESULTS.md` and `18_SESSION6_REPORT.md`** with final numbers.

**Begin now. Create `19_SESSION6_RESULTS.md`, run the 730-day backtest, then fill in all tables and diagnose.**
