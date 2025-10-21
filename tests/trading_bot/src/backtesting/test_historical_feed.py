"""
Comprehensive Unit Tests for HistoricalDataFeed

This module provides comprehensive unit tests for the HistoricalDataFeed class,
ensuring 100% test coverage and following TDD principles.

Author: Trading Bot Development Team
Version: 1.0.0
"""

import pytest
import sys
import os
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock, patch, mock_open
import pandas as pd
import tempfile
import pickle

# Add project paths for imports
project_root = Path(__file__).parent.parent.parent.parent.parent.parent
src_path = project_root / "src"
sys.path.append(str(src_path))
sys.path.append(str(src_path / "trading_bot" / "src"))

# Import the modules under test
from trading_bot.src.backtesting.feeds import HistoricalDataFeed
from trading_bot.src.core.models import CandleData, TimeFrame


class TestHistoricalDataFeed:
    """Test suite for HistoricalDataFeed class"""
    
    def test_initialization(self):
        """Test HistoricalDataFeed initialization"""
        feed = HistoricalDataFeed("/test/data")
        
        assert feed.data_dir == Path("/test/data")
        assert feed.data == {}
    
    def test_initialization_with_path_object(self):
        """Test initialization with Path object"""
        data_path = Path("/test/data")
        feed = HistoricalDataFeed(data_path)
        
        assert feed.data_dir == data_path
        assert feed.data == {}
    
    @patch('pandas.read_pickle')
    def test_load_pair_tf_success(self, mock_read_pickle):
        """Test successful loading of pair and timeframe data"""
        # Create mock DataFrame
        mock_df = pd.DataFrame({
            'time': [
                pd.Timestamp('2024-01-01 12:00:00', tz='UTC'),
                pd.Timestamp('2024-01-01 12:05:00', tz='UTC')
            ],
            'mid_o': [1.1000, 1.1005],
            'mid_h': [1.1010, 1.1015],
            'mid_l': [1.0990, 1.0995],
            'mid_c': [1.1005, 1.1010],
            'volume': [1000, 1100]
        })
        mock_read_pickle.return_value = mock_df
        
        # Create temporary file
        with tempfile.TemporaryDirectory() as temp_dir:
            feed = HistoricalDataFeed(temp_dir)
            
            # Create the expected file
            file_path = Path(temp_dir) / "EUR_USD_M5.pkl"
            with open(file_path, 'wb') as f:
                pickle.dump(mock_df, f)
            
            # Test loading
            candles = feed._load_pair_tf("EUR_USD", TimeFrame.M5)
            
            # Verify results
            assert len(candles) == 2
            assert isinstance(candles[0], CandleData)
            assert candles[0].pair == "EUR_USD"
            assert candles[0].timeframe == TimeFrame.M5
            assert candles[0].open == Decimal('1.1000')
            assert candles[0].high == Decimal('1.1010')
            assert candles[0].low == Decimal('1.0990')
            assert candles[0].close == Decimal('1.1005')
            assert candles[0].volume == Decimal('1000')
            assert candles[0].timestamp == datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    def test_load_pair_tf_file_not_exists(self):
        """Test loading when file doesn't exist"""
        with tempfile.TemporaryDirectory() as temp_dir:
            feed = HistoricalDataFeed(temp_dir)
            
            candles = feed._load_pair_tf("EUR_USD", TimeFrame.M5)
            
            assert candles == []
    
    @patch('pandas.read_pickle')
    def test_load_pair_tf_with_column_mapping(self, mock_read_pickle):
        """Test loading with column name mapping"""
        # Create mock DataFrame with different column names
        mock_df = pd.DataFrame({
            'time': [pd.Timestamp('2024-01-01 12:00:00', tz='UTC')],
            'open': [1.1000],    # Should map to mid_o
            'high': [1.1010],    # Should map to mid_h
            'low': [1.0990],     # Should map to mid_l
            'close': [1.1005],   # Should map to mid_c
            'volume': [1000]
        })
        mock_read_pickle.return_value = mock_df
        
        with tempfile.TemporaryDirectory() as temp_dir:
            feed = HistoricalDataFeed(temp_dir)
            
            # Create the file
            file_path = Path(temp_dir) / "EUR_USD_M5.pkl"
            with open(file_path, 'wb') as f:
                pickle.dump(mock_df, f)
            
            # Test loading
            candles = feed._load_pair_tf("EUR_USD", TimeFrame.M5)
            
            # Verify column mapping worked
            assert len(candles) == 1
            assert candles[0].open == Decimal('1.1000')
            assert candles[0].high == Decimal('1.1010')
            assert candles[0].low == Decimal('1.0990')
            assert candles[0].close == Decimal('1.1005')
    
    @patch('pandas.read_pickle')
    def test_load_pair_tf_without_volume(self, mock_read_pickle):
        """Test loading without volume column"""
        # Create mock DataFrame without volume
        mock_df = pd.DataFrame({
            'time': [pd.Timestamp('2024-01-01 12:00:00', tz='UTC')],
            'mid_o': [1.1000],
            'mid_h': [1.1010],
            'mid_l': [1.0990],
            'mid_c': [1.1005]
        })
        mock_read_pickle.return_value = mock_df
        
        with tempfile.TemporaryDirectory() as temp_dir:
            feed = HistoricalDataFeed(temp_dir)
            
            # Create the file
            file_path = Path(temp_dir) / "EUR_USD_M5.pkl"
            with open(file_path, 'wb') as f:
                pickle.dump(mock_df, f)
            
            # Test loading
            candles = feed._load_pair_tf("EUR_USD", TimeFrame.M5)
            
            # Verify volume is None
            assert len(candles) == 1
            assert candles[0].volume is None
    
    @patch('pandas.read_pickle')
    def test_load_pair_tf_with_missing_columns(self, mock_read_pickle):
        """Test loading with missing required columns"""
        # Create mock DataFrame with missing columns
        mock_df = pd.DataFrame({
            'time': [pd.Timestamp('2024-01-01 12:00:00', tz='UTC')],
            'mid_o': [1.1000]
            # Missing mid_h, mid_l, mid_c
        })
        mock_read_pickle.return_value = mock_df
        
        with tempfile.TemporaryDirectory() as temp_dir:
            feed = HistoricalDataFeed(temp_dir)
            
            # Create the file
            file_path = Path(temp_dir) / "EUR_USD_M5.pkl"
            with open(file_path, 'wb') as f:
                pickle.dump(mock_df, f)
            
            # Test loading - should handle missing columns gracefully
            candles = feed._load_pair_tf("EUR_USD", TimeFrame.M5)
            
            # Should still create candle but with None values for missing columns
            assert len(candles) == 1
            assert candles[0].open == Decimal('1.1000')
            assert candles[0].high is None or candles[0].high == Decimal('0')
            assert candles[0].low is None or candles[0].low == Decimal('0')
            assert candles[0].close is None or candles[0].close == Decimal('0')
    
    def test_load_success(self):
        """Test successful loading of data"""
        with tempfile.TemporaryDirectory() as temp_dir:
            feed = HistoricalDataFeed(temp_dir)
            
            # Mock the _load_pair_tf method
            mock_candles = [
                CandleData(
                    timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                    open=Decimal('1.1000'),
                    high=Decimal('1.1010'),
                    low=Decimal('1.0990'),
                    close=Decimal('1.1005'),
                    volume=Decimal('1000'),
                    pair='EUR_USD',
                    timeframe=TimeFrame.M5
                )
            ]
            feed._load_pair_tf = Mock(return_value=mock_candles)
            
            # Test loading
            feed.load(["EUR_USD"], [TimeFrame.M5])
            
            # Verify results
            feed._load_pair_tf.assert_called_once_with("EUR_USD", TimeFrame.M5)
            assert "EUR_USD" in feed.data
            assert TimeFrame.M5 in feed.data["EUR_USD"]
    
    def test_get_pair_timeframes(self):
        """Test getting pair timeframes"""
        with tempfile.TemporaryDirectory() as temp_dir:
            feed = HistoricalDataFeed(temp_dir)
            
            # Mock the _load_pair_tf method
            mock_candles = [
                CandleData(
                    timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                    open=Decimal('1.1000'),
                    high=Decimal('1.1010'),
                    low=Decimal('1.0990'),
                    close=Decimal('1.1005'),
                    volume=Decimal('1000'),
                    pair='EUR_USD',
                    timeframe=TimeFrame.M5
                )
            ]
            feed._load_pair_tf = Mock(return_value=mock_candles)
            
            # Load data
            feed.load(["EUR_USD"], [TimeFrame.M5])
            
            # Get pair timeframes
            timeframes = feed.get_pair_timeframes("EUR_USD")
            
            # Verify results
            assert TimeFrame.M5 in timeframes
            assert timeframes[TimeFrame.M5] == mock_candles
    
    def test_min_length_across_timeframes(self):
        """Test getting minimum length across timeframes"""
        with tempfile.TemporaryDirectory() as temp_dir:
            feed = HistoricalDataFeed(temp_dir)
            
            # Mock different data for different timeframes
            m5_candles = [Mock() for _ in range(100)]  # 100 candles
            m15_candles = [Mock() for _ in range(50)]  # 50 candles
            
            feed._load_pair_tf = Mock(side_effect=lambda pair, tf: m5_candles if tf == TimeFrame.M5 else m15_candles)
            
            # Load data
            feed.load(["EUR_USD"], [TimeFrame.M5, TimeFrame.M15])
            
            # Get minimum length
            min_length = feed.min_length_across_timeframes("EUR_USD")
            
            # Verify results
            assert min_length == 50  # Minimum of 100 and 50
    
    def test_step_candles(self):
        """Test stepping through candles"""
        with tempfile.TemporaryDirectory() as temp_dir:
            feed = HistoricalDataFeed(temp_dir)
            
            # Mock candles
            m5_candles = [Mock() for _ in range(100)]
            m15_candles = [Mock() for _ in range(50)]
            
            feed._load_pair_tf = Mock(side_effect=lambda pair, tf: m5_candles if tf == TimeFrame.M5 else m15_candles)
            
            # Load data
            feed.load(["EUR_USD"], [TimeFrame.M5, TimeFrame.M15])
            
            # Step through candles
            step_result = feed.step_candles("EUR_USD", 10)
            
            # Verify results
            assert TimeFrame.M5 in step_result
            assert TimeFrame.M15 in step_result
            assert len(step_result[TimeFrame.M5]) == 11  # 0 to 10 inclusive
            assert len(step_result[TimeFrame.M15]) == 11  # 0 to 10 inclusive
    
    def test_empty_data_handling(self):
        """Test handling when no data is available"""
        with tempfile.TemporaryDirectory() as temp_dir:
            feed = HistoricalDataFeed(temp_dir)
            
            # Mock empty data
            feed._load_pair_tf = Mock(return_value=[])
            
            # Load empty data
            feed.load(["EUR_USD"], [TimeFrame.M5])
            
            # Verify results
            assert "EUR_USD" in feed.data
            assert TimeFrame.M5 in feed.data["EUR_USD"]
            assert feed.data["EUR_USD"][TimeFrame.M5] == []
    
    def test_data_structure(self):
        """Test data structure organization"""
        with tempfile.TemporaryDirectory() as temp_dir:
            feed = HistoricalDataFeed(temp_dir)
            
            # Mock candles
            mock_candles = [Mock() for _ in range(10)]
            feed._load_pair_tf = Mock(return_value=mock_candles)
            
            # Load data
            feed.load(["EUR_USD", "GBP_USD"], [TimeFrame.M5, TimeFrame.M15])
            
            # Verify data structure
            assert "EUR_USD" in feed.data
            assert "GBP_USD" in feed.data
            assert TimeFrame.M5 in feed.data["EUR_USD"]
            assert TimeFrame.M15 in feed.data["EUR_USD"]
            assert TimeFrame.M5 in feed.data["GBP_USD"]
            assert TimeFrame.M15 in feed.data["GBP_USD"]
            
            # Verify all data is the same mock candles
            for pair in ["EUR_USD", "GBP_USD"]:
                for tf in [TimeFrame.M5, TimeFrame.M15]:
                    assert feed.data[pair][tf] == mock_candles


