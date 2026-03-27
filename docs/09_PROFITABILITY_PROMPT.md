# PROMPT: Regime Gating + Trade Management Fixes — Push Past Profitability

## Who You Are

You are a **Senior Quantitative Developer** building a swing trading system. You understand that strategy selection is more important than strategy tuning — running the right strategy in the wrong market regime is the fastest way to lose money. You also understand that entries are only half the trade; exit management (trailing stops, profit targets, premature closes) determines whether winners pay for losers.

---

## Context

This Forex swing trading bot has been through:
1. Full audit → 40 issues found (`DEBUG_JOURNAL.md`)
2. 25 fixes applied and verified (`FIX_TRACKER.md`, `VERIFICATION_LOG.md`)
3. V-issues fixed + swing conversion (`SWING_CONVERSION_TRACKER.md`)

**Current state after clean 90-day backtest:**
- 12 trades, 41.7% win rate, profit factor 0.87, return -4.01%, max drawdown 13.91%
- V-1 (inverted stops) and V-2 (nano-lot sizing) are fixed
- Swing config is in place (H1/H4/D1, 1hr polling, 2 max open trades)
- Three additional backtest bugs fixed (B-1, B-2, B-3)

**Why it's losing money (diagnosed in SWING_CONVERSION_TRACKER.md):**
1. **No regime gating** — mean reversion strategies fire during trends, trend strategies fire during chop. The `MarketCondition` enum is incomplete and not wired into strategy selection.
2. **Premature 5% unrealized profit auto-close** — `_should_close_position` kills winners at 5% unrealized gain before they reach take profit.
3. **Trailing stop too tight** — 1.5x ATR trail is closing swing trades on normal H4 noise before TP is reached. Realized R:R is ~1.2:1 instead of target 2:1.

