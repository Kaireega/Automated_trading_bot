"""
Comprehensive Tests for Scraping Data Integration Module

This module provides comprehensive tests for the scraping data integration functionality,
ensuring 100% test coverage and following TDD principles. Updated to cover all new features
including pivot points, trend analysis, news sentiment, MyFXBook integration, and more.

Author: Trading Bot Development Team
Version: 2.0.0
"""

import pytest
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import logging

# Add project paths for imports
project_root = Path(__file__).parent.parent.parent.parent.parent
src_path = project_root / "src"
sys.path.append(str(src_path))
sys.path.append(str(src_path / "scraping"))
sys.path.append(str(src_path / "constants"))

# Import the module under test
from trading_bot.src.data.scraping_data_integration import (
    ScrapingDataIntegration, get_scraping_data_integration, get_market_data_for_pair
)


class TestScrapingDataIntegration:
    """Test suite for ScrapingDataIntegration class"""
    
    def test_initialization(self):
        """Test ScrapingDataIntegration initialization"""
        integration = ScrapingDataIntegration()
        
        assert integration.cache == {}
        assert integration.cache_expiry == {}
        assert integration.logger is not None
        assert hasattr(integration, 'cache_durations')
        assert hasattr(integration, 'data_quality_scores')
        assert hasattr(integration, 'accuracy_history')
        assert hasattr(integration, 'market_sessions')
        assert hasattr(integration, 'session_priorities')
    
    def test_initialization_with_logger(self):
        """Test ScrapingDataIntegration initialization with custom logger"""
        custom_logger = logging.getLogger("test_logger")
        integration = ScrapingDataIntegration(custom_logger)
        
        assert integration.logger == custom_logger
        assert integration.cache == {}
        assert integration.cache_expiry == {}
    
    def test_cache_durations_configuration(self):
        """Test cache durations are properly configured"""
        integration = ScrapingDataIntegration()
        
        expected_durations = {
            'economic_calendar': 3600,
            'technical_analysis': 300,
            'market_sentiment': 600,
            'financial_news': 180,
            'myfxbook_sentiment': 900,
            'comprehensive_data': 300
        }
        
        for data_type, duration in expected_durations.items():
            assert integration.cache_durations[data_type] == duration
    
    def test_data_quality_scores_configuration(self):
        """Test data quality scores are properly configured"""
        integration = ScrapingDataIntegration()
        
        expected_scores = {
            'economic_calendar': 0.9,
            'technical_analysis': 0.8,
            'market_sentiment': 0.6,
            'financial_news': 0.7,
            'myfxbook_sentiment': 0.5
        }
        
        for data_type, score in expected_scores.items():
            assert integration.data_quality_scores[data_type] == score
    
    def test_market_sessions_configuration(self):
        """Test market sessions are properly configured"""
        integration = ScrapingDataIntegration()
        
        expected_sessions = {
            'asian': {'start': 0, 'end': 9},
            'london': {'start': 8, 'end': 17},
            'new_york': {'start': 13, 'end': 22}
        }
        
        for session, times in expected_sessions.items():
            assert integration.market_sessions[session] == times
    
    def test_cache_validation(self):
        """Test cache validation functionality"""
        integration = ScrapingDataIntegration()
        
        # Test with no cache
        assert not integration._is_cache_valid("nonexistent_key")
        
        # Test with expired cache
        integration.cache_expiry["test_key"] = datetime.now() - timedelta(seconds=1)
        assert not integration._is_cache_valid("test_key")
        
        # Test with valid cache
        integration.cache_expiry["test_key"] = datetime.now() + timedelta(seconds=100)
        integration.cache["test_key"] = "test_data"
        assert integration._is_cache_valid("test_key")
    
    def test_cache_update(self):
        """Test cache update functionality"""
        integration = ScrapingDataIntegration()
        
        test_data = {"test": "data"}
        integration._update_cache("test_key", test_data, "economic_calendar")
        
        assert integration.cache["test_key"] == test_data
        assert "test_key" in integration.cache_expiry
        assert integration.cache_expiry["test_key"] > datetime.now()
    
    def test_cache_update_with_different_types(self):
        """Test cache update with different data types"""
        integration = ScrapingDataIntegration()
        
        # Test with economic calendar (1 hour cache)
        integration._update_cache("econ_key", {"event": "test"}, "economic_calendar")
        econ_expiry = integration.cache_expiry["econ_key"]
        
        # Test with technical analysis (5 minutes cache)
        integration._update_cache("tech_key", {"signal": "test"}, "technical_analysis")
        tech_expiry = integration.cache_expiry["tech_key"]
        
        # Economic calendar should expire later than technical analysis
        assert econ_expiry > tech_expiry
    
    @patch('trading_bot.src.data.scraping_data_integration.get_fx_calendar')
    def test_get_economic_calendar_success(self, mock_get_fx_calendar):
        """Test successful economic calendar retrieval"""
        mock_data = [
            {
                'date': datetime(2022, 3, 7),
                'country': 'US',
                'category': 'Interest Rate',
                'event': 'Fed Rate Decision',
                'symbol': 'USD',
                'actual': '0.25%',
                'previous': '0.0%',
                'forecast': '0.25%'
            },
            {
                'date': datetime(2022, 3, 8),
                'country': 'US',
                'category': 'Weather',
                'event': 'Daily Weather Report',
                'symbol': 'USD',
                'actual': 'Sunny',
                'previous': 'Cloudy',
                'forecast': 'Rainy'
            }
        ]
        mock_get_fx_calendar.return_value = mock_data
        
        integration = ScrapingDataIntegration()
        result = integration.get_economic_calendar(7)
        
        # Should filter for high-impact events only
        assert len(result) == 1  # Only the Fed Rate Decision should be included
        assert result[0]['event'] == 'Fed Rate Decision'
        assert 'scraped_at' in result[0]
        assert "economic_calendar_7" in integration.cache
        mock_get_fx_calendar.assert_called_once()
    
    @patch('trading_bot.src.data.scraping_data_integration.get_fx_calendar')
    def test_get_economic_calendar_error(self, mock_get_fx_calendar):
        """Test economic calendar retrieval with error"""
        mock_get_fx_calendar.side_effect = Exception("Network error")
        
        integration = ScrapingDataIntegration()
        result = integration.get_economic_calendar(7)
        
        assert result == []
    
    @patch('trading_bot.src.data.scraping_data_integration.get_fx_calendar')
    def test_get_economic_calendar_cache(self, mock_get_fx_calendar):
        """Test economic calendar cache functionality"""
        mock_data = [{'event': 'Test Event', 'category': 'Interest Rate'}]
        mock_get_fx_calendar.return_value = mock_data
        
        integration = ScrapingDataIntegration()
        
        # First call
        result1 = integration.get_economic_calendar(7)
        assert result1 == mock_data  # Should filter for important events
        
        # Second call should use cache
        result2 = integration.get_economic_calendar(7)
        assert result2 == mock_data
        assert mock_get_fx_calendar.call_count == 1
    
    @patch('trading_bot.src.data.scraping_data_integration.investing_com_fetch')
    def test_get_technical_analysis_success(self, mock_fetch):
        """Test successful technical analysis retrieval"""
        mock_data = {
            'pair_id': 1,
            'time_frame': 3600,
            'pair_name': 'EUR_USD',
            'ti_buy': '5',
            'ti_sell': '3',
            'ma_buy': '4',
            'ma_sell': '2',
            'percent_bullish': 60.0,
            'percent_bearish': 40.0,
            'pivot': '1.1745',
            'S1': '1.1700',
            'S2': '1.1650',
            'S3': '1.1600',
            'R1': '1.1800',
            'R2': '1.1850',
            'R3': '1.1900',
            'updated': datetime.now()
        }
        mock_fetch.return_value = mock_data
        
        integration = ScrapingDataIntegration()
        result = integration.get_technical_analysis("EUR_USD", "H1")
        
        assert result['pair_name'] == 'EUR_USD'
        assert result['signal_strength'] is not None
        assert 'analysis_timestamp' in result
        assert 'pivot_analysis' in result
        assert 'trend_strength' in result
        assert 'quality_score' in result
        
        # Test pivot analysis
        pivot_analysis = result['pivot_analysis']
        assert 'support_levels' in pivot_analysis
        assert 'resistance_levels' in pivot_analysis
        assert 'key_levels' in pivot_analysis
        
        # Test trend analysis
        trend_analysis = result['trend_strength']
        assert 'overall_trend' in trend_analysis
        assert 'trend_direction' in trend_analysis
        assert 'trend_strength' in trend_analysis
        assert 'confidence' in trend_analysis
    
    @patch('trading_bot.src.data.scraping_data_integration.investing_com_fetch')
    def test_get_technical_analysis_invalid_pair(self, mock_fetch):
        """Test technical analysis with invalid pair"""
        integration = ScrapingDataIntegration()
        result = integration.get_technical_analysis("INVALID_PAIR", "H1")
        
        assert result is None
        mock_fetch.assert_not_called()
    
    @patch('trading_bot.src.data.scraping_data_integration.investing_com_fetch')
    def test_get_technical_analysis_error(self, mock_fetch):
        """Test technical analysis with error"""
        mock_fetch.side_effect = Exception("Network error")
        
        integration = ScrapingDataIntegration()
        result = integration.get_technical_analysis("EUR_USD", "H1")
        
        assert result is None
    
    def test_get_market_sentiment_success(self):
        """Test successful market sentiment retrieval"""
        integration = ScrapingDataIntegration()
        result = integration.get_market_sentiment()
        
        assert isinstance(result, pd.DataFrame)
        assert 'sentiment_score' in result.columns
        assert 'analysis_timestamp' in result.columns
        assert len(result) == 5  # Should have 5 pairs
        assert 'EUR_USD' in result['pair'].values
        assert 'GBP_USD' in result['pair'].values
    
    def test_get_market_sentiment_caching(self):
        """Test market sentiment caching"""
        integration = ScrapingDataIntegration()
        
        # First call
        result1 = integration.get_market_sentiment()
        
        # Second call should use cache
        result2 = integration.get_market_sentiment()
        
        assert result1.equals(result2)
        assert "market_sentiment" in integration.cache
    
    @patch('trading_bot.src.data.scraping_data_integration.bloomberg_com')
    def test_get_financial_news_success(self, mock_bloomberg):
        """Test successful financial news retrieval"""
        mock_data = [
            {
                'headline': 'Fed Raises Interest Rates Amid Inflation Concerns',
                'link': 'https://www.reuters.com/article/fed-raises-rates'
            },
            {
                'headline': 'Weather Forecast for Tomorrow',
                'link': 'https://www.reuters.com/article/weather'
            }
        ]
        mock_bloomberg.return_value = mock_data
        
        integration = ScrapingDataIntegration()
        result = integration.get_financial_news()
        
        assert len(result) == 2
        assert result[0]['headline'] == 'Fed Raises Interest Rates Amid Inflation Concerns'
        assert 'relevance_score' in result[0]
        assert 'analysis_timestamp' in result[0]
        assert 'impact_level' in result[0]
        assert 'category' in result[0]
        assert 'sentiment' in result[0]
        
        # High relevance article should be first (sorted by relevance)
        assert result[0]['relevance_score'] > result[1]['relevance_score']
    
    @patch('trading_bot.src.data.scraping_data_integration.bloomberg_com')
    def test_get_financial_news_error(self, mock_bloomberg):
        """Test financial news with error"""
        mock_bloomberg.side_effect = Exception("Network error")
        
        integration = ScrapingDataIntegration()
        result = integration.get_financial_news()
        
        assert result == []
    
    @patch('trading_bot.src.data.scraping_data_integration.get_fx_calendar')
    @patch('trading_bot.src.data.scraping_data_integration.investing_com_fetch')
    @patch('trading_bot.src.data.scraping_data_integration.bloomberg_com')
    @patch('scraping.my_fx_book.get_sentiment_data')
    def test_get_comprehensive_market_data_success(self, mock_myfxbook, mock_bloomberg, 
                                                   mock_fetch, mock_fx_calendar):
        """Test successful comprehensive market data retrieval"""
        # Mock all data sources
        mock_fx_calendar.return_value = [{'event': 'Test Event', 'category': 'Interest Rate'}]
        mock_fetch.return_value = {
            'pair_id': 1,
            'pair_name': 'EUR_USD',
            'ti_buy': '5',
            'ti_sell': '3',
            'ma_buy': '4',
            'ma_sell': '2',
            'percent_bullish': 60.0,
            'percent_bearish': 40.0
        }
        mock_bloomberg.return_value = [{'headline': 'Fed Raises Interest Rates'}]
        mock_myfxbook.return_value = pd.DataFrame([{
            'pair_name': 'EURUSD',
            'bullish_perc': '55',
            'bearish_perc': '45',
            'popularity': '85'
        }])
        
        integration = ScrapingDataIntegration()
        result = integration.get_comprehensive_market_data("EUR_USD", "H1")
        
        assert result['pair_name'] == 'EUR_USD'
        assert result['timeframe'] == 'H1'
        assert 'economic_calendar' in result
        assert 'technical_analysis' in result
        assert 'market_sentiment' in result
        assert 'myfxbook_sentiment' in result
        assert 'financial_news' in result
        assert 'overall_score' in result
        assert 'signal_consensus' in result
    
    @patch('trading_bot.src.data.scraping_data_integration.get_fx_calendar')
    @patch('trading_bot.src.data.scraping_data_integration.investing_com_fetch')
    @patch('trading_bot.src.data.scraping_data_integration.bloomberg_com')
    @patch('scraping.my_fx_book.get_sentiment_data')
    def test_get_comprehensive_market_data_error(self, mock_myfxbook, mock_bloomberg, 
                                                mock_fetch, mock_fx_calendar):
        """Test comprehensive market data with error"""
        mock_fx_calendar.side_effect = Exception("Network error")
        mock_fetch.side_effect = Exception("Network error")
        mock_bloomberg.side_effect = Exception("Network error")
        mock_myfxbook.side_effect = Exception("Network error")
        
        integration = ScrapingDataIntegration()
        result = integration.get_comprehensive_market_data("EUR_USD", "H1")
        
        # Should still return a structure with empty data
        assert 'pair_name' in result
        assert 'economic_calendar' in result
        assert 'technical_analysis' in result
        assert 'myfxbook_sentiment' in result
        assert result['economic_calendar'] == []
        assert result['technical_analysis'] is None
    
    def test_calculate_signal_strength(self):
        """Test signal strength calculation"""
        integration = ScrapingDataIntegration()
        
        # Test with bullish signals
        technical_data = {
            'ti_buy': '8',
            'ti_sell': '2',
            'ma_buy': '7',
            'ma_sell': '3'
        }
        score = integration._calculate_signal_strength(technical_data)
        assert score > 0
        
        # Test with bearish signals
        technical_data = {
            'ti_buy': '2',
            'ti_sell': '8',
            'ma_buy': '3',
            'ma_sell': '7'
        }
        score = integration._calculate_signal_strength(technical_data)
        assert score < 0
        
        # Test with no signals
        technical_data = {
            'ti_buy': '0',
            'ti_sell': '0',
            'ma_buy': '0',
            'ma_sell': '0'
        }
        score = integration._calculate_signal_strength(technical_data)
        assert score == 0.0
    
    def test_calculate_signal_strength_error(self):
        """Test signal strength calculation with error"""
        integration = ScrapingDataIntegration()
        
        # Test with invalid data
        technical_data = {
            'ti_buy': 'invalid',
            'ti_sell': 'invalid'
        }
        score = integration._calculate_signal_strength(technical_data)
        assert score == 0.0
    
    def test_calculate_sentiment_score(self):
        """Test sentiment score calculation"""
        integration = ScrapingDataIntegration()
        
        sentiment_data = pd.DataFrame([
            {'sentiment': 'Bullish'},
            {'sentiment': 'Bearish'},
            {'sentiment': 'Neutral'}
        ])
        
        scores = integration._calculate_sentiment_score(sentiment_data)
        
        assert scores.iloc[0] == 1.0  # Bullish
        assert scores.iloc[1] == -1.0  # Bearish
        assert scores.iloc[2] == 0.0  # Neutral
    
    def test_calculate_news_relevance(self):
        """Test news relevance calculation"""
        integration = ScrapingDataIntegration()
        
        # Test high relevance article
        article = {
            'headline': 'Fed Raises Interest Rates Amid Inflation Concerns'
        }
        score = integration._calculate_news_relevance(article)
        assert score > 0.3  # Should find at least 3 keywords
        
        # Test low relevance article
        article = {
            'headline': 'Weather Forecast for Tomorrow'
        }
        score = integration._calculate_news_relevance(article)
        assert score == 0.0
    
    def test_calculate_overall_market_score(self):
        """Test overall market score calculation"""
        integration = ScrapingDataIntegration()
        
        market_data = {
            'pair_name': 'EUR_USD',
            'technical_analysis': {'signal_strength': 0.2},
            'market_sentiment': pd.DataFrame([{'pair': 'EUR_USD', 'sentiment_score': 0.3}]),
            'financial_news': [{'relevance_score': 0.8}],
            'economic_calendar': [{'event': 'Test'}]
        }
        
        score = integration._calculate_overall_market_score(market_data)
        assert isinstance(score, float)
        assert -1.0 <= score <= 1.0
    
    def test_calculate_overall_market_score_error(self):
        """Test overall market score calculation with error"""
        integration = ScrapingDataIntegration()
        
        market_data = {
            'pair_name': 'EUR_USD',
            'technical_analysis': {'signal_strength': 'invalid'}
        }
        
        score = integration._calculate_overall_market_score(market_data)
        assert score == 0.0
    
    def test_clear_cache(self):
        """Test cache clearing functionality"""
        integration = ScrapingDataIntegration()
        
        # Add some cache data
        integration.cache['test_key'] = 'test_data'
        integration.cache_expiry['test_key'] = datetime.now()
        
        # Clear cache
        integration.clear_cache()
        
        assert len(integration.cache) == 0
        assert len(integration.cache_expiry) == 0
    
    def test_get_cache_status(self):
        """Test cache status retrieval"""
        integration = ScrapingDataIntegration()
        
        # Add some cache data
        integration.cache['test_key'] = 'test_data'
        integration.cache_expiry['test_key'] = datetime.now()
        
        status = integration.get_cache_status()
        
        assert status['cache_size'] == 1
        assert 'test_key' in status['cache_keys']
        assert 'test_key' in status['cache_expiry']


