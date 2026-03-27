# PROMPT: Full Strategy Overhaul — From 9-Indicator Committee to 2-Strategy Regime-Switched System

## Who You Are

You are a **Senior Quantitative Developer** rebuilding a Forex trading bot's strategy layer from the ground up. You've read the quant critique. You understand that the current system — 9 correlated indicators voting in consensus — is noise averaging, not signal detection. You're going to replace it with something that has a documented, structural edge: two clean strategies (one trend, one mean reversion), hard regime switching (not voting), D1 as the directional anchor, H4 for entry timing, and M15 for precision entry on pullbacks.

You keep things simple. Fewer moving parts. Clearer edge. Testable out-of-sample.

---

## Context — What Exists and What's Wrong

**Read these files — they are your complete history:**
1. `08_trading_bot_handoff_report.md` — original architecture, file map, component inventory
2. `19_SESSION7_REPORT.md` — latest session, current state, live blocker
3. `17_SESSION6_TRACKER.md` — Session 6 results (BT-1: 475 trades, PF 0.97)
4. `15_SESSION5_REPORT.md` — trade analysis, filter history
5. `DEBUG_JOURNAL.md` — original audit, architecture flow
6. `SWING_CONVERSION_TRACKER.md` — swing config reference

**Current system (after Session 7):**
- 730-day backtest: 284 trades, 35.9% WR, PF 1.045, +8.07%
- 9 strategies in weighted consensus voting
- H4 primary, H1 intermediate, M15 confidence boost
- Regime detection (ADX > 25 gate, EMA20/EMA100 filters)
- Pairs: EUR_USD + GBP_USD
- GBP_USD profitable (PF 1.09), EUR_USD near breakeven (PF 0.99)

**Why it needs an overhaul:**
1. 9 strategies are measuring the same thing (trend persistence via lagging indicators). When they "agree," the trend is already mature and near exhaustion
2. 35.9% WR with 1.25:1 R:R is mathematically underwater — the +8.07% return depends on trailing stop tail events, which is fragile
3. ADX > 25 as a trend gate fires when the trend is 60-70% done — entries are too late
4. Six sessions of filter additions (hour blocks, EMA100, ATR contraction, M15 boost) are curve-fitting to the 730-day sample
5. 21.43% max drawdown would fail FTMO challenge rules instantly (5% daily / 10% total max)

---

## Step 0: Create Your Tracker

Create `STRATEGY_OVERHAUL_TRACKER.md` in the project root:

```markdown
# Strategy Overhaul Tracker
> Replacing 9-indicator consensus with 2-strategy regime-switched system.
> Started: [date/time]
> Baseline: 284 trades, 35.9% WR, PF 1.045, +8.07%, DD 21.43% (730d)

## Phase 1: New Strategy Architecture
| # | Description | Status |
|---|-------------|--------|
| A-1 | Add D1 timeframe to data pipeline | ⬜ |
| A-2 | Build Daily Breakout strategy (trend regime) | ⬜ |
| A-3 | Build Structure Reversal strategy (ranging regime) | ⬜ |
| A-4 | Rebuild regime detector (replace ADX threshold with proper detection) | ⬜ |
| A-5 | Replace consensus voting with hard regime switch | ⬜ |
| A-6 | M15 pullback entry (replace confidence boost) | ⬜ |

## Phase 2: Risk & Sizing for FTMO
| # | Description | Status |
|---|-------------|--------|
| R-1 | FTMO drawdown rules in backtest (5% daily, 10% total) | ⬜ |
| R-2 | Position sizing for $10K FTMO account | ⬜ |
| R-3 | Kill switch: halt trading if 4% total drawdown reached | ⬜ |

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
| Old system | 9-strategy consensus | 284 | 35.9% | 1.045 | +8.07% | 21.43% | Baseline |
| Train (500d) | New 2-strategy | — | — | — | — | — | — |
| Test (230d) | New 2-strategy (unchanged) | — | — | — | — | — | — |
| Full (730d) | New 2-strategy | — | — | — | — | — | — |
| FTMO sim | New + FTMO rules | — | — | — | — | — | — |
```

---

# PHASE 1: NEW STRATEGY ARCHITECTURE

## The New Design

```
D1 Candle Close
    │
    ├─ Regime Detector (D1-level)
    │   ├─ TRENDING → Daily Breakout Strategy
    │   └─ RANGING  → Structure Reversal Strategy
    │
    ├─ H4 Entry Window
    │   └─ Wait for H4 candle that confirms D1 direction
    │
    └─ M15 Precision Entry
        └─ Enter on M15 pullback to 20 EMA within the H4 window
```

