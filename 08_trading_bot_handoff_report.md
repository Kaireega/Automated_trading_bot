# Forex Trading Bot — Full Technical Handoff Report
**Purpose:** Complete context document for a new Claude session in VS Code to continue coding work.  
**Project:** Automated forex trading bot targeting OANDA practice → FTMO prop firm path  
**Repo location (local machine):** `/Users/ree/Documents/GitHub/notification bot/Automated_trading_bot/`  
**Repo location (reference copy):** `/home/claude/repo/Automated_trading_bot-main/`

---

## 1. THE GOAL

Build a fully automated forex trading bot that generates consistent monthly income.

**Path:**
1. OANDA practice account (paper trading) — prove profitability over 60+ trades
2. FTMO Challenge ($167 entry fee) → $25,000 funded account
3. Scale to 3 funded accounts ($100K total)
4. Target: $2,000–$5,000/month realistic at that scale

**Realistic return expectations:**
- Annual: 18–35% after losing months, commissions, slippage
- $10,000 account: ~$200–500/month average
- FTMO $25K funded at 80% split: ~$417/month
- 3 funded accounts ($100K): $2,000–5,000/month

---

## 2. ARCHITECTURE OVERVIEW

The bot is a **15-strategy intraday ensemble system** on M5/M15 timeframes. Every component is already written. The problem is configuration and wiring, not missing code.

### Component Map

```
main.py                          ← Main orchestrator (TradingBot class)
src/trading_bot/
├── config/
│   └── trading_config.yaml      ← THE most important file — controls all behavior
├── src/
│   ├── ai/
│   │   ├── technical_analysis_layer.py   ← Calls strategy_manager
│   │   ├── multi_timeframe_analyzer.py   ← M5/M15 weighting
│   │   ├── technical_analyzer.py         ← Calculates indicators
│   │   └── order_flow_analyzer.py        ← Order flow signals
│   ├── strategies/
│   │   ├── strategy_manager.py           ← CONSENSUS VOTING — key file
│   │   ├── strategy_base.py              ← BaseStrategy class
│   │   ├── strategy_registry.py          ← @StrategyRegistry.register decorator
│   │   ├── session_based/
│   │   │   ├── london_open_break.py      ← PRIMARY EDGE STRATEGY
│   │   │   └── ny_open_momentum.py       ← PRIMARY EDGE STRATEGY
│   │   ├── trend_momentum/
│   │   │   ├── adx_trend.py              ← GOOD — uses real trend filter
│   │   │   ├── macd_momentum.py          ← GOOD as confirming filter
│   │   │   ├── ema_crossover.py          ← BROKEN — overtrades noise
│   │   │   └── fast_ichimoku.py          ← BROKEN — index bug
│   │   ├── mean_reversion/
│   │   │   ├── bollinger_bounce.py       ← OK as confirming filter
│   │   │   ├── rsi_extremes.py           ← OK as confirming filter
│   │   │   └── stochastic_reversal.py    ← Weak
│   │   ├── breakout/
│   │   │   ├── atr_breakout.py           ← OK
│   │   │   ├── support_resistance.py     ← OK
│   │   │   └── donchian_break.py         ← Weak
│   │   └── scalping/
│   │       ├── price_action_scalp.py     ← DISABLE — negative EV at spread cost
│   │       ├── spread_squeeze.py         ← DISABLE
│   │       └── order_flow_momentum.py    ← DISABLE
│   ├── core/
│   │   ├── market_regime_detector.py     ← BUILT, PARTIALLY CONNECTED
│   │   ├── position_manager.py           ← Handles OANDA trade execution
│   │   ├── advanced_risk_manager.py      ← Kelly Criterion, drawdown — BUILT, DISCONNECTED
│   │   ├── portfolio_risk_manager.py     ← VaR, CVaR — BUILT, DISCONNECTED
│   │   ├── smart_execution_engine.py     ← TWAP/VWAP — BUILT, DISCONNECTED
│   │   ├── fundamental_analyzer.py       ← News/economic calendar
│   │   ├── fx_position_sizing.py         ← Correct pip-based sizing
│   │   └── models.py                     ← All dataclasses and enums
│   ├── decision/
│   │   ├── technical_decision_layer.py   ← Final trade decision gating
│   │   ├── risk_manager.py               ← Basic risk checks
│   │   └── performance_tracker.py        ← Trade recording
│   ├── data/
│   │   └── data_layer.py                 ← OANDA data fetching
│   ├── backtesting/
│   │   ├── backtest_engine.py            ← Backtest orchestrator (fixed)
│   │   └── feeds_oanda.py                ← OandaHistoricalFeed class
│   ├── notifications/
│   │   └── notification_layer.py         ← Telegram + email alerts
│   └── utils/
│       ├── config.py                     ← Config parser/dataclasses
│       └── logger.py                     ← Logging setup
run.py                            ← CLI entry: validate / live / backtest
```

