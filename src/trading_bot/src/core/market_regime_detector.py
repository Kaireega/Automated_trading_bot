"""
Market Regime Detection & Dynamic Strategy Adaptation - Identifies market conditions and adapts strategies.
Uses existing technical indicators and market data.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
import statistics

import sys
from pathlib import Path

# Add the project root to the path to import API modules
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.append(str(root_dir))

from ..core.models import MarketContext, TechnicalIndicators, CandleData, MarketCondition
from technicals.indicators import RSI, MACD, BollingerBands, ATR  # noqa: F401 (kept for future use)
from ..utils.config import Config
from ..utils.logger import get_logger


class MarketRegimeDetector:
    """Market regime detection and strategy adaptation system."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger(__name__)
        
        # Regime definitions
        self.regimes = {
            'TRENDING_UP': 'Strong uptrend with momentum',
            'TRENDING_DOWN': 'Strong downtrend with momentum',
            'RANGING': 'Sideways movement with support/resistance',
            'VOLATILE': 'High volatility with unpredictable moves',
            'BREAKOUT': 'Price breaking key levels with volume',
            'CONSOLIDATION': 'Low volatility, tight range',
            'REVERSAL': 'Potential trend reversal forming'
        }
        
        # Regime detection parameters
        self.trend_threshold = 0.6  # Minimum trend strength for trending regime
        self.volatility_threshold = 0.2  # High volatility threshold
        self.ranging_threshold = 0.1  # Low volatility for ranging
        self.consolidation_threshold = 0.05  # Very low volatility for consolidation
        
        # Strategy parameters for each regime
        self.regime_strategies = {
            'TRENDING_UP': {
                'timeframes': ['M5', 'M15'],  # Focus on shorter timeframes
                'indicators': ['EMA', 'MACD', 'RSI'],
                'entry_method': 'pullback',
                'stop_loss_multiplier': 1.5,
                'take_profit_multiplier': 2.5,
                'position_size_multiplier': 1.2,
                'hold_time_minutes': [60, 300]
            },
            'TRENDING_DOWN': {
                'timeframes': ['M5', 'M15'],
                'indicators': ['EMA', 'MACD', 'RSI'],
                'entry_method': 'pullback',
                'stop_loss_multiplier': 1.5,
                'take_profit_multiplier': 2.5,
                'position_size_multiplier': 1.2,
                'hold_time_minutes': [60, 300]
            },
            'RANGING': {
                'timeframes': ['M1', 'M5'],
                'indicators': ['BollingerBands', 'RSI', 'Stochastic'],
                'entry_method': 'bounce',
                'stop_loss_multiplier': 1.0,
                'take_profit_multiplier': 1.5,
                'position_size_multiplier': 0.8,
                'hold_time_minutes': [30, 120]
            },
            'VOLATILE': {
                'timeframes': ['M1', 'M5'],
                'indicators': ['ATR', 'BollingerBands', 'Keltner'],
                'entry_method': 'momentum',
                'stop_loss_multiplier': 2.0,
                'take_profit_multiplier': 3.0,
                'position_size_multiplier': 0.6,
                'hold_time_minutes': [15, 60]
            },
            'BREAKOUT': {
                'timeframes': ['M5', 'M15'],
                'indicators': ['BollingerBands', 'Volume', 'ATR'],
                'entry_method': 'breakout',
                'stop_loss_multiplier': 1.2,
                'take_profit_multiplier': 2.0,
                'position_size_multiplier': 1.0,
                'hold_time_minutes': [120, 480]
            },
            'CONSOLIDATION': {
                'timeframes': ['M15', 'M30'],
                'indicators': ['BollingerBands', 'RSI'],
                'entry_method': 'range_break',
                'stop_loss_multiplier': 1.0,
                'take_profit_multiplier': 1.5,
                'position_size_multiplier': 0.7,
                'hold_time_minutes': [180, 600]
            },
            'REVERSAL': {
                'timeframes': ['M15', 'M30'],
                'indicators': ['RSI', 'MACD', 'Candle_Patterns'],
                'entry_method': 'confirmation',
                'stop_loss_multiplier': 1.8,
                'take_profit_multiplier': 2.5,
                'position_size_multiplier': 0.9,
                'hold_time_minutes': [240, 720]
            }
        }
        
        # Regime memory and learning
        self.regime_history: List[Dict[str, Any]] = []
        self.regime_performance: Dict[str, Dict[str, Any]] = {}
        self.current_regime = 'UNKNOWN'
        self.regime_confidence = 0.0
        self.regime_duration = 0
        
        # Adaptive parameters
        self.adaptive_timeframes = True
        self.adaptive_indicators = True
        self.adaptive_sizing = True
        
        # Performance tracking
        self.regime_trades: Dict[str, List[Dict[str, Any]]] = {}
    
    async def start(self) -> None:
        """Start market regime detection system."""
        print("📈 [DEBUG] Starting market regime detector...")
        self.logger.info("Starting market regime detector...")
        
        print("📊 [DEBUG] Loading regime history...")
        await self._load_regime_history()
        print("✅ [DEBUG] Regime history loaded")
        
        print("✅ [DEBUG] Market regime detector started successfully")
        self.logger.info("Market regime detector started successfully")
    
    async def stop(self) -> None:
        """Stop market regime detection system."""
        self.logger.info("Stopping market regime detector...")
        self.logger.info("Market regime detector stopped")
    
    async def detect_regime(self, pair: str, candles: List[CandleData], 
                          market_context: MarketContext, 
                          technical_indicators: TechnicalIndicators) -> Dict[str, Any]:
        """Detect current market regime for a pair."""
        self.logger.info(f"📊 Starting market regime detection for {pair}...")
        
        try:
            self.logger.info(f"📈 {pair}: Analyzing {len(candles)} candles")
            
            # Calculate regime indicators
            self.logger.info(f"📊 {pair}: Calculating trend strength...")
            trend_strength = await self._calculate_trend_strength(candles)
            self.logger.info(f"📊 {pair}: Trend strength: {trend_strength:.3f}")
            
            self.logger.info(f"📊 {pair}: Calculating volatility level...")
            volatility_level = await self._calculate_volatility_level(candles, market_context)
            self.logger.info(f"📊 {pair}: Volatility level: {volatility_level:.3f}")
            
            self.logger.info(f"📊 {pair}: Calculating momentum score...")
            momentum_score = await self._calculate_momentum_score(technical_indicators)
            self.logger.info(f"📊 {pair}: Momentum score: {momentum_score:.3f}")
            
            self.logger.info(f"📊 {pair}: Calculating support/resistance levels...")
            support_resistance = await self._analyze_support_resistance(candles)
            self.logger.info(f"📊 {pair}: Support/Resistance - Support: {support_resistance['strength']:.5f}, Resistance: {support_resistance['strength']:.5f}")
            
            # Determine market regime
            self.logger.info(f"🎯 {pair}: Determining market regime...")
            regime = self._determine_regime(trend_strength, volatility_level, momentum_score, support_resistance)
            self.logger.info(f"🎯 {pair}: Detected regime: {regime}")
            
            # Calculate confidence
            self.logger.info(f"📊 {pair}: Calculating confidence...")
            confidence = self._calculate_regime_confidence(trend_strength, volatility_level, momentum_score, support_resistance)
            self.logger.info(f"📊 {pair}: Confidence: {confidence:.3f}")
            
            # Get strategy parameters
            strategy_params = self._get_strategy_parameters(regime)
            self.logger.info(f"📊 {pair}: Strategy params: {str(strategy_params)[:100]}...")
            
            result = {
                'regime': regime,
                'confidence': confidence,
                'trend_strength': trend_strength,
                'volatility_level': volatility_level,
                'momentum_score': momentum_score,
                'support_resistance': support_resistance,
                'strategy_params': strategy_params,
                'detection_timestamp': datetime.now()
            }
            
            self.logger.info(f"✅ Market regime detection completed for {pair}")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Error in market regime detection for {pair}: {e}")
            return {
                'regime': 'UNKNOWN',
                'confidence': 0.0,
                'error': str(e),
                'detection_timestamp': datetime.now()
            }
    
    async def _calculate_trend_strength(self, candles: List[CandleData]) -> float:
        """Calculate trend strength using multiple methods."""
        if len(candles) < 20:
            return 0.5
        
        # Method 1: Linear regression slope
        prices = [float(c.close) for c in candles]
        n = len(prices)
        x = list(range(n))
        
        x_mean = sum(x) / n
        y_mean = sum(prices) / n
        
        numerator = sum((x[i] - x_mean) * (prices[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator
        
        # Method 2: EMA alignment
        ema_fast = [float(c.close) for c in candles[-10:]]  # Last 10 candles
        ema_slow = [float(c.close) for c in candles[-20:]]  # Last 20 candles
        
        ema_alignment = 1.0 if ema_fast[-1] > ema_slow[-1] else 0.0
        
        # Method 3: Price position relative to moving averages
        current_price = prices[-1]
        sma_20 = sum(prices[-20:]) / 20
        sma_50 = sum(prices[-50:]) / 50 if len(prices) >= 50 else sma_20
        
        price_position = 1.0 if current_price > sma_20 > sma_50 else 0.0
        
        # Combine methods
        trend_strength = (abs(slope) * 0.4 + ema_alignment * 0.3 + price_position * 0.3)
        
        return min(1.0, trend_strength)
    
    async def _calculate_volatility_level(self, candles: List[CandleData], 
                                        market_context: MarketContext) -> float:
        """Calculate volatility level."""
        # Use existing volatility calculation from market context
        volatility = market_context.volatility / 100.0  # Convert from percentage
        return max(0.0, min(1.0, volatility))  # Ensure between 0 and 1
        
        # Normalize to 0-1 scale
        if volatility > 0.5:
            return 1.0
        elif volatility > 0.2:
            return 0.7
        elif volatility > 0.1:
            return 0.4
        else:
            return 0.2
    
    async def _calculate_momentum_score(self, technical_indicators: TechnicalIndicators) -> float:
        """Calculate momentum score using technical indicators."""
        momentum_score = 0.0
        indicators_count = 0
        
        # Check if technical_indicators is None
        if technical_indicators is None:
            raise ValueError("Technical indicators cannot be None for momentum calculation")
        
        # RSI momentum
        if hasattr(technical_indicators, 'rsi') and technical_indicators.rsi is not None:
            rsi = technical_indicators.rsi
            if rsi > 70:
                momentum_score += 0.8  # Strong bullish momentum
            elif rsi > 60:
                momentum_score += 0.6  # Moderate bullish momentum
            elif rsi < 30:
                momentum_score += 0.2  # Strong bearish momentum
            elif rsi < 40:
                momentum_score += 0.4  # Moderate bearish momentum
            else:
                momentum_score += 0.5  # Neutral
            indicators_count += 1
        
        # MACD momentum
        if (hasattr(technical_indicators, 'macd') and technical_indicators.macd is not None and 
            hasattr(technical_indicators, 'macd_signal') and technical_indicators.macd_signal is not None):
            macd = technical_indicators.macd
            macd_signal = technical_indicators.macd_signal
            
            if macd > macd_signal and macd > 0:
                momentum_score += 0.8  # Strong bullish
            elif macd > macd_signal:
                momentum_score += 0.6  # Moderate bullish
            elif macd < macd_signal and macd < 0:
                momentum_score += 0.2  # Strong bearish
            elif macd < macd_signal:
                momentum_score += 0.4  # Moderate bearish
            else:
                momentum_score += 0.5  # Neutral
            indicators_count += 1
        
        # EMA momentum
        if (hasattr(technical_indicators, 'ema_fast') and technical_indicators.ema_fast is not None and 
            hasattr(technical_indicators, 'ema_slow') and technical_indicators.ema_slow is not None):
            ema_fast = technical_indicators.ema_fast
            ema_slow = technical_indicators.ema_slow
            
            if ema_fast > ema_slow:
                momentum_score += 0.7  # Bullish
            else:
                momentum_score += 0.3  # Bearish
            indicators_count += 1
        
        # Average momentum score
        if indicators_count > 0:
            return momentum_score / indicators_count
        else:
            return 0.5
    
    async def _analyze_support_resistance(self, candles: List[CandleData]) -> Dict[str, Any]:
        """Analyze support and resistance levels."""
        if len(candles) < 20:
            return {'strength': 0.5, 'levels': []}
        
        prices = [float(c.close) for c in candles]
        highs = [float(c.high) for c in candles]
        lows = [float(c.low) for c in candles]
        
        current_price = prices[-1]
        
        # Find recent highs and lows
        recent_highs = sorted(highs[-20:], reverse=True)[:3]
        recent_lows = sorted(lows[-20:])[:3]
        
        # Calculate distance to nearest levels
        distance_to_resistance = min(abs(current_price - high) for high in recent_highs)
        distance_to_support = min(abs(current_price - low) for low in recent_lows)
        
        # Normalize distances
        price_range = max(prices) - min(prices)
        if price_range == 0:
            return {'strength': 0.5, 'levels': []}
        
        resistance_strength = 1.0 - (distance_to_resistance / price_range)
        support_strength = 1.0 - (distance_to_support / price_range)
        
        # Overall support/resistance strength
        overall_strength = (resistance_strength + support_strength) / 2
        
        return {
            'strength': overall_strength,
            'resistance_levels': recent_highs,
            'support_levels': recent_lows,
            'distance_to_resistance': distance_to_resistance,
            'distance_to_support': distance_to_support
        }
    
    # Removed unused _analyze_volume_profile; integrate later if volume is used in regime
    
    def _determine_regime(self, trend_strength: float, volatility_level: float,
                         momentum_score: float, support_resistance: Dict[str, Any]) -> str:
        """Determine market regime based on indicators."""
        # Consolidation (low volatility, low trend)
        if volatility_level < 0.3 and trend_strength < 0.3:
            return 'CONSOLIDATION'
        
        # Volatile (high volatility, low trend)
        if volatility_level > 0.7 and trend_strength < 0.4:
            return 'VOLATILE'
        
        # Trending up (strong trend, momentum > 0.6)
        if trend_strength > self.trend_threshold and momentum_score > 0.6:
            return 'TRENDING_UP'
        
        # Trending down (strong trend, momentum < 0.4)
        if trend_strength > self.trend_threshold and momentum_score < 0.4:
            return 'TRENDING_DOWN'
        
        # Breakout (high volume, breaking levels)
        if (support_resistance['strength'] > 0.6): # Assuming volume_profile is not directly used here
            return 'BREAKOUT'
        
        # Reversal (momentum divergence, pattern formation)
        if (0.4 <= momentum_score <= 0.6 and 
            support_resistance['strength'] > 0.5):
            return 'REVERSAL'
        
        # Default to ranging
        return 'RANGING'
    
    def _calculate_regime_confidence(self, trend_strength: float, volatility_level: float,
                                   momentum_score: float, support_resistance: Dict[str, Any]) -> float:
        """Calculate confidence in regime detection."""
        # Higher confidence when indicators align
        confidence_factors = []
        
        # Trend strength confidence
        if trend_strength > 0.7:
            confidence_factors.append(0.9)
        elif trend_strength > 0.5:
            confidence_factors.append(0.7)
        else:
            confidence_factors.append(0.5)
        
        # Volatility confidence
        if volatility_level > 0.7 or volatility_level < 0.3:
            confidence_factors.append(0.8)
        else:
            confidence_factors.append(0.6)
        
        # Momentum confidence
        if momentum_score > 0.7 or momentum_score < 0.3:
            confidence_factors.append(0.8)
        else:
            confidence_factors.append(0.6)
        
        # Support/resistance confidence
        confidence_factors.append(support_resistance['strength'])
        
        # Volume confidence
        # volume_profile = await self._analyze_volume_profile(candles) # This line was removed from detect_regime
        # confidence_factors.append(volume_profile['breakout_potential']) # This line was removed from detect_regime
        
        # Average confidence
        return sum(confidence_factors) / len(confidence_factors)
    
    async def _update_regime_history(self, pair: str, regime: str, confidence: float) -> None:
        """Update regime history and track duration."""
        current_time = datetime.now(timezone.utc)
        
        # Check if regime changed
        if regime != self.current_regime:
            # Record previous regime performance
            if self.current_regime != 'UNKNOWN':
                await self._record_regime_performance(pair, self.current_regime)
            
            # Start new regime
            self.current_regime = regime
            self.regime_duration = 0
            self.regime_confidence = confidence
            
            self.logger.info(f"🔄 Regime change for {pair}: {regime} (confidence: {confidence:.2f})")
        else:
            # Update existing regime
            self.regime_duration += 1
            self.regime_confidence = (self.regime_confidence + confidence) / 2
        
        # Add to history
        regime_record = {
            'pair': pair,
            'regime': regime,
            'confidence': confidence,
            'timestamp': current_time,
            'duration': self.regime_duration
        }
        
        self.regime_history.append(regime_record)
        
        # Keep only recent history
        if len(self.regime_history) > 1000:
            self.regime_history = self.regime_history[-1000:]
    
    def _get_strategy_parameters(self, regime: str) -> Dict[str, Any]:
        """Get strategy parameters for a specific regime."""
        return self.regime_strategies.get(regime, self.regime_strategies['RANGING'])
    
    async def _adapt_strategy_parameters(self, pair: str, regime: str, 
                                       base_params: Dict[str, Any]) -> Dict[str, Any]:
        """Adapt strategy parameters based on historical performance."""
        adapted_params = base_params.copy()
        
        # Get historical performance for this regime
        regime_perf = self.regime_performance.get(regime, {})
        win_rate = regime_perf.get('win_rate', 0.5)
        profit_factor = regime_perf.get('profit_factor', 1.0)
        
        # Adjust position sizing based on performance
        if self.adaptive_sizing:
            if win_rate > 0.6 and profit_factor > 1.5:
                # Good performance - increase size
                adapted_params['position_size_multiplier'] *= 1.2
            elif win_rate < 0.4 or profit_factor < 1.0:
                # Poor performance - decrease size
                adapted_params['position_size_multiplier'] *= 0.8
        
        # Adjust timeframes based on regime duration
        if self.adaptive_timeframes and self.regime_duration > 100:
            # Long regime - use longer timeframes
            if 'M1' in adapted_params['timeframes']:
                adapted_params['timeframes'].remove('M1')
                adapted_params['timeframes'].append('M30')
        
        # Adjust stop loss based on volatility
        if regime == 'VOLATILE':
            adapted_params['stop_loss_multiplier'] *= 1.5
        elif regime == 'CONSOLIDATION':
            adapted_params['stop_loss_multiplier'] *= 0.8
        
        return adapted_params
    
    async def _record_regime_performance(self, pair: str, regime: str) -> None:
        """Record performance for a regime."""
        if regime not in self.regime_trades:
            self.regime_trades[regime] = []
        
        # This would be populated with actual trade results
        # For now, just track the regime
        self.regime_trades[regime].append({
            'pair': pair,
            'regime': regime,
            'duration': self.regime_duration,
            'timestamp': datetime.now(timezone.utc)
        })
    
    async def _load_regime_history(self) -> None:
        """Load regime history from storage."""
        # This would load from database or file
        # For now, initialize empty
        self.regime_history = []
        self.regime_performance = {}
    
    async def get_regime_summary(self) -> Dict[str, Any]:
        """Get summary of current regime detection."""
        return {
            'current_regime': self.current_regime,
            'regime_confidence': self.regime_confidence,
            'regime_duration': self.regime_duration,
            'regime_description': self.regimes.get(self.current_regime, 'Unknown'),
            'total_regimes_detected': len(set(r['regime'] for r in self.regime_history)),
            'regime_performance': self.regime_performance
        }
    
    async def get_adaptive_parameters(self, pair: str) -> Dict[str, Any]:
        """Get adaptive parameters for current market conditions."""
        # This would return the most effective parameters based on current regime
        return {
            'timeframes': self._get_optimal_timeframes(),
            'indicators': self._get_optimal_indicators(),
            'position_sizing': self._get_optimal_sizing(),
            'risk_management': self._get_optimal_risk()
        }
    
    def _get_optimal_timeframes(self) -> List[str]:
        """Get optimal timeframes for current regime."""
        if self.current_regime in ['TRENDING_UP', 'TRENDING_DOWN']:
            return ['M5', 'M15']
        elif self.current_regime == 'VOLATILE':
            return ['M1', 'M5']
        elif self.current_regime == 'CONSOLIDATION':
            return ['M15', 'M30']
        else:
            return ['M5', 'M15']
    
    def _get_optimal_indicators(self) -> List[str]:
        """Get optimal indicators for current regime."""
        if self.current_regime in ['TRENDING_UP', 'TRENDING_DOWN']:
            return ['EMA', 'MACD', 'RSI']
        elif self.current_regime == 'RANGING':
            return ['BollingerBands', 'RSI', 'Stochastic']
        elif self.current_regime == 'VOLATILE':
            return ['ATR', 'BollingerBands', 'Keltner']
        else:
            return ['RSI', 'MACD', 'BollingerBands']
    
    def _get_optimal_sizing(self) -> Dict[str, Any]:
        """Get optimal position sizing for current regime."""
        base_sizing = {
            'max_position_size': 0.1,
            'risk_per_trade': 0.02,
            'max_correlation': 0.7
        }
        
        if self.current_regime == 'VOLATILE':
            base_sizing['max_position_size'] *= 0.6
            base_sizing['risk_per_trade'] *= 0.8
        elif self.current_regime in ['TRENDING_UP', 'TRENDING_DOWN']:
            base_sizing['max_position_size'] *= 1.2
            base_sizing['risk_per_trade'] *= 1.1
        
        return base_sizing
    
    def _get_optimal_risk(self) -> Dict[str, Any]:
        """Get optimal risk management for current regime."""
        base_risk = {
            'stop_loss_multiplier': 1.5,
            'take_profit_multiplier': 2.0,
            'trailing_stop': True
        }
        
        if self.current_regime == 'VOLATILE':
            base_risk['stop_loss_multiplier'] *= 1.5
            base_risk['take_profit_multiplier'] *= 1.5
        elif self.current_regime == 'CONSOLIDATION':
            base_risk['stop_loss_multiplier'] *= 0.8
            base_risk['take_profit_multiplier'] *= 0.8
        
        return base_risk 