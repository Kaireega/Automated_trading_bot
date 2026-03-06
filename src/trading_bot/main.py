#!/usr/bin/env python3
"""
Market Adaptive Trading Bot - Main Entry Point and Orchestrator.

This is the main entry point for the Market Adaptive Trading Bot, a comprehensive
automated trading system that combines technical analysis, fundamental analysis,
advanced risk management, and market regime detection to make informed trading decisions.

Key Features:
- Real-time market data collection via OANDA API
- Multi-timeframe technical analysis and signal generation
- Fundamental analysis and economic calendar integration
- Advanced risk management and position sizing
- Market regime detection and adaptation
- Comprehensive backtesting and simulation capabilities
- Real-time notifications and trade management
- Performance tracking and optimization

Architecture:
- TradingBot: Main orchestrator and entry point
- DataLayer: Market data collection and management
- TechnicalAnalysisLayer: Technical analysis and signal generation
- TechnicalDecisionLayer: Decision making and risk management
- PositionManager: Trade execution and position management
- FundamentalAnalyzer: Economic analysis and market context
- AdvancedRiskManager: Risk assessment and position sizing
- MarketRegimeDetector: Market condition analysis
- BacktestEngine: Strategy testing and optimization
- NotificationLayer: User communications and alerts

The bot operates in a continuous loop, analyzing market conditions, generating
signals, making decisions, and executing trades while maintaining strict risk
management and performance monitoring.

Author: Trading Bot Development Team
Version: 2.0.0
Last Updated: 2024
"""
import asyncio
import logging
import signal
import sys
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

# Add the project root to the path for imports
root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Import comprehensive debugging utilities
from trading_bot.src.utils.debug_utils import (
    debug_tracker, debug_line, debug_variable, debug_context, 
    debug_performance, debug_data_flow, debug_api_call, 
    debug_trade_decision, debug_strategy_execution, debug_risk_calculation,
    debug_indicator_calculation, debug_backtest_step, debug_entry_point,
    debug_exit_point, debug_conditional, debug_loop_iteration,
    get_debug_summary, export_debug_report
)

from trading_bot.src.utils.config import Config
from trading_bot.src.utils.logger import get_logger
from trading_bot.src.data.data_layer import DataLayer
from trading_bot.src.ai.technical_analysis_layer import TechnicalAnalysisLayer
from trading_bot.src.decision.technical_decision_layer import TechnicalDecisionLayer
from trading_bot.src.notifications.notification_layer import NotificationLayer
from trading_bot.src.core.position_manager import PositionManager
from trading_bot.src.core.fundamental_analyzer import FundamentalAnalyzer
from trading_bot.src.core.advanced_risk_manager import AdvancedRiskManager
from trading_bot.src.core.market_regime_detector import MarketRegimeDetector
from trading_bot.src.backtesting.backtest_engine import BacktestEngine
from infrastructure.instrument_collection import instrumentCollection as ic
from api.oanda_api import OandaApi
from trading_bot.src.core.models import TimeFrame, TradeDecision, CandleData
from decimal import Decimal


