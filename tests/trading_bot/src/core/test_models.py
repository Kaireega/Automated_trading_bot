"""
Unit tests for core data models.
"""
import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import sys
from pathlib import Path

# Add the src directory to the path
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent / "src" / "trading_bot" / "src"))

from core.models import (
    CandleData, TimeFrame, MarketContext, MarketCondition,
    TradeRecommendation, TradeDecision, TradeSignal, TechnicalIndicators
)


class TestCandleData:
    """Test CandleData model functionality."""
    
    @pytest.mark.unit
    def test_candle_data_creation_success(self):
        """Test successful CandleData creation."""
        candle = CandleData(
            timestamp=datetime.now(timezone.utc),
            open=Decimal('1.2000'),
            high=Decimal('1.2010'),
            low=Decimal('1.1990'),
            close=Decimal('1.2005'),
            pair="EUR_USD",
            timeframe=TimeFrame.M5
        )
        
        assert candle.open == Decimal('1.2000')
        assert candle.high == Decimal('1.2010')
        assert candle.low == Decimal('1.1990')
        assert candle.close == Decimal('1.2005')
        assert candle.pair == "EUR_USD"
        assert candle.timeframe == TimeFrame.M5
    
    @pytest.mark.unit
    def test_candle_data_float_conversion(self):
        """Test automatic float to Decimal conversion."""
        candle = CandleData(
            timestamp=datetime.now(timezone.utc),
            open=1.2000,  # Float input
            high=1.2010,
            low=1.1990,
            close=1.2005,
            pair="EUR_USD"
        )
        
        assert isinstance(candle.open, Decimal)
        assert candle.open == Decimal('1.2000')
    
    @pytest.mark.unit
    def test_candle_data_volume_optional(self):
        """Test that volume is optional."""
        candle = CandleData(
            timestamp=datetime.now(timezone.utc),
            open=Decimal('1.2000'),
            high=Decimal('1.2010'),
            low=Decimal('1.1990'),
            close=Decimal('1.2005'),
            pair="EUR_USD"
        )
        
        assert candle.volume is None


class TestTechnicalIndicators:
    """Test TechnicalIndicators model functionality."""
    
    @pytest.mark.unit
    def test_technical_indicators_creation(self):
        """Test TechnicalIndicators creation with all fields."""
        indicators = TechnicalIndicators(
            rsi=45.5,
            macd=0.0012,
            macd_signal=0.0008,
            ema_fast=1.2005,
            ema_slow=1.2002,
            atr=0.0025
        )
        
        assert indicators.rsi == 45.5
        assert indicators.macd == 0.0012
        assert indicators.macd_signal == 0.0008
        assert indicators.ema_fast == 1.2005
        assert indicators.ema_slow == 1.2002
        assert indicators.atr == 0.0025
    
    @pytest.mark.unit
    def test_technical_indicators_defaults(self):
        """Test TechnicalIndicators with default values."""
        indicators = TechnicalIndicators()
        
        assert indicators.rsi is None
        assert indicators.macd is None
        assert indicators.ema_fast is None
        assert indicators.atr is None


class TestTradeRecommendation:
    """Test TradeRecommendation model functionality."""
    
    @pytest.mark.unit
    def test_trade_recommendation_creation(self):
        """Test TradeRecommendation creation."""
        recommendation = TradeRecommendation(
            pair="EUR_USD",
            signal=TradeSignal.BUY,
            entry_price=Decimal('1.2000'),
            stop_loss=Decimal('1.1950'),
            take_profit=Decimal('1.2100'),
            confidence=0.75,
            reasoning="Test reasoning"
        )
        
        assert recommendation.pair == "EUR_USD"
        assert recommendation.signal == TradeSignal.BUY
        assert recommendation.entry_price == Decimal('1.2000')
        assert recommendation.confidence == 0.75
        assert recommendation.reasoning == "Test reasoning"
        assert recommendation.id is not None  # Should auto-generate UUID
    
    @pytest.mark.unit
    def test_trade_recommendation_float_conversion(self):
        """Test automatic float to Decimal conversion for prices."""
        recommendation = TradeRecommendation(
            pair="EUR_USD",
            signal=TradeSignal.BUY,
            entry_price=1.2000,  # Float input
            stop_loss=1.1950,
            take_profit=1.2100,
            confidence=0.75
        )
        
        assert isinstance(recommendation.entry_price, Decimal)
        assert isinstance(recommendation.stop_loss, Decimal)
        assert isinstance(recommendation.take_profit, Decimal)


