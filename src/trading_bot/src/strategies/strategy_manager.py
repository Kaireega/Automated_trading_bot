"""
Strategy Manager — A-5 Strategy Overhaul
==========================================
Hard regime switch. Two strategies. No voting. No consensus. No weights.

Old system: 9 correlated strategies voting in weighted ensemble.
New system:
    D1 regime → TRENDING → DailyBreakoutStrategy
    D1 regime → RANGING  → StructureReversalStrategy
    M15 pullback gate refines entry timing (A-6).
"""
from datetime import datetime
from typing import Dict, List, Optional, Any

from ..core.models import (
    CandleData, TradeSignal, MarketCondition, TradeRecommendation, TimeFrame
)
from ..utils.config import Config
from ..utils.logger import get_logger
from ..core.market_regime_detector import MarketRegimeDetector
from .swing.daily_breakout import DailyBreakoutStrategy
from .swing.structure_reversal import StructureReversalStrategy


class StrategyManager:
    """
    Selects and runs one strategy based on D1 market regime.
    Replaces the 9-strategy weighted consensus system.
    """

    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger(__name__)

        self.regime_detector = MarketRegimeDetector(config)
        self.daily_breakout = DailyBreakoutStrategy(config)
        self.structure_reversal = StructureReversalStrategy(config)

        # M15 pullback gate — can be disabled if rejection rate > 50%
        self.m15_pullback_enabled = True
        self.m15_pullback_ema_period = 20
        self.m15_pullback_tolerance_pips = 3

        # Compatibility fields (used by some callers)
        self.enabled = True
        self.strategies = [self.daily_breakout, self.structure_reversal]
        self.strategy_performance: Dict[str, Dict[str, Any]] = {
            'Daily_Breakout': {'signals_generated': 0, 'signals_accepted': 0,
                               'win_count': 0, 'loss_count': 0, 'total_pnl': 0.0},
            'Structure_Reversal': {'signals_generated': 0, 'signals_accepted': 0,
                                   'win_count': 0, 'loss_count': 0, 'total_pnl': 0.0},
        }

    # ── Public interface ───────────────────────────────────────────────────────

    async def generate_signal(
        self,
        pair: str,
        candles_by_tf: Dict,
        market_context=None,
        current_time: Optional[datetime] = None,
        **kwargs,
    ) -> Optional[TradeRecommendation]:
        """
        Hard regime switch — run ONE strategy based on D1 regime.
        No voting. No consensus. No weighted confidence.
        """
        # ── Time filters ───────────────────────────────────────────────────────
        if current_time is not None:
            # Weekend filter
            if current_time.weekday() in (5, 6):
                self.logger.debug(f"{pair}: Weekend — skipping")
                return None

            # Session-close dead zone (21:00–22:00 UTC = daily candle rollover)
            if current_time.hour in {21}:
                self.logger.debug(f"{pair}: 21:00 UTC dead zone — skipping")
                return None

        # ── Resolve candles by timeframe ───────────────────────────────────────
        d1_candles = self._get_candles(candles_by_tf, TimeFrame.D1, 'D1')
        h4_candles = self._get_candles(candles_by_tf, TimeFrame.H4, 'H4')
        m15_candles = self._get_candles(candles_by_tf, TimeFrame.M15, 'M15')

        if not d1_candles or not h4_candles:
            self.logger.debug(f"{pair}: Missing D1 or H4 candles — no signal")
            return None

        # ── Step 1: Detect regime from D1 ─────────────────────────────────────
        regime = self.regime_detector.detect_regime_sync(d1_candles)
        self.logger.info(f"{pair}: D1 regime = {regime.value}")

        # ── Step 2: Select and run ONE strategy ───────────────────────────────
        signal = None

        if regime in (MarketCondition.TRENDING_UP, MarketCondition.TRENDING_DOWN):
            signal = await self.daily_breakout.generate_signal(
                d1_candles=d1_candles,
                h4_candles=h4_candles,
                m15_candles=m15_candles,
                pair=pair,
            )
            if signal:
                self.strategy_performance['Daily_Breakout']['signals_generated'] += 1
                self.logger.info(f"{pair}: Daily Breakout → {signal.signal.value}")

        elif regime == MarketCondition.RANGING:
            signal = await self.structure_reversal.generate_signal(
                d1_candles=d1_candles,
                h4_candles=h4_candles,
                m15_candles=m15_candles,
                pair=pair,
            )
            if signal:
                self.strategy_performance['Structure_Reversal']['signals_generated'] += 1
                self.logger.info(f"{pair}: Structure Reversal → {signal.signal.value}")

        else:
            self.logger.info(f"{pair}: Regime UNKNOWN — no trade")
            return None

        if not signal:
            return None

        # ── Step 3: M15 pullback entry gate (A-6) ─────────────────────────────
        if self.m15_pullback_enabled and m15_candles and len(m15_candles) >= 21:
            direction = 'buy' if signal.signal == TradeSignal.BUY else 'sell'
            if not self._m15_pullback_confirms(direction, m15_candles, pair):
                self.logger.info(
                    f"{pair}: Signal valid but M15 pullback not aligned — waiting for better entry"
                )
                return None

        return signal

    async def generate_consensus_signal(
        self,
        pair: str,
        candles: List[CandleData],
        indicators=None,
        market_condition: MarketCondition = MarketCondition.UNKNOWN,
        current_time: Optional[datetime] = None,
        regime: Optional[str] = None,
        candles_by_tf: Optional[Dict] = None,
        **kwargs,
    ) -> Optional[TradeRecommendation]:
        """
        Compatibility shim — old callers used generate_consensus_signal().
        Routes to the new generate_signal() method.
        """
        # Build candles_by_tf from the primary candle list if not provided
        tf_dict = candles_by_tf or {}
        if candles and not tf_dict:
            tf_dict = {TimeFrame.H4: candles}

        return await self.generate_signal(
            pair=pair,
            candles_by_tf=tf_dict,
            market_context=None,
            current_time=current_time,
        )

    def get_strategy_count(self) -> int:
        return len(self.strategies)

    def get_strategy_performance(self) -> Dict[str, Dict[str, Any]]:
        return self.strategy_performance.copy()

    def update_strategy_performance(self, strategy_name: str, won: bool, pnl: float):
        if strategy_name in self.strategy_performance:
            perf = self.strategy_performance[strategy_name]
            perf['signals_accepted'] += 1
            if won:
                perf['win_count'] += 1
            else:
                perf['loss_count'] += 1
            perf['total_pnl'] += pnl

    # ── M15 pullback entry gate (A-6) ─────────────────────────────────────────

    def _m15_pullback_confirms(
        self,
        direction: str,
        m15_candles: List[CandleData],
        pair: str = "",
    ) -> bool:
        """
        Check if M15 price has pulled back to the 20 EMA.
        Better entry price than chasing the breakout.

        BUY:  M15 price touched or came within 3 pips of EMA20 from above,
              and the last candle closed above EMA20 (bounce = entry).
        SELL: Mirror logic.

        Returns True (allow trade) or False (wait for pullback).
        If EMA can't be calculated, returns True (don't block the trade).
        """
        closes = [float(c.close) for c in m15_candles]
        ema_20 = self._ema(closes, self.m15_pullback_ema_period)
        if ema_20 is None:
            return True  # can't calculate → don't block

        current_close = closes[-1]
        pip_size = 0.01 if 'JPY' in pair else 0.0001
        tolerance = self.m15_pullback_tolerance_pips * pip_size

        if direction == 'buy':
            # Price touched near or below EMA in last 4 candles (pullback)
            near_ema = min(float(c.low) for c in m15_candles[-4:]) <= (ema_20 + tolerance)
            # Last close is above EMA (bounce confirmed)
            closed_above = current_close > ema_20
            result = near_ema and closed_above
            self.logger.debug(
                f"{pair}: M15 BUY pullback check — near_ema={near_ema}, "
                f"closed_above={closed_above}, ema={ema_20:.5f}, price={current_close:.5f}"
            )
            return result

        elif direction == 'sell':
            near_ema = max(float(c.high) for c in m15_candles[-4:]) >= (ema_20 - tolerance)
            closed_below = current_close < ema_20
            result = near_ema and closed_below
            self.logger.debug(
                f"{pair}: M15 SELL pullback check — near_ema={near_ema}, "
                f"closed_below={closed_below}, ema={ema_20:.5f}, price={current_close:.5f}"
            )
            return result

        return True

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_candles(
        self,
        candles_by_tf: Dict,
        tf_enum: TimeFrame,
        tf_str: str,
    ) -> Optional[List[CandleData]]:
        """Resolve candles from dict — accepts both TimeFrame enum and string keys."""
        return (
            candles_by_tf.get(tf_enum)
            or candles_by_tf.get(tf_str)
            or candles_by_tf.get(tf_enum.value if hasattr(tf_enum, 'value') else tf_str)
        )

    def _ema(self, values: List[float], period: int):
        if len(values) < period:
            return None
        multiplier = 2 / (period + 1)
        ema = sum(values[:period]) / period
        for v in values[period:]:
            ema = (v - ema) * multiplier + ema
        return ema
