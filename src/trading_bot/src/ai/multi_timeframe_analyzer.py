"""
Multi-Timeframe Analyzer - Advanced analysis across multiple timeframes.
"""
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
import statistics

from ..core.models import (
    CandleData, TimeFrame, MarketContext, TradeRecommendation, 
    TradeSignal, TechnicalIndicators, MarketCondition
)
from ..utils.logger import get_logger
from ..utils.config import Config


class MultiTimeframeAnalyzer:
    """Advanced multi-timeframe analysis and consensus generation."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger(__name__)
        
        # Timeframe weights (higher weight = more importance)
        self.timeframe_weights = {
            TimeFrame.M1: 0.1,   # 10% weight - noise filtering
            TimeFrame.M5: 0.3,   # 30% weight - short-term signals
            TimeFrame.M15: 0.4,  # 40% weight - medium-term trends
            TimeFrame.H1: 0.2    # 20% weight - long-term context
        }
        
        # Signal strength thresholds - READ FROM CONFIG (with fallbacks)
        self.signal_thresholds = getattr(config.technical_analysis, 'signal_thresholds', {
            'strong_buy': 0.8, 'buy': 0.6, 'neutral': 0.4, 'sell': 0.6, 'strong_sell': 0.8
        })
        
        # CONFIGURABLE THRESHOLDS - Read from config instead of hardcoding
        self.min_risk_reward = config.technical_analysis.risk_reward_ratio_minimum
        self.min_confidence = config.technical_analysis.confidence_threshold
        self.ranging_confidence_penalty = getattr(config.technical_analysis, 'ranging_confidence_penalty', 0.05)
        
        self.logger.info(f"🔧 MultiTimeframeAnalyzer initialized with configurable thresholds:")
        self.logger.info(f"   Min Risk/Reward: {self.min_risk_reward}")
        self.logger.info(f"   Min Confidence: {self.min_confidence}")
        self.logger.info(f"   RANGING Penalty: {self.ranging_confidence_penalty}")
    
    async def analyze(self, pair: str, candles_by_timeframe: Dict[TimeFrame, List[CandleData]], 
                     technical_indicators: TechnicalIndicators, market_context: MarketContext) -> Optional[TradeRecommendation]:
        """Analyze multiple timeframes and generate consensus recommendation."""
        try:
            # Store for ATR calculation in consensus
            self.last_candles_by_timeframe = candles_by_timeframe
            # Analyze each timeframe
            timeframe_analyses = {}
            for timeframe, candles in candles_by_timeframe.items():
                try:
                    if len(candles) >= 20:  # Minimum candles required
                        analysis = await self._analyze_single_timeframe(
                            pair, timeframe, candles, technical_indicators, market_context
                        )
                        timeframe_analyses[timeframe] = analysis
                except Exception as e:
                    self.logger.error(f"Invalid timeframe {timeframe} for {pair}: {e}")
                    continue
            
            if len(timeframe_analyses) < 2:
                return None
            
            # Generate consensus recommendation
            recommendation = await self._generate_consensus_recommendation(
                pair, timeframe_analyses, market_context
            )
            
            return recommendation
            
        except Exception as e:
            self.logger.error(f"Error in multi-timeframe analysis for {pair}: {e}")
            return None
    
    async def _analyze_single_timeframe(self, pair: str, timeframe: TimeFrame, candles: List[CandleData], 
                                      technical_indicators: TechnicalIndicators, market_context: MarketContext) -> Dict[str, Any]:
        """Analyze a single timeframe and return analysis results."""
        try:
            
            if len(candles) < 20:
                return None
            
            # Calculate basic price metrics
            closes = [float(candle.close) for candle in candles]
            highs = [float(candle.high) for candle in candles]
            lows = [float(candle.low) for candle in candles]
            
            current_price = closes[-1]
            price_change = ((current_price - closes[0]) / closes[0]) * 100
            
            # Calculate volatility
            volatility = (max(highs) - min(lows)) / current_price * 100
            
            # Determine trend
            if price_change > 0.1:
                trend = "BULLISH"
            elif price_change < -0.1:
                trend = "BEARISH"
            else:
                trend = "NEUTRAL"
            
            # Analyze technical indicators
            signal_strength = 0.0
            signal_direction = "NEUTRAL"
            
            if technical_indicators and hasattr(technical_indicators, 'rsi'):
                # RSI analysis
                if technical_indicators.rsi is not None:
                    if technical_indicators.rsi > 70:
                        signal_strength += 0.3
                        signal_direction = "SELL"
                    elif technical_indicators.rsi < 30:
                        signal_strength += 0.3
                        signal_direction = "BUY"
                
                # MACD analysis
                if technical_indicators.macd is not None and technical_indicators.macd_signal is not None:
                    if technical_indicators.macd > technical_indicators.macd_signal:
                        signal_strength += 0.2
                        if signal_direction == "NEUTRAL":
                            signal_direction = "BUY"
                    else:
                        signal_strength -= 0.2
                        if signal_direction == "NEUTRAL":
                            signal_direction = "SELL"
                
                # EMA analysis
                if hasattr(technical_indicators, 'ema_fast') and hasattr(technical_indicators, 'ema_slow'):
                    if technical_indicators.ema_fast is not None and technical_indicators.ema_slow is not None:
                        if technical_indicators.ema_fast > technical_indicators.ema_slow:
                            signal_strength += 0.2
                            if signal_direction == "NEUTRAL":
                                signal_direction = "BUY"
                        else:
                            signal_strength -= 0.2
                            if signal_direction == "NEUTRAL":
                                signal_direction = "SELL"
            else:
                return None
            
            confidence = min(1.0, abs(signal_strength))
            
            result = {
                'timeframe': timeframe.value,
                'trend': trend,
                'price_change': price_change,
                'volatility': volatility,
                'signal_strength': signal_strength,
                'signal_direction': signal_direction,
                'current_price': current_price,
                'confidence': confidence
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error analyzing {timeframe} timeframe for {pair}: {e}")
            return None
    

    
    def _calculate_trend_direction(self, candles: List[CandleData]) -> float:
        """Calculate trend direction (-1 to 1, where 1 is strongly bullish)."""
        if len(candles) < 10:
            return 0.0
        
        # Use linear regression on recent prices
        prices = [float(c.close) for c in candles[-10:]]
        x = list(range(len(prices)))
        
        # Simple linear regression
        n = len(prices)
        sum_x = sum(x)
        sum_y = sum(prices)
        sum_xy = sum(x[i] * prices[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))
        
        if n * sum_x2 - sum_x ** 2 == 0:
            return 0.0
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
        
        # Normalize slope to -1 to 1 range
        max_price = max(prices)
        normalized_slope = slope / max_price if max_price > 0 else 0
        
        return max(-1.0, min(1.0, normalized_slope * 100))
    
    def _calculate_momentum(self, candles: List[CandleData]) -> float:
        """Calculate price momentum."""
        if len(candles) < 5:
            return 0.0
        
        # Calculate rate of change
        recent_prices = [float(c.close) for c in candles[-5:]]
        momentum = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
        
        return float(momentum)
    
    def _calculate_volatility(self, candles: List[CandleData]) -> float:
        """Calculate price volatility."""
        if len(candles) < 10:
            return 0.0
        
        prices = [float(c.close) for c in candles[-10:]]
        returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
        
        return float(statistics.stdev(returns)) if len(returns) > 1 else 0.0
    
    def _analyze_technical_indicators(self, indicators: TechnicalIndicators) -> float:
        """Analyze technical indicators and return a score (-1 to 1)."""
        if not indicators:
            return 0.0
        
        score = 0.0
        count = 0
        
        # RSI analysis
        if indicators.rsi is not None:
            if indicators.rsi < 30:
                score += 0.5  # Oversold - bullish (increased from 0.3)
            elif indicators.rsi > 70:
                score -= 0.5  # Overbought - bearish (increased from 0.3)
            count += 1
        
        # MACD analysis
        if indicators.macd is not None and indicators.macd_signal is not None:
            if indicators.macd > indicators.macd_signal:
                score += 0.4  # Bullish MACD (increased from 0.2)
            else:
                score -= 0.4  # Bearish MACD (increased from 0.2)
            count += 1
        
        # EMA analysis
        if indicators.ema_fast is not None and indicators.ema_slow is not None:
            if indicators.ema_fast > indicators.ema_slow:
                score += 0.4  # Bullish EMA (increased from 0.2)
            else:
                score -= 0.4  # Bearish EMA (increased from 0.2)
            count += 1
        
        # Stochastic analysis
        if indicators.stoch_k is not None:
            if indicators.stoch_k < 20:
                score += 0.3  # Oversold (increased from 0.1)
            elif indicators.stoch_k > 80:
                score -= 0.3  # Overbought (increased from 0.1)
            count += 1
        
        return score / count if count > 0 else 0.0
    
    def _calculate_signal_strength(
        self, 
        trend_direction: float, 
        momentum: float, 
        volatility: float, 
        technical_score: float,
        timeframe: TimeFrame
    ) -> float:
        """Calculate overall signal strength."""
        
        # Weight the components based on timeframe
        if timeframe == TimeFrame.M1:
            # M1 is more noise, focus on momentum
            weights = {'trend': 0.2, 'momentum': 0.5, 'technical': 0.3}
        elif timeframe == TimeFrame.M5:
            # M5 balances all factors
            weights = {'trend': 0.3, 'momentum': 0.4, 'technical': 0.3}
        elif timeframe == TimeFrame.M15:
            # M15 focuses on trend
            weights = {'trend': 0.5, 'momentum': 0.3, 'technical': 0.2}
        else:  # H1
            # H1 focuses heavily on trend
            weights = {'trend': 0.6, 'momentum': 0.2, 'technical': 0.2}
        
        # Calculate weighted score
        score = (
            trend_direction * weights['trend'] +
            momentum * weights['momentum'] +
            technical_score * weights['technical']
        )
        
        # Adjust for volatility (higher volatility = lower confidence)
        # Reduced penalty multiplier from 10 to 2 for more reasonable signal strength
        volatility_penalty = min(volatility * 2, 0.1)  # Max 10% penalty instead of 30%
        score *= (1 - volatility_penalty)
        
        return max(-1.0, min(1.0, score))
    
    def _determine_signal_type(self, signal_strength: float) -> str:
        """Determine signal type based on strength."""
        if signal_strength >= self.signal_thresholds['strong_buy']:
            return 'strong_buy'
        elif signal_strength >= self.signal_thresholds['buy']:
            return 'buy'
        elif signal_strength <= -self.signal_thresholds['strong_sell']:
            return 'strong_sell'
        elif signal_strength <= -self.signal_thresholds['sell']:
            return 'sell'
        else:
            return 'neutral'
    
    def _calculate_trade_levels(
        self, 
        candles: List[CandleData], 
        signal_type: str, 
        timeframe: TimeFrame
    ) -> Tuple[Decimal, Decimal, Decimal]:
        """Calculate entry, stop loss, and take profit levels."""
        
        current_price = candles[-1].close
        
        # Calculate ATR for stop loss
        atr = self._calculate_atr(candles)
        
        # Adjust hold time based on timeframe and signal strength
        if timeframe == TimeFrame.M1:
            base_hold_time = 30  # 30 minutes for M1
        elif timeframe == TimeFrame.M5:
            base_hold_time = 60  # 1 hour for M5
        elif timeframe == TimeFrame.M15:
            base_hold_time = 120  # 2 hours for M15
        elif timeframe == TimeFrame.H1:
            base_hold_time = 240  # 4 hours for H1
        else:
            base_hold_time = 180  # 3 hours default
        
        # Adjust based on signal strength
        if 'strong' in signal_type:
            hold_time = base_hold_time * 1.5  # Stronger signals can hold longer
        else:
            hold_time = base_hold_time
        
        # Cap at maximum 5 hours (300 minutes)
        hold_time = min(hold_time, 300)
        
        # Calculate levels based on ATR for WINNING trades
        if signal_type in ['buy', 'strong_buy']:
            entry_price = current_price
            stop_loss = current_price - (atr * 1.5)  # Tighter stop loss for better R:R
            take_profit = current_price + (atr * 3)  # 3x ATR for take profit (1:2 risk/reward)
        elif signal_type in ['sell', 'strong_sell']:
            entry_price = current_price
            stop_loss = current_price + (atr * 1.5)  # Tighter stop loss for better R:R
            take_profit = current_price - (atr * 3)  # 3x ATR for take profit (1:2 risk/reward)
        else:
            entry_price = current_price
            stop_loss = current_price
            take_profit = current_price
        
        return entry_price, stop_loss, take_profit
    
    def _calculate_atr(self, candles: List[CandleData], period: int = 14) -> Decimal:
        """Calculate Average True Range."""
        if len(candles) < period + 1:
            return Decimal('0.001')
        
        true_ranges = []
        for i in range(1, len(candles)):
            high_low = candles[i].high - candles[i].low
            high_close = abs(candles[i].high - candles[i-1].close)
            low_close = abs(candles[i].low - candles[i-1].close)
            true_range = max(high_low, high_close, low_close)
            true_ranges.append(true_range)
        
        # Calculate average
        atr = sum(true_ranges[-period:]) / period
        return atr
    
    def _calculate_risk_reward_ratio(
        self, 
        entry_price: Decimal, 
        stop_loss: Decimal, 
        take_profit: Decimal
    ) -> float:
        """Calculate risk-reward ratio."""
        if entry_price == stop_loss:
            return 0.0
        
        risk = abs(float(entry_price - stop_loss))
        reward = abs(float(take_profit - entry_price))
        
        return reward / risk if risk > 0 else 0.0
    
    async def _generate_consensus_recommendation(
        self, 
        pair: str, 
        timeframe_analyses: Dict[TimeFrame, Dict[str, Any]],
        market_context: MarketContext
    ) -> Optional[TradeRecommendation]:
        """Generate consensus recommendation from multiple timeframes."""
        
        try:
            if not timeframe_analyses:
                return None
            
            # Calculate weighted consensus
            weighted_signals = {}
            total_weight = 0.0
            
            for timeframe, analysis in timeframe_analyses.items():
                weight = self.timeframe_weights.get(timeframe, 0.1)
                signal_strength = analysis['signal_strength']
                
                # Convert signal strength to signal type
                if signal_strength > 0:
                    signal = 'buy' if signal_strength > 0.6 else 'weak_buy'
                else:
                    signal = 'sell' if signal_strength < -0.6 else 'weak_sell'
                
                weighted_signals[signal] = weighted_signals.get(signal, 0) + (signal_strength * weight)
                total_weight += weight
                
            # Find dominant signal
            if not weighted_signals:
                return None
            
            dominant_signal = max(weighted_signals.items(), key=lambda x: abs(x[1]))
            
            # Get signal strength threshold from config (default to 0.03 if not set) - Production settings
            signal_threshold = getattr(self, 'config', None) and getattr(self.config, 'signal_strength_threshold', 0.03) or 0.03
            
            # Only proceed if signal is strong enough for WINNING trades
            if abs(dominant_signal[1]) < signal_threshold:
                return None
            
            # Additional WINNING trade filters
            # 1. Check if we have multiple timeframe confirmation
            if len(timeframe_analyses) < 2:
                return None
            
            # 2. Check if signal is consistent across timeframes
            consistent_signals = 0
            for timeframe, analysis in timeframe_analyses.items():
                expected_direction = dominant_signal[0].replace('weak_', '').upper()
                actual_direction = analysis.get('signal_direction', 'NEUTRAL')
                if analysis and actual_direction == expected_direction:
                    consistent_signals += 1
            
            if consistent_signals < 2:
                return None
            
            # Get best analysis for trade levels
            best_analysis = max(timeframe_analyses.values(), key=lambda x: abs(x['signal_strength']))
            
            # Calculate trade levels based on current price and ATR
            current_price = Decimal(str(best_analysis['current_price']))
            
            # Get candles from the best timeframe for ATR calculation
            best_timeframe = None
            for tf, analysis in timeframe_analyses.items():
                if analysis == best_analysis:
                    best_timeframe = tf
                    break
            
            if not best_timeframe:
                return None
            
            # Calculate ATR for stop loss and take profit from the selected timeframe
            # Use candles passed to the analyzer for the best timeframe
            from decimal import Decimal as _D
            atr = self._calculate_atr(candles=[])  # fallback
            try:
                # best_timeframe is determined above; candles_by_timeframe is available in caller
                # We pass through by storing it in the analyzer on analyze(), but here we recompute defensively
                # If unavailable, keep a minimal non-zero ATR to avoid div-by-zero
                if hasattr(self, 'last_candles_by_timeframe') and self.last_candles_by_timeframe:
                    best_candles = self.last_candles_by_timeframe.get(best_timeframe, [])
                    atr = self._calculate_atr(best_candles)
                if atr <= 0:
                    atr = _D('0.0001')
            except Exception:
                atr = _D('0.0001')
            
            # Calculate trade levels
            if dominant_signal[0] in ['buy', 'weak_buy']:
                final_signal = TradeSignal.BUY
                entry_price = current_price
                stop_loss = current_price - (atr * Decimal('1.5'))
                take_profit = current_price + (atr * Decimal('3.0'))
            elif dominant_signal[0] in ['sell', 'weak_sell']:
                final_signal = TradeSignal.SELL
                entry_price = current_price
                stop_loss = current_price + (atr * Decimal('1.5'))
                take_profit = current_price - (atr * Decimal('3.0'))
            else:
                final_signal = TradeSignal.HOLD
                entry_price = current_price
                stop_loss = current_price
                take_profit = current_price
            
            # Calculate consensus confidence
            consensus_confidence = abs(dominant_signal[1]) / total_weight
            
            # Calculate risk/reward ratio
            risk_reward_ratio = self._calculate_risk_reward_ratio(entry_price, stop_loss, take_profit)
            
            # Check risk/reward ratio using configurable threshold
            self.logger.info(f"🔍 Risk/Reward check: {risk_reward_ratio:.2f} vs {self.min_risk_reward}")
            if risk_reward_ratio < self.min_risk_reward:
                self.logger.info(f"❌ Risk/reward {risk_reward_ratio:.2f} < {self.min_risk_reward} (REJECTED)")
                return None
            else:
                self.logger.info(f"✅ Risk/reward check passed: {risk_reward_ratio:.2f} >= {self.min_risk_reward}")
            
            # Check minimum confidence using configurable threshold
            self.logger.info(f"🔍 Confidence check: {consensus_confidence:.3f} vs {self.min_confidence}")
            if consensus_confidence < self.min_confidence:
                self.logger.info(f"❌ Confidence {consensus_confidence:.3f} < {self.min_confidence} (REJECTED)")
                return None
            else:
                self.logger.info(f"✅ Confidence check passed: {consensus_confidence:.3f} >= {self.min_confidence}")
            
            # Market condition adjustments - CONFIGURABLE
            if market_context.condition in {MarketCondition.RANGING}:
                # For RANGING markets, apply small confidence penalty instead of hardcoded 0.8
                required_confidence = self.min_confidence + self.ranging_confidence_penalty
                self.logger.info(f"⚠️ RANGING market detected, requiring confidence: {required_confidence:.3f}")
                
                if consensus_confidence < required_confidence:
                    self.logger.info(f"❌ RANGING market confidence {consensus_confidence:.3f} < {required_confidence:.3f} (REJECTED)")
                    return None
                else:
                    self.logger.info(f"✅ RANGING market confidence check passed: {consensus_confidence:.3f} >= {required_confidence:.3f}")
            else:
                self.logger.info(f"✅ Market condition {market_context.condition.value} - no additional confidence requirement")
            
            # Create WINNING trade recommendation
                from datetime import datetime, timezone
                recommendation = TradeRecommendation(
                pair=pair,
                signal=final_signal,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                confidence=consensus_confidence,
                market_condition=market_context.condition,
                reasoning=f"WINNING trade setup: {len(timeframe_analyses)} timeframes, R:R {risk_reward_ratio:.2f}, Conf {consensus_confidence:.3f}",
                risk_reward_ratio=risk_reward_ratio,
                estimated_hold_time=timedelta(minutes=120),
                    timestamp=datetime.now(timezone.utc)
            )
            
            return recommendation
            
        except Exception as e:
            self.logger.error(f"Error generating consensus recommendation: {e}")
            return None
    
    def get_timeframe_summary(self, timeframe_analyses: Dict[TimeFrame, Dict[str, Any]]) -> Dict[str, Any]:
        """Get a summary of all timeframe analyses."""
        summary = {
            'timeframes_analyzed': len(timeframe_analyses),
            'signals': {},
            'average_confidence': 0.0,
            'consensus_signal': 'neutral'
        }
        
        if not timeframe_analyses:
            return summary
        
        # Count signals
        signal_counts = {}
        total_confidence = 0.0
        
        for timeframe, analysis in timeframe_analyses.items():
            signal = analysis['signal_type']
            signal_counts[signal] = signal_counts.get(signal, 0) + 1
            total_confidence += analysis['confidence']
        
        summary['signals'] = signal_counts
        summary['average_confidence'] = total_confidence / len(timeframe_analyses)
        
        # Determine consensus
        if signal_counts:
            dominant_signal = max(signal_counts.items(), key=lambda x: x[1])[0]
            summary['consensus_signal'] = dominant_signal
        
        return summary 