"""
Unit tests for TechnicalAnalysisLayer.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import sys
from pathlib import Path

# Add the src directory to the path
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent / "src" / "trading_bot" / "src"))
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent / "src"))

from ai.technical_analysis_layer import TechnicalAnalysisLayer
from core.models import CandleData, TimeFrame, MarketContext, MarketCondition, TradeSignal


class TestTechnicalAnalysisLayer:
    """Test TechnicalAnalysisLayer functionality."""
    
    @pytest.fixture
    def technical_layer(self, mock_config):
        """Create TechnicalAnalysisLayer instance for testing."""
        with patch('ai.technical_analysis_layer.TechnicalAnalyzer'), \
             patch('ai.technical_analysis_layer.MultiTimeframeAnalyzer'):
            layer = TechnicalAnalysisLayer(mock_config)
            layer.logger = Mock()
            return layer
    
    @pytest.mark.unit
    def test_initialization(self, mock_config):
        """Test TechnicalAnalysisLayer initialization."""
        with patch('ai.technical_analysis_layer.TechnicalAnalyzer'), \
             patch('ai.technical_analysis_layer.MultiTimeframeAnalyzer'):
            layer = TechnicalAnalysisLayer(mock_config)
            
            assert layer.config == mock_config
            assert layer.rsi_oversold == 20
            assert layer.rsi_overbought == 80
            assert layer.min_signal_strength == 0.75
            assert layer.trade_cooldown_minutes == 30
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_trade_cooldown_check(self, technical_layer, sample_candles):
        """Test trade cooldown functionality."""
        pair = "EUR_USD"
        current_time = datetime.now(timezone.utc)
        
        # Set last trade time to 15 minutes ago (within cooldown)
        technical_layer._last_trade_time[pair] = current_time - timedelta(minutes=15)
        
        # Mock technical analyzer
        technical_layer.technical_analyzer.calculate_indicators = Mock(return_value=Mock())
        
        # Should return None due to cooldown
        result = await technical_layer.analyze_multiple_timeframes(
            pair, {TimeFrame.M5: sample_candles}, Mock()
        )
        
        assert result == (None, None)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_insufficient_candles(self, technical_layer):
        """Test handling of insufficient candle data."""
        pair = "EUR_USD"
        insufficient_candles = [Mock() for _ in range(10)]  # Less than 20 required
        
        result = await technical_layer.analyze_multiple_timeframes(
            pair, {TimeFrame.M5: insufficient_candles}, Mock()
        )
        
        assert result == (None, None)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_unfavorable_market_condition(self, technical_layer, sample_candles):
        """Test rejection due to unfavorable market conditions."""
        pair = "EUR_USD"
        market_context = MarketContext(condition=MarketCondition.RANGING)
        
        # Mock technical analyzer
        technical_layer.technical_analyzer.calculate_indicators = Mock(return_value=Mock())
        
        result = await technical_layer.analyze_multiple_timeframes(
            pair, {TimeFrame.M5: sample_candles}, market_context
        )
        
        # Should return None due to ranging market condition
        assert result[0] is None
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_insufficient_volatility(self, technical_layer, sample_candles):
        """Test rejection due to insufficient volatility."""
        pair = "EUR_USD"
        market_context = MarketContext(condition=MarketCondition.BREAKOUT)
        
        # Mock technical analyzer with low ATR
        mock_indicators = Mock()
        mock_indicators.atr = 0.001  # Below 0.003 threshold
        technical_layer.technical_analyzer.calculate_indicators = Mock(return_value=mock_indicators)
        
        result = await technical_layer.analyze_multiple_timeframes(
            pair, {TimeFrame.M5: sample_candles}, market_context
        )
        
        # Should return None due to low volatility
        assert result[0] is None
    
    @pytest.mark.unit
    def test_signal_analysis_buy_signals(self, technical_layer):
        """Test signal analysis with buy signals."""
        # Mock indicators with buy signals
        indicators = Mock()
        indicators.rsi = 15  # Oversold
        indicators.macd = 0.001
        indicators.macd_signal = 0.0005
        indicators.bollinger_upper = 1.2010
        indicators.bollinger_middle = 1.2000
        indicators.bollinger_lower = 1.1990
        indicators.ema_fast = 1.2005
        indicators.ema_slow = 1.2002
        indicators.atr = 0.005  # Sufficient volatility
        
        market_context = Mock()
        
        result = technical_layer._analyze_technical_signals(indicators, market_context)
        
        assert result['rsi_signal'] == TradeSignal.BUY
        assert result['macd_signal'] == TradeSignal.BUY
        assert result['ema_signal'] == TradeSignal.BUY
        assert result['overall_signal'] == TradeSignal.BUY
        assert result['has_signal'] is True
    
    @pytest.mark.unit
    def test_signal_analysis_sell_signals(self, technical_layer):
        """Test signal analysis with sell signals."""
        # Mock indicators with sell signals
        indicators = Mock()
        indicators.rsi = 85  # Overbought
        indicators.macd = 0.0005
        indicators.macd_signal = 0.001
        indicators.bollinger_upper = 1.2010
        indicators.bollinger_middle = 1.2000
        indicators.bollinger_lower = 1.1990
        indicators.ema_fast = 1.1995
        indicators.ema_slow = 1.2002
        indicators.atr = 0.005
        
        market_context = Mock()
        
        result = technical_layer._analyze_technical_signals(indicators, market_context)
        
        assert result['rsi_signal'] == TradeSignal.SELL
        assert result['macd_signal'] == TradeSignal.SELL
        assert result['ema_signal'] == TradeSignal.SELL
        assert result['overall_signal'] == TradeSignal.SELL
        assert result['has_signal'] is True
    
    @pytest.mark.unit
    def test_signal_confluence_insufficient(self, technical_layer):
        """Test signal confluence with insufficient signals."""
        signals = {
            'rsi_signal': TradeSignal.BUY,
            'macd_signal': None,
            'bollinger_signal': None,
            'ema_signal': None,
            'overall_signal': None,
            'has_signal': False,
            'signal_strength': 0.0,
            'reasoning': []
        }
        
        result = technical_layer._calculate_signal_confluence(signals)
        
        assert result['has_signal'] is False
        assert result['confluence_score'] == 0.0
    
    @pytest.mark.unit
    def test_signal_confluence_sufficient(self, technical_layer):
        """Test signal confluence with sufficient signals."""
        signals = {
            'rsi_signal': TradeSignal.BUY,
            'macd_signal': TradeSignal.BUY,
            'bollinger_signal': TradeSignal.BUY,
            'ema_signal': None,
            'overall_signal': None,
            'has_signal': False,
            'signal_strength': 0.0,
            'reasoning': []
        }
        
        result = technical_layer._calculate_signal_confluence(signals)
        
        assert result['has_signal'] is True
        assert result['overall_signal'] == TradeSignal.BUY
        assert result['confluence_score'] > 0.6
    
    @pytest.mark.unit
    def test_get_current_price(self, technical_layer, sample_candles):
        """Test current price calculation."""
        price = technical_layer._get_current_price(sample_candles)
        
        # Should be typical price (high + low) / 2
        expected_price = (sample_candles[-1].high + sample_candles[-1].low) / Decimal('2')
        assert price == expected_price
    
    @pytest.mark.unit
    def test_get_current_price_empty(self, technical_layer):
        """Test current price calculation with empty candles."""
        price = technical_layer._get_current_price([])
        
        assert price == Decimal('0')
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_start_stop(self, technical_layer):
        """Test start and stop methods."""
        await technical_layer.start()
        await technical_layer.stop()
        
        # Should not raise exceptions
        assert True

