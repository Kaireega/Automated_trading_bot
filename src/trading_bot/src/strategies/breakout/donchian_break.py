"""
Donchian Channel Breakout Strategy - Trades channel breakouts.

Uses 10-period Donchian Channel for intraday breakouts.
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


@StrategyRegistry.register("Donchian_Break")
class DonchianBreakStrategy(BaseStrategy):
    """
    Donchian Channel breakout strategy.
    
    Entry Rules:
    - BUY: Price breaks above upper channel (highest high)
    - SELL: Price breaks below lower channel (lowest low)
    
    Parameters:
    - period: Donchian Channel period (default: 10 for intraday)
    - exit_period: Period for exit channel (default: 5)
    """
    
    @debug_line

    
    def __init__(self, name: str, strategy_type: str, config: Dict[str, Any]):
        super().__init__(name, strategy_type, config)
        
        # Strategy parameters
        self.entry_period = self.parameters.get('period', 10)
        self.exit_period = self.parameters.get('exit_period', 5)
    
    async def generate_signal(
        self,
        candles: List[CandleData],
        indicators: TechnicalIndicators,
        market_condition: MarketCondition,
        current_time: Optional[datetime] = None
    ) -> Optional[StrategySignal]:
        """Generate Donchian Channel breakout signal."""
        
        if len(candles) < self.entry_period + 5:
            return None
        
        current_price = float(candles[-1].mid_c)
        current_high = float(candles[-1].mid_h)
        current_low = float(candles[-1].mid_l)
        
        # Calculate Donchian Channels
        lookback_candles = candles[-self.entry_period-1:-1]  # Exclude current
        upper_channel = max(float(c.mid_h) for c in lookback_candles)
        lower_channel = min(float(c.mid_l) for c in lookback_candles)
        middle_channel = (upper_channel + lower_channel) / 2
        
        # Exit channels (for stop loss)
        exit_candles = candles[-self.exit_period-1:-1]
        exit_upper = max(float(c.mid_h) for c in exit_candles)
        exit_lower = min(float(c.mid_l) for c in exit_candles)
        
        # ATR for targets
        atr = indicators.atr if indicators.atr else (current_price * 0.001)
        
        # BUY Signal: Breakout above upper channel
        if current_high > upper_channel:
            confidence = 0.65
            
            # Higher confidence in trending markets
            if market_condition.value in ['TRENDING_UP', 'BREAKOUT']:
                confidence += 0.05
            
            # Channel width (volatility)
            channel_width = (upper_channel - lower_channel) / middle_channel
            strength = min(1.0, channel_width * 50)
            
            return StrategySignal(
                signal=TradeSignal.BUY,
                confidence=confidence,
                strength=strength,
                reasoning=f"Donchian breakout above {upper_channel:.5f}",
                entry_price=Decimal(str(current_price)),
                stop_loss=Decimal(str(exit_lower)),  # Exit on break of lower exit channel
                take_profit=Decimal(str(current_price + (channel_width * current_price))),
                metadata={
                    'upper_channel': upper_channel,
                    'lower_channel': lower_channel,
                    'middle_channel': middle_channel,
                    'channel_width': channel_width
                }
            )
        
        # SELL Signal: Breakout below lower channel
        elif current_low < lower_channel:
            confidence = 0.65
            
            # Higher confidence in trending markets
            if market_condition.value in ['TRENDING_DOWN', 'BREAKOUT']:
                confidence += 0.05
            
            # Channel width (volatility)
            channel_width = (upper_channel - lower_channel) / middle_channel
            strength = min(1.0, channel_width * 50)
            
            return StrategySignal(
                signal=TradeSignal.SELL,
                confidence=confidence,
                strength=strength,
                reasoning=f"Donchian breakout below {lower_channel:.5f}",
                entry_price=Decimal(str(current_price)),
                stop_loss=Decimal(str(exit_upper)),  # Exit on break of upper exit channel
                take_profit=Decimal(str(current_price - (channel_width * current_price))),
                metadata={
                    'upper_channel': upper_channel,
                    'lower_channel': lower_channel,
                    'middle_channel': middle_channel,
                    'channel_width': channel_width
                }
            )
        
        return None









