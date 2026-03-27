# PROMPT: Build Intraday FX Bot — Session-Based Strategies for FTMO

## Who You Are

You are a **Senior Quantitative Developer** building an intraday Forex trading bot from scratch. This is a SEPARATE project from the existing swing trading bot. Different strategies, different timeframe, different edge source. You build simple systems — two to three rules per strategy, structural edges based on session timing and price levels, no indicator soup.

---

## Context — Why This Bot Exists

The goal is to pass FTMO challenges ($10K–$25K funded accounts) and generate monthly income from the profit split. FTMO gives you 30 days to hit a 10% profit target with a 5% daily and 10% total max drawdown. A swing bot that produces 2–5 trades per week doesn't generate enough trades to hit that target reliably. An intraday bot producing 2–3 trades per day during specific session windows gives enough volume to hit 10% in 10–15 trading days with room for losing streaks.

**This is NOT the old 9-strategy consensus system.** That system failed because:
- 9 correlated indicators measuring the same thing (lagging trend via EMA, MACD, ADX)
- Scalping strategies targeting 5–10 pips where 1.5 pip spread = 15–30% cost
- No session timing — treated all hours equally
- Consensus voting = noise averaging

**The new system is based on:**
- Session timing edges documented in academic research (Ranaldo 2009, Krohn et al. 2024, Breedon & Ranaldo 2013)
- Structural price levels (prior day's range, Asian session range) where institutional orders cluster (Osler 2003)
- Intraday mean reversion on M5 and breakout on M15 — matching the optimal horizons from Safari & Schmidhuber (2025)
- Trading ONLY during London open (07:00–10:00 GMT) and London/NY overlap (13:00–16:00 GMT)
- 15–30 pip targets where spread cost is 3–5% of profit, not 15–30%

**Pairs:** EUR_USD and GBP_USD only (tightest spreads, highest liquidity, most researched)

---

## Architecture

```
INTRADAY BOT
│
├── Data Pipeline
│   ├── D1 candles (prior day high/low/close — updated once at session start)
│   ├── H1 candles (session context — ATR, trend direction)
│   ├── M15 candles (entry signals for breakout strategies)
│   └── M5 candles (entry signals for mean reversion, precise timing)
│
├── Session Clock
│   ├── Asian session: 00:00–07:00 GMT (range accumulation — NO trading)
│   ├── London open: 07:00–10:00 GMT (ACTIVE — breakout strategies)
│   ├── London midday: 10:00–13:00 GMT (reduced activity — NO trading)
│   ├── London/NY overlap: 13:00–16:00 GMT (ACTIVE — momentum/breakout)
│   └── After 16:00 GMT: CLOSE all open positions, NO new trades
│
├── Strategy 1: Asian Range Breakout (London open window)
├── Strategy 2: London Open ORB (London open window)  
├── Strategy 3: NY Overlap Momentum (London/NY overlap window)
│
├── Risk Manager (FTMO-aware)
│   ├── 0.75% risk per trade
│   ├── Max 2 trades open simultaneously
│   ├── Daily loss limit: 2.5% (hard stop — leaves buffer to FTMO's 5%)
│   ├── Consecutive loss protocol: 2 losses → half size, 3 losses → stop for session
│   └── All positions closed by 16:00 GMT (no overnight risk)
│
└── Position Manager
    ├── ATR-based stops (1.5× M15 ATR)
    ├── Fixed R:R targets (1.5:1 minimum, 2:1 preferred)
    └── No trailing stop (intraday trades are too short — let TP hit or SL hit)
```

---

## Step 0: Project Setup

This is a SEPARATE codebase or a separate mode in the existing bot. Create a new directory:

```bash
mkdir -p src/trading_bot/src/strategies/intraday
```

Create `INTRADAY_BOT_TRACKER.md` in the project root:

```markdown
# Intraday Bot Build Tracker
> Session-based intraday strategies for FTMO.
> Started: [date/time]

## Build Progress
| # | Component | Status |
|---|-----------|--------|
| 1 | Session clock (trading window manager) | ⬜ |
| 2 | Asian Range Breakout strategy | ⬜ |
| 3 | London Open ORB strategy | ⬜ |
| 4 | NY Overlap Momentum strategy | ⬜ |
| 5 | FTMO risk manager | ⬜ |
| 6 | Intraday position manager (close all by 16:00) | ⬜ |
| 7 | Backtest engine (M5/M15 loop) | ⬜ |
| 8 | 180-day backtest | ⬜ |
| 9 | Out-of-sample validation | ⬜ |
| 10 | FTMO challenge simulation | ⬜ |

## Backtest Results
| Run | Strategies | Trades | WR | PF | Monthly Return | Max DD | FTMO Pass? |
|-----|-----------|--------|----|----|---------------|--------|------------|
```

---

## Component 1: Session Clock

Create `src/trading_bot/src/strategies/intraday/session_clock.py`

The session clock determines WHEN the bot is allowed to trade. This is the most important component — the edge comes from WHEN you trade, not WHAT indicators say.

```python
"""
Session Clock — Controls when each strategy is allowed to trade.

Trading windows (all times GMT/UTC):
- Asian accumulation: 00:00–07:00 — NO TRADING, only range marking
- London open:        07:00–10:00 — Asian Range Breakout + London ORB active
- London midday:      10:00–13:00 — NO TRADING (low volume, choppy)
- London/NY overlap:  13:00–16:00 — NY Overlap Momentum active
- After 16:00:        CLOSE ALL — no new trades, close any open positions

Why these windows:
- London open (07:00–10:00): 35% of daily FX volume. Institutional orders 
  from European banks create directional moves. Breakout strategies thrive.
- London/NY overlap (13:00–16:00): Highest liquidity of the day. Two major 
  centers trading simultaneously. Momentum strategies work best here.
- Asian session: Low volume, tight ranges. Perfect for marking S/R levels, 
  terrible for trading. Let the range form, then trade the breakout.
- Midday London: Volume drops between sessions. Whipsaw kills strategies.
"""

from datetime import datetime, time
from enum import Enum


class SessionState(Enum):
    ASIAN_ACCUMULATION = "asian_accumulation"    # 00:00–07:00 — mark ranges
    LONDON_OPEN = "london_open"                  # 07:00–10:00 — breakout window
    LONDON_MIDDAY = "london_midday"              # 10:00–13:00 — no trading
    NY_OVERLAP = "ny_overlap"                    # 13:00–16:00 — momentum window
    CLOSED = "closed"                            # 16:00–00:00 — no trading


class SessionClock:
    
    # Define session boundaries (GMT/UTC)
    SESSIONS = [
        (time(0, 0), time(7, 0), SessionState.ASIAN_ACCUMULATION),
        (time(7, 0), time(10, 0), SessionState.LONDON_OPEN),
        (time(10, 0), time(13, 0), SessionState.LONDON_MIDDAY),
        (time(13, 0), time(16, 0), SessionState.NY_OVERLAP),
        (time(16, 0), time(23, 59), SessionState.CLOSED),
    ]
    
    # Which strategies are active in which session
    ACTIVE_STRATEGIES = {
        SessionState.ASIAN_ACCUMULATION: [],          # no trading, just data collection
        SessionState.LONDON_OPEN: ['asian_range_breakout', 'london_orb'],
        SessionState.LONDON_MIDDAY: [],               # no trading
        SessionState.NY_OVERLAP: ['ny_overlap_momentum'],
        SessionState.CLOSED: [],                      # close positions
    }
    
    def get_session(self, current_time: datetime) -> SessionState:
        """Get the current session state."""
        t = current_time.time()
        for start, end, session in self.SESSIONS:
            if start <= t < end:
                return session
        return SessionState.CLOSED
    
    def is_trading_allowed(self, current_time: datetime) -> bool:
        """Check if any trading is allowed right now."""
        session = self.get_session(current_time)
        return len(self.ACTIVE_STRATEGIES.get(session, [])) > 0
    
    def get_active_strategies(self, current_time: datetime) -> list:
        """Get list of strategy names active in current session."""
        session = self.get_session(current_time)
        return self.ACTIVE_STRATEGIES.get(session, [])
    
    def should_close_all(self, current_time: datetime) -> bool:
        """Check if we should close all open positions."""
        return self.get_session(current_time) == SessionState.CLOSED
    
    def is_friday_close(self, current_time: datetime) -> bool:
        """Check if it's Friday after 15:00 — close early to avoid weekend gaps."""
        return current_time.weekday() == 4 and current_time.hour >= 15
    
    def is_weekend(self, current_time: datetime) -> bool:
        """No trading Saturday/Sunday."""
        return current_time.weekday() in (5, 6)
```

---

## Component 2: Asian Range Breakout Strategy

Create `src/trading_bot/src/strategies/intraday/asian_range_breakout.py`

**The edge:** The Asian session (00:00–07:00 GMT) creates a tight range on GBP/USD as low-volume trading oscillates. When London opens at 07:00, institutional order flow from European banks breaks this range with conviction. The breakout direction tends to persist through the London morning because it reflects real positioning, not noise.

**Documented performance:** Profit factor ~1.5 on GBP/USD, used by practitioners "for decades." The edge persists because it's driven by institutional session mechanics, not technical patterns that get arbitraged.

```python
"""
Asian Range Breakout Strategy
==============================
1. During 00:00–07:00 GMT, mark the HIGH and LOW of GBP/USD (and EUR/USD)
2. After 07:00 GMT, if price breaks ABOVE the range high by 5+ pips → BUY
3. After 07:00 GMT, if price breaks BELOW the range low by 5+ pips → SELL
4. Stop loss: opposite side of the Asian range
5. Take profit: 1.5× the stop distance (R:R = 1.5:1)
6. Close by 16:00 GMT regardless of P&L

Filters:
- Skip if Asian range > 40 pips (unusual volatility — news overnight)
- Skip if Asian range < 15 pips (too tight — no conviction in the breakout)
- Only trade GBP/USD (best documented results) and EUR/USD
- Only one breakout per day per pair (first break only — no re-entry)

Why it works:
- Asian session is dominated by Japanese/Australian flow — lower volume
- London open brings 35% of daily FX volume
- The Asian range acts as a compression zone
- Breakout of compression with volume = follow-through
- Stop at opposite side of range = structural level with meaning
"""

from datetime import datetime, time
from typing import Optional, List, Dict
from trading_bot.src.core.models import CandleData, TradeRecommendation


class AsianRangeBreakoutStrategy:
    
    def __init__(self, config=None):
        self.name = "Asian_Range_Breakout"
        self.asian_start = time(0, 0)       # midnight GMT
        self.asian_end = time(7, 0)         # 7 AM GMT
        self.trade_window_end = time(12, 0) # stop looking for breakouts by noon
        self.breakout_buffer_pips = 5       # require 5 pips beyond range
        self.min_range_pips = 15            # skip if range too tight
        self.max_range_pips = 40            # skip if range too wide
        self.rr_ratio = 1.5                 # reward:risk
        self._daily_ranges = {}             # pair -> {date: {high, low, traded}}
    
    def mark_asian_range(self, pair: str, candles: List[CandleData], current_time: datetime):
        """
        Call this during/after Asian session to record the range.
        Uses M5 or M15 candles from 00:00–07:00 GMT.
        """
        today = current_time.date()
        
        # Filter candles to Asian session today
        asian_candles = [
            c for c in candles
            if hasattr(c, 'timestamp') and 
               c.timestamp.date() == today and
               self.asian_start <= c.timestamp.time() < self.asian_end
        ]
        
        if not asian_candles:
            return
        
        asian_high = max(c.high for c in asian_candles)
        asian_low = min(c.low for c in asian_candles)
        
        if pair not in self._daily_ranges:
            self._daily_ranges[pair] = {}
        
        self._daily_ranges[pair][today] = {
            'high': asian_high,
            'low': asian_low,
            'range_pips': 0,  # calculated below
            'traded': False,   # only one trade per day per pair
        }
        
        pip_size = 0.01 if 'JPY' in pair else 0.0001
        self._daily_ranges[pair][today]['range_pips'] = (asian_high - asian_low) / pip_size
    
    async def generate_signal(
        self,
        pair: str,
        m15_candles: List[CandleData],
        current_time: datetime,
        **kwargs
    ) -> Optional[TradeRecommendation]:
        """
        Check if price has broken the Asian range.
        Call this on every M15 candle during the London open window (07:00–12:00).
        """
        today = current_time.date()
        
        # Check we have a range for today
        if pair not in self._daily_ranges or today not in self._daily_ranges[pair]:
            return None
        
        range_data = self._daily_ranges[pair][today]
        
        # Already traded this pair today — one shot only
        if range_data['traded']:
            return None
        
        # Range filter
        if range_data['range_pips'] < self.min_range_pips:
            return None  # too tight — no conviction
        if range_data['range_pips'] > self.max_range_pips:
            return None  # too wide — likely news-driven, unreliable
        
        # Past the trade window
        if current_time.time() >= self.trade_window_end:
            return None
        
        asian_high = range_data['high']
        asian_low = range_data['low']
        pip_size = 0.01 if 'JPY' in pair else 0.0001
        buffer = self.breakout_buffer_pips * pip_size
        
        # Current price
        if not m15_candles:
            return None
        current_price = m15_candles[-1].close
        current_high = m15_candles[-1].high
        current_low = m15_candles[-1].low
        
        signal = None
        
        # BUY breakout: candle high broke above Asian high + buffer
        if current_high > (asian_high + buffer) and current_price > asian_high:
            entry = current_price
            stop_loss = asian_low               # opposite side of range
            stop_distance = entry - stop_loss
            take_profit = entry + (stop_distance * self.rr_ratio)
            
            signal = TradeRecommendation(
                pair=pair,
                direction="buy",
                confidence=0.70,
                entry_price=entry,
                stop_loss=stop_loss,
                take_profit=take_profit,
                metadata={
                    'strategy': self.name,
                    'asian_high': float(asian_high),
                    'asian_low': float(asian_low),
                    'range_pips': range_data['range_pips'],
                    'r_r_ratio': self.rr_ratio,
                    'session': 'london_open',
                }
            )
            range_data['traded'] = True
        
        # SELL breakout: candle low broke below Asian low - buffer
        elif current_low < (asian_low - buffer) and current_price < asian_low:
            entry = current_price
            stop_loss = asian_high              # opposite side of range
            stop_distance = stop_loss - entry
            take_profit = entry - (stop_distance * self.rr_ratio)
            
            signal = TradeRecommendation(
                pair=pair,
                direction="sell",
                confidence=0.70,
                entry_price=entry,
                stop_loss=stop_loss,
                take_profit=take_profit,
                metadata={
                    'strategy': self.name,
                    'asian_high': float(asian_high),
                    'asian_low': float(asian_low),
                    'range_pips': range_data['range_pips'],
                    'r_r_ratio': self.rr_ratio,
                    'session': 'london_open',
                }
            )
            range_data['traded'] = True
        
        return signal
    
    def reset_daily(self):
        """Call at end of each trading day to clean up old ranges."""
        self._daily_ranges = {}
```

---

## Component 3: London Open ORB Strategy

Create `src/trading_bot/src/strategies/intraday/london_orb.py`

**The edge:** The first 30 minutes of London (07:00–07:30 GMT) establish a "opening range" driven by the initial wave of European institutional orders. When price breaks this range convincingly, it tends to follow through because the breakout represents genuine directional commitment from the largest participants.

```python
"""
London Open ORB (Opening Range Breakout)
==========================================
1. Mark the HIGH and LOW from 07:00–07:30 GMT (first 30 min of London)
2. After 07:30, if price breaks above the range high → BUY
3. After 07:30, if price breaks below the range low → SELL
4. Stop: opposite side of the opening range
5. TP: 1.5× stop distance (R:R = 1.5:1)
6. Confirmation: price must CLOSE an M5 candle beyond the range (not just wick)
7. Close by 12:00 GMT if neither TP nor SL hit

Filters:
- Opening range must be 8–25 pips (skip if too tight or too wide)
- Skip if Asian Range Breakout already triggered for this pair today
  (avoid doubling up on the same directional move)
- Skip Mondays before 08:00 (weekend gap noise)
- Skip days with high-impact news in the 07:00–08:00 window

Best on: EUR/USD (tighter spreads during London)
"""

from datetime import datetime, time
from typing import Optional, List
from trading_bot.src.core.models import CandleData, TradeRecommendation


class LondonORBStrategy:
    
    def __init__(self, config=None):
        self.name = "London_ORB"
        self.orb_start = time(7, 0)         # 07:00 GMT
        self.orb_end = time(7, 30)          # 07:30 GMT
        self.trade_window_end = time(12, 0) # close by noon if no TP/SL
        self.min_range_pips = 8
        self.max_range_pips = 25
        self.rr_ratio = 1.5
        self._daily_orb = {}                # pair -> {date: {high, low, traded}}
    
    def mark_opening_range(self, pair: str, candles: List[CandleData], current_time: datetime):
        """
        Record the 07:00–07:30 GMT opening range.
        Call this after 07:30 GMT using M5 candles.
        """
        today = current_time.date()
        
        orb_candles = [
            c for c in candles
            if hasattr(c, 'timestamp') and
               c.timestamp.date() == today and
               self.orb_start <= c.timestamp.time() < self.orb_end
        ]
        
        if not orb_candles or len(orb_candles) < 3:  # need at least 3 M5 candles in 30 min
            return
        
        orb_high = max(c.high for c in orb_candles)
        orb_low = min(c.low for c in orb_candles)
        
        pip_size = 0.01 if 'JPY' in pair else 0.0001
        range_pips = (orb_high - orb_low) / pip_size
        
        if pair not in self._daily_orb:
            self._daily_orb[pair] = {}
        
        self._daily_orb[pair][today] = {
            'high': orb_high,
            'low': orb_low,
            'range_pips': range_pips,
            'traded': False,
        }
    
    async def generate_signal(
        self,
        pair: str,
        m5_candles: List[CandleData],
        current_time: datetime,
        asian_breakout_triggered: bool = False,
        **kwargs
    ) -> Optional[TradeRecommendation]:
        """
        Check for ORB breakout after 07:30 GMT.
        Requires an M5 candle CLOSE beyond the range (not just a wick).
        """
        today = current_time.date()
        
        if pair not in self._daily_orb or today not in self._daily_orb[pair]:
            return None
        
        orb = self._daily_orb[pair][today]
        
        if orb['traded']:
            return None
        
        # Range filter
        if orb['range_pips'] < self.min_range_pips or orb['range_pips'] > self.max_range_pips:
            return None
        
        # Don't double up if Asian Range Breakout already fired
        if asian_breakout_triggered:
            return None
        
        # Must be after ORB period
        if current_time.time() < self.orb_end:
            return None
        
        if current_time.time() >= self.trade_window_end:
            return None
        
        # Skip Monday before 08:00 (weekend gap noise)
        if current_time.weekday() == 0 and current_time.hour < 8:
            return None
        
        if not m5_candles:
            return None
        
        latest = m5_candles[-1]
        pip_size = 0.01 if 'JPY' in pair else 0.0001
        
        signal = None
        
        # BUY: M5 candle CLOSED above ORB high (not just wicked)
        if latest.close > orb['high']:
            entry = latest.close
            stop_loss = orb['low']
            stop_distance = entry - stop_loss
            take_profit = entry + (stop_distance * self.rr_ratio)
            
            signal = TradeRecommendation(
                pair=pair,
                direction="buy",
                confidence=0.70,
                entry_price=entry,
                stop_loss=stop_loss,
                take_profit=take_profit,
                metadata={
                    'strategy': self.name,
                    'orb_high': float(orb['high']),
                    'orb_low': float(orb['low']),
                    'range_pips': orb['range_pips'],
                    'r_r_ratio': self.rr_ratio,
                    'session': 'london_open',
                }
            )
            orb['traded'] = True
        
        # SELL: M5 candle CLOSED below ORB low
        elif latest.close < orb['low']:
            entry = latest.close
            stop_loss = orb['high']
            stop_distance = stop_loss - entry
            take_profit = entry - (stop_distance * self.rr_ratio)
            
            signal = TradeRecommendation(
                pair=pair,
                direction="sell",
                confidence=0.70,
                entry_price=entry,
                stop_loss=stop_loss,
                take_profit=take_profit,
                metadata={
                    'strategy': self.name,
                    'orb_high': float(orb['high']),
                    'orb_low': float(orb['low']),
                    'range_pips': orb['range_pips'],
                    'r_r_ratio': self.rr_ratio,
                    'session': 'london_open',
                }
            )
            orb['traded'] = True
        
        return signal
    
    def reset_daily(self):
        self._daily_orb = {}
```

---

## Component 4: NY Overlap Momentum Strategy

Create `src/trading_bot/src/strategies/intraday/ny_overlap_momentum.py`

**The edge:** When New York opens and overlaps with London (13:00–16:00 GMT), the combined volume from two major financial centers creates the strongest directional moves of the day. If the London session established a clear direction (up or down from the open), the NY session tends to extend that move as NY participants pile on.

```python
"""
NY Overlap Momentum Strategy
==============================
1. At 13:00 GMT, check the direction of the London session so far:
   - London bullish: price is above the 07:00 GMT open AND above the London session VWAP
   - London bearish: price is below the 07:00 GMT open AND below the VWAP
2. If London bullish → look for BUY entry on M15 pullback
3. If London bearish → look for SELL entry on M15 pullback
4. Entry: M15 candle pulls back to 20 EMA then closes in the momentum direction
5. Stop: 1.5× M15 ATR(14) below entry (BUY) or above entry (SELL)
6. TP: 2× stop distance (R:R = 2:1)
7. Close by 16:00 GMT regardless

Filters:
- London must have moved 15+ pips in one direction (clear trend, not chop)
- Skip if 2+ intraday trades already taken today (prevent overtrading)
- Skip if current M15 ATR < 5 pips (low volatility, no momentum)
- Skip Fridays after 14:30 (pre-weekend position squaring)

Best on: EUR/USD and GBP/USD equally
"""

from datetime import datetime, time
from typing import Optional, List
from trading_bot.src.core.models import CandleData, TradeRecommendation


class NYOverlapMomentumStrategy:
    
    def __init__(self, config=None):
        self.name = "NY_Overlap_Momentum"
        self.london_open_time = time(7, 0)
        self.ny_start = time(13, 0)
        self.ny_end = time(16, 0)
        self.min_london_move_pips = 15
        self.ema_period = 20
        self.atr_period = 14
        self.rr_ratio = 2.0
        self.atr_stop_multiplier = 1.5
        self.min_atr_pips = 5
        self._daily_london_open = {}  # pair -> {date: open_price}
    
    def mark_london_open(self, pair: str, candles: List[CandleData], current_time: datetime):
        """Record the 07:00 GMT opening price."""
        today = current_time.date()
        
        for c in candles:
            if (hasattr(c, 'timestamp') and 
                c.timestamp.date() == today and 
                c.timestamp.time() >= self.london_open_time):
                if pair not in self._daily_london_open:
                    self._daily_london_open[pair] = {}
                self._daily_london_open[pair][today] = c.open
                break
    
    async def generate_signal(
        self,
        pair: str,
        m15_candles: List[CandleData],
        current_time: datetime,
        trades_today: int = 0,
        **kwargs
    ) -> Optional[TradeRecommendation]:
        """
        Check for momentum continuation during NY overlap.
        """
        today = current_time.date()
        
        # Must be in NY overlap window
        if not (self.ny_start <= current_time.time() < self.ny_end):
            return None
        
        # Skip Friday late afternoon
        if current_time.weekday() == 4 and current_time.hour >= 14 and current_time.minute >= 30:
            return None
        
        # Max trades per day
        if trades_today >= 2:
            return None
        
        # Need London open price
        if pair not in self._daily_london_open or today not in self._daily_london_open[pair]:
            return None
        
        london_open_price = self._daily_london_open[pair][today]
        
        if not m15_candles or len(m15_candles) < self.ema_period + 1:
            return None
        
        pip_size = 0.01 if 'JPY' in pair else 0.0001
        current_price = m15_candles[-1].close
        
        # How far has London moved?
        london_move = current_price - london_open_price
        london_move_pips = london_move / pip_size
        
        if abs(london_move_pips) < self.min_london_move_pips:
            return None  # no clear direction from London
        
        london_bullish = london_move_pips > 0
        
        # Calculate M15 EMA(20) and ATR(14)
        closes = [c.close for c in m15_candles]
        ema_20 = self._ema(closes, self.ema_period)
        atr = self._atr(m15_candles, self.atr_period)
        
        if ema_20 is None or atr is None:
            return None
        
        atr_pips = atr / pip_size
        if atr_pips < self.min_atr_pips:
            return None  # too quiet
        
        latest = m15_candles[-1]
        prev = m15_candles[-2] if len(m15_candles) >= 2 else latest
        
        signal = None
        stop_distance = atr * self.atr_stop_multiplier
        
        # BUY: London bullish + price pulled back near EMA + closed above EMA
        if london_bullish and current_price > ema_20:
            # Check pullback: low of recent candles touched or came near EMA
            recent_low = min(c.low for c in m15_candles[-4:])
            tolerance = 3 * pip_size
            pulled_back = recent_low <= (ema_20 + tolerance)
            
            if pulled_back:
                entry = current_price
                stop_loss = entry - stop_distance
                take_profit = entry + (stop_distance * self.rr_ratio)
                
                signal = TradeRecommendation(
                    pair=pair,
                    direction="buy",
                    confidence=0.65,
                    entry_price=entry,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    metadata={
                        'strategy': self.name,
                        'london_move_pips': float(london_move_pips),
                        'ema_20': float(ema_20),
                        'atr_pips': float(atr_pips),
                        'r_r_ratio': self.rr_ratio,
                        'session': 'ny_overlap',
                    }
                )
        
        # SELL: London bearish + price pulled back near EMA + closed below EMA
        elif not london_bullish and current_price < ema_20:
            recent_high = max(c.high for c in m15_candles[-4:])
            tolerance = 3 * pip_size
            pulled_back = recent_high >= (ema_20 - tolerance)
            
            if pulled_back:
                entry = current_price
                stop_loss = entry + stop_distance
                take_profit = entry - (stop_distance * self.rr_ratio)
                
                signal = TradeRecommendation(
                    pair=pair,
                    direction="sell",
                    confidence=0.65,
                    entry_price=entry,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    metadata={
                        'strategy': self.name,
                        'london_move_pips': float(london_move_pips),
                        'ema_20': float(ema_20),
                        'atr_pips': float(atr_pips),
                        'r_r_ratio': self.rr_ratio,
                        'session': 'ny_overlap',
                    }
                )
        
        return signal
    
    def _ema(self, values, period):
        if len(values) < period:
            return None
        multiplier = 2 / (period + 1)
        ema = sum(values[:period]) / period
        for v in values[period:]:
            ema = (v - ema) * multiplier + ema
        return ema
    
    def _atr(self, candles, period):
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
        return sum(trs[-period:]) / period
    
    def reset_daily(self):
        self._daily_london_open = {}
```

---

## Component 5: FTMO Risk Manager

Create `src/trading_bot/src/strategies/intraday/ftmo_risk_manager.py`

```python
"""
FTMO-Aware Risk Manager
========================
Enforces FTMO challenge rules as hard constraints:
- 5% max daily drawdown (we stop at 2.5% — leave buffer)
- 10% max total drawdown (we stop at 8% — leave buffer)
- Max 2 positions open simultaneously
- Consecutive loss protocol: 2 losses → half size, 3 → stop for session
- All positions closed by 16:00 GMT (no overnight risk)
"""

from datetime import datetime, date, timedelta
from typing import Optional


class FTMORiskManager:
    
    def __init__(self, initial_balance: float, config=None):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.daily_start_balance = initial_balance
        self.current_date = None
        
        # FTMO limits (with safety buffer)
        self.daily_loss_limit_pct = 2.5     # FTMO allows 5%, we stop at 2.5%
        self.total_loss_limit_pct = 8.0     # FTMO allows 10%, we stop at 8%
        self.max_open_positions = 2
        self.base_risk_pct = 0.75           # 0.75% risk per trade
        
        # Consecutive loss tracking
        self.consecutive_losses = 0
        self.max_consecutive_before_halt = 3
        self.session_halted = False
        
        # Trade counting
        self.trades_today = 0
        self.max_trades_per_day = 5         # hard cap
        
        # Open position tracking
        self.open_position_count = 0
    
    def on_new_day(self, current_time: datetime):
        """Reset daily counters."""
        today = current_time.date()
        if self.current_date != today:
            self.daily_start_balance = self.current_balance
            self.current_date = today
            self.trades_today = 0
            self.session_halted = False
            # Don't reset consecutive_losses — they span days
    
    def can_open_trade(self) -> tuple:
        """
        Check if a new trade is allowed under FTMO rules.
        Returns (allowed: bool, reason: str)
        """
        # Session halted from consecutive losses
        if self.session_halted:
            return False, "Session halted: 3 consecutive losses"
        
        # Daily trade limit
        if self.trades_today >= self.max_trades_per_day:
            return False, f"Daily trade limit reached ({self.max_trades_per_day})"
        
        # Position limit
        if self.open_position_count >= self.max_open_positions:
            return False, f"Max positions open ({self.max_open_positions})"
        
        # Daily loss check
        daily_loss_pct = (self.daily_start_balance - self.current_balance) / self.daily_start_balance * 100
        if daily_loss_pct >= self.daily_loss_limit_pct:
            return False, f"Daily loss limit: {daily_loss_pct:.1f}% (limit {self.daily_loss_limit_pct}%)"
        
        # Total loss check
        total_loss_pct = (self.initial_balance - self.current_balance) / self.initial_balance * 100
        if total_loss_pct >= self.total_loss_limit_pct:
            return False, f"Total drawdown limit: {total_loss_pct:.1f}% (limit {self.total_loss_limit_pct}%)"
        
        return True, "OK"
    
    def get_risk_percentage(self) -> float:
        """
        Get current risk per trade, adjusted for consecutive losses.
        Normal: 0.75%. After 2 losses: 0.375% (half size).
        """
        if self.consecutive_losses >= 2:
            return self.base_risk_pct * 0.5  # half size after 2 consecutive losses
        return self.base_risk_pct
    
    def on_trade_opened(self):
        """Called when a new trade is opened."""
        self.open_position_count += 1
        self.trades_today += 1
    
    def on_trade_closed(self, pnl: float):
        """Called when a trade is closed."""
        self.current_balance += pnl
        self.open_position_count = max(0, self.open_position_count - 1)
        
        if pnl < 0:
            self.consecutive_losses += 1
            if self.consecutive_losses >= self.max_consecutive_before_halt:
                self.session_halted = True
        else:
            self.consecutive_losses = 0  # reset on any win
    
    def get_stats(self) -> dict:
        """Get current risk status for logging."""
        daily_pnl_pct = (self.current_balance - self.daily_start_balance) / self.daily_start_balance * 100
        total_pnl_pct = (self.current_balance - self.initial_balance) / self.initial_balance * 100
        
        return {
            'balance': self.current_balance,
            'daily_pnl_pct': daily_pnl_pct,
            'total_pnl_pct': total_pnl_pct,
            'consecutive_losses': self.consecutive_losses,
            'trades_today': self.trades_today,
            'open_positions': self.open_position_count,
            'session_halted': self.session_halted,
            'risk_pct': self.get_risk_percentage(),
        }
```

---

## Component 6: Intraday Strategy Manager (Orchestrator)

Create `src/trading_bot/src/strategies/intraday/intraday_manager.py`

This replaces the old consensus voting entirely. No voting. The session clock decides which strategy runs. Each strategy independently decides whether to signal.

```python
"""
Intraday Strategy Manager
==========================
Orchestrates the three session-based strategies.
No voting. No consensus. Each strategy is independent.
The session clock controls which strategies are active.
"""

from datetime import datetime
from typing import Optional, List, Dict
from trading_bot.src.core.models import CandleData, TradeRecommendation

from .session_clock import SessionClock, SessionState
from .asian_range_breakout import AsianRangeBreakoutStrategy
from .london_orb import LondonORBStrategy
from .ny_overlap_momentum import NYOverlapMomentumStrategy
from .ftmo_risk_manager import FTMORiskManager

import logging

logger = logging.getLogger(__name__)


class IntradayManager:
    
    def __init__(self, config, initial_balance: float = 10000):
        self.config = config
        self.session_clock = SessionClock()
        self.risk_manager = FTMORiskManager(initial_balance, config)
        
        self.asian_breakout = AsianRangeBreakoutStrategy(config)
        self.london_orb = LondonORBStrategy(config)
        self.ny_momentum = NYOverlapMomentumStrategy(config)
        
        self._asian_breakout_fired_today = {}  # pair -> bool
    
    async def on_candle(
        self,
        pair: str,
        m5_candles: List[CandleData],
        m15_candles: List[CandleData],
        current_time: datetime
    ) -> Optional[TradeRecommendation]:
        """
        Called on every M5 candle. Routes to the correct strategy
        based on session clock.
        """
        # New day reset
        self.risk_manager.on_new_day(current_time)
        
        # Weekend — no trading
        if self.session_clock.is_weekend(current_time):
            return None
        
        # Friday close — no new trades after 15:00
        if self.session_clock.is_friday_close(current_time):
            return None
        
        # Risk check
        can_trade, reason = self.risk_manager.can_open_trade()
        if not can_trade:
            logger.debug(f"{pair}: Trade blocked — {reason}")
            return None
        
        session = self.session_clock.get_session(current_time)
        
        # === ASIAN SESSION: Mark ranges, don't trade ===
        if session == SessionState.ASIAN_ACCUMULATION:
            self.asian_breakout.mark_asian_range(pair, m5_candles, current_time)
            return None
        
        # === LONDON OPEN: Run breakout strategies ===
        if session == SessionState.LONDON_OPEN:
            # Mark London ORB range (07:00–07:30)
            if current_time.time().hour == 7 and current_time.time().minute <= 30:
                self.london_orb.mark_opening_range(pair, m5_candles, current_time)
                self.ny_momentum.mark_london_open(pair, m5_candles, current_time)
            
            # Try Asian Range Breakout first (wider range, bigger moves)
            signal = await self.asian_breakout.generate_signal(
                pair=pair, m15_candles=m15_candles, current_time=current_time
            )
            if signal:
                self._asian_breakout_fired_today[pair] = True
                logger.info(f"{pair}: Asian Range Breakout → {signal.direction}")
                self.risk_manager.on_trade_opened()
                return signal
            
            # Try London ORB (after 07:30)
            asian_fired = self._asian_breakout_fired_today.get(pair, False)
            signal = await self.london_orb.generate_signal(
                pair=pair, m5_candles=m5_candles, current_time=current_time,
                asian_breakout_triggered=asian_fired
            )
            if signal:
                logger.info(f"{pair}: London ORB → {signal.direction}")
                self.risk_manager.on_trade_opened()
                return signal
        
        # === LONDON MIDDAY: No trading ===
        if session == SessionState.LONDON_MIDDAY:
            return None
        
        # === NY OVERLAP: Run momentum strategy ===
        if session == SessionState.NY_OVERLAP:
            signal = await self.ny_momentum.generate_signal(
                pair=pair, m15_candles=m15_candles, current_time=current_time,
                trades_today=self.risk_manager.trades_today
            )
            if signal:
                logger.info(f"{pair}: NY Overlap Momentum → {signal.direction}")
                self.risk_manager.on_trade_opened()
                return signal
        
        return None
    
    def on_trade_closed(self, pnl: float):
        """Notify risk manager of closed trade."""
        self.risk_manager.on_trade_closed(pnl)
    
    def should_close_all(self, current_time: datetime) -> bool:
        """Check if all positions should be closed (end of day)."""
        return self.session_clock.should_close_all(current_time)
    
    def reset_daily(self):
        """End-of-day cleanup."""
        self.asian_breakout.reset_daily()
        self.london_orb.reset_daily()
        self.ny_momentum.reset_daily()
        self._asian_breakout_fired_today = {}
```

---

## Component 7: Backtest Configuration

The intraday backtest needs to loop at M5 frequency (every 5 minutes) during trading hours and skip non-trading hours.

```yaml
# intraday_config.yaml
intraday:
  pairs:
    - EUR_USD
    - GBP_USD
  
  timeframes:
    - M5       # precise entry timing
    - M15      # strategy signals
  
  risk:
    risk_percentage: 0.75
    max_open_trades: 2
    max_trades_per_day: 5
    daily_loss_limit_pct: 2.5
    total_loss_limit_pct: 8.0
    consecutive_loss_halt: 3
  
  sessions:
    asian_start: "00:00"
    london_open: "07:00"
    london_midday: "10:00"
    ny_overlap_start: "13:00"
    close_all: "16:00"
  
  strategies:
    asian_range_breakout:
      min_range_pips: 15
      max_range_pips: 40
      breakout_buffer_pips: 5
      rr_ratio: 1.5
    
    london_orb:
      min_range_pips: 8
      max_range_pips: 25
      rr_ratio: 1.5
    
    ny_overlap_momentum:
      min_london_move_pips: 15
      ema_period: 20
      atr_period: 14
      atr_stop_multiplier: 1.5
      rr_ratio: 2.0
      min_atr_pips: 5
  
  backtesting:
    period_days: 365            # 1 year minimum
    initial_balance: 10000
    spread_pips: 0.7            # realistic FTMO spread on EUR/USD
    loop_interval_minutes: 5    # M5 loop
```

---

## Backtest & Validation Plan

### Step 1: Build and run 365-day backtest

```bash
python run.py --backtest-intraday --days 365 --pairs EUR_USD GBP_USD
```

### Step 2: Record per-strategy results

| Strategy | Trades | WR | PF | Avg Win | Avg Loss | R:R |
|----------|--------|----|----|---------|----------|-----|
| Asian Range Breakout | — | — | — | — | — | — |
| London ORB | — | — | — | — | — | — |
| NY Overlap Momentum | — | — | — | — | — | — |
| **Combined** | — | — | — | — | — | — |

### Step 3: Out-of-sample split (same as swing bot)

- Train: first 250 days
- Test: last 115 days (unchanged parameters)
- Compare PF between train and test

### Step 4: FTMO challenge simulation

Run 30-day windows through the backtest and check:
- Did it hit 10% profit before 5% daily or 10% total drawdown?
- How many of the 30-day windows pass vs fail?
- What's the average time to hit 10%?

---

## Expected Results

| Metric | Target | Why |
|--------|--------|-----|
| Trades per day | 2–3 | Two sessions × two pairs, filtered |
| Win rate | 50–55% | Session breakout strategies documented at this range |
| R:R | 1.5:1 to 2:1 | Structural stops + fixed targets |
| Profit factor | 1.3–1.6 | Conservative given transaction costs |
| Monthly return (gross) | 3–5% | 40–60 trades × $25–35 expectancy per trade |
| Max drawdown | <8% | FTMO buffer maintained |
| FTMO challenge pass | 10–15 trading days | ~$32/trade × 30 trades = $960 = ~10% of $10K |

---

## Rules

1. **This is a SEPARATE system from the swing bot.** Don't merge them. Different strategies, different timeframes, different config.
2. **Session timing is the edge.** If you find yourself adding RSI filters, MACD confirmations, or ADX gates — stop. The edge is WHEN you trade, not what indicators say.
3. **One trade per strategy per pair per day.** The Asian Range Breakout fires once or not at all. The London ORB fires once or not at all. No re-entries.
4. **Close everything by 16:00 GMT.** No overnight risk. FTMO overnight gaps have ended more challenges than bad entries.
5. **The FTMO risk manager is a HARD constraint.** It can block trades. It cannot be overridden.
6. **Out-of-sample testing is required before using real money.** If the test period PF drops below 1.0, the strategy is overfit.
7. **GBP/USD is the primary pair for Asian Range Breakout.** EUR/USD is secondary. Research shows GBP responds more strongly to the Asian-to-London transition.
8. **Don't add more strategies.** Three is the maximum. Each additional strategy adds complexity without proportional edge. If one strategy underperforms, disable it — don't replace it with a fourth.
9. **Log every trade with session, strategy, regime, and R:R.** This data is your feedback loop.
10. **Update `INTRADAY_BOT_TRACKER.md` after every component and every backtest.**

**Begin now. Create `INTRADAY_BOT_TRACKER.md`, then build Component 1 (Session Clock), then Component 2 (Asian Range Breakout), and work through the list in order.**
