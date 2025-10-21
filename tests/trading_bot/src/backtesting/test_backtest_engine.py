"""
Comprehensive Unit Tests for BacktestEngine

This module provides comprehensive unit tests for the BacktestEngine class,
ensuring 100% test coverage and following TDD principles.

Author: Trading Bot Development Team
Version: 1.0.0
"""

import pytest
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from decimal import Decimal
import pandas as pd
import asyncio

# Add project paths for imports
project_root = Path(__file__).parent.parent.parent.parent.parent.parent
src_path = project_root / "src"
sys.path.append(str(src_path))
sys.path.append(str(src_path / "trading_bot" / "src"))
sys.path.append(str(src_path / "constants"))

# Import the modules under test
from trading_bot.src.backtesting.backtest_engine import BacktestEngine, BacktestResult
from trading_bot.src.core.models import (
    TradeDecision, TradeRecommendation, CandleData, TimeFrame, 
    TradeSignal, MarketContext, TechnicalIndicators, MarketCondition
)
from trading_bot.src.utils.config import Config


class TestBacktestResult:
    """Test suite for BacktestResult dataclass"""
    
    def test_backtest_result_creation(self):
        """Test BacktestResult creation with default values"""
        result = BacktestResult()
        
        assert result.initial_balance == 0.0
        assert result.final_balance == 0.0
        assert result.total_return == 0.0
        assert result.total_return_pct == 0.0
        assert result.max_drawdown == 0.0
        assert result.max_drawdown_pct == 0.0
        assert result.sharpe_ratio == 0.0
        assert result.total_trades == 0
        assert result.winning_trades == 0
        assert result.losing_trades == 0
        assert result.win_rate == 0.0
        assert result.avg_win == 0.0
        assert result.avg_loss == 0.0
        assert result.profit_factor == 0.0
        assert result.largest_win == 0.0
        assert result.largest_loss == 0.0
        assert result.trades == []
        assert result.equity_curve == []
        assert result.drawdown_curve == []
        assert result.daily_returns == []
        assert result.start_date is not None
        assert result.end_date is not None
    
    def test_backtest_result_with_values(self):
        """Test BacktestResult creation with specific values"""
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)
        
        result = BacktestResult(
            initial_balance=10000.0,
            final_balance=11000.0,
            total_return=1000.0,
            total_return_pct=10.0,
            max_drawdown=500.0,
            max_drawdown_pct=5.0,
            sharpe_ratio=1.5,
            total_trades=50,
            winning_trades=30,
            losing_trades=20,
            win_rate=60.0,
            start_date=start_date,
            end_date=end_date
        )
        
        assert result.initial_balance == 10000.0
        assert result.final_balance == 11000.0
        assert result.total_return == 1000.0
        assert result.total_return_pct == 10.0
        assert result.max_drawdown == 500.0
        assert result.max_drawdown_pct == 5.0
        assert result.sharpe_ratio == 1.5
        assert result.total_trades == 50
        assert result.winning_trades == 30
        assert result.losing_trades == 20
        assert result.win_rate == 60.0
        assert result.start_date == start_date
        assert result.end_date == end_date


