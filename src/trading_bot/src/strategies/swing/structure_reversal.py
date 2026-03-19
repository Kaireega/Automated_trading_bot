"""
Structure Reversal Strategy — A-3 Strategy Overhaul
=====================================================
Entry:  Price touches a D1 support/resistance zone AND H4 RSI(14) is extreme
        (< 30 for BUY at support, > 70 for SELL at resistance).
Stop:   Beyond the S/R level by 0.5× H4 ATR.
TP:     Midpoint of the D1 range (1:1 to 1.5:1 R:R typically).
Filter: Only runs in RANGING regime.

Runs ONLY in RANGING regime.

Edge: D1 swing highs/lows represent areas where large orders have historically
been filled. RSI extremes at these levels signal momentum exhaustion.
The edge persists because it's driven by market microstructure (order clustering).
"""
from decimal import Decimal
from typing import List, Optional, Tuple

from trading_bot.src.core.models import CandleData, TradeRecommendation, TradeSignal
from trading_bot.src.utils.logger import get_logger


class StructureReversalStrategy:
    """Mean reversion at D1 support/resistance with H4 RSI confirmation."""

    def __init__(self, config=None):
        self.config = config
        self.name = "Structure_Reversal"
        self.strategy_type = "mean_reversion"
        self.sr_lookback = 50          # D1 candles to scan for swing highs/lows
        self.sr_zone_pips = 15         # price must be within this many pips of an S/R level
        self.swing_window = 5          # candles on each side to confirm a swing high/low
        self.rsi_period = 14
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        self.atr_period = 14
        self.min_rr = 1.0              # skip trade if R:R below this
        self.allocation = 100          # required for StrategyManager compatibility
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
        Generate a reversal signal at D1 structure levels.
        Returns TradeRecommendation or None.
        """
        if not d1_candles or len(d1_candles) < self.sr_lookback:
            return None
        if not h4_candles or len(h4_candles) < self.rsi_period + 1:
            return None

        pip_size = 0.01 if 'JPY' in pair else 0.0001
        zone_distance = self.sr_zone_pips * pip_size
        current_price = float(h4_candles[-1].close)

        # Find D1 support and resistance levels (swing highs/lows)
        supports, resistances = self._find_sr_levels(d1_candles[-self.sr_lookback:])

        # H4 RSI
        h4_closes = [float(c.close) for c in h4_candles]
        rsi = self._rsi(h4_closes, self.rsi_period)
        if rsi is None:
            return None

        # H4 ATR for stop placement
        atr = self._atr(h4_candles, self.atr_period)
        if atr is None or atr == 0:
            return None

        # Range midpoint (target for mean reversion)
        recent_high = max(float(c.high) for c in d1_candles[-20:])
        recent_low = min(float(c.low) for c in d1_candles[-20:])
        range_midpoint = (recent_high + recent_low) / 2

        # BUY: price at a support level + RSI oversold
        for support in supports:
            if abs(current_price - support) <= zone_distance and rsi < self.rsi_oversold:
                stop_loss = support - (0.5 * atr)
                take_profit = range_midpoint
                stop_distance = current_price - stop_loss
                tp_distance = take_profit - current_price

                if stop_distance <= 0 or tp_distance <= 0:
                    continue
                rr = tp_distance / stop_distance
                if rr < self.min_rr:
                    continue

                self.logger.info(
                    f"{pair}: BUY reversal — support={support:.5f}, "
                    f"entry={current_price:.5f}, RSI={rsi:.1f}, R:R={rr:.2f}"
                )
                return TradeRecommendation(
                    pair=pair,
                    signal=TradeSignal.BUY,
                    confidence=0.65,
                    entry_price=Decimal(str(current_price)),
                    stop_loss=Decimal(str(stop_loss)),
                    take_profit=Decimal(str(take_profit)),
                    reasoning=(
                        f"Structure Reversal BUY: at support {support:.5f}, "
                        f"RSI={rsi:.1f} (oversold), R:R={rr:.2f}"
                    ),
                    metadata={
                        'strategy': self.name,
                        'regime': 'RANGING',
                        'support_level': support,
                        'rsi': rsi,
                        'range_midpoint': range_midpoint,
                        'r_r_ratio': rr,
                    },
                )

        # SELL: price at a resistance level + RSI overbought
        for resistance in resistances:
            if abs(current_price - resistance) <= zone_distance and rsi > self.rsi_overbought:
                stop_loss = resistance + (0.5 * atr)
                take_profit = range_midpoint
                stop_distance = stop_loss - current_price
                tp_distance = current_price - take_profit

                if stop_distance <= 0 or tp_distance <= 0:
                    continue
                rr = tp_distance / stop_distance
                if rr < self.min_rr:
                    continue

                self.logger.info(
                    f"{pair}: SELL reversal — resistance={resistance:.5f}, "
                    f"entry={current_price:.5f}, RSI={rsi:.1f}, R:R={rr:.2f}"
                )
                return TradeRecommendation(
                    pair=pair,
                    signal=TradeSignal.SELL,
                    confidence=0.65,
                    entry_price=Decimal(str(current_price)),
                    stop_loss=Decimal(str(stop_loss)),
                    take_profit=Decimal(str(take_profit)),
                    reasoning=(
                        f"Structure Reversal SELL: at resistance {resistance:.5f}, "
                        f"RSI={rsi:.1f} (overbought), R:R={rr:.2f}"
                    ),
                    metadata={
                        'strategy': self.name,
                        'regime': 'RANGING',
                        'resistance_level': resistance,
                        'rsi': rsi,
                        'range_midpoint': range_midpoint,
                        'r_r_ratio': rr,
                    },
                )

        return None

    # ── Indicator helpers ──────────────────────────────────────────────────────

    def _find_sr_levels(self, candles: List[CandleData]) -> Tuple[List[float], List[float]]:
        """
        Find swing lows (support) and swing highs (resistance) in D1 candle data.
        A swing high: candle whose high is higher than `window` candles on each side.
        A swing low: candle whose low is lower than `window` candles on each side.
        Returns (supports[-5:], resistances[-5:]) — most recent 5 levels only.
        """
        w = self.swing_window
        supports = []
        resistances = []

        for i in range(w, len(candles) - w):
            high_i = float(candles[i].high)
            low_i = float(candles[i].low)

            is_swing_high = all(
                high_i >= float(candles[i + j].high) and
                high_i >= float(candles[i - j].high)
                for j in range(1, w + 1)
            )
            if is_swing_high:
                resistances.append(high_i)

            is_swing_low = all(
                low_i <= float(candles[i + j].low) and
                low_i <= float(candles[i - j].low)
                for j in range(1, w + 1)
            )
            if is_swing_low:
                supports.append(low_i)

        return supports[-5:], resistances[-5:]

    def _rsi(self, closes: List[float], period: int) -> Optional[float]:
        if len(closes) < period + 1:
            return None
        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]

        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def _atr(self, candles: List[CandleData], period: int) -> Optional[float]:
        if len(candles) < period + 1:
            return None
        trs = []
        for i in range(1, len(candles)):
            high = float(candles[i].high)
            low = float(candles[i].low)
            prev_close = float(candles[i - 1].close)
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            trs.append(tr)
        if len(trs) < period:
            return None
        return sum(trs[-period:]) / period