**Key differences from old system:**
- D1 is the directional anchor (was H4)
- Only ONE strategy runs at a time, selected by regime (was 9 voting)
- No consensus voting, no weighted confidence, no minimum_strategies_agreeing
- M15 is a pullback entry tool, not a confidence booster
- Two completely independent strategies with different logic (not 9 variations of trend measurement)

---

## A-1: Add D1 Timeframe to Data Pipeline

### Config

**File:** `src/trading_bot/src/config/trading_config.yaml`

```yaml
multi_timeframe:
  timeframes:
    - D1      # directional anchor — regime + trend direction
    - H4      # entry window — confirms D1 direction
    - M15     # precision entry — pullback to EMA
  primary_timeframe: D1
  entry_timeframe: H4
  trigger_timeframe: M15
```

### Data Layer

**File:** `src/trading_bot/src/data/data_layer.py`

Verify D1 candles can be fetched from OANDA. Check the TimeFrame enum:

```bash
grep -n "class TimeFrame\|D1\|DAILY" src/trading_bot/src/core/models.py
```

If `TimeFrame.D1` doesn't exist, add it:
```python
class TimeFrame(Enum):
    M15 = "M15"
    H1 = "H1"
    H4 = "H4"
    D1 = "D"        # OANDA uses "D" for daily
    # Check OANDA API docs for exact granularity string
```

**OANDA granularity for daily candles is `"D"` not `"D1"`** — verify this in the OANDA API wrapper:
```bash
grep -n "granularity\|D1\|daily\|DAILY" src/trading_bot/src/data/data_layer.py
grep -n "granularity\|D1\|daily" api/oanda_api.py
```

### Backtest Engine

**File:** `src/trading_bot/src/backtesting/backtest_engine.py`

Add D1 candle fetching alongside H4/H1/M15. For the backtest loop:
- Loop step: every 4 hours (H4 candle close) — this is when entry decisions are made
- D1 candle: use the last completed daily candle (updates once per day at 21:00 UTC / 17:00 EST)
- M15: fetch the recent M15 candles within the current H4 window for pullback entry

```python
# At each H4 step:
d1_candles = self._get_completed_d1_candles(pair, current_time, lookback=200)
h4_candles = self._get_completed_h4_candles(pair, current_time, lookback=200)
m15_candles = self._get_recent_m15_candles(pair, current_time, lookback=50)

candles_by_tf = {
    TimeFrame.D1: d1_candles,
    TimeFrame.H4: h4_candles,
    TimeFrame.M15: m15_candles,
}
```

---

## A-2: Build Daily Breakout Strategy (Trend Regime)

This replaces ALL trend-following strategies (EMA crossover, ADX trend, MACD momentum, ATR breakout, Donchian break). One clean strategy with a documented structural edge.

### The Edge