class TestMarketContext:
    """Test MarketContext model functionality."""
    
    @pytest.mark.unit
    def test_market_context_creation(self):
        """Test MarketContext creation."""
        context = MarketContext(
            condition=MarketCondition.BREAKOUT,
            volatility=0.02,
            trend_strength=0.7,
            news_sentiment=0.3
        )
        
        assert context.condition == MarketCondition.BREAKOUT
        assert context.volatility == 0.02
        assert context.trend_strength == 0.7
        assert context.news_sentiment == 0.3
        assert context.timestamp is not None
    
    @pytest.mark.unit
    def test_market_context_defaults(self):
        """Test MarketContext with default values."""
        context = MarketContext()
        
        assert context.condition == MarketCondition.UNKNOWN
        assert context.volatility == 0.0
        assert context.trend_strength == 0.0
        assert context.news_sentiment == 0.0
        assert context.economic_events == []
        assert context.key_levels == {}


class TestTradeDecision:
    """Test TradeDecision model functionality."""
    
    @pytest.mark.unit
    def test_trade_decision_creation(self, sample_trade_recommendation):
        """Test TradeDecision creation."""
        decision = TradeDecision(
            recommendation=sample_trade_recommendation,
            approved=True,
            position_size=Decimal('1000'),
            risk_amount=Decimal('50'),
            modified_stop_loss=Decimal('1.1940'),
            modified_take_profit=Decimal('1.2110'),
            risk_management_notes="Kelly Criterion applied"
        )
        
        assert decision.recommendation == sample_trade_recommendation
        assert decision.approved is True
        assert decision.position_size == Decimal('1000')
        assert decision.risk_amount == Decimal('50')
        assert decision.risk_management_notes == "Kelly Criterion applied"
        assert decision.timestamp is not None


class TestTimeFrame:
    """Test TimeFrame enum functionality."""
    
    @pytest.mark.unit
    def test_timeframe_values(self):
        """Test TimeFrame enum values."""
        assert TimeFrame.M1.value == "M1"
        assert TimeFrame.M5.value == "M5"
        assert TimeFrame.M15.value == "M15"
        assert TimeFrame.H1.value == "H1"
    
    @pytest.mark.unit
    def test_timeframe_from_string(self):
        """Test creating TimeFrame from string."""
        tf = TimeFrame("M5")
        assert tf == TimeFrame.M5


class TestMarketCondition:
    """Test MarketCondition enum functionality."""
    
    @pytest.mark.unit
    def test_market_condition_values(self):
        """Test MarketCondition enum values."""
        assert MarketCondition.NEWS_REACTIONARY.value == "news_reactionary"
        assert MarketCondition.REVERSAL.value == "reversal"
        assert MarketCondition.BREAKOUT.value == "breakout"
        assert MarketCondition.RANGING.value == "ranging"
        assert MarketCondition.UNKNOWN.value == "unknown"


class TestTradeSignal:
    """Test TradeSignal enum functionality."""
    
    @pytest.mark.unit
    def test_trade_signal_values(self):
        """Test TradeSignal enum values."""
        assert TradeSignal.BUY.value == "buy"
        assert TradeSignal.SELL.value == "sell"
        assert TradeSignal.HOLD.value == "hold"