class TradingBot:
    """
    Enhanced Market Adaptive Trading Bot with comprehensive trading capabilities.
    
    This is the main orchestrator class that coordinates all components of the
    trading system. It manages the complete trading workflow from data collection
    to trade execution, including analysis, decision making, risk management,
    and performance monitoring.
    
    Key Responsibilities:
    - Orchestrate the complete trading workflow
    - Manage component lifecycle and initialization
    - Coordinate data collection and analysis
    - Execute trading decisions and manage positions
    - Monitor performance and handle errors
    - Provide backtesting and simulation capabilities
    - Manage user notifications and communications
    
    Components:
    - DataLayer: Market data collection and management
    - TechnicalAnalysisLayer: Technical analysis and signal generation
    - TechnicalDecisionLayer: Decision making and risk management
    - PositionManager: Trade execution and position management
    - FundamentalAnalyzer: Economic analysis and market context
    - AdvancedRiskManager: Risk assessment and position sizing
    - MarketRegimeDetector: Market condition analysis
    - BacktestEngine: Strategy testing and optimization
    - NotificationLayer: User communications and alerts
    
    The bot operates continuously, adapting to market conditions and making
    informed trading decisions based on comprehensive analysis.
    """
    
    def __init__(self):
        """
        Initialize the Trading Bot with all required components.
        
        The initialization process:
        1. Sets up logging and configuration
        2. Initializes OANDA API connection
        3. Creates all core trading components
        4. Sets up advanced analysis components
        5. Configures backtesting engine
        6. Prepares bot state and tracking
        
        This creates a fully functional trading bot ready for live trading
        or backtesting operations.
        """
        # Debug entry point
        debug_entry_point("TradingBot.__init__")
        
        with debug_context("TradingBot initialization") as context:
            print(f"🔧 [DEBUG] Creating TradingBot instance...")
            debug_variable("init_start_time", datetime.now(), context)
            
            # Initialize logger
            print(f"📝 [DEBUG] Creating logger: __main__")
            debug_variable("logger_name", __name__, context)
            self.logger = get_logger(__name__)
            debug_variable("logger_created", True, context)
            print(f"🔧 [DEBUG] Logger initialized")
            
            # Load configuration
            print(f"🔧 [DEBUG] Loading configuration...")
            debug_data_flow("config_loading", "starting", "configuration")
            self.config = Config()
            debug_variable("trading_pairs", self.config.trading_pairs, context)
            debug_variable("timeframes", [tf.value for tf in self.config.timeframes], context)
            print(f"🔧 [DEBUG] Configuration loaded - Trading pairs: {self.config.trading_pairs}")
            print(f"🔧 [DEBUG] Configuration loaded - Timeframes: {[tf.value for tf in self.config.timeframes]}")
            
            # Initialize OANDA API
            print(f"🔧 [DEBUG] Initializing OANDA API...")
            debug_api_call("OANDA", "initialization", {}, None)
            self.oanda_api = OandaApi()
            debug_variable("oanda_api_initialized", True, context)
            print(f"🔧 [DEBUG] OANDA API initialized")
                
            # Ensure instruments metadata is loaded for correct FX sizing
            try:
                data_dir = Path(__file__).parent.parent.parent / "data"
                debug_variable("data_dir", str(data_dir), context)
                ic.LoadInstruments(str(data_dir))
                debug_variable("instruments_loaded", True, context)
                print(f"✅ [DEBUG] Instruments loaded from {data_dir}")
            except Exception as e:
                debug_tracker.log_error(context, e, "Failed to load instruments")
                print(f"❌ [DEBUG] Failed to load instruments: {e}")

            # Initialize core components
            print(f"🔧 [DEBUG] Initializing core components...")
            debug_data_flow("core_components", "initializing", "core_components")
            
            # Data Layer
            debug_variable("data_layer_config", self.config, context)
            self.data_layer = DataLayer(self.config)
            debug_variable("data_layer_initialized", True, context)
            print(f"🔧 [DEBUG] Data layer initialized")
            
            # Technical Analysis Layer
            debug_variable("technical_layer_config", self.config, context)
            self.technical_layer = TechnicalAnalysisLayer(self.config)
            debug_variable("technical_layer_initialized", True, context)
            print(f"🔧 [DEBUG] Technical analysis layer initialized")
            
            # Decision Layer
            debug_variable("decision_layer_config", self.config, context)
            self.decision_layer = TechnicalDecisionLayer(self.config)
            debug_variable("decision_layer_initialized", True, context)
            print(f"🔧 [DEBUG] Technical decision layer initialized")
            
            # Notification Layer
            debug_variable("notification_layer_config", self.config, context)
            self.notification_layer = NotificationLayer(self.config)
            debug_variable("notification_layer_initialized", True, context)
            print(f"🔧 [DEBUG] Notification layer initialized")
                
            # Initialize new advanced components
            print(f"🔧 [DEBUG] Initializing advanced components...")
            debug_data_flow("advanced_components", "initializing", "advanced_components")
            
            # Position Manager
            debug_variable("position_manager_config", self.config, context)
            debug_variable("position_manager_oanda_api", self.oanda_api, context)
            self.position_manager = PositionManager(self.config, self.oanda_api)
            debug_variable("position_manager_initialized", True, context)
            print(f"🔧 [DEBUG] Position manager initialized")
            
            # Fundamental Analyzer
            debug_variable("fundamental_analyzer_config", self.config, context)
            self.fundamental_analyzer = FundamentalAnalyzer(self.config)
            debug_variable("fundamental_analyzer_initialized", True, context)
            print(f"🔧 [DEBUG] Fundamental analyzer initialized")
            
            # Advanced Risk Manager
            debug_variable("advanced_risk_manager_config", self.config, context)
            self.advanced_risk_manager = AdvancedRiskManager(self.config)
            debug_variable("advanced_risk_manager_initialized", True, context)
            print(f"🔧 [DEBUG] Advanced risk manager initialized")
            
            # Market Regime Detector
            debug_variable("market_regime_detector_config", self.config, context)
            self.market_regime_detector = MarketRegimeDetector(self.config)
            debug_variable("market_regime_detector_initialized", True, context)
            print(f"🔧 [DEBUG] Market regime detector initialized")
            
            # Initialize backtesting engine
            print(f"🔧 [DEBUG] Initializing backtesting engine...")
            debug_variable("backtest_engine_config", self.config, context)
            debug_variable("use_historical_feed", False, context)
            self.backtest_engine = BacktestEngine(self.config, use_historical_feed=False)
            debug_variable("backtest_engine_initialized", True, context)
            print(f"🔧 [DEBUG] Backtesting engine initialized")
            
            # Bot state
            self.is_running = False
            self.loop_count = 0
            debug_variable("is_running", self.is_running, context)
            debug_variable("loop_count", self.loop_count, context)
            print(f"✅ [DEBUG] TradingBot initialized successfully")
            
            # Log memory usage after initialization
            debug_tracker.log_memory_usage(context)
            
            # Export debug report for initialization
            debug_tracker.log_execution(context, "TradingBot initialization completed successfully")
    
    @debug_performance
    async def start(self):
        """Start the enhanced trading bot."""
        debug_entry_point("TradingBot.start")
        
        with debug_context("TradingBot startup") as context:
            try:
                print("🚀 [DEBUG] Starting Enhanced Market Adaptive Trading Bot...")
                debug_variable("start_time", datetime.now(), context)
                self.logger.info("Starting Enhanced Market Adaptive Trading Bot...")
                
                # Start all components
                print("🚀 [DEBUG] Starting data layer...")
                debug_data_flow("data_layer", "starting", "data_layer")
                await self.data_layer.start()
                debug_variable("data_layer_started", True, context)
                print("✅ [DEBUG] Data layer started successfully")
                
                print("🚀 [DEBUG] Starting technical analysis layer...")
                debug_data_flow("technical_layer", "starting", "technical_layer")
                await self.technical_layer.start()
                debug_variable("technical_layer_started", True, context)
                print("✅ [DEBUG] Technical analysis layer started successfully")
                
                print("🚀 [DEBUG] Starting technical decision layer...")
                debug_data_flow("decision_layer", "starting", "decision_layer")
                await self.decision_layer.start()
                debug_variable("decision_layer_started", True, context)
                print("✅ [DEBUG] Technical decision layer started successfully")
                
                print("🚀 [DEBUG] Starting notification layer...")
                debug_data_flow("notification_layer", "starting", "notification_layer")
                await self.notification_layer.start()
                debug_variable("notification_layer_started", True, context)
                print("✅ [DEBUG] Notification layer started successfully")

                # Register trade executor for manual approvals
                debug_variable("trade_executor", self._execute_trade_from_notification, context)
                self.notification_layer.set_trade_executor(self._execute_trade_from_notification)
                debug_variable("trade_executor_registered", True, context)
                
                # Start new advanced components
                print("🚀 [DEBUG] Starting advanced components...")
                debug_data_flow("advanced_components", "starting", "advanced_components")
                
                debug_variable("position_manager", self.position_manager, context)
                await self.position_manager.start()
                debug_variable("position_manager_started", True, context)
                print("✅ [DEBUG] Position manager started successfully")
                
                debug_variable("fundamental_analyzer", self.fundamental_analyzer, context)
                await self.fundamental_analyzer.start()
                debug_variable("fundamental_analyzer_started", True, context)
                print("✅ [DEBUG] Fundamental analyzer started successfully")
                
                debug_variable("advanced_risk_manager", self.advanced_risk_manager, context)
                await self.advanced_risk_manager.start()
                debug_variable("advanced_risk_manager_started", True, context)
                print("✅ [DEBUG] Advanced risk manager started successfully")
                
                debug_variable("market_regime_detector", self.market_regime_detector, context)
                await self.market_regime_detector.start()
                debug_variable("market_regime_detector_started", True, context)
                print("✅ [DEBUG] Market regime detector started successfully")
                
                debug_variable("backtest_engine", self.backtest_engine, context)
                await self.backtest_engine.start()
                debug_variable("backtest_engine_started", True, context)
                print("✅ [DEBUG] Backtesting engine started successfully")
                
                self.logger.info("All components initialized successfully")
                debug_variable("all_components_started", True, context)
                print("✅ [DEBUG] All components initialized successfully")
                
                # Send startup notification
                print("🚀 [DEBUG] Sending startup notification...")
                debug_data_flow("startup_notification", "sending", "startup_notification")
                await self._send_startup_message()
                debug_variable("startup_notification_sent", True, context)
                print("✅ [DEBUG] Startup notification sent")
                
                # Start main trading loop
                print("🚀 [DEBUG] Starting main trading loop...")
                debug_variable("is_running", True, context)
                self.is_running = True
                debug_data_flow("trading_loop", "starting", "trading_loop")
                await self._enhanced_trading_loop()
                
            except Exception as e:
                debug_tracker.log_error(context, e, "Error starting bot")
                print(f"❌ [DEBUG] Error starting bot: {e}")
                print(f"❌ [DEBUG] Traceback: {traceback.format_exc()}")
                self.logger.error(f"Error starting bot: {e}")
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                raise

    async def _send_startup_message(self):
        """Send enhanced startup message with all component status."""
        try:
            # Get component summaries
            position_summary = await self.position_manager.get_position_summary()
            fundamental_summary = await self.fundamental_analyzer.get_fundamental_summary()
            risk_summary = await self.advanced_risk_manager.get_risk_summary()
            regime_summary = await self.market_regime_detector.get_regime_summary()

            startup_message = f"""
🤖 Enhanced Trading Bot Started Successfully

📊 Component Status:
✅ Data Layer: Active
✅ Technical Analysis: Active  
✅ Technical Decision Layer: Active
✅ Notifications: Active
✅ Position Manager: Active
✅ Fundamental Analyzer: Active
✅ Advanced Risk Manager: Active
✅ Market Regime Detector: Active

🎯 Configuration:
• Trading Pairs: {', '.join([p.replace('_','') for p in self.config.trading_pairs])}
• Multi-timeframe Analysis: {', '.join([tf.value for tf in self.config.timeframes])}
• Risk Management: {self.config.trading.risk_percentage}% per trade
• Daily Loss Limit: {self.config.risk_management.max_daily_loss}%

📈 Advanced Features:
• Real-time Position Monitoring
• Economic Calendar Integration
• Kelly Criterion Position Sizing
• Market Regime Detection
• Dynamic Strategy Adaptation
• Portfolio Heat Management

🔄 Current Status:
• Active Positions: {position_summary['active_positions']}
• Daily P&L: ${position_summary['daily_pnl']:.2f}
• Current Regime: {regime_summary['current_regime']}
• Risk Score: {risk_summary.get('current_drawdown', 0):.2%}

Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""".strip()
            
            await self.notification_layer.send_notification(
                notification_type="STARTUP",
                data={"message": startup_message}
            )
            self.logger.info("Enhanced startup notification sent successfully")
            
        except Exception as e:
            self.logger.error(f"Error sending startup message: {e}")

    async def _execute_trade_from_notification(self, decision: TradeDecision) -> Optional[str]:
        """Executor used by notification layer after manual acceptance."""
        try:
            market_context = await self.data_layer.get_market_context(decision.recommendation.pair)
            trade_id = await self.position_manager.execute_trade(decision, market_context)
            return trade_id
        except Exception as e:
            self.logger.error(f"Error executing trade from notification: {e}")
            return None
    
    @debug_performance
    async def _enhanced_trading_loop(self) -> None:
        """Enhanced trading loop with comprehensive analysis and reporting."""
        debug_entry_point("TradingBot._enhanced_trading_loop")
        
        with debug_context("Enhanced trading loop") as context:
            while self.is_running:
                try:
                    debug_loop_iteration("trading_loop", self.loop_count + 1, None, context)
                    self.loop_count += 1
                    debug_variable("loop_count", self.loop_count, context)
                    
                    # Get data for all pairs
                    debug_data_flow("market_data", "fetching", "all_pairs_data")
                    all_data = await self.data_layer.get_all_data()
                    debug_variable("all_data_keys", list(all_data.keys()) if all_data else [], context)
                    debug_variable("all_data_size", len(all_data) if all_data else 0, context)
                    
                    # Initialize loop statistics
                    loop_stats = {
                        'timestamp': datetime.now(),
                        'pairs_analyzed': set(),
                        'technical_analyses': 0,
                        'technical_indicators': 0,
                        'data_points': 0,
                        'fundamental_analyses': 0,
                        'regime_detections': 0,
                        'trades_executed': 0,
                        'trades_rejected': 0,
                        'errors': [],
                        'pair_analyses': {}
                    }
                    debug_variable("loop_stats_initialized", True, context)
                
                    # Process each pair
                    debug_variable("pairs_to_process", list(all_data.keys()), context)
                    for pair in all_data.keys():
                        debug_variable("current_pair", pair, context)
                        # Check shutdown signal more frequently
                        if not self.is_running:
                            print("🛑 [DEBUG] Shutdown signal detected, stopping pair processing...")
                            debug_conditional(False, "Shutdown signal detected", "Continuing processing", context)
                            break
                        
                        debug_conditional(self._should_analyze_pair(pair), f"Should analyze {pair}", f"Skipping {pair}", context)
                        if self._should_analyze_pair(pair):
                            loop_stats['pairs_analyzed'].add(pair)
                            debug_variable("pairs_analyzed_count", len(loop_stats['pairs_analyzed']), context)
                            
                            # Initialize pair analysis
                            pair_analysis = {
                                'candles_by_timeframe': {},
                                'market_context': {},
                                'fundamental_analysis': {},
                                'technical_indicators': {},
                                'technical_recommendation': None,
                                'regime_analysis': {},
                                'decision': None,
                                'risk_assessment': {},
                                'trade_executed': False,
                                'trade_id': None,
                                'errors': []
                            }
                            debug_variable("pair_analysis_initialized", True, context)
                        
                            try:
                                # Get candles data for this pair
                                debug_data_flow("candles_data", "fetching", f"candles_for_{pair}")
                                candles_data = all_data[pair]
                                debug_variable("candles_data_keys", list(candles_data.keys()) if candles_data else [], context)
                                
                                total_candles = sum(len(candles) for candles in candles_data.values())
                                debug_variable("total_candles", total_candles, context)
                                loop_stats['data_points'] += total_candles
                                debug_variable("total_data_points", loop_stats['data_points'], context)
                                
                                # Check if we have enough data
                                debug_conditional(len(candles_data) >= 2, f"Enough data for {pair}", f"Insufficient data for {pair}", context)
                                if len(candles_data) < 2:
                                    debug_variable("skipping_pair_reason", "insufficient_data", context)
                                    continue
                                
                                # Store candle counts by timeframe
                                for timeframe, candles in candles_data.items():
                                    pair_analysis['candles_by_timeframe'][timeframe.value] = len(candles)
                                    debug_variable(f"candles_{timeframe.value}", len(candles), context)
                                
                                # Get market context
                                debug_data_flow("market_context", "fetching", f"context_for_{pair}")
                                market_context = await self.data_layer.get_market_context(pair)
                                debug_variable("market_context_condition", market_context.condition.value, context)
                                debug_variable("market_context_volatility", market_context.volatility, context)
                                debug_variable("market_context_trend_strength", market_context.trend_strength, context)
                                debug_variable("market_context_news_sentiment", market_context.news_sentiment, context)
                                
                                pair_analysis['market_context'] = {
                                    'condition': market_context.condition.value,
                                    'volatility': market_context.volatility,
                                    'trend_strength': market_context.trend_strength,
                                    'news_sentiment': market_context.news_sentiment
                                }
                                debug_variable("market_context_stored", True, context)
                            
                                # Check if we have enough timeframes with data
                                candles_by_timeframe = {
                                    tf: candles for tf, candles in candles_data.items() 
                                    if len(candles) >= 20
                                }
                                
                                if len(candles_by_timeframe) < 2:
                                    continue
                                
                                # Check shutdown signal before long operations
                                if not self.is_running:
                                    break
                                    
                                # Fundamental Analysis
                                try:
                                    fundamental_analysis = await self.fundamental_analyzer.analyze_fundamentals(pair, market_context)
                                    pair_analysis['fundamental_analysis'] = {
                                        'sentiment': fundamental_analysis.get('sentiment', 'NEUTRAL'),
                                        'sentiment_score': fundamental_analysis.get('sentiment_score', 0.0),
                                        'news_count': fundamental_analysis.get('news_count', 0),
                                        'economic_events': fundamental_analysis.get('economic_events', [])
                                    }
                                    loop_stats['fundamental_analyses'] += 1
                                except Exception as e:
                                    pair_analysis['errors'].append(f"Fundamental analysis failed: {str(e)}")
                                
                                # Check shutdown signal before technical analysis
                                if not self.is_running:
                                    break
                                    
                                # Technical Analysis
                                try:
                                    recommendation, technical_indicators = await self.technical_layer.analyze_multiple_timeframes(
                                        pair, candles_by_timeframe, market_context
                                    )
                                    
                                    # Store technical indicators
                                    if technical_indicators:
                                        pair_analysis['technical_indicators'] = {
                                            'rsi': technical_indicators.rsi,
                                            'macd': technical_indicators.macd,
                                            'macd_signal': technical_indicators.macd_signal,
                                            'macd_histogram': technical_indicators.macd_histogram,
                                            'atr': technical_indicators.atr,
                                            'ema_fast': technical_indicators.ema_fast,
                                            'ema_slow': technical_indicators.ema_slow,
                                            'bollinger_upper': technical_indicators.bollinger_upper,
                                            'bollinger_middle': technical_indicators.bollinger_middle,
                                            'bollinger_lower': technical_indicators.bollinger_lower,
                                            'keltner_upper': technical_indicators.keltner_upper,
                                            'keltner_middle': technical_indicators.keltner_middle,
                                            'keltner_lower': technical_indicators.keltner_lower
                                        }
                                        loop_stats['technical_indicators'] += 1
                                    
                                    if recommendation:
                                        pair_analysis['technical_recommendation'] = {
                                            'signal': recommendation.signal.value,
                                            'confidence': recommendation.confidence,
                                            'entry_price': float(recommendation.entry_price) if recommendation.entry_price else None,
                                            'stop_loss': float(recommendation.stop_loss) if recommendation.stop_loss else None,
                                            'take_profit': float(recommendation.take_profit) if recommendation.take_profit else None,
                                            'risk_reward_ratio': recommendation.risk_reward_ratio,
                                            'reasoning': recommendation.reasoning
                                        }
                                    loop_stats['technical_analyses'] += 1
                                except Exception as e:
                                    pair_analysis['errors'].append(f"Technical analysis failed: {str(e)}")
                                    recommendation = None
                                    technical_indicators = None
                            
                                # Check shutdown signal before regime detection
                                if not self.is_running:
                                    break
                                    
                                # Market Regime Detection
                                try:
                                    if technical_indicators:
                                        # Get primary candles for regime detection
                                        primary_candles = candles_by_timeframe.get(TimeFrame.M5, [])
                                        if not primary_candles:
                                            primary_candles = list(candles_by_timeframe.values())[0] if candles_by_timeframe else []
                                        
                                        regime_analysis = await self.market_regime_detector.detect_regime(
                                            pair, primary_candles, 
                                            market_context, technical_indicators
                                        )
                                        loop_stats['regime_detections'] += 1
                                        
                                        # Convert volatility level to descriptive state
                                        volatility_level = regime_analysis.get('volatility_level', 0.0)
                                        if volatility_level >= 0.8:
                                            volatility_state = "VERY_HIGH"
                                        elif volatility_level >= 0.6:
                                            volatility_state = "HIGH"
                                        elif volatility_level >= 0.4:
                                            volatility_state = "MEDIUM"
                                        elif volatility_level >= 0.2:
                                            volatility_state = "LOW"
                                        else:
                                            volatility_state = "VERY_LOW"
                                        
                                        pair_analysis['regime_analysis'] = {
                                            'regime': regime_analysis.get('regime', 'UNKNOWN'),
                                            'confidence': regime_analysis.get('confidence', 0.0),
                                            'volatility_state': volatility_state,
                                            'trend_strength': regime_analysis.get('trend_strength', 0.0)
                                        }
                                    else:
                                        regime_analysis = {'regime': 'UNKNOWN', 'confidence': 0.0}
                                        pair_analysis['regime_analysis'] = {
                                            'regime': 'UNKNOWN',
                                            'confidence': 0.0,
                                            'volatility_state': 'UNKNOWN',
                                            'trend_strength': 0.0
                                        }
                                except Exception as e:
                                    pair_analysis['errors'].append(f"Regime detection failed: {str(e)}")
                                
                                # Check shutdown signal before decision making
                                if not self.is_running:
                                    break
                                    
                                # Technical Decision Making
                                try:
                                    # Get current price for decision making
                                    current_price = self._get_current_price(candles_by_timeframe.get(TimeFrame.M5, []))
                                    
                                    # Convert single TechnicalIndicators to dictionary format expected by decision layer
                                    technical_indicators_dict = {TimeFrame.M5: technical_indicators} if technical_indicators else {}
                                    
                                    decision = await self.decision_layer.make_technical_decision(
                                        pair, technical_indicators_dict, market_context, current_price, candles_by_timeframe
                                    )
                                    
                                    # Risk Management - Always assess risk for recommendations
                                    if recommendation:
                                        try:
                                            # Create a temporary decision for risk assessment
                                            temp_decision = TradeDecision(
                                                recommendation=recommendation,
                                                approved=False,
                                                position_size=None,
                                                risk_amount=None,
                                                modified_stop_loss=recommendation.stop_loss,
                                                modified_take_profit=recommendation.take_profit,
                                                risk_management_notes="",
                                                timestamp=datetime.utcnow()
                                            )
                                            
                                            risk_assessment = await self.advanced_risk_manager.assess_trade_risk(
                                                temp_decision, market_context, technical_indicators, fundamental_analysis
                                            )
                                        except Exception as e:
                                            risk_assessment = {
                                                'approved': False,
                                                'reason': f'Risk assessment failed: {str(e)}',
                                                'risk_score': 0.0,
                                                'max_position_size': 0.0,
                                                'portfolio_heat': 0.0
                                            }
                                    else:
                                        risk_assessment = {
                                            'approved': False,
                                            'reason': 'No recommendation',
                                            'risk_score': 0.0,
                                            'max_position_size': 0.0,
                                            'portfolio_heat': 0.0
                                        }
                                    
                                    pair_analysis['risk_assessment'] = {
                                        'approved': risk_assessment.get('approved', False),
                                        'reason': risk_assessment.get('reason', 'Unknown'),
                                        'risk_score': risk_assessment.get('risk_score', 0.0),
                                        'max_position_size': risk_assessment.get('max_position_size', 0.0),
                                        'portfolio_heat': risk_assessment.get('portfolio_heat', 0.0)
                                    }
                                    
                                    if decision:
                                        # Position sizing handled in RiskManager; avoid duplicate sizing here
                                        try:
                                            pass
                                        except Exception as e:
                                            pair_analysis['errors'].append(f"Position sizing failed: {str(e)}")
                                        pair_analysis['decision'] = {
                                            'signal': decision.recommendation.signal.value,
                                            'entry_price': float(decision.recommendation.entry_price) if decision.recommendation.entry_price else None,
                                            'stop_loss': float(decision.modified_stop_loss) if decision.modified_stop_loss else None,
                                            'take_profit': float(decision.modified_take_profit) if decision.modified_take_profit else None,
                                            'position_size': float(decision.position_size) if decision.position_size else None,
                                            'reasoning': decision.recommendation.reasoning
                                        }
                                        
                                        if risk_assessment['approved']:
                                            # Optional manual approval gate
                                            try:
                                                if self.config.notifications.manual_trade_approval:
                                                    # Send pre-trade notification and stop here; execution will happen via callback handler on Accept
                                                    await self._send_pre_trade_notification(decision, fundamental_analysis, regime_analysis)
                                                    pair_analysis['trade_executed'] = False
                                                    pair_analysis['trade_id'] = None
                                                    # Skip auto execution when manual approval is enabled
                                                    continue
                                            except Exception as e:
                                                self.logger.error(f"Pre-trade notification failed: {e}")

                                            # Auto execution path
                                            trade_id = await self.position_manager.execute_trade(decision, market_context)
                                            
                                            if trade_id:
                                                loop_stats['trades_executed'] += 1
                                                pair_analysis['trade_executed'] = True
                                                pair_analysis['trade_id'] = trade_id
                                        else:
                                            loop_stats['trades_rejected'] += 1
                                    else:
                                        pair_analysis['decision'] = None
                                        if recommendation:
                                            loop_stats['trades_rejected'] += 1
                                except Exception as e:
                                    pair_analysis['errors'].append(f"Decision making failed: {str(e)}")
                                    
                            except Exception as e:
                                debug_tracker.log_error(context, e, f"General analysis failed for {pair}")
                                pair_analysis['errors'].append(f"General analysis failed: {str(e)}")
                                
                            # Store pair analysis in loop stats
                            loop_stats['pair_analyses'][pair] = pair_analysis
                
                    # Check shutdown signal before sending report
                    if not self.is_running:
                        print("🛑 [DEBUG] Shutdown signal detected, skipping loop report...")
                        break
                        
                    # Generate and send enhanced loop report
                    await self._send_enhanced_loop_report(loop_stats)
                    
                    # Wait for next loop
                    await asyncio.sleep(self.config.data_update_frequency)
                    
                except Exception as e:
                    debug_tracker.log_error(context, e, "Error in trading loop iteration")
                    print(f"❌ [DEBUG] Error in enhanced trading loop: {e}")
                    print(f"❌ [DEBUG] Traceback: {traceback.format_exc()}")
                    self.logger.error(f"Error in enhanced trading loop: {e}")
                    self.logger.error(f"Traceback: {traceback.format_exc()}")
                    await asyncio.sleep(5)  # Wait before retrying
    
    async def _send_enhanced_trade_notification(self, decision, trade_id, 
                                              fundamental_analysis, regime_analysis):
        """Send enhanced trade notification with all analysis data."""
        try:
            notification_message = f"""
🎯 ENHANCED TRADE EXECUTED

📊 Trade Details:
• Pair: {decision.recommendation.pair}
• Signal: {decision.recommendation.signal.value.upper()}
• Entry: {decision.recommendation.entry_price}
• Stop Loss: {decision.modified_stop_loss}
• Take Profit: {decision.modified_take_profit}
• Position Size: {decision.position_size:.2f}
• Risk Amount: ${decision.risk_amount:.2f}

🔍 Market Analysis:
• Market Condition: {decision.recommendation.market_condition.value}
• Regime: {regime_analysis['regime']} (Confidence: {regime_analysis['confidence']:.2f})
• Fundamental Score: {fundamental_analysis['fundamental_score']:.2f}
• Session: {fundamental_analysis['current_session']}

⚡ Risk Management:
• Kelly Criterion: {decision.risk_management_notes}
• Portfolio Heat: {fundamental_analysis.get('correlation_analysis', {}).get('portfolio_heat', 0):.2f}
• Position Multiplier: {fundamental_analysis['position_size_multiplier']:.2f}

🕐 Executed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""".strip()
            
            await self.notification_layer.send_trade_alert(decision, chart_data={
                'fundamental_analysis': fundamental_analysis,
                'regime_analysis': regime_analysis,
                'trade_id': trade_id
            }, custom_message=notification_message)
            
        except Exception as e:
            self.logger.error(f"Error sending enhanced trade notification: {e}")
    
    async def _send_pre_trade_notification(self, decision, fundamental_analysis, regime_analysis):
        """Send pre-trade notification prior to execution when manual approval is enabled."""
        try:
            message = f"""
🚨 PENDING TRADE

• Pair: {decision.recommendation.pair}
• Signal: {decision.recommendation.signal.value.upper()}
• Entry: {decision.recommendation.entry_price}
• Stop Loss: {decision.modified_stop_loss}
• Take Profit: {decision.modified_take_profit}
• Position Size: {decision.position_size if decision.position_size else 'N/A'}

📊 Market:
• Condition: {decision.recommendation.market_condition.value}
• Regime: {regime_analysis.get('regime', 'UNKNOWN')} (Conf: {regime_analysis.get('confidence', 0):.2f})
• Fundamental Score: {fundamental_analysis.get('fundamental_score', 0):.2f}

⏳ Awaiting execution...
""".strip()

            await self.notification_layer.send_trade_alert(
                decision,
                chart_data={
                    'fundamental_analysis': fundamental_analysis,
                    'regime_analysis': regime_analysis,
                },
                custom_message=message
            )
        except Exception as e:
            self.logger.error(f"Error sending pre-trade notification: {e}")
    
    async def _send_enhanced_loop_report(self, loop_stats):
        """Send enhanced loop report with detailed analysis for each pair."""
        try:
            # Get component summaries
            position_summary = await self.position_manager.get_position_summary()
            fundamental_summary = await self.fundamental_analyzer.get_fundamental_summary()
            risk_summary = await self.advanced_risk_manager.get_risk_summary()
            regime_summary = await self.market_regime_detector.get_regime_summary()
            
            loop_duration = (datetime.now() - loop_stats['timestamp']).total_seconds()
            
            # Build detailed pair analysis section
            pair_analysis_section = ""
            for pair, analysis in loop_stats['pair_analyses'].items():
                self.logger.info(f"Processing analysis for {pair}: {type(analysis)}")
                if analysis is None:
                    self.logger.error(f"Analysis is None for {pair}")
                    continue
                pair_analysis_section += f"""
🔍 {pair} ANALYSIS:
   📊 Market Context: {analysis.get('market_context', {}).get('condition', 'UNKNOWN')} | Volatility: {analysis.get('market_context', {}).get('volatility', 0.0):.4f} | Trend Strength: {analysis.get('market_context', {}).get('trend_strength', 0.0):.3f}
   📈 Timeframes: {', '.join([f"{tf}({count})" for tf, count in analysis.get('candles_by_timeframe', {}).items()])}
   
   📰 Fundamental: Sentiment {analysis.get('fundamental_analysis', {}).get('sentiment', 'NEUTRAL')} ({analysis.get('fundamental_analysis', {}).get('sentiment_score', 0):.3f}) | News: {analysis.get('fundamental_analysis', {}).get('news_count', 0)}
   
   📊 Technical Recommendation: {(analysis.get('technical_recommendation') or {}).get('signal', 'NONE')} | Confidence: {(analysis.get('technical_recommendation') or {}).get('confidence', 0.0):.3f}
   💰 Entry: {(analysis.get('technical_recommendation') or {}).get('entry_price', 'N/A')}
   🛑 Stop Loss: {(analysis.get('technical_recommendation') or {}).get('stop_loss', 'N/A')}
   🎯 Take Profit: {(analysis.get('technical_recommendation') or {}).get('take_profit', 'N/A')}
   ⚖️ R:R Ratio: {(analysis.get('technical_recommendation') or {}).get('risk_reward_ratio', 0.0):.2f}
   
   📈 Technical Indicators:
   • RSI: {analysis.get('technical_indicators', {}).get('rsi', 'N/A') if analysis.get('technical_indicators') else 'N/A'}
   • MACD: {analysis.get('technical_indicators', {}).get('macd', 'N/A') if analysis.get('technical_indicators') else 'N/A'}
   • MACD Signal: {analysis.get('technical_indicators', {}).get('macd_signal', 'N/A') if analysis.get('technical_indicators') else 'N/A'}
   • MACD Hist: {analysis.get('technical_indicators', {}).get('macd_histogram', 'N/A') if analysis.get('technical_indicators') else 'N/A'}
   • ATR: {analysis.get('technical_indicators', {}).get('atr', 'N/A') if analysis.get('technical_indicators') else 'N/A'}
   • EMA Fast/Slow: {analysis.get('technical_indicators', {}).get('ema_fast', 'N/A') if analysis.get('technical_indicators') else 'N/A'} / {analysis.get('technical_indicators', {}).get('ema_slow', 'N/A') if analysis.get('technical_indicators') else 'N/A'}
   • Bollinger U/M/L: {analysis.get('technical_indicators', {}).get('bollinger_upper', 'N/A') if analysis.get('technical_indicators') else 'N/A'} / {analysis.get('technical_indicators', {}).get('bollinger_middle', 'N/A') if analysis.get('technical_indicators') else 'N/A'} / {analysis.get('technical_indicators', {}).get('bollinger_lower', 'N/A') if analysis.get('technical_indicators') else 'N/A'}
   • Keltner U/M/L: {analysis.get('technical_indicators', {}).get('keltner_upper', 'N/A') if analysis.get('technical_indicators') else 'N/A'} / {analysis.get('technical_indicators', {}).get('keltner_middle', 'N/A') if analysis.get('technical_indicators') else 'N/A'} / {analysis.get('technical_indicators', {}).get('keltner_lower', 'N/A') if analysis.get('technical_indicators') else 'N/A'}
   
   📊 Regime: {(analysis.get('regime_analysis') or {}).get('regime', 'UNKNOWN')} | Confidence: {(analysis.get('regime_analysis') or {}).get('confidence', 0.0):.3f} | Volatility: {(analysis.get('regime_analysis') or {}).get('volatility_state', 'UNKNOWN')}
   
   🎯 Decision: {(analysis.get('decision') or {}).get('signal', 'NONE')} | Entry: {(analysis.get('decision') or {}).get('entry_price', 'N/A')}
   
   ⚠️ Risk Assessment: {'✅ APPROVED' if (analysis.get('risk_assessment') or {}).get('approved', False) else '❌ REJECTED'} | Score: {(analysis.get('risk_assessment') or {}).get('risk_score', 0.0):.3f} | Reason: {(analysis.get('risk_assessment') or {}).get('reason', 'Unknown')}
   
   💰 Trade Status: {'✅ EXECUTED' if analysis.get('trade_executed', False) else '❌ NOT EXECUTED'} | ID: {analysis.get('trade_id', 'N/A') if analysis.get('trade_id') else 'N/A'}
   
   ❌ Errors: {', '.join(analysis['errors']) if analysis['errors'] else 'None'}
"""
            
            report_message = f"""
📊 ENHANCED LOOP REPORT
✅ Status: COMPLETED
⏱️ Duration: {loop_duration:.2f} seconds
🕐 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📈 ANALYSIS SUMMARY:
• Pairs Analyzed: {len(loop_stats['pairs_analyzed'])} ({', '.join(loop_stats['pairs_analyzed'])})
• Technical Analyses Performed: {loop_stats['technical_analyses']}
• Technical Indicators Calculated: {loop_stats['technical_indicators']}
• Data Points Processed: {loop_stats['data_points']}
• Fundamental Analyses: {loop_stats['fundamental_analyses']}
• Regime Detections: {loop_stats['regime_detections']}

🎯 TRADE DECISIONS:
• Trades Executed: {loop_stats['trades_executed']}
• Trades Rejected: {loop_stats['trades_rejected']}
• Approval Rate: {(loop_stats['trades_executed'] / max(1, loop_stats['trades_executed'] + loop_stats['trades_rejected'])) * 100:.1f}%

🚀 ADVANCED COMPONENTS:
• Active Positions: {position_summary['active_positions']}
• Daily P&L: ${position_summary['daily_pnl']:.2f}
• Current Regime: {regime_summary['current_regime']} (Confidence: {regime_summary['regime_confidence']:.2f})
• Portfolio Heat: {risk_summary['portfolio_heat']:.2f}
• Win Rate: {risk_summary['win_rate']:.1%}
• Drawdown: {risk_summary['current_drawdown']:.2%}

📊 DAILY PERFORMANCE:
• Total Trades: {risk_summary['total_trades']}
• Winning Trades: {int(risk_summary['win_rate'] * risk_summary['total_trades'])}
• Losing Trades: {risk_summary['total_trades'] - int(risk_summary['win_rate'] * risk_summary['total_trades'])}
• Win Rate: {risk_summary['win_rate']:.1%}
• Profit Factor: {risk_summary['profit_factor']:.2f}
• Net Profit: ${position_summary['daily_pnl']:.2f}

{pair_analysis_section}
""".strip()
            
            await self.notification_layer.send_notification(
                notification_type="LOOP_REPORT",
                data={"message": report_message}
            )
            
        except Exception as e:
            self.logger.error(f"Error sending enhanced loop report: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _should_analyze_pair(self, pair: str) -> bool:
        """Check if we should analyze this pair."""
        return pair in self.config.trading_pairs
    
    def _get_current_price(self, candles: List[CandleData]) -> Decimal:
        """Get current price from the latest candle."""
        if not candles:
            return Decimal('0')
        
        latest_candle = candles[-1]
        return (latest_candle.high + latest_candle.low) / 2  # Use typical price
    
    async def cleanup(self):
        """Cleanup all components."""
        print("🧹 [DEBUG] Cleaning up trading bot...")
        self.logger.info("Cleaning up trading bot...")
        self.is_running = False
        
        # Stop all components
        print("🧹 [DEBUG] Stopping data layer...")
        await self.data_layer.stop()
        print("✅ [DEBUG] Data layer stopped")
        
        print("🧹 [DEBUG] Closing technical analysis layer...")
        await self.technical_layer.stop()
        print("✅ [DEBUG] Technical analysis layer closed")
        
        print("🧹 [DEBUG] Closing decision layer...")
        await self.decision_layer.close()
        print("✅ [DEBUG] Decision layer closed")
        
        print("🧹 [DEBUG] Closing notification layer...")
        await self.notification_layer.close()
        print("✅ [DEBUG] Notification layer closed")
        
        # Stop new advanced components
        print("🧹 [DEBUG] Stopping position manager...")
        await self.position_manager.stop()
        print("✅ [DEBUG] Position manager stopped")
        
        print("🧹 [DEBUG] Stopping fundamental analyzer...")
        await self.fundamental_analyzer.stop()
        print("✅ [DEBUG] Fundamental analyzer stopped")
        
        print("🧹 [DEBUG] Stopping advanced risk manager...")
        await self.advanced_risk_manager.stop()
        print("✅ [DEBUG] Advanced risk manager stopped")
        
        print("🧹 [DEBUG] Stopping market regime detector...")
        await self.market_regime_detector.stop()
        print("✅ [DEBUG] Market regime detector stopped")
        
        print("✅ [DEBUG] Trading bot cleanup completed")
        self.logger.info("Trading bot cleanup completed")


@debug_performance
async def main():
    """Main entry point."""
    debug_entry_point("main")
    
    with debug_context("Main function execution") as context:
        print("🚀 [DEBUG] Starting main function...")
        debug_variable("main_start_time", datetime.now(), context)
        bot = None
        debug_variable("bot_initial", None, context)
        
        try:
            print("🔧 [DEBUG] Creating TradingBot instance...")
            debug_data_flow("bot_creation", "starting", "TradingBot")
            bot = TradingBot()
            debug_variable("bot_created", True, context)
            debug_variable("bot_instance", bot, context)
            print("✅ [DEBUG] TradingBot instance created successfully")
            
            # Setup signal handlers
            print("🔧 [DEBUG] Setting up signal handlers...")
            debug_data_flow("signal_handlers", "setting_up", "signal_handlers")
            
            def signal_handler(signum, frame):
                print("\n🛑 [DEBUG] Shutdown signal received. Cleaning up...")
                debug_variable("signal_received", signum, context)
                # Set the running flag to False to stop the main loop
                if bot:
                    bot.is_running = False
                    debug_variable("bot_is_running_set_false", True, context)
                    # Force exit after a short delay if the bot doesn't stop gracefully
                    import threading
                    def force_exit():
                        import time
                        time.sleep(3)  # Wait 3 seconds
                        print("🛑 [DEBUG] Force exiting...")
                        debug_variable("force_exit_triggered", True, context)
                        import os
                        os._exit(0)
                    threading.Thread(target=force_exit, daemon=True).start()
                    debug_variable("force_exit_thread_started", True, context)
            
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            debug_variable("signal_handlers_registered", True, context)
            print("✅ [DEBUG] Signal handlers set up")
            
            print("🚀 [DEBUG] Starting bot...")
            debug_data_flow("bot_start", "starting", "bot_start")
            await bot.start()
            debug_variable("bot_started", True, context)
            print("✅ [DEBUG] Bot started successfully")
            
        except KeyboardInterrupt:
            print("\n🛑 [DEBUG] Keyboard interrupt received.")
            debug_tracker.log_warning(context, "Keyboard interrupt received")
        except Exception as e:
            debug_tracker.log_error(context, e, "Error in main function")
            print(f"❌ [DEBUG] Error in main: {e}")
            print(f"❌ [DEBUG] Traceback: {traceback.format_exc()}")
        finally:
            print("🧹 [DEBUG] Cleaning up...")
            debug_data_flow("cleanup", "starting", "cleanup")
            if bot:
                await bot.cleanup()
                debug_variable("bot_cleanup_completed", True, context)
                print("✅ [DEBUG] Cleanup completed")
            else:
                debug_variable("no_bot_to_cleanup", True, context)
                print("ℹ️ [DEBUG] No bot instance to cleanup")
            
            # Export final debug report
            debug_report_path = export_debug_report()
            debug_variable("debug_report_path", debug_report_path, context)
            print(f"📊 [DEBUG] Debug report exported to: {debug_report_path}")
            
            # Log final debug summary
            debug_summary = get_debug_summary()
            debug_variable("final_debug_summary", debug_summary, context)
            print(f"📊 [DEBUG] Final debug summary: {debug_summary}")


if __name__ == "__main__":
    asyncio.run(main())