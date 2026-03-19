"""
Stochastic Reversal Strategy - Fast stochastic oversold/overbought.

Uses fast stochastic (5,3,3) for quick intraday reversals.
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


@StrategyRegistry.register("Fast_Stochastic")
class StochasticReversalStrategy(BaseStrategy):
    """
    Fast Stochastic mean reversion strategy.
    
    Entry Rules:
    - BUY: %K < 20 (oversold) + %K crosses above %D
    - SELL: %K > 80 (overbought) + %K crosses below %D
    
    Parameters:
    - k_period: %K period (default: 5 for fast)
    - d_period: %D period (default: 3)
    - smooth: Smoothing factor (default: 3)
    """
    
    @debug_line

    
    def __init__(self, name: str, strategy_type: str, config: Dict[str, Any]):
        super().__init__(name, strategy_type, config)
        
        # Fast stochastic parameters
        self.k_period = self.parameters.get('k_period', 5)
        self.d_period = self.parameters.get('d_period', 3)
        self.smooth = self.parameters.get('smooth', 3)
        self.oversold = 20
        self.overbought = 80
    
    def _calculate_stochastic(self, candles: List[CandleData]) -> Dict[str, float]:
        """Calculate Fast Stochastic %K and %D."""
        df = pd.DataFrame([{
            'high': float(c.mid_h),
            'low': float(c.mid_l),
            'close': float(c.mid_c)
        } for c in candles])
        
        # %K = (Current Close - Lowest Low) / (Highest High - Lowest Low) * 100
        low_min = df['low'].rolling(window=self.k_period).min()
        high_max = df['high'].rolling(window=self.k_period).max()
        
        df['stoch_k'] = 100 * (df['close'] - low_min) / (high_max - low_min)
        
        # Smooth %K
        df['stoch_k'] = df['stoch_k'].rolling(window=self.smooth).mean()
        
        # %D = SMA of %K
        df['stoch_d'] = df['stoch_k'].rolling(window=self.d_period).mean()
        
        return {
            'k': df['stoch_k'].iloc[-1] if not pd.isna(df['stoch_k'].iloc[-1]) else 50,
            'd': df['stoch_d'].iloc[-1] if not pd.isna(df['stoch_d'].iloc[-1]) else 50,
            'k_prev': df['stoch_k'].iloc[-2] if len(df) > 1 and not pd.isna(df['stoch_k'].iloc[-2]) else 50,
            'd_prev': df['stoch_d'].iloc[-2] if len(df) > 1 and not pd.isna(df['stoch_d'].iloc[-2]) else 50
        }
    
    async def generate_signal(
        self,
        candles: List[CandleData],
        indicators: TechnicalIndicators,
        market_condition: MarketCondition,
        current_time: Optional[datetime] = None
    ) -> Optional[StrategySignal]:
        """Generate stochastic reversal signal."""
        
        if len(candles) < self.k_period + self.d_period + self.smooth:
            return None
        
        # Calculate stochastic or use from indicators
        if indicators.stoch_k is not None and indicators.stoch_d is not None:
            stoch_k = indicators.stoch_k
            stoch_d = indicators.stoch_d
            stoch = {'k': stoch_k, 'd': stoch_d, 'k_prev': stoch_k, 'd_prev': stoch_d}
        else:
            stoch = self._calculate_stochastic(candles)
        
        k = stoch['k']
        d = stoch['d']
        k_prev = stoch.get('k_prev', k)
        d_prev = stoch.get('d_prev', d)
        
        current_price = float(candles[-1].mid_c)
        atr = indicators.atr if indicators.atr else (current_price * 0.001)
        
        # BUY Signal: Oversold + %K crosses above %D
        if k < self.oversold and k_prev <= d_prev and k > d:
            confidence = 0.70
            
            # Higher confidence if very oversold
            if k < 10:
                confidence = 0.75
            
            strength = min(1.0, (self.oversold - k) / self.oversold)
            
            return StrategySignal(
                signal=TradeSignal.BUY,
                confidence=confidence,
                strength=strength,
                reasoning=f"Stochastic oversold + bullish cross: %K={k:.1f}, %D={d:.1f}",
                entry_price=Decimal(str(current_price)),
                stop_loss=Decimal(str(current_price - (1.5 * atr))),
                take_profit=Decimal(str(current_price + (2.0 * atr))),
                metadata={
                    'stoch_k': k,
                    'stoch_d': d,
                    'oversold_level': self.oversold
                }
            )
        
        # SELL Signal: Overbought + %K crosses below %D
        elif k > self.overbought and k_prev >= d_prev and k < d:
            confidence = 0.70
            
            # Higher confidence if very overbought
            if k > 90:
                confidence = 0.75
            
            strength = min(1.0, (k - self.overbought) / (100 - self.overbought))
            
            return StrategySignal(
                signal=TradeSignal.SELL,
                confidence=confidence,
                strength=strength,
                reasoning=f"Stochastic overbought + bearish cross: %K={k:.1f}, %D={d:.1f}",
                entry_price=Decimal(str(current_price)),
                stop_loss=Decimal(str(current_price + (1.5 * atr))),
                take_profit=Decimal(str(current_price - (2.0 * atr))),
                metadata={
                    'stoch_k': k,
                    'stoch_d': d,
                    'overbought_level': self.overbought
                }
            )
        
        return None









