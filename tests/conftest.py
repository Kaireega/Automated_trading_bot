"""
Shared Test Configuration and Fixtures for the Trading Bot Test Suite.

This module provides comprehensive test configuration, fixtures, and utilities
for testing the Market Adaptive Trading Bot. It includes mock objects, test data
generators, and shared configuration for all test modules.

Key Features:
- Comprehensive test fixtures for all bot components
- Mock configuration and API objects
- Test data generators for market data and indicators
- Async test support with proper event loop management
- Shared test utilities and helper functions
- Integration test setup and teardown

Test Fixtures:
- mock_config: Mock configuration object with realistic settings
- sample_candles: Sample candle data for testing
- sample_indicators: Sample technical indicators
- sample_recommendation: Sample trade recommendation
- sample_decision: Sample trade decision
- mock_oanda_api: Mock OANDA API for testing
- mock_data_layer: Mock data layer for testing

The test suite is designed to provide comprehensive coverage of all bot
components while maintaining realistic test conditions and data.

Author: Trading Bot Development Team
Version: 2.0.0
Last Updated: 2024
"""
import pytest
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import Mock, AsyncMock

# Add the src directory to the path
sys.path.append(str(Path(__file__).parent.parent / "src" / "trading_bot" / "src"))
sys.path.append(str(Path(__file__).parent.parent / "src"))

from core.models import (
    CandleData, TimeFrame, MarketContext, MarketCondition, 
    TradeRecommendation, TradeDecision, TradeSignal, TechnicalIndicators
)
from utils.config import Config


@pytest.fixture(scope="session")
def event_loop():
    """
    Create an instance of the default event loop for the test session.
    
    This fixture ensures that async tests have access to a proper event loop
    and handles cleanup after the test session completes.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_config():
    """
    Create a comprehensive mock configuration for testing.
    
    This fixture provides a realistic configuration object with all necessary
    settings for testing bot components. It includes trading parameters,
    risk management settings, and technical analysis thresholds.
    
    Returns:
        Mock: Mock configuration object with realistic test settings
    """
    config = Mock(spec=Config)
    
    # Trading settings
    config.trading_pairs = ['EUR_USD', 'USD_JPY', 'GBP_JPY']
    config.timeframes = [TimeFrame.M1, TimeFrame.M5, TimeFrame.M15]
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
def sample_candles():
    """Create sample candle data for testing."""
    candles = []
    base_time = datetime.now(timezone.utc)
    base_price = Decimal('1.2000')
    
    for i in range(50):
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


@pytest.fixture
def sample_technical_indicators():
    """Create sample technical indicators for testing."""
    return TechnicalIndicators(
        rsi=45.5,
        macd=0.0012,
        macd_signal=0.0008,
        macd_histogram=0.0004,
        ema_fast=1.2005,
        ema_slow=1.2002,
        bollinger_upper=1.2010,
        bollinger_middle=1.2000,
        bollinger_lower=1.1990,
        atr=0.0025,
        stoch_k=55.0,
        stoch_d=50.0
    )


@pytest.fixture
def sample_market_context():
    """Create sample market context for testing."""
    return MarketContext(
        condition=MarketCondition.BREAKOUT,
        volatility=0.02,
        trend_strength=0.7,
        news_sentiment=0.3,
        economic_events=[],
        key_levels={},
        timestamp=datetime.now(timezone.utc)
    )


@pytest.fixture
def sample_trade_recommendation():
    """Create sample trade recommendation for testing."""
    return TradeRecommendation(
        pair="EUR_USD",
        signal=TradeSignal.BUY,
        entry_price=Decimal('1.2000'),
        stop_loss=Decimal('1.1950'),
        take_profit=Decimal('1.2100'),
        confidence=0.75,
        market_condition=MarketCondition.BREAKOUT,
        reasoning="Strong bullish signals from RSI and MACD",
        risk_reward_ratio=2.0,
        estimated_hold_time=timedelta(hours=2)
    )


@pytest.fixture
def mock_oanda_api():
    """Create a mock OANDA API for testing."""
    api = Mock()
    api.validate_credentials = Mock(return_value=True)
    api.make_request = Mock(return_value=(True, {"data": "test"}))
    api.get_account_summary = AsyncMock(return_value={"balance": 10000.0})
    api.get_pricing = AsyncMock(return_value={"prices": [{"bid": 1.2000, "ask": 1.2001}]})
    return api


@pytest.fixture
def mock_notification_layer():
    """Create a mock notification layer for testing."""
    layer = Mock()
    layer.send_notification = AsyncMock(return_value=True)
    layer.send_trade_alert = AsyncMock(return_value=True)
    layer.start = AsyncMock()
    layer.close = AsyncMock()
    return layer


# Test markers
pytest_plugins = ["pytest_asyncio"]