**Read these files first:**
1. `SWING_CONVERSION_TRACKER.md` — current state, P-1 through P-6 priorities
2. `DEBUG_JOURNAL.md` — architecture, data flow, original issues
3. `FIX_TRACKER.md` — 25 fixes already applied (don't break these)

---

## Step 0: Create Your Tracker

Create `PROFITABILITY_TRACKER.md` in the project root:

```markdown
# Profitability Tracker
> Implementing regime gating + trade management fixes.
> Started: [date/time]
> Last updated: [date/time]

## Fixes Planned
| # | Priority | Description | Status | Verified? |
|---|----------|-------------|--------|-----------|
| P-1 | Critical | Add missing MarketCondition enum members | ⬜ | ⬜ |
| P-2 | Critical | Wire regime-based strategy eligibility gate | ⬜ | ⬜ |
| P-3 | Critical | Pass regime through full call chain | ⬜ | ⬜ |
| P-4 | High | Remove premature 5% profit auto-close | ⬜ | ⬜ |
| P-5 | High | Widen trailing stop for swing timeframe | ⬜ | ⬜ |

## Backtest Comparisons
| Metric | Before (no regime) | After P-1/P-2/P-3 | After P-4/P-5 | Final |
|--------|-------------------|--------------------|----|-------|
| Trades (90d) | 12 | — | — | — |
| Win Rate | 41.7% | — | — | — |
| Profit Factor | 0.87 | — | — | — |
| Avg Win | $25.85 | — | — | — |
| Avg Loss | $21.33 | — | — | — |
| Avg R:R realized | ~1.2:1 | — | — | — |
| Max Drawdown | 13.91% | — | — | — |
| Return | -4.01% | — | — | — |

## Investigation Log
[Updated as you work]

## New Issues Found
| # | Severity | File | Description |
|---|----------|------|-------------|
```

---

# P-1: Complete the MarketCondition Enum

## What's Wrong

The `MarketCondition` enum (likely in `src/trading_bot/src/core/models.py`) is missing members that the regime detector and strategy gating need. The data_layer's `_determine_market_condition()` was already updated (Fix 13) to detect real conditions, but references like `TRENDING_UP`, `TRENDING_DOWN`, `VOLATILE`, and `CONSOLIDATION` either don't exist in the enum or map to the wrong values.

## What To Do

**Step 1:** Read the current `MarketCondition` enum:
```bash
grep -n "class MarketCondition" src/trading_bot/src/core/models.py
grep -A 20 "class MarketCondition" src/trading_bot/src/core/models.py
```

**Step 2:** Read what values the regime detector and data layer actually return:
```bash
grep -rn "MarketCondition\." src/trading_bot/src/data/data_layer.py
grep -rn "MarketCondition\." src/trading_bot/src/core/market_regime_detector.py
grep -rn "MarketCondition\." src/trading_bot/src/backtesting/backtest_engine.py
```

**Step 3:** Add missing members. The enum should include at minimum:

```python
class MarketCondition(Enum):
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    CONSOLIDATION = "consolidation"    # tight range, low volatility
    BREAKOUT = "breakout"
    VOLATILE = "volatile"              # high ATR, no clear direction
    REVERSAL = "reversal"
    UNKNOWN = "unknown"
```

**Step 4:** Verify every file that references `MarketCondition` uses only members that exist in the enum:
```bash
grep -rn "MarketCondition\." src/trading_bot/
```

Every `MarketCondition.X` must correspond to a member in the enum. If any don't, either add the member or fix the reference.

---

# P-2: Wire Regime-Based Strategy Eligibility Gate

## What's Wrong

Currently `strategy_manager.py`'s `generate_consensus_signal()` runs ALL enabled strategies regardless of market condition. This means:
- BB_Bounce and RSI_Extremes (mean reversion) fire during strong trends → get stopped out
- EMA_Crossover and ADX_Trend (trend following) fire during chop → whipsaw losses
- ATR_Breakout fires during low-volatility consolidation → false breakouts

## What To Do

**Step 1:** Define which strategies are eligible for which regimes. Add this mapping to config or as a constant:

```yaml
# In trading_config.yaml:
regime_strategy_map:
  trending_up:
    - EMA_Crossover_H4
    - ADX_Trend_H4
    - MACD_Momentum_H4
    - Fast_Ichimoku_D1
    - Donchian_Break_H4
  trending_down:
    - EMA_Crossover_H4
    - ADX_Trend_H4
    - MACD_Momentum_H4
    - Fast_Ichimoku_D1
    - Donchian_Break_H4
  ranging:
    - BB_Bounce_H4
    - RSI_Extremes_H4
    - Support_Resistance_H4
  consolidation:
    - BB_Bounce_H4
    - RSI_Extremes_H4
    - Support_Resistance_H4
  breakout:
    - ATR_Breakout_H4
    - Donchian_Break_H4
    - Support_Resistance_H4
  volatile:
    - ATR_Breakout_H4
    - RSI_Extremes_H4          # for catching oversold/overbought extremes
  reversal:
    - RSI_Extremes_H4
    - BB_Bounce_H4
    - Support_Resistance_H4
  unknown:
    []                          # don't trade if we can't identify the regime
```

**Step 2:** In `strategy_manager.py`, modify `generate_consensus_signal()` to filter strategies by regime BEFORE running them:

```python
async def generate_consensus_signal(self, pair, candles_by_tf, market_context, ...):
    # Get current market regime
    regime = market_context.condition if market_context else MarketCondition.UNKNOWN
    
    # Get eligible strategies for this regime
    eligible_strategy_names = self._get_eligible_strategies(regime)
    
    if not eligible_strategy_names:
        self.logger.info(f"{pair}: No strategies eligible for regime {regime.value}")
        return None
    
    # Filter active strategies to only eligible ones
    strategies_to_run = [
        s for s in self.active_strategies
        if s.name in eligible_strategy_names  # check how strategy name is stored
    ]
    
    self.logger.info(f"{pair}: Regime={regime.value}, eligible={len(strategies_to_run)}/{len(self.active_strategies)}")
    
    # Run only eligible strategies
    # ... rest of existing consensus logic, but only on strategies_to_run
```

**Step 3:** Implement `_get_eligible_strategies()`:

```python
def _get_eligible_strategies(self, regime: MarketCondition) -> list:
    """Return strategy names eligible for the current market regime."""
    # Read from config
    regime_map = getattr(self.config, 'regime_strategy_map', None)
    
    if regime_map is None:
        # Fallback: hardcoded default map
        regime_map = {
            MarketCondition.TRENDING_UP: ['EMA_Crossover_H4', 'ADX_Trend_H4', 'MACD_Momentum_H4', 'Fast_Ichimoku_D1', 'Donchian_Break_H4'],
            MarketCondition.TRENDING_DOWN: ['EMA_Crossover_H4', 'ADX_Trend_H4', 'MACD_Momentum_H4', 'Fast_Ichimoku_D1', 'Donchian_Break_H4'],
            MarketCondition.RANGING: ['BB_Bounce_H4', 'RSI_Extremes_H4', 'Support_Resistance_H4'],
            MarketCondition.CONSOLIDATION: ['BB_Bounce_H4', 'RSI_Extremes_H4', 'Support_Resistance_H4'],
            MarketCondition.BREAKOUT: ['ATR_Breakout_H4', 'Donchian_Break_H4', 'Support_Resistance_H4'],
            MarketCondition.VOLATILE: ['ATR_Breakout_H4', 'RSI_Extremes_H4'],
            MarketCondition.REVERSAL: ['RSI_Extremes_H4', 'BB_Bounce_H4', 'Support_Resistance_H4'],
            MarketCondition.UNKNOWN: [],
        }
    
    return regime_map.get(regime, [])
```

**CRITICAL:** Check how strategy names are stored and referenced. The debug journal noted names like `BB_Bounce_M5` with timeframe suffixes. After the swing conversion, are they now `BB_Bounce_H4`? The names in the regime map MUST exactly match the registered strategy names. Run this check:

```bash
# Find all registered strategy names
grep -rn "@register_strategy\|registry.register\|strategy_name\|self.name" src/trading_bot/src/strategies/
```

---

# P-3: Pass Regime Through the Full Call Chain

## What's Wrong

The market condition is detected somewhere (data_layer or backtest_engine), but it may not reach `strategy_manager.generate_consensus_signal()`. The debug journal's architecture diagram shows the data flow — trace it and make sure `market_context` (with its `.condition` field) arrives at the strategy manager.

## What To Do

**Step 1:** Trace the call chain in the backtest path:
```
backtest_engine._run_simulation()
  → calls TechnicalAnalysisLayer.analyze_multiple_timeframes(pair, candles_by_tf, ???)
    → calls StrategyManager.generate_consensus_signal(pair, candles_by_tf, ???)
```

Check: does `market_context` get passed at each step? Or does it get lost?

```bash
# Check what analyze_multiple_timeframes receives and passes through
grep -n "analyze_multiple_timeframes\|generate_consensus_signal" src/trading_bot/src/ai/technical_analysis_layer.py
grep -n "generate_consensus_signal" src/trading_bot/src/strategies/strategy_manager.py
```

**Step 2:** Trace the call chain in the live trading path:
```
main.py → _enhanced_trading_loop()
  → DataLayer.get_market_context() → returns market_context
  → TechnicalAnalysisLayer.analyze_multiple_timeframes(pair, candles, market_context?)
    → StrategyManager.generate_consensus_signal(pair, candles, market_context?)
```

**Step 3:** If `market_context` is not being passed, add it as a parameter at each level. Follow the existing function signatures and add `market_context` where missing:

```python
# In technical_analysis_layer.py:
async def analyze_multiple_timeframes(self, pair, candles_by_tf, market_context=None, ...):
    # ... existing code ...
    signal = await self.strategy_manager.generate_consensus_signal(
        pair, candles_by_tf, market_context=market_context, ...
    )
```

**Step 4:** In the backtest engine, make sure the market context created by `_create_market_context()` is passed into the analysis call:

```python
# In backtest_engine._run_simulation():
market_context = self._create_market_context(pair, candles)
# ... then this must reach strategy_manager:
result = await self.technical_analysis.analyze_multiple_timeframes(
    pair, candles_by_tf, market_context=market_context, ...
)
```

### Verification for P-1/P-2/P-3

After all three are done, run the backtest and check:

1. **Log output should show regime detection:**
   ```
   EUR_USD: Regime=trending_up, eligible=5/9
   GBP_USD: Regime=ranging, eligible=3/9
   ```
   If you see `Regime=unknown` for everything, P-3 is broken (context not reaching strategy manager).
   If you see `eligible=9/9` for everything, P-2 is broken (gate not filtering).

2. **Different strategies should fire in different regimes.** If BB_Bounce fires during a strong trend, the gate isn't working.

3. **Trade count may change** — could go up (more targeted signals) or down (unknown regime = no trade). Both are fine as long as win rate improves.

4. **Run the 90-day backtest and record metrics** in the tracker before moving to P-4/P-5.

---

# P-4: Remove Premature 5% Unrealized Profit Auto-Close

## What's Wrong

`position_manager.py` has a `_should_close_position()` method (or similar) that closes trades when unrealized profit hits 5%. For swing trades targeting 100–500 pips, this kills winners at ~30–50 pips — roughly 1.2:1 R:R instead of the 2:1 or 3:1 the strategy intended. The take-profit order should handle exits, not an arbitrary percentage cap.

## How To Find It

```bash
grep -rn "unrealized.*profit\|profit.*close\|should_close\|auto_close\|5.*percent\|0\.05" src/trading_bot/src/core/position_manager.py
grep -rn "_should_close" src/trading_bot/src/core/position_manager.py
```

Also check the backtest engine — it may have its own version:
```bash
grep -rn "unrealized.*profit\|auto_close\|should_close\|5.*percent\|0\.05" src/trading_bot/src/backtesting/backtest_engine.py
```

## How To Fix

**Option A (recommended): Remove the auto-close entirely.** Let take-profit and trailing stop handle exits. The risk is already defined by the stop loss.

```python
# If _should_close_position checks unrealized profit:
# DELETE or DISABLE the unrealized profit close condition
# Keep: max hold time close, trailing stop close, stop loss close
# Remove: unrealized profit percentage close
```

**Option B: If you want to keep a profit protection mechanism**, replace the 5% blanket close with a configurable trailing take-profit:

```yaml
# In config:
trade_management:
  # Don't auto-close at fixed profit %
  auto_close_profit_pct: null    # disabled
  
  # Instead, let trailing stop protect profits
  trailing_stop:
    enabled: true
    activation_pips: 80          # start trailing after 80 pips profit
    trail_distance_pips: 40      # trail 40 pips behind
```

**IMPORTANT:** Make this change in BOTH the live position manager AND the backtest engine if the backtest has its own exit logic.

---

# P-5: Widen Trailing Stop for Swing Timeframe

## What's Wrong

The trailing stop is set to 1.5x ATR. On H4 candles, ATR might be 60–100 pips. A 1.5x trail = 90–150 pips is actually reasonable for swing — BUT the activation distance matters too. If the trail activates after only 20 pips of profit, it's going to get clipped by normal H4 noise before the trade has room to develop.

## How To Investigate

```bash
grep -rn "trailing\|trail_distance\|trail_activation\|atr.*mult\|atr.*trail" src/trading_bot/src/core/position_manager.py
grep -rn "trailing\|trail_distance\|trail_activation" src/trading_bot/src/config/trading_config.yaml
grep -rn "trailing\|trail" src/trading_bot/src/backtesting/backtest_engine.py
```

Check:
1. **When does the trail activate?** (after how many pips of profit)
2. **How wide is the trail?** (fixed pips, ATR multiple, or percentage)
3. **Is the trail in the backtest engine too?** (it must match live behavior)

## How To Fix

Set trailing stop parameters appropriate for H4 swing trading:

```yaml
trailing_stop:
  enabled: true
  # Don't start trailing until the trade has enough room
  activation_pips: 80            # start trailing after 80 pips unrealized profit
  # OR activation_atr_multiple: 1.5  # start after 1.5x ATR profit
  
  # Trail distance — must be wider than normal H4 candle range
  trail_distance_pips: 50        # trail 50 pips behind best price
  # OR trail_atr_multiple: 1.0   # trail 1x ATR behind (60-100 pips on H4)
  
  # Step size — don't update on every tick, update on candle close
  update_on_candle_close: true   # for swing: adjust trail only on H4 close
```

**The key insight:** For swing trades, the trailing stop should:
- **Not activate too early** — let the trade develop. 80+ pips minimum.
- **Not trail too tight** — H4 candles can easily move 40–60 pips. Trail must be wider than typical candle range.
- **Update on candle close, not on every price tick** — intraday noise shouldn't move the trail.

If the current implementation trails on every tick or has a very tight activation, that explains why the realized R:R is only 1.2:1.

### Verification for P-4/P-5

After both are done, run the 90-day backtest and check:

1. **Average winning trade size should increase.** If winners were previously capped at ~$25, they should now be $40–$100+ (depending on account size and position sizing).
2. **Realized R:R should improve.** Target: average win / average loss > 1.5, ideally 2.0+.
3. **Some trades should reach their take-profit.** If zero trades hit TP, the trailing stop is still too tight or there's another early-exit condition.
4. **Win rate may drop slightly.** This is fine — wider trails mean some trades that previously locked in small profits will now reverse to a loss. But the bigger winners should more than compensate.

---

## Execution Order

```
1. P-1: Complete MarketCondition enum
2. P-3: Wire regime through call chain (do this before P-2 so the data is flowing)
3. P-2: Implement regime-based strategy gate
4. → Run 90-day backtest → record metrics in tracker
5. P-4: Remove 5% auto-close
6. P-5: Widen trailing stop
7. → Run 90-day backtest → record metrics in tracker
8. → Compare all three states (before, after regime, after exit fixes)
```

**Why this order:** P-1/P-2/P-3 are tightly coupled and address the biggest issue (wrong strategies in wrong regimes). Run a backtest after that group to isolate the impact. P-4/P-5 address exit management and should be measured separately so you know which changes drove which improvements.

---

## What Success Looks Like

| Metric | Current | After Regime (P-1/2/3) | After Exits (P-4/5) | Target |
|--------|---------|----------------------|---------------------|--------|
| Trades (90d) | 12 | 10–25 | 10–25 | 15–30 |
| Win Rate | 41.7% | 48–58% | 45–55% | >50% |
| Profit Factor | 0.87 | 1.1–1.5 | 1.3–2.5 | >1.3 |
| Avg Win / Avg Loss | 1.21 | 1.3–1.5 | 1.8–2.5 | >1.5 |
| Max Drawdown | 13.91% | <12% | <10% | <10% |
| Return (90d) | -4.01% | ~0% to +5% | +5% to +15% | Positive |

**Key expectations:**
- Regime gating (P-1/2/3) should improve **win rate** the most — right strategy + right market = fewer losers.
- Exit management (P-4/5) should improve **avg win size** the most — let winners run = bigger R:R.
- Trade count may decrease — that's fine. Fewer, higher-quality trades is the goal for swing on a small account.
- If profit factor is still below 1.0 after all five fixes, the strategies themselves may need parameter tuning or the regime detection may be misclassifying conditions. In that case, add logging to show regime + strategy + outcome for each trade to diagnose.

---

## Rules

1. **Update `PROFITABILITY_TRACKER.md` after every change.**
2. **Run a backtest after P-1/P-2/P-3 as a group, then after P-4/P-5 as a group.** Two checkpoints, not five.
3. **Check strategy name matching carefully.** The regime map strategy names MUST exactly match registered names. A typo means a strategy never gets selected. This was a recurring issue in the original audit.
4. **Don't break the 25 existing fixes or the swing conversion.** If unsure, grep for the fix before modifying a function.
5. **If regime detection shows `UNKNOWN` for >50% of candles**, the detection logic in `data_layer.py` or `backtest_engine._create_market_context()` needs tuning — thresholds may be too tight. ADX > 25 for trending is standard; if H4 ADX rarely exceeds 25, try 20.
6. **If trade count drops to <5 over 90 days after regime gating**, the gate is too restrictive. Either loosen `min_strategies_agreeing` to 1, or widen which strategies are eligible per regime.
7. **Log regime + strategy + direction + outcome for every trade.** This is the diagnostic data you need to tune further.

**Begin now. Read `SWING_CONVERSION_TRACKER.md`, create `PROFITABILITY_TRACKER.md`, then start with P-1.**
