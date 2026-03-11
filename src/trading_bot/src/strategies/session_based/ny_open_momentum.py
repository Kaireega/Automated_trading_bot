"""
NY Open Momentum Strategy.

Trades momentum in first 30 minutes of NY session.
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


@StrategyRegistry.register("NY_Open_Momentum")
class NYOpenMomentumStrategy(BaseStrategy):
    """
    NY Open Momentum strategy.
    
    Entry Rules:
    - Strong momentum in first 30 minutes of NY session (13:00-13:30 UTC / 8:00-8:30 EST)
    - Volume confirmation
    - Clear directional move
    
    Parameters:
    - session_start: NY open time UTC (default: "13:00")
    - momentum_period_minutes: Momentum window (default: 30)
    - min_momentum_pips: Minimum move for signal (default: 8 pips)
    """
    
    @debug_line

    
    def __init__(self, name: str, strategy_type: str, config: Dict[str, Any]):
        super().__init__(name, strategy_type, config)
        
        # Strategy parameters
        self.session_start_str = self.parameters.get('session_start', '13:00')
        self.momentum_period = self.parameters.get('momentum_period_minutes', 30)
        self.min_momentum_pips = self.parameters.get('min_momentum_pips', 8)
        
        # Parse session start time (13:00 UTC = 8:00 EST)
        hour, minute = map(int, self.session_start_str.split(':'))
        self.session_start = time(hour, minute)
        self.momentum_end = time(hour, minute + self.momentum_period)
    
    def _is_ny_session(self, current_time: datetime) -> bool:
        """Check if current time is during NY session (13:00-22:00 UTC)."""
        if current_time is None:
            return False
        current = current_time.time()
        return time(13, 0) <= current <= time(22, 0)
    
    def _is_momentum_window(self, current_time: datetime) -> bool:
        """Check if current time is within momentum window (first 30 min)."""
        if current_time is None:
            return False
        current = current_time.time()
        return self.session_start <= current <= self.momentum_end
    
    def _calculate_session_momentum(self, candles: List[CandleData], current_time: datetime) -> Optional[Dict[str, Any]]:
        """Calculate momentum since session start."""
        if not current_time:
            return None
        
        # Find candles since session start
        session_candles = []
        for candle in candles:
            candle_time = candle.timestamp.time() if hasattr(candle.timestamp, 'time') else candle.timestamp
            if candle_time >= self.session_start:
                session_candles.append(candle)
        
        if len(session_candles) < 3:
            return None
        
        # Calculate momentum
        session_open = float(session_candles[0].mid_o)
        current_close = float(session_candles[-1].mid_c)
        momentum = current_close - session_open
        momentum_pips = abs(momentum) * 10000
        
        # Calculate volume
        total_volume = sum(c.volume if hasattr(c, 'volume') and c.volume else 0 
                          for c in session_candles)
        avg_volume_per_candle = total_volume / len(session_candles) if len(session_candles) > 0 else 0
        
        return {
            'momentum': momentum,
            'momentum_pips': momentum_pips,
            'session_open': session_open,
            'current_close': current_close,
            'direction': 'bullish' if momentum > 0 else 'bearish',
            'avg_volume': avg_volume_per_candle
        }
    
    async def generate_signal(
        self,
        candles: List[CandleData],
        indicators: TechnicalIndicators,
        market_condition: MarketCondition,
        current_time: Optional[datetime] = None
    ) -> Optional[StrategySignal]:
        """Generate NY open momentum signal."""
        
        if not current_time or not self._is_ny_session(current_time):
            return None
        
        # Only trade within momentum window
        if not self._is_momentum_window(current_time):
            return None
        
        if len(candles) < 10:
            return None
        
        # Calculate momentum
        momentum_data = self._calculate_session_momentum(candles, current_time)
        if not momentum_data:
            return None
        
        momentum = momentum_data['momentum']
        momentum_pips = momentum_data['momentum_pips']
        direction = momentum_data['direction']
        session_open = momentum_data['session_open']
        
        # Check minimum momentum requirement
        if momentum_pips < self.min_momentum_pips:
            return None
        
        current_price = float(candles[-1].mid_c)
        atr = indicators.atr if indicators.atr else (current_price * 0.001)
        
        # BUY Signal: Strong bullish momentum
        if direction == 'bullish':
            confidence = 0.70
            
            # Higher confidence if very strong momentum
            if momentum_pips > 15:
                confidence = 0.75
            
            # Check volume confirmation
            current_volume = candles[-1].volume if hasattr(candles[-1], 'volume') and candles[-1].volume else 0
            avg_volume = momentum_data['avg_volume']
            if current_volume > avg_volume * 1.2:
                confidence += 0.05
            
            strength = min(1.0, momentum_pips / 20)
            
            return StrategySignal(
                signal=TradeSignal.BUY,
                confidence=confidence,
                strength=strength,
                reasoning=f"NY open bullish momentum: +{momentum_pips:.1f} pips",
                entry_price=Decimal(str(current_price)),
                stop_loss=Decimal(str(session_open - atr)),  # Stop below session open
                take_profit=Decimal(str(current_price + (2.0 * abs(momentum)))),  # Target 2x momentum
                metadata={
                    'momentum_pips': momentum_pips,
                    'session_open': session_open,
                    'session': 'NY',
                    'direction': direction
                }
            )
        
        # SELL Signal: Strong bearish momentum
        elif direction == 'bearish':
            confidence = 0.70
            
            # Higher confidence if very strong momentum
            if momentum_pips > 15:
                confidence = 0.75
            
            # Check volume confirmation
            current_volume = candles[-1].volume if hasattr(candles[-1], 'volume') and candles[-1].volume else 0
            avg_volume = momentum_data['avg_volume']
            if current_volume > avg_volume * 1.2:
                confidence += 0.05
            
            strength = min(1.0, momentum_pips / 20)
            
            return StrategySignal(
                signal=TradeSignal.SELL,
                confidence=confidence,
                strength=strength,
                reasoning=f"NY open bearish momentum: -{momentum_pips:.1f} pips",
                entry_price=Decimal(str(current_price)),
                stop_loss=Decimal(str(session_open + atr)),  # Stop above session open
                take_profit=Decimal(str(current_price - (2.0 * abs(momentum)))),  # Target 2x momentum
                metadata={
                    'momentum_pips': momentum_pips,
                    'session_open': session_open,
                    'session': 'NY',
                    'direction': direction
                }
            )
        
        return None






