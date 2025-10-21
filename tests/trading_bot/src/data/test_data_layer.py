"""
Unit tests for DataLayer.
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

from data.data_layer import DataLayer
from core.models import CandleData, TimeFrame, MarketContext, MarketCondition


class TestDataLayer:
    """Test DataLayer functionality."""
    
    @pytest.fixture
    def data_layer(self, mock_config):
        """Create DataLayer instance for testing."""
        with patch('data.data_layer.OandaApi'), \
             patch('data.data_layer.defs'), \
             patch('data.data_layer.OANDA_AVAILABLE', True):
            layer = DataLayer(mock_config)
            layer.logger = Mock()
            return layer
    
    @pytest.mark.unit
    def test_initialization(self, mock_config):
        """Test DataLayer initialization."""
        with patch('data.data_layer.OandaApi'), \
             patch('data.data_layer.defs'), \
             patch('data.data_layer.OANDA_AVAILABLE', True):
            layer = DataLayer(mock_config)
            
            assert layer.config == mock_config
            assert layer._candles == {}
            assert layer._market_contexts == {}
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_start_stop(self, data_layer):
        """Test start and stop methods."""
        await data_layer.start()
        await data_layer.stop()
        
        # Should not raise exceptions
        assert True
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_all_data_empty(self, data_layer):
        """Test get_all_data with no data."""
        result = await data_layer.get_all_data()
        
        assert result == {}
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_all_data_with_candles(self, data_layer, sample_candles):
        """Test get_all_data with sample data."""
        # Add some test data
        data_layer._candles['EUR_USD'] = {
            TimeFrame.M5: sample_candles,
            TimeFrame.M15: sample_candles[:30]
        }
        
        result = await data_layer.get_all_data()
        
        assert 'EUR_USD' in result
        assert TimeFrame.M5 in result['EUR_USD']
        assert TimeFrame.M15 in result['EUR_USD']
        assert len(result['EUR_USD'][TimeFrame.M5]) == len(sample_candles)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_market_context(self, data_layer):
        """Test get_market_context method."""
        pair = "EUR_USD"
        
        # Mock the market context generation
        with patch.object(data_layer, '_generate_market_context') as mock_generate:
            mock_context = MarketContext(
                condition=MarketCondition.BREAKOUT,
                volatility=0.02,
                trend_strength=0.7
            )
            mock_generate.return_value = mock_context
            
            result = await data_layer.get_market_context(pair)
            
            assert result == mock_context
            mock_generate.assert_called_once_with(pair)
    
    @pytest.mark.unit
    def test_generate_market_context(self, data_layer):
        """Test market context generation."""
        pair = "EUR_USD"
        
        # Mock candles data
        data_layer._candles[pair] = {
            TimeFrame.M5: [Mock() for _ in range(20)]
        }
        
        with patch.object(data_layer, '_calculate_volatility') as mock_vol, \
             patch.object(data_layer, '_calculate_trend_strength') as mock_trend:
            
            mock_vol.return_value = 0.02
            mock_trend.return_value = 0.7
            
            result = data_layer._generate_market_context(pair)
            
            assert isinstance(result, MarketContext)
            assert result.volatility == 0.02
            assert result.trend_strength == 0.7
    
    @pytest.mark.unit
    def test_calculate_volatility(self, data_layer, sample_candles):
        """Test volatility calculation."""
        volatility = data_layer._calculate_volatility(sample_candles)
        
        assert isinstance(volatility, float)
        assert volatility >= 0.0
    
    @pytest.mark.unit
    def test_calculate_volatility_insufficient_data(self, data_layer):
        """Test volatility calculation with insufficient data."""
        insufficient_candles = [Mock() for _ in range(5)]
        
        volatility = data_layer._calculate_volatility(insufficient_candles)
        
        assert volatility == 0.0
    
    @pytest.mark.unit
    def test_calculate_trend_strength(self, data_layer, sample_candles):
        """Test trend strength calculation."""
        trend_strength = data_layer._calculate_trend_strength(sample_candles)
        
        assert isinstance(trend_strength, float)
        assert 0.0 <= trend_strength <= 1.0
    
    @pytest.mark.unit
    def test_calculate_trend_strength_insufficient_data(self, data_layer):
        """Test trend strength calculation with insufficient data."""
        insufficient_candles = [Mock() for _ in range(5)]
        
        trend_strength = data_layer._calculate_trend_strength(insufficient_candles)
        
        assert trend_strength == 0.0
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_collect_data_oanda_unavailable(self, data_layer):
        """Test data collection when OANDA is unavailable."""
        # Mock OANDA as unavailable
        data_layer.oanda_api = None
        
        result = await data_layer._collect_data("EUR_USD", TimeFrame.M5)
        
        # Should return empty list when OANDA unavailable
        assert result == []
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_collect_data_with_mock_data(self, data_layer):
        """Test data collection with mock data."""
        pair = "EUR_USD"
        timeframe = TimeFrame.M5
        
        # Mock OANDA API response
        mock_response = {
            "candles": [
                {
                    "time": "2024-01-01T00:00:00.000000000Z",
                    "mid": {
                        "o": "1.2000",
                        "h": "1.2010",
                        "l": "1.1990",
                        "c": "1.2005"
                    }
                }
            ]
        }
        
        data_layer.oanda_api.get_candles = AsyncMock(return_value=(True, mock_response))
        
        result = await data_layer._collect_data(pair, timeframe)
        
        assert len(result) == 1
        assert isinstance(result[0], CandleData)
        assert result[0].pair == pair
        assert result[0].timeframe == timeframe
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_collect_data_api_error(self, data_layer):
        """Test data collection with API error."""
        pair = "EUR_USD"
        timeframe = TimeFrame.M5
        
        # Mock OANDA API error
        data_layer.oanda_api.get_candles = AsyncMock(return_value=(False, "API Error"))
        
        result = await data_layer._collect_data(pair, timeframe)
        
        # Should return empty list on API error
        assert result == []
    
    @pytest.mark.unit
    def test_validate_candle_data(self, data_layer):
        """Test candle data validation."""
        # Valid candle
        valid_candle = CandleData(
            timestamp=datetime.now(timezone.utc),
            open=Decimal('1.2000'),
            high=Decimal('1.2010'),
            low=Decimal('1.1990'),
            close=Decimal('1.2005'),
            pair="EUR_USD"
        )
        
        assert data_layer._validate_candle_data(valid_candle) is True
        
        # Invalid candle (high < low)
        invalid_candle = CandleData(
            timestamp=datetime.now(timezone.utc),
            open=Decimal('1.2000'),
            high=Decimal('1.1990'),  # High < Low
            low=Decimal('1.2010'),
            close=Decimal('1.2005'),
            pair="EUR_USD"
        )
        
        assert data_layer._validate_candle_data(invalid_candle) is False
    
    @pytest.mark.unit
    def test_filter_duplicate_candles(self, data_layer):
        """Test filtering duplicate candles."""
        base_time = datetime.now(timezone.utc)
        
        # Create candles with duplicates
        candles = [
            CandleData(
                timestamp=base_time,
                open=Decimal('1.2000'),
                high=Decimal('1.2010'),
                low=Decimal('1.1990'),
                close=Decimal('1.2005'),
                pair="EUR_USD"
            ),
            CandleData(
                timestamp=base_time,  # Same timestamp (duplicate)
                open=Decimal('1.2001'),
                high=Decimal('1.2011'),
                low=Decimal('1.1991'),
                close=Decimal('1.2006'),
                pair="EUR_USD"
            ),
            CandleData(
                timestamp=base_time + timedelta(minutes=5),  # Different timestamp
                open=Decimal('1.2002'),
                high=Decimal('1.2012'),
                low=Decimal('1.1992'),
                close=Decimal('1.2007'),
                pair="EUR_USD"
            )
        ]
        
        filtered = data_layer._filter_duplicate_candles(candles)
        
        # Should have 2 candles (duplicate removed)
        assert len(filtered) == 2
        assert filtered[0].timestamp == base_time
        assert filtered[1].timestamp == base_time + timedelta(minutes=5)