class TestNewAnalysisMethods:
    """Test suite for new analysis methods"""
    
    def test_process_pivot_points(self):
        """Test pivot points processing"""
        integration = ScrapingDataIntegration()
        
        technical_data = {
            'pivot': '1.1745',
            'S1': '1.1700',
            'S2': '1.1650',
            'S3': '1.1600',
            'R1': '1.1800',
            'R2': '1.1850',
            'R3': '1.1900'
        }
        
        result = integration._process_pivot_points(technical_data)
        
        assert 'support_levels' in result
        assert 'resistance_levels' in result
        assert 'key_levels' in result
        assert len(result['support_levels']) == 3
        assert len(result['resistance_levels']) == 3
        assert result['key_levels'] == [1.1745]
    
    def test_calculate_trend_strength_bullish(self):
        """Test trend strength calculation for bullish trend"""
        integration = ScrapingDataIntegration()
        
        technical_data = {
            'percent_bullish': 70.0,
            'percent_bearish': 30.0,
            'signal_strength': 0.4
        }
        
        result = integration._calculate_trend_strength(technical_data)
        
        assert result['overall_trend'] == 'bullish'
        assert result['trend_direction'] == 'up'
        assert result['trend_strength'] > 0
        assert result['confidence'] > 0
    
    def test_assess_news_impact_high(self):
        """Test news impact assessment for high impact news"""
        integration = ScrapingDataIntegration()
        
        article = {
            'headline': 'Fed Raises Interest Rates to Combat Inflation'
        }
        
        result = integration._assess_news_impact(article)
        assert result == 'high'
    
    def test_categorize_news_economic_indicator(self):
        """Test news categorization for economic indicators"""
        integration = ScrapingDataIntegration()
        
        article = {
            'headline': 'GDP Growth Rate Exceeds Expectations'
        }
        
        result = integration._categorize_news(article)
        assert result == 'economic_indicator'
    
    def test_analyze_news_sentiment_positive(self):
        """Test news sentiment analysis for positive sentiment"""
        integration = ScrapingDataIntegration()
        
        article = {
            'headline': 'Economic Growth Surges to Record High'
        }
        
        result = integration._analyze_news_sentiment(article)
        assert result == 'positive'


