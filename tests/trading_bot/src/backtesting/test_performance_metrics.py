"""
Comprehensive Unit Tests for PerformanceMetrics

This module provides comprehensive unit tests for the PerformanceMetrics class,
ensuring 100% test coverage and following TDD principles.

Author: Trading Bot Development Team
Version: 1.0.0
"""

import pytest
import sys
import os
from pathlib import Path
from decimal import Decimal
import numpy as np
import pandas as pd

# Add project paths for imports
project_root = Path(__file__).parent.parent.parent.parent.parent.parent
src_path = project_root / "src"
sys.path.append(str(src_path))
sys.path.append(str(src_path / "trading_bot" / "src"))

# Import the modules under test
from trading_bot.src.backtesting.performance_metrics import PerformanceMetrics


class TestPerformanceMetrics:
    """Test suite for PerformanceMetrics class"""
    
    def test_initialization(self):
        """Test PerformanceMetrics initialization"""
        metrics = PerformanceMetrics()
        assert metrics is not None
    
    def test_calculate_returns_empty_curve(self):
        """Test returns calculation with empty equity curve"""
        metrics = PerformanceMetrics()
        
        returns = metrics.calculate_returns([])
        
        assert returns == []
    
    def test_calculate_returns_single_value(self):
        """Test returns calculation with single value"""
        metrics = PerformanceMetrics()
        
        returns = metrics.calculate_returns([10000.0])
        
        assert returns == []
    
    def test_calculate_returns_normal_curve(self):
        """Test returns calculation with normal equity curve"""
        metrics = PerformanceMetrics()
        
        equity_curve = [10000.0, 10100.0, 10050.0, 10200.0, 10150.0]
        returns = metrics.calculate_returns(equity_curve)
        
        expected_returns = [0.01, -0.00495, 0.01493, -0.00490]
        assert len(returns) == 4
        for i, expected in enumerate(expected_returns):
            assert abs(returns[i] - expected) < 0.0001
    
    def test_calculate_returns_with_zero_values(self):
        """Test returns calculation with zero values in curve"""
        metrics = PerformanceMetrics()
        
        equity_curve = [10000.0, 0.0, 5000.0, 7500.0]
        returns = metrics.calculate_returns(equity_curve)
        
        expected_returns = [-1.0, 0.0, 0.5]  # -100%, 0%, 50%
        assert len(returns) == 3
        for i, expected in enumerate(expected_returns):
            assert abs(returns[i] - expected) < 0.0001
    
    def test_calculate_returns_with_negative_values(self):
        """Test returns calculation with negative values"""
        metrics = PerformanceMetrics()
        
        equity_curve = [10000.0, 9500.0, 9000.0, 11000.0]
        returns = metrics.calculate_returns(equity_curve)
        
        expected_returns = [-0.05, -0.0526, 0.2222]
        assert len(returns) == 3
        for i, expected in enumerate(expected_returns):
            assert abs(returns[i] - expected) < 0.0001
    
    def test_calculate_sharpe_ratio_empty_returns(self):
        """Test Sharpe ratio calculation with empty returns"""
        metrics = PerformanceMetrics()
        
        sharpe = metrics.calculate_sharpe_ratio([])
        
        assert sharpe == 0.0
    
    def test_calculate_sharpe_ratio_single_return(self):
        """Test Sharpe ratio calculation with single return"""
        metrics = PerformanceMetrics()
        
        sharpe = metrics.calculate_sharpe_ratio([0.01])
        
        assert sharpe == 0.0
    
    def test_calculate_sharpe_ratio_normal_returns(self):
        """Test Sharpe ratio calculation with normal returns"""
        metrics = PerformanceMetrics()
        
        returns = [0.01, 0.02, -0.01, 0.015, 0.005]
        sharpe = metrics.calculate_sharpe_ratio(returns, risk_free_rate=0.02)
        
        # Should be positive for positive average returns
        assert sharpe > 0
        assert isinstance(sharpe, float)
    
    def test_calculate_sharpe_ratio_negative_returns(self):
        """Test Sharpe ratio calculation with negative returns"""
        metrics = PerformanceMetrics()
        
        returns = [-0.01, -0.02, -0.005, -0.015, -0.01]
        sharpe = metrics.calculate_sharpe_ratio(returns, risk_free_rate=0.02)
        
        # Should be negative for negative average returns
        assert sharpe < 0
        assert isinstance(sharpe, float)
    
    def test_calculate_sharpe_ratio_zero_volatility(self):
        """Test Sharpe ratio calculation with zero volatility"""
        metrics = PerformanceMetrics()
        
        returns = [0.01, 0.01, 0.01, 0.01, 0.01]  # All same returns
        sharpe = metrics.calculate_sharpe_ratio(returns)
        
        assert sharpe == 0.0
    
    def test_calculate_sharpe_ratio_custom_risk_free_rate(self):
        """Test Sharpe ratio calculation with custom risk-free rate"""
        metrics = PerformanceMetrics()
        
        returns = [0.01, 0.02, -0.01, 0.015, 0.005]
        sharpe_high_rf = metrics.calculate_sharpe_ratio(returns, risk_free_rate=0.05)
        sharpe_low_rf = metrics.calculate_sharpe_ratio(returns, risk_free_rate=0.01)
        
        # Higher risk-free rate should result in lower Sharpe ratio
        assert sharpe_high_rf < sharpe_low_rf
    
    def test_calculate_max_drawdown_empty_curve(self):
        """Test max drawdown calculation with empty equity curve"""
        metrics = PerformanceMetrics()
        
        max_dd = metrics.calculate_max_drawdown([])
        
        assert max_dd == 0.0
    
    def test_calculate_max_drawdown_single_value(self):
        """Test max drawdown calculation with single value"""
        metrics = PerformanceMetrics()
        
        max_dd = metrics.calculate_max_drawdown([10000.0])
        
        assert max_dd == 0.0
    
    def test_calculate_max_drawdown_no_drawdown(self):
        """Test max drawdown calculation with no drawdown"""
        metrics = PerformanceMetrics()
        
        equity_curve = [10000.0, 10100.0, 10200.0, 10300.0, 10400.0]
        max_dd = metrics.calculate_max_drawdown(equity_curve)
        
        assert max_dd == 0.0
    
    def test_calculate_max_drawdown_with_drawdown(self):
        """Test max drawdown calculation with drawdown"""
        metrics = PerformanceMetrics()
        
        equity_curve = [10000.0, 11000.0, 10500.0, 12000.0, 10000.0, 13000.0]
        max_dd = metrics.calculate_max_drawdown(equity_curve)
        
        # Max drawdown should be 0.1667 (16.67% from 12000 to 10000)
        assert abs(max_dd - 0.1667) < 0.0001
    
    def test_calculate_max_drawdown_continuous_decline(self):
        """Test max drawdown calculation with continuous decline"""
        metrics = PerformanceMetrics()
        
        equity_curve = [10000.0, 9500.0, 9000.0, 8500.0, 8000.0]
        max_dd = metrics.calculate_max_drawdown(equity_curve)
        
        # Max drawdown should be 0.2 (20% from 10000 to 8000)
        assert max_dd == 0.2
    
    def test_calculate_consecutive_wins_no_trades(self):
        """Test consecutive wins calculation with no trades"""
        metrics = PerformanceMetrics()
        
        consecutive_wins = metrics.calculate_consecutive_wins([])
        
        assert consecutive_wins == 0
    
    def test_calculate_consecutive_wins_with_trades(self):
        """Test consecutive wins calculation with trades"""
        metrics = PerformanceMetrics()
        
        trades = [
            {'pnl': 100.0},   # Win
            {'pnl': 200.0},   # Win
            {'pnl': -50.0},   # Loss
            {'pnl': 150.0},   # Win
            {'pnl': 300.0},   # Win
            {'pnl': 250.0},   # Win
            {'pnl': -75.0}    # Loss
        ]
        consecutive_wins = metrics.calculate_consecutive_wins(trades)
        
        # Max consecutive wins should be 3 (trades 4, 5, 6)
        assert consecutive_wins == 3
    
    def test_calculate_consecutive_losses_no_trades(self):
        """Test consecutive losses calculation with no trades"""
        metrics = PerformanceMetrics()
        
        consecutive_losses = metrics.calculate_consecutive_losses([])
        
        assert consecutive_losses == 0
    
    def test_calculate_consecutive_losses_with_trades(self):
        """Test consecutive losses calculation with trades"""
        metrics = PerformanceMetrics()
        
        trades = [
            {'pnl': 100.0},   # Win
            {'pnl': -50.0},   # Loss
            {'pnl': -75.0},   # Loss
            {'pnl': 150.0},   # Win
            {'pnl': -25.0},   # Loss
            {'pnl': -100.0},  # Loss
            {'pnl': -200.0}   # Loss
        ]
        consecutive_losses = metrics.calculate_consecutive_losses(trades)
        
        # Max consecutive losses should be 3 (trades 5, 6, 7)
        assert consecutive_losses == 3
    
    def test_calculate_profit_factor_no_trades(self):
        """Test profit factor calculation with no trades"""
        metrics = PerformanceMetrics()
        
        profit_factor = metrics.calculate_profit_factor([])
        
        assert profit_factor == 0.0
    
    def test_calculate_profit_factor_all_wins(self):
        """Test profit factor calculation with all winning trades"""
        metrics = PerformanceMetrics()
        
        trades = [
            {'pnl': 100.0},
            {'pnl': 200.0},
            {'pnl': 150.0}
        ]
        profit_factor = metrics.calculate_profit_factor(trades)
        
        # All wins, no losses = 0.0 (no gross loss)
        assert profit_factor == 0.0
    
    def test_calculate_profit_factor_all_losses(self):
        """Test profit factor calculation with all losing trades"""
        metrics = PerformanceMetrics()
        
        trades = [
            {'pnl': -100.0},
            {'pnl': -200.0},
            {'pnl': -150.0}
        ]
        profit_factor = metrics.calculate_profit_factor(trades)
        
        # All losses, no wins = 0 profit factor
        assert profit_factor == 0.0
    
    def test_calculate_profit_factor_mixed_trades(self):
        """Test profit factor calculation with mixed trades"""
        metrics = PerformanceMetrics()
        
        trades = [
            {'pnl': 100.0},   # Win
            {'pnl': -50.0},   # Loss
            {'pnl': 200.0},   # Win
            {'pnl': -75.0},   # Loss
            {'pnl': 150.0}    # Win
        ]
        profit_factor = metrics.calculate_profit_factor(trades)
        
        # Total wins: 450, Total losses: 125, Profit factor: 450/125 = 3.6
        assert abs(profit_factor - 3.6) < 0.0001
    
    def test_calculate_win_loss_ratio(self):
        """Test win/loss ratio calculation"""
        metrics = PerformanceMetrics()
        
        trades = [
            {'pnl': 100.0},   # Win
            {'pnl': -50.0},   # Loss
            {'pnl': 200.0},   # Win
            {'pnl': -75.0},   # Loss
            {'pnl': 150.0}    # Win
        ]
        win_loss_ratio = metrics.calculate_win_loss_ratio(trades)
        
        # Average win: (100 + 200 + 150) / 3 = 150
        # Average loss: (50 + 75) / 2 = 62.5
        # Ratio: 150 / 62.5 = 2.4
        assert abs(win_loss_ratio - 2.4) < 0.0001
    
    def test_calculate_expectancy(self):
        """Test expectancy calculation"""
        metrics = PerformanceMetrics()
        
        trades = [
            {'pnl': 100.0},   # Win
            {'pnl': -50.0},   # Loss
            {'pnl': 200.0},   # Win
            {'pnl': -75.0},   # Loss
            {'pnl': 150.0}    # Win
        ]
        expectancy = metrics.calculate_expectancy(trades)
        
        # Win rate: 3/5 = 0.6
        # Average win: 150, Average loss: 62.5
        # Expectancy: (0.6 * 150) - (0.4 * 62.5) = 90 - 25 = 65
        assert abs(expectancy - 65.0) < 0.0001
    
    def test_calculate_kelly_criterion(self):
        """Test Kelly criterion calculation"""
        metrics = PerformanceMetrics()
        
        kelly = metrics.calculate_kelly_criterion(
            win_rate=0.6,
            avg_win=150.0,
            avg_loss=62.5
        )
        
        # Kelly = (0.6 * 150 - 0.4 * 62.5) / 150 = (90 - 25) / 150 = 0.433
        assert abs(kelly - 0.433) < 0.001
    
    def test_calculate_recovery_factor(self):
        """Test recovery factor calculation"""
        metrics = PerformanceMetrics()
        
        recovery_factor = metrics.calculate_recovery_factor(
            total_return=1500.0,
            max_drawdown=0.1
        )
        
        # Recovery factor = 1500 / 0.1 = 15000
        assert recovery_factor == 15000.0
    
    def test_calculate_ulcer_index(self):
        """Test Ulcer Index calculation"""
        metrics = PerformanceMetrics()
        
        equity_curve = [10000.0, 10100.0, 10050.0, 10200.0, 10150.0, 11500.0]
        ulcer_index = metrics.calculate_ulcer_index(equity_curve)
        
        # Should be a positive number representing downside risk
        assert ulcer_index >= 0.0
        assert isinstance(ulcer_index, float)
    
    def test_calculate_mar_ratio(self):
        """Test MAR ratio calculation"""
        metrics = PerformanceMetrics()
        
        mar_ratio = metrics.calculate_mar_ratio(
            total_return=0.15,
            ulcer_index=0.05
        )
        
        # MAR ratio = 0.15 / 0.05 = 3.0
        assert mar_ratio == 3.0