### Key External Files
```
api/oanda_api.py                  ← OANDA REST API wrapper
infrastructure/instrument_collection.py  ← FX instrument metadata
src/constants/defs.py             ← Credential loader (CRITICAL — see Section 5)
.env                              ← Real credentials (KEEP)
config.env                        ← Placeholder credentials (DELETE THIS)
```

---

## 3. CREDENTIAL LOADING — CRITICAL BLOCKER

**The bot cannot authenticate until this is fixed.**

`src/constants/defs.py` loads credential files in this order:
```python
possible_paths = [
    'config.env',   # ← Found first, has PLACEHOLDER values → MUST DELETE
    '.env',         # ← Has REAL credentials, never reached while config.env exists
]
```

**Real credentials are in `.env`:**
```
OANDA_API_KEY=c7050cbd...
OANDA_ACCOUNT_ID=101-001-23541205-001
OANDA_URL=https://api-fxpractice.oanda.com/v3
```

**Fix (run once on local machine):**
```bash
rm "/Users/ree/Documents/GitHub/notification bot/Automated_trading_bot/config.env"
```

---

## 4. CURRENT STATE — WHAT WORKS VS WHAT'S BROKEN

### ✅ Already Fixed (All Sessions)
| Fix | File | Status |
|-----|------|--------|
| JPY position sizing (was 30x too large) | fx_position_sizing.py | ✅ Done |
| EMA crossover state-based detection | ema_crossover.py | ✅ Done |
| Bollinger Bounce wick-based touch | bollinger_bounce.py | ✅ Done |
| Consensus threshold lowered to 0.30 | strategy_manager.py | ✅ Done |
| Ichimoku cloud index fix | fast_ichimoku.py | ✅ Done |
| London Open entry window + JPY pip divisor | london_open_break.py | ✅ Done |
| YAML parse error (`simulation: true` → `simulation:`) | trading_config.yaml | ✅ Done |
| 5 dead strategies removed from `__init__.py` | strategies/__init__.py | ✅ Done |
| run.py `result.starting_balance` → `result.initial_balance` | run.py | ✅ Done |
| run.py `result.ending_balance` → `result.final_balance` | run.py | ✅ Done |
| `data_source: db` → `data_source: oanda` in config | trading_config.yaml | ✅ Done |
| Backtest engine OANDA feed wiring | backtest_engine.py | ✅ Done |
| RSI thresholds corrected (30/70) | trading_config.yaml | ✅ Done |

### ✅ Validation Passes
```
python3 run.py validate

✅ Strategies registered: 10
   - ADX_Trend_M5, ATR_Breakout, BB_Bounce_M5, Fast_EMA_Cross_M5
   - London_Open_Break, MACD_Momentum_M5, NY_Open_Momentum
   - Price_Action_Scalp, RSI_Extremes, Support_Resistance_Break
✅ Multi-Strategy: ENABLED
✅ Total allocation: 100%
```

### ❌ Still Broken / Not Yet Done
| Problem | File | Impact |
|---------|------|--------|
| `config.env` exists and blocks real credentials | defs.py loading order | Bot cannot trade |
| `min_strategies_agreeing: 2` — too low, noise passes as signal | trading_config.yaml | False signals every loop |
| Scalping strategies enabled — negative EV at spread cost | trading_config.yaml | Loses money |
| EMA crossover fires 4+ times/day on M5 noise | trading_config.yaml | Loses money |
| Regime detector does NOT gate which strategies vote | strategy_manager.py | Wrong strategies in wrong markets |
| Position manager closes at 5% unrealized profit | position_manager.py | Kills trades too early |
| Force close at 16:30 UTC | trading_config.yaml | Kills session trades prematurely |
| SmartExecutionEngine not wired into live flow | main.py | Not used |
| PortfolioRiskManager not wired into live flow | main.py | Not used |
| AdvancedRiskManager called but not actually gating trades | main.py | Risk checks not enforced |
| No trade journal — MongoDB connected but no trades recorded | position_manager.py | Cannot track performance |
| News gatekeeper scraping exists but never blocks trades | fundamental_analyzer.py | Trades during news events |
| Trailing stop in config but no live updater in position_manager | position_manager.py | Trailing stops not moving |

