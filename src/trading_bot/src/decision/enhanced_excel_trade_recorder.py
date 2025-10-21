"""
Enhanced Excel Trade Recorder - Records complete AI outputs and decision data.
"""
import pandas as pd
import json
import os
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List
from decimal import Decimal
from pathlib import Path

from ..core.models import (
    TradeDecision, TradeRecommendation, MarketContext, 
    TechnicalIndicators, CandleData, TimeFrame
)
from ..utils.logger import get_logger


class EnhancedExcelTradeRecorder:
    """Records comprehensive trade information including complete AI outputs to Excel."""
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger(__name__)
        
        # Create logs directory
        self.logs_dir = Path("logs/trades")
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Excel file path
        self.excel_file = self.logs_dir / "complete_trading_records.xlsx"
        
        # Data storage for batch writing
        self.trades_data = []
        self.market_conditions_data = []
        self.indicators_data = []
        self.ai_outputs_data = []
        self.multi_timeframe_data = []
        self.risk_assessment_data = []
        self.raw_data_data = []
        
        # Initialize Excel file if it doesn't exist
        self._initialize_excel_file()
    
    def _initialize_excel_file(self):
        """Initialize Excel file with headers if it doesn't exist."""
        if not self.excel_file.exists():
            # Create empty DataFrames with comprehensive headers
            trades_df = pd.DataFrame(columns=[
                'timestamp', 'pair', 'signal', 'confidence', 'entry_price', 
                'stop_loss', 'take_profit', 'risk_reward_ratio', 'estimated_hold_time',
                'market_condition', 'reasoning', 'approved', 'position_size', 
                'risk_amount', 'modified_stop_loss', 'modified_take_profit', 
                'risk_management_notes', 'final_decision_reason'
            ])
            
            market_df = pd.DataFrame(columns=[
                'timestamp', 'pair', 'condition', 'volatility', 'trend_strength',
                'volume_profile', 'news_events', 'economic_calendar', 'market_sentiment',
                'key_levels', 'support_resistance'
            ])
            
            indicators_df = pd.DataFrame(columns=[
                'timestamp', 'pair', 'timeframe', 'rsi', 'macd', 'macd_signal',
                'macd_histogram', 'ema_fast', 'ema_slow', 'bollinger_upper',
                'bollinger_middle', 'bollinger_lower', 'atr', 'stoch_k', 'stoch_d',
                'support_level', 'resistance_level', 'fibonacci_levels'
            ])
            
            ai_outputs_df = pd.DataFrame(columns=[
                'timestamp', 'pair', 'ai_prompt_used', 'ai_raw_response', 'ai_parsed_data',
                'ai_confidence', 'ai_signal', 'ai_reasoning', 'ai_market_condition',
                'ai_entry_price', 'ai_stop_loss', 'ai_take_profit', 'ai_risk_reward',
                'ai_hold_time', 'ai_model_used', 'ai_temperature', 'ai_max_tokens'
            ])
            
            multi_timeframe_df = pd.DataFrame(columns=[
                'timestamp', 'pair', 'timeframe', 'signal_type', 'signal_strength',
                'trend_direction', 'momentum', 'volatility', 'technical_score',
                'entry_price', 'stop_loss', 'take_profit', 'risk_reward_ratio',
                'confidence', 'consensus_weight'
            ])
            
            risk_assessment_df = pd.DataFrame(columns=[
                'timestamp', 'pair', 'risk_assessment_result', 'risk_reason',
                'position_size_calculated', 'risk_amount_calculated',
                'daily_loss_check', 'correlation_check', 'max_trades_check',
                'volatility_check', 'market_hours_check', 'risk_notes'
            ])
            
            raw_data_df = pd.DataFrame(columns=[
                'timestamp', 'pair', 'timeframe', 'candle_count', 'price_data',
                'volume_data', 'market_context_raw', 'technical_analysis_raw',
                'news_data', 'economic_data', 'sentiment_data'
            ])
            
            # Write to Excel with multiple sheets
            with pd.ExcelWriter(self.excel_file, engine='openpyxl') as writer:
                trades_df.to_excel(writer, sheet_name='Trades', index=False)
                market_df.to_excel(writer, sheet_name='Market_Conditions', index=False)
                indicators_df.to_excel(writer, sheet_name='Technical_Indicators', index=False)
                ai_outputs_df.to_excel(writer, sheet_name='AI_Outputs', index=False)
                multi_timeframe_df.to_excel(writer, sheet_name='Multi_Timeframe_Analysis', index=False)
                risk_assessment_df.to_excel(writer, sheet_name='Risk_Assessment', index=False)
                raw_data_df.to_excel(writer, sheet_name='Raw_Data', index=False)
    
    def record_complete_trade_decision(
        self,
        decision: TradeDecision,
        market_context: MarketContext,
        technical_indicators: Dict[TimeFrame, TechnicalIndicators] = None,
        candles_by_timeframe: Dict[TimeFrame, List[CandleData]] = None,
        ai_outputs: Dict[str, Any] = None,
        multi_timeframe_analysis: Dict[str, Any] = None,
        risk_assessment: Dict[str, Any] = None,
        raw_data: Dict[str, Any] = None
    ) -> None:
        """Record a complete trade decision with ALL data that went into it."""
        
        try:
            print(f"📝 [DEBUG] Recording complete trade decision for {decision.recommendation.pair}...")
            from datetime import datetime, timezone
            timestamp = datetime.now(timezone.utc)
            
            # Record trade decision
            print("📝 [DEBUG] Creating trade record...")
            trade_record = self._create_trade_record(decision, timestamp)
            self.trades_data.append(trade_record)
            
            # Record market conditions
            print("📝 [DEBUG] Creating market record...")
            market_record = self._create_market_record(market_context, decision.recommendation.pair, timestamp)
            self.market_conditions_data.append(market_record)
            
            # Record technical indicators for each timeframe
            if technical_indicators:
                print(f"📝 [DEBUG] Recording {len(technical_indicators)} technical indicator sets...")
                for timeframe, indicators in technical_indicators.items():
                    indicators_record = self._create_indicators_record(
                        indicators, decision.recommendation.pair, timeframe, timestamp
                    )
                    self.indicators_data.append(indicators_record)
            
            # Record AI outputs
            if ai_outputs:
                print("📝 [DEBUG] Recording AI outputs...")
                ai_record = self._create_ai_outputs_record(ai_outputs, decision, timestamp)
                self.ai_outputs_data.append(ai_record)
            
            # Record multi-timeframe analysis
            if multi_timeframe_analysis:
                print(f"📝 [DEBUG] Recording {len(multi_timeframe_analysis)} multi-timeframe analyses...")
                for timeframe, analysis in multi_timeframe_analysis.items():
                    mtf_record = self._create_multi_timeframe_record(
                        analysis, decision.recommendation.pair, timeframe, timestamp
                    )
                    self.multi_timeframe_data.append(mtf_record)
            
            # Record risk assessment
            if risk_assessment:
                print("📝 [DEBUG] Recording risk assessment...")
                risk_record = self._create_risk_assessment_record(risk_assessment, decision, timestamp)
                self.risk_assessment_data.append(risk_record)
            
            # Record raw data
            if raw_data:
                print("📝 [DEBUG] Recording raw data...")
                raw_record = self._create_raw_data_record(raw_data, decision, timestamp)
                self.raw_data_data.append(raw_record)
            
            # Write to Excel every 5 records (to avoid memory issues)
            if len(self.trades_data) % 5 == 0:
                print("📝 [DEBUG] Writing batch to Excel...")
                self._write_to_excel()
            
            print(f"✅ [DEBUG] Successfully recorded complete trade decision for {decision.recommendation.pair}")
            self.logger.info(f"Recorded complete trade decision for {decision.recommendation.pair}")
            
        except Exception as e:
            print(f"❌ [DEBUG] Error recording trade: {e}")
            print(f"❌ [DEBUG] Traceback: {traceback.format_exc()}")
            self.logger.error(f"Error recording trade: {e}")
    
    def _create_trade_record(self, decision: TradeDecision, timestamp: datetime) -> Dict[str, Any]:
        """Create a trade decision record."""
        rec = decision.recommendation
        
        return {
            "timestamp": timestamp.isoformat(),
            "pair": rec.pair,
            "signal": rec.signal.value,
            "confidence": float(rec.confidence),
            "entry_price": float(rec.entry_price) if rec.entry_price else None,
            "stop_loss": float(rec.stop_loss) if rec.stop_loss else None,
            "take_profit": float(rec.take_profit) if rec.take_profit else None,
            "risk_reward_ratio": float(rec.risk_reward_ratio),
            "estimated_hold_time": rec.estimated_hold_time.total_seconds() / 60 if rec.estimated_hold_time else None,
            "market_condition": rec.market_condition.value,
            "reasoning": rec.reasoning,
            "approved": decision.approved,
            "position_size": float(decision.position_size) if decision.position_size else None,
            "risk_amount": float(decision.risk_amount) if decision.risk_amount else None,
            "modified_stop_loss": float(decision.modified_stop_loss) if decision.modified_stop_loss else None,
            "modified_take_profit": float(decision.modified_take_profit) if decision.modified_take_profit else None,
            "risk_management_notes": decision.risk_management_notes,
            "final_decision_reason": f"AI Confidence: {rec.confidence:.2f}, Risk Assessment: {decision.risk_management_notes}"
        }
    
    def _create_market_record(self, market_context: MarketContext, pair: str, timestamp: datetime) -> Dict[str, Any]:
        """Create a market conditions record."""
        return {
            "timestamp": timestamp.isoformat(),
            "pair": pair,
            "condition": market_context.condition.value,
            "volatility": float(market_context.volatility) if hasattr(market_context, 'volatility') else None,
            "trend_strength": float(market_context.trend_strength) if hasattr(market_context, 'trend_strength') else None,
            "volume_profile": str(getattr(market_context, 'volume_profile', None)),
            "news_events": str(getattr(market_context, 'news_events', None)),
            "economic_calendar": str(getattr(market_context, 'economic_calendar', None)),
            "market_sentiment": str(getattr(market_context, 'market_sentiment', None)),
            "key_levels": str(market_context.key_levels) if market_context.key_levels else None,
            "support_resistance": str(getattr(market_context, 'support_resistance', None))
        }
    
    def _create_indicators_record(
        self, 
        indicators: TechnicalIndicators,
        pair: str,
        timeframe: TimeFrame,
        timestamp: datetime
    ) -> Dict[str, Any]:
        """Create a technical indicators record."""
        return {
            "timestamp": timestamp.isoformat(),
            "pair": pair,
            "timeframe": timeframe.value,
            "rsi": float(indicators.rsi) if indicators.rsi else None,
            "macd": float(indicators.macd) if indicators.macd else None,
            "macd_signal": float(indicators.macd_signal) if indicators.macd_signal else None,
            "macd_histogram": float(indicators.macd_histogram) if indicators.macd_histogram else None,
            "ema_fast": float(indicators.ema_fast) if indicators.ema_fast else None,
            "ema_slow": float(indicators.ema_slow) if indicators.ema_slow else None,
            "bollinger_upper": float(indicators.bollinger_upper) if indicators.bollinger_upper else None,
            "bollinger_middle": float(indicators.bollinger_middle) if indicators.bollinger_middle else None,
            "bollinger_lower": float(indicators.bollinger_lower) if indicators.bollinger_lower else None,
            "atr": float(indicators.atr) if indicators.atr else None,
            "stoch_k": float(indicators.stoch_k) if indicators.stoch_k else None,
            "stoch_d": float(indicators.stoch_d) if indicators.stoch_d else None,
            "support_level": float(indicators.support_level) if indicators.support_level else None,
            "resistance_level": float(indicators.resistance_level) if indicators.resistance_level else None,
            "fibonacci_levels": "Calculated"  # Placeholder for Fibonacci levels
        }
    
    def _create_ai_outputs_record(
        self, 
        ai_outputs: Dict[str, Any], 
        decision: TradeDecision, 
        timestamp: datetime
    ) -> Dict[str, Any]:
        """Create an AI outputs record."""
        return {
            "timestamp": timestamp.isoformat(),
            "pair": decision.recommendation.pair,
            "ai_prompt_used": ai_outputs.get("prompt", ""),
            "ai_raw_response": ai_outputs.get("raw_response", ""),
            "ai_parsed_data": str(ai_outputs.get("parsed_data", {})),
            "ai_confidence": float(ai_outputs.get("confidence", 0)),
            "ai_signal": ai_outputs.get("signal", ""),
            "ai_reasoning": ai_outputs.get("reasoning", ""),
            "ai_market_condition": ai_outputs.get("market_condition", ""),
            "ai_entry_price": float(ai_outputs.get("entry_price", 0)) if ai_outputs.get("entry_price") else None,
            "ai_stop_loss": float(ai_outputs.get("stop_loss", 0)) if ai_outputs.get("stop_loss") else None,
            "ai_take_profit": float(ai_outputs.get("take_profit", 0)) if ai_outputs.get("take_profit") else None,
            "ai_risk_reward": float(ai_outputs.get("risk_reward_ratio", 0)),
            "ai_hold_time": ai_outputs.get("estimated_hold_time_minutes", 0),
            "ai_model_used": ai_outputs.get("model", "gpt-4"),
            "ai_temperature": ai_outputs.get("temperature", 0.3),
            "ai_max_tokens": ai_outputs.get("max_tokens", 1000)
        }
    
    def _create_multi_timeframe_record(
        self, 
        analysis: Dict[str, Any], 
        pair: str, 
        timeframe: str, 
        timestamp: datetime
    ) -> Dict[str, Any]:
        """Create a multi-timeframe analysis record."""
        return {
            "timestamp": timestamp.isoformat(),
            "pair": pair,
            "timeframe": timeframe,
            "signal_type": analysis.get("signal_type", ""),
            "signal_strength": float(analysis.get("signal_strength", 0)),
            "trend_direction": float(analysis.get("trend_direction", 0)),
            "momentum": float(analysis.get("momentum", 0)),
            "volatility": float(analysis.get("volatility", 0)),
            "technical_score": float(analysis.get("technical_score", 0)),
            "entry_price": float(analysis.get("entry_price", 0)) if analysis.get("entry_price") else None,
            "stop_loss": float(analysis.get("stop_loss", 0)) if analysis.get("stop_loss") else None,
            "take_profit": float(analysis.get("take_profit", 0)) if analysis.get("take_profit") else None,
            "risk_reward_ratio": float(analysis.get("risk_reward_ratio", 0)),
            "confidence": float(analysis.get("confidence", 0)),
            "consensus_weight": float(analysis.get("weight", 0))
        }
    
    def _create_risk_assessment_record(
        self, 
        risk_assessment: Dict[str, Any], 
        decision: TradeDecision, 
        timestamp: datetime
    ) -> Dict[str, Any]:
        """Create a risk assessment record."""
        return {
            "timestamp": timestamp.isoformat(),
            "pair": decision.recommendation.pair,
            "risk_assessment_result": risk_assessment.get("approved", False),
            "risk_reason": risk_assessment.get("reason", ""),
            "position_size_calculated": float(risk_assessment.get("position_size", {}).get("size", 0)) if risk_assessment.get("position_size") else None,
            "risk_amount_calculated": float(risk_assessment.get("position_size", {}).get("risk_amount", 0)) if risk_assessment.get("position_size") else None,
            "daily_loss_check": risk_assessment.get("daily_loss_check", True),
            "correlation_check": risk_assessment.get("correlation_check", True),
            "max_trades_check": risk_assessment.get("max_trades_check", True),
            "volatility_check": risk_assessment.get("volatility_check", True),
            "market_hours_check": risk_assessment.get("market_hours_check", True),
            "risk_notes": risk_assessment.get("notes", "")
        }
    
    def _create_raw_data_record(
        self, 
        raw_data: Dict[str, Any], 
        decision: TradeDecision, 
        timestamp: datetime
    ) -> Dict[str, Any]:
        """Create a raw data record."""
        return {
            "timestamp": timestamp.isoformat(),
            "pair": decision.recommendation.pair,
            "timeframe": raw_data.get("timeframe", ""),
            "candle_count": raw_data.get("candle_count", 0),
            "price_data": str(raw_data.get("price_data", [])),
            "volume_data": str(raw_data.get("volume_data", [])),
            "market_context_raw": str(raw_data.get("market_context_raw", {})),
            "technical_analysis_raw": str(raw_data.get("technical_analysis_raw", {})),
            "news_data": str(raw_data.get("news_data", [])),
            "economic_data": str(raw_data.get("economic_data", [])),
            "sentiment_data": str(raw_data.get("sentiment_data", {}))
        }
    
    def _write_to_excel(self):
        """Write accumulated data to Excel file."""
        try:
            # Convert to DataFrames
            trades_df = pd.DataFrame(self.trades_data)
            market_df = pd.DataFrame(self.market_conditions_data)
            indicators_df = pd.DataFrame(self.indicators_data)
            ai_outputs_df = pd.DataFrame(self.ai_outputs_data)
            multi_timeframe_df = pd.DataFrame(self.multi_timeframe_data)
            risk_assessment_df = pd.DataFrame(self.risk_assessment_data)
            raw_data_df = pd.DataFrame(self.raw_data_data)
            
            # Write to Excel with multiple sheets
            with pd.ExcelWriter(self.excel_file, engine='openpyxl', mode='w') as writer:
                trades_df.to_excel(writer, sheet_name='Trades', index=False)
                market_df.to_excel(writer, sheet_name='Market_Conditions', index=False)
                indicators_df.to_excel(writer, sheet_name='Technical_Indicators', index=False)
                ai_outputs_df.to_excel(writer, sheet_name='AI_Outputs', index=False)
                multi_timeframe_df.to_excel(writer, sheet_name='Multi_Timeframe_Analysis', index=False)
                risk_assessment_df.to_excel(writer, sheet_name='Risk_Assessment', index=False)
                raw_data_df.to_excel(writer, sheet_name='Raw_Data', index=False)
            
            self.logger.info(f"Complete data written to Excel file: {self.excel_file}")
            
        except Exception as e:
            self.logger.error(f"Error writing to Excel: {e}")
    
    async def start(self) -> None:
        """Start the enhanced Excel trade recorder."""
        self.logger.info("Enhanced Excel trade recorder started")
    
    async def stop(self) -> None:
        """Stop the enhanced Excel trade recorder and write final data."""
        self._write_to_excel()
        self.logger.info("Enhanced Excel trade recorder stopped") 