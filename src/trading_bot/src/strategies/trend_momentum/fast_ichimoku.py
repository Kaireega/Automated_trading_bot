"""
Fast Ichimoku Strategy - Ichimoku Cloud with faster settings for intraday.

Uses 5/13/26 instead of traditional 9/26/52 for M5/M15 trading.
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


@StrategyRegistry.register("Fast_Ichimoku")
class FastIchimokuStrategy(BaseStrategy):
    """
    Fast Ichimoku Cloud strategy for intraday trading.
    
    Entry Rules:
    - BUY: Price above cloud + Tenkan > Kijun + Chikou above price
    - SELL: Price below cloud + Tenkan < Kijun + Chikou below price
    
    Parameters:
    - tenkan: Tenkan-sen period (default: 5 for intraday, vs 9 standard)
    - kijun: Kijun-sen period (default: 13 for intraday, vs 26 standard)
    - senkou: Senkou Span B period (default: 26 for intraday, vs 52 standard)
    """
    
    @debug_line

    
    def __init__(self, name: str, strategy_type: str, config: Dict[str, Any]):
        super().__init__(name, strategy_type, config)
        
        # Fast Ichimoku parameters for intraday
        self.tenkan_period = self.parameters.get('tenkan', 5)
        self.kijun_period = self.parameters.get('kijun', 13)
        self.senkou_period = self.parameters.get('senkou', 26)
    
    def _calculate_ichimoku(self, candles: List[CandleData]) -> Dict[str, float]:
        """Calculate Ichimoku Cloud indicators."""
        df = pd.DataFrame([{
            'high': float(c.mid_h),
            'low': float(c.mid_l),
            'close': float(c.mid_c)
        } for c in candles])
        
        # Tenkan-sen (Conversion Line): (highest high + lowest low) / 2 for tenkan period
        high_tenkan = df['high'].rolling(window=self.tenkan_period).max()
        low_tenkan = df['low'].rolling(window=self.tenkan_period).min()
        df['tenkan_sen'] = (high_tenkan + low_tenkan) / 2
        
        # Kijun-sen (Base Line): (highest high + lowest low) / 2 for kijun period
        high_kijun = df['high'].rolling(window=self.kijun_period).max()
        low_kijun = df['low'].rolling(window=self.kijun_period).min()
        df['kijun_sen'] = (high_kijun + low_kijun) / 2
        
        # Senkou Span A (Leading Span A): (Tenkan + Kijun) / 2, shifted forward
        df['senkou_span_a'] = ((df['tenkan_sen'] + df['kijun_sen']) / 2).shift(self.kijun_period)
        
        # Senkou Span B (Leading Span B): (highest high + lowest low) / 2 for senkou period, shifted forward
        high_senkou = df['high'].rolling(window=self.senkou_period).max()
        low_senkou = df['low'].rolling(window=self.senkou_period).min()
        df['senkou_span_b'] = ((high_senkou + low_senkou) / 2).shift(self.kijun_period)
        
        # Chikou Span (Lagging Span): Close shifted backward
        df['chikou_span'] = df['close'].shift(-self.kijun_period)
        
        # Use correct cloud index — senkou spans are shifted forward by kijun_period
        # so current cloud is at -(kijun_period + 1), not -1
        cloud_idx = -(self.kijun_period + 1)

        return {
            'tenkan': df['tenkan_sen'].iloc[-1] if not pd.isna(df['tenkan_sen'].iloc[-1]) else 0,
            'kijun': df['kijun_sen'].iloc[-1] if not pd.isna(df['kijun_sen'].iloc[-1]) else 0,
            'senkou_a': df['senkou_span_a'].iloc[cloud_idx] if len(df) > abs(cloud_idx) and not pd.isna(df['senkou_span_a'].iloc[cloud_idx]) else 0,
            'senkou_b': df['senkou_span_b'].iloc[cloud_idx] if len(df) > abs(cloud_idx) and not pd.isna(df['senkou_span_b'].iloc[cloud_idx]) else 0,
            # Chikou: compare current close to the close kijun_period candles ago.
            # df['chikou_span'] = close.shift(-kijun) → NaN at tail (future data).
            # Correct interpretation: chikou is bullish if current close > close from kijun periods ago.
            'chikou': df['close'].iloc[-1] if len(df) > self.kijun_period else 0,
            'chikou_past_price': df['close'].iloc[-(self.kijun_period + 1)] if len(df) > self.kijun_period else 0,
            'close': df['close'].iloc[-1]
        }
    
    async def generate_signal(
        self,
        candles: List[CandleData],
        indicators: TechnicalIndicators,
        market_condition: MarketCondition,
        current_time: Optional[datetime] = None
    ) -> Optional[StrategySignal]:
        """Generate Ichimoku Cloud signal."""
        
        if len(candles) < self.senkou_period + self.kijun_period + 5:
            return None
        
        # Calculate Ichimoku indicators
        ichimoku = self._calculate_ichimoku(candles)
        
        tenkan = ichimoku['tenkan']
        kijun = ichimoku['kijun']
        senkou_a = ichimoku['senkou_a']
        senkou_b = ichimoku['senkou_b']
        chikou = ichimoku['chikou']
        chikou_past_price = ichimoku['chikou_past_price']
        current_price = ichimoku['close']

        # Cloud top and bottom
        cloud_top = max(senkou_a, senkou_b)
        cloud_bottom = min(senkou_a, senkou_b)

        # ATR for stops
        atr = indicators.atr if indicators.atr else (current_price * 0.001)

        # Chikou confirmation: current close vs close kijun_period bars ago
        chikou_bullish = chikou > chikou_past_price  # price rising over kijun period
        chikou_bearish = chikou < chikou_past_price  # price falling over kijun period

        # BUY Signal: Price above cloud + TK cross bullish
        if current_price > cloud_top and tenkan > kijun:
            confidence = 0.70

            # Increase confidence if Chikou also confirms
            if chikou_bullish:
                confidence += 0.05

            # Strong signal if well above cloud
            distance_from_cloud = (current_price - cloud_top) / current_price
            strength = min(1.0, distance_from_cloud * 100)

            return StrategySignal(
                signal=TradeSignal.BUY,
                confidence=confidence,
                strength=strength,
                reasoning=f"Ichimoku bullish: Price above cloud, TK cross",
                entry_price=Decimal(str(current_price)),
                stop_loss=Decimal(str(cloud_top - atr)),  # Stop below cloud
                take_profit=Decimal(str(current_price + (3.0 * atr))),
                metadata={
                    'tenkan': tenkan,
                    'kijun': kijun,
                    'cloud_top': cloud_top,
                    'cloud_bottom': cloud_bottom
                }
            )

        # SELL Signal: Price below cloud + TK cross bearish
        elif current_price < cloud_bottom and tenkan < kijun:
            confidence = 0.70

            # Increase confidence if Chikou also confirms
            if chikou_bearish:
                confidence += 0.05
            
            # Strong signal if well below cloud
            distance_from_cloud = (cloud_bottom - current_price) / current_price
            strength = min(1.0, distance_from_cloud * 100)
            
            return StrategySignal(
                signal=TradeSignal.SELL,
                confidence=confidence,
                strength=strength,
                reasoning=f"Ichimoku bearish: Price below cloud, TK cross",
                entry_price=Decimal(str(current_price)),
                stop_loss=Decimal(str(cloud_bottom + atr)),  # Stop above cloud
                take_profit=Decimal(str(current_price - (3.0 * atr))),
                metadata={
                    'tenkan': tenkan,
                    'kijun': kijun,
                    'cloud_top': cloud_top,
                    'cloud_bottom': cloud_bottom
                }
            )
        
        return None









