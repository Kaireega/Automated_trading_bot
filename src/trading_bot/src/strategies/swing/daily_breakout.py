"""
Daily Breakout Strategy — A-2 Strategy Overhaul
================================================
Entry:  Price breaks above yesterday's high (BUY) or below yesterday's low (SELL)
        on the H4 timeframe, with D1 EMA(50) slope confirming direction.
Stop:   Other side of yesterday's range — a structural level, not ATR multiple.
TP:     1.5× the stop distance (R:R = 1.5:1).
Filter: D1 EMA(50) slope must agree with breakout direction.
        Range filter: skip if yesterday's range < 40 pips (consolidation)
                      or > 200 pips (news spike).

Runs ONLY in TRENDING regime.

Edge: Institutional stops cluster above/below prior day extremes.
When price breaks these levels, triggered stops create directional momentum.
This is documented in Opening Range Breakout literature (Crabel 1990).
"""
from decimal import Decimal
from typing import List, Optional

from trading_bot.src.core.models import CandleData, TradeRecommendation, TradeSignal
from trading_bot.src.utils.logger import get_logger


class DailyBreakoutStrategy:
    """Break of prior day's high/low with D1 trend confirmation."""

    def __init__(self, config=None):
        self.config = config
        self.name = "Daily_Breakout"
        self.strategy_type = "trend"
        self.breakout_buffer_pips = 5    # require X pips beyond the prior day level
        self.min_range_pips = 40         # skip if yesterday's range < 40 pips (consolidation)
        self.max_range_pips = 200        # skip if yesterday's range > 200 pips (news spike)
        self.rr_ratio = 1.5              # R:R — structural stop → 1.5× TP
        self.allocation = 100            # required by StrategyManager compatibility
        self.logger = get_logger(__name__)

    async def generate_signal(
        self,
        d1_candles: List[CandleData],
        h4_candles: List[CandleData],
        m15_candles: Optional[List[CandleData]] = None,
        pair: str = "",
        **kwargs,
    ) -> Optional[TradeRecommendation]:
        """
        Generate a breakout signal based on prior day's high/low.
        Returns TradeRecommendation or None.
        """
        if not d1_candles or len(d1_candles) < 52:
            return None  # need 52 D1 candles for EMA(50) with 2 spare
        if not h4_candles or len(h4_candles) < 2:
            return None

        pip_size = 0.01 if 'JPY' in pair else 0.0001

        # Yesterday = last COMPLETED D1 candle (index -1)
        yesterday = d1_candles[-1]
        prev_high = float(yesterday.high)
        prev_low = float(yesterday.low)
        prev_range = prev_high - prev_low
        range_pips = prev_range / pip_size

        # Skip if range is too narrow (consolidation) or too wide (news spike)
        if range_pips < self.min_range_pips or range_pips > self.max_range_pips:
            self.logger.debug(
                f"{pair}: Breakout skipped — range {range_pips:.0f} pips outside "
                f"[{self.min_range_pips}, {self.max_range_pips}]"
            )
            return None

        # D1 EMA(50) slope — is the trend up or down?
        d1_closes = [float(c.close) for c in d1_candles]
        ema_now = self._ema(d1_closes, 50)
        ema_5d_ago = self._ema(d1_closes[:-5], 50)
        if ema_now is None or ema_5d_ago is None:
            return None
        ema_slope_up = ema_now > ema_5d_ago

        # Current price = latest H4 close
        current_price = float(h4_candles[-1].close)
        buffer = self.breakout_buffer_pips * pip_size

        # BUY: price broke above yesterday's high AND D1 EMA sloping up
        if current_price > (prev_high + buffer) and ema_slope_up:
            stop_loss = prev_low
            stop_distance = current_price - stop_loss
            if stop_distance <= 0:
                return None
            take_profit = current_price + (stop_distance * self.rr_ratio)

            self.logger.info(
                f"{pair}: BUY breakout — prev_high={prev_high:.5f}, "
                f"entry={current_price:.5f}, SL={stop_loss:.5f}, "
                f"TP={take_profit:.5f}, range={range_pips:.0f}pips"
            )
            return TradeRecommendation(
                pair=pair,
                signal=TradeSignal.BUY,
                confidence=0.70,
                entry_price=Decimal(str(current_price)),
                stop_loss=Decimal(str(stop_loss)),
                take_profit=Decimal(str(take_profit)),
                reasoning=(
                    f"Daily Breakout BUY: price {current_price:.5f} broke above "
                    f"prev_high {prev_high:.5f} (range {range_pips:.0f}pips, EMA sloping up)"
                ),
                metadata={
                    'strategy': self.name,
                    'regime': 'TRENDING',
                    'prev_high': prev_high,
                    'prev_low': prev_low,
                    'range_pips': range_pips,
                    'ema_50': ema_now,
                    'r_r_ratio': self.rr_ratio,
                },
            )

        # SELL: price broke below yesterday's low AND D1 EMA sloping down
        elif current_price < (prev_low - buffer) and not ema_slope_up:
            stop_loss = prev_high
            stop_distance = stop_loss - current_price
            if stop_distance <= 0:
                return None
            take_profit = current_price - (stop_distance * self.rr_ratio)

            self.logger.info(
                f"{pair}: SELL breakout — prev_low={prev_low:.5f}, "
                f"entry={current_price:.5f}, SL={stop_loss:.5f}, "
                f"TP={take_profit:.5f}, range={range_pips:.0f}pips"
            )
            return TradeRecommendation(
                pair=pair,
                signal=TradeSignal.SELL,
                confidence=0.70,
                entry_price=Decimal(str(current_price)),
                stop_loss=Decimal(str(stop_loss)),
                take_profit=Decimal(str(take_profit)),
                reasoning=(
                    f"Daily Breakout SELL: price {current_price:.5f} broke below "
                    f"prev_low {prev_low:.5f} (range {range_pips:.0f}pips, EMA sloping down)"
                ),
                metadata={
                    'strategy': self.name,
                    'regime': 'TRENDING',
                    'prev_high': prev_high,
                    'prev_low': prev_low,
                    'range_pips': range_pips,
                    'ema_50': ema_now,
                    'r_r_ratio': self.rr_ratio,
                },
            )

        return None

    # ── Indicator helpers ──────────────────────────────────────────────────────

    def _ema(self, closes: List[float], period: int) -> Optional[float]:
        if len(closes) < period:
            return None
        multiplier = 2 / (period + 1)
        ema = sum(closes[:period]) / period
        for price in closes[period:]:
            ema = (price - ema) * multiplier + ema
        return ema
