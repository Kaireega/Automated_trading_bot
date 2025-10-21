"""
Integration tests for the complete trading bot system.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import sys
from pathlib import Path

# Add the src directory to the path
sys.path.append(str(Path(__file__).parent.parent.parent / "src" / "trading_bot" / "src"))
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from core.models import CandleData, TimeFrame, MarketContext, MarketCondition, TradeSignal


class TestTradingBotIntegration:
    """Integration tests for the complete trading bot system."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a comprehensive mock configuration."""
        config = Mock()
        
        # Trading settings
        config.trading_pairs = ['EUR_USD', 'USD_JPY']
        config.timeframes = [TimeFrame.M5, TimeFrame.M15]
        config.technical_confidence_threshold = 0.6
        config.data_update_frequency = 60
        config.max_trades_per_day = 10
        config.notification_cooldown = 300
        
        # Risk management
        config.risk_management.max_daily_loss = 5.0
        config.risk_management.max_position_size = 10.0
        config.risk_management.correlation_limit = 0.7
        config.risk_management.max_open_trades = 3
        
        # Technical analysis
        config.technical_analysis.confidence_threshold = 0.6
        config.technical_analysis.signal_strength_threshold = 0.03
        config.technical_analysis.risk_reward_ratio_minimum = 1.8
        
        # Notifications
        config.notifications.telegram_enabled = False
        config.notifications.email_enabled = False
        config.notifications.manual_trade_approval = True
        
        # API settings
        config.oanda_api_key = "test_api_key"
        config.oanda_account_id = "test_account_id"
        config.oanda_url = "https://api-fxpractice.oanda.com/v3"
        
        return config
    
    @pytest.fixture
    def sample_candles(self):
        """Create comprehensive sample candle data."""
        candles = []
        base_time = datetime.now(timezone.utc)
        base_price = Decimal('1.2000')
        
        for i in range(100):
            candle = CandleData(
                timestamp=base_time - timedelta(minutes=i*5),
                open=base_price + Decimal(str(i * 0.0001)),
                high=base_price + Decimal(str(i * 0.0001 + 0.0005)),
                low=base_price + Decimal(str(i * 0.0001 - 0.0005)),
                close=base_price + Decimal(str(i * 0.0001 + 0.0002)),
                pair="EUR_USD",
                timeframe=TimeFrame.M5
            )
            candles.append(candle)
        
        return candles
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_complete_trading_flow(self, mock_config, sample_candles):
        """Test the complete trading flow from data collection to trade decision."""
        with patch('data.data_layer.OandaApi') as mock_oanda, \
             patch('data.data_layer.defs') as mock_defs, \
             patch('data.data_layer.OANDA_AVAILABLE', True), \
             patch('ai.technical_analysis_layer.TechnicalAnalyzer') as mock_tech, \
             patch('decision.risk_manager.OandaApi') as mock_risk_oanda, \
             patch('decision.risk_manager.instrumentCollection') as mock_instruments, \
             patch('decision.risk_manager.ic') as mock_ic, \
             patch('notifications.notification_layer.NotificationLayer') as mock_notifications:
            
            # Setup mocks
            mock_oanda.return_value.validate_credentials = Mock(return_value=True)
            mock_oanda.return_value.get_candles = AsyncMock(return_value=(True, {
                "candles": [{
                    "time": "2024-01-01T00:00:00.000000000Z",
                    "mid": {"o": "1.2000", "h": "1.2010", "l": "1.1990", "c": "1.2005"}
                }]
            }))
            
            # Mock technical analyzer
            mock_tech.return_value.calculate_indicators = Mock(return_value=Mock(
                rsi=25,  # Oversold
                macd=0.001,
                macd_signal=0.0005,
                ema_fast=1.2005,
                ema_slow=1.2002,
                atr=0.005,  # Sufficient volatility
                bollinger_upper=1.2010,
                bollinger_middle=1.2000,
                bollinger_lower=1.1990
            ))
            
            # Import and setup components
            from data.data_layer import DataLayer
            from ai.technical_analysis_layer import TechnicalAnalysisLayer
            from decision.risk_manager import RiskManager
            from notifications.notification_layer import NotificationLayer
            
            # Initialize components
            data_layer = DataLayer(mock_config)
            technical_layer = TechnicalAnalysisLayer(mock_config)
            risk_manager = RiskManager(mock_config)
            notification_layer = NotificationLayer(mock_config)
            
            # Start all components
            await data_layer.start()
            await technical_layer.start()
            await risk_manager.start()
            await notification_layer.start()
            
            try:
                # Test data collection
                market_context = await data_layer.get_market_context("EUR_USD")
                assert isinstance(market_context, MarketContext)
                
                # Test technical analysis
                recommendation, confidence = await technical_layer.analyze_multiple_timeframes(
                    "EUR_USD", {TimeFrame.M5: sample_candles}, market_context
                )
                
                if recommendation is not None:
                    # Test risk assessment
                    risk_assessment = await risk_manager.assess_risk(
                        recommendation, 1.2000, market_context
                    )
                    
                    assert 'approved' in risk_assessment
                    assert 'reason' in risk_assessment
                    assert 'score' in risk_assessment
                    
                    if risk_assessment['approved']:
                        # Test position sizing
                        position_data = await risk_manager.calculate_position_size(
                            recommendation, risk_assessment
                        )
                        
                        assert 'size' in position_data
                        assert 'risk_amount' in position_data
                        assert 'stop_loss' in position_data
                        assert 'take_profit' in position_data
                        
                        # Test notification
                        await notification_layer.send_trade_alert(
                            recommendation, risk_assessment, position_data
                        )
                        
                        # Verify notification was called
                        mock_notifications.return_value.send_trade_alert.assert_called()
                
            finally:
                # Cleanup
                await data_layer.stop()
                await technical_layer.stop()
                await risk_manager.stop()
                await notification_layer.stop()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_data_flow_integration(self, mock_config):
        """Test data flow between components."""
        with patch('data.data_layer.OandaApi') as mock_oanda, \
             patch('data.data_layer.defs') as mock_defs, \
             patch('data.data_layer.OANDA_AVAILABLE', True), \
             patch('ai.technical_analysis_layer.TechnicalAnalyzer') as mock_tech:
            
            # Setup OANDA mock
            mock_oanda.return_value.validate_credentials = Mock(return_value=True)
            mock_oanda.return_value.get_candles = AsyncMock(return_value=(True, {
                "candles": [{
                    "time": "2024-01-01T00:00:00.000000000Z",
                    "mid": {"o": "1.2000", "h": "1.2010", "l": "1.1990", "c": "1.2005"}
                }]
            }))
            
            # Setup technical analyzer mock
            mock_tech.return_value.calculate_indicators = Mock(return_value=Mock(
                rsi=45,
                macd=0.001,
                atr=0.005
            ))
            
            from data.data_layer import DataLayer
            from ai.technical_analysis_layer import TechnicalAnalysisLayer
            
            # Initialize components
            data_layer = DataLayer(mock_config)
            technical_layer = TechnicalAnalysisLayer(mock_config)
            
            await data_layer.start()
            await technical_layer.start()
            
            try:
                # Test data collection and processing
                all_data = await data_layer.get_all_data()
                
                # Test technical analysis with collected data
                for pair, timeframes in all_data.items():
                    market_context = await data_layer.get_market_context(pair)
                    
                    recommendation, confidence = await technical_layer.analyze_multiple_timeframes(
                        pair, timeframes, market_context
                    )
                    
                    # Verify data flow
                    assert isinstance(market_context, MarketContext)
                    if recommendation is not None:
                        assert recommendation.pair == pair
                        assert confidence is not None
                
            finally:
                await data_layer.stop()
                await technical_layer.stop()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_risk_management_integration(self, mock_config, sample_trade_recommendation):
        """Test risk management integration with other components."""
        with patch('decision.risk_manager.OandaApi') as mock_oanda, \
             patch('decision.risk_manager.instrumentCollection') as mock_instruments, \
             patch('decision.risk_manager.ic') as mock_ic:
            
            # Setup mocks
            mock_oanda.return_value.validate_credentials = Mock(return_value=True)
            mock_oanda.return_value.get_account_summary = AsyncMock(return_value={
                "balance": 10000.0
            })
            
            from decision.risk_manager import RiskManager
            
            risk_manager = RiskManager(mock_config)
            await risk_manager.start()
            
            try:
                # Test risk assessment
                market_context = MarketContext(condition=MarketCondition.BREAKOUT)
                risk_assessment = await risk_manager.assess_risk(
                    sample_trade_recommendation, 1.2000, market_context
                )
                
                assert 'approved' in risk_assessment
                assert 'reason' in risk_assessment
                assert 'score' in risk_assessment
                
                # Test position sizing
                if risk_assessment['approved']:
                    position_data = await risk_manager.calculate_position_size(
                        sample_trade_recommendation, risk_assessment
                    )
                    
                    assert 'size' in position_data
                    assert 'risk_amount' in position_data
                    assert position_data['size'] > 0
                    assert position_data['risk_amount'] > 0
                
            finally:
                await risk_manager.stop()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_notification_integration(self, mock_config, sample_trade_recommendation):
        """Test notification system integration."""
        with patch('notifications.notification_layer.NotificationLayer') as mock_notifications:
            
            from notifications.notification_layer import NotificationLayer
            
            notification_layer = NotificationLayer(mock_config)
            await notification_layer.start()
            
            try:
                # Test trade alert
                risk_assessment = {'approved': True, 'reason': 'OK', 'score': 0.8}
                position_data = {
                    'size': Decimal('1000'),
                    'risk_amount': Decimal('50'),
                    'stop_loss': Decimal('1.1950'),
                    'take_profit': Decimal('1.2100')
                }
                
                await notification_layer.send_trade_alert(
                    sample_trade_recommendation, risk_assessment, position_data
                )
                
                # Verify notification was sent
                mock_notifications.return_value.send_trade_alert.assert_called()
                
            finally:
                await notification_layer.stop()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_error_handling_integration(self, mock_config):
        """Test error handling across components."""
        with patch('data.data_layer.OandaApi') as mock_oanda, \
             patch('data.data_layer.defs') as mock_defs, \
             patch('data.data_layer.OANDA_AVAILABLE', True), \
             patch('ai.technical_analysis_layer.TechnicalAnalyzer') as mock_tech:
            
            # Setup OANDA to return errors
            mock_oanda.return_value.validate_credentials = Mock(return_value=False)
            mock_oanda.return_value.get_candles = AsyncMock(return_value=(False, "API Error"))
            
            # Setup technical analyzer to raise exceptions
            mock_tech.return_value.calculate_indicators = Mock(side_effect=Exception("Technical Error"))
            
            from data.data_layer import DataLayer
            from ai.technical_analysis_layer import TechnicalAnalysisLayer
            
            data_layer = DataLayer(mock_config)
            technical_layer = TechnicalAnalysisLayer(mock_config)
            
            await data_layer.start()
            await technical_layer.start()
            
            try:
                # Test error handling in data collection
                all_data = await data_layer.get_all_data()
                assert all_data == {}  # Should return empty dict on error
                
                # Test error handling in technical analysis
                market_context = MarketContext()
                recommendation, confidence = await technical_layer.analyze_multiple_timeframes(
                    "EUR_USD", {}, market_context
                )
                
                assert recommendation is None
                assert confidence is None
                
            finally:
                await data_layer.stop()
                await technical_layer.stop()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_performance_integration(self, mock_config, sample_candles):
        """Test performance with realistic data volumes."""
        with patch('data.data_layer.OandaApi') as mock_oanda, \
             patch('data.data_layer.defs') as mock_defs, \
             patch('data.data_layer.OANDA_AVAILABLE', True), \
             patch('ai.technical_analysis_layer.TechnicalAnalyzer') as mock_tech:
            
            # Setup mocks for performance testing
            mock_oanda.return_value.validate_credentials = Mock(return_value=True)
            mock_oanda.return_value.get_candles = AsyncMock(return_value=(True, {
                "candles": [{
                    "time": "2024-01-01T00:00:00.000000000Z",
                    "mid": {"o": "1.2000", "h": "1.2010", "l": "1.1990", "c": "1.2005"}
                }]
            }))
            
            mock_tech.return_value.calculate_indicators = Mock(return_value=Mock(
                rsi=45,
                macd=0.001,
                atr=0.005
            ))
            
            from data.data_layer import DataLayer
            from ai.technical_analysis_layer import TechnicalAnalysisLayer
            
            data_layer = DataLayer(mock_config)
            technical_layer = TechnicalAnalysisLayer(mock_config)
            
            await data_layer.start()
            await technical_layer.start()
            
            try:
                # Test with multiple pairs and timeframes
                pairs = ['EUR_USD', 'USD_JPY', 'GBP_JPY']
                timeframes = [TimeFrame.M5, TimeFrame.M15]
                
                start_time = datetime.now()
                
                for pair in pairs:
                    for timeframe in timeframes:
                        market_context = await data_layer.get_market_context(pair)
                        recommendation, confidence = await technical_layer.analyze_multiple_timeframes(
                            pair, {timeframe: sample_candles}, market_context
                        )
                
                end_time = datetime.now()
                processing_time = (end_time - start_time).total_seconds()
                
                # Verify performance is reasonable (less than 10 seconds for this test)
                assert processing_time < 10.0
                
            finally:
                await data_layer.stop()
                await technical_layer.stop()

