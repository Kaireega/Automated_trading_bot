#!/usr/bin/env python3
"""
Market Adaptive Trading Bot - Main Entry Point and Orchestrator.
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
    """Enhanced Market Adaptive Trading Bot."""

    def __init__(self):
        debug_entry_point("TradingBot.__init__")

        with debug_context("TradingBot initialization") as context:
            print("🔧 [DEBUG] Creating TradingBot instance...")
            self.logger = get_logger(__name__)
            print("🔧 [DEBUG] Logger initialized")

            print("🔧 [DEBUG] Loading configuration...")
            self.config = Config()
            print(f"🔧 [DEBUG] Configuration loaded - Trading pairs: {self.config.trading_pairs}")

            print("🔧 [DEBUG] Initializing OANDA API...")
            self.oanda_api = OandaApi()
            print("🔧 [DEBUG] OANDA API initialized")

            try:
                data_dir = Path(__file__).parent.parent.parent / "data"
                ic.LoadInstruments(str(data_dir))
                print(f"✅ [DEBUG] Instruments loaded from {data_dir}")
            except Exception as e:
                print(f"❌ [DEBUG] Failed to load instruments: {e}")

            # Core components
            self.data_layer = DataLayer(self.config)
            self.technical_layer = TechnicalAnalysisLayer(self.config)
            self.decision_layer = TechnicalDecisionLayer(self.config)
            self.notification_layer = NotificationLayer(self.config)
            self.position_manager = PositionManager(self.config, self.oanda_api)
            self.fundamental_analyzer = FundamentalAnalyzer(self.config)
            self.advanced_risk_manager = AdvancedRiskManager(self.config)
            self.market_regime_detector = MarketRegimeDetector(self.config)
            self.backtest_engine = BacktestEngine(self.config, use_historical_feed=False)

            self.is_running = False
            self.loop_count = 0
            print("✅ [DEBUG] TradingBot initialized successfully")

    @debug_performance
    async def start(self):
        """Start the trading bot."""
        debug_entry_point("TradingBot.start")

        with debug_context("TradingBot startup") as context:
            try:
                self.logger.info("Starting Enhanced Market Adaptive Trading Bot...")

                await self.data_layer.start()
                await self.technical_layer.start()
                await self.decision_layer.start()
                await self.notification_layer.start()
                self.notification_layer.set_trade_executor(self._execute_trade_from_notification)
                await self.position_manager.start()
                await self.fundamental_analyzer.start()
                await self.advanced_risk_manager.start()
                await self.market_regime_detector.start()
                await self.backtest_engine.start()

                self.logger.info("All components initialized successfully")
                await self._send_startup_message()

                self.is_running = True
                await self._enhanced_trading_loop()

            except Exception as e:
                print(f"❌ [DEBUG] Error starting bot: {e}")
                self.logger.error(f"Error starting bot: {e}\n{traceback.format_exc()}")
                raise

    async def _send_startup_message(self):
        """Send startup notification."""
        try:
            position_summary = await self.position_manager.get_position_summary()
            regime_summary = await self.market_regime_detector.get_regime_summary()
            risk_summary = await self.advanced_risk_manager.get_risk_summary()

            msg = f"""
🤖 Enhanced Trading Bot Started Successfully

🎯 Configuration:
• Trading Pairs: {', '.join([p.replace('_', '') for p in self.config.trading_pairs])}
• Risk Management: {self.config.trading.risk_percentage}% per trade
• Daily Loss Limit: {self.config.risk_management.max_daily_loss}%

