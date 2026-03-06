"""
Bollinger Band Bounce Strategy - Mean reversion at band extremes.

Buys at lower band, sells at upper band in ranging markets.
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


@StrategyRegistry.register("BB_Bounce_M5")
class BollingerBounceStrategy(BaseStrategy):
    """
    Bollinger Band mean reversion strategy.
    
    Entry Rules:
    - BUY: Price touches/crosses lower band + RSI < 35
    - SELL: Price touches/crosses upper band + RSI > 65
    - Target: Middle band (mean reversion)
    
    Parameters:
    - period: BB period (default: 20)
    - std_dev: Standard deviations (default: 2)
    - touch_threshold: How close to band (default: 0.001 = 0.1%)
    """
    
    @debug_line

    
    def __init__(self, name: str, strategy_type: str, config: Dict[str, Any]):
        super().__init__(name, strategy_type, config)
        
        # Strategy parameters
        self.bb_period = self.parameters.get('period', 20)
        self.std_dev = self.parameters.get('std_dev', 2)
        self.touch_threshold = self.parameters.get('touch_threshold', 0.001)
    
    async def generate_signal(
        self,
        candles: List[CandleData],
        indicators: TechnicalIndicators,
        market_condition: MarketCondition,
        current_time: Optional[datetime] = None
    ) -> Optional[StrategySignal]:
        """Generate Bollinger Band bounce signal."""
        
        # Need Bollinger Band indicators
        if (indicators.bollinger_upper is None or indicators.bollinger_lower is None or 
            indicators.bollinger_middle is None):
            return None
        
        current_price = float(candles[-1].mid_c)
        bb_upper = indicators.bollinger_upper
        bb_lower = indicators.bollinger_lower
        bb_middle = indicators.bollinger_middle
        
        
        # Use candle wicks not close price — price touches band on wick and bounces before close
        candle_low = float(candles[-1].mid_l)
        candle_high = float(candles[-1].mid_h)
        distance_from_lower = abs(candle_low - bb_lower) / current_price
        distance_from_upper = abs(candle_high - bb_upper) / current_price
                
        # ATR for stops
        atr = indicators.atr if indicators.atr else (current_price * 0.001)
        
        # BUY Signal: Price at lower band + RSI oversold
        if distance_from_lower <= self.touch_threshold and candle_low <= bb_lower * 1.001:
            # RSI confirmation (oversold)
            rsi_oversold = indicators.rsi is not None and indicators.rsi < 35
            
            if rsi_oversold:
                confidence = 0.70
                
                # Increase confidence if very oversold
                if indicators.rsi < 30:
                    confidence += 0.05
                
                # Band width (volatility)
                band_width = (bb_upper - bb_lower) / bb_middle
                strength = min(1.0, band_width * 10)
                
                return StrategySignal(
                    signal=TradeSignal.BUY,
                    confidence=confidence,
                    strength=strength,
                    reasoning=f"BB bounce: Price at lower band ({current_price:.5f}), RSI={indicators.rsi:.1f}",
                    entry_price=Decimal(str(current_price)),
                    stop_loss=Decimal(str(bb_lower - (1.5 * atr))),
                    take_profit=Decimal(str(bb_middle)),  # Target middle band
                    metadata={
                        'bb_upper': bb_upper,
                        'bb_middle': bb_middle,
                        'bb_lower': bb_lower,
                        'rsi': indicators.rsi,
                        'distance_from_band': distance_from_lower
                    }
                )
        
        # SELL Signal: Price at upper band + RSI overbought
        elif distance_from_upper <= self.touch_threshold and candle_high >= bb_upper * 0.999:
            # RSI confirmation (overbought)
            rsi_overbought = indicators.rsi is not None and indicators.rsi > 65
            
            if rsi_overbought:
                confidence = 0.70
                
                # Increase confidence if very overbought
                if indicators.rsi > 70:
                    confidence += 0.05
                
                # Band width (volatility)
                band_width = (bb_upper - bb_lower) / bb_middle
                strength = min(1.0, band_width * 10)
                
                return StrategySignal(
                    signal=TradeSignal.SELL,
                    confidence=confidence,
                    strength=strength,
                    reasoning=f"BB bounce: Price at upper band ({current_price:.5f}), RSI={indicators.rsi:.1f}",
                    entry_price=Decimal(str(current_price)),
                    stop_loss=Decimal(str(bb_upper + (1.5 * atr))),
                    take_profit=Decimal(str(bb_middle)),  # Target middle band
                    metadata={
                        'bb_upper': bb_upper,
                        'bb_middle': bb_middle,
                        'bb_lower': bb_lower,
                        'rsi': indicators.rsi,
                        'distance_from_band': distance_from_upper
                    }
                )
        
        return None