---

## 5. THE CORE PROBLEM — WHY IT DOESN'T MAKE MONEY YET

**Diagnosis from code review and simulated backtest:**

The 15-strategy consensus vote was designed to require genuine confluence. Instead it has these fatal flaws:

**Flaw 1: `min_strategies_agreeing: 2` out of 15**  
On M5 with 15 indicators running simultaneously, 2 will almost always randomly align. This is not signal — it's noise. Raising this to 4–5 is the single most important change.

**Flaw 2: No regime-based strategy gating**  
The `MarketRegimeDetector` detects 7 regimes (`TRENDING_UP`, `TRENDING_DOWN`, `RANGING`, `VOLATILE`, `BREAKOUT`, `CONSOLIDATION`, `REVERSAL`). But in `strategy_manager.py`, ALL 15 strategies vote in ALL market conditions.

The `is_applicable()` method in `strategy_base.py` DOES check `market_condition.value in self.conditions`, but there is a mismatch:
- The regime detector produces regime strings like `"TRENDING_UP"`, `"RANGING"`, etc.
- The `MarketCondition` enum (in `models.py`) only has: `"news_reactionary"`, `"reversal"`, `"breakout"`, `"ranging"`, `"unknown"`
- There is no `"trending"` or `"volatile"` in the enum

This means strategies configured with `conditions: ["TRENDING_UP", "TRENDING_DOWN"]` will NEVER match a `MarketCondition` because those strings don't exist in the enum. Every strategy with non-`ALL` conditions silently passes through `is_applicable()` or falls through to returning `None`. The regime gating is effectively dead.

**Flaw 3: Scalping strategies have negative EV**  
At 1.2 pip spread on EUR/USD, a scalp targeting 5–10 pips gives up 12–24% of the target to spread alone. With slippage included, these strategies cannot be profitable on M5.

**Flaw 4: Force close at 16:30 UTC kills session trades**  
London Open Break entries are valid through 16:00 UTC. Force closing at 16:30 gives only 30 minutes for the trade to develop. Real London Open trades need 2–4 hours.

---

## 6. THE FIVE FIXES — IN EXACT ORDER

### Fix 1: Delete config.env (Blocking — do this first)
```bash
rm "/Users/ree/Documents/GitHub/notification bot/Automated_trading_bot/config.env"
```

### Fix 2: Rewrite trading_config.yaml — Strategy Allocation and Thresholds

**File:** `src/trading_bot/config/trading_config.yaml`

Change these specific values:

```yaml
# CHANGE: Raise consensus bar
strategy_portfolio:
  selection:
    min_strategies_agreeing: 4      # Was 2 — 4 out of 9 active strategies

# CHANGE: Extend hold time, push force close to end of NY session
trading:
  hold_time_settings:
    max_hold_time_minutes: 480      # Was 240 — allow 8-hour holds
    force_close_time: "21:00"       # Was 16:30 — let NY session run fully
    market_condition_hold_times:
      breakout: [90, 480]
      reversal: [60, 480]

# CHANGE: Strategy allocations (must sum to 100)
# DISABLE these by setting allocation to 0 (or remove from list):
#   - Fast_EMA_Cross_M5     (overtrades M5 noise)
#   - Price_Action_Scalp    (negative EV at spread)
#   - Spread_Squeeze        (negative EV at spread)
#   - Order_Flow_Momentum   (negative EV at spread)
#   - Fast_Ichimoku         (index bug, unreliable)
#   - Donchian_Break        (weak signal on M5)

# KEEP with new allocations:
strategies:
  - name: "London_Open_Break"
    allocation: 22          # Was 5 — primary edge, anchor strategy

  - name: "NY_Open_Momentum"
    allocation: 22          # Was 5 — primary edge, anchor strategy

  - name: "ADX_Trend_M5"
    allocation: 18          # Was 7 — required trend confirmation
    parameters:
      threshold: 25         # Was 20 — require stronger trend signal

  - name: "MACD_Momentum_M5"
    allocation: 13          # Was 8 — confirming filter

  - name: "BB_Bounce_M5"
    allocation: 10          # Was 19 — mean reversion only in RANGING
    conditions: ["RANGING", "ranging"]

  - name: "RSI_Extremes"
    allocation: 8           # Was 8 — confirming filter
    parameters:
      oversold: 30          # Correct level
      overbought: 70        # Correct level

  - name: "ATR_Breakout"
    allocation: 7           # Was 7 — breakout confirmation

  - name: "Support_Resistance_Break"
    allocation: 0           # Disabled for now

  # All scalping strategies: allocation 0 or removed entirely
```

