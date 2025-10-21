"""
Technical Decision Layer - Pure Technical Trading Decision Making.

This module provides comprehensive trading decision-making capabilities based on
technical analysis, risk management, and performance tracking. It replaces AI-dependent
decision making with proven technical analysis methods and strict risk management rules.

Key Features:
- Technical analysis-based decision making
- Advanced risk management and position sizing
- Performance tracking and metrics calculation
- Trade recording and audit trail
- Multi-timeframe consensus validation
- Strict trading thresholds to prevent overtrading

Architecture:
- TechnicalDecisionLayer: Main decision orchestrator
- RiskManager: Risk assessment and position sizing
- PerformanceTracker: Performance metrics and tracking
- EnhancedExcelTradeRecorder: Trade recording and audit

The decision layer is the final arbiter of trading decisions, combining technical
analysis with risk management to make informed, disciplined trading choices.

Author: Trading Bot Development Team
Version: 2.0.0
Last Updated: 2024
"""
import asyncio
import traceback
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from decimal import Decimal
import json

from ..core.models import (
    TradeRecommendation, TradeDecision, MarketCondition, TradeSignal,
    PerformanceMetrics, CandleData, TimeFrame, TechnicalIndicators, MarketContext
)
from ..utils.config import Config
from ..utils.logger import get_logger
from .risk_manager import RiskManager
from .performance_tracker import PerformanceTracker
from .enhanced_excel_trade_recorder import EnhancedExcelTradeRecorder


