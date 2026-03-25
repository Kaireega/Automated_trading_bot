"""
Asian Range Breakout Strategy
==============================
Edge: Asian session (00:00–07:00 GMT) creates a tight range as low-volume
trading oscillates. When London opens at 07:00, institutional order flow
breaks this range with conviction. Breakout direction tends to persist
through the London morning because it reflects real positioning, not noise.

Rules:
1. During 00:00–07:00 GMT, mark the HIGH and LOW (Asian range)
2. After 07:00 GMT, if price breaks ABOVE the range high by 5+ pips → BUY
3. After 07:00 GMT, if price breaks BELOW the range low by 5+ pips → SELL
4. Stop loss: opposite side of the Asian range (structural)
5. Take profit: 1.5× the stop distance (R:R = 1.5:1)
6. Close by 16:00 GMT regardless of P&L

Filters:
- Skip if Asian range > 40 pips (unusual overnight volatility)
- Skip if Asian range < 15 pips (too tight — no conviction in breakout)
- Only one breakout per day per pair (first break only, no re-entry)
- Trade window closes at 12:00 GMT (past that, move is likely over)

Primary: GBP_USD (strongest documented results)
Secondary: EUR_USD
"""

from datetime import datetime, time
from typing import Optional, List
from decimal import Decimal


class AsianRangeBreakoutStrategy:

    def __init__(self, config=None):
        self.name = "Asian_Range_Breakout"
        self.asian_start = time(0, 0)        # midnight GMT
        self.asian_end = time(7, 0)          # 07:00 GMT
        self.trade_window_end = time(12, 0)  # stop trading at noon
        self.breakout_buffer_pips = 5        # pips beyond range required
        self.min_range_pips = 15             # skip if range too tight
        self.max_range_pips = 40             # skip if range too wide
        self.rr_ratio = 1.5
        self._daily_ranges = {}              # pair -> {date: range_data}

    def mark_asian_range(self, pair: str, candles: list, current_time: datetime):
        """
        Record the Asian session high/low from M5 or M15 candles.
        Call this continuously during Asian session to keep range updated.
        """
        today = current_time.date()

        asian_candles = [
            c for c in candles
            if hasattr(c, 'timestamp') and
               c.timestamp.date() == today and
               self.asian_start <= c.timestamp.time() < self.asian_end
        ]

        if not asian_candles:
            return

        asian_high = max(float(c.high) for c in asian_candles)
        asian_low = min(float(c.low) for c in asian_candles)
        pip_size = 0.01 if 'JPY' in pair else 0.0001
        range_pips = (asian_high - asian_low) / pip_size

        if pair not in self._daily_ranges:
            self._daily_ranges[pair] = {}

        self._daily_ranges[pair][today] = {
            'high': asian_high,
            'low': asian_low,
            'range_pips': range_pips,
            'traded': False,
        }

    async def generate_signal(
        self,
        pair: str,
        m15_candles: list,
        current_time: datetime,
        **kwargs
    ) -> Optional[dict]:
        """
        Check if price has broken the Asian range.
        Call this on every M15 candle during London open (07:00–12:00 GMT).
        Returns a signal dict or None.
        """
        today = current_time.date()

        if pair not in self._daily_ranges or today not in self._daily_ranges[pair]:
            return None

        range_data = self._daily_ranges[pair][today]

        if range_data['traded']:
            return None

        if range_data['range_pips'] < self.min_range_pips:
            return None
        if range_data['range_pips'] > self.max_range_pips:
            return None

        if current_time.time() >= self.trade_window_end:
            return None

        if not m15_candles:
            return None

        asian_high = range_data['high']
        asian_low = range_data['low']
        pip_size = 0.01 if 'JPY' in pair else 0.0001
        buffer = self.breakout_buffer_pips * pip_size

        current_price = float(m15_candles[-1].close)
        current_high = float(m15_candles[-1].high)
        current_low = float(m15_candles[-1].low)

        signal = None

        # BUY: candle high broke above Asian high + buffer, close still above range
        if current_high > (asian_high + buffer) and current_price > asian_high:
            entry = current_price
            stop_loss = asian_low
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
                    'asian_high': asian_high,
                    'asian_low': asian_low,
                    'range_pips': range_data['range_pips'],
                    'rr_ratio': self.rr_ratio,
                },
            }
            range_data['traded'] = True

        # SELL: candle low broke below Asian low - buffer, close still below range
        elif current_low < (asian_low - buffer) and current_price < asian_low:
            entry = current_price
            stop_loss = asian_high
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
                    'asian_high': asian_high,
                    'asian_low': asian_low,
                    'range_pips': range_data['range_pips'],
                    'rr_ratio': self.rr_ratio,
                },
            }
            range_data['traded'] = True

        return signal

    def reset_daily(self):
        """Call at end of each trading day."""
        self._daily_ranges = {}
