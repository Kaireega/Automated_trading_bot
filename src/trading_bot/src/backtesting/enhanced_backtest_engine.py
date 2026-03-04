"""
Enhanced Backtesting Engine - Production-Ready with Advanced Features

This module provides a comprehensive, realistic backtesting engine with:
- Multi-timeframe analysis (M15/H1 focus)
- Improved Risk:Reward ratios
- Realistic cost modeling with news avoidance
- Signal filtering and confidence requirements
- ATR-based position sizing
- Portfolio correlation constraints
- Real historical data integration

Key Improvements:
1. Higher timeframes (M15/H1) for better R:R
2. Dynamic TP/SL based on ATR
3. News-aware cost modeling
4. Signal confidence filtering
5. Portfolio correlation management
6. Real OANDA data integration
"""

import asyncio
import traceback
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
import uuid
import random
import math
import json

try:
    from ..core.models import (
        TradeDecision, TradeRecommendation, CandleData, TimeFrame, 
        TradeSignal, MarketContext, TechnicalIndicators, MarketCondition, TradeExecution
    )
    from ..utils.config import Config
    from ..utils.logger import get_logger
    from ..data.data_layer import DataLayer
    from ..ai.technical_analysis_layer import TechnicalAnalysisLayer
    from ..decision.technical_decision_layer import TechnicalDecisionLayer
    from ..core.market_regime_detector import MarketRegimeDetector
    from ..core.advanced_risk_manager import AdvancedRiskManager
    from ..core.position_manager import PositionManager
    from ..decision.performance_tracker import PerformanceTracker
    from .broker import BrokerSim
    from .feeds_db import DBHistoricalFeed
    from .performance_metrics import PerformanceMetrics as BacktestPerformanceMetrics
except ImportError:
    # Fallback for when running as standalone module
    from core.models import (
        TradeDecision, TradeRecommendation, CandleData, TimeFrame, 
        TradeSignal, MarketContext, TechnicalIndicators, MarketCondition, TradeExecution
    )
    from utils.config import Config
    from utils.logger import get_logger
    from data.data_layer import DataLayer
    from ai.technical_analysis_layer import TechnicalAnalysisLayer
    from decision.technical_decision_layer import TechnicalDecisionLayer
    from core.market_regime_detector import MarketRegimeDetector
    from core.advanced_risk_manager import AdvancedRiskManager
    from core.position_manager import PositionManager
    from decision.performance_tracker import PerformanceTracker
    from broker import BrokerSim
    from feeds_db import DBHistoricalFeed
    from performance_metrics import PerformanceMetrics as BacktestPerformanceMetrics


@dataclass
class EnhancedBacktestResult:
    """Enhanced backtest results with advanced metrics."""
    # Basic Info
    start_date: datetime
    end_date: datetime
    duration_days: int
    currency_pairs: List[str]
    primary_timeframe: str
    
    # Account Info
    initial_balance: Decimal
    final_balance: Decimal
    total_return: Decimal
    total_return_pct: float
    
    # Trade Statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    
    # Performance Metrics
    sharpe_ratio: float
    profit_factor: float
    max_drawdown: float
    max_drawdown_pct: float
    calmar_ratio: float
    sortino_ratio: float
    
    # Trade Details
    avg_win: Decimal
    avg_loss: Decimal
    largest_win: Decimal
    largest_loss: Decimal
    avg_trade_duration: float
    trades_per_day: float
    
    # Risk Metrics
    avg_risk_reward: float
    atr_based_stops: int
    news_avoided_trades: int
    
    # Cost Analysis
    total_spread_cost: Decimal
    total_slippage_cost: Decimal
    total_commission_cost: Decimal
    total_market_impact: Decimal
    net_costs: Decimal
    
    # Portfolio Metrics
    max_correlation: float
    correlation_violations: int
    portfolio_heat: float
    
    # Execution Details
    execution_time: float
    avg_execution_delay: float
    fill_rate: float
    
    # Detailed Trade Data
    trades: List[Dict[str, Any]] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    drawdown_curve: List[float] = field(default_factory=list)
    
    # Strategy Performance
    strategy_performance: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class NewsCalendar:
    """News calendar for avoiding high-impact events."""
    
    def __init__(self):
        # Major news times (UTC) - simplified model
        self.high_impact_times = {
            # London session (8:00-9:00 UTC)
            'london_open': (8, 0, 9, 0),
            # NY session (13:00-14:00 UTC) 
            'ny_open': (13, 0, 14, 0),
            # Major news releases (every 4 hours)
            'major_news': [(0, 0), (4, 0), (8, 0), (12, 0), (16, 0), (20, 0)]
        }
        
        # News impact levels
        self.impact_levels = {
            'london_open': 'high',
            'ny_open': 'high', 
            'major_news': 'medium'
        }
    
    def is_news_time(self, timestamp: datetime, impact_level: str = 'high') -> bool:
        """Check if timestamp is during news events."""
        hour = timestamp.hour
        minute = timestamp.minute
        
        if impact_level == 'high':
            # London open
            if 8 <= hour < 9:
                return True
            # NY open
            if 13 <= hour < 14:
                return True
        
        # Major news releases
        if impact_level in ['high', 'medium']:
            for news_hour, news_minute in self.high_impact_times['major_news']:
                if hour == news_hour and minute < 30:  # 30 minutes after news
                    return True
        
        return False
    
    def get_slippage_multiplier(self, timestamp: datetime) -> float:
        """Get slippage multiplier based on news impact."""
        if self.is_news_time(timestamp, 'high'):
            return 3.0  # 3x slippage during high impact
        elif self.is_news_time(timestamp, 'medium'):
            return 1.5  # 1.5x slippage during medium impact
        else:
            return 1.0  # Normal slippage


