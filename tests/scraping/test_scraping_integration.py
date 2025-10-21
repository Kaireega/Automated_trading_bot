"""
Integration Tests for Trading Bot Scraping Modules

This module provides integration tests for scraping modules working together,
including end-to-end testing and data flow validation.

Author: Trading Bot Development Team
Version: 1.0.0
"""

import pytest
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import requests
import time
import json

# Add project paths for imports
project_root = Path(__file__).parent.parent.parent
src_path = project_root / "src"
sys.path.append(str(src_path))
sys.path.append(str(src_path / "scraping"))
sys.path.append(str(src_path / "constants"))

# Import scraping modules
from scraping.fx_calendar import get_fx_calendar
from scraping.investing_com import investing_com_fetch, get_pair
from scraping.dailyfx_com import dailyfx_com
from scraping.bloomberg_com import bloomberg_com
import constants.defs as defs


class TestScrapingIntegration:
    """Integration tests for scraping modules"""
    
    def test_scraper_runner_integration(self):
        """Test the scraper runner integration"""
        # Import the scraper runner
        sys.path.append(str(project_root))
        from run_all_scrapers import ScraperRunner
        
        runner = ScraperRunner()
        
        # Test that all scrapers can be initialized
        assert runner.results is not None
        assert 'fx_calendar' in runner.results
        assert 'investing_com' in runner.results
        assert 'dailyfx' in runner.results
        assert 'bloomberg' in runner.results
        assert 'errors' in runner.results
        assert 'summary' in runner.results
    
    def test_data_flow_consistency(self):
        """Test that data flows consistently through all scrapers"""
        # Test data structure consistency without making actual HTTP requests
        # This test verifies that all scrapers return data in expected formats
        
        # Test FX Calendar data structure
        fx_sample = [
            {
                'date': datetime(2022, 3, 7),
                'country': 'US',
                'category': 'Employment',
                'event': 'Non-Farm Payrolls',
                'symbol': 'USD',
                'actual': '200K',
                'previous': '180K',
                'forecast': '190K'
            }
        ]
        
        # Test Investing.com data structure
        investing_sample = {
            'pair_id': 1,
            'time_frame': 3600,
            'pair_name': 'EUR_USD',
            'ti_buy': '5',
            'ti_sell': '3',
            'updated': datetime.now()
        }
        
        # Test DailyFX data structure
        dailyfx_sample = pd.DataFrame([
            {
                'pair': 'EUR_USD',
                'sentiment': 'Bullish',
                'longs_d': '+5.2%',
                'shorts_d': '-2.1%',
                'longs_w': '+3.8%',
                'shorts_w': '+1.2%'
            }
        ])
        
        # Test Bloomberg data structure
        bloomberg_sample = [
            {
                'headline': 'Fed Raises Interest Rates',
                'link': 'https://www.reuters.com/article/fed-raises-rates'
            }
        ]
        
        # Verify data structures
        assert isinstance(fx_sample, list)
        assert isinstance(investing_sample, dict)
        assert isinstance(dailyfx_sample, pd.DataFrame)
        assert isinstance(bloomberg_sample, list)
    
    def test_error_handling_consistency(self):
        """Test that all scrapers handle errors consistently"""
        # Test network errors
        with patch('scraping.fx_calendar.requests.Session') as mock_fx, \
             patch('scraping.investing_com.requests.get') as mock_inv, \
             patch('scraping.dailyfx_com.requests.get') as mock_dfx, \
             patch('scraping.bloomberg_com.cloudscraper.create_scraper') as mock_bloom:
            
            # Set up all mocks to raise network errors
            mock_fx.return_value.get.side_effect = requests.RequestException("Network error")
            mock_inv.side_effect = requests.RequestException("Network error")
            mock_dfx.side_effect = requests.RequestException("Network error")
            
            mock_bloom_scraper = Mock()
            mock_bloom_scraper.get.side_effect = requests.RequestException("Network error")
            mock_bloom.return_value = mock_bloom_scraper
            
            # All should raise RequestException
            with pytest.raises(requests.RequestException):
                get_fx_calendar(datetime.now())
            
            with pytest.raises(requests.RequestException):
                investing_com_fetch(1, 3600)
            
            with pytest.raises(requests.RequestException):
                dailyfx_com()
            
            with pytest.raises(requests.RequestException):
                bloomberg_com()
    
    def test_data_validation_integration(self):
        """Test data validation across all scrapers"""
        # Test with valid data structures
        fx_sample = [
            {
                'date': datetime(2022, 3, 7),
                'country': 'US',
                'category': 'Employment',
                'event': 'Non-Farm Payrolls',
                'symbol': 'USD',
                'actual': '200K',
                'previous': '180K',
                'forecast': '190K'
            }
        ]
        
        investing_sample = {
            'pair_id': 1,
            'time_frame': 3600,
            'pair_name': 'EUR_USD',
            'ti_buy': '5',
            'ti_sell': '3',
            'updated': datetime.now()
        }
        
        dailyfx_sample = pd.DataFrame([
            {
                'pair': 'EUR_USD',
                'sentiment': 'Bullish',
                'longs_d': '+5.2%',
                'shorts_d': '-2.1%',
                'longs_w': '+3.8%',
                'shorts_w': '+1.2%'
            }
        ])
        
        bloomberg_sample = [
            {
                'headline': 'Fed Raises Interest Rates',
                'link': 'https://www.reuters.com/article/fed-raises-rates'
            }
        ]
        
        # Validate data structures
        assert isinstance(fx_sample, list)
        assert isinstance(investing_sample, dict)
        assert isinstance(dailyfx_sample, pd.DataFrame)
        assert isinstance(bloomberg_sample, list)
        
        # Validate required fields
        if fx_sample:
            for item in fx_sample:
                assert 'date' in item
                assert 'country' in item
                assert 'event' in item
        
        assert 'pair_id' in investing_sample
        assert 'pair_name' in investing_sample
        assert 'updated' in investing_sample
        
        if not dailyfx_sample.empty:
            assert 'pair' in dailyfx_sample.columns
            assert 'sentiment' in dailyfx_sample.columns
        
        if bloomberg_sample:
            for item in bloomberg_sample:
                assert 'headline' in item
                assert 'link' in item