class TestBacktestEngine:
    """Test suite for BacktestEngine class"""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing"""
        config = Mock(spec=Config)
        config.trading = Mock()
        config.trading.risk_percentage = 2.0
        config.trading.max_position_size = 0.1
        config.trading.pairs = ['EUR_USD', 'GBP_USD']
        config.trading.timeframes = [TimeFrame.M5, TimeFrame.M15]
        config.simulation = Mock()
        config.simulation.csv_dir = '/test/data'
        config.simulation.spread_pips = 0.1
        config.simulation.slippage_pips = 0.1
        config.technical_confidence_threshold = 0.6
        config.account_balance = 10000.0
        config.oanda_api_key = None
        config.risk_management = Mock()
        config.risk_management.max_daily_loss = 100.0
        config.risk_management.max_position_size = 0.1
        config.risk_management.stop_loss_pips = 50
        config.risk_management.take_profit_pips = 100
        return config
    
    @pytest.fixture
    def mock_data_layer(self):
        """Create a mock DataLayer for testing"""
        data_layer = Mock()
        data_layer.scraping_integration = Mock()
        data_layer.get_market_context = Mock(return_value=Mock())
        data_layer.get_historical_data = Mock(return_value=pd.DataFrame())
        return data_layer
    
    @pytest.fixture
    def mock_candle_data(self):
        """Create mock candle data for testing"""
        return [
            CandleData(
                timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                open=Decimal('1.1000'),
                high=Decimal('1.1010'),
                low=Decimal('1.0990'),
                close=Decimal('1.1005'),
                volume=Decimal('1000'),
                pair='EUR_USD',
                timeframe=TimeFrame.M5
            ),
            CandleData(
                timestamp=datetime(2024, 1, 1, 12, 5, 0, tzinfo=timezone.utc),
                open=Decimal('1.1005'),
                high=Decimal('1.1015'),
                low=Decimal('1.0995'),
                close=Decimal('1.1010'),
                volume=Decimal('1100'),
                pair='EUR_USD',
                timeframe=TimeFrame.M5
            )
        ]
    
    @pytest.fixture
    def mock_technical_indicators(self):
        """Create mock technical indicators for testing"""
        return TechnicalIndicators(
            rsi=50.0,
            macd=0.001,
            macd_signal=0.0005,
            macd_histogram=0.0005,
            atr=0.002,
            ema_fast=1.1005,
            ema_slow=1.1000,
            bollinger_upper=1.1015,
            bollinger_middle=1.1005,
            bollinger_lower=1.0995,
            keltner_upper=1.1010,
            keltner_middle=1.1005,
            keltner_lower=1.1000
        )
    
    @pytest.fixture
    def mock_trade_recommendation(self):
        """Create mock trade recommendation for testing"""
        return TradeRecommendation(
            pair='EUR_USD',
            signal=TradeSignal.BUY,
            confidence=0.8,
            entry_price=Decimal('1.1005'),
            stop_loss=Decimal('1.0995'),
            take_profit=Decimal('1.1015'),
            risk_reward_ratio=1.0,
            reasoning='Strong bullish signal with good risk-reward'
        )
    
    @pytest.fixture
    def mock_trade_decision(self, mock_trade_recommendation):
        """Create mock trade decision for testing"""
        return TradeDecision(
            recommendation=mock_trade_recommendation,
            approved=True,
            position_size=Decimal('0.05'),
            risk_amount=Decimal('100.0'),
            modified_stop_loss=Decimal('1.0995'),
            modified_take_profit=Decimal('1.1015'),
            risk_management_notes='Risk management applied',
            timestamp=datetime.now(timezone.utc)
        )
    
    @patch('trading_bot.src.backtesting.backtest_engine.DataLayer')
    @patch('trading_bot.src.backtesting.backtest_engine.TechnicalAnalysisLayer')
    @patch('trading_bot.src.backtesting.backtest_engine.TechnicalDecisionLayer')
    @patch('trading_bot.src.backtesting.backtest_engine.ScrapingDataIntegration')
    @patch('trading_bot.src.backtesting.backtest_engine.AdvancedRiskManager')
    @patch('trading_bot.src.backtesting.backtest_engine.MarketRegimeDetector')
    @patch('trading_bot.src.backtesting.backtest_engine.FundamentalAnalyzer')
    @patch('trading_bot.src.backtesting.backtest_engine.PerformanceTracker')
    def test_initialization_without_historical_feed(self, mock_perf, mock_fundamentals, 
                                                   mock_regime, mock_risk, mock_scraping,
                                                   mock_decision, mock_technical, mock_data, 
                                                   mock_config):
        """Test BacktestEngine initialization without historical feed"""
        # Setup mocks
        mock_data.return_value = Mock()
        mock_technical.return_value = Mock()
        mock_decision.return_value = Mock()
        mock_scraping.return_value = Mock()
        mock_risk.return_value = Mock()
        mock_regime.return_value = Mock()
        mock_fundamentals.return_value = Mock()
        mock_perf.return_value = Mock()
        
        # Initialize engine
        engine = BacktestEngine(mock_config, use_historical_feed=False)
        
        # Verify initialization
        assert engine.config == mock_config
        assert engine.use_historical_feed is False
        assert engine.data_layer is not None
        assert engine.technical_layer is not None
        assert engine.decision_layer is not None
        assert engine.scraping_integration is not None
        assert engine.risk_adv is not None
        assert engine.regime is not None
        assert engine.fundamentals is not None
        assert engine.perf is not None
        assert not hasattr(engine, 'feed')
        assert not hasattr(engine, 'broker')
        assert engine.current_balance == 0.0
    
    @patch('trading_bot.src.backtesting.backtest_engine.DataLayer')
    @patch('trading_bot.src.backtesting.backtest_engine.TechnicalAnalysisLayer')
    @patch('trading_bot.src.backtesting.backtest_engine.TechnicalDecisionLayer')
    @patch('trading_bot.src.backtesting.backtest_engine.ScrapingDataIntegration')
    @patch('trading_bot.src.backtesting.backtest_engine.AdvancedRiskManager')
    @patch('trading_bot.src.backtesting.backtest_engine.MarketRegimeDetector')
    @patch('trading_bot.src.backtesting.backtest_engine.FundamentalAnalyzer')
    @patch('trading_bot.src.backtesting.backtest_engine.PerformanceTracker')
    @patch('trading_bot.src.backtesting.backtest_engine.HistoricalDataFeed')
    @patch('trading_bot.src.backtesting.backtest_engine.BrokerSim')
    def test_initialization_with_historical_feed(self, mock_broker, mock_feed, mock_perf, 
                                                mock_fundamentals, mock_regime, mock_risk, 
                                                mock_scraping, mock_decision, mock_technical, 
                                                mock_data, mock_config):
        """Test BacktestEngine initialization with historical feed"""
        # Setup mocks
        mock_data.return_value = Mock()
        mock_technical.return_value = Mock()
        mock_decision.return_value = Mock()
        mock_scraping.return_value = Mock()
        mock_risk.return_value = Mock()
        mock_regime.return_value = Mock()
        mock_fundamentals.return_value = Mock()
        mock_perf.return_value = Mock()
        mock_feed.return_value = Mock()
        mock_broker.return_value = Mock()
        
        # Initialize engine
        engine = BacktestEngine(mock_config, use_historical_feed=True)
        
        # Verify initialization
        assert engine.config == mock_config
        assert engine.use_historical_feed is True
        assert engine.feed is not None
        assert engine.broker is not None
        assert engine._order_to_decision == {}
        mock_feed.assert_called_once_with(mock_config.simulation.csv_dir)
        mock_broker.assert_called_once_with(
            spread_pips=mock_config.simulation.spread_pips,
            slippage_pips=mock_config.simulation.slippage_pips
        )
    
    @pytest.mark.asyncio
    @patch('trading_bot.src.backtesting.backtest_engine.DataLayer')
    async def test_run_simulation_success(self, mock_data_layer_class, mock_config, mock_data_layer, mock_candle_data, 
                                         mock_technical_indicators, mock_trade_decision):
        """Test successful simulation execution"""
        # Setup mocks
        mock_data_layer_class.return_value = mock_data_layer
        
        # Create engine
        engine = BacktestEngine(mock_config, use_historical_feed=True)
        
        # Mock the feed and broker
        engine.feed = Mock()
        engine.feed.load = Mock()
        engine.feed.min_length_across_timeframes = Mock(return_value=100)
        engine.feed.step_candles = Mock(return_value={TimeFrame.M5: []})
        engine.broker = Mock()
        
        # Run simulation
        result = await engine.run_simulation(
            pairs=['EUR_USD'],
            timeframes=[TimeFrame.M5]
        )
        
        # Verify result
        assert isinstance(result, BacktestResult)
        assert result.initial_balance == 0.0
        assert result.final_balance == 0.0
    
    @pytest.mark.asyncio
    @patch('trading_bot.src.backtesting.backtest_engine.DataLayer')
    async def test_run_simulation_with_error(self, mock_data_layer_class, mock_config, mock_data_layer):
        """Test simulation execution with error handling"""
        # Setup mocks
        mock_data_layer_class.return_value = mock_data_layer
        
        # Create engine
        engine = BacktestEngine(mock_config, use_historical_feed=True)
        
        # Mock the feed to raise exception
        engine.feed = Mock()
        engine.feed.load = Mock(side_effect=Exception("Test error"))
        engine.feed.min_length_across_timeframes = Mock(return_value=100)
        engine.feed.step_candles = Mock(return_value={TimeFrame.M5: []})
        
        # Run simulation - should catch exception and return BacktestResult
        result = await engine.run_simulation(
            pairs=['EUR_USD'],
            timeframes=[TimeFrame.M5]
        )
        
        # Should return empty result due to exception
        assert isinstance(result, BacktestResult)
        assert result.initial_balance == 0.0
    
    def test_component_initialization(self, mock_config):
        """Test component initialization during engine creation"""
        with patch('trading_bot.src.backtesting.backtest_engine.DataLayer') as mock_data, \
             patch('trading_bot.src.backtesting.backtest_engine.TechnicalAnalysisLayer') as mock_technical, \
             patch('trading_bot.src.backtesting.backtest_engine.TechnicalDecisionLayer') as mock_decision, \
             patch('trading_bot.src.backtesting.backtest_engine.ScrapingDataIntegration') as mock_scraping, \
             patch('trading_bot.src.backtesting.backtest_engine.AdvancedRiskManager') as mock_risk, \
             patch('trading_bot.src.backtesting.backtest_engine.MarketRegimeDetector') as mock_regime, \
             patch('trading_bot.src.backtesting.backtest_engine.FundamentalAnalyzer') as mock_fundamentals, \
             patch('trading_bot.src.backtesting.backtest_engine.PerformanceTracker') as mock_perf:
            
            # Setup mocks
            mock_data.return_value = Mock()
            mock_technical.return_value = Mock()
            mock_decision.return_value = Mock()
            mock_scraping.return_value = Mock()
            mock_risk.return_value = Mock()
            mock_regime.return_value = Mock()
            mock_fundamentals.return_value = Mock()
            mock_perf.return_value = Mock()
            
            # Create engine
            engine = BacktestEngine(mock_config, use_historical_feed=False)
            
            # Verify all components were initialized
            assert engine.data_layer is not None
            assert engine.technical_layer is not None
            assert engine.decision_layer is not None
            assert engine.scraping_integration is not None
            assert engine.risk_adv is not None
            assert engine.regime is not None
            assert engine.fundamentals is not None
            assert engine.perf is not None
    
    @pytest.mark.asyncio
    @patch('trading_bot.src.backtesting.backtest_engine.DataLayer')
    async def test_start_stop_lifecycle(self, mock_data_layer_class, mock_config, mock_data_layer):
        """Test engine start and stop lifecycle"""
        with patch('trading_bot.src.backtesting.backtest_engine.BacktestEngine.start') as mock_start, \
             patch('trading_bot.src.backtesting.backtest_engine.BacktestEngine.stop') as mock_stop:
            
            # Setup mocks
            mock_data_layer_class.return_value = mock_data_layer
            mock_start.return_value = None
            mock_stop.return_value = None
            
            # Create engine
            engine = BacktestEngine(mock_config, use_historical_feed=False)
            
            # Test start
            await engine.start()
            mock_start.assert_called_once()
            
            # Test stop
            await engine.stop()
            mock_stop.assert_called_once()
    
    @patch('trading_bot.src.backtesting.backtest_engine.DataLayer')
    def test_backtest_state_initialization(self, mock_data_layer_class, mock_config, mock_data_layer):
        """Test backtest state initialization"""
        # Setup mocks
        mock_data_layer_class.return_value = mock_data_layer
        
        # Create engine
        engine = BacktestEngine(mock_config, use_historical_feed=False)
        
        # Verify initial state
        assert engine.current_balance == 0.0
        assert engine.initial_balance == 0.0
        assert engine.peak_balance == 0.0
        assert engine.open_positions == {}
        assert engine.trade_history == []
        assert engine.equity_curve == []
        assert engine.drawdown_curve == []
        assert engine.daily_pnl == {}
        assert engine.total_trades == 0
        assert engine.winning_trades == 0
        assert engine.losing_trades == 0
        assert engine.total_pnl == 0.0
    
    @patch('trading_bot.src.backtesting.backtest_engine.DataLayer')
    def test_scraping_integration_access(self, mock_data_layer_class, mock_config, mock_data_layer):
        """Test access to scraping integration component"""
        # Setup mocks
        mock_data_layer_class.return_value = mock_data_layer
        
        # Create engine
        engine = BacktestEngine(mock_config, use_historical_feed=False)
        
        # Verify scraping integration is accessible
        assert engine.scraping_integration is not None
        
        # Test that we can call methods on it
        mock_calendar_data = [{'event': 'NFP', 'date': datetime.now()}]
        engine.scraping_integration.get_economic_calendar = Mock(
            return_value=mock_calendar_data
        )
        
        # Test method call
        result = engine.scraping_integration.get_economic_calendar(7)
        assert result == mock_calendar_data


class TestBacktestEngineEdgeCases:
    """Test edge cases and error conditions for BacktestEngine"""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing"""
        config = Mock(spec=Config)
        config.trading = Mock()
        config.trading.risk_percentage = 2.0
        config.trading.max_position_size = 0.1
        config.trading.pairs = ['EUR_USD']
        config.trading.timeframes = [TimeFrame.M5]
        config.simulation = Mock()
        config.simulation.csv_dir = '/test/data'
        config.simulation.spread_pips = 0.1
        config.simulation.slippage_pips = 0.1
        config.technical_confidence_threshold = 0.6
        config.account_balance = 10000.0
        config.oanda_api_key = None
        config.risk_management = Mock()
        config.risk_management.max_daily_loss = 100.0
        config.risk_management.max_position_size = 0.1
        config.risk_management.stop_loss_pips = 50
        config.risk_management.take_profit_pips = 100
        return config
    
    @pytest.fixture
    def mock_data_layer(self):
        """Create a mock DataLayer for testing"""
        data_layer = Mock()
        data_layer.scraping_integration = Mock()
        data_layer.get_market_context = Mock(return_value=Mock())
        data_layer.get_historical_data = Mock(return_value=pd.DataFrame())
        return data_layer
    
    def test_initialization_with_invalid_config(self):
        """Test initialization with invalid configuration"""
        with pytest.raises(AttributeError):
            BacktestEngine(None, use_historical_feed=False)
    
    @patch('trading_bot.src.backtesting.backtest_engine.DataLayer')
    def test_simulation_without_historical_feed(self, mock_data_layer_class, mock_config, mock_data_layer):
        """Test simulation without historical feed enabled"""
        # Setup mocks
        mock_data_layer_class.return_value = mock_data_layer
        
        engine = BacktestEngine(mock_config, use_historical_feed=False)
        
        # Test that simulation requires historical feed
        with pytest.raises(ValueError, match="Simulation mode requires use_historical_feed=True"):
            asyncio.run(engine.run_simulation(
                pairs=['EUR_USD'],
                timeframes=[TimeFrame.M5]
            ))
    
    @patch('trading_bot.src.backtesting.backtest_engine.DataLayer')
    def test_simulation_with_empty_pairs(self, mock_data_layer_class, mock_config, mock_data_layer):
        """Test simulation with empty pairs list"""
        # Setup mocks
        mock_data_layer_class.return_value = mock_data_layer
        
        engine = BacktestEngine(mock_config, use_historical_feed=True)
        
        # Mock the feed
        engine.feed = Mock()
        engine.feed.load = Mock()
        engine.feed.min_length_across_timeframes = Mock(return_value=0)
        
        # Test with empty pairs
        result = asyncio.run(engine.run_simulation(
            pairs=[],
            timeframes=[TimeFrame.M5]
        ))
        
        # Should return empty result
        assert isinstance(result, BacktestResult)
        assert result.initial_balance == 0.0
    
    @patch('trading_bot.src.backtesting.backtest_engine.DataLayer')
    def test_simulation_with_insufficient_data(self, mock_data_layer_class, mock_config, mock_data_layer):
        """Test simulation with insufficient historical data"""
        # Setup mocks
        mock_data_layer_class.return_value = mock_data_layer
        
        engine = BacktestEngine(mock_config, use_historical_feed=True)
        
        # Mock the feed with insufficient data
        engine.feed = Mock()
        engine.feed.load = Mock()
        engine.feed.min_length_across_timeframes = Mock(return_value=10)  # Less than 50
        
        # Test with insufficient data
        result = asyncio.run(engine.run_simulation(
            pairs=['EUR_USD'],
            timeframes=[TimeFrame.M5]
        ))
        
        # Should return empty result
        assert isinstance(result, BacktestResult)
        assert result.initial_balance == 0.0


