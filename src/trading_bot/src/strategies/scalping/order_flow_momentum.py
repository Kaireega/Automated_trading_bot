"""
Order Flow Momentum Strategy - Trades based on order flow imbalance.

Detects buy/sell pressure from price action and volume.
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


@StrategyRegistry.register("Order_Flow_Momentum")
class OrderFlowMomentumStrategy(BaseStrategy):
    """
    Order flow momentum strategy based on buy/sell imbalance.
    
    Entry Rules:
    - Strong imbalance detected (> threshold)
    - Momentum in clear direction
    - Volume confirmation
    
    Parameters:
    - imbalance_threshold: Minimum imbalance (default: 0.6 = 60% buy or sell)
    - lookback: Candles to analyze (default: 5)
    """
    
    @debug_line

    
    def __init__(self, name: str, strategy_type: str, config: Dict[str, Any]):
        super().__init__(name, strategy_type, config)
        
        # Strategy parameters
        self.imbalance_threshold = self.parameters.get('imbalance_threshold', 0.6)
        self.lookback = self.parameters.get('lookback', 5)
    
    def _calculate_order_flow_imbalance(self, candles: List[CandleData]) -> Dict[str, float]:
        """
        Calculate order flow imbalance from recent candles.
        
        Simplified approach:
        - Bullish candle (close > open) with volume = buy pressure
        - Bearish candle (close < open) with volume = sell pressure
        """
        buy_volume = 0
        sell_volume = 0
        total_volume = 0
        
        for candle in candles[-self.lookback:]:
            volume = candle.volume if hasattr(candle, 'volume') and candle.volume else 1
            open_price = float(candle.mid_o)
            close_price = float(candle.mid_c)
            
            if close_price > open_price:
                buy_volume += volume
            elif close_price < open_price:
                sell_volume += volume
            
            total_volume += volume
        
        if total_volume == 0:
            return {'buy_ratio': 0.5, 'sell_ratio': 0.5, 'imbalance': 0}
        
        buy_ratio = buy_volume / total_volume
        sell_ratio = sell_volume / total_volume
        imbalance = buy_ratio - sell_ratio  # Positive = buying pressure
        
        return {
            'buy_ratio': buy_ratio,
            'sell_ratio': sell_ratio,
            'imbalance': imbalance,
            'total_volume': total_volume
        }
    
    async def generate_signal(
        self,
        candles: List[CandleData],
        indicators: TechnicalIndicators,
        market_condition: MarketCondition,
        current_time: Optional[datetime] = None
    ) -> Optional[StrategySignal]:
        """Generate order flow momentum signal."""
        
        if len(candles) < self.lookback + 5:
            return None
        
        current_price = float(candles[-1].mid_c)
        
        # Calculate order flow
        flow = self._calculate_order_flow_imbalance(candles)
        
        buy_ratio = flow['buy_ratio']
        sell_ratio = flow['sell_ratio']
        imbalance = flow['imbalance']
        
        # ATR for stops/targets
        atr = indicators.atr if indicators.atr else (current_price * 0.001)
        
        # BUY Signal: Strong buying pressure
        if buy_ratio > self.imbalance_threshold and imbalance > (self.imbalance_threshold - 0.5):
            confidence = 0.70
            
            # Higher confidence if very strong imbalance
            if buy_ratio > 0.75:
                confidence = 0.75
            
            strength = buy_ratio
            
            return StrategySignal(
                signal=TradeSignal.BUY,
                confidence=confidence,
                strength=strength,
                reasoning=f"Order flow: {buy_ratio*100:.1f}% buy pressure",
                entry_price=Decimal(str(current_price)),
                stop_loss=Decimal(str(current_price - (1.5 * atr))),
                take_profit=Decimal(str(current_price + (2.0 * atr))),
                metadata={
                    'buy_ratio': buy_ratio,
                    'sell_ratio': sell_ratio,
                    'imbalance': imbalance
                }
            )
        
        # SELL Signal: Strong selling pressure
        elif sell_ratio > self.imbalance_threshold and imbalance < -(self.imbalance_threshold - 0.5):
            confidence = 0.70
            
            # Higher confidence if very strong imbalance
            if sell_ratio > 0.75:
                confidence = 0.75
            
            strength = sell_ratio
            
            return StrategySignal(
                signal=TradeSignal.SELL,
                confidence=confidence,
                strength=strength,
                reasoning=f"Order flow: {sell_ratio*100:.1f}% sell pressure",
                entry_price=Decimal(str(current_price)),
                stop_loss=Decimal(str(current_price + (1.5 * atr))),
                take_profit=Decimal(str(current_price - (2.0 * atr))),
                metadata={
                    'buy_ratio': buy_ratio,
                    'sell_ratio': sell_ratio,
                    'imbalance': imbalance
                }
            )
        
        return None









