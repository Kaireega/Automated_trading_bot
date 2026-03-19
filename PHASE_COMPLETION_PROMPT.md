# PROMPT: Strategy Reset + Complete Phase 2 & Phase 3 — Full Path to Profitability

## Who You Are

You are a **Senior Forex Systems Engineer** completing a trading bot that is architecturally sound but misconfigured. You understand that profitable forex trading on small accounts requires correct trade math (R:R, win rate, position sizing), not more indicators. You also understand that built-but-disconnected safety components (risk managers, execution engines) exist for good reasons and should be wired in before live trading.

---

## Context — The Full Picture

**Read these files in order:**
1. `08_trading_bot_handoff_report.md` — original architecture, design intent, Phase 2/3/4 plan
2. `17_SESSION6_TRACKER.md` — latest backtest results (BT-1: 475 trades, PF 0.97, -8.88%)
3. `18_SESSION6_REPORT.md` — Session 6 changes, M15 integration details
4. `15_SESSION5_REPORT.md` — filter analysis, what works and what doesn't
5. `DEBUG_JOURNAL.md` — original audit, architecture flow

**Current state (730-day BT-1):**
| Metric | Value |
|--------|-------|
| Trades | 475 |
| Win Rate | 39.6% |
| Profit Factor | 0.97 |
| Return | -8.88% |
| Max Drawdown | 29.04% |

**What's working:** GBP_USD is profitable (PF 1.04, +$401). All code bugs are fixed. Regime gating, EMA filter, ADX gate, hour blocks — all functional.

**What's broken:** R:R structure (4×ATR TP almost never hit), USD_JPY losing money, M15 boost adding too many trades, three built components sitting disconnected.

**The handoff report's original targets:**
- Win rate: 45–55%
- R:R: 1.5:1 minimum
- Monthly return: 3–6%
- Max drawdown: 10%

