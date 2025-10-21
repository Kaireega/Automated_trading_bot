"""
Edge case tests for the trading bot system.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import asyncio

import sys
from pathlib import Path

# Add the src directory to the path
sys.path.append(str(Path(__file__).parent.parent.parent / "src" / "trading_bot" / "src"))
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from core.models import CandleData, TimeFrame, MarketContext, MarketCondition, TradeSignal


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration for edge case testing."""
        config = Mock()
        config.trading_pairs = ['EUR_USD']
        config.timeframes = [TimeFrame.M5]
        config.technical_confidence_threshold = 0.6
        config.risk_management.max_daily_loss = 5.0
        config.risk_management.max_position_size = 10.0
        config.risk_management.correlation_limit = 0.7
        config.risk_management.max_open_trades = 3
        config.notifications.telegram_enabled = False
        config.notifications.email_enabled = False
        config.oanda_api_key = "test_api_key"
        config.oanda_account_id = "test_account_id"
        config.oanda_url = "https://api-fxpractice.oanda.com/v3"
        return config
    
    @pytest.mark.edge
    def test_empty_candle_data(self, mock_config):
        """Test handling of empty candle data."""
        with patch('data.data_layer.OandaApi'), \
             patch('data.data_layer.defs'), \
             patch('data.data_layer.OANDA_AVAILABLE', True):
            
            from data.data_layer import DataLayer
            
            data_layer = DataLayer(mock_config)
            
            # Test with empty candle list
            empty_candles = []
            volatility = data_layer._calculate_volatility(empty_candles)
            trend_strength = data_layer._calculate_trend_strength(empty_candles)
            
            assert volatility == 0.0
            assert trend_strength == 0.0
    
    @pytest.mark.edge
    def test_single_candle_data(self, mock_config):
        """Test handling of single candle data."""
        with patch('data.data_layer.OandaApi'), \
             patch('data.data_layer.defs'), \
             patch('data.data_layer.OANDA_AVAILABLE', True):
            
            from data.data_layer import DataLayer
            
            data_layer = DataLayer(mock_config)
            
            # Test with single candle
            single_candle = [CandleData(
                timestamp=datetime.now(timezone.utc),
                open=Decimal('1.2000'),
                high=Decimal('1.2010'),
                low=Decimal('1.1990'),
                close=Decimal('1.2005'),
                pair="EUR_USD"
            )]
            
            volatility = data_layer._calculate_volatility(single_candle)
            trend_strength = data_layer._calculate_trend_strength(single_candle)
            
            assert volatility == 0.0  # Cannot calculate volatility with single candle
            assert trend_strength == 0.0  # Cannot calculate trend with single candle
    
    @pytest.mark.edge
    def test_invalid_candle_data(self, mock_config):
        """Test handling of invalid candle data."""
        with patch('data.data_layer.OandaApi'), \
             patch('data.data_layer.defs'), \
             patch('data.data_layer.OANDA_AVAILABLE', True):
            
            from data.data_layer import DataLayer
            
            data_layer = DataLayer(mock_config)
            
            # Test with invalid candle (high < low)
            invalid_candle = CandleData(
                timestamp=datetime.now(timezone.utc),
                open=Decimal('1.2000'),
                high=Decimal('1.1990'),  # High < Low
                low=Decimal('1.2010'),
                close=Decimal('1.2005'),
                pair="EUR_USD"
            )
            
            is_valid = data_layer._validate_candle_data(invalid_candle)
            assert is_valid is False
    
    @pytest.mark.edge
    def test_extreme_price_values(self, mock_config):
        """Test handling of extreme price values."""
        with patch('data.data_layer.OandaApi'), \
             patch('data.data_layer.defs'), \
             patch('data.data_layer.OANDA_AVAILABLE', True):
            
            from data.data_layer import DataLayer
            
            data_layer = DataLayer(mock_config)
            
            # Test with extreme price values
            extreme_candles = [
                CandleData(
                    timestamp=datetime.now(timezone.utc),
                    open=Decimal('0.0001'),  # Very small price
                    high=Decimal('0.0002'),
                    low=Decimal('0.0001'),
                    close=Decimal('0.0002'),
                    pair="EUR_USD"
                ),
                CandleData(
                    timestamp=datetime.now(timezone.utc) + timedelta(minutes=5),
                    open=Decimal('999999.9999'),  # Very large price
                    high=Decimal('999999.9999'),
                    low=Decimal('999999.9999'),
                    close=Decimal('999999.9999'),
                    pair="EUR_USD"
                )
            ]
            
            volatility = data_layer._calculate_volatility(extreme_candles)
            trend_strength = data_layer._calculate_trend_strength(extreme_candles)
            
            # Should handle extreme values without crashing
            assert isinstance(volatility, float)
            assert isinstance(trend_strength, float)
            assert volatility >= 0.0
            assert 0.0 <= trend_strength <= 1.0
    
    @pytest.mark.edge
    def test_duplicate_timestamps(self, mock_config):
        """Test handling of duplicate timestamps."""
        with patch('data.data_layer.OandaApi'), \
             patch('data.data_layer.defs'), \
             patch('data.data_layer.OANDA_AVAILABLE', True):
            
            from data.data_layer import DataLayer
            
            data_layer = DataLayer(mock_config)
            
            base_time = datetime.now(timezone.utc)
            
            # Create candles with duplicate timestamps
            duplicate_candles = [
                CandleData(
                    timestamp=base_time,
                    open=Decimal('1.2000'),
                    high=Decimal('1.2010'),
                    low=Decimal('1.1990'),
                    close=Decimal('1.2005'),
                    pair="EUR_USD"
                ),
                CandleData(
                    timestamp=base_time,  # Same timestamp
                    open=Decimal('1.2001'),
                    high=Decimal('1.2011'),
                    low=Decimal('1.1991'),
                    close=Decimal('1.2006'),
                    pair="EUR_USD"
                ),
                CandleData(
                    timestamp=base_time + timedelta(minutes=5),
                    open=Decimal('1.2002'),
                    high=Decimal('1.2012'),
                    low=Decimal('1.1992'),
                    close=Decimal('1.2007'),
                    pair="EUR_USD"
                )
            ]
            
            filtered_candles = data_layer._filter_duplicate_candles(duplicate_candles)
            
            # Should remove duplicate and keep only 2 candles
            assert len(filtered_candles) == 2
            assert filtered_candles[0].timestamp == base_time
            assert filtered_candles[1].timestamp == base_time + timedelta(minutes=5)
    
    @pytest.mark.edge
    def test_missing_technical_indicators(self, mock_config):
        """Test handling of missing technical indicators."""
        with patch('ai.technical_analysis_layer.TechnicalAnalyzer'), \
             patch('ai.technical_analysis_layer.MultiTimeframeAnalyzer'):
            
            from ai.technical_analysis_layer import TechnicalAnalysisLayer
            
            technical_layer = TechnicalAnalysisLayer(mock_config)
            
            # Test with None indicators
            indicators = Mock()
            indicators.rsi = None
            indicators.macd = None
            indicators.ema_fast = None
            indicators.ema_slow = None
            indicators.atr = None
            
            market_context = Mock()
            
            result = technical_layer._analyze_technical_signals(indicators, market_context)
            
            # Should handle None indicators gracefully
            assert result['rsi_signal'] is None
            assert result['macd_signal'] is None
            assert result['ema_signal'] is None
            assert result['overall_signal'] is None
            assert result['has_signal'] is False
    
    @pytest.mark.edge
    def test_extreme_technical_indicator_values(self, mock_config):
        """Test handling of extreme technical indicator values."""
        with patch('ai.technical_analysis_layer.TechnicalAnalyzer'), \
             patch('ai.technical_analysis_layer.MultiTimeframeAnalyzer'):
            
            from ai.technical_analysis_layer import TechnicalAnalysisLayer
            
            technical_layer = TechnicalAnalysisLayer(mock_config)
            
            # Test with extreme indicator values
            indicators = Mock()
            indicators.rsi = 150.0  # Invalid RSI value
            indicators.macd = 999999.0  # Extreme MACD value
            indicators.ema_fast = 0.0001  # Very small EMA
            indicators.ema_slow = 999999.0  # Very large EMA
            indicators.atr = 0.0  # Zero ATR
            indicators.bollinger_upper = 1.2010
            indicators.bollinger_middle = 1.2000
            indicators.bollinger_lower = 1.1990
            
            market_context = Mock()
            
            result = technical_layer._analyze_technical_signals(indicators, market_context)
            
            # Should handle extreme values without crashing
            assert 'rsi_signal' in result
            assert 'macd_signal' in result
            assert 'ema_signal' in result
            assert 'overall_signal' in result
            assert 'has_signal' in result
    
    @pytest.mark.edge
    def test_risk_manager_daily_limits(self, mock_config):
        """Test risk manager daily limit edge cases."""
        with patch('decision.risk_manager.OandaApi'), \
             patch('decision.risk_manager.instrumentCollection'), \
             patch('decision.risk_manager.ic'):
            
            from decision.risk_manager import RiskManager
            from core.models import TradeRecommendation, TradeSignal
            
            risk_manager = RiskManager(mock_config)
            
            # Test with daily loss at exactly the limit
            risk_manager._daily_loss = Decimal('5.0')  # Exactly at limit
            
            recommendation = TradeRecommendation(
                pair="EUR_USD",
                signal=TradeSignal.BUY,
                entry_price=Decimal('1.2000'),
                stop_loss=Decimal('1.1950'),
                take_profit=Decimal('1.2100'),
                confidence=0.75
            )
            
            market_context = Mock()
            current_price = 1.2000
            
            # Should still allow trades at exactly the limit
            result = risk_manager._check_daily_limits(recommendation, current_price, market_context)
            assert result['approved'] is True
    
    @pytest.mark.edge
    def test_risk_manager_zero_position_size(self, mock_config):
        """Test risk manager with zero position size."""
        with patch('decision.risk_manager.OandaApi'), \
             patch('decision.risk_manager.instrumentCollection'), \
             patch('decision.risk_manager.ic'):
            
            from decision.risk_manager import RiskManager
            from core.models import TradeRecommendation, TradeSignal
            
            risk_manager = RiskManager(mock_config)
            
            # Test with recommendation that would result in zero position size
            recommendation = TradeRecommendation(
                pair="EUR_USD",
                signal=TradeSignal.BUY,
                entry_price=Decimal('1.2000'),
                stop_loss=Decimal('1.2000'),  # Same as entry (no risk)
                take_profit=Decimal('1.2100'),
                confidence=0.75
            )
            
            risk_assessment = {'approved': True, 'reason': 'OK', 'score': 0.8}
            
            result = risk_manager.calculate_position_size(recommendation, risk_assessment)
            
            # Should return zero position size
            assert result['size'] == Decimal('0')
            assert result['risk_amount'] == Decimal('0')
    
    @pytest.mark.edge
    def test_notification_layer_connection_failure(self, mock_config):
        """Test notification layer connection failure handling."""
        with patch('notifications.notification_layer.NotificationLayer') as mock_notifications:
            
            from notifications.notification_layer import NotificationLayer
            
            # Mock connection failure
            mock_notifications.return_value.start = AsyncMock(side_effect=Exception("Connection failed"))
            
            notification_layer = NotificationLayer(mock_config)
            
            # Should handle connection failure gracefully
            with pytest.raises(Exception, match="Connection failed"):
                await notification_layer.start()
    
    @pytest.mark.edge
    def test_notification_layer_send_failure(self, mock_config):
        """Test notification layer send failure handling."""
        with patch('notifications.notification_layer.NotificationLayer') as mock_notifications:
            
            from notifications.notification_layer import NotificationLayer
            from core.models import TradeRecommendation, TradeSignal
            
            # Mock send failure
            mock_notifications.return_value.send_notification = AsyncMock(
                side_effect=Exception("Send failed")
            )
            
            notification_layer = NotificationLayer(mock_config)
            
            # Should handle send failure gracefully
            with pytest.raises(Exception, match="Send failed"):
                await notification_layer.send_notification("Test message")
    
    @pytest.mark.edge
    def test_concurrent_data_access(self, mock_config):
        """Test concurrent data access edge cases."""
        with patch('data.data_layer.OandaApi'), \
             patch('data.data_layer.defs'), \
             patch('data.data_layer.OANDA_AVAILABLE', True):
            
            from data.data_layer import DataLayer
            
            data_layer = DataLayer(mock_config)
            
            # Test concurrent access to the same data
            async def concurrent_access():
                # Simulate concurrent access
                tasks = []
                for _ in range(10):
                    task = asyncio.create_task(data_layer.get_all_data())
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks)
                return results
            
            # Should handle concurrent access without issues
            results = asyncio.run(concurrent_access())
            assert len(results) == 10
            assert all(isinstance(result, dict) for result in results)
    
    @pytest.mark.edge
    def test_memory_usage_with_large_datasets(self, mock_config):
        """Test memory usage with large datasets."""
        with patch('data.data_layer.OandaApi'), \
             patch('data.data_layer.defs'), \
             patch('data.data_layer.OANDA_AVAILABLE', True):
            
            from data.data_layer import DataLayer
            
            data_layer = DataLayer(mock_config)
            
            # Create large dataset
            large_candles = []
            base_time = datetime.now(timezone.utc)
            base_price = Decimal('1.2000')
            
            for i in range(10000):  # Large dataset
                candle = CandleData(
                    timestamp=base_time - timedelta(minutes=i*5),
                    open=base_price + Decimal(str(i * 0.0001)),
                    high=base_price + Decimal(str(i * 0.0001 + 0.0005)),
                    low=base_price + Decimal(str(i * 0.0001 - 0.0005)),
                    close=base_price + Decimal(str(i * 0.0001 + 0.0002)),
                    pair="EUR_USD"
                )
                large_candles.append(candle)
            
            # Test processing large dataset
            volatility = data_layer._calculate_volatility(large_candles)
            trend_strength = data_layer._calculate_trend_strength(large_candles)
            
            # Should handle large datasets without memory issues
            assert isinstance(volatility, float)
            assert isinstance(trend_strength, float)
            assert volatility >= 0.0
            assert 0.0 <= trend_strength <= 1.0
    
    @pytest.mark.edge
    def test_timezone_edge_cases(self, mock_config):
        """Test timezone edge cases."""
        with patch('data.data_layer.OandaApi'), \
             patch('data.data_layer.defs'), \
             patch('data.data_layer.OANDA_AVAILABLE', True):
            
            from data.data_layer import DataLayer
            
            data_layer = DataLayer(mock_config)
            
            # Test with different timezones
            utc_time = datetime.now(timezone.utc)
            local_time = datetime.now()
            
            candles = [
                CandleData(
                    timestamp=utc_time,
                    open=Decimal('1.2000'),
                    high=Decimal('1.2010'),
                    low=Decimal('1.1990'),
                    close=Decimal('1.2005'),
                    pair="EUR_USD"
                ),
                CandleData(
                    timestamp=local_time,
                    open=Decimal('1.2001'),
                    high=Decimal('1.2011'),
                    low=Decimal('1.1991'),
                    close=Decimal('1.2006'),
                    pair="EUR_USD"
                )
            ]
            
            # Should handle different timezones
            volatility = data_layer._calculate_volatility(candles)
            trend_strength = data_layer._calculate_trend_strength(candles)
            
            assert isinstance(volatility, float)
            assert isinstance(trend_strength, float)