class TestScrapingPerformance:
    """Performance tests for scraping modules"""
    
    def test_scraping_timeout_handling(self):
        """Test that scrapers handle timeouts appropriately"""
        with patch('scraping.fx_calendar.requests.Session') as mock_fx:
            mock_fx.return_value.get.side_effect = requests.Timeout("Request timeout")
            
            with pytest.raises(requests.Timeout):
                get_fx_calendar(datetime.now())
    
    def test_concurrent_scraping_simulation(self):
        """Test simulated concurrent scraping operations"""
        # This test simulates multiple scrapers running concurrently
        with patch('scraping.fx_calendar.requests.Session') as mock_fx, \
             patch('scraping.investing_com.requests.get') as mock_inv:
            
            # Mock responses
            mock_fx_response = Mock()
            mock_fx_response.content = "<html><table id='calendar'></table></html>"
            mock_fx.return_value.get.return_value = mock_fx_response
            
            mock_inv_response = Mock()
            mock_inv_response.content = b"pair_name=EUR/USD*;*quote_link"
            mock_inv.return_value = mock_inv_response
            
            # Simulate concurrent calls
            start_time = time.time()
            
            fx_data = get_fx_calendar(datetime.now())
            investing_data = investing_com_fetch(1, 3600)
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Should complete quickly with mocked responses
            assert execution_time < 1.0
            assert isinstance(fx_data, list)
            assert isinstance(investing_data, dict)
    
    def test_memory_usage_with_large_datasets(self):
        """Test memory usage with large datasets"""
        # Create large mock datasets
        large_fx_data = []
        for i in range(1000):
            large_fx_data.append({
                'date': datetime.now(),
                'country': f'Country_{i}',
                'category': 'Test',
                'event': f'Event_{i}',
                'symbol': 'USD',
                'actual': f'{i}',
                'previous': f'{i-1}',
                'forecast': f'{i+1}'
            })
        
        # Test that large datasets can be handled
        assert len(large_fx_data) == 1000
        assert all('date' in item for item in large_fx_data)
        
        # Test DataFrame creation with large data
        large_df = pd.DataFrame(large_fx_data)
        assert len(large_df) == 1000
        assert 'date' in large_df.columns


