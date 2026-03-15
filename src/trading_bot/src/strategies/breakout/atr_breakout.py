"""
ATR Breakout Strategy - Volatility-based breakout trades.

Enters when price breaks out by a multiple of ATR.
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


@StrategyRegistry.register("ATR_Breakout")
class ATRBreakoutStrategy(BaseStrategy):
    """
    ATR-based volatility breakout strategy.
    
    Entry Rules:
    - BUY: Price breaks above recent high by ATR_multiplier * ATR
    - SELL: Price breaks below recent low by ATR_multiplier * ATR
    
    Parameters:
    - atr_period: ATR calculation period (default: 14)
    - multiplier: ATR multiplier for breakout (default: 1.5)
    - lookback: Lookback period for high/low (default: 20)
    """
    
    @debug_line

    
    def __init__(self, name: str, strategy_type: str, config: Dict[str, Any]):
        super().__init__(name, strategy_type, config)
        
        # Strategy parameters
        self.atr_period = self.parameters.get('atr_period', 14)
        self.multiplier = self.parameters.get('multiplier', 1.5)
        self.lookback = self.parameters.get('lookback', 20)
    
    async def generate_signal(
        self,
        candles: List[CandleData],
        indicators: TechnicalIndicators,
        market_condition: MarketCondition,
        current_time: Optional[datetime] = None
    ) -> Optional[StrategySignal]:
        """Generate ATR breakout signal."""
        
        if len(candles) < max(self.atr_period, self.lookback) + 5:
            return None
        
        current_price = float(candles[-1].mid_c)
        
        # Get ATR
        atr = indicators.atr if indicators.atr else (current_price * 0.001)
        
        # Calculate recent high/low
        recent_candles = candles[-self.lookback:-1]  # Exclude current candle
        recent_high = max(float(c.mid_h) for c in recent_candles)
        recent_low = min(float(c.mid_l) for c in recent_candles)
        
        # Breakout thresholds
        breakout_high = recent_high + (self.multiplier * atr)
        breakout_low = recent_low - (self.multiplier * atr)
        
        # BUY Signal: Bullish breakout
        if current_price > breakout_high:
            # Check volume confirmation if available
            volume_confirmed = True
            if len(candles) >= 2:
                current_volume = candles[-1].volume if hasattr(candles[-1], 'volume') else 0
                prev_volume = candles[-2].volume if hasattr(candles[-2], 'volume') else 0
                if current_volume and prev_volume:
                    volume_confirmed = current_volume > prev_volume
            
            confidence = 0.70
            if volume_confirmed:
                confidence += 0.05
            
            # Strength based on how far above breakout level
            breakout_strength = (current_price - breakout_high) / atr
            strength = min(1.0, breakout_strength)
            
            return StrategySignal(
                signal=TradeSignal.BUY,
                confidence=confidence,
                strength=strength,
                reasoning=f"ATR breakout above {breakout_high:.5f}, ATR={atr:.5f}",
                entry_price=Decimal(str(current_price)),
                stop_loss=Decimal(str(current_price - (2.0 * atr))),  # I-9: 2×ATR below entry (was 0.5×ATR below recent_high — too tight)
                take_profit=Decimal(str(current_price + (4.0 * atr))),  # 2:1 R:R
                metadata={
                    'breakout_level': breakout_high,
                    'recent_high': recent_high,
                    'atr': atr,
                    'multiplier': self.multiplier
                }
            )
        
        # SELL Signal: Bearish breakout
        elif current_price < breakout_low:
            # Check volume confirmation if available
            volume_confirmed = True
            if len(candles) >= 2:
                current_volume = candles[-1].volume if hasattr(candles[-1], 'volume') else 0
                prev_volume = candles[-2].volume if hasattr(candles[-2], 'volume') else 0
                if current_volume and prev_volume:
                    volume_confirmed = current_volume > prev_volume
            
            confidence = 0.70
            if volume_confirmed:
                confidence += 0.05
            
            # Strength based on how far below breakout level
            breakout_strength = (breakout_low - current_price) / atr
            strength = min(1.0, breakout_strength)
            
            return StrategySignal(
                signal=TradeSignal.SELL,
                confidence=confidence,
                strength=strength,
                reasoning=f"ATR breakout below {breakout_low:.5f}, ATR={atr:.5f}",
                entry_price=Decimal(str(current_price)),
                stop_loss=Decimal(str(current_price + (2.0 * atr))),  # I-9: 2×ATR above entry (was 0.5×ATR above recent_low — too tight)
                take_profit=Decimal(str(current_price - (4.0 * atr))),  # 2:1 R:R
                metadata={
                    'breakout_level': breakout_low,
                    'recent_low': recent_low,
                    'atr': atr,
                    'multiplier': self.multiplier
                }
            )
        
        return None