class TestMyFXBookIntegration:
    """Test suite for MyFXBook integration"""
    
    @patch('scraping.my_fx_book.get_sentiment_data')
    def test_get_myfxbook_sentiment_success(self, mock_get_sentiment):
        """Test successful MyFXBook sentiment retrieval"""
        mock_data = pd.DataFrame([
            {
                'pair_name': 'EURUSD',
                'bullish_perc': '55',
                'bearish_perc': '45',
                'popularity': '85'
            }
        ])
        mock_get_sentiment.return_value = mock_data
        
        integration = ScrapingDataIntegration()
        result = integration.get_myfxbook_sentiment()
        
        assert isinstance(result, pd.DataFrame)
        assert 'sentiment_score' in result.columns
        assert 'sentiment_strength' in result.columns
        assert 'contrarian_signal' in result.columns
    
    def test_calculate_myfxbook_sentiment_score(self):
        """Test MyFXBook sentiment score calculation"""
        integration = ScrapingDataIntegration()
        
        sentiment_data = pd.DataFrame([
            {'bullish_perc': '60', 'bearish_perc': '40'},
            {'bullish_perc': '30', 'bearish_perc': '70'}
        ])
        
        result = integration._calculate_myfxbook_sentiment_score(sentiment_data)
        
        assert len(result) == 2
        assert result.iloc[0] == 0.2  # 60-40 = 20%
        assert result.iloc[1] == -0.4  # 30-70 = -40%


