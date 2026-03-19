"""
D1 Market Regime Detector — A-4 Strategy Overhaul
====================================================
Detects market regime (TRENDING_UP / TRENDING_DOWN / RANGING) from D1 candle data.

Key improvement over old system:
- Old: ADX > 25 threshold fires when trend is 60-70% done
- New: ADX SLOPE (rising 3+ days) catches trends 2-5 days earlier
- Old: ran on H4/H1 candles with arbitrary volatility metrics
- New: runs on D1 only — regime is a daily-level question, not hourly
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from ..core.models import CandleData, MarketCondition
from ..utils.config import Config
from ..utils.logger import get_logger


class MarketRegimeDetector:
    """
    Classifies the current market regime from D1 candle data.

    Returns TRENDING_UP, TRENDING_DOWN, or RANGING — nothing else.
    Simpler outputs → simpler downstream logic.
    """

    def __init__(self, config: Config = None):
        self.config = config
        self.logger = get_logger(__name__)
        self.ema_period = 50
        self.adx_period = 14
        self.adx_slope_lookback = 3    # ADX must be rising for this many days to call a trend

    # ── Public interface (called by main.py and backtest_engine) ──────────────

    async def start(self) -> None:
        self.logger.info("Market regime detector started (D1 ADX-slope mode)")

    async def stop(self) -> None:
        self.logger.info("Market regime detector stopped")

    async def detect_regime(
        self,
        pair: str,
        candles: List[CandleData],           # D1 candles (primary)
        market_context=None,                  # kept for interface compatibility — not used
        technical_indicators=None,            # kept for interface compatibility — not used
        candles_by_tf: Optional[Dict] = None, # alternative: pass full tf dict
    ) -> Dict[str, Any]:
        """
        Detect current market regime. Primary input is D1 candles.
        Falls back gracefully if not enough data.
        """
        # Resolve D1 candles — accept either direct list or dict by timeframe
        from ..core.models import TimeFrame
        d1_candles = candles
        if candles_by_tf:
            d1_candles = (
                candles_by_tf.get(TimeFrame.D1)
                or candles_by_tf.get('D1')
                or candles
            )

        regime = self._detect_regime_from_d1(d1_candles)
        self.logger.info(f"{pair}: D1 regime = {regime.value}")

        return {
            'regime': regime.value.upper(),
            'market_condition': regime,
            'confidence': 0.75,
            'detection_timestamp': datetime.now(timezone.utc),
        }

    def detect_regime_sync(self, d1_candles: List[CandleData]) -> MarketCondition:
        """Synchronous version for backtest engine use."""
        return self._detect_regime_from_d1(d1_candles)

    # ── Core detection logic ──────────────────────────────────────────────────

    def _detect_regime_from_d1(self, d1_candles: List[CandleData]) -> MarketCondition:
        """
        Classify regime from D1 candles.

        Logic:
        1. D1 EMA(50) — are we in an uptrend or downtrend? (price consistently above/below)
        2. ADX slope (3 days) — is the trend gaining or losing strength?
        3. If ADX rising OR ADX > 20, AND price consistently on one side → TRENDING
           But if ADX falling from > 30 → skip (trend exhaustion)
        4. Otherwise → RANGING
        """
        if not d1_candles or len(d1_candles) < self.ema_period + self.adx_slope_lookback + 1:
            self.logger.debug("Not enough D1 candles for regime detection — defaulting to RANGING")
            return MarketCondition.RANGING

        closes = [float(c.close) for c in d1_candles]
        current_price = closes[-1]

        # D1 EMA(50)
        ema = self._ema(closes, self.ema_period)
        if ema is None:
            return MarketCondition.RANGING

        # How many of the last 5 closes are consistently on the same side of EMA?
        price_above_ema = current_price > ema
        consistent_side = sum(
            1 for c in closes[-5:] if (c > ema) == price_above_ema
        )

        # ADX values for the last (slope_lookback + 1) days
        adx_values = self._adx_series(d1_candles, self.adx_period, lookback=self.adx_slope_lookback + 1)
        if not adx_values or len(adx_values) < 2:
            # Can't compute ADX slope — fall back to EMA position only
            if consistent_side >= 4:
                return MarketCondition.TRENDING_UP if price_above_ema else MarketCondition.TRENDING_DOWN
            return MarketCondition.RANGING

        current_adx = adx_values[-1]
        adx_rising = all(adx_values[i] < adx_values[i + 1] for i in range(len(adx_values) - 1))
        adx_falling = all(adx_values[i] > adx_values[i + 1] for i in range(len(adx_values) - 1))

        # Trend exhaustion: ADX falling from high levels → skip (don't enter late)
        if adx_falling and current_adx > 30:
            self.logger.debug(f"ADX falling from {current_adx:.1f} — trend exhausting, RANGING")
            return MarketCondition.RANGING

        # TRENDING: price consistently on one side of EMA AND (ADX rising OR ADX > 20)
        is_trending = consistent_side >= 4 and (adx_rising or current_adx > 20)

        if is_trending:
            return MarketCondition.TRENDING_UP if price_above_ema else MarketCondition.TRENDING_DOWN

        return MarketCondition.RANGING

    # ── Indicator calculations ────────────────────────────────────────────────

    def _ema(self, values: List[float], period: int) -> Optional[float]:
        if len(values) < period:
            return None
        multiplier = 2 / (period + 1)
        ema = sum(values[:period]) / period
        for v in values[period:]:
            ema = (v - ema) * multiplier + ema
        return ema

    def _adx_series(self, candles: List[CandleData], period: int, lookback: int) -> Optional[List[float]]:
        """
        Calculate ADX for each of the last `lookback` candles.
        Returns a list of ADX values in chronological order.
        """
        # Need enough candles: period warmup + lookback
        if len(candles) < period * 2 + lookback:
            return None

        results = []
        for offset in range(lookback - 1, -1, -1):
            end_idx = len(candles) - offset
            adx = self._calculate_adx(candles[:end_idx], period)
            if adx is not None:
                results.append(adx)

        return results if results else None

    def _calculate_adx(self, candles: List[CandleData], period: int) -> Optional[float]:
        """Wilder's ADX from a candle list."""
        if len(candles) < period * 2:
            return None

        tr_list, plus_dm_list, minus_dm_list = [], [], []

        for i in range(1, len(candles)):
            high = float(candles[i].high)
            low = float(candles[i].low)
            prev_close = float(candles[i - 1].close)
            prev_high = float(candles[i - 1].high)
            prev_low = float(candles[i - 1].low)

            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            up_move = high - prev_high
            down_move = prev_low - low

            plus_dm = up_move if up_move > down_move and up_move > 0 else 0
            minus_dm = down_move if down_move > up_move and down_move > 0 else 0

            tr_list.append(tr)
            plus_dm_list.append(plus_dm)
            minus_dm_list.append(minus_dm)

        # Wilder smoothing initialisation
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

        # Wilder smooth the DX values into ADX
        adx = sum(dx_list[:period]) / period
        for i in range(period, len(dx_list)):
            adx = (adx * (period - 1) + dx_list[i]) / period

        return adx