### Fix 3: Wire Regime Gating in strategy_manager.py

**File:** `src/trading_bot/src/strategies/strategy_manager.py`

**The problem:** `MarketCondition` enum values don't match the regime detector's output strings, so `is_applicable()` never correctly matches conditions like `TRENDING_UP`.

**The fix:** In `generate_consensus_signal()`, add a regime-aware eligibility filter. Replace the loop that collects signals with this version:

```python
async def generate_consensus_signal(
    self,
    pair: str,
    candles: List[CandleData],
    indicators: TechnicalIndicators,
    market_condition: MarketCondition,
    current_time: Optional[datetime] = None,
    regime: Optional[str] = None          # ADD THIS PARAMETER
) -> Optional[TradeRecommendation]:
    
    if not self.enabled or not self.strategies:
        return None

    # --- REGIME-BASED ELIGIBILITY GATE ---
    # Map regime detector output to which strategy types are valid
    REGIME_ALLOWED_TYPES = {
        'TRENDING_UP':     ['trend_momentum', 'session_based', 'breakout'],
        'TRENDING_DOWN':   ['trend_momentum', 'session_based', 'breakout'],
        'RANGING':         ['mean_reversion'],
        'VOLATILE':        ['breakout', 'session_based'],
        'BREAKOUT':        ['breakout', 'session_based', 'trend_momentum'],
        'CONSOLIDATION':   ['mean_reversion'],
        'REVERSAL':        ['mean_reversion', 'trend_momentum'],
        None:              ['trend_momentum', 'session_based', 'breakout', 'mean_reversion'],
        'UNKNOWN':         ['trend_momentum', 'session_based', 'breakout', 'mean_reversion'],
    }
    
    current_regime = regime or 'UNKNOWN'
    allowed_types = REGIME_ALLOWED_TYPES.get(current_regime, REGIME_ALLOWED_TYPES[None])
    
    eligible_strategies = [
        s for s in self.strategies
        if s.allocation > 0 and s.strategy_type in allowed_types
    ]
    
    self.logger.debug(
        f"Regime: {current_regime} | Eligible strategies: "
        f"{[s.name for s in eligible_strategies]}"
    )
    # --- END REGIME GATE ---

    strategy_signals: List[Dict[str, Any]] = []
    
    for strategy in eligible_strategies:   # ← Was self.strategies
        try:
            if not strategy.is_active_now(current_time):
                continue

            signal = await strategy.generate_signal(
                candles=candles,
                indicators=indicators,
                market_condition=market_condition,
                current_time=current_time
            )

            if signal and strategy.validate_signal(signal):
                strategy_signals.append({
                    'strategy_name': strategy.name,
                    'strategy_type': strategy.strategy_type,
                    'allocation': strategy.allocation,
                    'signal': signal
                })
                self.strategy_performance[strategy.name]['signals_generated'] += 1

        except Exception as e:
            self.logger.error(f"❌ Error in strategy {strategy.name}: {e}")

    if len(strategy_signals) < self.min_strategies_agreeing:
        self.logger.debug(
            f"Insufficient consensus: {len(strategy_signals)}/{self.min_strategies_agreeing}"
        )
        return None

    if self.selection_mode == 'weighted_ensemble':
        return self._calculate_weighted_consensus(pair, strategy_signals)
    elif self.selection_mode == 'best_fit':
        return self._select_best_fit(pair, strategy_signals)
    elif self.selection_mode == 'democratic':
        return self._democratic_vote(pair, strategy_signals)
    
    return None
```