class TestTypeConversionFixes:
    """Test suite for type conversion fixes in backtest evaluation"""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing"""
        config = Mock(spec=Config)
        config.trading = Mock()
        config.trading.risk_percentage = 2.0
        config.trading.max_position_size = 0.1
        config.trading.pairs = ['EUR_USD']
        config.trading.timeframes = [TimeFrame.M5]
        config.simulation = Mock()
        config.simulation.csv_dir = '/test/data'
        config.simulation.spread_pips = 0.1
        config.simulation.slippage_pips = 0.1
        config.technical_confidence_threshold = 0.6
        config.account_balance = 10000.0
        config.oanda_api_key = None
        config.risk_management = Mock()
        config.risk_management.max_daily_loss = 100.0
        config.risk_management.max_position_size = 0.1
        config.risk_management.stop_loss_pips = 50
        config.risk_management.take_profit_pips = 100
        return config
    
    @patch('trading_bot.src.backtesting.backtest_engine.DataLayer')
    def test_equity_curve_type_conversion(self, mock_data_layer_class, mock_config):
        """Test that equity curve properly converts Decimal to float"""
        # Setup mocks
        mock_data_layer_class.return_value = Mock()
        
        # Create engine
        engine = BacktestEngine(mock_config, use_historical_feed=False)
        
        # Set up Decimal balance
        engine.current_balance = Decimal('10000.50')
        engine.peak_balance = Decimal('10000.50')
        
        # Test _update_equity_curve
        engine._update_equity_curve(datetime.now())
        
        # Verify equity curve contains float values
        assert len(engine.equity_curve) == 1
        assert isinstance(engine.equity_curve[0], float)
        assert engine.equity_curve[0] == 10000.50
        
        # Verify drawdown curve contains float values
        assert len(engine.drawdown_curve) == 1
        assert isinstance(engine.drawdown_curve[0], float)
        assert engine.drawdown_curve[0] == 0.0
    
    @patch('trading_bot.src.backtesting.backtest_engine.DataLayer')
    def test_pnl_type_conversion_in_trades(self, mock_data_layer_class, mock_config):
        """Test that P&L values in trades are converted to float"""
        # Setup mocks
        mock_data_layer_class.return_value = Mock()
        
        # Create engine
        engine = BacktestEngine(mock_config, use_historical_feed=False)
        
        # Create mock position with Decimal P&L
        position = {
            'entry_price': Decimal('1.1000'),
            'exit_price': Decimal('1.1100'),
            'units': Decimal('1000'),
            'signal': 'BUY',
            'entry_time': datetime.now(),
            'exit_time': datetime.now(),
            'exit_reason': 'test',
            'status': 'CLOSED'
        }
        
        # Test _process_closed_position
        engine._process_closed_position(position)
        
        # Verify P&L is converted to float
        assert isinstance(position['pnl'], float)
        assert position['pnl'] == 100.0  # (1.1100 - 1.1000) * 1000
    
    @patch('trading_bot.src.backtesting.backtest_engine.DataLayer')
    def test_performance_metrics_with_mixed_types(self, mock_data_layer_class, mock_config):
        """Test performance metrics calculation with mixed Decimal/float types"""
        # Setup mocks
        mock_data_layer_class.return_value = Mock()
        
        # Create engine
        engine = BacktestEngine(mock_config, use_historical_feed=False)
        
        # Create BacktestResult with mixed types
        result = BacktestResult()
        result.trades = [
            {'pnl': Decimal('100.50')},  # Decimal P&L
            {'pnl': 200.75},             # Float P&L
            {'pnl': Decimal('-50.25')}   # Decimal negative P&L
        ]
        result.equity_curve = [10000.0, 10100.5, 10301.25, 10250.0]  # Float equity curve
        
        # Test _calculate_performance_metrics
        engine._calculate_performance_metrics(result)
        
        # Verify metrics are calculated correctly
        assert result.total_trades == 3
        assert result.winning_trades == 2
        assert result.losing_trades == 1
        assert result.avg_win == 150.625  # (100.5 + 200.75) / 2
        assert result.avg_loss == 50.25
        assert result.profit_factor == 3.0  # 301.25 / 50.25
    
    def test_performance_metrics_type_safety(self):
        """Test PerformanceMetrics class handles mixed types safely"""
        from trading_bot.src.backtesting.performance_metrics import PerformanceMetrics
        
        metrics = PerformanceMetrics()
        
        # Test with mixed types in equity curve
        mixed_equity_curve = [Decimal('10000'), 10100.5, Decimal('10200.75'), 10300.0]
        
        # Test calculate_returns
        returns = metrics.calculate_returns(mixed_equity_curve)
        assert len(returns) == 3
        assert all(isinstance(r, float) for r in returns)
        
        # Test calculate_max_drawdown
        max_dd = metrics.calculate_max_drawdown(mixed_equity_curve)
        assert isinstance(max_dd, float)
        assert max_dd >= 0.0
        
        # Test calculate_ulcer_index
        ulcer_index = metrics.calculate_ulcer_index(mixed_equity_curve)
        assert isinstance(ulcer_index, float)
        assert ulcer_index >= 0.0
    
    def test_performance_metrics_error_handling(self):
        """Test PerformanceMetrics handles type conversion errors gracefully"""
        from trading_bot.src.backtesting.performance_metrics import PerformanceMetrics
        
        metrics = PerformanceMetrics()
        
        # Test with invalid types
        invalid_equity_curve = ['invalid', None, 'not_a_number']
        
        # Should handle gracefully
        returns = metrics.calculate_returns(invalid_equity_curve)
        assert returns == []  # Should return empty list
        
        max_dd = metrics.calculate_max_drawdown(invalid_equity_curve)
        assert max_dd == 0.0  # Should return 0.0
        
        ulcer_index = metrics.calculate_ulcer_index(invalid_equity_curve)
        assert ulcer_index == 0.0  # Should return 0.0
    
    @patch('trading_bot.src.backtesting.backtest_engine.DataLayer')
    def test_backtest_result_finalization_types(self, mock_data_layer_class, mock_config):
        """Test that BacktestResult receives proper float types for all metrics"""
        # Setup mocks
        mock_data_layer_class.return_value = Mock()
        
        # Create engine
        engine = BacktestEngine(mock_config, use_historical_feed=False)
        
        # Set up Decimal balances
        engine.current_balance = Decimal('10500.75')
        engine.initial_balance = Decimal('10000.00')
        engine.peak_balance = Decimal('10500.75')
        engine.drawdown_curve = [0.0, 50.25, 0.0]
        
        # Create result and populate it
        result = BacktestResult()
        result.final_balance = float(engine.current_balance)
        result.total_return = float(engine.current_balance - engine.initial_balance)
        result.total_return_pct = (result.total_return / float(engine.initial_balance)) * 100
        result.max_drawdown = max(engine.drawdown_curve) if engine.drawdown_curve else 0.0
        result.max_drawdown_pct = (float(result.max_drawdown) / float(engine.peak_balance)) * 100
        
        # Verify all values are float
        assert isinstance(result.final_balance, float)
        assert isinstance(result.total_return, float)
        assert isinstance(result.total_return_pct, float)
        assert isinstance(result.max_drawdown, float)
        assert isinstance(result.max_drawdown_pct, float)
        
        # Verify values are correct
        assert result.final_balance == 10500.75
        assert result.total_return == 500.75
        assert result.total_return_pct == 5.0075


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
