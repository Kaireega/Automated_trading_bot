"""
Support/Resistance Break Strategy - Trades level breakouts.

Enters when price breaks through key support or resistance levels.
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


@StrategyRegistry.register("Support_Resistance_Break")
class SupportResistanceBreakStrategy(BaseStrategy):
    """
    Support/Resistance breakout strategy.
    
    Entry Rules:
    - BUY: Price breaks above resistance + confirmation
    - SELL: Price breaks below support + confirmation
    
    Parameters:
    - lookback_periods: Periods to identify S/R levels (default: 50)
    - break_threshold: Minimum break distance in pips (default: 0.0005)
    - confirmation_candles: Wait for confirmation (default: 1)
    """
    
    @debug_line

    
    def __init__(self, name: str, strategy_type: str, config: Dict[str, Any]):
        super().__init__(name, strategy_type, config)
        
        # Strategy parameters
        self.lookback_periods = self.parameters.get('lookback_periods', 50)
        self.break_threshold = self.parameters.get('break_threshold', 0.0005)
        self.confirmation_candles = self.parameters.get('confirmation_candles', 1)
    
    def _identify_support_resistance(self, candles: List[CandleData]) -> Dict[str, float]:
        """Identify key support and resistance levels."""
        df = pd.DataFrame([{
            'high': float(c.mid_h),
            'low': float(c.mid_l),
            'close': float(c.mid_c)
        } for c in candles[-self.lookback_periods:]])
        
        # Find recent highs (resistance)
        df['is_peak'] = (df['high'] == df['high'].rolling(window=5, center=True).max())
        peaks = df[df['is_peak']]['high'].values
        
        # Find recent lows (support)
        df['is_trough'] = (df['low'] == df['low'].rolling(window=5, center=True).min())
        troughs = df[df['is_trough']]['low'].values
        
        # Calculate strongest levels (most touches)
        resistance = max(peaks) if len(peaks) > 0 else df['high'].max()
        support = min(troughs) if len(troughs) > 0 else df['low'].min()
        
        return {
            'resistance': resistance,
            'support': support,
            'num_resistance_touches': len(peaks),
            'num_support_touches': len(troughs)
        }
    
    async def generate_signal(
        self,
        candles: List[CandleData],
        indicators: TechnicalIndicators,
        market_condition: MarketCondition,
        current_time: Optional[datetime] = None
    ) -> Optional[StrategySignal]:
        """Generate support/resistance breakout signal."""
        
        if len(candles) < self.lookback_periods + 5:
            return None
        
        current_price = float(candles[-1].mid_c)
        prev_price = float(candles[-2].mid_c) if len(candles) >= 2 else current_price
        
        # Get ATR
        atr = indicators.atr if indicators.atr else (current_price * 0.001)
        
        # Use indicators S/R levels if available, otherwise calculate
        if indicators.resistance_level and indicators.support_level:
            resistance = indicators.resistance_level
            support = indicators.support_level
            sr_data = {'resistance': resistance, 'support': support}
        else:
            sr_data = self._identify_support_resistance(candles)
            resistance = sr_data['resistance']
            support = sr_data['support']
        
        # BUY Signal: Break above resistance
        if prev_price <= resistance and current_price > (resistance + self.break_threshold):
            confidence = 0.65
            
            # Higher confidence if strong level (many touches)
            num_touches = sr_data.get('num_resistance_touches', 0)
            if num_touches >= 3:
                confidence += 0.05
            
            # Volume confirmation
            if len(candles) >= 2:
                current_volume = candles[-1].volume if hasattr(candles[-1], 'volume') else 0
                prev_volume = candles[-2].volume if hasattr(candles[-2], 'volume') else 0
                if current_volume and prev_volume and current_volume > prev_volume * 1.2:
                    confidence += 0.05
            
            # Strength based on break distance
            break_distance = current_price - resistance
            strength = min(1.0, break_distance / atr)
            
            return StrategySignal(
                signal=TradeSignal.BUY,
                confidence=confidence,
                strength=strength,
                reasoning=f"Resistance break: {current_price:.5f} > {resistance:.5f}",
                entry_price=Decimal(str(current_price)),
                stop_loss=Decimal(str(resistance - atr)),  # Stop below broken resistance
                take_profit=Decimal(str(current_price + (2.5 * atr))),
                metadata={
                    'resistance_level': resistance,
                    'support_level': support,
                    'break_distance': break_distance
                }
            )
        
        # SELL Signal: Break below support
        elif prev_price >= support and current_price < (support - self.break_threshold):
            confidence = 0.65
            
            # Higher confidence if strong level (many touches)
            num_touches = sr_data.get('num_support_touches', 0)
            if num_touches >= 3:
                confidence += 0.05
            
            # Volume confirmation
            if len(candles) >= 2:
                current_volume = candles[-1].volume if hasattr(candles[-1], 'volume') else 0
                prev_volume = candles[-2].volume if hasattr(candles[-2], 'volume') else 0
                if current_volume and prev_volume and current_volume > prev_volume * 1.2:
                    confidence += 0.05
            
            # Strength based on break distance
            break_distance = support - current_price
            strength = min(1.0, break_distance / atr)
            
            return StrategySignal(
                signal=TradeSignal.SELL,
                confidence=confidence,
                strength=strength,
                reasoning=f"Support break: {current_price:.5f} < {support:.5f}",
                entry_price=Decimal(str(current_price)),
                stop_loss=Decimal(str(support + atr)),  # Stop above broken support
                take_profit=Decimal(str(current_price - (2.5 * atr))),
                metadata={
                    'support_level': support,
                    'resistance_level': resistance,
                    'break_distance': break_distance
                }
            )
        
        return None









