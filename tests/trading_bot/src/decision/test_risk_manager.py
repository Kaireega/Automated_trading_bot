"""
Unit tests for RiskManager.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
from decimal import Decimal

import sys
from pathlib import Path

# Add the src directory to the path
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent / "src" / "trading_bot" / "src"))
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent / "src"))

from decision.risk_manager import RiskManager
from core.models import TradeRecommendation, TradeSignal, MarketContext, MarketCondition


class TestRiskManager:
    """Test RiskManager functionality."""
    
    @pytest.fixture
    def risk_manager(self, mock_config):
        """Create RiskManager instance for testing."""
        with patch('decision.risk_manager.OandaApi'), \
             patch('decision.risk_manager.instrumentCollection'), \
             patch('decision.risk_manager.ic'):
            manager = RiskManager(mock_config)
            manager.logger = Mock()
            return manager
    
    @pytest.mark.unit
    def test_initialization(self, mock_config):
        """Test RiskManager initialization."""
        with patch('decision.risk_manager.OandaApi'), \
             patch('decision.risk_manager.instrumentCollection'), \
             patch('decision.risk_manager.ic'):
            manager = RiskManager(mock_config)
            
            assert manager.max_daily_loss == Decimal('5.0')
            assert manager.max_position_size == Decimal('10.0')
            assert manager.correlation_limit == 0.7
            assert manager.max_open_trades == 3
            assert manager._daily_loss == Decimal('0')
            assert manager._daily_trades == 0
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_assess_risk_approved(self, risk_manager, sample_trade_recommendation):
        """Test risk assessment approval."""
        market_context = MarketContext(condition=MarketCondition.BREAKOUT)
        current_price = 1.2000
        
        result = await risk_manager.assess_risk(sample_trade_recommendation, current_price, market_context)
        
        assert result['approved'] is True
        assert 'reason' in result
        assert 'score' in result
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_assess_risk_daily_loss_exceeded(self, risk_manager, sample_trade_recommendation):
        """Test risk assessment rejection due to daily loss limit."""
        # Set daily loss to exceed limit
        risk_manager._daily_loss = Decimal('6.0')  # Above 5.0 limit
        
        market_context = MarketContext()
        current_price = 1.2000
        
        result = await risk_manager.assess_risk(sample_trade_recommendation, current_price, market_context)
        
        assert result['approved'] is False
        assert 'daily loss' in result['reason'].lower()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_assess_risk_max_trades_exceeded(self, risk_manager, sample_trade_recommendation):
        """Test risk assessment rejection due to max trades limit."""
        # Set daily trades to exceed limit
        risk_manager._daily_trades = 10  # Above 3 limit
        
        market_context = MarketContext()
        current_price = 1.2000
        
        result = await risk_manager.assess_risk(sample_trade_recommendation, current_price, market_context)
        
        assert result['approved'] is False
        assert 'max trades' in result['reason'].lower()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_calculate_position_size(self, risk_manager, sample_trade_recommendation):
        """Test position size calculation."""
        risk_assessment = {'approved': True, 'reason': 'OK', 'score': 0.8}
        
        result = await risk_manager.calculate_position_size(sample_trade_recommendation, risk_assessment)
        
        assert 'size' in result
        assert 'risk_amount' in result
        assert 'stop_loss' in result
        assert 'take_profit' in result
        assert result['size'] > 0
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_calculate_position_size_no_stop_loss(self, risk_manager):
        """Test position size calculation without stop loss."""
        recommendation = TradeRecommendation(
            pair="EUR_USD",
            signal=TradeSignal.BUY,
            entry_price=Decimal('1.2000'),
            stop_loss=None,  # No stop loss
            take_profit=Decimal('1.2100'),
            confidence=0.75
        )
        
        risk_assessment = {'approved': True, 'reason': 'OK', 'score': 0.8}
        
        result = await risk_manager.calculate_position_size(recommendation, risk_assessment)
        
        assert result['size'] == Decimal('0')
        assert result['risk_amount'] == Decimal('0')
    
    @pytest.mark.unit
    def test_check_position_sizing(self, risk_manager, sample_trade_recommendation):
        """Test position sizing checks."""
        current_price = Decimal('1.2000')
        
        result = risk_manager._check_position_sizing(sample_trade_recommendation, current_price)
        
        assert result['approved'] is True
        assert 'reason' in result
        assert 'score' in result
    
    @pytest.mark.unit
    def test_reset_daily_counters_new_day(self, risk_manager):
        """Test daily counter reset for new day."""
        # Set some values
        risk_manager._daily_loss = Decimal('100')
        risk_manager._daily_trades = 5
        
        # Mock yesterday's date
        yesterday = datetime.now(timezone.utc).date()
        risk_manager._last_reset = yesterday
        
        # Call reset (should reset since it's a new day)
        risk_manager._reset_daily_counters_if_needed()
        
        assert risk_manager._daily_loss == Decimal('0')
        assert risk_manager._daily_trades == 0
    
    @pytest.mark.unit
    def test_reset_daily_counters_same_day(self, risk_manager):
        """Test daily counter reset for same day."""
        # Set some values
        risk_manager._daily_loss = Decimal('100')
        risk_manager._daily_trades = 5
        
        # Mock today's date
        today = datetime.now(timezone.utc).date()
        risk_manager._last_reset = today
        
        # Call reset (should not reset since it's the same day)
        risk_manager._reset_daily_counters_if_needed()
        
        assert risk_manager._daily_loss == Decimal('100')
        assert risk_manager._daily_trades == 5