class TestHistoricalDataFeedEdgeCases:
    """Test edge cases and error conditions for HistoricalDataFeed"""
    
    def test_initialization_with_nonexistent_directory(self):
        """Test initialization with non-existent directory"""
        feed = HistoricalDataFeed("/nonexistent/directory")
        
        assert feed.data_dir == Path("/nonexistent/directory")
        assert feed.data == {}
    
    @patch('pandas.read_pickle')
    def test_load_pair_tf_with_corrupted_file(self, mock_read_pickle):
        """Test loading with corrupted pickle file"""
        # Mock pandas to raise an exception
        mock_read_pickle.side_effect = Exception("Corrupted pickle file")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            feed = HistoricalDataFeed(temp_dir)
            
            # Create a file (even if corrupted)
            file_path = Path(temp_dir) / "EUR_USD_M5.pkl"
            with open(file_path, 'w') as f:
                f.write("corrupted data")
            
            # Test loading - should handle exception gracefully
            with pytest.raises(Exception, match="Corrupted pickle file"):
                feed._load_pair_tf("EUR_USD", TimeFrame.M5)
    
    @patch('pandas.read_pickle')
    def test_load_pair_tf_with_invalid_dataframe(self, mock_read_pickle):
        """Test loading with invalid DataFrame structure"""
        # Mock pandas to return invalid data
        mock_read_pickle.return_value = "not a dataframe"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            feed = HistoricalDataFeed(temp_dir)
            
            # Create the file
            file_path = Path(temp_dir) / "EUR_USD_M5.pkl"
            with open(file_path, 'wb') as f:
                pickle.dump("invalid data", f)
            
            # Test loading - should handle gracefully
            candles = feed._load_pair_tf("EUR_USD", TimeFrame.M5)
            
            # Should return empty list or handle gracefully
            assert candles == []
    
    @patch('pandas.read_pickle')
    def test_load_pair_tf_with_malformed_timestamps(self, mock_read_pickle):
        """Test loading with malformed timestamp data"""
        # Create mock DataFrame with malformed timestamps
        mock_df = pd.DataFrame({
            'time': ['invalid_timestamp', None, 12345],
            'mid_o': [1.1000, 1.1005, 1.1010],
            'mid_h': [1.1010, 1.1015, 1.1020],
            'mid_l': [1.0990, 1.0995, 1.1000],
            'mid_c': [1.1005, 1.1010, 1.1015]
        })
        mock_read_pickle.return_value = mock_df
        
        with tempfile.TemporaryDirectory() as temp_dir:
            feed = HistoricalDataFeed(temp_dir)
            
            # Create the file
            file_path = Path(temp_dir) / "EUR_USD_M5.pkl"
            with open(file_path, 'wb') as f:
                pickle.dump(mock_df, f)
            
            # Test loading - should handle malformed timestamps
            candles = feed._load_pair_tf("EUR_USD", TimeFrame.M5)
            
            # Should handle gracefully (might skip invalid rows or use defaults)
            assert isinstance(candles, list)
    
    def test_get_candles_with_special_characters_in_pair(self):
        """Test getting candles with special characters in pair name"""
        with tempfile.TemporaryDirectory() as temp_dir:
            feed = HistoricalDataFeed(temp_dir)
            
            # Mock the _load_pair_tf method
            feed._load_pair_tf = Mock(return_value=[])
            
            # Test with special characters
            candles = feed.get_candles("EUR-USD", TimeFrame.M5)
            
            # Should handle gracefully
            assert candles == []
            feed._load_pair_tf.assert_called_once_with("EUR-USD", TimeFrame.M5)
    
    def test_get_candles_with_empty_pair_name(self):
        """Test getting candles with empty pair name"""
        with tempfile.TemporaryDirectory() as temp_dir:
            feed = HistoricalDataFeed(temp_dir)
            
            # Mock the _load_pair_tf method
            feed._load_pair_tf = Mock(return_value=[])
            
            # Test with empty pair name
            candles = feed.get_candles("", TimeFrame.M5)
            
            # Should handle gracefully
            assert candles == []
            feed._load_pair_tf.assert_called_once_with("", TimeFrame.M5)
    
    def test_clear_cache_when_empty(self):
        """Test clearing cache when it's already empty"""
        with tempfile.TemporaryDirectory() as temp_dir:
            feed = HistoricalDataFeed(temp_dir)
            
            # Clear empty cache
            feed.clear_cache()
            
            # Should not raise any errors
            assert feed.data == {}
    
    def test_get_available_pairs_with_no_files(self):
        """Test getting available pairs when no files exist"""
        with tempfile.TemporaryDirectory() as temp_dir:
            feed = HistoricalDataFeed(temp_dir)
            
            # Test getting available pairs
            pairs = feed.get_available_pairs()
            
            # Should return empty list
            assert pairs == []
    
    def test_get_available_timeframes_with_no_files(self):
        """Test getting available timeframes when no files exist"""
        with tempfile.TemporaryDirectory() as temp_dir:
            feed = HistoricalDataFeed(temp_dir)
            
            # Test getting available timeframes
            timeframes = feed.get_available_timeframes("EUR_USD")
            
            # Should return empty list
            assert timeframes == []
    
    def test_get_available_pairs_with_malformed_filenames(self):
        """Test getting available pairs with malformed filenames"""
        with tempfile.TemporaryDirectory() as temp_dir:
            feed = HistoricalDataFeed(temp_dir)
            
            # Create files with malformed names
            malformed_files = [
                "EUR_USD.pkl",  # Missing timeframe
                "M5.pkl",       # Missing pair
                "EUR_USD_M5",   # Missing extension
                "EUR_USD_M5_H1.pkl",  # Too many parts
                ".pkl"          # Empty name
            ]
            
            for file_name in malformed_files:
                file_path = Path(temp_dir) / file_name
                with open(file_path, 'wb') as f:
                    pickle.dump(pd.DataFrame(), f)
            
            # Test getting available pairs
            pairs = feed.get_available_pairs()
            
            # Should only return valid pairs
            assert pairs == []  # None of the malformed files should be valid


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