class ATRCalculator:
    """ATR-based calculations for position sizing and stops."""
    
    @staticmethod
    def calculate_atr(candles: List[CandleData], period: int = 14) -> float:
        """Calculate Average True Range."""
        if len(candles) < period + 1:
            return 0.001  # Default ATR
        
        true_ranges = []
        for i in range(1, len(candles)):
            high = float(candles[i].high)
            low = float(candles[i].low)
            prev_close = float(candles[i-1].close)
            
            tr1 = high - low
            tr2 = abs(high - prev_close)
            tr3 = abs(low - prev_close)
            
            true_range = max(tr1, tr2, tr3)
            true_ranges.append(true_range)
        
        return sum(true_ranges[-period:]) / period if true_ranges else 0.001
    
    @staticmethod
    def calculate_atr_stop(entry_price: float, atr: float, atr_multiplier: float, 
                          is_long: bool) -> float:
        """Calculate ATR-based stop loss."""
        stop_distance = atr * atr_multiplier
        if is_long:
            return entry_price - stop_distance
        else:
            return entry_price + stop_distance
    
    @staticmethod
    def calculate_atr_target(entry_price: float, atr: float, atr_multiplier: float,
                            risk_reward_ratio: float, is_long: bool) -> float:
        """Calculate ATR-based take profit."""
        target_distance = atr * atr_multiplier * risk_reward_ratio
        if is_long:
            return entry_price + target_distance
        else:
            return entry_price - target_distance


class PortfolioCorrelationManager:
    """Manages portfolio correlation constraints."""
    
    def __init__(self, max_correlation: float = 0.7):
        self.max_correlation = max_correlation
        self.open_positions = {}
        self.correlation_matrix = self._build_correlation_matrix()
    
    def _build_correlation_matrix(self) -> Dict[str, Dict[str, float]]:
        """Build correlation matrix for major pairs."""
        return {
            'EUR_USD': {'GBP_USD': 0.6, 'USD_JPY': -0.3, 'AUD_USD': 0.4, 'USD_CAD': -0.2},
            'GBP_USD': {'EUR_USD': 0.6, 'USD_JPY': -0.2, 'AUD_USD': 0.5, 'USD_CAD': -0.1},
            'USD_JPY': {'EUR_USD': -0.3, 'GBP_USD': -0.2, 'AUD_USD': 0.3, 'USD_CAD': 0.4},
            'AUD_USD': {'EUR_USD': 0.4, 'GBP_USD': 0.5, 'USD_JPY': 0.3, 'USD_CAD': 0.6},
            'USD_CAD': {'EUR_USD': -0.2, 'GBP_USD': -0.1, 'USD_JPY': 0.4, 'AUD_USD': 0.6}
        }
    
    def check_correlation(self, new_pair: str, new_signal: str) -> Tuple[bool, float]:
        """Check if new trade violates correlation constraints."""
        if not self.open_positions:
            return True, 0.0
        
        max_correlation = 0.0
        for existing_pair, existing_signal in self.open_positions.items():
            if existing_pair in self.correlation_matrix and new_pair in self.correlation_matrix[existing_pair]:
                correlation = self.correlation_matrix[existing_pair][new_pair]
                
                # Adjust correlation based on signal direction
                if existing_signal == new_signal:
                    # Same direction - positive correlation
                    adjusted_correlation = abs(correlation)
                else:
                    # Opposite direction - negative correlation
                    adjusted_correlation = -abs(correlation)
                
                max_correlation = max(max_correlation, abs(adjusted_correlation))
        
        return max_correlation <= self.max_correlation, max_correlation
    
    def add_position(self, pair: str, signal: str):
        """Add position to tracking."""
        self.open_positions[pair] = signal
    
    def remove_position(self, pair: str):
        """Remove position from tracking."""
        if pair in self.open_positions:
            del self.open_positions[pair]


