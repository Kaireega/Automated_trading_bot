"""
Comprehensive Unit Tests for ParameterOptimizer

This module provides comprehensive unit tests for the ParameterOptimizer class,
ensuring 100% test coverage and following TDD principles.

Author: Trading Bot Development Team
Version: 1.0.0
"""

import pytest
import sys
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock, mock_open
from decimal import Decimal
import asyncio

# Add project paths for imports
project_root = Path(__file__).parent.parent.parent.parent.parent.parent
src_path = project_root / "src"
sys.path.append(str(src_path))
sys.path.append(str(src_path / "trading_bot" / "src"))

# Import the modules under test
from trading_bot.src.backtesting.optimizer import ParameterOptimizer, OptimizationResult
from trading_bot.src.backtesting.backtest_engine import BacktestResult
from trading_bot.src.utils.config import Config


class TestOptimizationResult:
    """Test suite for OptimizationResult dataclass"""
    
    def test_optimization_result_creation(self):
        """Test OptimizationResult creation with all parameters"""
        best_params = {'param1': 0.5, 'param2': 1.0}
        best_result = BacktestResult()
        all_results = [(best_params, best_result)]
        
        result = OptimizationResult(
            best_parameters=best_params,
            best_score=1.5,
            best_result=best_result,
            all_results=all_results,
            optimization_method='grid_search',
            iterations=10,
            execution_time=5.5
        )
        
        assert result.best_parameters == best_params
        assert result.best_score == 1.5
        assert result.best_result == best_result
        assert result.all_results == all_results
        assert result.optimization_method == 'grid_search'
        assert result.iterations == 10
        assert result.execution_time == 5.5


