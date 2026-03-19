"""
London Open Range Breakout Strategy.

Trades breakouts from the first hour of London session.
"""
from datetime import datetime, time
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


@StrategyRegistry.register("London_Open_Break")
class LondonOpenBreakStrategy(BaseStrategy):
    """
    London Open Range Breakout strategy.
    
    Entry Rules:
    - Identify range during first hour of London session (08:00-09:00 UTC)
    - Trade breakouts after 09:00 UTC
    - Only active during London session hours
    
    Parameters:
    - session_start: London open time UTC (default: "08:00")
    - range_period_minutes: Range identification period (default: 60)
    - min_range_pips: Minimum range for valid setup (default: 10 pips)
    """
    
    @debug_line

    
    def __init__(self, name: str, strategy_type: str, config: Dict[str, Any]):
        super().__init__(name, strategy_type, config)
        
        # Strategy parameters
        self.session_start_str = self.parameters.get('session_start', '08:00')
        self.range_period_minutes = self.parameters.get('range_period_minutes', 60)
        self.min_range_pips = self.parameters.get('min_range_pips', 10)
        
        # Parse session start time
        hour, minute = map(int, self.session_start_str.split(':'))
        self.session_start = time(hour, minute)
        self.range_end = time(hour + 1 if hour < 23 else 0, minute)
    
    def _is_london_session(self, current_time: datetime) -> bool:
        """Check if current time is during London session (08:00-16:00 UTC)."""
        if current_time is None:
            return False
        current = current_time.time()
        return time(8, 0) <= current <= time(16, 0)
    
    def _calculate_opening_range(self, candles: List[CandleData], current_time: datetime, pair: str = '') -> Optional[Dict[str, float]]:
        """Calculate the opening range from first hour."""
        if not current_time:
            return None
        
        # Filter candles from first hour of London session
        range_candles = []
        for candle in candles:
            candle_time = candle.timestamp.time() if hasattr(candle.timestamp, 'time') else candle.timestamp
            if self.session_start <= candle_time < self.range_end:
                range_candles.append(candle)
        
        if len(range_candles) < 3:  # Need at least a few candles
            return None
        
        # Calculate range high/low
        range_high = max(float(c.mid_h) for c in range_candles)
        range_low = min(float(c.mid_l) for c in range_candles)
        pip_divisor = 100 if 'JPY' in pair else 10000
        range_pips = (range_high - range_low) * pip_divisor
        
        # Check minimum range requirement
        if range_pips < self.min_range_pips:
            return None
        
        return {
            'high': range_high,
            'low': range_low,
            'pips': range_pips
        }
    
    async def generate_signal(
        self,
        candles: List[CandleData],
        indicators: TechnicalIndicators,
        market_condition: MarketCondition,
        current_time: Optional[datetime] = None
    ) -> Optional[StrategySignal]:
        """Generate London open breakout signal."""
        
        if not current_time or not self._is_london_session(current_time):
            return None
        
        # Only trade after range period
        current = current_time.time()
        if current < self.range_end:
            return None
        
        if len(candles) < 20:
            return None
        
        # Calculate opening range
        opening_range = self._calculate_opening_range(candles, current_time)
        if not opening_range:
            return None
        
        range_high = opening_range['high']
        range_low = opening_range['low']
        range_pips = opening_range['pips']
        
        current_price = float(candles[-1].mid_c)
        atr = indicators.atr if indicators.atr else (current_price * 0.001)
        
        # BUY Signal: Break above range high
        if current_price > range_high:
            confidence = 0.70
            
            # Higher confidence if strong breakout
            breakout_distance = (current_price - range_high) * 10000  # pips
            if breakout_distance > 5:
                confidence += 0.05
            
            strength = min(1.0, breakout_distance / 10)
            
            return StrategySignal(
                signal=TradeSignal.BUY,
                confidence=confidence,
                strength=strength,
                reasoning=f"London open break above {range_high:.5f} (range: {range_pips:.1f} pips)",
                entry_price=Decimal(str(current_price)),
                stop_loss=Decimal(str(range_low)),  # Stop at range low
                take_profit=Decimal(str(current_price + (range_high - range_low))),  # Target = range size
                metadata={
                    'range_high': range_high,
                    'range_low': range_low,
                    'range_pips': range_pips,
                    'session': 'London'
                }
            )
        
        # SELL Signal: Break below range low
        elif current_price < range_low:
            confidence = 0.70
            
            # Higher confidence if strong breakout
            breakout_distance = (range_low - current_price) * 10000  # pips
            if breakout_distance > 5:
                confidence += 0.05
            
            strength = min(1.0, breakout_distance / 10)
            
            return StrategySignal(
                signal=TradeSignal.SELL,
                confidence=confidence,
                strength=strength,
                reasoning=f"London open break below {range_low:.5f} (range: {range_pips:.1f} pips)",
                entry_price=Decimal(str(current_price)),
                stop_loss=Decimal(str(range_high)),  # Stop at range high
                take_profit=Decimal(str(current_price - (range_high - range_low))),  # Target = range size
                metadata={
                    'range_high': range_high,
                    'range_low': range_low,
                    'range_pips': range_pips,
                    'session': 'London'
                }
            )
        
        return None