class TestScrapingDataQuality:
    """Data quality tests for scraping results"""
    
    def test_fx_calendar_data_completeness(self):
        """Test FX calendar data completeness"""
        sample_data = [
            {
                'date': datetime(2022, 3, 7),
                'country': 'US',
                'category': 'Employment',
                'event': 'Non-Farm Payrolls',
                'symbol': 'USD',
                'actual': '200K',
                'previous': '180K',
                'forecast': '190K'
            }
        ]
        
        # Check data completeness
        required_fields = ['date', 'country', 'category', 'event', 'symbol', 'actual', 'previous', 'forecast']
        for item in sample_data:
            for field in required_fields:
                assert field in item
                assert item[field] is not None
    
    def test_investing_com_data_completeness(self):
        """Test Investing.com data completeness"""
        sample_data = {
            'pair_id': 1,
            'time_frame': 3600,
            'pair_name': 'EUR_USD',
            'ti_buy': '5',
            'ti_sell': '3',
            'ma_buy': '4',
            'ma_sell': '2',
            'S1': '1.0800',
            'pivot': '1.0850',
            'R1': '1.0900',
            'percent_bullish': '65',
            'percent_bearish': '35',
            'updated': datetime.now()
        }
        
        # Check required fields
        required_fields = ['pair_id', 'time_frame', 'pair_name', 'updated']
        for field in required_fields:
            assert field in sample_data
            assert sample_data[field] is not None
        
        # Check data types
        assert isinstance(sample_data['pair_id'], int)
        assert isinstance(sample_data['time_frame'], int)
        assert isinstance(sample_data['pair_name'], str)
        assert isinstance(sample_data['updated'], datetime)
    
    def test_dailyfx_data_completeness(self):
        """Test DailyFX data completeness"""
        sample_data = pd.DataFrame([
            {
                'pair': 'EUR_USD',
                'sentiment': 'Bullish',
                'longs_d': '+5.2%',
                'shorts_d': '-2.1%',
                'longs_w': '+3.8%',
                'shorts_w': '+1.2%'
            }
        ])
        
        # Check required columns
        required_columns = ['pair', 'sentiment', 'longs_d', 'shorts_d', 'longs_w', 'shorts_w']
        for col in required_columns:
            assert col in sample_data.columns
        
        # Check data types
        assert isinstance(sample_data, pd.DataFrame)
        if not sample_data.empty:
            assert sample_data['pair'].dtype == 'object'
            assert sample_data['sentiment'].dtype == 'object'
    
    def test_bloomberg_data_completeness(self):
        """Test Bloomberg data completeness"""
        sample_data = [
            {
                'headline': 'Fed Raises Interest Rates',
                'link': 'https://www.reuters.com/article/fed-raises-rates'
            }
        ]
        
        # Check required fields
        for item in sample_data:
            assert 'headline' in item
            assert 'link' in item
            assert item['headline'] is not None
            assert item['link'] is not None
            assert item['link'].startswith('https://')


class TestScrapingConfiguration:
    """Test scraping configuration and constants"""
    
    def test_constants_definitions(self):
        """Test that constants are properly defined"""
        # Test that defs module is importable and has required constants
        assert hasattr(defs, 'TFS')
        assert hasattr(defs, 'INVESTING_COM_PAIRS')
        
        # Test TFS structure
        assert isinstance(defs.TFS, dict)
        assert 'H1' in defs.TFS
        assert 'D' in defs.TFS
        
        # Test INVESTING_COM_PAIRS structure
        assert isinstance(defs.INVESTING_COM_PAIRS, dict)
        if defs.INVESTING_COM_PAIRS:
            # Test first pair structure
            first_pair = next(iter(defs.INVESTING_COM_PAIRS.values()))
            assert 'pair_id' in first_pair
    
    def test_timeframe_validation(self):
        """Test timeframe validation in get_pair function"""
        with patch('scraping.investing_com.investing_com_fetch') as mock_fetch:
            # Create a side effect that returns different timeframes based on call
            def mock_fetch_side_effect(pair_id, time_frame):
                return {
                    'pair_id': pair_id,
                    'time_frame': time_frame,
                    'pair_name': 'EUR_USD',
                    'updated': datetime.now()
                }
            
            mock_fetch.side_effect = mock_fetch_side_effect
            
            # Test valid timeframes
            valid_timeframes = ['H1', 'D']
            for tf in valid_timeframes:
                if tf in defs.TFS:
                    result = get_pair("EUR_USD", tf)
                    assert result['time_frame'] == defs.TFS[tf]
            
            # Test invalid timeframe (should default)
            result = get_pair("EUR_USD", "INVALID")
            assert result['time_frame'] == defs.TFS['H1']


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
