"""
London Open ORB (Opening Range Breakout)
==========================================
Edge: The first 30 minutes of London (07:00–07:30 GMT) establish an "opening
range" driven by the initial wave of European institutional orders. When price
breaks this range convincingly (M5 candle CLOSE, not just a wick), it tends
to follow through because the breakout represents genuine directional
commitment from the largest market participants.

Rules:
1. Mark the HIGH and LOW from 07:00–07:30 GMT (first 6 M5 candles)
2. After 07:30, if an M5 candle CLOSES above the range high → BUY
3. After 07:30, if an M5 candle CLOSES below the range low → SELL
4. Stop: opposite side of the opening range (structural)
5. TP: 1.5× stop distance (R:R = 1.5:1)
6. Close by 12:00 GMT if neither TP nor SL hit

Filters:
- Opening range must be 8–25 pips (skip too tight or too wide)
- Skip if Asian Range Breakout already triggered for this pair today
  (avoid doubling up on the same directional move)
- Skip Mondays before 08:00 (weekend gap noise)
- One ORB trade per pair per day maximum

Primary: EUR_USD (tighter spreads during London open)
"""

from datetime import datetime, time
from typing import Optional, List


class LondonORBStrategy:

    def __init__(self, config=None):
        self.name = "London_ORB"
        self.orb_start = time(7, 0)          # 07:00 GMT
        self.orb_end = time(7, 30)           # 07:30 GMT (end of range formation)
        self.trade_window_end = time(12, 0)  # no trades after noon
        self.min_range_pips = 8
        self.max_range_pips = 25
        self.rr_ratio = 1.5
        self._daily_orb = {}                 # pair -> {date: orb_data}

    def mark_opening_range(self, pair: str, candles: list, current_time: datetime):
        """
        Record the 07:00–07:30 GMT opening range from M5 candles.
        Call this once after 07:30 GMT.
        """
        today = current_time.date()

        orb_candles = [
            c for c in candles
            if hasattr(c, 'timestamp') and
               c.timestamp.date() == today and
               self.orb_start <= c.timestamp.time() < self.orb_end
        ]

        if not orb_candles or len(orb_candles) < 3:
            return

        orb_high = max(float(c.high) for c in orb_candles)
        orb_low = min(float(c.low) for c in orb_candles)
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
        m5_candles: list,
        current_time: datetime,
        asian_breakout_triggered: bool = False,
        **kwargs
    ) -> Optional[dict]:
        """
        Check for ORB breakout. Requires M5 candle CLOSE beyond the range.
        Call this on every M5 candle after 07:30 GMT.
        """
        today = current_time.date()

        if pair not in self._daily_orb or today not in self._daily_orb[pair]:
            return None

        orb = self._daily_orb[pair][today]

        if orb['traded']:
            return None

        if orb['range_pips'] < self.min_range_pips or orb['range_pips'] > self.max_range_pips:
            return None

        # Asian Range Breakout already fired — don't double up
        if asian_breakout_triggered:
            return None

        # Must be past ORB formation period
        if current_time.time() < self.orb_end:
            return None

        if current_time.time() >= self.trade_window_end:
            return None

        # Skip Monday before 08:00 (weekend gap noise)
        if current_time.weekday() == 0 and current_time.hour < 8:
            return None

        if not m5_candles:
            return None

        # Requires candle CLOSE beyond range (not just a wick)
        latest_close = float(m5_candles[-1].close)

        signal = None

        if latest_close > orb['high']:
            entry = latest_close
            stop_loss = orb['low']
            stop_distance = entry - stop_loss
            if stop_distance <= 0:
                return None
            take_profit = entry + (stop_distance * self.rr_ratio)

            signal = {
                'pair': pair,
                'direction': 'buy',
                'confidence': 0.70,
                'entry_price': entry,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'strategy': self.name,
                'session': 'london_open',
                'metadata': {
                    'orb_high': orb['high'],
                    'orb_low': orb['low'],
                    'range_pips': orb['range_pips'],
                    'rr_ratio': self.rr_ratio,
                },
            }
            orb['traded'] = True

        elif latest_close < orb['low']:
            entry = latest_close
            stop_loss = orb['high']
            stop_distance = stop_loss - entry
            if stop_distance <= 0:
                return None
            take_profit = entry - (stop_distance * self.rr_ratio)

            signal = {
                'pair': pair,
                'direction': 'sell',
                'confidence': 0.70,
                'entry_price': entry,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'strategy': self.name,
                'session': 'london_open',
                'metadata': {
                    'orb_high': orb['high'],
                    'orb_low': orb['low'],
                    'range_pips': orb['range_pips'],
                    'rr_ratio': self.rr_ratio,
                },
            }
            orb['traded'] = True

        return signal

    def reset_daily(self):
        """Call at end of each trading day."""
        self._daily_orb = {}