🔄 Current Status:
• Active Positions: {position_summary['active_positions']}
• Daily P&L: ${position_summary['daily_pnl']:.2f}
• Current Regime: {regime_summary['current_regime']}

Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""".strip()

            await self.notification_layer.send_notification(
                notification_type="STARTUP",
                data={"message": msg}
            )
        except Exception as e:
            self.logger.error(f"Error sending startup message: {e}")

    async def _execute_trade_from_notification(self, decision: TradeDecision) -> Optional[str]:
        """Executor used by notification layer after manual acceptance."""
        try:
            market_context = await self.data_layer.get_market_context(decision.recommendation.pair)
            return await self.position_manager.execute_trade(decision, market_context)
        except Exception as e:
            self.logger.error(f"Error executing trade from notification: {e}")
            return None

    @debug_performance
    async def _enhanced_trading_loop(self) -> None:
        """Main trading loop."""
        debug_entry_point("TradingBot._enhanced_trading_loop")

        with debug_context("Enhanced trading loop") as context:
            while self.is_running:
                try:
                    self.loop_count += 1

                    # Fetch data for all pairs
                    all_data = await self.data_layer.get_all_data()

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

                    for pair in all_data.keys():
                        if not self.is_running:
                            break

                        if not self._should_analyze_pair(pair):
                            continue

                        loop_stats['pairs_analyzed'].add(pair)

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

                        try:
                            # ── Candle data ──────────────────────────────────
                            candles_data = all_data[pair]
                            loop_stats['data_points'] += sum(len(c) for c in candles_data.values())

                            if len(candles_data) < 2:
                                continue

                            for timeframe, candles in candles_data.items():
                                pair_analysis['candles_by_timeframe'][timeframe.value] = len(candles)

                            # ── Market context ───────────────────────────────
                            market_context = await self.data_layer.get_market_context(pair)
                            pair_analysis['market_context'] = {
                                'condition': market_context.condition.value,
                                'volatility': market_context.volatility,
                                'trend_strength': market_context.trend_strength,
                                'news_sentiment': market_context.news_sentiment
                            }

                            # Filter timeframes with enough candles
                            candles_by_timeframe = {
                                tf: candles for tf, candles in candles_data.items()
                                if len(candles) >= 20
                            }

                            if len(candles_by_timeframe) < self.config.multi_timeframe.minimum_timeframes:
                                continue

                            if not self.is_running:
                                break

                            # ── Fundamental analysis ─────────────────────────
                            # FIX: default set before try so it's always defined
                            fundamental_analysis = {
                                'sentiment': 'NEUTRAL',
                                'sentiment_score': 0.0,
                                'news_count': 0,
                                'economic_events': [],
                                'fundamental_score': 0.0,
                                'current_session': 'UNKNOWN',
                                'position_size_multiplier': 1.0
                            }
                            try:
                                fundamental_analysis = await self.fundamental_analyzer.analyze_fundamentals(
                                    pair, market_context
                                )
                                pair_analysis['fundamental_analysis'] = {
                                    'sentiment': fundamental_analysis.get('sentiment', 'NEUTRAL'),
                                    'sentiment_score': fundamental_analysis.get('sentiment_score', 0.0),
                                    'news_count': fundamental_analysis.get('news_count', 0),
                                    'economic_events': fundamental_analysis.get('economic_events', [])
                                }
                                loop_stats['fundamental_analyses'] += 1
                            except Exception as e:
                                pair_analysis['errors'].append(f"Fundamental analysis failed: {str(e)}")

                            if not self.is_running:
                                break

                            # ── Technical analysis ───────────────────────────
                            recommendation = None
                            technical_indicators = None
                            try:
                                recommendation, technical_indicators = await self.technical_layer.analyze_multiple_timeframes(
                                    pair, candles_by_timeframe, market_context
                                )

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

                            if not self.is_running:
                                break

                            # ── Market regime detection ──────────────────────
                            regime_analysis = {'regime': 'UNKNOWN', 'confidence': 0.0}
                            try:
                                if technical_indicators:
                                    primary_candles = candles_by_timeframe.get(TimeFrame.M5, [])
                                    if not primary_candles:
                                        primary_candles = list(candles_by_timeframe.values())[0] if candles_by_timeframe else []

                                    regime_analysis = await self.market_regime_detector.detect_regime(
                                        pair, primary_candles, market_context, technical_indicators
                                    )
                                    loop_stats['regime_detections'] += 1

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
                                    pair_analysis['regime_analysis'] = {
                                        'regime': 'UNKNOWN',
                                        'confidence': 0.0,
                                        'volatility_state': 'UNKNOWN',
                                        'trend_strength': 0.0
                                    }
                            except Exception as e:
                                pair_analysis['errors'].append(f"Regime detection failed: {str(e)}")

                            if not self.is_running:
                                break

                            # ── Decision making ──────────────────────────────
                            try:
                                current_price = self._get_current_price(
                                    candles_by_timeframe.get(TimeFrame.M5, [])
                                )
                                technical_indicators_dict = {TimeFrame.M5: technical_indicators} if technical_indicators else {}

                                decision = await self.decision_layer.make_technical_decision(
                                    pair, technical_indicators_dict, market_context,
                                    current_price, candles_by_timeframe
                                )

                                # Risk assessment
                                if recommendation:
                                    try:
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
                                            temp_decision, market_context,
                                            technical_indicators, fundamental_analysis
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
                                    pair_analysis['decision'] = {
                                        'signal': decision.recommendation.signal.value,
                                        'entry_price': float(decision.recommendation.entry_price) if decision.recommendation.entry_price else None,
                                        'stop_loss': float(decision.modified_stop_loss) if decision.modified_stop_loss else None,
                                        'take_profit': float(decision.modified_take_profit) if decision.modified_take_profit else None,
                                        'position_size': float(decision.position_size) if decision.position_size else None,
                                        'reasoning': decision.recommendation.reasoning
                                    }

                                    if risk_assessment['approved']:
                                        try:
                                            if self.config.notifications.manual_trade_approval:
                                                await self._send_pre_trade_notification(
                                                    decision, fundamental_analysis, regime_analysis
                                                )
                                                pair_analysis['trade_executed'] = False
                                                pair_analysis['trade_id'] = None
                                                continue
                                        except Exception as e:
                                            self.logger.error(f"Pre-trade notification failed: {e}")
                                            continue  # CRITICAL: prevent trade executing without approval

                                        trade_id = await self.position_manager.execute_trade(
                                            decision, market_context
                                        )
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

                            # Store pair analysis
                            loop_stats['pair_analyses'][pair] = pair_analysis

                        except Exception as e:
                            self.logger.error(f"General analysis failed for {pair}: {e}")
                            pair_analysis['errors'].append(f"General analysis failed: {str(e)}")
                            loop_stats['pair_analyses'][pair] = pair_analysis

                    # End of pair loop
                    if not self.is_running:
                        break

                    await self._send_enhanced_loop_report(loop_stats)
                    await asyncio.sleep(self.config.data_update_frequency)

                except Exception as e:
                    self.logger.error(f"Error in trading loop: {e}\n{traceback.format_exc()}")
                    await asyncio.sleep(5)

    async def _send_pre_trade_notification(self, decision, fundamental_analysis, regime_analysis):
        """Send pre-trade notification when manual approval is enabled."""
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
        """Send loop report with analysis for each pair."""
        try:
            position_summary = await self.position_manager.get_position_summary()
            risk_summary = await self.advanced_risk_manager.get_risk_summary()
            regime_summary = await self.market_regime_detector.get_regime_summary()

            loop_duration = (datetime.now() - loop_stats['timestamp']).total_seconds()

            pair_section = ""
            for pair, analysis in loop_stats['pair_analyses'].items():
                if analysis is None:
                    continue
                rec = analysis.get('technical_recommendation') or {}
                ind = analysis.get('technical_indicators') or {}
                reg = analysis.get('regime_analysis') or {}
                dec = analysis.get('decision') or {}
                risk = analysis.get('risk_assessment') or {}
                ctx = analysis.get('market_context') or {}
                fund = analysis.get('fundamental_analysis') or {}

                pair_section += f"""