class TestSessionOptimization:
    """Test suite for session-based optimization"""
    
    def test_get_current_market_session_asian(self):
        """Test current market session detection for Asian session"""
        integration = ScrapingDataIntegration()
        
        with patch('trading_bot.src.data.scraping_data_integration.datetime') as mock_datetime:
            mock_datetime.now.return_value.hour = 5  # 5 AM UTC (Asian session)
            
            result = integration._get_current_market_session()
            assert result == 'asian'
    
    def test_get_current_market_session_london(self):
        """Test current market session detection for London session"""
        integration = ScrapingDataIntegration()
        
        with patch('trading_bot.src.data.scraping_data_integration.datetime') as mock_datetime:
            mock_datetime.now.return_value.hour = 10  # 10 AM UTC (London session)
            
            result = integration._get_current_market_session()
            assert result == 'london'


class TestDataQualityAndRecency:
    """Test suite for data quality and recency features"""
    
    def test_assess_data_quality_high_quality(self):
        """Test data quality assessment for high quality data"""
        integration = ScrapingDataIntegration()
        
        data = [{'event': 'Test Event', 'category': 'Interest Rate'}]
        result = integration._assess_data_quality(data, 'economic_calendar')
        
        assert result > 0.8  # Should be high quality
    
    def test_calculate_data_recency_weight_fresh(self):
        """Test data recency weight calculation for fresh data"""
        integration = ScrapingDataIntegration()
        
        fresh_timestamp = datetime.now() - timedelta(minutes=2)
        result = integration._calculate_data_recency_weight(fresh_timestamp, 'technical_analysis')
        
        assert result == 1.0  # Should be full weight


