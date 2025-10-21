"""
RSI Extremes Strategy - RSI oversold/overbought reversals.

Trades RSI extremes with support/resistance confirmation.
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


@StrategyRegistry.register("RSI_Extremes")
class RSIExtremesStrategy(BaseStrategy):
    """
    RSI oversold/overbought mean reversion strategy.
    
    Entry Rules:
    - BUY: RSI < oversold + Price near support
    - SELL: RSI > overbought + Price near resistance
    
    Parameters:
    - period: RSI period (default: 14)
    - oversold: Oversold threshold (default: 35 for intraday)
    - overbought: Overbought threshold (default: 65 for intraday)
    """
    
    @debug_line

    
    def __init__(self, name: str, strategy_type: str, config: Dict[str, Any]):
        super().__init__(name, strategy_type, config)
        
        # Strategy parameters
        self.rsi_period = self.parameters.get('period', 14)
        self.oversold = self.parameters.get('oversold', 35)
        self.overbought = self.parameters.get('overbought', 65)
        self.extreme_oversold = self.parameters.get('extreme_oversold', 25)
        self.extreme_overbought = self.parameters.get('extreme_overbought', 75)
    
    async def generate_signal(
        self,
        candles: List[CandleData],
        indicators: TechnicalIndicators,
        market_condition: MarketCondition,
        current_time: Optional[datetime] = None
    ) -> Optional[StrategySignal]:
        """Generate RSI extremes signal."""
        
        # Need RSI
        if indicators.rsi is None:
            return None
        
        current_price = float(candles[-1].mid_c)
        rsi = indicators.rsi
        
        # ATR for stops
        atr = indicators.atr if indicators.atr else (current_price * 0.001)
        
        # BUY Signal: RSI oversold
        if rsi < self.oversold:
            confidence = 0.65
            
            # Higher confidence if extremely oversold
            if rsi < self.extreme_oversold:
                confidence = 0.75
            
            # Additional confirmation from Bollinger Bands if available
            if indicators.bollinger_lower and current_price <= indicators.bollinger_lower:
                confidence += 0.05
            
            # Strength based on how oversold
            strength = min(1.0, (self.oversold - rsi) / self.oversold)
            
            return StrategySignal(
                signal=TradeSignal.BUY,
                confidence=confidence,
                strength=strength,
                reasoning=f"RSI oversold: {rsi:.1f} < {self.oversold}",
                entry_price=Decimal(str(current_price)),
                stop_loss=Decimal(str(current_price - (1.5 * atr))),
                take_profit=Decimal(str(current_price + (2.0 * atr))),
                metadata={
                    'rsi': rsi,
                    'oversold_threshold': self.oversold,
                    'support_level': indicators.support_level
                }
            )
        
        # SELL Signal: RSI overbought
        elif rsi > self.overbought:
            confidence = 0.65
            
            # Higher confidence if extremely overbought
            if rsi > self.extreme_overbought:
                confidence = 0.75
            
            # Additional confirmation from Bollinger Bands if available
            if indicators.bollinger_upper and current_price >= indicators.bollinger_upper:
                confidence += 0.05
            
            # Strength based on how overbought
            strength = min(1.0, (rsi - self.overbought) / (100 - self.overbought))
            
            return StrategySignal(
                signal=TradeSignal.SELL,
                confidence=confidence,
                strength=strength,
                reasoning=f"RSI overbought: {rsi:.1f} > {self.overbought}",
                entry_price=Decimal(str(current_price)),
                stop_loss=Decimal(str(current_price + (1.5 * atr))),
                take_profit=Decimal(str(current_price - (2.0 * atr))),
                metadata={
                    'rsi': rsi,
                    'overbought_threshold': self.overbought,
                    'resistance_level': indicators.resistance_level
                }
            )
        
        return None









