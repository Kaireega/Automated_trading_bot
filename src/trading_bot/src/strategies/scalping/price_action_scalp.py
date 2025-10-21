"""
Price Action Scalp Strategy - Candle pattern scalping.

Trades pin bars, engulfing patterns, and other price action signals.
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


@StrategyRegistry.register("Price_Action_Scalp")
class PriceActionScalpStrategy(BaseStrategy):
    """
    Price action scalping strategy using candle patterns.
    
    Entry Rules:
    - BUY: Bullish pin bar or engulfing at support
    - SELL: Bearish pin bar or engulfing at resistance
    
    Parameters:
    - min_body_ratio: Minimum body-to-range ratio (default: 0.6)
    - min_wick_ratio: Minimum wick-to-body ratio for pin bars (default: 2.0)
    """
    
    @debug_line

    
    def __init__(self, name: str, strategy_type: str, config: Dict[str, Any]):
        super().__init__(name, strategy_type, config)
        
        # Strategy parameters
        self.min_body_ratio = self.parameters.get('min_body_ratio', 0.6)
        self.min_wick_ratio = self.parameters.get('min_wick_ratio', 2.0)
    
    def _detect_pin_bar(self, candle: CandleData, bullish: bool) -> bool:
        """Detect pin bar pattern."""
        high = float(candle.mid_h)
        low = float(candle.mid_l)
        open_price = float(candle.mid_o)
        close = float(candle.mid_c)
        
        body = abs(close - open_price)
        total_range = high - low
        
        if total_range == 0 or body == 0:
            return False
        
        if bullish:
            # Bullish pin bar: long lower wick, small body, close near high
            lower_wick = min(open_price, close) - low
            return lower_wick / body >= self.min_wick_ratio and close > open_price
        else:
            # Bearish pin bar: long upper wick, small body, close near low
            upper_wick = high - max(open_price, close)
            return upper_wick / body >= self.min_wick_ratio and close < open_price
    
    def _detect_engulfing(self, current: CandleData, previous: CandleData, bullish: bool) -> bool:
        """Detect engulfing pattern."""
        curr_open = float(current.mid_o)
        curr_close = float(current.mid_c)
        prev_open = float(previous.mid_o)
        prev_close = float(previous.mid_c)
        
        curr_body = abs(curr_close - curr_open)
        prev_body = abs(prev_close - prev_open)
        
        if curr_body == 0 or prev_body == 0:
            return False
        
        # Check body size requirement
        if curr_body / prev_body < 1.2:  # Current body should be at least 20% larger
            return False
        
        if bullish:
            # Bullish engulfing: previous bearish, current bullish, engulfs previous
            return (prev_close < prev_open and curr_close > curr_open and 
                    curr_close > prev_open and curr_open < prev_close)
        else:
            # Bearish engulfing: previous bullish, current bearish, engulfs previous
            return (prev_close > prev_open and curr_close < curr_open and 
                    curr_close < prev_open and curr_open > prev_close)
    
    async def generate_signal(
        self,
        candles: List[CandleData],
        indicators: TechnicalIndicators,
        market_condition: MarketCondition,
        current_time: Optional[datetime] = None
    ) -> Optional[StrategySignal]:
        """Generate price action scalp signal."""
        
        if len(candles) < 3:
            return None
        
        current_candle = candles[-1]
        previous_candle = candles[-2]
        current_price = float(current_candle.mid_c)
        
        # ATR for stops/targets
        atr = indicators.atr if indicators.atr else (current_price * 0.001)
        
        # Detect patterns
        bullish_pin = self._detect_pin_bar(current_candle, bullish=True)
        bearish_pin = self._detect_pin_bar(current_candle, bullish=False)
        bullish_engulfing = self._detect_engulfing(current_candle, previous_candle, bullish=True)
        bearish_engulfing = self._detect_engulfing(current_candle, previous_candle, bullish=False)
        
        # BUY Signal: Bullish patterns
        if bullish_pin or bullish_engulfing:
            pattern_name = "Pin Bar" if bullish_pin else "Engulfing"
            confidence = 0.70
            
            # Higher confidence near support
            if indicators.support_level and current_price <= indicators.support_level * 1.002:
                confidence += 0.05
            
            strength = 0.7
            
            return StrategySignal(
                signal=TradeSignal.BUY,
                confidence=confidence,
                strength=strength,
                reasoning=f"Bullish {pattern_name} pattern detected",
                entry_price=Decimal(str(current_price)),
                stop_loss=Decimal(str(float(current_candle.mid_l) - (0.5 * atr))),
                take_profit=Decimal(str(current_price + (1.5 * atr))),
                metadata={
                    'pattern': f"Bullish {pattern_name}",
                    'candle_high': float(current_candle.mid_h),
                    'candle_low': float(current_candle.mid_l)
                }
            )
        
        # SELL Signal: Bearish patterns
        elif bearish_pin or bearish_engulfing:
            pattern_name = "Pin Bar" if bearish_pin else "Engulfing"
            confidence = 0.70
            
            # Higher confidence near resistance
            if indicators.resistance_level and current_price >= indicators.resistance_level * 0.998:
                confidence += 0.05
            
            strength = 0.7
            
            return StrategySignal(
                signal=TradeSignal.SELL,
                confidence=confidence,
                strength=strength,
                reasoning=f"Bearish {pattern_name} pattern detected",
                entry_price=Decimal(str(current_price)),
                stop_loss=Decimal(str(float(current_candle.mid_h) + (0.5 * atr))),
                take_profit=Decimal(str(current_price - (1.5 * atr))),
                metadata={
                    'pattern': f"Bearish {pattern_name}",
                    'candle_high': float(current_candle.mid_h),
                    'candle_low': float(current_candle.mid_l)
                }
            )
        
        return None