**Also update the caller in `technical_analysis_layer.py`** to pass the regime from `market_regime_detector`:
```python
# Find the call to generate_consensus_signal and pass regime:
consensus = await self.strategy_manager.generate_consensus_signal(
    pair=pair,
    candles=candles,
    indicators=indicators,
    market_condition=market_condition,
    current_time=current_time,
    regime=regime_analysis.get('regime', 'UNKNOWN')   # ← ADD THIS
)
```

### Fix 4: Remove Premature Position Close in position_manager.py

**File:** `src/trading_bot/src/core/position_manager.py`

Find the `_should_close_position` method (~line 214). Remove the block that auto-closes at 5% unrealized profit:

```python
async def _should_close_position(self, existing_position, decision, market_context):
    """Determine if existing position should be closed before opening new one."""
    try:
        current_units = existing_position['units']
        new_signal = decision.recommendation.signal.value
        is_long = current_units > 0

        # Close only if new signal is opposite direction
        if (is_long and new_signal == 'sell') or (not is_long and new_signal == 'buy'):
            self.logger.info("New signal opposite to existing — closing")
            return True

        # DELETE THESE LINES — they kill trades too early:
        # unrealized_pl = existing_position.get('unrealized_pl', 0)
        # if unrealized_pl > 0:
        #     account_summary = self.oanda_api.get_account_summary()
        #     if account_summary:
        #         balance = float(account_summary.get('balance', 10000))
        #         profit_pct = unrealized_pl / balance
        #         if profit_pct > 0.05:   # ← DELETE THIS ENTIRE BLOCK
        #             return True

        return False
    except Exception as e:
        self.logger.error(f"Error in should_close_position: {e}")
        return False
```

### Fix 5: Run Backtest on Real OANDA Data

After fixes 1–4 are deployed:

```bash
cd "/Users/ree/Documents/GitHub/notification bot/Automated_trading_bot"
python3 run.py backtest --days 30 --pairs EUR_USD 2>&1 | tee backtest_output.txt
```

**What to look for in the output:**
- Trades generated > 0 (confirms OANDA data is flowing)
- Win rate > 40% (minimum for 1.5:1 R:R to be profitable)
- Profit factor > 1.2 (total wins / total losses)
- Monthly breakdown shows more green than red months

---

## 7. WHAT EACH STRATEGY ACTUALLY DOES

### Primary Edge Strategies (Keep, high allocation)

**London_Open_Break** — `session_based/london_open_break.py`
- Range window: 08:00–09:00 UTC (first hour of London session)
- Entry: Price breaks above range high (BUY) or below range low (SELL) after 09:00
- Stop: Other side of the range
- Target: Range distance projected from breakout point
- Active window: 08:00–16:00 UTC
- Minimum range: 10 pips (configurable)
- Why it works: Institutional orders cluster at session open levels. Real breakouts above/below the first hour's range reflect genuine directional commitment.

**NY_Open_Momentum** — `session_based/ny_open_momentum.py`
- Entry window: 13:00–13:30 UTC (first 30 minutes of NY session)
- Signal: 8+ pip directional momentum from session open
- Stop: Session open ± ATR
- Target: 2× the momentum move
- Volume confirmation: Volume spike gives +0.05 confidence
- Why it works: NY open is the highest volume session overlap. Momentum in the first 30 minutes reflects institutional positioning for the day.

**ADX_Trend_M5** — `trend_momentum/adx_trend.py`
- Signal: ADX > 25 (trend strength) AND +DI > -DI (direction) AND EMA fast/slow alignment
- Stop: 2× ATR
- Target: 3× ATR
- Why it works: ADX confirms a genuine trend is in place before entering. It prevents trading in ranging conditions when trend strategies have no edge.

### Confirming Filters (Keep, medium allocation)

**MACD_Momentum_M5** — `trend_momentum/macd_momentum.py`
- Fires when MACD is above signal line AND histogram is positive AND RSI < 70
- Works as a trend direction confirmer, not as a primary signal source

**BB_Bounce_M5** — `mean_reversion/bollinger_bounce.py`
- Fires when price touches the outer Bollinger Band with a wick rejection
- Only valid in RANGING regime
- Should NOT fire in trending markets

**RSI_Extremes** — `mean_reversion/rsi_extremes.py`
- Fires at RSI < 35 (oversold) or RSI > 65 (overbought) — uses tighter thresholds than config
- Only valid in RANGING regime