class TestParameterOptimizer:
    """Test suite for ParameterOptimizer class"""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing"""
        config = Mock(spec=Config)
        config.trading = Mock()
        config.trading.risk_percentage = 2.0
        config.trading.max_position_size = 0.1
        config.trading.pairs = ['EUR_USD']
        config.trading.timeframes = ['M5']
        config.simulation = Mock()
        config.simulation.csv_dir = '/test/data'
        config.simulation.spread_pips = 0.1
        config.simulation.slippage_pips = 0.1
        config.oanda_api_key = None
        config.risk_management = Mock()
        config.risk_management.max_daily_loss = 100.0
        config.risk_management.max_position_size = 0.1
        config.risk_management.stop_loss_pips = 50
        config.risk_management.take_profit_pips = 100
        return config
    
    @pytest.fixture
    def mock_historical_data(self):
        """Create mock historical data for testing"""
        return {
            'EUR_USD': {
                'M5': [
                    {
                        'timestamp': datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                        'open': 1.1000,
                        'high': 1.1010,
                        'low': 1.0990,
                        'close': 1.1005,
                        'volume': 1000
                    }
                ]
            }
        }
    
    @pytest.fixture
    def mock_parameter_ranges(self):
        """Create mock parameter ranges for testing"""
        return {
            'risk_percentage': [1.0, 2.0, 3.0],
            'max_position_size': [0.05, 0.1, 0.15],
            'confidence_threshold': [0.5, 0.6, 0.7]
        }
    
    def test_initialization(self, mock_config):
        """Test ParameterOptimizer initialization"""
        optimizer = ParameterOptimizer(mock_config)
        
        assert optimizer.config == mock_config
        assert optimizer.logger is not None
        assert optimizer.performance_metrics is not None
    
    @pytest.mark.asyncio
    @patch('trading_bot.src.backtesting.optimizer.BacktestEngine')
    async def test_optimize_parameters_grid_search(self, mock_backtest_engine_class, mock_config, mock_historical_data, 
                                                   mock_parameter_ranges):
        """Test parameter optimization using grid search"""
        # Setup mock backtest results
        mock_result = BacktestResult()
        mock_result.sharpe_ratio = 1.5
        
        # Setup mock BacktestEngine
        mock_engine = Mock()
        mock_engine.run_simulation = AsyncMock(return_value=mock_result)
        mock_backtest_engine_class.return_value = mock_engine
        
        with patch('trading_bot.src.backtesting.optimizer.ParameterOptimizer._run_parallel_backtests') as mock_backtests:
            # Return tuples of (params, score, result) as expected by _find_best_result
            mock_backtests.return_value = [
                ({'param1': 0.5, 'param2': 1.0}, 1.5, mock_result),
                ({'param1': 0.6, 'param2': 1.1}, 1.2, mock_result)
            ]
            
            optimizer = ParameterOptimizer(mock_config)
            
            # Run optimization
            result = await optimizer.optimize_parameters(
                historical_data=mock_historical_data,
                start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                end_date=datetime(2024, 1, 31, tzinfo=timezone.utc),
                parameter_ranges=mock_parameter_ranges,
                optimization_target='sharpe_ratio',
                method='grid_search',
                max_iterations=10
            )
            
            # Verify result
            assert isinstance(result, OptimizationResult)
            assert result.optimization_method == 'grid_search'
            assert result.best_score == 1.5
            assert result.best_result == mock_result
            assert len(result.all_results) > 0
    
    @pytest.mark.asyncio
    async def test_optimize_parameters_random_search(self, mock_config, mock_historical_data, 
                                                     mock_parameter_ranges):
        """Test parameter optimization using random search"""
        with patch('trading_bot.src.backtesting.optimizer.ParameterOptimizer._run_backtest') as mock_backtest:
            # Setup mock backtest results
            mock_result = BacktestResult()
            mock_result.sharpe_ratio = 1.8
            mock_backtest.return_value = mock_result
            
            optimizer = ParameterOptimizer(mock_config)
            
            # Run optimization
            result = await optimizer.optimize_parameters(
                historical_data=mock_historical_data,
                start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                end_date=datetime(2024, 1, 31, tzinfo=timezone.utc),
                parameter_ranges=mock_parameter_ranges,
                optimization_target='sharpe_ratio',
                method='random_search',
                max_iterations=5
            )
            
            # Verify result
            assert isinstance(result, OptimizationResult)
            assert result.optimization_method == 'random_search'
            assert result.best_score == 1.8
            assert result.best_result == mock_result
    
    @pytest.mark.asyncio
    async def test_optimize_parameters_bayesian_optimization(self, mock_config, mock_historical_data, 
                                                             mock_parameter_ranges):
        """Test parameter optimization using Bayesian optimization"""
        with patch('trading_bot.src.backtesting.optimizer.ParameterOptimizer._run_backtest') as mock_backtest:
            # Setup mock backtest results
            mock_result = BacktestResult()
            mock_result.sharpe_ratio = 2.0
            mock_backtest.return_value = mock_result
            
            optimizer = ParameterOptimizer(mock_config)
            
            # Run optimization
            result = await optimizer.optimize_parameters(
                historical_data=mock_historical_data,
                start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                end_date=datetime(2024, 1, 31, tzinfo=timezone.utc),
                parameter_ranges=mock_parameter_ranges,
                optimization_target='sharpe_ratio',
                method='bayesian_optimization',
                max_iterations=5
            )
            
            # Verify result
            assert isinstance(result, OptimizationResult)
            assert result.optimization_method == 'bayesian_optimization'
            assert result.best_score == 2.0
            assert result.best_result == mock_result
    
    @pytest.mark.asyncio
    async def test_optimize_parameters_genetic_algorithm(self, mock_config, mock_historical_data, 
                                                         mock_parameter_ranges):
        """Test parameter optimization using genetic algorithm"""
        with patch('trading_bot.src.backtesting.optimizer.ParameterOptimizer._run_backtest') as mock_backtest:
            # Setup mock backtest results
            mock_result = BacktestResult()
            mock_result.sharpe_ratio = 1.7
            mock_backtest.return_value = mock_result
            
            optimizer = ParameterOptimizer(mock_config)
            
            # Run optimization
            result = await optimizer.optimize_parameters(
                historical_data=mock_historical_data,
                start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                end_date=datetime(2024, 1, 31, tzinfo=timezone.utc),
                parameter_ranges=mock_parameter_ranges,
                optimization_target='sharpe_ratio',
                method='genetic_algorithm',
                max_iterations=5
            )
            
            # Verify result
            assert isinstance(result, OptimizationResult)
            assert result.optimization_method == 'genetic_algorithm'
            assert result.best_score == 1.7
            assert result.best_result == mock_result
    
    @pytest.mark.asyncio
    async def test_optimize_parameters_invalid_method(self, mock_config, mock_historical_data, 
                                                      mock_parameter_ranges):
        """Test parameter optimization with invalid method"""
        optimizer = ParameterOptimizer(mock_config)
        
        # Run optimization with invalid method
        with pytest.raises(ValueError, match="Unsupported optimization method"):
            await optimizer.optimize_parameters(
                historical_data=mock_historical_data,
                start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                end_date=datetime(2024, 1, 31, tzinfo=timezone.utc),
                parameter_ranges=mock_parameter_ranges,
                optimization_target='sharpe_ratio',
                method='invalid_method',
                max_iterations=5
            )
    
    @pytest.mark.asyncio
    async def test_optimize_parameters_invalid_target(self, mock_config, mock_historical_data, 
                                                      mock_parameter_ranges):
        """Test parameter optimization with invalid optimization target"""
        optimizer = ParameterOptimizer(mock_config)
        
        # Run optimization with invalid target
        with pytest.raises(ValueError, match="Unsupported optimization target"):
            await optimizer.optimize_parameters(
                historical_data=mock_historical_data,
                start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                end_date=datetime(2024, 1, 31, tzinfo=timezone.utc),
                parameter_ranges=mock_parameter_ranges,
                optimization_target='invalid_target',
                method='grid_search',
                max_iterations=5
            )
    
    def test_generate_parameter_combinations_grid_search(self, mock_config, mock_parameter_ranges):
        """Test parameter combination generation for grid search"""
        optimizer = ParameterOptimizer(mock_config)
        
        combinations = list(optimizer._generate_parameter_combinations(
            mock_parameter_ranges, 'grid_search', max_combinations=10
        ))
        
        # Should generate all possible combinations (3^3 = 27, but limited to 10)
        assert len(combinations) <= 10
        assert len(combinations) > 0
        
        # Verify each combination has all required parameters
        for combo in combinations:
            assert 'risk_percentage' in combo
            assert 'max_position_size' in combo
            assert 'confidence_threshold' in combo
            assert combo['risk_percentage'] in mock_parameter_ranges['risk_percentage']
            assert combo['max_position_size'] in mock_parameter_ranges['max_position_size']
            assert combo['confidence_threshold'] in mock_parameter_ranges['confidence_threshold']
    
    def test_generate_parameter_combinations_random_search(self, mock_config, mock_parameter_ranges):
        """Test parameter combination generation for random search"""
        optimizer = ParameterOptimizer(mock_config)
        
        combinations = list(optimizer._generate_parameter_combinations(
            mock_parameter_ranges, 'random_search', max_combinations=5
        ))
        
        # Should generate random combinations
        assert len(combinations) == 5
        
        # Verify each combination has all required parameters
        for combo in combinations:
            assert 'risk_percentage' in combo
            assert 'max_position_size' in combo
            assert 'confidence_threshold' in combo
            assert combo['risk_percentage'] in mock_parameter_ranges['risk_percentage']
            assert combo['max_position_size'] in mock_parameter_ranges['max_position_size']
            assert combo['confidence_threshold'] in mock_parameter_ranges['confidence_threshold']
    
    def test_generate_parameter_combinations_invalid_method(self, mock_config, mock_parameter_ranges):
        """Test parameter combination generation with invalid method"""
        optimizer = ParameterOptimizer(mock_config)
        
        with pytest.raises(ValueError, match="Unsupported optimization method"):
            list(optimizer._generate_parameter_combinations(
                mock_parameter_ranges, 'invalid_method', max_combinations=5
            ))
    
    @pytest.mark.asyncio
    async def test_run_backtest_success(self, mock_config, mock_historical_data):
        """Test successful backtest execution"""
        with patch('trading_bot.src.backtesting.optimizer.BacktestEngine') as mock_engine_class:
            # Setup mock engine
            mock_engine = Mock()
            mock_engine.run_backtest = AsyncMock(return_value=BacktestResult())
            mock_engine_class.return_value = mock_engine
            
            optimizer = ParameterOptimizer(mock_config)
            
            # Test parameters
            test_params = {
                'risk_percentage': 2.0,
                'max_position_size': 0.1,
                'confidence_threshold': 0.6
            }
            
            # Run backtest
            result = await optimizer._run_backtest(
                historical_data=mock_historical_data,
                start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                end_date=datetime(2024, 1, 31, tzinfo=timezone.utc),
                parameters=test_params
            )
            
            # Verify result
            assert isinstance(result, BacktestResult)
            mock_engine.run_backtest.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_backtest_with_error(self, mock_config, mock_historical_data):
        """Test backtest execution with error"""
        with patch('trading_bot.src.backtesting.optimizer.BacktestEngine') as mock_engine_class:
            # Setup mock engine to raise exception
            mock_engine = Mock()
            mock_engine.run_backtest = AsyncMock(side_effect=Exception("Backtest failed"))
            mock_engine_class.return_value = mock_engine
            
            optimizer = ParameterOptimizer(mock_config)
            
            # Test parameters
            test_params = {
                'risk_percentage': 2.0,
                'max_position_size': 0.1,
                'confidence_threshold': 0.6
            }
            
            # Run backtest and expect exception
            with pytest.raises(Exception, match="Backtest failed"):
                await optimizer._run_backtest(
                    historical_data=mock_historical_data,
                    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                    end_date=datetime(2024, 1, 31, tzinfo=timezone.utc),
                    parameters=test_params
                )
    
    def test_evaluate_parameters_success(self, mock_config):
        """Test parameter evaluation with successful backtest"""
        optimizer = ParameterOptimizer(mock_config)
        
        # Mock backtest result
        mock_result = BacktestResult()
        mock_result.sharpe_ratio = 1.5
        mock_result.total_return_pct = 10.0
        mock_result.max_drawdown_pct = 5.0
        mock_result.win_rate = 60.0
        
        # Test parameters
        test_params = {
            'risk_percentage': 2.0,
            'max_position_size': 0.1,
            'confidence_threshold': 0.6
        }
        
        # Evaluate parameters
        score = optimizer._evaluate_parameters(test_params, mock_result, 'sharpe_ratio')
        
        # Verify score
        assert score == 1.5
    
    def test_evaluate_parameters_different_targets(self, mock_config):
        """Test parameter evaluation with different optimization targets"""
        optimizer = ParameterOptimizer(mock_config)
        
        # Mock backtest result
        mock_result = BacktestResult()
        mock_result.sharpe_ratio = 1.5
        mock_result.total_return_pct = 10.0
        mock_result.max_drawdown_pct = 5.0
        mock_result.win_rate = 60.0
        
        # Test parameters
        test_params = {
            'risk_percentage': 2.0,
            'max_position_size': 0.1,
            'confidence_threshold': 0.6
        }
        
        # Test different targets
        assert optimizer._evaluate_parameters(test_params, mock_result, 'sharpe_ratio') == 1.5
        assert optimizer._evaluate_parameters(test_params, mock_result, 'total_return_pct') == 10.0
        assert optimizer._evaluate_parameters(test_params, mock_result, 'max_drawdown_pct') == -5.0  # Negative for minimization
        assert optimizer._evaluate_parameters(test_params, mock_result, 'win_rate') == 60.0
    
    def test_evaluate_parameters_invalid_target(self, mock_config):
        """Test parameter evaluation with invalid optimization target"""
        optimizer = ParameterOptimizer(mock_config)
        
        # Mock backtest result
        mock_result = BacktestResult()
        
        # Test parameters
        test_params = {
            'risk_percentage': 2.0,
            'max_position_size': 0.1,
            'confidence_threshold': 0.6
        }
        
        # Test invalid target
        with pytest.raises(ValueError, match="Unsupported optimization target"):
            optimizer._evaluate_parameters(test_params, mock_result, 'invalid_target')
    
    def test_validate_parameters_success(self, mock_config):
        """Test parameter validation with valid parameters"""
        optimizer = ParameterOptimizer(mock_config)
        
        # Valid parameters
        valid_params = {
            'risk_percentage': 2.0,
            'max_position_size': 0.1,
            'confidence_threshold': 0.6
        }
        
        # Should not raise exception
        optimizer._validate_parameters(valid_params)
    
    def test_validate_parameters_missing_required(self, mock_config):
        """Test parameter validation with missing required parameters"""
        optimizer = ParameterOptimizer(mock_config)
        
        # Missing required parameters
        invalid_params = {
            'risk_percentage': 2.0
            # Missing max_position_size and confidence_threshold
        }
        
        # Should raise exception
        with pytest.raises(ValueError, match="Missing required parameters"):
            optimizer._validate_parameters(invalid_params)
    
    def test_validate_parameters_invalid_values(self, mock_config):
        """Test parameter validation with invalid parameter values"""
        optimizer = ParameterOptimizer(mock_config)
        
        # Invalid parameter values
        invalid_params = {
            'risk_percentage': -1.0,  # Negative risk percentage
            'max_position_size': 0.1,
            'confidence_threshold': 0.6
        }
        
        # Should raise exception
        with pytest.raises(ValueError, match="Invalid parameter values"):
            optimizer._validate_parameters(invalid_params)
    
    def test_save_optimization_results(self, mock_config):
        """Test saving optimization results to file"""
        with patch('builtins.open', mock_open()) as mock_file, \
             patch('json.dump') as mock_json_dump:
            
            optimizer = ParameterOptimizer(mock_config)
            
            # Create test result
            result = OptimizationResult(
                best_parameters={'param1': 0.5},
                best_score=1.5,
                best_result=BacktestResult(),
                all_results=[],
                optimization_method='grid_search',
                iterations=10,
                execution_time=5.5
            )
            
            # Save results
            optimizer.save_optimization_results(result, '/test/path/results.json')
            
            # Verify file operations
            mock_file.assert_called_once_with('/test/path/results.json', 'w')
            mock_json_dump.assert_called_once()
    
    def test_load_optimization_results(self, mock_config):
        """Test loading optimization results from file"""
        with patch('builtins.open', mock_open(read_data='{"best_parameters": {"param1": 0.5}}')), \
             patch('json.load') as mock_json_load:
            
            # Mock JSON data
            mock_json_load.return_value = {
                'best_parameters': {'param1': 0.5},
                'best_score': 1.5,
                'optimization_method': 'grid_search',
                'iterations': 10,
                'execution_time': 5.5
            }
            
            optimizer = ParameterOptimizer(mock_config)
            
            # Load results
            result = optimizer.load_optimization_results('/test/path/results.json')
            
            # Verify result
            assert result is not None
            assert result['best_parameters'] == {'param1': 0.5}
            assert result['best_score'] == 1.5
    
    def test_load_optimization_results_file_not_found(self, mock_config):
        """Test loading optimization results when file doesn't exist"""
        with patch('builtins.open', side_effect=FileNotFoundError):
            optimizer = ParameterOptimizer(mock_config)
            
            # Should return None when file doesn't exist
            result = optimizer.load_optimization_results('/nonexistent/path/results.json')
            assert result is None


