"""
EMA Crossover Strategy - Fast EMA crosses Slow EMA with momentum confirmation.

Optimized for M5/M15 intraday trading with 8/21 EMA periods.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from decimal import Decimal
import pandas as pd

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


@StrategyRegistry.register("Fast_EMA_Cross_M5")
class EMACrossoverStrategy(BaseStrategy):
    """
    EMA crossover strategy with momentum confirmation.
    
    Entry Rules:
    - BUY: Fast EMA crosses above Slow EMA + RSI > 50 + MACD > Signal
    - SELL: Fast EMA crosses below Slow EMA + RSI < 50 + MACD < Signal
    
    Parameters:
    - ema_fast: Fast EMA period (default: 8)
    - ema_slow: Slow EMA period (default: 21)
    """
    
    @debug_line

    
    def __init__(self, name: str, strategy_type: str, config: Dict[str, Any]):
        super().__init__(name, strategy_type, config)
        
        # Strategy parameters
        self.ema_fast_period = self.parameters.get('ema_fast', 8)
        self.ema_slow_period = self.parameters.get('ema_slow', 21)
    
    async def generate_signal(
        self,
        candles: List[CandleData],
        indicators: TechnicalIndicators,
        market_condition: MarketCondition,
        current_time: Optional[datetime] = None
    ) -> Optional[StrategySignal]:
        """Generate EMA crossover signal with momentum confirmation."""
        
        if len(candles) < max(self.ema_fast_period, self.ema_slow_period) + 5:
            return None
        
        # Calculate EMAs if not provided in indicators
        df = pd.DataFrame([{
            'close': float(c.mid_c)
        } for c in candles])
        
        df['ema_fast'] = df['close'].ewm(span=self.ema_fast_period, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=self.ema_slow_period, adjust=False).mean()
        
        # Current and previous values
        ema_fast_current = df['ema_fast'].iloc[-1]
        ema_slow_current = df['ema_slow'].iloc[-1]
        ema_fast_prev = df['ema_fast'].iloc[-2]
        ema_slow_prev = df['ema_slow'].iloc[-2]
        
        current_price = float(candles[-1].mid_c)
        atr = indicators.atr if indicators.atr else (current_price * 0.001)  # Fallback to 0.1%
        
        # State-based detection — fires whenever EMAs are aligned, not just on crossover candle
        bullish_cross = ema_fast_current > ema_slow_current
        bearish_cross = ema_fast_current < ema_slow_current

        # Require minimum separation to avoid flat/tangled EMA signals
        ema_separation = abs(ema_fast_current - ema_slow_current) / ema_slow_current
        if ema_separation < 0.0002:  # Less than 2 pips separation — EMAs too close, skip
            return None
        
    
        # Momentum confirmation
        rsi_bullish = indicators.rsi is not None and indicators.rsi > 50
        rsi_bearish = indicators.rsi is not None and indicators.rsi < 50
        
        macd_bullish = (indicators.macd is not None and indicators.macd_signal is not None and 
                       indicators.macd > indicators.macd_signal)
        macd_bearish = (indicators.macd is not None and indicators.macd_signal is not None and 
                       indicators.macd < indicators.macd_signal)
        
        # BUY Signal
        if bullish_cross and rsi_bullish and macd_bullish:
            confidence = 0.70 + min(0.10, ema_separation * 50)
            strength = min(1.0, abs(ema_fast_current - ema_slow_current) / ema_slow_current * 100)
            
            return StrategySignal(
                signal=TradeSignal.BUY,
                confidence=confidence,
                strength=strength,
                reasoning=f"EMA{self.ema_fast_period}/{self.ema_slow_period} bullish crossover + momentum",
                entry_price=Decimal(str(current_price)),
                stop_loss=Decimal(str(current_price - (1.5 * atr))),
                take_profit=Decimal(str(current_price + (2.5 * atr))),
                metadata={
                    'ema_fast': ema_fast_current,
                    'ema_slow': ema_slow_current,
                    'rsi': indicators.rsi,
                    'macd': indicators.macd
                }
            )
        
        # SELL Signal
        elif bearish_cross and rsi_bearish and macd_bearish:
            confidence = 0.70 + min(0.10, ema_separation * 50)
            strength = min(1.0, abs(ema_fast_current - ema_slow_current) / ema_slow_current * 100)
            
            return StrategySignal(
                signal=TradeSignal.SELL,
                confidence=confidence,
                strength=strength,
                reasoning=f"EMA{self.ema_fast_period}/{self.ema_slow_period} bearish crossover + momentum",
                entry_price=Decimal(str(current_price)),
                stop_loss=Decimal(str(current_price + (1.5 * atr))),
                take_profit=Decimal(str(current_price - (2.5 * atr))),
                metadata={
                    'ema_fast': ema_fast_current,
                    'ema_slow': ema_slow_current,
                    'rsi': indicators.rsi,
                    'macd': indicators.macd
                }
            )
        
        return None









