"""
ADX Trend Strategy - ADX strength with directional movement.

Uses ADX > 20 threshold for intraday trending conditions.
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


@StrategyRegistry.register("ADX_Trend_M5")
class ADXTrendStrategy(BaseStrategy):
    """
    ADX trend strength strategy with directional indicators.
    
    Entry Rules:
    - BUY: ADX > threshold + +DI > -DI + Price above EMA
    - SELL: ADX > threshold + -DI > +DI + Price below EMA
    
    Parameters:
    - period: ADX period (default: 14)
    - threshold: Minimum ADX value (default: 20 for intraday)
    """
    
    @debug_line

    
    def __init__(self, name: str, strategy_type: str, config: Dict[str, Any]):
        super().__init__(name, strategy_type, config)
        
        # Strategy parameters
        self.adx_period = self.parameters.get('period', 14)
        self.adx_threshold = self.parameters.get('threshold', 20)
    
    def _calculate_adx(self, candles: List[CandleData]) -> Dict[str, float]:
        """Calculate ADX, +DI, -DI indicators."""
        df = pd.DataFrame([{
            'high': float(c.mid_h),
            'low': float(c.mid_l),
            'close': float(c.mid_c)
        } for c in candles])
        
        # True Range
        df['h-l'] = df['high'] - df['low']
        df['h-pc'] = abs(df['high'] - df['close'].shift(1))
        df['l-pc'] = abs(df['low'] - df['close'].shift(1))
        df['tr'] = df[['h-l', 'h-pc', 'l-pc']].max(axis=1)
        
        # Directional Movement
        df['up_move'] = df['high'] - df['high'].shift(1)
        df['down_move'] = df['low'].shift(1) - df['low']
        
        df['plus_dm'] = df.apply(
            lambda row: row['up_move'] if row['up_move'] > row['down_move'] and row['up_move'] > 0 else 0,
            axis=1
        )
        df['minus_dm'] = df.apply(
            lambda row: row['down_move'] if row['down_move'] > row['up_move'] and row['down_move'] > 0 else 0,
            axis=1
        )
        
        # Smoothed indicators
        atr = df['tr'].rolling(window=self.adx_period).mean()
        plus_di = 100 * (df['plus_dm'].rolling(window=self.adx_period).mean() / atr)
        minus_di = 100 * (df['minus_dm'].rolling(window=self.adx_period).mean() / atr)
        
        # ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=self.adx_period).mean()
        
        return {
            'adx': adx.iloc[-1] if not pd.isna(adx.iloc[-1]) else 0,
            'plus_di': plus_di.iloc[-1] if not pd.isna(plus_di.iloc[-1]) else 0,
            'minus_di': minus_di.iloc[-1] if not pd.isna(minus_di.iloc[-1]) else 0,
            'atr': atr.iloc[-1] if not pd.isna(atr.iloc[-1]) else 0
        }
    
    async def generate_signal(
        self,
        candles: List[CandleData],
        indicators: TechnicalIndicators,
        market_condition: MarketCondition,
        current_time: Optional[datetime] = None
    ) -> Optional[StrategySignal]:
        """Generate ADX trend signal."""
        
        if len(candles) < self.adx_period * 2:
            return None
        
        # Calculate ADX indicators
        adx_indicators = self._calculate_adx(candles)
        
        adx = adx_indicators['adx']
        plus_di = adx_indicators['plus_di']
        minus_di = adx_indicators['minus_di']
        atr_value = adx_indicators['atr']
        
        # Check ADX strength
        if adx < self.adx_threshold:
            return None
        
        current_price = float(candles[-1].mid_c)
        
        # Use ATR from indicators or calculated
        atr = indicators.atr if indicators.atr else atr_value
        
        # EMA confirmation (use indicators if available)
        ema_bullish = indicators.ema_fast and indicators.ema_slow and indicators.ema_fast > indicators.ema_slow
        ema_bearish = indicators.ema_fast and indicators.ema_slow and indicators.ema_fast < indicators.ema_slow
        
        # BUY Signal
        if plus_di > minus_di and (ema_bullish or indicators.ema_fast is None):
            # Strong trend if ADX > 25
            confidence = 0.70 if adx > 25 else 0.65
            strength = min(1.0, (plus_di - minus_di) / 50)
            
            return StrategySignal(
                signal=TradeSignal.BUY,
                confidence=confidence,
                strength=strength,
                reasoning=f"ADX trending up: ADX={adx:.1f}, +DI={plus_di:.1f}, -DI={minus_di:.1f}",
                entry_price=Decimal(str(current_price)),
                stop_loss=Decimal(str(current_price - (2.0 * atr))),
                take_profit=Decimal(str(current_price + (4.0 * atr))),  # I-3: 2:1 R:R (was 3×ATR = 1.5:1)
                metadata={
                    'adx': adx,
                    'plus_di': plus_di,
                    'minus_di': minus_di
                }
            )

        # SELL Signal
        elif minus_di > plus_di and (ema_bearish or indicators.ema_fast is None):
            confidence = 0.70 if adx > 25 else 0.65
            strength = min(1.0, (minus_di - plus_di) / 50)

            return StrategySignal(
                signal=TradeSignal.SELL,
                confidence=confidence,
                strength=strength,
                reasoning=f"ADX trending down: ADX={adx:.1f}, +DI={plus_di:.1f}, -DI={minus_di:.1f}",
                entry_price=Decimal(str(current_price)),
                stop_loss=Decimal(str(current_price + (2.0 * atr))),
                take_profit=Decimal(str(current_price - (4.0 * atr))),  # I-3: 2:1 R:R (was 3×ATR = 1.5:1)
                metadata={
                    'adx': adx,
                    'plus_di': plus_di,
                    'minus_di': minus_di
                }
            )
        
        return None