class TestParameterOptimizerEdgeCases:
    """Test edge cases and error conditions for ParameterOptimizer"""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing"""
        config = Mock(spec=Config)
        config.trading = Mock()
        config.trading.risk_percentage = 2.0
        config.trading.max_position_size = 0.1
        config.trading.pairs = ['EUR_USD']
        config.trading.timeframes = ['M5']
        config.simulation = Mock()
        config.simulation.csv_dir = '/test/data'
        config.simulation.spread_pips = 0.1
        config.simulation.slippage_pips = 0.1
        config.oanda_api_key = None
        config.risk_management = Mock()
        config.risk_management.max_daily_loss = 100.0
        config.risk_management.max_position_size = 0.1
        config.risk_management.stop_loss_pips = 50
        config.risk_management.take_profit_pips = 100
        return config
    
    def test_initialization_with_none_config(self):
        """Test initialization with None configuration"""
        with pytest.raises(AttributeError):
            ParameterOptimizer(None)
    
    @pytest.mark.asyncio
    async def test_optimize_parameters_with_empty_historical_data(self, mock_config):
        """Test optimization with empty historical data"""
        optimizer = ParameterOptimizer(mock_config)
        
        empty_data = {}
        parameter_ranges = {
            'risk_percentage': [1.0, 2.0],
            'max_position_size': [0.05, 0.1]
        }
        
        # Should handle empty data gracefully
        with pytest.raises(ValueError, match="No historical data provided"):
            await optimizer.optimize_parameters(
                historical_data=empty_data,
                start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                end_date=datetime(2024, 1, 31, tzinfo=timezone.utc),
                parameter_ranges=parameter_ranges,
                optimization_target='sharpe_ratio',
                method='grid_search',
                max_iterations=5
            )
    
    @pytest.mark.asyncio
    async def test_optimize_parameters_with_empty_parameter_ranges(self, mock_config):
        """Test optimization with empty parameter ranges"""
        optimizer = ParameterOptimizer(mock_config)
        
        historical_data = {
            'EUR_USD': {
                'M5': [{'timestamp': datetime.now(), 'open': 1.1, 'high': 1.11, 'low': 1.09, 'close': 1.105}]
            }
        }
        empty_ranges = {}
        
        # Should handle empty ranges gracefully
        with pytest.raises(ValueError, match="No parameter ranges provided"):
            await optimizer.optimize_parameters(
                historical_data=historical_data,
                start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                end_date=datetime(2024, 1, 31, tzinfo=timezone.utc),
                parameter_ranges=empty_ranges,
                optimization_target='sharpe_ratio',
                method='grid_search',
                max_iterations=5
            )
    
    @pytest.mark.asyncio
    async def test_optimize_parameters_with_invalid_date_range(self, mock_config):
        """Test optimization with invalid date range"""
        optimizer = ParameterOptimizer(mock_config)
        
        historical_data = {
            'EUR_USD': {
                'M5': [{'timestamp': datetime.now(), 'open': 1.1, 'high': 1.11, 'low': 1.09, 'close': 1.105}]
            }
        }
        parameter_ranges = {
            'risk_percentage': [1.0, 2.0],
            'max_position_size': [0.05, 0.1]
        }
        
        # Should handle invalid date range gracefully
        with pytest.raises(ValueError, match="Invalid date range"):
            await optimizer.optimize_parameters(
                historical_data=historical_data,
                start_date=datetime(2024, 1, 31, tzinfo=timezone.utc),  # End before start
                end_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                parameter_ranges=parameter_ranges,
                optimization_target='sharpe_ratio',
                method='grid_search',
                max_iterations=5
            )
    
    def test_generate_parameter_combinations_with_empty_ranges(self, mock_config):
        """Test parameter combination generation with empty ranges"""
        optimizer = ParameterOptimizer(mock_config)
        
        empty_ranges = {}
        
        # Should handle empty ranges gracefully
        with pytest.raises(ValueError, match="No parameter ranges provided"):
            list(optimizer._generate_parameter_combinations(
                empty_ranges, 'grid_search', max_combinations=5
            ))
    
    def test_generate_parameter_combinations_with_zero_max_combinations(self, mock_config):
        """Test parameter combination generation with zero max combinations"""
        optimizer = ParameterOptimizer(mock_config)
        
        parameter_ranges = {
            'risk_percentage': [1.0, 2.0],
            'max_position_size': [0.05, 0.1]
        }
        
        # Should return empty list
        combinations = list(optimizer._generate_parameter_combinations(
            parameter_ranges, 'grid_search', max_combinations=0
        ))
        
        assert combinations == []
    
    def test_evaluate_parameters_with_none_result(self, mock_config):
        """Test parameter evaluation with None result"""
        optimizer = ParameterOptimizer(mock_config)
        
        test_params = {
            'risk_percentage': 2.0,
            'max_position_size': 0.1,
            'confidence_threshold': 0.6
        }
        
        # Should handle None result gracefully
        with pytest.raises(ValueError, match="Backtest result is None"):
            optimizer._evaluate_parameters(test_params, None, 'sharpe_ratio')
    
    def test_validate_parameters_with_none_params(self, mock_config):
        """Test parameter validation with None parameters"""
        optimizer = ParameterOptimizer(mock_config)
        
        # Should handle None parameters gracefully
        with pytest.raises(ValueError, match="Parameters cannot be None"):
            optimizer._validate_parameters(None)
    
    def test_validate_parameters_with_empty_params(self, mock_config):
        """Test parameter validation with empty parameters"""
        optimizer = ParameterOptimizer(mock_config)
        
        # Should handle empty parameters gracefully
        with pytest.raises(ValueError, match="Parameters cannot be empty"):
            optimizer._validate_parameters({})
    
    def test_save_optimization_results_with_none_result(self, mock_config):
        """Test saving optimization results with None result"""
        optimizer = ParameterOptimizer(mock_config)
        
        # Should handle None result gracefully
        with pytest.raises(ValueError, match="Optimization result cannot be None"):
            optimizer.save_optimization_results(None, '/test/path/results.json')
    
    def test_save_optimization_results_with_none_path(self, mock_config):
        """Test saving optimization results with None path"""
        optimizer = ParameterOptimizer(mock_config)
        
        result = OptimizationResult(
            best_parameters={'param1': 0.5},
            best_score=1.5,
            best_result=BacktestResult(),
            all_results=[],
            optimization_method='grid_search',
            iterations=10,
            execution_time=5.5
        )
        
        # Should handle None path gracefully
        with pytest.raises(ValueError, match="File path cannot be None or empty"):
            optimizer.save_optimization_results(result, None)
    
    def test_load_optimization_results_with_none_path(self, mock_config):
        """Test loading optimization results with None path"""
        optimizer = ParameterOptimizer(mock_config)
        
        # Should handle None path gracefully
        with pytest.raises(ValueError, match="File path cannot be None or empty"):
            optimizer.load_optimization_results(None)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