### Disable Immediately

**Fast_EMA_Cross_M5** — Fires 4+ times per day on M5 noise. 22% win rate in backtesting. Every month is a losing month. Must be set to allocation 0.

**Price_Action_Scalp, Spread_Squeeze, Order_Flow_Momentum** — Scalping on M5 with 1.2 pip spread. At a 5–10 pip target, spread alone consumes 12–24% of the potential gain before slippage. Negative EV by construction.

**Fast_Ichimoku** — Has a known array index bug in `fast_ichimoku.py`. Unreliable signals. Set allocation to 0 until fixed.

**Donchian_Break** — Weak signal on M5. Insufficient lookback on 5-minute data.

---

## 8. COMPONENTS BUILT BUT NOT YET CONNECTED

These three components are fully implemented and tested in isolation, but are not wired into the live trading flow in `main.py`. After the five core fixes are done and the backtest confirms positive expectancy, wire these in:

**SmartExecutionEngine** — `src/core/smart_execution_engine.py`
- Implements TWAP (Time-Weighted Average Price) order slicing
- Implements VWAP-based entry timing
- Implements iceberg orders for large position sizes
- Currently: completely unused — all trades execute as market orders at current price

**PortfolioRiskManager** — `src/core/portfolio_risk_manager.py`
- Calculates VaR (Value at Risk) at 95% and 99% confidence
- Calculates CVaR / Expected Shortfall
- Runs Monte Carlo portfolio simulations
- Tracks correlation between open positions
- Currently: completely unused

**AdvancedRiskManager** — `src/core/advanced_risk_manager.py`
- Kelly Criterion position sizing (currently sizing is flat percentage)
- Portfolio heat management (max aggregate exposure)
- Consecutive loss protection (halves size after N losses)
- Currently: `assess_trade_risk()` is called but its `approved` flag is only used sometimes — the approval path has a logic gap

---

## 9. KNOWN BUGS NOT YET FIXED

| Bug | Location | Description |
|-----|----------|-------------|
| `simulation: true` YAML parse | trading_config.yaml | Fixed in working copy but may revert if config is regenerated |
| Ichimoku index | fast_ichimoku.py | Cloud array indexing causes IndexError under certain candle counts |
| MACD "crossover" detection | macd_momentum.py | Uses only current bar, not previous — cannot detect actual crossover, only current state |
| Trailing stop | position_manager.py | Config says `trailing_stop: true` but no live position updater moves the stop |
| Pre-trade cooldown | trading_config.yaml | `pre_trade_cooldown_seconds: 0` — should be 30 for real money |
| ~20 raw `print()` calls | notification_layer.py | Should be `logger.debug()` — creates console noise |
| MongoDB no trade recording | position_manager.py | MongoDB is connected but `execute_trade()` never writes trade data |
| Manual approval race condition | notification_layer.py | `manual_trade_approval: true` has a timing gap where market can move before user approves |

---

## 10. MARKET CONDITION / REGIME MISMATCH (Important)

This is the root cause of the regime gating being broken.

`models.py` defines `MarketCondition` enum with these values:
```python
class MarketCondition(Enum):
    NEWS_REACTIONARY = "news_reactionary"
    REVERSAL = "reversal"
    BREAKOUT = "breakout"
    RANGING = "ranging"
    UNKNOWN = "unknown"
```

`market_regime_detector.py` detects these regimes:
```python
self.regimes = {
    'TRENDING_UP', 'TRENDING_DOWN', 'RANGING',
    'VOLATILE', 'BREAKOUT', 'CONSOLIDATION', 'REVERSAL'
}
```

`trading_config.yaml` strategy conditions reference:
```yaml
conditions: ["TRENDING_UP", "TRENDING_DOWN"]   # Not in MarketCondition enum
conditions: ["RANGING"]                         # "ranging" IS in enum (lowercase)
conditions: ["BREAKOUT"]                        # "breakout" IS in enum (lowercase)
```

**The fix (two options):**

Option A — Expand the `MarketCondition` enum in `models.py` to include all regime strings:
```python
class MarketCondition(Enum):
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    RANGING = "RANGING"
    VOLATILE = "VOLATILE"
    BREAKOUT = "BREAKOUT"
    CONSOLIDATION = "CONSOLIDATION"
    REVERSAL = "REVERSAL"
    NEWS_REACTIONARY = "NEWS_REACTIONARY"
    UNKNOWN = "UNKNOWN"
```

