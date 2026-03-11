"""
Technical Analysis Layer - Pure Technical Analysis and Signal Generation.

This module provides comprehensive technical analysis capabilities without AI dependencies.
It calculates technical indicators, performs multi-timeframe analysis, and generates
trading signals based on traditional technical analysis methods.

Key Features:
- Multi-timeframe technical analysis
- Comprehensive indicator calculations (RSI, MACD, Bollinger Bands, etc.)
- Signal generation based on technical patterns
- Market condition detection
- Risk-reward ratio calculations
- Support and resistance level identification

Architecture:
- TechnicalAnalysisLayer: Main orchestrator for technical analysis
- TechnicalAnalyzer: Core indicator calculations
- MultiTimeframeAnalyzer: Multi-timeframe consensus analysis

The technical analysis layer is the primary signal generation component,
replacing AI-based analysis with proven technical analysis methods.

Author: Trading Bot Development Team
Version: 2.0.0
Last Updated: 2024
"""
import asyncio
import traceback
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal

try:
    from ..core.models import (
        CandleData, MarketContext, MarketCondition, TradeRecommendation, 
        TradeSignal, TechnicalIndicators, TimeFrame
    )
    from ..utils.config import Config
    from ..utils.logger import get_logger
    from .technical_analyzer import TechnicalAnalyzer
    from .multi_timeframe_analyzer import MultiTimeframeAnalyzer
    # Multi-Strategy Framework
    from ..strategies.strategy_manager import StrategyManager
    from ..strategies import register_all  # Register all strategies
except ImportError:
    # Fallback for when running as standalone module
    from core.models import (
        CandleData, MarketContext, MarketCondition, TradeRecommendation, 
        TradeSignal, TechnicalIndicators, TimeFrame
    )
    from utils.config import Config
    from utils.logger import get_logger
    from technical_analyzer import TechnicalAnalyzer
    from multi_timeframe_analyzer import MultiTimeframeAnalyzer
    # Multi-Strategy Framework
    try:
        from strategies.strategy_manager import StrategyManager
        from strategies import register_all
    except ImportError:
        StrategyManager = None