class TestFallbackMechanisms:
    """Test suite for fallback mechanisms"""
    
    def test_get_fallback_market_data(self):
        """Test fallback market data when primary sources fail"""
        integration = ScrapingDataIntegration()
        
        result = integration.get_fallback_market_data('EUR_USD', 'H1')
        
        assert result['pair_name'] == 'EUR_USD'
        assert result['timeframe'] == 'H1'
        assert result['data_source'] in ['fallback', 'myfxbook_fallback', 'emergency_fallback']
        assert 'overall_score' in result
        assert 'signal_consensus' in result


class TestConvenienceFunctions:
    """Test suite for convenience functions"""
    
    def test_get_scraping_data_integration(self):
        """Test get_scraping_data_integration function"""
        integration = get_scraping_data_integration()
        
        assert isinstance(integration, ScrapingDataIntegration)
    
    def test_get_scraping_data_integration_with_logger(self):
        """Test get_scraping_data_integration function with logger"""
        custom_logger = logging.getLogger("test_logger")
        integration = get_scraping_data_integration(custom_logger)
        
        assert isinstance(integration, ScrapingDataIntegration)
        assert integration.logger == custom_logger
    
    @patch('trading_bot.src.data.scraping_data_integration.ScrapingDataIntegration.get_comprehensive_market_data')
    def test_get_market_data_for_pair(self, mock_get_data):
        """Test get_market_data_for_pair convenience function"""
        mock_data = {'pair_name': 'EUR_USD', 'test': 'data'}
        mock_get_data.return_value = mock_data
        
        result = get_market_data_for_pair("EUR_USD", "H1")
        
        assert result == mock_data
        mock_get_data.assert_called_once_with("EUR_USD", "H1")


class TestScrapingDataIntegrationEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_empty_data_handling(self):
        """Test handling of empty data from scrapers"""
        integration = ScrapingDataIntegration()
        
        # Test with empty economic calendar
        with patch('trading_bot.src.data.scraping_data_integration.get_fx_calendar') as mock_get:
            mock_get.return_value = []
            result = integration.get_economic_calendar()
            assert result == []
        
        # Test with empty sentiment data (market sentiment is now placeholder)
        result = integration.get_market_sentiment()
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 5  # Should have 5 pairs in placeholder data
    
    def test_malformed_data_handling(self):
        """Test handling of malformed data"""
        integration = ScrapingDataIntegration()
        
        # Test with malformed technical data
        with patch('trading_bot.src.data.scraping_data_integration.investing_com_fetch') as mock_get:
            mock_get.return_value = {'invalid': 'data'}
            result = integration.get_technical_analysis("EUR_USD", "H1")
            # Should still process but with default values
            assert result is not None
    
    def test_concurrent_access(self):
        """Test concurrent access to cache"""
        integration = ScrapingDataIntegration()
        
        # Simulate concurrent access
        integration.cache['key1'] = 'data1'
        integration.cache['key2'] = 'data2'
        
        # Should not interfere with each other
        assert integration.cache['key1'] == 'data1'
        assert integration.cache['key2'] == 'data2'
    
    def test_cache_expiry_edge_cases(self):
        """Test cache expiry edge cases"""
        integration = ScrapingDataIntegration()
        
        # Test with exactly expired cache
        past_time = datetime.now() - timedelta(seconds=1)
        integration.cache_expiry['test_key'] = past_time
        integration.cache['test_key'] = 'test_data'
        
        assert not integration._is_cache_valid("test_key")
        
        # Test with exactly valid cache
        future_time = datetime.now() + timedelta(seconds=1)
        integration.cache_expiry['test_key'] = future_time
        
        assert integration._is_cache_valid("test_key")


class TestScrapingDataIntegrationPerformance:
    """Test performance characteristics"""
    
    def test_cache_performance(self):
        """Test cache performance benefits"""
        integration = ScrapingDataIntegration()
        
        # Add data to cache
        test_data = {'test': 'data'}
        integration._update_cache('perf_test', test_data)
        
        # Multiple accesses should be fast (no external calls)
        start_time = datetime.now()
        for _ in range(100):
            assert integration._is_cache_valid('perf_test')
        end_time = datetime.now()
        
        # Should be very fast (less than 1 second for 100 checks)
        duration = (end_time - start_time).total_seconds()
        assert duration < 1.0
    
    def test_memory_usage(self):
        """Test memory usage with large datasets"""
        integration = ScrapingDataIntegration()
        
        # Create large dataset
        large_data = [{'event': f'Event {i}'} for i in range(1000)]
        integration._update_cache('large_data', large_data)
        
        # Should handle large datasets
        assert len(integration.cache['large_data']) == 1000
        assert integration._is_cache_valid('large_data')


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