class TestPerformanceMetricsEdgeCases:
    """Test edge cases and error conditions for PerformanceMetrics"""
    
    def test_calculate_returns_with_nan_values(self):
        """Test returns calculation with NaN values"""
        metrics = PerformanceMetrics()
        
        equity_curve = [10000.0, float('nan'), 10100.0, 10200.0]
        returns = metrics.calculate_returns(equity_curve)
        
        # Should handle NaN gracefully
        assert len(returns) == 3
        assert not np.isnan(returns[0])  # First return should be valid
        assert np.isnan(returns[1])      # Second return should be NaN
        assert not np.isnan(returns[2])  # Third return should be valid
    
    def test_calculate_returns_with_inf_values(self):
        """Test returns calculation with infinite values"""
        metrics = PerformanceMetrics()
        
        equity_curve = [10000.0, float('inf'), 10100.0, 10200.0]
        returns = metrics.calculate_returns(equity_curve)
        
        # Should handle infinity gracefully
        assert len(returns) == 3
        assert returns[0] == float('inf')  # First return should be infinity
        assert returns[1] == float('-inf') # Second return should be negative infinity
        assert not np.isinf(returns[2])    # Third return should be valid
    
    def test_calculate_sharpe_ratio_with_nan_returns(self):
        """Test Sharpe ratio calculation with NaN returns"""
        metrics = PerformanceMetrics()
        
        returns = [0.01, float('nan'), 0.02, -0.01]
        sharpe = metrics.calculate_sharpe_ratio(returns)
        
        # Should handle NaN gracefully
        assert isinstance(sharpe, float)
        assert not np.isnan(sharpe)
    
    def test_calculate_sharpe_ratio_with_inf_returns(self):
        """Test Sharpe ratio calculation with infinite returns"""
        metrics = PerformanceMetrics()
        
        returns = [0.01, float('inf'), 0.02, -0.01]
        sharpe = metrics.calculate_sharpe_ratio(returns)
        
        # Should handle infinity gracefully
        assert isinstance(sharpe, float)
        assert not np.isinf(sharpe)
    
    def test_calculate_max_drawdown_with_nan_values(self):
        """Test max drawdown calculation with NaN values"""
        metrics = PerformanceMetrics()
        
        equity_curve = [10000.0, float('nan'), 10100.0, 10200.0]
        max_dd = metrics.calculate_max_drawdown(equity_curve)
        
        # Should handle NaN gracefully
        assert isinstance(max_dd, float)
        assert not np.isnan(max_dd)
    
    def test_calculate_consecutive_wins_with_nan_pnl(self):
        """Test consecutive wins calculation with NaN PnL values"""
        metrics = PerformanceMetrics()
        
        trades = [
            {'pnl': 100.0},
            {'pnl': float('nan')},
            {'pnl': 200.0}
        ]
        consecutive_wins = metrics.calculate_consecutive_wins(trades)
        
        # Should handle NaN gracefully
        assert isinstance(consecutive_wins, int)
        assert consecutive_wins >= 0
    
    def test_calculate_profit_factor_with_nan_pnl(self):
        """Test profit factor calculation with NaN PnL values"""
        metrics = PerformanceMetrics()
        
        trades = [
            {'pnl': 100.0},
            {'pnl': float('nan')},
            {'pnl': -50.0},
            {'pnl': 200.0}
        ]
        profit_factor = metrics.calculate_profit_factor(trades)
        
        # Should handle NaN gracefully
        assert isinstance(profit_factor, float)
        assert not np.isnan(profit_factor)
    
    def test_calculate_consecutive_losses_with_nan_pnl(self):
        """Test consecutive losses calculation with NaN PnL values"""
        metrics = PerformanceMetrics()
        
        trades = [
            {'pnl': -100.0},
            {'pnl': float('nan')},
            {'pnl': -200.0}
        ]
        consecutive_losses = metrics.calculate_consecutive_losses(trades)
        
        # Should handle NaN gracefully
        assert isinstance(consecutive_losses, int)
        assert consecutive_losses >= 0
    
    def test_calculate_win_loss_ratio_with_nan_pnl(self):
        """Test win/loss ratio calculation with NaN PnL values"""
        metrics = PerformanceMetrics()
        
        trades = [
            {'pnl': 100.0},
            {'pnl': float('nan')},
            {'pnl': -50.0},
            {'pnl': 200.0}
        ]
        win_loss_ratio = metrics.calculate_win_loss_ratio(trades)
        
        # Should handle NaN gracefully
        assert isinstance(win_loss_ratio, float)
        assert not np.isnan(win_loss_ratio)
    
    def test_calculate_expectancy_with_nan_pnl(self):
        """Test expectancy calculation with NaN PnL values"""
        metrics = PerformanceMetrics()
        
        trades = [
            {'pnl': 100.0},
            {'pnl': float('nan')},
            {'pnl': -50.0},
            {'pnl': 200.0}
        ]
        expectancy = metrics.calculate_expectancy(trades)
        
        # Should handle NaN gracefully
        assert isinstance(expectancy, float)
        assert not np.isnan(expectancy)
    
    def test_calculate_kelly_criterion_with_zero_avg_loss(self):
        """Test Kelly criterion calculation with zero average loss"""
        metrics = PerformanceMetrics()
        
        kelly = metrics.calculate_kelly_criterion(
            win_rate=0.6,
            avg_win=150.0,
            avg_loss=0.0
        )
        
        # Should return 0.0 when avg_loss is 0
        assert kelly == 0.0
    
    def test_calculate_recovery_factor_with_zero_drawdown(self):
        """Test recovery factor calculation with zero drawdown"""
        metrics = PerformanceMetrics()
        
        recovery_factor = metrics.calculate_recovery_factor(
            total_return=1500.0,
            max_drawdown=0.0
        )
        
        # Should return 0.0 when max_drawdown is 0
        assert recovery_factor == 0.0
    
    def test_calculate_mar_ratio_with_zero_ulcer_index(self):
        """Test MAR ratio calculation with zero ulcer index"""
        metrics = PerformanceMetrics()
        
        mar_ratio = metrics.calculate_mar_ratio(
            total_return=0.15,
            ulcer_index=0.0
        )
        
        # Should return 0.0 when ulcer_index is 0
        assert mar_ratio == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