class TechnicalAnalysisLayer:
    """
    Technical analysis and signal generation system.
    
    This class orchestrates comprehensive technical analysis by combining
    multiple technical indicators, multi-timeframe analysis, and market
    condition detection to generate high-quality trading signals.
    
    Key Responsibilities:
    - Calculate technical indicators across multiple timeframes
    - Perform multi-timeframe consensus analysis
    - Generate trading signals based on technical patterns
    - Detect market conditions (trending, ranging, breakout)
    - Calculate risk-reward ratios and support/resistance levels
    - Provide confidence scoring for recommendations
    
    Components:
    - TechnicalAnalyzer: Core indicator calculations
    - MultiTimeframeAnalyzer: Multi-timeframe consensus
    - Signal generation and validation
    - Market condition analysis
    
    The layer replaces AI-based analysis with proven technical analysis
    methods, providing reliable and interpretable trading signals.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the Technical Analysis Layer.
        
        Args:
            config: Configuration object containing analysis parameters
            
        The initialization process:
        1. Sets up the technical analyzer for indicator calculations
        2. Initializes the multi-timeframe analyzer for consensus analysis
        3. Prepares analysis tracking and caching systems
        4. Configures logging for the analysis components
        """
        self.config = config
        self.logger = get_logger(__name__)
        
        # Initialize technical analyzer for indicator calculations
        self.technical_analyzer = TechnicalAnalyzer()
        self.technical_analyzer.logger = self.logger
        
        # Initialize multi-timeframe analyzer for consensus analysis with config
        self.multi_timeframe_analyzer = MultiTimeframeAnalyzer(config)
        self.multi_timeframe_analyzer.logger = self.logger
        
        # Initialize Multi-Strategy Framework
        self.strategy_manager = None
        if StrategyManager is not None:
            try:
                self.strategy_manager = StrategyManager(config)
                if self.strategy_manager.enabled:
                    strategy_count = self.strategy_manager.get_strategy_count()
                    self.logger.info(f"🎯 Multi-Strategy Framework ENABLED: {strategy_count} strategies loaded")
                else:
                    self.logger.info("📊 Multi-Strategy Framework disabled in config - using legacy approach")
            except Exception as e:
                self.logger.warning(f"⚠️ Failed to initialize Strategy Manager: {e}. Using legacy approach.")
                self.strategy_manager = None
        
        # Analysis tracking and caching
        self._last_analysis_time: Dict[str, datetime] = {}
        self._analysis_cache: Dict[str, TradeRecommendation] = {}
        
        # Technical thresholds - ALL READ FROM CONFIG (with fallbacks)
        self.rsi_oversold = getattr(config.technical_analysis, 'rsi_oversold', 30)
        self.rsi_overbought = getattr(config.technical_analysis, 'rsi_overbought', 70)
        self.macd_signal_threshold = getattr(config.technical_analysis, 'macd_signal_threshold', 0.0001)
        self.bollinger_threshold = getattr(config.technical_analysis, 'bollinger_threshold', 0.05)
        self.atr_multiplier = getattr(config.technical_analysis, 'atr_multiplier', 2.0)
        self.min_signal_strength = getattr(config.technical_analysis, 'signal_strength_threshold', 0.005)
        
        # Trade cooldown tracking to prevent excessive trading
        self._last_trade_time: Dict[str, datetime] = {}
        self.trade_cooldown_minutes = getattr(config.technical_analysis, 'trade_cooldown_minutes', 30)
        
    async def analyze_multiple_timeframes(
        self,
        pair: str,
        candles_by_timeframe: Dict[TimeFrame, List[CandleData]],
        market_context: MarketContext,
        current_time: Optional[datetime] = None
    ) -> Tuple[Optional[TradeRecommendation], Optional[TechnicalIndicators]]:
        """
        Analyze multiple timeframes and generate consensus trading recommendation.
        
        Args:
            pair: Currency pair symbol (e.g., 'EUR_USD')
            candles_by_timeframe: Dictionary of candles organized by timeframe
            market_context: Current market context and conditions
            
        Returns:
            Tuple[Optional[TradeRecommendation], Optional[TechnicalIndicators]]:
            - Trade recommendation if strong signal detected, None otherwise
            - Technical indicators for the primary timeframe
            
        This method performs comprehensive multi-timeframe analysis:
        1. Checks trade cooldown to prevent excessive trading
        2. Calculates technical indicators for all timeframes
        3. Validates market conditions for trading
        4. Generates consensus signals across timeframes
        5. Applies strict thresholds to filter weak signals
        6. Calculates risk-reward ratios and confidence scores
        """
        
        try:
            # CHECK TRADE COOLDOWN - Prevent excessive trading
            if current_time is None:
                current_time = datetime.now(timezone.utc)
            if pair in self._last_trade_time:
                time_since_last_trade = current_time - self._last_trade_time[pair]
                cooldown_remaining = timedelta(minutes=self.trade_cooldown_minutes) - time_since_last_trade
                
                if cooldown_remaining.total_seconds() > 0:
                    self.logger.debug(f"⏰ {pair}: Trade cooldown active - {cooldown_remaining.total_seconds()/60:.1f} minutes remaining")
                    return None, None
            
            # Calculate technical indicators for all timeframes
            technical_indicators = {}
            
            for timeframe, candles in candles_by_timeframe.items():
                self.logger.info(f"🔍 {pair} {timeframe.value}: {len(candles)} candles available")
                if len(candles) < 20:  # Need minimum data for indicators
                    self.logger.info(f"❌ {pair} {timeframe.value}: Insufficient candles ({len(candles)} < 20)")
                    continue
                    
                indicators = self.technical_analyzer.calculate_indicators(candles)
                technical_indicators[timeframe] = indicators
                self.logger.info(f"✅ {pair} {timeframe.value}: Technical indicators calculated")
            
            if not technical_indicators:
                self.logger.debug(f"❌ {pair}: No technical indicators calculated")
                return None, None
            
            # Get primary timeframe (M5) for main analysis
            primary_timeframe = TimeFrame.M5
            primary_indicators = technical_indicators.get(primary_timeframe)
            
            if not primary_indicators:
                # Fallback to first available timeframe
                primary_timeframe = list(technical_indicators.keys())[0]
                primary_indicators = technical_indicators[primary_timeframe]
            
            # TRY MULTI-STRATEGY CONSENSUS FIRST (if enabled)
            if self.strategy_manager and self.strategy_manager.enabled:
                try:
                    primary_candles = candles_by_timeframe.get(primary_timeframe, [])
                    if primary_candles:
                        # Derive regime string from market_condition for regime gate
                        regime_str = (
                            market_context.condition.value.upper()
                            if market_context and market_context.condition
                            else 'UNKNOWN'
                        )
                        consensus_recommendation = await self.strategy_manager.generate_consensus_signal(
                            pair=pair,
                            candles=primary_candles,
                            indicators=primary_indicators,
                            market_condition=market_context.condition if market_context else MarketCondition.UNKNOWN,
                            current_time=current_time,
                            regime=regime_str
                        )
                        
                        if consensus_recommendation:
                            self.logger.info(f"✅ {pair}: Multi-strategy consensus {consensus_recommendation.signal.value} "
                                           f"(confidence: {consensus_recommendation.confidence:.2f}, "
                                           f"strategies: {consensus_recommendation.metadata.get('strategy_count', 0)})")
                            self._last_trade_time[pair] = current_time
                            return consensus_recommendation, primary_indicators
                        else:
                            self.logger.debug(f"ℹ️ {pair}: No multi-strategy consensus - falling back to legacy analysis")
                except Exception as e:
                    self.logger.warning(f"⚠️ {pair}: Multi-strategy analysis failed: {e}. Using legacy approach.")
            
            # CHECK MARKET CONDITIONS - Log but allow all conditions for backtesting
            if market_context and market_context.condition:
                self.logger.debug(f"📊 {pair}: Market condition detected: {market_context.condition.value}")
                # Note: Allowing all market conditions including RANGING for realistic backtesting
                # In live trading, you might want to exclude certain conditions
            
            # ADDITIONAL VOLATILITY CHECK - Require sufficient volatility for trading
            if primary_indicators and primary_indicators.atr:
                # Use configurable volatility threshold from config
                vol_threshold = getattr(self.config.market_conditions, 'volatility_threshold', 0.0008)
                if primary_indicators.atr < vol_threshold:
                    self.logger.debug(f"❌ {pair}: Insufficient volatility (ATR: {primary_indicators.atr:.5f}, need {vol_threshold}+)")
                    return None, primary_indicators
                else:
                    self.logger.debug(f"✅ {pair}: Volatility sufficient (ATR: {primary_indicators.atr:.5f})")
            
            # Analyze technical signals
            signal_analysis = self._analyze_technical_signals(primary_indicators, market_context)
            
            if not signal_analysis['has_signal']:
                self.logger.info(f"ℹ️ {pair}: No clear technical signal detected - insufficient confluence")
                self.logger.info(f"   Signal analysis: {signal_analysis}")
                self.logger.info(f"   RSI: {primary_indicators.rsi:.2f}, MACD: {primary_indicators.macd:.6f}")
                self.logger.info(f"   Reasoning: {signal_analysis.get('reasoning', 'No reasoning provided')}")
                return None, primary_indicators
            
            # Calculate confidence based on signal strength and multi-timeframe agreement
            confidence = self._calculate_technical_confidence(signal_analysis, technical_indicators)
            
            # Check minimum signal strength with detailed logging
            self.logger.info(f"🔍 {pair}: Signal strength check: {confidence:.3f} vs {self.min_signal_strength}")
            if confidence < self.min_signal_strength:
                self.logger.info(f"❌ {pair}: Signal strength {confidence:.3f} < {self.min_signal_strength} (REJECTED)")
                self.logger.info(f"   Signal analysis details: {signal_analysis}")
                return None, primary_indicators
            else:
                self.logger.info(f"✅ {pair}: Signal strength check passed: {confidence:.3f} >= {self.min_signal_strength}")
            
            # Get current price from latest candle
            current_price = self._get_current_price(candles_by_timeframe[primary_timeframe])
            
            # Create trade recommendation
            recommendation = self._create_technical_recommendation(
                pair, signal_analysis, confidence, current_price, primary_indicators, market_context
            )
            
            # Log the recommendation
            self.logger.info(f"🎯 Technical Recommendation for {pair}: "
                           f"Signal={recommendation.signal.value}, "
                           f"Confidence={recommendation.confidence:.2f}, "
                           f"RR={recommendation.risk_reward_ratio:.2f}")
            
            # Update cache and trade cooldown
            cache_key = f"{pair}_{primary_timeframe.value}"
            self._analysis_cache[cache_key] = recommendation
            self._last_analysis_time[pair] = current_time
            self._last_trade_time[pair] = current_time  # Start cooldown period
            
            return recommendation, primary_indicators
            
        except Exception as e:
            self.logger.error(f"Error in technical analysis for {pair}: {e}")
            return None, None
    
    def _analyze_technical_signals(self, indicators: TechnicalIndicators, market_context: MarketContext) -> Dict[str, Any]:
        """Analyze technical indicators with improved signal confluence logic."""
        
        signals = {
            'rsi_signal': None,
            'macd_signal': None,
            'bollinger_signal': None,
            'ema_signal': None,
            'atr_signal': None,
            'volume_signal': None,
            'overall_signal': None,
            'has_signal': False,
            'signal_strength': 0.0,
            'confluence_score': 0.0,
            'reasoning': []
        }
        
        try:
            # RSI Analysis
            self.logger.info(f"🔍 RSI Analysis: RSI={indicators.rsi}, oversold={self.rsi_oversold}, overbought={self.rsi_overbought}")
            if indicators.rsi is not None:
                if indicators.rsi < self.rsi_oversold:
                    signals['rsi_signal'] = TradeSignal.BUY
                    signals['reasoning'].append(f"RSI oversold ({indicators.rsi:.2f})")
                    self.logger.info(f"✅ RSI BUY signal generated: {indicators.rsi:.2f} < {self.rsi_oversold}")
                elif indicators.rsi > self.rsi_overbought:
                    signals['rsi_signal'] = TradeSignal.SELL
                    signals['reasoning'].append(f"RSI overbought ({indicators.rsi:.2f})")
                    self.logger.info(f"✅ RSI SELL signal generated: {indicators.rsi:.2f} > {self.rsi_overbought}")
                else:
                    self.logger.info(f"ℹ️ RSI neutral: {indicators.rsi:.2f} (between {self.rsi_oversold} and {self.rsi_overbought})")
            else:
                self.logger.info(f"❌ RSI is None - cannot generate signal")
            
            # MACD Analysis
            if (indicators.macd is not None and indicators.macd_signal is not None and 
                abs(indicators.macd - indicators.macd_signal) > self.macd_signal_threshold):
                
                if indicators.macd > indicators.macd_signal:
                    signals['macd_signal'] = TradeSignal.BUY
                    signals['reasoning'].append("MACD bullish crossover")
                else:
                    signals['macd_signal'] = TradeSignal.SELL
                    signals['reasoning'].append("MACD bearish crossover")
            
            # Bollinger Bands Analysis
            if (indicators.bollinger_upper is not None and indicators.bollinger_lower is not None and 
                indicators.bollinger_middle is not None):
                
                # Calculate price position relative to bands
                price = indicators.bollinger_middle  # Use middle band as reference
                upper_distance = (indicators.bollinger_upper - price) / price
                lower_distance = (price - indicators.bollinger_lower) / price
                
                if upper_distance < self.bollinger_threshold:
                    signals['bollinger_signal'] = TradeSignal.SELL
                    signals['reasoning'].append("Price near upper Bollinger band")
                elif lower_distance < self.bollinger_threshold:
                    signals['bollinger_signal'] = TradeSignal.BUY
                    signals['reasoning'].append("Price near lower Bollinger band")
            
            # EMA Analysis
            if (indicators.ema_fast is not None and indicators.ema_slow is not None):
                if indicators.ema_fast > indicators.ema_slow:
                    signals['ema_signal'] = TradeSignal.BUY
                    signals['reasoning'].append("EMA bullish alignment")
                else:
                    signals['ema_signal'] = TradeSignal.SELL
                    signals['reasoning'].append("EMA bearish alignment")
            
            # ATR Analysis (volatility-based signal) - Production volatility requirement
            if indicators.atr is not None:
                # Use ATR for volatility confirmation
                # High ATR suggests good volatility for trading
                if indicators.atr > 0.001:  # Production volatility requirement
                    # ATR doesn't give direction, just confirms volatility is sufficient
                    signals['atr_signal'] = 'VOLATILE'
                    signals['reasoning'].append(f"Sufficient volatility (ATR: {indicators.atr:.5f})")
            
            # Volume Analysis (if available)
            # This would be implemented if volume data is available
            signals['volume_signal'] = 'NEUTRAL'  # Placeholder
            
            # IMPROVED SIGNAL CONFLUENCE LOGIC
            signals = self._calculate_signal_confluence(signals)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error in technical signal analysis: {e}")
            return signals
    
    def _calculate_signal_confluence(self, signals: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate signal confluence and overall signal strength."""
        
        # Count signals by direction
        buy_signals = []
        sell_signals = []
        
        for signal_type, signal in signals.items():
            if signal_type.endswith('_signal') and signal is not None:
                if signal == TradeSignal.BUY:
                    buy_signals.append(signal_type)
                elif signal == TradeSignal.SELL:
                    sell_signals.append(signal_type)
        
        # Calculate confluence score
        total_signals = len(buy_signals) + len(sell_signals)
        max_signals = 5  # RSI, MACD, Bollinger, EMA, ATR
        
        if total_signals == 0:
            signals['confluence_score'] = 0.0
            signals['has_signal'] = False
            return signals
        
        # Determine overall signal direction
        if len(buy_signals) > len(sell_signals):
            signals['overall_signal'] = TradeSignal.BUY
            dominant_signals = buy_signals
            signal_count = len(buy_signals)
        elif len(sell_signals) > len(buy_signals):
            signals['overall_signal'] = TradeSignal.SELL
            dominant_signals = sell_signals
            signal_count = len(sell_signals)
        else:
            # Equal signals - no clear direction
            signals['overall_signal'] = None
            signals['confluence_score'] = 0.0
            signals['has_signal'] = False
            return signals
        
        # Calculate confluence score (0.0 to 1.0)
        signals['confluence_score'] = signal_count / max_signals
        
        # Read confluence requirements from config
        min_signals_required = getattr(self.config.technical_analysis, 'min_signals_required', 1)
        min_confluence_score = getattr(self.config.technical_analysis, 'min_confluence_score', 0.3)
        
        # Additional quality checks
        has_strong_signal = False
        if 'rsi_signal' in dominant_signals:
            # Any RSI signal is considered strong for more trades
            has_strong_signal = True
        
        if 'macd_signal' in dominant_signals:
            # MACD signals are strong when clear crossover
            has_strong_signal = True
        
        # EMA signals are also considered strong
        if 'ema_signal' in dominant_signals:
            has_strong_signal = True
        
        # Bollinger signals are also considered strong
        if 'bollinger_signal' in dominant_signals:
            has_strong_signal = True
        
        if signal_count >= min_signals_required and signals['confluence_score'] >= min_confluence_score and has_strong_signal:
            signals['has_signal'] = True
            
            # Calculate signal strength based on confluence and market conditions
            signals['signal_strength'] = self._calculate_signal_strength(signals, dominant_signals)
            
            # Add confluence reasoning
            signals['reasoning'].append(f"Strong signal confluence: {signal_count}/{max_signals} indicators agree ({signals['confluence_score']:.1%})")
            signals['reasoning'].append(f"Signal strength: {signals['signal_strength']:.3f}")
        else:
            signals['has_signal'] = False
            signals['signal_strength'] = 0.0
            if signal_count < min_signals_required:
                signals['reasoning'].append(f"Insufficient signals: {signal_count}, need {min_signals_required}")
            elif signals['confluence_score'] < min_confluence_score:
                signals['reasoning'].append(f"Low confluence: {signals['confluence_score']:.1%}, need {min_confluence_score:.1%}")
            else:
                signals['reasoning'].append("No strong signal detected")
        
        return signals
    
    def _calculate_signal_strength(self, signals: Dict[str, Any], dominant_signals: List[str]) -> float:
        """Calculate signal strength based on confluence and signal quality."""
        
        base_strength = signals['confluence_score']
        
        # Boost strength based on signal quality
        strength_boost = 0.0
        
        # RSI signals are strong when extreme
        if 'rsi_signal' in dominant_signals:
            strength_boost += 0.1
        
        # MACD signals are strong when clear crossover
        if 'macd_signal' in dominant_signals:
            strength_boost += 0.15
        
        # Bollinger signals are strong when price is at bands
        if 'bollinger_signal' in dominant_signals:
            strength_boost += 0.1
        
        # EMA signals are strong when clear alignment
        if 'ema_signal' in dominant_signals:
            strength_boost += 0.1
        
        # ATR confirmation adds strength
        if signals.get('atr_signal') == 'VOLATILE':
            strength_boost += 0.05
        
        # Cap strength at 1.0
        final_strength = min(1.0, base_strength + strength_boost)
        
        return final_strength
    
    def _calculate_technical_confidence(self, signal_analysis: Dict[str, Any], 
                                      technical_indicators: Dict[TimeFrame, TechnicalIndicators]) -> float:
        """Calculate confidence based on technical signal strength and consistency."""
        
        base_confidence = signal_analysis['signal_strength']
        
        # Boost confidence based on multi-timeframe agreement
        timeframe_agreement = 0.0
        total_timeframes = 0
        
        for timeframe, indicators in technical_indicators.items():
            if indicators is None:
                continue
                
            total_timeframes += 1
            timeframe_signals = self._analyze_technical_signals(indicators, None)
            
            if (timeframe_signals['overall_signal'] == signal_analysis['overall_signal'] and 
                timeframe_signals['has_signal']):
                timeframe_agreement += 1.0
        
        if total_timeframes > 0:
            timeframe_agreement /= total_timeframes
            base_confidence += timeframe_agreement * 0.3
        
        # Cap confidence at 0.95
        return min(base_confidence, 0.95)
    
    def _get_current_price(self, candles: List[CandleData]) -> Decimal:
        """Get current price from the latest candle."""
        if not candles:
            return Decimal('0')
        
        latest_candle = candles[-1]
        return (latest_candle.high + latest_candle.low) / Decimal('2')  # Use typical price
    
    def _create_technical_recommendation(
        self,
        pair: str,
        signal_analysis: Dict[str, Any],
        confidence: float,
        current_price: Decimal,
        indicators: TechnicalIndicators,
        market_context=None
    ) -> TradeRecommendation:
        """Create trade recommendation from technical analysis."""
        
        # Calculate stop loss and take profit using ATR
        # Using 1.5 ATR for stop loss and 3 ATR for take profit (1:2 risk-reward ratio)
        atr = Decimal(str(indicators.atr)) if indicators.atr else Decimal('0.001')
        stop_loss_distance = atr * Decimal('1.5')  # 1.5 ATR stop loss
        take_profit_distance = atr * Decimal('3.0')  # 3.0 ATR take profit (1:2 R:R)
        
        if signal_analysis['overall_signal'] == TradeSignal.BUY:
            stop_loss = current_price - stop_loss_distance
            take_profit = current_price + take_profit_distance
        else:
            stop_loss = current_price + stop_loss_distance
            take_profit = current_price - take_profit_distance
        
        # Calculate risk-reward ratio
        risk = abs(current_price - stop_loss)
        reward = abs(take_profit - current_price)
        risk_reward_ratio = float(reward / risk) if risk > 0 else 0.0
        
        reasoning = " | ".join(signal_analysis['reasoning'])
        
        return TradeRecommendation(
            pair=pair,
            signal=signal_analysis['overall_signal'],
            confidence=confidence,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=risk_reward_ratio,
            reasoning=reasoning,
            market_condition=market_context.condition if market_context else MarketCondition.UNKNOWN,
            estimated_hold_time=timedelta(minutes=120)  # 2 hours default
        )
    
    async def start(self) -> None:
        """Start the technical analysis layer."""
        try:
            self.logger.info("Starting technical analysis layer...")
            self.logger.info("Technical analysis layer started successfully")
        except Exception as e:
            self.logger.error(f"Error starting technical analysis layer: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the technical analysis layer."""
        try:
            self.logger.info("Technical analysis layer stopped")
        except Exception as e:
            self.logger.error(f"Error stopping technical analysis layer: {e}")