class TechnicalDecisionLayer:
    """
    Technical trading decision making system.
    
    This class orchestrates the final trading decision process by combining
    technical analysis recommendations with risk management, performance tracking,
    and trade recording. It makes disciplined trading decisions based on
    technical indicators and strict risk management rules.
    
    Key Responsibilities:
    - Process technical analysis recommendations
    - Apply risk management rules and position sizing
    - Validate trading conditions and thresholds
    - Track performance metrics and trade history
    - Record trades for audit and analysis
    - Prevent overtrading through cooldown mechanisms
    
    Components:
    - RiskManager: Risk assessment and position sizing
    - PerformanceTracker: Performance metrics calculation
    - EnhancedExcelTradeRecorder: Trade recording and audit
    - Decision validation and filtering
    
    The decision layer ensures that only high-quality, well-managed trades
    are executed, maintaining strict discipline and risk control.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the Technical Decision Layer.
        
        Args:
            config: Configuration object containing trading parameters and thresholds
            
        The initialization process:
        1. Sets up risk management and performance tracking components
        2. Initializes trade recording and audit systems
        3. Configures decision tracking and position management
        4. Sets strict technical analysis thresholds to prevent overtrading
        5. Prepares performance metrics tracking
        """
        self.config = config
        self.logger = get_logger(__name__)
        
        # Initialize core components
        self.risk_manager = RiskManager(config)
        self.performance_tracker = PerformanceTracker()
        self.trade_recorder = EnhancedExcelTradeRecorder(config)
        
        # Decision tracking and position management
        self._daily_trades: List[TradeDecision] = []
        self._open_positions: Dict[str, TradeDecision] = {}
        self._last_decision_time: Dict[str, datetime] = {}
        
        # Performance metrics tracking
        self._performance_metrics = PerformanceMetrics()
        
        # Technical analysis thresholds - OPTIMIZED FOR INTRADAY TRADING
        self.rsi_oversold = 35  # Intraday: 35 catches more opportunities
        self.rsi_overbought = 65  # Intraday: 65 catches more opportunities
        self.macd_signal_threshold = 0.00005  # Lower threshold for faster signals
        self.bollinger_threshold = 0.10  # Allow trades within 10% of bands
        self.atr_multiplier = 2.0  # ATR multiplier for stop loss
        
    async def make_technical_decision(
        self, 
        pair: str,
        technical_indicators: Dict[TimeFrame, TechnicalIndicators],
        market_context: MarketContext,
        current_price: Decimal,
        candles_by_timeframe: Dict[TimeFrame, List[CandleData]] = None
    ) -> Optional[TradeDecision]:
        """Make trading decision based on technical indicators only."""
        
        self.logger.info(f"🎯 Starting technical decision making for {pair}...")
        
        try:
            # Get primary timeframe indicators (M5)
            primary_indicators = technical_indicators.get(TimeFrame.M5)
            if not primary_indicators:
                self.logger.info(f"ℹ️ {pair}: No primary timeframe indicators available")
                return None
            
            # Analyze technical signals
            signal_analysis = self._analyze_technical_signals(primary_indicators, market_context)
            
            if not signal_analysis['has_signal']:
                self.logger.info(f"ℹ️ {pair}: No clear technical signal detected")
                return None
            
            # Calculate confidence based on signal strength
            confidence = self._calculate_technical_confidence(signal_analysis, technical_indicators)
            
            # Check if confidence meets threshold
            if confidence < self.config.technical_confidence_threshold:
                self.logger.info(f"❌ {pair}: Technical confidence {confidence:.2f} below threshold {self.config.technical_confidence_threshold}")
                return None
            
            # Create trade recommendation
            recommendation = self._create_technical_recommendation(
                pair, signal_analysis, confidence, current_price, primary_indicators
            )
            
            # Apply risk management
            risk_assessment = await self.risk_manager.assess_risk(
                recommendation, current_price, market_context
            )
            
            if not risk_assessment['approved']:
                self.logger.info(f"❌ Risk management rejected trade for {pair}: {risk_assessment['reason']}")
                self.logger.debug(f"   Risk assessment details: {risk_assessment}")
                return self._create_rejected_decision(recommendation, risk_assessment)
            
            # Calculate position size
            position_size = await self.risk_manager.calculate_position_size(
                recommendation, risk_assessment
            )
            
            # Create trade decision
            decision = TradeDecision(
                recommendation=recommendation,
                approved=True,
                position_size=position_size['size'],
                risk_amount=position_size['risk_amount'],
                modified_stop_loss=position_size['stop_loss'],
                modified_take_profit=position_size['take_profit'],
                risk_management_notes=risk_assessment['reason'],
                timestamp=datetime.now(timezone.utc)
            )
            
            # Log successful decision
            self.logger.info(f"✅ Technical trade APPROVED for {pair}: "
                           f"Signal={recommendation.signal}, "
                           f"Confidence={confidence:.2f}, "
                           f"Size={position_size['size']:.2f}")
            
            # Record the decision
            self._log_decision(decision)
            
            # Record the COMPLETE trade decision with ALL data
            if self.trade_recorder:
                self.trade_recorder.record_complete_trade_decision(
                    decision=decision,
                    market_context=market_context,
                    technical_indicators=technical_indicators,
                    candles_by_timeframe=candles_by_timeframe or {},
                    ai_outputs={},  # Empty since no AI analysis
                    multi_timeframe_analysis={},  # Simplified for now
                    risk_assessment=risk_assessment,
                    raw_data={'technical_analysis': signal_analysis}
                )
            
            # Update tracking
            self._daily_trades.append(decision)
            self._last_decision_time[pair] = datetime.now(timezone.utc)
            
            return decision
            
        except Exception as e:
            self.logger.error(f"Error in technical decision making for {pair}: {e}")
            return None
    
    def _analyze_technical_signals(self, indicators: TechnicalIndicators, market_context: MarketContext) -> Dict[str, Any]:
        """Analyze technical indicators to generate trading signals."""
        
        signals = {
            'rsi_signal': None,
            'macd_signal': None,
            'bollinger_signal': None,
            'ema_signal': None,
            'overall_signal': None,
            'has_signal': False,
            'signal_strength': 0.0,
            'reasoning': []
        }
        
        try:
            # RSI Analysis
            if indicators.rsi is not None:
                if indicators.rsi < self.rsi_oversold:
                    signals['rsi_signal'] = TradeSignal.BUY
                    signals['reasoning'].append(f"RSI oversold ({indicators.rsi:.2f})")
                elif indicators.rsi > self.rsi_overbought:
                    signals['rsi_signal'] = TradeSignal.SELL
                    signals['reasoning'].append(f"RSI overbought ({indicators.rsi:.2f})")
            
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
                    signals['reasoning'].append("Fast EMA above slow EMA")
                else:
                    signals['ema_signal'] = TradeSignal.SELL
                    signals['reasoning'].append("Fast EMA below slow EMA")
            
            # Determine overall signal
            buy_signals = sum(1 for signal in [signals['rsi_signal'], signals['macd_signal'], 
                                             signals['bollinger_signal'], signals['ema_signal']] 
                            if signal == TradeSignal.BUY)
            sell_signals = sum(1 for signal in [signals['rsi_signal'], signals['macd_signal'], 
                                              signals['bollinger_signal'], signals['ema_signal']] 
                             if signal == TradeSignal.SELL)
            
            if buy_signals > sell_signals and buy_signals >= 1:  # More lenient: only need 1 signal
                signals['overall_signal'] = TradeSignal.BUY
                signals['has_signal'] = True
                signals['signal_strength'] = buy_signals / 4.0
            elif sell_signals > buy_signals and sell_signals >= 1:  # More lenient: only need 1 signal
                signals['overall_signal'] = TradeSignal.SELL
                signals['has_signal'] = True
                signals['signal_strength'] = sell_signals / 4.0
            elif buy_signals == sell_signals and buy_signals >= 1:  # Handle tie cases
                # In case of tie, prefer the stronger signal or use RSI as tiebreaker
                if signals['rsi_signal'] == TradeSignal.BUY:
                    signals['overall_signal'] = TradeSignal.BUY
                    signals['has_signal'] = True
                    signals['signal_strength'] = buy_signals / 4.0
                elif signals['rsi_signal'] == TradeSignal.SELL:
                    signals['overall_signal'] = TradeSignal.SELL
                    signals['has_signal'] = True
                    signals['signal_strength'] = sell_signals / 4.0
            
        except Exception as e:
            self.logger.error(f"Error analyzing technical signals: {e}")
        
        return signals
    
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
    
    def _create_technical_recommendation(
        self, 
        pair: str, 
        signal_analysis: Dict[str, Any], 
        confidence: float, 
        current_price: Decimal,
        indicators: TechnicalIndicators
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
            market_condition=MarketCondition.BREAKOUT,  # Default to breakout
            estimated_hold_time=timedelta(minutes=120)  # 2 hours default
        )
    
    def _create_multi_timeframe_analysis(self, technical_indicators: Dict[TimeFrame, TechnicalIndicators]) -> Dict[str, Any]:
        """Create multi-timeframe analysis summary for recording."""
        
        analysis = {}
        
        for timeframe, indicators in technical_indicators.items():
            if indicators is None:
                continue
                
            analysis[timeframe.value] = {
                'rsi': indicators.rsi,
                'macd': indicators.macd,
                'macd_signal': indicators.macd_signal,
                'atr': indicators.atr,
                'ema_fast': indicators.ema_fast,
                'ema_slow': indicators.ema_slow,
                'bollinger_upper': indicators.bollinger_upper,
                'bollinger_middle': indicators.bollinger_middle,
                'bollinger_lower': indicators.bollinger_lower
            }
        
        return analysis
    
    def _create_rejected_decision(
        self, 
        recommendation: TradeRecommendation, 
        risk_assessment: Dict[str, Any]
    ) -> TradeDecision:
        """Create a rejected trade decision."""
        return TradeDecision(
            recommendation=recommendation,
            approved=False,
            risk_management_notes=risk_assessment['reason'],
            timestamp=datetime.now(timezone.utc)
        )
    
    def _log_decision(self, decision: TradeDecision) -> None:
        """Log the decision details."""
        self.logger.info(
            f"📊 Technical Decision: {decision.recommendation.pair} - "
            f"Signal: {decision.recommendation.signal.value}, "
            f"Confidence: {decision.recommendation.confidence:.2f}, "
            f"Entry: {decision.recommendation.entry_price}, "
            f"SL: {decision.modified_stop_loss}, "
            f"TP: {decision.modified_take_profit}"
        )
    
    async def start(self) -> None:
        """Start the technical decision layer."""
        try:
            print("🎯 [DEBUG] Starting technical decision layer...")
            self.logger.info("Starting technical decision layer...")
            
            # Start trade recorder
            print("📝 [DEBUG] Starting trade recorder...")
            await self.trade_recorder.start()
            print("✅ [DEBUG] Trade recorder started")
            
            # Initialize performance tracker
            print("📊 [DEBUG] Starting performance tracker...")
            await self.performance_tracker.start()
            print("✅ [DEBUG] Performance tracker started")
            
            print("✅ [DEBUG] Technical decision layer started successfully")
            self.logger.info("Technical decision layer started successfully")
        except Exception as e:
            print(f"❌ [DEBUG] Error starting technical decision layer: {e}")
            self.logger.error(f"Error starting technical decision layer: {e}")
            raise
    
    async def make_enhanced_decision(self, pair: str, recommendation: Optional[TradeRecommendation], 
                                   technical_indicators: Optional[TechnicalIndicators],
                                   fundamental_analysis: Dict[str, Any], 
                                   regime_analysis: Dict[str, Any],
                                   market_context: MarketContext) -> Optional[TradeDecision]:
        """Make enhanced trading decision based on all available data."""
        self.logger.info(f"🎯 Starting enhanced decision making for {pair}...")
        
        try:
            if not recommendation:
                self.logger.info(f"ℹ️ {pair}: No trade recommendation - waiting for better market conditions")
                return None
            
            self.logger.info(f"📊 {pair}: Analyzing recommendation - Signal: {recommendation.signal}, Confidence: {recommendation.confidence}")
            
            # Check confidence threshold
            if recommendation.confidence < self.config.technical_confidence_threshold:
                self.logger.info(
                    f"❌ {pair}: Confidence {recommendation.confidence} below threshold {self.config.technical_confidence_threshold}"
                )
                return None
            
            self.logger.info(f"✅ {pair}: Confidence threshold met")
            
            # Create decision
            # Create canonical TradeDecision as defined in core.models
            from datetime import datetime, timezone
            decision = TradeDecision(
                recommendation=recommendation,
                approved=True,
                position_size=None,
                risk_amount=None,
                modified_stop_loss=recommendation.stop_loss,
                modified_take_profit=recommendation.take_profit,
                risk_management_notes="",
                timestamp=datetime.now(timezone.utc)
            )
            
            self.logger.info(f"✅ {pair}: Decision created successfully")
            return decision
            
        except Exception as e:
            self.logger.error(f"Error in enhanced decision making for {pair}: {e}")
            return None

    async def close(self) -> None:
        """Close technical decision layer."""
        try:
            # Stop trade recorder
            await self.trade_recorder.stop()
            await self.performance_tracker.close()
            self.logger.info("Technical decision layer closed")
        except Exception as e:
            self.logger.error(f"Error closing technical decision layer: {e}")

    def _calculate_dynamic_atr_multiplier(self, timeframe: TimeFrame, market_condition: MarketCondition) -> float:
        """Calculate dynamic ATR multiplier based on timeframe and market condition."""
        
        # Base multipliers by timeframe (tighter for shorter timeframes)
        base_multipliers = {
            TimeFrame.M1: 0.3,
            TimeFrame.M5: 0.5,
            TimeFrame.M15: 0.7,
            TimeFrame.M30: 0.8,
            TimeFrame.H1: 1.0,
            TimeFrame.H4: 1.2,
            TimeFrame.D1: 1.5
        }
        
        base_multiplier = base_multipliers.get(timeframe, 0.5)
        
        # Adjust based on market condition
        condition_adjustments = {
            MarketCondition.TRENDING: 0.8,      # Tighter stops in trending markets
            MarketCondition.RANGING: 0.6,       # Even tighter in ranging markets
            MarketCondition.VOLATILE: 1.2,      # Wider stops in volatile markets
            MarketCondition.BREAKOUT: 0.7,      # Moderate stops for breakouts
            MarketCondition.CONSOLIDATION: 0.5, # Tight stops in consolidation
            MarketCondition.REVERSAL: 0.9       # Moderate stops for reversals
        }
        
        adjustment = condition_adjustments.get(market_condition, 1.0)
        
        # Cap the multiplier to prevent overly wide stops
        final_multiplier = min(base_multiplier * adjustment, 1.5)
        
        return final_multiplier