Option B — Use the regime parameter approach in Fix 3 above (passing regime as a separate string, bypassing the enum mismatch entirely). This is the lower-risk option.

---

## 11. STARTUP COMMANDS

```bash
# Validate configuration (no credentials needed)
python3 run.py validate

# Run 30-day backtest on EUR/USD
python3 run.py backtest --days 30 --pairs EUR_USD 2>&1 | tee backtest_output.txt

# Run live paper trading (markets must be open)
python3 run.py live
```

---

## 12. AFTER THE BACKTEST — NEXT PHASE PLAN

Once the backtest confirms positive expectancy (profit factor > 1.2, win rate > 40%):

**Phase 2 — Safety Layer (2 weeks paper trading)**
- Connect `fundamental_analyzer.py` news scraping as a hard trade blocker (currently scrapes but never gates)
- Add trailing stop updater in `position_manager.py` — loop that checks open positions and moves stop to lock in profit
- Set `pre_trade_cooldown_seconds: 30`
- Replace `print()` calls in `notification_layer.py` with `logger.debug()`

**Phase 3 — Robustness (after 300 paper trades)**
- Wire `SmartExecutionEngine` into `main.py` for all trade execution
- Wire `PortfolioRiskManager` for live correlation and VaR checks
- Ensure `AdvancedRiskManager.assess_trade_risk()` result actually gates trades
- Build trade journal: write every executed trade to MongoDB

**Phase 4 — ML Signal Filter (after 500 paper trades)**
- Train scikit-learn Random Forest or XGBoost on historical trade data
- Input features: indicator values at entry, regime, session, volatility
- Output: probability of trade being profitable
- Gate: only take trades with > 55% ML probability
- Retrain weekly on own trade journal data

---

## 13. REALISTIC PERFORMANCE EXPECTATIONS

**What the code can do after fixes (best case, verified through real OANDA backtest):**
- 1–2 trades per day maximum (London Open + NY Open anchors)
- Win rate target: 45–55%
- R:R ratio: 1.5:1 minimum (configured), some trades reach 2:1–3:1
- Expected monthly return: 3–6% on account size (after spread and slippage)
- Maximum drawdown budget: 10% before position sizing scales down

**What it cannot do:**
- Cannot guarantee profitability before real backtest on OANDA data confirms it
- Cannot trade without valid credentials (config.env must be deleted first)
- Cannot be evaluated on synthetic data — the synthetic data compresses volatility by 4–8× vs real EUR/USD

---

## 14. FILES NOT TO TOUCH

These files are working and should not be modified unless there is a specific reason:

- `api/oanda_api.py` — OANDA REST wrapper, working correctly
- `infrastructure/instrument_collection.py` — FX pip/precision metadata, correct
- `src/trading_bot/src/core/fx_position_sizing.py` — JPY-aware position sizing, fixed and correct
- `src/trading_bot/src/utils/config.py` — Config parser, working correctly
- `src/trading_bot/src/strategies/strategy_base.py` — BaseStrategy class, correct
- `src/trading_bot/src/strategies/strategy_registry.py` — `@StrategyRegistry.register` decorator, correct
- `src/trading_bot/src/backtesting/feeds_oanda.py` — `OandaHistoricalFeed`, working
- `.env` — Real credentials, never modify or delete

---

## 15. SUMMARY — WHAT THE NEW CLAUDE SESSION NEEDS TO DO

The five changes needed, in strict order of priority:

| Priority | Action | File | Lines Changed |
|----------|--------|------|---------------|
| 1 | Delete config.env | Terminal command | 0 lines |
| 2 | Raise min_strategies_agreeing to 4, extend hold time to 480 min, push force_close to 21:00, disable 6 losing strategies | trading_config.yaml | ~30 lines |
| 3 | Add regime-based strategy eligibility gate, add `regime` parameter to `generate_consensus_signal()` | strategy_manager.py | ~40 lines |
| 4 | Remove the 5% unrealized profit auto-close block | position_manager.py | ~8 lines deleted |
| 5 | Run backtest and analyze output | Terminal | 0 lines |

Everything else — ML, VaR, trade journal, smart execution — comes after the backtest confirms the core signal generation has positive expectancy. Don't build Phase 3 before Phase 1 works.