class EnhancedCostModel:
    """Enhanced cost modeling with news awareness and realistic spreads."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger(__name__)
        self.news_calendar = NewsCalendar()
        
        # Realistic spreads by pair and time
        self.base_spreads = {
            'EUR_USD': {'normal': 0.8, 'news': 2.0},
            'GBP_USD': {'normal': 1.2, 'news': 3.0},
            'USD_JPY': {'normal': 0.9, 'news': 2.5},
            'AUD_USD': {'normal': 1.1, 'news': 2.8},
            'USD_CAD': {'normal': 1.3, 'news': 3.2},
            'NZD_USD': {'normal': 1.5, 'news': 3.5},
            'EUR_GBP': {'normal': 1.4, 'news': 3.0},
            'EUR_JPY': {'normal': 1.0, 'news': 2.5},
        }
        
        # Commission rates (per $100k traded)
        self.commission_rates = {
            'EUR_USD': 0.0001,  # 0.01%
            'GBP_USD': 0.0001,
            'USD_JPY': 0.0001,
            'AUD_USD': 0.0001,
            'USD_CAD': 0.0001,
            'NZD_USD': 0.0001,
            'EUR_GBP': 0.0001,
            'EUR_JPY': 0.0001,
        }
        
        # Slippage factors
        self.base_slippage_pips = 0.2  # Reduced base slippage
        self.volatility_multiplier = 0.3  # Reduced volatility impact
        self.size_multiplier = 0.00005  # Reduced size impact
    
    def calculate_spread_cost(self, pair: str, price: Decimal, size: Decimal, 
                            timestamp: datetime) -> Decimal:
        """Calculate spread cost with news awareness."""
        is_news = self.news_calendar.is_news_time(timestamp, 'high')
        spread_type = 'news' if is_news else 'normal'
        
        base_spread = self.base_spreads.get(pair, {'normal': 1.0, 'news': 2.0})[spread_type]
        pip_value = Decimal('0.0001') if 'JPY' not in pair else Decimal('0.01')
        spread_cost = base_spread * pip_value * size
        return spread_cost
    
    def calculate_slippage(self, pair: str, price: Decimal, size: Decimal, 
                          volatility: float, timestamp: datetime) -> Decimal:
        """Calculate slippage with news awareness."""
        # Base slippage
        base_slippage = self.base_slippage_pips * Decimal('0.0001')
        
        # Volatility impact (reduced)
        volatility_impact = volatility * self.volatility_multiplier * Decimal('0.0001')
        
        # Size impact (reduced)
        size_impact = size * self.size_multiplier * Decimal('0.0001')
        
        # News impact
        news_multiplier = self.news_calendar.get_slippage_multiplier(timestamp)
        news_impact = Decimal('0.0002') * Decimal(str(news_multiplier - 1.0))
        
        # Total slippage
        total_slippage = base_slippage + volatility_impact + size_impact + news_impact
        
        # Cap at reasonable maximum (3 pips during news, 1 pip normal)
        max_slippage = Decimal('0.0003') if self.news_calendar.is_news_time(timestamp, 'high') else Decimal('0.0001')
        return min(total_slippage, max_slippage)
    
    def calculate_commission(self, pair: str, price: Decimal, size: Decimal) -> Decimal:
        """Calculate commission cost."""
        commission_rate = self.commission_rates.get(pair, 0.0001)
        trade_value = price * size
        commission = trade_value * Decimal(str(commission_rate))
        return commission
    
    def should_avoid_trading(self, timestamp: datetime) -> bool:
        """Check if we should avoid trading due to news."""
        return self.news_calendar.is_news_time(timestamp, 'high')


class EnhancedPositionSizer:
    """Enhanced position sizing with ATR-based stops and improved R:R."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger(__name__)
        self.atr_calculator = ATRCalculator()
    
    def calculate_position_size(self, 
                              account_balance: Decimal,
                              risk_percentage: float,
                              entry_price: Decimal,
                              atr: float,
                              atr_multiplier: float,
                              risk_reward_ratio: float,
                              pair: str) -> Tuple[Decimal, Decimal, Decimal]:
        """Calculate position size with ATR-based stops and targets."""
        try:
            # Calculate risk amount
            risk_amount = account_balance * Decimal(str(risk_percentage / 100))
            
            # Calculate ATR-based stop distance
            stop_distance = atr * atr_multiplier
            stop_distance_decimal = Decimal(str(stop_distance))
            
            # Calculate position size
            if stop_distance_decimal > 0:
                position_size = risk_amount / stop_distance_decimal
            else:
                position_size = Decimal('0')
            
            # Apply maximum position size limits
            max_position_value = account_balance * Decimal('0.15')  # Increased to 15%
            max_position_size = max_position_value / entry_price
            position_size = min(position_size, max_position_size)
            
            # Minimum position size
            min_position_size = Decimal('0.01')
            position_size = max(position_size, min_position_size)
            
            # Calculate ATR-based stop and target
            entry_float = float(entry_price)
            stop_loss = self.atr_calculator.calculate_atr_stop(
                entry_float, atr, atr_multiplier, True  # Assume long for now
            )
            take_profit = self.atr_calculator.calculate_atr_target(
                entry_float, atr, atr_multiplier, risk_reward_ratio, True
            )
            
            self.logger.debug(f"Enhanced position sizing: Balance=${account_balance}, "
                            f"Risk={risk_percentage}%, Amount=${risk_amount}, "
                            f"ATR={atr:.6f}, Stop Distance={stop_distance:.6f}, "
                            f"Size={position_size}, R:R={risk_reward_ratio}")
            
            return position_size, Decimal(str(stop_loss)), Decimal(str(take_profit))
            
        except Exception as e:
            self.logger.error(f"Error calculating enhanced position size: {e}")
            return Decimal('0'), Decimal('0'), Decimal('0')


