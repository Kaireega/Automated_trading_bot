"""
Integration tests for API interactions.
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

from core.models import CandleData, TimeFrame


class TestOandaApiIntegration:
    """Integration tests for OANDA API interactions."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration for API testing."""
        config = Mock()
        config.oanda_api_key = "test_api_key"
        config.oanda_account_id = "test_account_id"
        config.oanda_url = "https://api-fxpractice.oanda.com/v3"
        return config
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_oanda_api_initialization(self, mock_config):
        """Test OANDA API initialization and validation."""
        with patch('api.oanda_api.OandaApi') as mock_oanda_class:
            mock_oanda = Mock()
            mock_oanda.validate_credentials = Mock(return_value=True)
            mock_oanda_class.return_value = mock_oanda
            
            from api.oanda_api import OandaApi
            
            api = OandaApi(mock_config)
            assert api is not None
            
            # Test credential validation
            is_valid = await api.validate_credentials()
            assert is_valid is True
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_oanda_api_candle_retrieval(self, mock_config):
        """Test OANDA API candle data retrieval."""
        with patch('api.oanda_api.OandaApi') as mock_oanda_class:
            mock_oanda = Mock()
            mock_oanda.validate_credentials = Mock(return_value=True)
            mock_oanda.get_candles = AsyncMock(return_value=(True, {
                "candles": [
                    {
                        "time": "2024-01-01T00:00:00.000000000Z",
                        "mid": {
                            "o": "1.2000",
                            "h": "1.2010",
                            "l": "1.1990",
                            "c": "1.2005"
                        }
                    },
                    {
                        "time": "2024-01-01T00:05:00.000000000Z",
                        "mid": {
                            "o": "1.2005",
                            "h": "1.2015",
                            "l": "1.1995",
                            "c": "1.2010"
                        }
                    }
                ]
            }))
            mock_oanda_class.return_value = mock_oanda
            
            from api.oanda_api import OandaApi
            
            api = OandaApi(mock_config)
            
            # Test candle retrieval
            success, data = await api.get_candles("EUR_USD", "M5", 2)
            
            assert success is True
            assert "candles" in data
            assert len(data["candles"]) == 2
            
            # Verify candle data structure
            candle = data["candles"][0]
            assert "time" in candle
            assert "mid" in candle
            assert "o" in candle["mid"]
            assert "h" in candle["mid"]
            assert "l" in candle["mid"]
            assert "c" in candle["mid"]
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_oanda_api_error_handling(self, mock_config):
        """Test OANDA API error handling."""
        with patch('api.oanda_api.OandaApi') as mock_oanda_class:
            mock_oanda = Mock()
            mock_oanda.validate_credentials = Mock(return_value=False)
            mock_oanda.get_candles = AsyncMock(return_value=(False, "API Error"))
            mock_oanda_class.return_value = mock_oanda
            
            from api.oanda_api import OandaApi
            
            api = OandaApi(mock_config)
            
            # Test credential validation failure
            is_valid = await api.validate_credentials()
            assert is_valid is False
            
            # Test candle retrieval failure
            success, data = await api.get_candles("EUR_USD", "M5", 2)
            assert success is False
            assert data == "API Error"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_oanda_api_account_summary(self, mock_config):
        """Test OANDA API account summary retrieval."""
        with patch('api.oanda_api.OandaApi') as mock_oanda_class:
            mock_oanda = Mock()
            mock_oanda.validate_credentials = Mock(return_value=True)
            mock_oanda.get_account_summary = AsyncMock(return_value={
                "account": {
                    "balance": "10000.00",
                    "currency": "USD",
                    "openTradeCount": 0,
                    "openPositionCount": 0
                }
            })
            mock_oanda_class.return_value = mock_oanda
            
            from api.oanda_api import OandaApi
            
            api = OandaApi(mock_config)
            
            # Test account summary retrieval
            account_data = await api.get_account_summary()
            
            assert "account" in account_data
            assert "balance" in account_data["account"]
            assert "currency" in account_data["account"]
            assert account_data["account"]["balance"] == "10000.00"
            assert account_data["account"]["currency"] == "USD"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_oanda_api_pricing(self, mock_config):
        """Test OANDA API pricing data retrieval."""
        with patch('api.oanda_api.OandaApi') as mock_oanda_class:
            mock_oanda = Mock()
            mock_oanda.validate_credentials = Mock(return_value=True)
            mock_oanda.get_pricing = AsyncMock(return_value={
                "prices": [
                    {
                        "instrument": "EUR_USD",
                        "time": "2024-01-01T00:00:00.000000000Z",
                        "bids": [{"price": "1.2000", "liquidity": 1000000}],
                        "asks": [{"price": "1.2001", "liquidity": 1000000}]
                    }
                ]
            })
            mock_oanda_class.return_value = mock_oanda
            
            from api.oanda_api import OandaApi
            
            api = OandaApi(mock_config)
            
            # Test pricing data retrieval
            pricing_data = await api.get_pricing(["EUR_USD"])
            
            assert "prices" in pricing_data
            assert len(pricing_data["prices"]) == 1
            
            price = pricing_data["prices"][0]
            assert price["instrument"] == "EUR_USD"
            assert "bids" in price
            assert "asks" in price
            assert len(price["bids"]) == 1
            assert len(price["asks"]) == 1
            assert price["bids"][0]["price"] == "1.2000"
            assert price["asks"][0]["price"] == "1.2001"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_oanda_api_rate_limiting(self, mock_config):
        """Test OANDA API rate limiting handling."""
        with patch('api.oanda_api.OandaApi') as mock_oanda_class:
            mock_oanda = Mock()
            mock_oanda.validate_credentials = Mock(return_value=True)
            
            # Mock rate limiting response
            mock_oanda.get_candles = AsyncMock(side_effect=[
                (False, "Rate limit exceeded"),
                (True, {"candles": []})
            ])
            mock_oanda_class.return_value = mock_oanda
            
            from api.oanda_api import OandaApi
            
            api = OandaApi(mock_config)
            
            # Test rate limiting handling
            success, data = await api.get_candles("EUR_USD", "M5", 2)
            assert success is False
            assert data == "Rate limit exceeded"
            
            # Test retry after rate limit
            success, data = await api.get_candles("EUR_USD", "M5", 2)
            assert success is True
            assert "candles" in data
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_oanda_api_connection_timeout(self, mock_config):
        """Test OANDA API connection timeout handling."""
        with patch('api.oanda_api.OandaApi') as mock_oanda_class:
            mock_oanda = Mock()
            mock_oanda.validate_credentials = Mock(return_value=True)
            mock_oanda.get_candles = AsyncMock(side_effect=asyncio.TimeoutError("Connection timeout"))
            mock_oanda_class.return_value = mock_oanda
            
            from api.oanda_api import OandaApi
            
            api = OandaApi(mock_config)
            
            # Test connection timeout handling
            with pytest.raises(asyncio.TimeoutError):
                await api.get_candles("EUR_USD", "M5", 2)
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_oanda_api_instrument_validation(self, mock_config):
        """Test OANDA API instrument validation."""
        with patch('api.oanda_api.OandaApi') as mock_oanda_class:
            mock_oanda = Mock()
            mock_oanda.validate_credentials = Mock(return_value=True)
            mock_oanda.get_candles = AsyncMock(return_value=(False, "Invalid instrument"))
            mock_oanda_class.return_value = mock_oanda
            
            from api.oanda_api import OandaApi
            
            api = OandaApi(mock_config)
            
            # Test invalid instrument handling
            success, data = await api.get_candles("INVALID_PAIR", "M5", 2)
            assert success is False
            assert data == "Invalid instrument"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_oanda_api_data_consistency(self, mock_config):
        """Test OANDA API data consistency across multiple requests."""
        with patch('api.oanda_api.OandaApi') as mock_oanda_class:
            mock_oanda = Mock()
            mock_oanda.validate_credentials = Mock(return_value=True)
            
            # Mock consistent data across multiple requests
            consistent_data = {
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
            
            mock_oanda.get_candles = AsyncMock(return_value=(True, consistent_data))
            mock_oanda_class.return_value = mock_oanda
            
            from api.oanda_api import OandaApi
            
            api = OandaApi(mock_config)
            
            # Test data consistency across multiple requests
            for _ in range(3):
                success, data = await api.get_candles("EUR_USD", "M5", 1)
                assert success is True
                assert data == consistent_data
                
                # Verify data structure consistency
                assert "candles" in data
                assert len(data["candles"]) == 1
                candle = data["candles"][0]
                assert "time" in candle
                assert "mid" in candle
                assert "o" in candle["mid"]
                assert "h" in candle["mid"]
                assert "l" in candle["mid"]
                assert "c" in candle["mid"]