Prior day's high and low act as support/resistance because:
- Institutional stop orders cluster above/below prior day extremes
- When price breaks these levels, the stops trigger and create momentum in the breakout direction
- This is a well-documented pattern (Opening Range Breakout literature, Crabel 1990, Toby Crabel's "Day Trading with Short-Term Price Patterns")

### Implementation

Create a new file: `src/trading_bot/src/strategies/swing/daily_breakout.py`

```python
"""
Daily Breakout Strategy
=======================
Entry: Price breaks above yesterday's high (BUY) or below yesterday's low (SELL)
       on the H4 timeframe, confirmed by D1 trend direction.
Stop:  Below yesterday's low (BUY) or above yesterday's high (SELL)
TP:    1.5× the stop distance (R:R = 1.5:1)
Filter: D1 EMA(50) slope must agree with breakout direction

This strategy runs ONLY in TRENDING regime.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from trading_bot.src.strategies.strategy_base import BaseStrategy
from trading_bot.src.core.models import CandleData, TradeSignal, TradeRecommendation


class DailyBreakoutStrategy(BaseStrategy):
    """
    Break of prior day's high/low with trend confirmation.
    """

    def __init__(self, config=None):
        super().__init__(config)
        self.name = "Daily_Breakout"
        self.strategy_type = "trend"
        self.breakout_buffer_pips = 5   # require X pips beyond the level
        self.min_range_pips = 40        # skip if yesterday's range was < 40 pips
        self.max_range_pips = 200       # skip if yesterday's range was > 200 pips (news day)

    async def generate_signal(
        self,
        d1_candles: List[CandleData],
        h4_candles: List[CandleData],
        m15_candles: Optional[List[CandleData]] = None,
        pair: str = "",
        **kwargs
    ) -> Optional[TradeRecommendation]:
        """
        Generate a breakout signal based on prior day's high/low.
        """
        if not d1_candles or len(d1_candles) < 52:
            return None  # need 52 D1 candles for EMA(50)
        if not h4_candles or len(h4_candles) < 2:
            return None

        # Yesterday's candle (last completed D1)
        yesterday = d1_candles[-1]
        prev_high = yesterday.high
        prev_low = yesterday.low
        prev_range = prev_high - prev_low

        # Pip size
        pip_size = 0.01 if 'JPY' in pair else 0.0001
        range_pips = prev_range / pip_size

        # Filter: skip if range is too narrow (consolidation) or too wide (news spike)
        if range_pips < self.min_range_pips or range_pips > self.max_range_pips:
            return None

        # D1 EMA(50) for trend direction
        d1_closes = [c.close for c in d1_candles]
        ema_50 = self._calculate_ema(d1_closes, 50)
        if ema_50 is None:
            return None

        # D1 EMA slope (compare current EMA to 5 days ago)
        ema_50_prev = self._calculate_ema(d1_closes[:-5], 50)
        if ema_50_prev is None:
            return None
        ema_slope_up = ema_50 > ema_50_prev

        # Current price (latest H4 close)
        current_price = h4_candles[-1].close
        buffer = self.breakout_buffer_pips * pip_size

        signal = None

        # BUY: price broke above yesterday's high AND D1 EMA sloping up
        if current_price > (prev_high + buffer) and ema_slope_up:
            stop_loss = prev_low  # below yesterday's low
            stop_distance = current_price - stop_loss
            take_profit = current_price + (stop_distance * 1.5)  # 1.5:1 R:R

            signal = TradeRecommendation(
                pair=pair,
                direction="buy",
                confidence=0.70,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                metadata={
                    'strategy': self.name,
                    'regime': 'TRENDING',
                    'prev_high': float(prev_high),
                    'prev_low': float(prev_low),
                    'range_pips': range_pips,
                    'ema_50': float(ema_50),
                    'r_r_ratio': 1.5,
                }
            )

        # SELL: price broke below yesterday's low AND D1 EMA sloping down
        elif current_price < (prev_low - buffer) and not ema_slope_up:
            stop_loss = prev_high  # above yesterday's high
            stop_distance = stop_loss - current_price
            take_profit = current_price - (stop_distance * 1.5)  # 1.5:1 R:R

            signal = TradeRecommendation(
                pair=pair,
                direction="sell",
                confidence=0.70,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                metadata={
                    'strategy': self.name,
                    'regime': 'TRENDING',
                    'prev_high': float(prev_high),
                    'prev_low': float(prev_low),
                    'range_pips': range_pips,
                    'ema_50': float(ema_50),
                    'r_r_ratio': 1.5,
                }
            )

        return signal

    def _calculate_ema(self, closes: list, period: int) -> Optional[float]:
        if len(closes) < period:
            return None
        multiplier = 2 / (period + 1)
        ema = sum(closes[:period]) / period
        for price in closes[period:]:
            ema = (price - ema) * multiplier + ema
        return ema
```

### Key Design Decisions

- **Stop = other side of yesterday's range.** This is a structural level, not an arbitrary ATR multiple. The stop has meaning — if price returns to the other side of yesterday's range, the breakout failed.
- **TP = 1.5× the stop distance.** R:R of 1.5:1. At 48% win rate: expectancy = (0.48 × 1.5) - (0.52 × 1) = +0.20 per unit risked. At 45%: +0.155. Both profitable.
- **No ADX, no MACD, no RSI.** The only filter is D1 EMA(50) slope — are we in an uptrend or downtrend? That's all the trend confirmation this strategy needs.
- **Range filter prevents false breakouts** during consolidation (< 40 pips) and news spikes (> 200 pips).

---

## A-3: Build Structure Reversal Strategy (Ranging Regime)

This replaces all mean-reversion strategies (BB Bounce, RSI Extremes, Stochastic Reversal). One clean strategy.

### The Edge

When price reaches a D1 support/resistance level (defined by prior swing highs/lows), it tends to reverse — especially when momentum indicators show exhaustion. This is the most basic and enduring edge in FX because:
- These levels represent areas where large orders have historically been placed
- RSI(14) extremes at these levels indicate momentum exhaustion
- The edge persists because it's driven by market microstructure (order clustering), not by pattern recognition that gets arbitraged away

### Implementation

Create a new file: `src/trading_bot/src/strategies/swing/structure_reversal.py`

```python
"""
Structure Reversal Strategy
============================
Entry: Price touches D1 support/resistance zone AND H4 RSI(14) is extreme
       (< 30 for BUY at support, > 70 for SELL at resistance)
Stop:  Beyond the structure level by 0.5× H4 ATR
TP:    Midpoint of the D1 range (1:1 to 1.5:1 R:R typically)
Filter: Only runs in RANGING regime (detected at D1 level)

This strategy runs ONLY in RANGING regime.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from trading_bot.src.strategies.strategy_base import BaseStrategy
from trading_bot.src.core.models import CandleData, TradeRecommendation


class StructureReversalStrategy(BaseStrategy):
    """
    Mean reversion at D1 support/resistance with RSI confirmation.
    """

    def __init__(self, config=None):
        super().__init__(config)
        self.name = "Structure_Reversal"
        self.strategy_type = "mean_reversion"
        self.sr_lookback = 50          # D1 candles to find S/R levels
        self.sr_zone_pips = 15         # how close price must be to S/R level
        self.rsi_period = 14
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        self.atr_period = 14

    async def generate_signal(
        self,
        d1_candles: List[CandleData],
        h4_candles: List[CandleData],
        m15_candles: Optional[List[CandleData]] = None,
        pair: str = "",
        **kwargs
    ) -> Optional[TradeRecommendation]:
        """
        Generate a reversal signal at D1 structure levels.
        """
        if not d1_candles or len(d1_candles) < self.sr_lookback:
            return None
        if not h4_candles or len(h4_candles) < self.rsi_period + 1:
            return None

        pip_size = 0.01 if 'JPY' in pair else 0.0001
        zone_distance = self.sr_zone_pips * pip_size
        current_price = h4_candles[-1].close

        # Find D1 support and resistance levels (swing highs/lows)
        support_levels, resistance_levels = self._find_sr_levels(d1_candles)

        # Calculate H4 RSI
        h4_closes = [c.close for c in h4_candles]
        rsi = self._calculate_rsi(h4_closes, self.rsi_period)
        if rsi is None:
            return None

        # Calculate H4 ATR for stop placement
        atr = self._calculate_atr(h4_candles, self.atr_period)
        if atr is None or atr == 0:
            return None

        # Calculate range midpoint for TP target
        recent_high = max(c.high for c in d1_candles[-20:])
        recent_low = min(c.low for c in d1_candles[-20:])
        range_midpoint = (recent_high + recent_low) / 2

        # BUY: price at support + RSI oversold
        for support in support_levels:
            if abs(current_price - support) <= zone_distance and rsi < self.rsi_oversold:
                stop_loss = support - (0.5 * atr)
                take_profit = range_midpoint
                stop_distance = current_price - stop_loss
                tp_distance = take_profit - current_price

                # Only take if R:R >= 1.0
                if stop_distance > 0 and tp_distance / stop_distance >= 1.0:
                    return TradeRecommendation(
                        pair=pair,
                        direction="buy",
                        confidence=0.65,
                        entry_price=current_price,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        metadata={
                            'strategy': self.name,
                            'regime': 'RANGING',
                            'support_level': float(support),
                            'rsi': float(rsi),
                            'range_midpoint': float(range_midpoint),
                            'r_r_ratio': float(tp_distance / stop_distance),
                        }
                    )

        # SELL: price at resistance + RSI overbought
        for resistance in resistance_levels:
            if abs(current_price - resistance) <= zone_distance and rsi > self.rsi_overbought:
                stop_loss = resistance + (0.5 * atr)
                take_profit = range_midpoint
                stop_distance = stop_loss - current_price
                tp_distance = current_price - take_profit

                if stop_distance > 0 and tp_distance / stop_distance >= 1.0:
                    return TradeRecommendation(
                        pair=pair,
                        direction="sell",
                        confidence=0.65,
                        entry_price=current_price,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        metadata={
                            'strategy': self.name,
                            'regime': 'RANGING',
                            'resistance_level': float(resistance),
                            'rsi': float(rsi),
                            'range_midpoint': float(range_midpoint),
                            'r_r_ratio': float(tp_distance / stop_distance),
                        }
                    )

        return None

    def _find_sr_levels(self, candles, window=5):
        """
        Find swing highs (resistance) and swing lows (support).
        A swing high is a candle whose high is higher than the `window` candles on each side.
        A swing low is a candle whose low is lower than the `window` candles on each side.
        """
        supports = []
        resistances = []

        for i in range(window, len(candles) - window):
            # Swing high (resistance)
            is_swing_high = all(
                candles[i].high >= candles[i + j].high and
                candles[i].high >= candles[i - j].high
                for j in range(1, window + 1)
            )
            if is_swing_high:
                resistances.append(candles[i].high)

            # Swing low (support)
            is_swing_low = all(
                candles[i].low <= candles[i + j].low and
                candles[i].low <= candles[i - j].low
                for j in range(1, window + 1)
            )
            if is_swing_low:
                supports.append(candles[i].low)

        # Return only the most recent 3-5 levels (most relevant)
        return supports[-5:], resistances[-5:]

    def _calculate_rsi(self, closes, period):
        if len(closes) < period + 1:
            return None
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]

        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def _calculate_atr(self, candles, period):
        if len(candles) < period + 1:
            return None
        trs = []
        for i in range(1, len(candles)):
            tr = max(
                candles[i].high - candles[i].low,
                abs(candles[i].high - candles[i-1].close),
                abs(candles[i].low - candles[i-1].close)
            )
            trs.append(tr)
        if len(trs) < period:
            return None
        return sum(trs[-period:]) / period
```

---

## A-4: Rebuild Regime Detector (D1-Level, Proper Detection)

Replace the current ADX > 25 threshold with a detection method that operates on D1 data and catches regimes EARLIER.

### Implementation

**File:** `src/trading_bot/src/core/market_regime_detector.py` (rewrite)

```python
"""
D1 Market Regime Detector
==========================
Uses multiple D1-level metrics to classify market state:
- TRENDING: D1 price consistently above/below EMA(50), ADX rising, directional movement clear
- RANGING: D1 price oscillating around EMA(50), ADX flat or declining, no directional commitment

Key improvement over old system:
- ADX SLOPE matters more than ADX level. Rising ADX from 15→25 = trend starting (enter early).
  ADX at 35 but falling = trend ending (don't enter).
- The old system waited for ADX > 25, which fires when the trend is 60-70% done.
- The new system detects ADX rising 3+ days in a row with price on one side of EMA, catching
  trends 2-5 days earlier.
"""

from typing import Optional, List
from trading_bot.src.core.models import CandleData, MarketCondition


class MarketRegimeDetector:

    def __init__(self, config=None):
        self.ema_period = 50
        self.adx_period = 14
        self.adx_slope_lookback = 3    # days to measure ADX direction

    def detect_regime(self, d1_candles: List[CandleData]) -> MarketCondition:
        """
        Classify the current market regime from D1 candle data.
        Returns TRENDING_UP, TRENDING_DOWN, or RANGING.
        """
        if not d1_candles or len(d1_candles) < self.ema_period + self.adx_slope_lookback:
            return MarketCondition.UNKNOWN

        closes = [c.close for c in d1_candles]
        current_price = closes[-1]

        # D1 EMA(50)
        ema = self._ema(closes, self.ema_period)
        if ema is None:
            return MarketCondition.UNKNOWN

        # ADX values for the last N days
        adx_values = self._adx_series(d1_candles, self.adx_period, lookback=self.adx_slope_lookback + 1)
        if not adx_values or len(adx_values) < self.adx_slope_lookback + 1:
            return MarketCondition.UNKNOWN

        current_adx = adx_values[-1]
        adx_rising = all(adx_values[i] < adx_values[i+1] for i in range(-self.adx_slope_lookback - 1, -1))
        adx_falling = all(adx_values[i] > adx_values[i+1] for i in range(-self.adx_slope_lookback - 1, -1))

        # Price position relative to EMA
        price_above_ema = current_price > ema
        # How many of last 5 closes are on the same side of EMA?
        consistent_side = sum(1 for c in closes[-5:] if (c > ema) == price_above_ema)

        # TRENDING detection:
        # - Price consistently on one side of EMA (4+ of last 5 days)
        # - ADX rising OR ADX > 20 (lower threshold than the old 25)
        # - This catches trends earlier than the old ADX > 25 gate
        is_trending = consistent_side >= 4 and (adx_rising or current_adx > 20)

        # But NOT trending if ADX is falling from high levels (trend exhaustion)
        if adx_falling and current_adx > 30:
            is_trending = False  # trend is dying, don't enter

        if is_trending:
            if price_above_ema:
                return MarketCondition.TRENDING_UP
            else:
                return MarketCondition.TRENDING_DOWN

        return MarketCondition.RANGING

    def _ema(self, values, period):
        if len(values) < period:
            return None
        multiplier = 2 / (period + 1)
        ema = sum(values[:period]) / period
        for v in values[period:]:
            ema = (v - ema) * multiplier + ema
        return ema

    def _adx_series(self, candles, period, lookback=5):
        """Calculate ADX for the last `lookback` candles."""
        # Requires period + lookback + some warmup candles
        if len(candles) < period * 2 + lookback:
            return None

        results = []
        for offset in range(lookback, -1, -1):
            end_idx = len(candles) - offset if offset > 0 else len(candles)
            subset = candles[:end_idx]
            adx = self._calculate_adx(subset, period)
            if adx is not None:
                results.append(adx)

        return results

    def _calculate_adx(self, candles, period):
        """Wilder's ADX calculation."""
        if len(candles) < period * 2:
            return None

        # True Range, +DM, -DM
        tr_list, plus_dm_list, minus_dm_list = [], [], []
        for i in range(1, len(candles)):
            high, low, prev_close = candles[i].high, candles[i].low, candles[i-1].close
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            plus_dm = max(high - candles[i-1].high, 0) if (high - candles[i-1].high) > (candles[i-1].low - low) else 0
            minus_dm = max(candles[i-1].low - low, 0) if (candles[i-1].low - low) > (high - candles[i-1].high) else 0
            tr_list.append(tr)
            plus_dm_list.append(plus_dm)
            minus_dm_list.append(minus_dm)

        # Wilder smoothing
        atr = sum(tr_list[:period]) / period
        plus_di_smooth = sum(plus_dm_list[:period]) / period
        minus_di_smooth = sum(minus_dm_list[:period]) / period

        dx_list = []
        for i in range(period, len(tr_list)):
            atr = (atr * (period - 1) + tr_list[i]) / period
            plus_di_smooth = (plus_di_smooth * (period - 1) + plus_dm_list[i]) / period
            minus_di_smooth = (minus_di_smooth * (period - 1) + minus_dm_list[i]) / period

            if atr == 0:
                continue
            plus_di = 100 * plus_di_smooth / atr
            minus_di = 100 * minus_di_smooth / atr

            di_sum = plus_di + minus_di
            if di_sum == 0:
                continue
            dx = 100 * abs(plus_di - minus_di) / di_sum
            dx_list.append(dx)

        if len(dx_list) < period:
            return None

        adx = sum(dx_list[:period]) / period
        for i in range(period, len(dx_list)):
            adx = (adx * (period - 1) + dx_list[i]) / period

        return adx
```

### Why ADX Slope > ADX Level

The old system: ADX > 25 → trending. This fires when the trend is already mature.

The new system: ADX rising for 3+ days AND price consistently on one side of EMA → trending. This detects:
- ADX going from 15 → 18 → 21 → 24 = "trend is forming" → enter early
- ADX at 35 but going 35 → 33 → 31 = "trend is exhausting" → don't enter

This single change should improve entry timing by 2–5 daily candles, which on D1 means 2–5 days of additional trend capture per trade.

---

## A-5: Replace Consensus Voting with Hard Regime Switch

This is the biggest architectural change. Delete the 9-strategy weighted consensus system and replace it with a simple if/else.

**File:** `src/trading_bot/src/strategies/strategy_manager.py` (major rewrite)

The new `generate_signal()` method:

```python
async def generate_signal(self, pair, candles_by_tf, market_context=None, **kwargs):
    """
    Hard regime switch — run ONE strategy based on current market regime.
    No voting. No consensus. No weighted confidence.
    """
    d1_candles = candles_by_tf.get(TimeFrame.D1, [])
    h4_candles = candles_by_tf.get(TimeFrame.H4, [])
    m15_candles = candles_by_tf.get(TimeFrame.M15, [])

    # Step 1: Detect regime from D1 data
    regime = self.regime_detector.detect_regime(d1_candles)
    self.logger.info(f"{pair}: Regime = {regime.value}")

    # Step 2: Select strategy based on regime
    signal = None

    if regime in (MarketCondition.TRENDING_UP, MarketCondition.TRENDING_DOWN):
        signal = await self.daily_breakout.generate_signal(
            d1_candles=d1_candles,
            h4_candles=h4_candles,
            m15_candles=m15_candles,
            pair=pair
        )
        if signal:
            self.logger.info(f"{pair}: Daily Breakout signal: {signal.direction}")

    elif regime == MarketCondition.RANGING:
        signal = await self.structure_reversal.generate_signal(
            d1_candles=d1_candles,
            h4_candles=h4_candles,
            m15_candles=m15_candles,
            pair=pair
        )
        if signal:
            self.logger.info(f"{pair}: Structure Reversal signal: {signal.direction}")

    else:
        self.logger.info(f"{pair}: Regime UNKNOWN — no trade")
        return None

    # Step 3: M15 pullback entry refinement (optional precision layer)
    if signal and m15_candles and len(m15_candles) >= 21:
        if not self._m15_pullback_confirms(signal.direction, m15_candles):
            self.logger.info(f"{pair}: Signal valid but M15 pullback not aligned — skipping for now")
            return None  # wait for better M15 entry on next check

    return signal
```

### M15 Pullback Entry (A-6)

Instead of M15 boosting confidence, M15 is now a precision entry gate. A valid D1/H4 signal is only executed when M15 shows a pullback to the 20 EMA in the signal direction:

```python
def _m15_pullback_confirms(self, direction, m15_candles):
    """
    Check if M15 price has pulled back to the 20 EMA.
    This gives a better entry price than chasing the breakout.
    
    For BUY: M15 price touched or came within 3 pips of EMA20 from above,
             then the last candle closed above EMA20 (bounce off EMA = entry)
    For SELL: Mirror logic.
    """
    closes = [c.close for c in m15_candles]
    ema_20 = self._calculate_ema(closes, 20)
    if ema_20 is None:
        return True  # if can't calculate, don't block — let H4 signal through

    current_close = closes[-1]
    prev_close = closes[-2] if len(closes) >= 2 else current_close
    pip_size = 0.01 if any('JPY' in str(c) for c in m15_candles[:1]) else 0.0001
    tolerance = 3 * pip_size  # within 3 pips of EMA

    if direction == "buy":
        # Price was near or below EMA (pullback), now closed above (bounce)
        near_ema = min(c.low for c in m15_candles[-4:]) <= (ema_20 + tolerance)
        closed_above = current_close > ema_20
        return near_ema and closed_above

    elif direction == "sell":
        near_ema = max(c.high for c in m15_candles[-4:]) >= (ema_20 - tolerance)
        closed_below = current_close < ema_20
        return near_ema and closed_below

    return True
```

**Why this matters:** The old system entered on the breakout candle — the worst possible price. The new system waits for a pullback to EMA, entering at a better price. This directly improves R:R because:
- BUY entry is lower (closer to stop) → same stop level = smaller stop distance = larger position size for same risk
- Or: same position size, same stop → TP is now closer relative to where you entered → more TP hits

---

### What to Do with the Old Strategy Files

**DO NOT DELETE THEM.** Move them to an `archived/` directory:

```bash
mkdir -p src/trading_bot/src/strategies/archived
mv src/trading_bot/src/strategies/trend_momentum/* src/trading_bot/src/strategies/archived/
mv src/trading_bot/src/strategies/mean_reversion/* src/trading_bot/src/strategies/archived/
mv src/trading_bot/src/strategies/breakout/* src/trading_bot/src/strategies/archived/
mv src/trading_bot/src/strategies/scalping/* src/trading_bot/src/strategies/archived/
mv src/trading_bot/src/strategies/session_based/* src/trading_bot/src/strategies/archived/
```

Create the new strategy directory:
```bash
mkdir -p src/trading_bot/src/strategies/swing
```

Update `register_all.py` to import only the two new strategies:
```python
from .swing.daily_breakout import DailyBreakoutStrategy
from .swing.structure_reversal import StructureReversalStrategy
```

---

# PHASE 2: FTMO-AWARE RISK MANAGEMENT

## R-1: FTMO Drawdown Rules in Backtest

The FTMO challenge has specific rules that MUST be respected:
- **5% max daily loss** (based on starting equity of the day)
- **10% max total loss** (based on initial account balance)
- **10% profit target** to pass the challenge
- **30-day time limit**

Add these as hard constraints in the backtest engine:

```python
class FTMOSimulator:
    """Simulate FTMO challenge rules during backtest."""
    
    def __init__(self, initial_balance, daily_loss_limit=0.05, total_loss_limit=0.10, profit_target=0.10):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.daily_start_balance = initial_balance
        self.daily_loss_limit = daily_loss_limit
        self.total_loss_limit = total_loss_limit
        self.profit_target = profit_target
        self.challenge_passed = False
        self.challenge_failed = False
        self.fail_reason = None
        self.current_day = None
    
    def on_new_day(self, date):
        """Reset daily tracking."""
        if self.current_day != date:
            self.daily_start_balance = self.current_balance
            self.current_day = date
    
    def can_trade(self):
        """Check if trading is allowed under FTMO rules."""
        if self.challenge_failed:
            return False
        
        # Daily loss check
        daily_loss_pct = (self.daily_start_balance - self.current_balance) / self.daily_start_balance
        if daily_loss_pct >= self.daily_loss_limit:
            self.challenge_failed = True
            self.fail_reason = f"Daily loss limit hit: {daily_loss_pct:.2%}"
            return False
        
        # Total loss check
        total_loss_pct = (self.initial_balance - self.current_balance) / self.initial_balance
        if total_loss_pct >= self.total_loss_limit:
            self.challenge_failed = True
            self.fail_reason = f"Total loss limit hit: {total_loss_pct:.2%}"
            return False
        
        return True
    
    def on_trade_close(self, pnl):
        """Update balance after trade close."""
        self.current_balance += pnl
        
        # Check if profit target reached
        profit_pct = (self.current_balance - self.initial_balance) / self.initial_balance
        if profit_pct >= self.profit_target:
            self.challenge_passed = True
```

Wire this into the backtest loop so every trade respects FTMO constraints.

## R-2: Position Sizing for FTMO

On a $10,000 FTMO account with 10% max total drawdown ($1,000 max loss):
- Risk per trade: 0.5% = $50 per trade
- Max open positions: 2
- Max daily risk: 2% = $200 (leaves buffer before 5% daily limit)

```yaml
# FTMO-aware config
risk_management:
  risk_percentage: 0.5          # $50 risk per trade on $10K
  max_open_trades: 2
  max_daily_loss_percentage: 2.0  # stop trading at 2% daily (FTMO limit is 5%)
  max_total_drawdown_percentage: 8.0  # stop at 8% (FTMO limit is 10% — leave 2% buffer)
```

## R-3: Kill Switch

If the account reaches 4% total drawdown during a live session, halt all trading and send a Telegram alert. Don't wait for FTMO's 10% limit — stop early to preserve the account.

---

# PHASE 3: OUT-OF-SAMPLE TESTING

This is the most important validation step. Without it, you don't know if you've built a strategy or memorized a dataset.

## T-1: Split the Data

```python
# 730 days total (Mar 2024 — Mar 2026)
# Training: Mar 2024 — Aug 2025 (500 days)
# Testing:  Aug 2025 — Mar 2026 (230 days)

TRAIN_START = "2024-03-01"
TRAIN_END = "2025-08-15"
TEST_START = "2025-08-16"
TEST_END = "2026-03-15"
```

## T-2: Optimize on Train Period ONLY

Run the new system on the 500-day training period. Adjust these parameters if needed:
- Breakout buffer pips
- Min/max range filter
- S/R zone distance
- RSI thresholds
- EMA period
- R:R ratio

**Log every parameter change and the reason for it.**

## T-3: Run UNCHANGED on Test Period

Take the exact parameters from T-2 and run them on the 230-day test period. **DO NOT change anything.** Not one parameter. Not one filter.

## T-4: Compare Results

| Metric | Train (500d) | Test (230d) | Ratio |
|--------|-------------|-------------|-------|
| Trades | — | — | — |
| Win Rate | — | — | should be within 5% |
| Profit Factor | — | — | should be within 0.15 |
| Return | — | — | — |
| Max DD | — | — | — |

**If the test period PF is within 0.15 of the train period PF, the strategy is robust.** If test PF drops below 1.0 while train PF is 1.3+, you've curve-fit.

---

## Execution Order

```
1. A-1: Add D1 to data pipeline
2. A-4: Rebuild regime detector (D1-level)
3. A-2: Build Daily Breakout strategy
4. A-3: Build Structure Reversal strategy
5. A-5: Replace consensus with hard regime switch
6. A-6: M15 pullback entry
7. → Run 730-day backtest → record results
8. R-1: FTMO simulator
9. R-2/R-3: FTMO sizing and kill switch
10. → Run FTMO simulation → record pass/fail
11. T-1/T-2: Train period optimization
12. T-3/T-4: Out-of-sample validation
13. → Compare train vs test → record in tracker
```

---

## What Success Looks Like

| Metric | Old System | New Target |
|--------|-----------|------------|
| Strategies | 9 correlated | 2 independent |
| Win Rate | 35.9% | 45–55% |
| Profit Factor | 1.045 | 1.3–1.8 |
| R:R | 1.25:1 (effective) | 1.5:1 (structural) |
| Max Drawdown | 21.43% | <10% |
| FTMO compatible | No (21% DD) | Yes (<5% daily, <10% total) |
| Out-of-sample PF | Unknown | >1.0 |
| Trades per week | ~0.75 | 2–4 |

---

## Rules

1. **Do not carry over ANY of the old consensus voting logic.** Fresh start. Two strategies. One regime detector. No voting.
2. **Update `STRATEGY_OVERHAUL_TRACKER.md` after every change.**
3. **Archive old strategy files, don't delete them.** They may contain useful indicator calculation code you can reuse.
4. **The regime detector runs on D1 candles only.** It should NOT look at H4 or M15 for regime classification.
5. **The M15 pullback gate is OPTIONAL.** If it blocks too many valid signals (>50% rejection rate), remove it and let H4-level entries through directly. Better to enter at a worse price than to miss the trade entirely.
6. **Out-of-sample testing (Phase 3) is NON-NEGOTIABLE.** If you skip it, you don't know if the strategy works. Period.
7. **FTMO simulation (Phase 2) determines whether the FTMO path is viable.** If the strategy can't hit 10% profit before hitting 5% daily or 10% total drawdown in simulation, don't spend $167 on the challenge.
8. **The Daily Breakout strategy's stop (yesterday's low/high) is a STRUCTURAL level.** Do not replace it with ATR-based stops. The whole edge comes from stop placement at meaningful price levels.
9. **If the Structure Reversal strategy produces <5 trades in 230 test days**, the S/R zone distance (15 pips) may be too tight. Widen to 20–25 pips. If still <5, ranging conditions may be too infrequent for this pair — consider this strategy as EUR_USD-only (EUR_USD ranges more than GBP_USD).
10. **Keep the existing risk management infrastructure** (AdvancedRiskManager, PortfolioRiskManager, consecutive loss limit, trailing stop). These are good. The strategy is what needed replacing, not the risk framework.

**Begin now. Read `08_trading_bot_handoff_report.md` for the file map, create `STRATEGY_OVERHAUL_TRACKER.md`, then start with A-1.**