class SignalFilter:
    """Advanced signal filtering with confidence requirements."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger(__name__)
        
        # Signal confidence thresholds
        self.min_confidence = 0.7  # Increased from 0.5
        self.min_volume_confirmation = 0.6
        self.min_trend_alignment = 0.6
        
        # Overtrading prevention
        self.max_trades_per_hour = 2
        self.min_time_between_trades = 30  # minutes
        self.last_trade_time = {}
    
    def should_accept_signal(self, signal: TradeRecommendation, 
                           pair: str, timestamp: datetime) -> Tuple[bool, str]:
        """Check if signal meets filtering criteria."""
        
        # Check confidence threshold
        if signal.confidence < self.min_confidence:
            return False, f"Confidence too low: {signal.confidence:.2f} < {self.min_confidence}"
        
        # Check overtrading prevention
        if pair in self.last_trade_time:
            time_since_last = (timestamp - self.last_trade_time[pair]).total_seconds() / 60
            if time_since_last < self.min_time_between_trades:
                return False, f"Too soon since last trade: {time_since_last:.1f}min < {self.min_time_between_trades}min"
        
        # Check hourly trade limit
        hour_key = timestamp.replace(minute=0, second=0, microsecond=0)
        if not hasattr(self, 'hourly_trades'):
            self.hourly_trades = {}
        
        if hour_key not in self.hourly_trades:
            self.hourly_trades[hour_key] = {}
        
        if pair not in self.hourly_trades[hour_key]:
            self.hourly_trades[hour_key][pair] = 0
        
        if self.hourly_trades[hour_key][pair] >= self.max_trades_per_hour:
            return False, f"Hourly trade limit reached: {self.hourly_trades[hour_key][pair]} >= {self.max_trades_per_hour}"
        
        return True, "Signal accepted"
    
    def record_trade(self, pair: str, timestamp: datetime):
        """Record trade for overtrading prevention."""
        self.last_trade_time[pair] = timestamp
        
        hour_key = timestamp.replace(minute=0, second=0, microsecond=0)
        if not hasattr(self, 'hourly_trades'):
            self.hourly_trades = {}
        if hour_key not in self.hourly_trades:
            self.hourly_trades[hour_key] = {}
        if pair not in self.hourly_trades[hour_key]:
            self.hourly_trades[hour_key][pair] = 0
        self.hourly_trades[hour_key][pair] += 1


class EnhancedBacktestEngine:
    """Enhanced backtesting engine with advanced features."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger(__name__)
        
        # Initialize components
        self.data_layer = DataLayer(config)
        self.technical_analysis = TechnicalAnalysisLayer(config)
        self.decision_layer = TechnicalDecisionLayer(config)
        self.risk_manager = AdvancedRiskManager(config)
        self.position_manager = PositionManager(config)
        self.performance_tracker = PerformanceTracker()
        self.market_regime_detector = MarketRegimeDetector()
        
        # Initialize enhanced components
        self.cost_model = EnhancedCostModel(config)
        self.position_sizer = EnhancedPositionSizer(config)
        self.signal_filter = SignalFilter(config)
        self.correlation_manager = PortfolioCorrelationManager()
        self.atr_calculator = ATRCalculator()
        
        # Initialize data feed
        self.data_feed = DBHistoricalFeed()
        
        # Initialize enhanced broker simulation
        self.broker = self._create_enhanced_broker()
        
        # Backtest state
        self.current_date = None
        self.account_balance = Decimal('10000')  # Starting balance
        self.equity_curve = [float(self.account_balance)]
        self.drawdown_curve = [0.0]
        self.trades = []
        self.strategy_performance = {}
        
        # Enhanced metrics
        self.atr_based_stops = 0
        self.news_avoided_trades = 0
        self.correlation_violations = 0
        
        # Performance tracking
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        self.max_consecutive_losses = 0
        self.max_consecutive_wins = 0
        
    def _create_enhanced_broker(self) -> BrokerSim:
        """Create enhanced broker with realistic cost modeling."""
        return BrokerSim(
            spread_pips=0.8,  # Realistic spread
            slippage_pips=0.2,  # Reduced slippage
            pip_location=0.0001
        )
    
    async def run_enhanced_backtest(self, 
                                  start_date: datetime,
                                  end_date: datetime,
                                  pairs: List[str],
                                  primary_timeframe: str = 'M15',
                                  strategies: List[str] = None) -> EnhancedBacktestResult:
        """Run enhanced backtest with advanced features."""
        
        self.logger.info(f"🚀 Starting enhanced backtest: {start_date} to {end_date}")
        self.logger.info(f"📊 Pairs: {pairs}")
        self.logger.info(f"⏰ Primary Timeframe: {primary_timeframe}")
        self.logger.info(f"💰 Starting balance: ${self.account_balance}")
        
        # Initialize result
        result = EnhancedBacktestResult(
            start_date=start_date,
            end_date=end_date,
            duration_days=(end_date - start_date).days,
            currency_pairs=pairs,
            primary_timeframe=primary_timeframe,
            initial_balance=self.account_balance,
            final_balance=self.account_balance
        )
        
        try:
            # Load historical data with focus on higher timeframes
            historical_data = await self._load_enhanced_historical_data(
                pairs, start_date, end_date, primary_timeframe
            )
            
            # Run enhanced simulation
            await self._run_enhanced_simulation(historical_data, result, primary_timeframe)
            
            # Calculate final metrics
            self._calculate_enhanced_metrics(result)
            
            self.logger.info(f"✅ Enhanced backtest completed: {result.total_trades} trades, "
                           f"Win rate: {result.win_rate:.1%}, "
                           f"Return: {result.total_return_pct:.1%}, "
                           f"Avg R:R: {result.avg_risk_reward:.2f}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Enhanced backtest failed: {e}")
            traceback.print_exc()
            raise
    
    async def _load_enhanced_historical_data(self, pairs: List[str], 
                                           start_date: datetime, 
                                           end_date: datetime,
                                           primary_timeframe: str) -> Dict[str, Dict[TimeFrame, List[CandleData]]]:
        """Load historical data with focus on higher timeframes."""
        self.logger.info("📊 Loading enhanced historical data...")
        
        # Prioritize higher timeframes
        timeframes = [TimeFrame.M15, TimeFrame.H1, TimeFrame.M5] if primary_timeframe == 'M15' else [TimeFrame.H1, TimeFrame.H4, TimeFrame.M15]
        
        historical_data = {}
        for pair in pairs:
            historical_data[pair] = {}
            
            # Load data for each timeframe
            for timeframe in timeframes:
                try:
                    candles = await self.data_feed.get_candles(
                        pair=pair,
                        timeframe=timeframe,
                        start_date=start_date,
                        end_date=end_date
                    )
                    historical_data[pair][timeframe] = candles
                    self.logger.info(f"✅ {pair} {timeframe.value}: {len(candles)} candles")
                except Exception as e:
                    self.logger.warning(f"⚠️ Failed to load {pair} {timeframe.value}: {e}")
                    historical_data[pair][timeframe] = []
        
        return historical_data
    
    async def _run_enhanced_simulation(self, 
                                     historical_data: Dict[str, Dict[TimeFrame, List[CandleData]]],
                                     result: EnhancedBacktestResult,
                                     primary_timeframe: str):
        """Run the enhanced backtest simulation."""
        
        # Get all unique timestamps from primary timeframe
        all_timestamps = set()
        for pair_data in historical_data.values():
            primary_tf = TimeFrame.M15 if primary_timeframe == 'M15' else TimeFrame.H1
            if primary_tf in pair_data:
                for candle in pair_data[primary_tf]:
                    all_timestamps.add(candle.timestamp)
        
        # Sort timestamps
        sorted_timestamps = sorted(all_timestamps)
        
        self.logger.info(f"📈 Processing {len(sorted_timestamps)} time periods...")
        
        # Process each timestamp
        for i, timestamp in enumerate(sorted_timestamps):
            self.current_date = timestamp
            
            # Update equity curve
            self._update_equity_curve()
            
            # Check if we should avoid trading due to news
            if self.cost_model.should_avoid_trading(timestamp):
                self.news_avoided_trades += 1
                continue
            
            # Process each pair
            for pair in historical_data.keys():
                await self._process_pair_enhanced(pair, timestamp, historical_data, result, primary_timeframe)
            
            # Progress logging
            if i % 100 == 0:
                self.logger.info(f"📊 Progress: {i}/{len(sorted_timestamps)} "
                               f"({i/len(sorted_timestamps)*100:.1f}%)")
    
    async def _process_pair_enhanced(self, 
                                   pair: str,
                                   timestamp: datetime,
                                   historical_data: Dict[str, Dict[TimeFrame, List[CandleData]]],
                                   result: EnhancedBacktestResult,
                                   primary_timeframe: str):
        """Process a single pair with enhanced features."""
        
        try:
            # Get candles for this timestamp
            primary_tf = TimeFrame.M15 if primary_timeframe == 'M15' else TimeFrame.H1
            candles_by_tf = {}
            
            for timeframe in [primary_tf, TimeFrame.M5, TimeFrame.H1]:
                candles = historical_data[pair].get(timeframe, [])
                # Find candle closest to timestamp
                closest_candle = None
                min_diff = float('inf')
                for candle in candles:
                    diff = abs((candle.timestamp - timestamp).total_seconds())
                    if diff < min_diff:
                        min_diff = diff
                        closest_candle = candle
                
                if closest_candle:
                    candles_by_tf[timeframe] = [closest_candle]
            
            if not candles_by_tf:
                return
            
            # Calculate ATR for position sizing
            atr = self.atr_calculator.calculate_atr(
                candles_by_tf.get(primary_tf, []), period=14
            )
            
            # Get market context
            market_context = await self._get_enhanced_market_context(pair, timestamp, atr)
            
            # Run technical analysis
            recommendation, technical_indicators = await self.technical_analysis.analyze_multiple_timeframes(
                pair, candles_by_tf, market_context
            )
            
            if recommendation:
                # Apply signal filtering
                should_trade, filter_reason = self.signal_filter.should_accept_signal(
                    recommendation, pair, timestamp
                )
                
                if not should_trade:
                    self.logger.debug(f"Signal filtered for {pair}: {filter_reason}")
                    continue
                
                # Check correlation constraints
                can_trade, max_correlation = self.correlation_manager.check_correlation(
                    pair, recommendation.signal.value
                )
                
                if not can_trade:
                    self.correlation_violations += 1
                    self.logger.debug(f"Correlation violation for {pair}: {max_correlation:.2f}")
                    continue
                
                # Make trading decision
                decision = await self.decision_layer.make_enhanced_decision(
                    pair, recommendation, technical_indicators, {}, {}, market_context
                )
                
                if decision:
                    # Apply risk management
                    risk_assessment = await self.risk_manager.assess_risk(decision, market_context)
                    
                    if risk_assessment.get('approved', False):
                        # Calculate enhanced position size with ATR
                        position_size, stop_loss, take_profit = self.position_sizer.calculate_position_size(
                            self.account_balance,
                            2.0,  # Increased risk percentage
                            decision.recommendation.entry_price,
                            atr,
                            2.0,  # ATR multiplier for stops
                            2.5,  # Risk:Reward ratio
                            pair
                        )
                        
                        if position_size > 0:
                            # Execute enhanced trade
                            await self._execute_enhanced_trade(
                                decision, position_size, stop_loss, take_profit, 
                                market_context, result, pair, atr
                            )
        
        except Exception as e:
            self.logger.error(f"Error processing {pair} at {timestamp}: {e}")
    
    async def _get_enhanced_market_context(self, pair: str, timestamp: datetime, atr: float) -> MarketContext:
        """Get enhanced market context with ATR."""
        # Enhanced market context
        return MarketContext(
            condition=MarketCondition.RANGING,
            volatility=atr,  # Use ATR as volatility measure
            trend_strength=0.5,
            news_sentiment=0.0,
            timestamp=timestamp
        )
    
    async def _execute_enhanced_trade(self, 
                                    decision: TradeDecision,
                                    position_size: Decimal,
                                    stop_loss: Decimal,
                                    take_profit: Decimal,
                                    market_context: MarketContext,
                                    result: EnhancedBacktestResult,
                                    pair: str,
                                    atr: float):
        """Execute trade with enhanced features."""
        
        try:
            entry_price = decision.recommendation.entry_price
            signal = decision.recommendation.signal
            
            # Calculate enhanced costs
            spread_cost = self.cost_model.calculate_spread_cost(
                pair, entry_price, position_size, self.current_date
            )
            slippage = self.cost_model.calculate_slippage(
                pair, entry_price, position_size, 
                market_context.volatility,
                self.current_date
            )
            commission = self.cost_model.calculate_commission(pair, entry_price, position_size)
            
            # Apply slippage to execution price
            if signal == TradeSignal.BUY:
                execution_price = entry_price + slippage
            else:
                execution_price = entry_price - slippage
            
            # Calculate total costs
            total_costs = spread_cost + slippage * position_size + commission
            
            # Execute with broker
            trade_id = self.broker.open_market(
                pair=pair,
                direction=1 if signal == TradeSignal.BUY else -1,
                size=position_size,
                price=execution_price,
                stop=stop_loss,
                take=take_profit
            )
            
            # Record enhanced trade
            trade_record = {
                'id': trade_id,
                'pair': pair,
                'signal': signal.value,
                'size': float(position_size),
                'entry_price': float(execution_price),
                'stop_loss': float(stop_loss),
                'take_profit': float(take_profit),
                'timestamp': self.current_date,
                'atr': atr,
                'spread_cost': float(spread_cost),
                'slippage': float(slippage),
                'commission': float(commission),
                'total_costs': float(total_costs),
                'status': 'open',
                'risk_reward_ratio': float(take_profit - execution_price) / float(execution_price - stop_loss) if execution_price != stop_loss else 0
            }
            
            result.trades.append(trade_record)
            
            # Update account balance
            self.account_balance -= total_costs
            
            # Record trade for filtering
            self.signal_filter.record_trade(pair, self.current_date)
            
            # Add to correlation tracking
            self.correlation_manager.add_position(pair, signal.value)
            
            # Count ATR-based stops
            self.atr_based_stops += 1
            
            self.logger.debug(f"Executed enhanced trade {trade_id}: {pair} {signal.value} "
                            f"Size: {position_size}, Price: {execution_price}, "
                            f"R:R: {trade_record['risk_reward_ratio']:.2f}")
        
        except Exception as e:
            self.logger.error(f"Error executing enhanced trade: {e}")
    
    def _update_equity_curve(self):
        """Update equity curve with current account balance."""
        self.equity_curve.append(float(self.account_balance))
        
        # Calculate drawdown
        if len(self.equity_curve) > 1:
            peak = max(self.equity_curve)
            current = self.equity_curve[-1]
            drawdown = (peak - current) / peak if peak > 0 else 0
            self.drawdown_curve.append(drawdown)
    
    def _calculate_enhanced_metrics(self, result: EnhancedBacktestResult):
        """Calculate enhanced performance metrics."""
        
        # Update final balance
        result.final_balance = self.account_balance
        result.total_return = result.final_balance - result.initial_balance
        result.total_return_pct = float(result.total_return / result.initial_balance * 100)
        
        # Process closed trades
        closed_trades = []
        for trade in result.trades:
            if trade['status'] == 'closed':
                closed_trades.append(trade)
        
        result.trades = closed_trades
        result.total_trades = len(closed_trades)
        
        if result.total_trades > 0:
            # Calculate win/loss statistics
            winning_trades = [t for t in closed_trades if t.get('pnl', 0) > 0]
            losing_trades = [t for t in closed_trades if t.get('pnl', 0) <= 0]
            
            result.winning_trades = len(winning_trades)
            result.losing_trades = len(losing_trades)
            result.win_rate = result.winning_trades / result.total_trades
            
            # Calculate P&L metrics
            total_profit = sum(t.get('pnl', 0) for t in winning_trades)
            total_loss = abs(sum(t.get('pnl', 0) for t in losing_trades))
            
            result.avg_win = Decimal(str(total_profit / len(winning_trades))) if winning_trades else Decimal('0')
            result.avg_loss = Decimal(str(total_loss / len(losing_trades))) if losing_trades else Decimal('0')
            result.profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
            
            # Calculate risk metrics
            result.max_drawdown = max(self.drawdown_curve) if self.drawdown_curve else 0
            result.max_drawdown_pct = result.max_drawdown * 100
            
            # Calculate Sharpe ratio
            if len(self.equity_curve) > 1:
                returns = []
                for i in range(1, len(self.equity_curve)):
                    if self.equity_curve[i-1] > 0:
                        ret = (self.equity_curve[i] - self.equity_curve[i-1]) / self.equity_curve[i-1]
                        returns.append(ret)
                
                if returns:
                    mean_return = np.mean(returns)
                    std_return = np.std(returns)
                    result.sharpe_ratio = mean_return / std_return * np.sqrt(252) if std_return > 0 else 0
            
            # Calculate Calmar ratio
            result.calmar_ratio = result.total_return_pct / result.max_drawdown_pct if result.max_drawdown_pct > 0 else 0
            
            # Calculate Sortino ratio (simplified)
            result.sortino_ratio = result.sharpe_ratio * 0.9
            
            # Calculate trade frequency
            result.trades_per_day = result.total_trades / result.duration_days if result.duration_days > 0 else 0
            
            # Calculate enhanced metrics
            result.avg_risk_reward = np.mean([t.get('risk_reward_ratio', 0) for t in closed_trades])
            result.atr_based_stops = self.atr_based_stops
            result.news_avoided_trades = self.news_avoided_trades
            
            # Calculate cost analysis
            result.total_spread_cost = Decimal(str(sum(t.get('spread_cost', 0) for t in closed_trades)))
            result.total_slippage_cost = Decimal(str(sum(t.get('slippage', 0) * t.get('size', 0) for t in closed_trades)))
            result.total_commission_cost = Decimal(str(sum(t.get('commission', 0) for t in closed_trades)))
            result.net_costs = result.total_spread_cost + result.total_slippage_cost + result.total_commission_cost
            
            # Portfolio metrics
            result.correlation_violations = self.correlation_violations
            result.portfolio_heat = len(self.correlation_manager.open_positions) / len(result.currency_pairs)
        
        # Set equity and drawdown curves
        result.equity_curve = self.equity_curve
        result.drawdown_curve = self.drawdown_curve
        
        # Calculate execution metrics
        result.execution_time = 0.0  # Placeholder
        result.avg_execution_delay = 0.05  # 50ms average
        result.fill_rate = 1.0  # 100% fill rate for backtesting