**The handoff report's phased plan (partially completed):**
- Phase 1 (core fixes): ✅ Done across Sessions 1–6
- Phase 2 (safety layer): ❌ Not started
- Phase 3 (wire disconnected components): ❌ Not started
- Phase 4 (ML filter): ❌ Not started (and shouldn't start until Phase 2–3 are done)

---

## Step 0: Create Your Tracker

Create `PHASE_COMPLETION_TRACKER.md` in the project root:

```markdown
# Phase 2 & 3 Completion Tracker
> Fixing R:R, completing safety layer, wiring disconnected components.
> Started: [date/time]
> Baseline: 475 trades, 39.6% WR, PF 0.97, -8.88% (730d)
> GBP_USD proof of concept: PF 1.04, +$401

## Phase 1B: Strategy Fundamentals (R:R Fix)
| # | Description | Status |
|---|-------------|--------|
| F-1 | Reduce TP from 4×ATR to 2.5×ATR globally | ⬜ |
| F-2 | Drop USD_JPY — trade EUR_USD + GBP_USD only | ⬜ |
| F-3 | Reduce M15 boost cap from 0.20 to 0.10 | ⬜ |
| F-4 | Verify trailing stop doesn't conflict with new TP | ⬜ |

## Phase 2: Safety Layer
| # | Description | File | Status |
|---|-------------|------|--------|
| S-1 | Wire news/fundamental analyzer as trade blocker | fundamental_analyzer.py + main.py | ⬜ |
| S-2 | Wire trailing stop updater for live positions | position_manager.py | ⬜ |
| S-3 | Set pre_trade_cooldown_seconds: 30 | trading_config.yaml | ⬜ |
| S-4 | Replace print() calls with logger.debug() | notification_layer.py | ⬜ |

## Phase 3: Wire Disconnected Components
| # | Description | File | Status |
|---|-------------|------|--------|
| W-1 | Wire AdvancedRiskManager to actually gate trades | main.py + advanced_risk_manager.py | ⬜ |
| W-2 | Wire PortfolioRiskManager for correlation checks | main.py + portfolio_risk_manager.py | ⬜ |
| W-3 | Wire trade journal to MongoDB | position_manager.py | ⬜ |

## Backtest Comparisons
| Run | Changes | Trades | WR | PF | Return | DD |
|-----|---------|--------|----|----|--------|-----|
| BT-1 (Session 6) | Current | 475 | 39.6% | 0.97 | -8.88% | 29.04% |
| BT-2 | + F-1/F-2/F-3/F-4 (R:R fix) | — | — | — | — | — |
| BT-3 | + Phase 2 + Phase 3 | — | — | — | — | — |
```

---

# PHASE 1B: FIX THE TRADE MATH

These changes have the highest impact. Do them first, backtest, then proceed to Phase 2/3.

---

## F-1: Reduce Take Profit from 4×ATR to 2.5×ATR

### Why This Is the #1 Problem

The handoff report specifies **1.5:1 R:R minimum**. Current config: SL = 2×ATR, TP = 4×ATR = 2:1 R:R on paper. But in practice:
- H4 ATR ≈ 33 pips → TP = 132 pips
- Trailing stop activates at 80 pips, trails at 50 pips
- A trade that goes +90 pips then pulls back 50 → stopped at +40, never reaches 132
- USD_JPY hit TP only 15.7% of the time (30/191 trades)

At 2.5×ATR: TP = 82 pips. This is reachable within 1–3 H4 candles in a trending market. With 2×ATR SL (66 pips), R:R = 1.25:1. Combined with the trailing stop catching runners at +80 to +130 pips, effective R:R will average ~1.5:1.

### How To Change

**File:** `src/trading_bot/src/config/trading_config.yaml`

```bash
grep -rn "take_profit.*atr\|tp.*atr\|atr.*4\|4.*atr" src/trading_bot/src/config/trading_config.yaml
grep -rn "take_profit.*atr\|tp.*atr\|atr.*4" src/trading_bot/src/strategies/
grep -rn "take_profit.*atr\|tp.*atr\|atr.*4" src/trading_bot/src/ai/technical_analysis_layer.py
```

Change from 4× to 2.5× everywhere it appears — config AND any strategy files that hardcode it:

```yaml
# Config:
take_profit_atr_multiplier: 2.5    # was 4.0
stop_loss_atr_multiplier: 2.0      # keep
```

Also check each strategy file — the debug journal documented a pattern of strategies hardcoding ATR multipliers:
```bash
grep -rn "4.*atr\|atr.*4\|tp_mult\|take_profit_mult" src/trading_bot/src/strategies/
```

Replace every instance of `4 * atr` or `4.0 * atr` with config-driven value or `2.5 * atr`.

### Breakeven Math With New R:R

```
SL = 2.0 × 33 = 66 pips
TP = 2.5 × 33 = 82 pips
R:R = 82/66 = 1.24:1

Breakeven WR = 1 / (1 + R:R) = 1 / (1 + 1.24) = 44.6%
Current WR: 39.6% (need +5% improvement)

BUT: trailing stop catches winners between 80–130 pips
Effective avg win will be higher → effective R:R ~1.5:1
Breakeven at 1.5:1 R:R = 40.0%
Current WR: 39.6% → only 0.4% below breakeven
```

With more TP hits (82 pips is reachable vs 132 which isn't), WR should jump well above 40%.

---

## F-2: Drop USD_JPY

### Why

From BT-1 per-pair results:
- USD_JPY: 191 trades, 45% WR, PF 0.92, **-$752.94**, 160 SL hits vs 30 TP hits
- GBP_USD: 151 trades, 37.1% WR, PF 1.04, **+$401.10**
- EUR_USD: 133 trades, 34.6% WR, PF 0.93, -$535.87

USD_JPY is a mean-reverting pair on H4. The bot runs trend-following strategies. Running a trend strategy on a mean-reverting instrument is burning money. The 160 SL hits vs 30 TP hits confirms price reverts before reaching TP.

### How To Change

**File:** `src/trading_bot/src/config/trading_config.yaml`

```yaml
trading:
  pairs:
    - EUR_USD
    - GBP_USD
    # - USD_JPY    # DISABLED — mean-reverting, trend strategy doesn't fit
```

**Don't delete USD_JPY code or data fetching** — just remove it from the active pairs list. You may want it back later with different strategy parameters.

### Impact Expectation

Removing USD_JPY's -$752.94 loss immediately shifts the 730-day return from -$888 to roughly -$135 (EUR+GBP only). Combined with the TP fix, this should push positive.

---

## F-3: Reduce M15 Boost Cap

### Why

M15 boost at 0.20 max pushed trade count from 298 to 475 (+59%). More trades during the 2024 adverse market = more losses. Cap at 0.10 to be more selective.

### How To Change

**File:** `src/trading_bot/src/ai/technical_analysis_layer.py`

Find `_calculate_m15_confidence_boost()` and change the cap:

```python
return min(boost, 0.10)  # was 0.20
```

Also reduce individual component boosts proportionally:
```python
# EMA alignment: +0.04 (was +0.08)
# RSI room: +0.03 (was +0.06)  
# Momentum: +0.03 (was +0.06)
# Max: 0.10
```

---

## F-4: Verify Trailing Stop Doesn't Conflict With New TP

With TP at 82 pips and trailing stop activating at 80 pips:
- A trade that reaches +82 pips hits TP → closed at TP ✅
- A trade that reaches +81 pips, pulls back → trailing activates at 80, trails at 50 pips behind → stopped at +31 pips
- This is correct behavior — the trailing stop protects profit on trades that get close to TP but don't quite reach it

**Check that the TP order fires BEFORE the trailing stop evaluation.** If the trailing stop is checked first, a trade at +82 might get trailing-stopped at +32 instead of TP'd at +82.

```bash
grep -n "take_profit\|trailing\|tp_hit\|sl_hit" src/trading_bot/src/backtesting/backtest_engine.py | head -30
```

In the position update logic, TP should be checked FIRST:
```python
# Correct order:
if hit_take_profit:     # check first
    close_at_tp()
elif hit_stop_loss:     # check second
    close_at_sl()
elif trailing_triggered:  # check third
    close_at_trail()
```

### After F-1 through F-4: Run BT-2

Run the 730-day backtest with only the R:R and pair changes. Record results before moving to Phase 2/3. This isolates the trade math impact.

---

# PHASE 2: SAFETY LAYER

The handoff report specifies these for paper trading readiness. They don't affect backtest results but are required before going live.

---

## S-1: Wire News/Fundamental Analyzer as Trade Blocker

**Files:** `src/trading_bot/src/core/fundamental_analyzer.py` + `src/trading_bot/main.py`

The handoff report says: "News gatekeeper scraping exists but never blocks trades."

### Step 1: Check what the fundamental analyzer currently does

```bash
grep -n "class FundamentalAnalyzer\|def analyze\|def get_upcoming\|def should_block\|def is_news" src/trading_bot/src/core/fundamental_analyzer.py
```

Read the class. It likely has methods to check for upcoming high-impact news events but they're never called from the main trading loop.

### Step 2: Wire it into the trading loop

In `main.py`, in `_enhanced_trading_loop()`, add a news check BEFORE generating signals:

```python
# Before signal generation for each pair:
if self.fundamental_analyzer:
    news_block = await self.fundamental_analyzer.should_block_trading(pair)
    if news_block:
        self.logger.info(f"{pair}: Blocked — high-impact news event within window")
        continue
```

### Step 3: Implement the block window

If `should_block_trading()` doesn't exist, create it:

```python
async def should_block_trading(self, pair: str) -> bool:
    """Block trading 30 minutes before and 30 minutes after high-impact news."""
    upcoming = self.get_upcoming_events(pair)
    now = datetime.utcnow()
    
    for event in upcoming:
        event_time = event.get('time')
        impact = event.get('impact', 'low')
        
        if impact in ('high', 'medium'):
            minutes_until = (event_time - now).total_seconds() / 60
            if -30 <= minutes_until <= 30:  # 30 min before to 30 min after
                return True
    
    return False
```

**Note:** If the fundamental analyzer uses external APIs (economic calendar), it may not work in backtest mode. That's fine — this is a live-only safety feature. Add a guard:

```python
if self.is_backtesting:
    return False  # skip news check in backtest
```

---

## S-2: Wire Trailing Stop Updater for Live Positions

**File:** `src/trading_bot/src/core/position_manager.py`

The handoff report says: "Trailing stop in config but no live updater in position_manager." The backtest has trailing stop logic, but the live position manager doesn't send trailing stop updates to OANDA.

### Step 1: Check current state

```bash
grep -n "trailing\|trail\|modify_trade\|update_stop" src/trading_bot/src/core/position_manager.py
```

### Step 2: Add a trailing stop update loop

The position monitoring loop (which runs every 30 minutes in swing mode) should check each open position and update stops:

```python
async def _update_trailing_stops(self):
    """Check open positions and move stop losses to lock in profit."""
    for trade_id, position in self.active_positions.items():
        try:
            # Get current price from OANDA
            current_price = await self._get_current_price(position['pair'])
            if not current_price:
                continue
            
            entry_price = position['entry_price']
            direction = position['direction']
            current_stop = position.get('stop_loss', 0)
            
            # Calculate profit in pips
            pip_size = 0.01 if 'JPY' in position['pair'] else 0.0001
            
            if direction == 'buy':
                profit_pips = (current_price - entry_price) / pip_size
                new_stop = current_price - (self.trail_distance_pips * pip_size)
            else:  # sell
                profit_pips = (entry_price - current_price) / pip_size
                new_stop = current_price + (self.trail_distance_pips * pip_size)
            
            # Only trail if profit exceeds activation threshold
            if profit_pips < self.trail_activation_pips:
                continue
            
            # Only move stop in favorable direction
            if direction == 'buy' and new_stop > current_stop:
                await self.oanda_api.modify_trade(trade_id, stop_loss=new_stop)
                position['stop_loss'] = new_stop
                self.logger.info(f"Trailing stop moved: {position['pair']} → SL={new_stop:.5f} (+{profit_pips:.0f} pips profit)")
            elif direction == 'sell' and (current_stop == 0 or new_stop < current_stop):
                await self.oanda_api.modify_trade(trade_id, stop_loss=new_stop)
                position['stop_loss'] = new_stop
                self.logger.info(f"Trailing stop moved: {position['pair']} → SL={new_stop:.5f} (+{profit_pips:.0f} pips profit)")
                
        except Exception as e:
            self.logger.error(f"Trailing stop update failed for {trade_id}: {e}")
```

Call this from the position monitoring loop:
```python
async def _monitor_positions(self):
    while True:
        await self._update_trailing_stops()
        await asyncio.sleep(1800)  # every 30 minutes
```

---

## S-3: Pre-Trade Cooldown

**File:** `src/trading_bot/src/config/trading_config.yaml`

```yaml
trading:
  pre_trade_cooldown_seconds: 30    # was 0 — prevents rapid-fire entries
```

Verify the cooldown is actually enforced in `position_manager.py` or `main.py`:
```bash
grep -rn "cooldown\|pre_trade_cool" src/trading_bot/
```

If not enforced, add a timestamp check:
```python
if (datetime.utcnow() - self.last_trade_time).total_seconds() < self.pre_trade_cooldown:
    return None  # too soon after last trade
```

---

## S-4: Replace print() With logger.debug()

```bash
grep -rn "print(" src/trading_bot/src/notifications/notification_layer.py | wc -l
```

Replace all `print()` calls with `self.logger.debug()` or `self.logger.info()` depending on importance. This cleans up console noise during live trading.

---

# PHASE 3: WIRE DISCONNECTED COMPONENTS

These are fully built and tested in isolation. They need to be connected to the main trading flow.

---

## W-1: Wire AdvancedRiskManager to Actually Gate Trades

**Files:** `src/trading_bot/src/core/advanced_risk_manager.py` + `src/trading_bot/main.py`

The handoff report says: "`assess_trade_risk()` is called but its `approved` flag is only used sometimes — the approval path has a logic gap."

### Step 1: Read the current wiring

```bash
grep -n "assess_trade_risk\|risk_manager\|approved" src/trading_bot/main.py
grep -n "assess_trade_risk\|approved" src/trading_bot/src/core/advanced_risk_manager.py
```

### Step 2: Ensure the approval flag is enforced

In `main.py`, after calling `assess_trade_risk()`, the code must check `approved` and reject if False:

```python
risk_result = await self.risk_manager.assess_trade_risk(recommendation, market_context)

if not risk_result.approved:
    self.logger.info(f"{pair}: Trade rejected by risk manager — {risk_result.reason}")
    continue  # DO NOT execute trade

# Only reach here if risk approved
await self.position_manager.execute_trade(decision)
```

**Check what `assess_trade_risk` actually evaluates:**
- Max risk threshold (already fixed in Session 1, Fix 2)
- Kelly Criterion sizing (if implemented)
- Portfolio heat (total exposure across all open positions)
- Consecutive loss protection (may overlap with R-1 from Session 6)

### Step 3: Verify it doesn't double-block

The backtest already has its own risk checks (R-1 consecutive loss, R-2 ADX scaling). The AdvancedRiskManager is for LIVE trading. Make sure they don't conflict:

```python
# In the live trading path:
# AdvancedRiskManager gates → then PositionManager executes
# R-1 and R-2 are already in the backtest path

# For consistency, consider having the AdvancedRiskManager perform 
# the same checks as R-1/R-2, replacing the backtest-only implementations
```

---

## W-2: Wire PortfolioRiskManager for Correlation Checks

**Files:** `src/trading_bot/src/core/portfolio_risk_manager.py` + `src/trading_bot/main.py`

### Step 1: Read what it does

```bash
grep -n "class PortfolioRiskManager\|def check\|def assess\|def calculate_var\|def get_correlation" src/trading_bot/src/core/portfolio_risk_manager.py
```

### Step 2: Wire it as a pre-trade check

Before opening a new position, check if it would create excessive correlated risk:

```python
# In main.py, before execute_trade:
if self.portfolio_risk_manager:
    portfolio_check = await self.portfolio_risk_manager.assess_new_trade(
        pair=pair,
        direction=recommendation.direction,
        size=position_size,
        open_positions=self.position_manager.active_positions
    )
    if not portfolio_check.approved:
        self.logger.info(f"{pair}: Blocked by portfolio risk — {portfolio_check.reason}")
        continue
```

**Key check:** EUR_USD and GBP_USD are highly correlated (~0.85). If you're long EUR_USD and get a long GBP_USD signal, the portfolio manager should either block it or reduce position size. Two full-size correlated positions doubles your effective exposure.

### Step 3: If the method doesn't exist, create a simple version

```python
async def assess_new_trade(self, pair, direction, size, open_positions):
    """Check if new trade would create excessive correlated exposure."""
    
    # Correlation matrix for major pairs
    CORRELATIONS = {
        ('EUR_USD', 'GBP_USD'): 0.85,
        ('EUR_USD', 'USD_JPY'): -0.60,
        ('GBP_USD', 'USD_JPY'): -0.50,
    }
    
    for trade_id, pos in open_positions.items():
        existing_pair = pos['pair']
        if existing_pair == pair:
            continue  # same pair check is handled elsewhere
        
        corr_key = tuple(sorted([pair, existing_pair]))
        correlation = CORRELATIONS.get(corr_key, 0)
        
        # Block if same direction on highly correlated pairs
        if abs(correlation) > 0.7 and pos['direction'] == direction and correlation > 0:
            return RiskResult(approved=False, reason=f"High correlation ({correlation:.2f}) with open {existing_pair} position")
        
        # Block if opposite direction on negatively correlated pairs
        if correlation < -0.7 and pos['direction'] != direction:
            return RiskResult(approved=False, reason=f"Negative correlation ({correlation:.2f}) with open {existing_pair} — effectively same exposure")
    
    return RiskResult(approved=True)
```

**Note:** With only EUR_USD and GBP_USD active (after dropping USD_JPY), this mainly prevents being long both simultaneously — which is the biggest risk for a small account since a USD strengthening event would hit both positions.

---

## W-3: Wire Trade Journal to MongoDB

**File:** `src/trading_bot/src/core/position_manager.py`

The handoff report says: "MongoDB is connected but `execute_trade()` never writes trade data."

### Step 1: Find the MongoDB connection

```bash
grep -rn "mongo\|MongoDB\|pymongo\|motor" src/trading_bot/
```

### Step 2: Add trade recording after execution

```python
async def execute_trade(self, decision):
    # ... existing execution code ...
    
    result = await self.oanda_api.create_order(order_params)
    
    if result and result.get('trade_id'):
        # Record to MongoDB
        await self._record_trade_to_journal({
            'trade_id': result['trade_id'],
            'pair': decision.pair,
            'direction': decision.direction,
            'entry_price': result.get('price'),
            'stop_loss': decision.stop_loss,
            'take_profit': decision.take_profit,
            'units': decision.units,
            'regime': decision.metadata.get('regime', 'unknown'),
            'strategies_agreed': decision.metadata.get('strategies', []),
            'confidence': decision.confidence,
            'adx_value': decision.metadata.get('adx_value'),
            'timestamp': datetime.utcnow(),
            'status': 'open'
        })
    
    return result

async def _record_trade_to_journal(self, trade_data):
    """Write trade to MongoDB for performance tracking."""
    try:
        if self.db:
            await self.db.trades.insert_one(trade_data)
            self.logger.info(f"Trade recorded: {trade_data['pair']} {trade_data['direction']}")
    except Exception as e:
        self.logger.error(f"Failed to record trade: {e}")
        # Don't let journal failure block trading
```

Also add a close record when positions are closed:
```python
async def _on_trade_closed(self, trade_id, exit_price, pnl, exit_reason):
    try:
        if self.db:
            await self.db.trades.update_one(
                {'trade_id': trade_id},
                {'$set': {
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'exit_reason': exit_reason,
                    'close_time': datetime.utcnow(),
                    'status': 'closed'
                }}
            )
    except Exception as e:
        self.logger.error(f"Failed to update trade journal: {e}")
```

**This is critical for Phase 4 (ML filter)** — the ML model needs historical trade data with outcomes. Without the journal, you can't train it.

---

# EXECUTION ORDER

```
1. F-1: Change TP from 4×ATR to 2.5×ATR
2. F-2: Remove USD_JPY from active pairs
3. F-3: Reduce M15 boost cap to 0.10
4. F-4: Verify TP fires before trailing stop in evaluation order
5. → Run BT-2 (730-day) → record results
6. S-1: Wire news blocker (live only)
7. S-2: Wire trailing stop updater (live only)
8. S-3: Set pre_trade_cooldown: 30
9. S-4: Replace print() with logger
10. W-1: Wire AdvancedRiskManager gating
11. W-2: Wire PortfolioRiskManager correlation check
12. W-3: Wire MongoDB trade journal
13. → Run BT-3 (730-day) if W-1/W-2 affect backtest path → record results
14. → If BT-2 shows PF > 1.0: move to paper trading with Phase 2+3 active
```

**Run BT-2 after F-1 through F-4** to isolate the R:R impact. Phase 2 and 3 mostly affect live trading, not backtest, but W-1 (AdvancedRiskManager) may have a backtest component.

---

## What Success Looks Like

| Metric | BT-1 (Current) | BT-2 Target | Why |
|--------|----------------|-------------|-----|
| Trades (730d) | 475 | 200–300 | Fewer (no USD_JPY, less M15 noise) |
| Win Rate | 39.6% | 45–52% | More TP hits at 82 pips vs 132 |
| Profit Factor | 0.97 | 1.15–1.40 | Better R:R + fewer losing trades |
| Return | -8.88% | +5% to +15% | Positive expectancy × 200–300 trades |
| Max Drawdown | 29.04% | 12–20% | No USD_JPY bleed, fewer trades |
| Avg Win | varies | ~$50–80 | 82-pip TP on appropriate sizing |
| Avg Loss | varies | ~$35–55 | 66-pip SL on appropriate sizing |

**The key math:**
```
At 48% WR and 1.5:1 R:R:
Expectancy = (0.48 × $75) - (0.52 × $50) = $36.00 - $26.00 = +$10/trade
250 trades × $10 = +$2,500 on a 730-day period
$2,500 / starting balance = significant positive return
```

---

## Rules

1. **F-1 (TP reduction) is the highest-impact change.** Do it first.
2. **Update `PHASE_COMPLETION_TRACKER.md` after every change.**
3. **Run BT-2 after Phase 1B (F-1 through F-4) before starting Phase 2/3.** You need to know if the trade math fix works before adding more layers.
4. **Phase 2 items (S-1 through S-4) are live-trading safety features.** They won't change backtest results but are required before paper trading.
5. **Phase 3 items (W-1 through W-3) add risk management and tracking.** W-1 may affect backtest if the AdvancedRiskManager is also used in the backtest path. Check before running BT-3.
6. **Don't start Phase 4 (ML filter) until you have 300+ trades in the MongoDB journal.** ML needs training data.
7. **If BT-2 shows PF > 1.05 and positive return: that's your green light for paper trading** with all Phase 2/3 features active.
8. **If BT-2 still shows PF < 1.0:** The problem is deeper than R:R. Check per-regime win rates — if TRENDING regimes lose money, the trend detection itself may be miscalibrated. If RANGING regimes lose money, mean reversion strategies may need disabling.
9. **GBP_USD is your proof of concept.** If GBP_USD stays profitable in BT-2 and EUR_USD improves with the TP fix, you're on track.
10. **Keep it simple.** The handoff report's Section 13 says it clearly: "1–2 trades per day maximum, 45–55% win rate, 1.5:1 R:R." That's the target. Not more indicators. Not more complexity.

**Begin now. Read `08_trading_bot_handoff_report.md`, create `PHASE_COMPLETION_TRACKER.md`, then start with F-1.**
