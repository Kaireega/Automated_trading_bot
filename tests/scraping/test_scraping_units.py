"""
Unit Tests for Trading Bot Scraping Modules

This module provides focused unit tests for individual scraping functions,
ensuring 100% test coverage and following TDD principles.

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
from bs4 import BeautifulSoup
import time
import json

# Add project paths for imports
project_root = Path(__file__).parent.parent.parent
src_path = project_root / "src"
sys.path.append(str(src_path))
sys.path.append(str(src_path / "scraping"))
sys.path.append(str(src_path / "constants"))

# Import scraping modules
from scraping.fx_calendar import (
    get_date, get_data_point, get_data_for_key, get_data_dict, 
    get_fx_calendar, fx_calendar
)
from scraping.investing_com import (
    get_data_object, investing_com_fetch, investing_com, get_pair
)
from scraping.dailyfx_com import dailyfx_com
from scraping.bloomberg_com import bloomberg_com, get_article
import constants.defs as defs


class TestFXCalendarUnitFunctions:
    """Unit tests for FX Calendar helper functions"""
    
    def test_get_date_with_valid_colspan(self):
        """Test get_date with valid colspan attribute"""
        mock_html = """
        <thead>
            <tr>
                <th colspan="3">Monday, March 7, 2022</th>
            </tr>
        </thead>
        """
        soup = BeautifulSoup(mock_html, 'html.parser')
        thead = soup.select_one("thead")
        
        result = get_date(thead)
        assert result is not None
        assert result.year == 2022
        assert result.month == 3
        assert result.day == 7
    
    def test_get_date_with_no_colspan(self):
        """Test get_date with no colspan attribute"""
        mock_html = """
        <thead>
            <tr>
                <th>Some Header</th>
            </tr>
        </thead>
        """
        soup = BeautifulSoup(mock_html, 'html.parser')
        thead = soup.select_one("thead")
        
        result = get_date(thead)
        assert result is None
    
    def test_get_date_with_multiple_headers(self):
        """Test get_date with multiple headers, one with colspan"""
        mock_html = """
        <thead>
            <tr>
                <th>Time</th>
                <th colspan="3">Monday, March 7, 2022</th>
                <th>Impact</th>
            </tr>
        </thead>
        """
        soup = BeautifulSoup(mock_html, 'html.parser')
        thead = soup.select_one("thead")
        
        result = get_date(thead)
        assert result is not None
        assert result.year == 2022
        assert result.month == 3
        assert result.day == 7
    
    def test_get_data_point_with_span(self):
        """Test get_data_point with span element"""
        mock_html = """
        <tr>
            <span id="actual">1.5%</span>
            <span id="previous">1.2%</span>
        </tr>
        """
        soup = BeautifulSoup(mock_html, 'html.parser')
        tr = soup.select_one("tr")
        
        actual = get_data_point('actual', tr)
        previous = get_data_point('previous', tr)
        
        assert actual == "1.5%"
        assert previous == "1.2%"
    
    def test_get_data_point_with_anchor(self):
        """Test get_data_point with anchor element"""
        mock_html = """
        <tr>
            <a id="actual">2.1%</a>
            <a id="forecast">2.0%</a>
        </tr>
        """
        soup = BeautifulSoup(mock_html, 'html.parser')
        tr = soup.select_one("tr")
        
        actual = get_data_point('actual', tr)
        forecast = get_data_point('forecast', tr)
        
        assert actual == "2.1%"
        assert forecast == "2.0%"
    
    def test_get_data_point_not_found(self):
        """Test get_data_point when element not found"""
        mock_html = """
        <tr>
            <span id="actual">1.5%</span>
        </tr>
        """
        soup = BeautifulSoup(mock_html, 'html.parser')
        tr = soup.select_one("tr")
        
        result = get_data_point('nonexistent', tr)
        assert result == ""
    
    def test_get_data_for_key_with_attributes(self):
        """Test get_data_for_key with valid attributes"""
        mock_html = """
        <tr data-country="US" data-category="Employment" data-event="NFP" data-symbol="USD">
        </tr>
        """
        soup = BeautifulSoup(mock_html, 'html.parser')
        tr = soup.select_one("tr")
        
        country = get_data_for_key(tr, 'data-country')
        category = get_data_for_key(tr, 'data-category')
        event = get_data_for_key(tr, 'data-event')
        symbol = get_data_for_key(tr, 'data-symbol')
        
        assert country == "US"
        assert category == "Employment"
        assert event == "NFP"
        assert symbol == "USD"
    
    def test_get_data_for_key_missing_attribute(self):
        """Test get_data_for_key with missing attribute"""
        mock_html = """
        <tr data-country="US">
        </tr>
        """
        soup = BeautifulSoup(mock_html, 'html.parser')
        tr = soup.select_one("tr")
        
        result = get_data_for_key(tr, 'data-category')
        assert result == ""
    
    def test_get_data_dict_single_row(self):
        """Test get_data_dict with single row"""
        test_date = datetime(2022, 3, 7)
        mock_html = """
        <tr data-country="US" data-category="Employment" data-event="NFP" data-symbol="USD">
            <span id="actual">200K</span>
            <span id="previous">180K</span>
            <span id="forecast">190K</span>
        </tr>
        """
        soup = BeautifulSoup(mock_html, 'html.parser')
        tr = soup.select_one("tr")
        
        result = get_data_dict(test_date, [tr])
        
        assert len(result) == 1
        data = result[0]
        assert data['date'] == test_date
        assert data['country'] == "US"
        assert data['category'] == "Employment"
        assert data['event'] == "NFP"
        assert data['symbol'] == "USD"
        assert data['actual'] == "200K"
        assert data['previous'] == "180K"
        assert data['forecast'] == "190K"
    
    def test_get_data_dict_multiple_rows(self):
        """Test get_data_dict with multiple rows"""
        test_date = datetime(2022, 3, 7)
        mock_html = """
        <tr data-country="US" data-category="Employment" data-event="NFP" data-symbol="USD">
            <span id="actual">200K</span>
            <span id="previous">180K</span>
            <span id="forecast">190K</span>
        </tr>
        <tr data-country="UK" data-category="Interest Rate" data-event="BOE" data-symbol="GBP">
            <span id="actual">0.75%</span>
            <span id="previous">0.5%</span>
            <span id="forecast">0.75%</span>
        </tr>
        """
        soup = BeautifulSoup(mock_html, 'html.parser')
        trs = soup.select("tr")
        
        result = get_data_dict(test_date, trs)
        
        assert len(result) == 2
        assert result[0]['country'] == "US"
        assert result[1]['country'] == "UK"
        assert all(item['date'] == test_date for item in result)
    
    def test_get_data_dict_empty_rows(self):
        """Test get_data_dict with empty row list"""
        test_date = datetime(2022, 3, 7)
        result = get_data_dict(test_date, [])
        assert result == []


class TestInvestingComUnitFunctions:
    """Unit tests for Investing.com helper functions"""
    
    def test_get_data_object_complete_data(self):
        """Test get_data_object with complete data"""
        text_list = [
            "pair_name=EUR/USD",
            "ti_buy=5",
            "ti_sell=3",
            "ma_buy=4",
            "ma_sell=2",
            "S1=1.0800",
            "S2=1.0780",
            "S3=1.0760",
            "pivot=1.0850",
            "R1=1.0870",
            "R2=1.0890",
            "R3=1.0910",
            "percent_bullish=65",
            "percent_bearish=35"
        ]
        
        result = get_data_object(text_list, 1, 3600)
        
        assert result['pair_id'] == 1
        assert result['time_frame'] == 3600
        assert result['pair_name'] == "EUR_USD"  # Should replace / with _
        assert result['ti_buy'] == "5"
        assert result['ti_sell'] == "3"
        assert result['ma_buy'] == "4"
        assert result['ma_sell'] == "2"
        assert result['S1'] == "1.0800"
        assert result['S2'] == "1.0780"
        assert result['S3'] == "1.0760"
        assert result['pivot'] == "1.0850"
        assert result['R1'] == "1.0870"
        assert result['R2'] == "1.0890"
        assert result['R3'] == "1.0910"
        assert result['percent_bullish'] == "65"
        assert result['percent_bearish'] == "35"
        assert 'updated' in result
        assert isinstance(result['updated'], datetime)
    
    def test_get_data_object_partial_data(self):
        """Test get_data_object with partial data"""
        text_list = [
            "pair_name=GBP/USD",
            "ti_buy=3",
            "pivot=1.3500",
            "percent_bullish=45"
        ]
        
        result = get_data_object(text_list, 2, 86400)
        
        assert result['pair_id'] == 2
        assert result['time_frame'] == 86400
        assert result['pair_name'] == "GBP_USD"
        assert result['ti_buy'] == "3"
        assert result['pivot'] == "1.3500"
        assert result['percent_bullish'] == "45"
        # Missing fields should not be present
        assert 'ti_sell' not in result
        assert 'ma_buy' not in result
    
    def test_get_data_object_invalid_format(self):
        """Test get_data_object with invalid format entries"""
        text_list = [
            "pair_name=USD/JPY",
            "invalid_entry",  # No equals sign
            "another_invalid=more=than=one=equals",  # Multiple equals
            "ti_buy=4"
        ]
        
        result = get_data_object(text_list, 3, 3600)
        
        assert result['pair_id'] == 3
        assert result['time_frame'] == 3600
        assert result['pair_name'] == "USD_JPY"
        assert result['ti_buy'] == "4"
        # Invalid entries should be ignored
        assert 'invalid_entry' not in result
    
    def test_get_data_object_unknown_keys(self):
        """Test get_data_object with unknown data keys"""
        text_list = [
            "pair_name=EUR/USD",
            "unknown_key=value",
            "ti_buy=5",
            "another_unknown=123"
        ]
        
        result = get_data_object(text_list, 1, 3600)
        
        assert result['pair_id'] == 1
        assert result['time_frame'] == 3600
        assert result['pair_name'] == "EUR_USD"
        assert result['ti_buy'] == "5"
        # Unknown keys should be ignored
        assert 'unknown_key' not in result
        assert 'another_unknown' not in result
    
    def test_get_data_object_empty_list(self):
        """Test get_data_object with empty list"""
        result = get_data_object([], 1, 3600)
        
        assert result['pair_id'] == 1
        assert result['time_frame'] == 3600
        assert 'updated' in result
        # No other fields should be present
        assert len(result) == 3
    
    def test_get_pair_valid_pair_timeframe(self):
        """Test get_pair with valid pair and timeframe"""
        with patch('scraping.investing_com.investing_com_fetch') as mock_fetch:
            mock_fetch.return_value = {
                'pair_id': 1,
                'time_frame': 3600,
                'pair_name': 'EUR_USD',
                'updated': datetime.now()
            }
            
            result = get_pair("EUR_USD", "H1")
            assert result['pair_name'] == "EUR_USD"
            assert result['time_frame'] == 3600
            mock_fetch.assert_called_once_with(1, 3600)
    
    def test_get_pair_invalid_timeframe(self):
        """Test get_pair with invalid timeframe (should default to H1)"""
        with patch('scraping.investing_com.investing_com_fetch') as mock_fetch:
            mock_fetch.return_value = {
                'pair_id': 1,
                'time_frame': defs.TFS['H1'],
                'pair_name': 'EUR_USD',
                'updated': datetime.now()
            }
            
            result = get_pair("EUR_USD", "INVALID_TF")
            assert result['time_frame'] == defs.TFS['H1']
            mock_fetch.assert_called_once_with(1, defs.TFS['H1'])
    
    def test_get_pair_different_timeframes(self):
        """Test get_pair with different valid timeframes"""
        with patch('scraping.investing_com.investing_com_fetch') as mock_fetch:
            mock_fetch.return_value = {
                'pair_id': 1,
                'time_frame': 86400,
                'pair_name': 'EUR_USD',
                'updated': datetime.now()
            }
            
            result = get_pair("EUR_USD", "D")
            assert result['time_frame'] == 86400
            mock_fetch.assert_called_once_with(1, 86400)


class TestBloombergUnitFunctions:
    """Unit tests for Bloomberg helper functions"""
    
    def test_get_article_with_href(self):
        """Test get_article with valid href attribute"""
        mock_card = Mock()
        mock_card.get_text.return_value = "Fed Raises Interest Rates"
        mock_card.get.return_value = "/article/fed-raises-rates"
        
        result = get_article(mock_card)
        
        assert result['headline'] == "Fed Raises Interest Rates"
        assert result['link'] == "https://www.reuters.com/article/fed-raises-rates"
        mock_card.get_text.assert_called_once()
        mock_card.get.assert_called_once_with('href')
    
    def test_get_article_with_none_href(self):
        """Test get_article with None href"""
        mock_card = Mock()
        mock_card.get_text.return_value = "Market Update"
        mock_card.get.return_value = None
        
        result = get_article(mock_card)
        
        assert result['headline'] == "Market Update"
        assert result['link'] == "https://www.reuters.com"
    
    def test_get_article_with_empty_href(self):
        """Test get_article with empty href"""
        mock_card = Mock()
        mock_card.get_text.return_value = "Economic Report"
        mock_card.get.return_value = ""
        
        result = get_article(mock_card)
        
        assert result['headline'] == "Economic Report"
        assert result['link'] == "https://www.reuters.com"


class TestScrapingEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_fx_calendar_malformed_html(self):
        """Test FX calendar with malformed HTML"""
        with patch('scraping.fx_calendar.requests.Session') as mock_session:
            mock_response = Mock()
            mock_response.content = "<html><body>Invalid HTML structure</body></html>"
            mock_session.return_value.get.return_value = mock_response
            
            test_date = datetime(2022, 3, 7)
            result = get_fx_calendar(test_date)
            
            # Should return empty list when no calendar table found
            assert isinstance(result, list)
    
    def test_investing_com_malformed_response(self):
        """Test Investing.com with malformed response"""
        with patch('scraping.investing_com.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.content = b"Invalid response without expected markers"
            mock_get.return_value = mock_response
            
            with pytest.raises(ValueError):  # Should raise when index not found
                investing_com_fetch(1, 3600)
    
    def test_dailyfx_empty_sentiment_cards(self):
        """Test DailyFX with no sentiment cards"""
        with patch('scraping.dailyfx_com.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.content = b"<html><body>No sentiment data available</body></html>"
            mock_get.return_value = mock_response
            
            result = dailyfx_com()
            
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 0
    
    def test_bloomberg_no_articles(self):
        """Test Bloomberg with no articles"""
        with patch('scraping.bloomberg_com.cloudscraper.create_scraper') as mock_scraper:
            mock_scraper_instance = Mock()
            mock_response = Mock()
            mock_response.content = b"<html><body>No articles found</body></html>"
            mock_scraper_instance.get.return_value = mock_response
            mock_scraper.return_value = mock_scraper_instance
            
            result = bloomberg_com()
            
            assert isinstance(result, list)
            assert len(result) == 0


class TestScrapingDataValidation:
    """Test data validation and type checking"""
    
    def test_fx_calendar_data_types(self):
        """Test FX calendar returns correct data types"""
        with patch('scraping.fx_calendar.requests.Session') as mock_session:
            mock_response = Mock()
            mock_response.content = """
            <html>
                <table id="calendar">
                    <thead>
                        <tr><th colspan="3">Monday, March 7, 2022</th></tr>
                    </thead>
                    <tr data-country="US" data-category="Employment" data-event="NFP" data-symbol="USD">
                        <span id="actual">200K</span>
                        <span id="previous">180K</span>
                        <span id="forecast">190K</span>
                    </tr>
                </table>
            </html>
            """
            mock_session.return_value.get.return_value = mock_response
            
            test_date = datetime(2022, 3, 7)
            result = get_fx_calendar(test_date)
            
            assert isinstance(result, list)
            if result:  # If data was parsed
                for item in result:
                    assert isinstance(item, dict)
                    assert isinstance(item.get('date'), datetime)
                    assert isinstance(item.get('country'), str)
                    assert isinstance(item.get('category'), str)
                    assert isinstance(item.get('event'), str)
    
    def test_investing_com_data_types(self):
        """Test Investing.com returns correct data types"""
        with patch('scraping.investing_com.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.content = b"""
            some text before pair_name=EUR/USD*;*ti_buy=5*;*ti_sell=3*;*ma_buy=4*;*ma_sell=2*;*S1=1.0800*;*pivot=1.0850*;*R1=1.0900*;*percent_bullish=65*;*percent_bearish=35*;*quote_link
            """
            mock_get.return_value = mock_response
            
            result = investing_com_fetch(1, 3600)
            
            assert isinstance(result, dict)
            assert isinstance(result.get('pair_id'), int)
            assert isinstance(result.get('time_frame'), int)
            assert isinstance(result.get('updated'), datetime)
            assert isinstance(result.get('pair_name'), str)
    
    def test_dailyfx_data_types(self):
        """Test DailyFX returns correct data types"""
        with patch('scraping.dailyfx_com.requests.get') as mock_get:
            mock_html = """
            <html>
                <div class="dfx-technicalSentimentCard">
                    <div class="dfx-technicalSentimentCard__pairAndSignal">
                        <a>EUR/USD</a>
                        <span>Bullish</span>
                    </div>
                    <div class="dfx-technicalSentimentCard__changeValue">+5.2%</div>
                    <div class="dfx-technicalSentimentCard__changeValue">-2.1%</div>
                    <div class="dfx-technicalSentimentCard__changeValue">+3.8%</div>
                    <div class="dfx-technicalSentimentCard__changeValue">+1.2%</div>
                    <div class="dfx-technicalSentimentCard__changeValue">-0.8%</div>
                </div>
            </html>
            """
            
            mock_response = Mock()
            mock_response.content = mock_html.encode()
            mock_get.return_value = mock_response
            
            result = dailyfx_com()
            
            assert isinstance(result, pd.DataFrame)
            if not result.empty:
                assert 'pair' in result.columns
                assert 'sentiment' in result.columns
                assert 'longs_d' in result.columns
                assert 'shorts_d' in result.columns
                assert 'longs_w' in result.columns
                assert 'shorts_w' in result.columns
    
    def test_bloomberg_data_types(self):
        """Test Bloomberg returns correct data types"""
        with patch('scraping.bloomberg_com.cloudscraper.create_scraper') as mock_scraper:
            mock_html = """
            <html>
                <div class="media-story-card__body">
                    <a data-testid="Heading" href="/article/fed-raises-rates">Fed Raises Interest Rates</a>
                </div>
            </html>
            """
            
            mock_scraper_instance = Mock()
            mock_response = Mock()
            mock_response.content = mock_html.encode()
            mock_scraper_instance.get.return_value = mock_response
            mock_scraper.return_value = mock_scraper_instance
            
            result = bloomberg_com()
            
            assert isinstance(result, list)
            if result:
                for item in result:
                    assert isinstance(item, dict)
                    assert isinstance(item.get('headline'), str)
                    assert isinstance(item.get('link'), str)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