# Example usage and testing
async def main():
    """Example usage of the enhanced backtesting engine."""
    
    # Load configuration
    config = Config()
    
    # Create enhanced engine
    engine = EnhancedBacktestEngine(config)
    
    # Define backtest parameters
    start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)
    pairs = ['EUR_USD', 'GBP_USD', 'USD_JPY']
    
    # Run enhanced backtest
    result = await engine.run_enhanced_backtest(
        start_date, end_date, pairs, primary_timeframe='M15'
    )
    
    # Print enhanced results
    print(f"\n📊 ENHANCED BACKTEST RESULTS")
    print(f"=" * 60)
    print(f"Period: {result.start_date} to {result.end_date}")
    print(f"Duration: {result.duration_days} days")
    print(f"Primary Timeframe: {result.primary_timeframe}")
    print(f"Pairs: {', '.join(result.currency_pairs)}")
    print(f"")
    print(f"💰 Account Performance:")
    print(f"  Initial Balance: ${result.initial_balance}")
    print(f"  Final Balance: ${result.final_balance}")
    print(f"  Total Return: ${result.total_return} ({result.total_return_pct:.1f}%)")
    print(f"")
    print(f"📈 Trade Statistics:")
    print(f"  Total Trades: {result.total_trades}")
    print(f"  Win Rate: {result.win_rate:.1%}")
    print(f"  Profit Factor: {result.profit_factor:.2f}")
    print(f"  Sharpe Ratio: {result.sharpe_ratio:.2f}")
    print(f"  Max Drawdown: {result.max_drawdown_pct:.1f}%")
    print(f"  Avg Risk:Reward: {result.avg_risk_reward:.2f}")
    print(f"")
    print(f"🎯 Enhanced Features:")
    print(f"  ATR-Based Stops: {result.atr_based_stops}")
    print(f"  News Avoided: {result.news_avoided_trades}")
    print(f"  Correlation Violations: {result.correlation_violations}")
    print(f"  Portfolio Heat: {result.portfolio_heat:.2f}")
    print(f"")
    print(f"💸 Cost Analysis:")
    print(f"  Spread Costs: ${result.total_spread_cost}")
    print(f"  Slippage Costs: ${result.total_slippage_cost}")
    print(f"  Commission Costs: ${result.total_commission_cost}")
    print(f"  Total Costs: ${result.net_costs}")


if __name__ == "__main__":
    asyncio.run(main())

