"""
Spread Squeeze Strategy - Trades tight spread with volume spike.

Enters when spread is tight and volume increases (high liquidity).
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


@StrategyRegistry.register("Spread_Squeeze")
class SpreadSqueezeStrategy(BaseStrategy):
    """
    Spread squeeze scalping strategy.
    
    Entry Rules:
    - Tight spread (< max_spread_pips)
    - Volume spike (> threshold)
    - Price momentum in clear direction
    
    Parameters:
    - max_spread_pips: Maximum spread for entry (default: 1.5 pips)
    - volume_spike_threshold: Volume multiplier (default: 1.5x average)
    """
    
    @debug_line

    
    def __init__(self, name: str, strategy_type: str, config: Dict[str, Any]):
        super().__init__(name, strategy_type, config)
        
        # Strategy parameters
        self.max_spread_pips = self.parameters.get('max_spread_pips', 1.5)
        self.volume_spike_threshold = self.parameters.get('volume_spike_threshold', 1.5)
    
    async def generate_signal(
        self,
        candles: List[CandleData],
        indicators: TechnicalIndicators,
        market_condition: MarketCondition,
        current_time: Optional[datetime] = None
    ) -> Optional[StrategySignal]:
        """Generate spread squeeze signal."""
        
        if len(candles) < 10:
            return None
        
        current_candle = candles[-1]
        current_price = float(current_candle.mid_c)
        
        # Calculate spread (bid-ask)
        # Note: In real implementation, would get actual bid/ask from API
        # For now, estimate from candle high/low
        estimated_spread = float(current_candle.mid_h) - float(current_candle.mid_l)
        spread_pips = estimated_spread * 10000  # Convert to pips
        
        # Check if spread is tight
        if spread_pips > self.max_spread_pips:
            return None
        
        # Check volume spike
        current_volume = current_candle.volume if hasattr(current_candle, 'volume') and current_candle.volume else 0
        if current_volume == 0:
            return None  # Need volume data
        
        # Calculate average volume
        avg_volume = sum(c.volume if hasattr(c, 'volume') and c.volume else 0 
                        for c in candles[-10:-1]) / 9
        
        if avg_volume == 0 or current_volume < (avg_volume * self.volume_spike_threshold):
            return None  # No volume spike
        
        # ATR for stops/targets
        atr = indicators.atr if indicators.atr else (current_price * 0.001)
        
        # Determine momentum direction
        price_change = float(current_candle.mid_c) - float(current_candle.mid_o)
        price_change_pct = price_change / float(current_candle.mid_o)
        
        # BUY Signal: Bullish momentum + volume spike + tight spread
        if price_change_pct > 0.0001:  # Positive momentum
            confidence = 0.70
            
            # Higher confidence if strong momentum
            if price_change_pct > 0.0003:
                confidence += 0.05
            
            volume_ratio = current_volume / avg_volume
            strength = min(1.0, volume_ratio / 3)
            
            return StrategySignal(
                signal=TradeSignal.BUY,
                confidence=confidence,
                strength=strength,
                reasoning=f"Spread squeeze: {spread_pips:.1f} pips, volume {volume_ratio:.1f}x",
                entry_price=Decimal(str(current_price)),
                stop_loss=Decimal(str(current_price - (1.0 * atr))),
                take_profit=Decimal(str(current_price + (1.5 * atr))),
                metadata={
                    'spread_pips': spread_pips,
                    'volume_ratio': volume_ratio,
                    'momentum': price_change_pct
                }
            )
        
        # SELL Signal: Bearish momentum + volume spike + tight spread
        elif price_change_pct < -0.0001:  # Negative momentum
            confidence = 0.70
            
            # Higher confidence if strong momentum
            if price_change_pct < -0.0003:
                confidence += 0.05
            
            volume_ratio = current_volume / avg_volume
            strength = min(1.0, volume_ratio / 3)
            
            return StrategySignal(
                signal=TradeSignal.SELL,
                confidence=confidence,
                strength=strength,
                reasoning=f"Spread squeeze: {spread_pips:.1f} pips, volume {volume_ratio:.1f}x",
                entry_price=Decimal(str(current_price)),
                stop_loss=Decimal(str(current_price + (1.0 * atr))),
                take_profit=Decimal(str(current_price - (1.5 * atr))),
                metadata={
                    'spread_pips': spread_pips,
                    'volume_ratio': volume_ratio,
                    'momentum': price_change_pct
                }
            )
        
        return None