🔍 {pair}:
   Market: {ctx.get('condition','?')} | Vol: {ctx.get('volatility',0):.4f} | Trend: {ctx.get('trend_strength',0):.3f}
   Fundamental: {fund.get('sentiment','NEUTRAL')} ({fund.get('sentiment_score',0):.3f})
   Signal: {rec.get('signal','NONE')} | Confidence: {rec.get('confidence',0):.3f} | R:R: {rec.get('risk_reward_ratio',0):.2f}
   RSI: {ind.get('rsi','N/A')} | MACD: {ind.get('macd','N/A')} | ATR: {ind.get('atr','N/A')}
   Regime: {reg.get('regime','?')} ({reg.get('confidence',0):.2f}) | Volatility: {reg.get('volatility_state','?')}
   Decision: {dec.get('signal','NONE')} | Risk: {'✅' if risk.get('approved') else '❌'} {risk.get('reason','?')}
   Trade: {'✅ EXECUTED' if analysis.get('trade_executed') else '❌ NOT EXECUTED'}
   Errors: {', '.join(analysis['errors']) if analysis['errors'] else 'None'}
"""

            report = f"""
📊 LOOP REPORT — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Duration: {loop_duration:.2f}s | Loop #{self.loop_count}

Pairs Analyzed: {len(loop_stats['pairs_analyzed'])}
Trades Executed: {loop_stats['trades_executed']} | Rejected: {loop_stats['trades_rejected']}
Active Positions: {position_summary['active_positions']} | Daily P&L: ${position_summary['daily_pnl']:.2f}
Regime: {regime_summary['current_regime']} | Win Rate: {risk_summary['win_rate']:.1%}
{pair_section}
""".strip()

            await self.notification_layer.send_notification(
                notification_type="LOOP_REPORT",
                data={"message": report}
            )
        except Exception as e:
            self.logger.error(f"Error sending loop report: {e}\n{traceback.format_exc()}")

    def _should_analyze_pair(self, pair: str) -> bool:
        return pair in self.config.trading_pairs

    def _get_current_price(self, candles: List[CandleData]) -> Decimal:
        if not candles:
            return Decimal('0')
        latest = candles[-1]
        return (latest.high + latest.low) / 2

    async def cleanup(self):
        """Gracefully stop all components."""
        self.logger.info("Cleaning up trading bot...")
        self.is_running = False

        await self.data_layer.stop()
        await self.technical_layer.stop()
        await self.decision_layer.close()
        await self.notification_layer.close()
        await self.position_manager.stop()
        await self.fundamental_analyzer.stop()
        await self.advanced_risk_manager.stop()
        await self.market_regime_detector.stop()

        self.logger.info("Trading bot cleanup completed")


@debug_performance
async def main():
    """Main entry point."""
    debug_entry_point("main")

    with debug_context("Main function execution") as context:
        bot = None
        try:
            bot = TradingBot()

            def signal_handler(signum, frame):
                print("\n🛑 Shutdown signal received. Cleaning up...")
                if bot:
                    bot.is_running = False
                    import threading
                    def force_exit():
                        import time, os
                        time.sleep(3)
                        os._exit(0)
                    threading.Thread(target=force_exit, daemon=True).start()

            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

            await bot.start()

        except KeyboardInterrupt:
            print("\n🛑 Keyboard interrupt received.")
        except Exception as e:
            print(f"❌ Error in main: {e}\n{traceback.format_exc()}")
        finally:
            if bot:
                await bot.cleanup()
            debug_report_path = export_debug_report()
            print(f"📊 Debug report: {debug_report_path}")


if __name__ == "__main__":
    asyncio.run(main())
