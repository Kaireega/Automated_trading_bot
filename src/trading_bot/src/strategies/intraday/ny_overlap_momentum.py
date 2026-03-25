"""
NY Overlap Momentum Strategy
==============================
Edge: When New York opens and overlaps with London (13:00–16:00 GMT), the
combined volume from two major financial centers creates the strongest
directional moves of the day. If London established a clear direction,
NY participants tend to extend that move as they pile on.

Rules:
1. At 13:00 GMT, check London session direction:
   - Bullish: price above 07:00 GMT open AND above M15 EMA(20)
   - Bearish: price below 07:00 GMT open AND below M15 EMA(20)
2. If London bullish → look for BUY entry on M15 pullback to EMA(20)
3. If London bearish → look for SELL entry on M15 pullback to EMA(20)
4. Entry: recent candles pulled back near EMA(20), last close above/below it
5. Stop: 1.5× M15 ATR(14) from entry
6. TP: 2× stop distance (R:R = 2:1)
7. Close by 16:00 GMT regardless

Filters:
- London must have moved 15+ pips from 07:00 open (clear trend)
- Skip if M15 ATR < 5 pips (no momentum)
- Skip if 2+ trades already taken today
- Skip Fridays after 14:30 (pre-weekend position squaring)
- One NY overlap trade per pair per day
"""

from datetime import datetime, time
from typing import Optional, List


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
        self._daily_traded = {}       # pair -> {date: bool}

    def mark_london_open(self, pair: str, candles: list, current_time: datetime):
        """Record the 07:00 GMT open price from the first candle at/after 07:00."""
        today = current_time.date()

        for c in candles:
            if (hasattr(c, 'timestamp') and
                    c.timestamp.date() == today and
                    c.timestamp.time() >= self.london_open_time):
                if pair not in self._daily_london_open:
                    self._daily_london_open[pair] = {}
                self._daily_london_open[pair][today] = float(c.open)
                break

    async def generate_signal(
        self,
        pair: str,
        m15_candles: list,
        current_time: datetime,
        trades_today: int = 0,
        **kwargs
    ) -> Optional[dict]:
        """
        Check for momentum continuation during NY overlap (13:00–16:00 GMT).
        """
        today = current_time.date()

        # Must be in NY overlap window
        if not (self.ny_start <= current_time.time() < self.ny_end):
            return None

        # Skip Friday late afternoon
        if current_time.weekday() == 4 and current_time.hour >= 14 and current_time.minute >= 30:
            return None

        # Max 2 trades per day across all strategies
        if trades_today >= 2:
            return None

        # One NY trade per pair per day
        if self._daily_traded.get(pair, {}).get(today, False):
            return None

        if pair not in self._daily_london_open or today not in self._daily_london_open[pair]:
            return None

        london_open_price = self._daily_london_open[pair][today]

        if not m15_candles or len(m15_candles) < self.ema_period + 1:
            return None

        pip_size = 0.01 if 'JPY' in pair else 0.0001
        current_price = float(m15_candles[-1].close)

        # How far has London moved from its open?
        london_move_pips = (current_price - london_open_price) / pip_size

        if abs(london_move_pips) < self.min_london_move_pips:
            return None  # no clear direction from London

        london_bullish = london_move_pips > 0

        closes = [float(c.close) for c in m15_candles]
        highs = [float(c.high) for c in m15_candles]
        lows = [float(c.low) for c in m15_candles]

        ema_20 = self._ema(closes, self.ema_period)
        atr = self._atr(m15_candles, self.atr_period)

        if ema_20 is None or atr is None:
            return None

        atr_pips = atr / pip_size
        if atr_pips < self.min_atr_pips:
            return None

        stop_distance = atr * self.atr_stop_multiplier
        tolerance = 3 * pip_size  # within 3 pips of EMA counts as "at EMA"
        signal = None

        # BUY: London bullish, price above EMA(20), recent pullback touched EMA
        if london_bullish and current_price > ema_20:
            recent_low = min(lows[-4:])
            pulled_back = recent_low <= (ema_20 + tolerance)

            if pulled_back:
                entry = current_price
                stop_loss = entry - stop_distance
                take_profit = entry + (stop_distance * self.rr_ratio)

                signal = {
                    'pair': pair,
                    'direction': 'buy',
                    'confidence': 0.65,
                    'entry_price': entry,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'strategy': self.name,
                    'session': 'ny_overlap',
                    'metadata': {
                        'london_move_pips': london_move_pips,
                        'ema_20': ema_20,
                        'atr_pips': atr_pips,
                        'rr_ratio': self.rr_ratio,
                    },
                }

        # SELL: London bearish, price below EMA(20), recent pullback touched EMA
        elif not london_bullish and current_price < ema_20:
            recent_high = max(highs[-4:])
            pulled_back = recent_high >= (ema_20 - tolerance)

            if pulled_back:
                entry = current_price
                stop_loss = entry + stop_distance
                take_profit = entry - (stop_distance * self.rr_ratio)

                signal = {
                    'pair': pair,
                    'direction': 'sell',
                    'confidence': 0.65,
                    'entry_price': entry,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'strategy': self.name,
                    'session': 'ny_overlap',
                    'metadata': {
                        'london_move_pips': london_move_pips,
                        'ema_20': ema_20,
                        'atr_pips': atr_pips,
                        'rr_ratio': self.rr_ratio,
                    },
                }

        if signal:
            if pair not in self._daily_traded:
                self._daily_traded[pair] = {}
            self._daily_traded[pair][today] = True

        return signal

    def _ema(self, values: list, period: int):
        if len(values) < period:
            return None
        multiplier = 2 / (period + 1)
        ema = sum(values[:period]) / period
        for v in values[period:]:
            ema = (v - ema) * multiplier + ema
        return ema

    def _atr(self, candles: list, period: int):
        if len(candles) < period + 1:
            return None
        trs = []
        for i in range(1, len(candles)):
            tr = max(
                float(candles[i].high) - float(candles[i].low),
                abs(float(candles[i].high) - float(candles[i - 1].close)),
                abs(float(candles[i].low) - float(candles[i - 1].close)),
            )
            trs.append(tr)
        return sum(trs[-period:]) / period

    def reset_daily(self):
        """Call at end of each trading day."""
        self._daily_london_open = {}
        self._daily_traded = {}
