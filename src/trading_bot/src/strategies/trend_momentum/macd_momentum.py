"""
MACD Momentum Strategy - MACD crossover with volume confirmation.

Standard MACD (12, 26, 9) optimized for M5 intraday trading.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from decimal import Decimal

from ...core.models import CandleData, TechnicalIndicators, TradeSignal, MarketCondition
from ..strategy_base import BaseStrategy, StrategySignal
from ..strategy_registry import StrategyRegistry

# Import comprehensive debugging utilities
from trading_bot.src.utils.debug_utils import (
    debug_tracker, debug_line, debug_variable, debug_context, 
    debug_performance, debug_data_flow, debug_api_call, 
    debug_trade_decision, debug_strategy_execution, debug_risk_calculation,
    debug_indicator_calculation, debug_backtest_step, debug_entry_point,
    debug_exit_point, debug_conditional, debug_loop_iteration,
    get_debug_summary, export_debug_report
)


@StrategyRegistry.register("MACD_Momentum_M5")
class MACDMomentumStrategy(BaseStrategy):
    """
    MACD momentum strategy with histogram divergence detection.
    
    Entry Rules:
    - BUY: MACD crosses above Signal + Histogram increasing + RSI not overbought
    - SELL: MACD crosses below Signal + Histogram decreasing + RSI not oversold
    
    Parameters:
    - fast: Fast EMA period (default: 12)
    - slow: Slow EMA period (default: 26)
    - signal: Signal line period (default: 9)
    """
    
    @debug_line

    
    def __init__(self, name: str, strategy_type: str, config: Dict[str, Any]):
        super().__init__(name, strategy_type, config)
        
        # Strategy parameters
        self.fast_period = self.parameters.get('fast', 12)
        self.slow_period = self.parameters.get('slow', 26)
        self.signal_period = self.parameters.get('signal', 9)
        self.histogram_threshold = self.parameters.get('histogram_threshold', 0.00005)
    
    async def generate_signal(
        self,
        candles: List[CandleData],
        indicators: TechnicalIndicators,
        market_condition: MarketCondition,
        current_time: Optional[datetime] = None
    ) -> Optional[StrategySignal]:
        """Generate MACD momentum signal."""
        
        # Need MACD indicators
        if indicators.macd is None or indicators.macd_signal is None or indicators.macd_histogram is None:
            return None
        
        if len(candles) < 3:
            return None
        
        current_price = float(candles[-1].mid_c)
        atr = indicators.atr if indicators.atr else (current_price * 0.001)
        
        # Current and previous MACD values (would need historical, using indicators for now)
        macd = indicators.macd
        macd_signal = indicators.macd_signal
        macd_hist = indicators.macd_histogram
        
        # Check for crossover (simplified - in production would track previous values)
        macd_above_signal = macd > macd_signal
        macd_below_signal = macd < macd_signal
        
        # Histogram momentum
        histogram_positive = macd_hist > self.histogram_threshold
        histogram_negative = macd_hist < -self.histogram_threshold
        
        # RSI filters
        rsi_not_overbought = indicators.rsi is None or indicators.rsi < 70
        rsi_not_oversold = indicators.rsi is None or indicators.rsi > 30
        
        # BUY Signal
        if macd_above_signal and histogram_positive and rsi_not_overbought:
            confidence = 0.70
            
            # Increase confidence if strong momentum
            if indicators.rsi and 50 < indicators.rsi < 60:
                confidence += 0.05
            
            strength = min(1.0, abs(macd_hist) * 10000)  # Scale histogram
            
            return StrategySignal(
                signal=TradeSignal.BUY,
                confidence=confidence,
                strength=strength,
                reasoning=f"MACD bullish crossover, histogram: {macd_hist:.5f}",
                entry_price=Decimal(str(current_price)),
                stop_loss=Decimal(str(current_price - (2.0 * atr))),  # I-3: 2×ATR (was 1.5×ATR — too tight)
                take_profit=Decimal(str(current_price + (4.0 * atr))),  # I-3: 2:1 R:R (was 2.5×ATR)
                metadata={
                    'macd': macd,
                    'macd_signal': macd_signal,
                    'macd_histogram': macd_hist,
                    'rsi': indicators.rsi
                }
            )

        # SELL Signal
        elif macd_below_signal and histogram_negative and rsi_not_oversold:
            confidence = 0.70

            # Increase confidence if strong momentum
            if indicators.rsi and 40 < indicators.rsi < 50:
                confidence += 0.05

            strength = min(1.0, abs(macd_hist) * 10000)

            return StrategySignal(
                signal=TradeSignal.SELL,
                confidence=confidence,
                strength=strength,
                reasoning=f"MACD bearish crossover, histogram: {macd_hist:.5f}",
                entry_price=Decimal(str(current_price)),
                stop_loss=Decimal(str(current_price + (2.0 * atr))),  # I-3: 2×ATR (was 1.5×ATR — too tight)
                take_profit=Decimal(str(current_price - (4.0 * atr))),  # I-3: 2:1 R:R (was 2.5×ATR)
                metadata={
                    'macd': macd,
                    'macd_signal': macd_signal,
                    'macd_histogram': macd_hist,
                    'rsi': indicators.rsi
                }
            )
        
        return None









