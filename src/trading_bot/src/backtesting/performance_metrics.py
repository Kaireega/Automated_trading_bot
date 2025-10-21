"""
Performance Metrics - Comprehensive performance calculation for backtesting.
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Any
from decimal import Decimal


class PerformanceMetrics:
    """Calculate comprehensive performance metrics for trading strategies."""
    
    def _ensure_float_list(self, values: List) -> List[float]:
        """Convert a list of mixed types to float list with error handling."""
        try:
            return [float(value) for value in values]
        except (TypeError, ValueError) as e:
            # Log warning and return empty list for safety
            print(f"Warning: Failed to convert values to float: {e}")
            return []
    
    def _safe_float_conversion(self, value) -> float:
        """Safely convert a single value to float."""
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
    
    def calculate_returns(self, equity_curve: List[float]) -> List[float]:
        """Calculate percentage returns from equity curve."""
        if len(equity_curve) < 2:
            return []
        
        # Convert all values to float for consistent calculations with error handling
        equity_curve_float = self._ensure_float_list(equity_curve)
        if not equity_curve_float:
            return []
        
        returns = []
        for i in range(1, len(equity_curve_float)):
            if equity_curve_float[i-1] != 0:
                return_pct = (equity_curve_float[i] - equity_curve_float[i-1]) / equity_curve_float[i-1]
                returns.append(return_pct)
            else:
                returns.append(0.0)
        
        return returns
    
    def calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio."""
        if not returns:
            return 0.0
        
        try:
            # Convert returns to float array with error handling
            returns_float = self._ensure_float_list(returns)
            if not returns_float:
                return 0.0
                
            returns_array = np.array(returns_float)
            excess_returns = returns_array - (risk_free_rate / 252)  # Daily risk-free rate
            
            if len(excess_returns) < 2:
                return 0.0
            
            mean_return = np.mean(excess_returns)
            std_return = np.std(excess_returns, ddof=1)
            
            if std_return == 0:
                return 0.0
            
            # Annualize (assuming daily returns)
            sharpe_ratio = (mean_return / std_return) * np.sqrt(252)
            
            return float(sharpe_ratio)
        except Exception as e:
            print(f"Warning: Error calculating Sharpe ratio: {e}")
            return 0.0
    
    def calculate_max_drawdown(self, equity_curve: List[float]) -> float:
        """Calculate maximum drawdown."""
        if not equity_curve:
            return 0.0
        
        # Convert all values to float for consistent calculations with error handling
        equity_curve_float = self._ensure_float_list(equity_curve)
        if not equity_curve_float:
            return 0.0
        
        peak = equity_curve_float[0]
        max_dd = 0.0
        
        for value in equity_curve_float:
            if value > peak:
                peak = value
            dd = (peak - value) / peak if peak > 0 else 0.0
            max_dd = max(max_dd, dd)
        
        return max_dd
    
    def calculate_calmar_ratio(self, total_return: float, max_drawdown: float) -> float:
        """Calculate Calmar ratio (return / max drawdown)."""
        if max_drawdown == 0:
            return 0.0
        return total_return / max_drawdown
    
    def calculate_sortino_ratio(self, returns: List[float], risk_free_rate: float = 0.02) -> float:
        """Calculate Sortino ratio (downside deviation)."""
        if not returns:
            return 0.0
        
        returns_array = np.array(returns)
        excess_returns = returns_array - (risk_free_rate / 252)
        
        # Calculate downside deviation
        downside_returns = excess_returns[excess_returns < 0]
        
        if len(downside_returns) == 0:
            return 0.0
        
        mean_return = np.mean(excess_returns)
        downside_deviation = np.std(downside_returns, ddof=1)
        
        if downside_deviation == 0:
            return 0.0
        
        # Annualize
        sortino_ratio = (mean_return / downside_deviation) * np.sqrt(252)
        
        return float(sortino_ratio)
    
    def calculate_consecutive_wins(self, trade_history: List[Dict[str, Any]]) -> int:
        """Calculate maximum consecutive winning trades."""
        if not trade_history:
            return 0
        
        max_consecutive = 0
        current_consecutive = 0
        
        for trade in trade_history:
            if trade['pnl'] > 0:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        return max_consecutive
    
    def calculate_consecutive_losses(self, trade_history: List[Dict[str, Any]]) -> int:
        """Calculate maximum consecutive losing trades."""
        if not trade_history:
            return 0
        
        max_consecutive = 0
        current_consecutive = 0
        
        for trade in trade_history:
            if trade['pnl'] < 0:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        return max_consecutive
    
    def calculate_win_loss_ratio(self, trade_history: List[Dict[str, Any]]) -> float:
        """Calculate average win / average loss ratio."""
        if not trade_history:
            return 0.0
        
        wins = [t['pnl'] for t in trade_history if t['pnl'] > 0]
        losses = [t['pnl'] for t in trade_history if t['pnl'] < 0]
        
        if not wins or not losses:
            return 0.0
        
        avg_win = np.mean(wins)
        avg_loss = abs(np.mean(losses))
        
        if avg_loss == 0:
            return 0.0
        
        return avg_win / avg_loss
    
    def calculate_expectancy(self, trade_history: List[Dict[str, Any]]) -> float:
        """Calculate expectancy (expected value per trade)."""
        if not trade_history:
            return 0.0
        
        win_rate = len([t for t in trade_history if t['pnl'] > 0]) / len(trade_history)
        
        wins = [t['pnl'] for t in trade_history if t['pnl'] > 0]
        losses = [t['pnl'] for t in trade_history if t['pnl'] < 0]
        
        avg_win = np.mean(wins) if wins else 0
        avg_loss = abs(np.mean(losses)) if losses else 0
        
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
        
        return expectancy
    
    def calculate_kelly_criterion(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """Calculate Kelly criterion for optimal position sizing.
        
        Uses the correct Kelly formula: f* = (bp - q) / b
        where:
            b = win/loss ratio (avg_win / avg_loss)
            p = probability of win (win_rate)
            q = probability of loss (1 - win_rate)
        """
        if avg_loss == 0:
            return 0.0
        
        b = avg_win / avg_loss  # Odds ratio
        p = win_rate
        q = 1 - win_rate
        
        # Kelly formula: (bp - q) / b
        kelly = (b * p - q) / b
        
        # Cap at 25% for safety
        return min(max(kelly, 0.0), 0.25)
    
    def calculate_recovery_factor(self, total_return: float, max_drawdown: float) -> float:
        """Calculate recovery factor."""
        if max_drawdown == 0:
            return 0.0
        return total_return / max_drawdown
    
    def calculate_profit_factor(self, trade_history: List[Dict[str, Any]]) -> float:
        """Calculate profit factor."""
        if not trade_history:
            return 0.0
        
        gross_profit = sum(t['pnl'] for t in trade_history if t['pnl'] > 0)
        gross_loss = abs(sum(t['pnl'] for t in trade_history if t['pnl'] < 0))
        
        if gross_loss == 0:
            return 0.0
        
        return gross_profit / gross_loss
    
    def calculate_risk_of_ruin(self, win_rate: float, avg_win: float, avg_loss: float, 
                             initial_capital: float, risk_per_trade: float) -> float:
        """Calculate risk of ruin probability."""
        if avg_loss == 0 or risk_per_trade == 0:
            return 0.0
        
        # Number of trades before ruin
        trades_to_ruin = initial_capital / risk_per_trade
        
        # Probability of ruin using binomial distribution
        if win_rate >= 0.5:
            # For winning strategies, use more complex calculation
            return 0.0  # Simplified for now
        else:
            # For losing strategies
            return (1 - win_rate) ** trades_to_ruin
    
    def calculate_ulcer_index(self, equity_curve: List[float]) -> float:
        """Calculate Ulcer Index (measure of downside risk)."""
        if len(equity_curve) < 2:
            return 0.0
        
        # Convert all values to float for consistent calculations with error handling
        equity_curve_float = self._ensure_float_list(equity_curve)
        if not equity_curve_float:
            return 0.0
        
        # Calculate drawdowns
        peak = equity_curve_float[0]
        drawdowns = []
        
        for value in equity_curve_float:
            if value > peak:
                peak = value
            dd = (peak - value) / peak if peak > 0 else 0.0
            drawdowns.append(dd)
        
        # Calculate Ulcer Index
        squared_drawdowns = [dd ** 2 for dd in drawdowns]
        ulcer_index = np.sqrt(np.mean(squared_drawdowns))
        
        return float(ulcer_index)
    
    def calculate_mar_ratio(self, total_return: float, ulcer_index: float) -> float:
        """Calculate MAR ratio (return / ulcer index)."""
        if ulcer_index == 0:
            return 0.0
        return total_return / ulcer_index
    
    def generate_performance_report(self, backtest_result: 'BacktestResult') -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        
        # Calculate additional metrics
        returns = self.calculate_returns(backtest_result.equity_curve)
        sortino_ratio = self.calculate_sortino_ratio(returns)
        calmar_ratio = self.calculate_calmar_ratio(backtest_result.total_return, backtest_result.max_drawdown)
        win_loss_ratio = self.calculate_win_loss_ratio(backtest_result.trade_history)
        expectancy = self.calculate_expectancy(backtest_result.trade_history)
        kelly_criterion = self.calculate_kelly_criterion(
            backtest_result.win_rate, backtest_result.avg_win, backtest_result.avg_loss
        )
        recovery_factor = self.calculate_recovery_factor(backtest_result.total_return, backtest_result.max_drawdown)
        ulcer_index = self.calculate_ulcer_index(backtest_result.equity_curve)
        mar_ratio = self.calculate_mar_ratio(backtest_result.total_return, ulcer_index)
        
        # Risk metrics
        if backtest_result.trade_history:
            trade_durations = [t['duration_minutes'] for t in backtest_result.trade_history]
            avg_trade_duration = np.mean(trade_durations)
            std_trade_duration = np.std(trade_durations)
        else:
            avg_trade_duration = std_trade_duration = 0
        
        # Monthly returns (if enough data)
        monthly_returns = self._calculate_monthly_returns(backtest_result.equity_curve, 
                                                        backtest_result.start_date, 
                                                        backtest_result.end_date)
        
        return {
            # Basic metrics
            'total_trades': backtest_result.total_trades,
            'winning_trades': backtest_result.winning_trades,
            'losing_trades': backtest_result.losing_trades,
            'win_rate': backtest_result.win_rate,
            'profit_factor': backtest_result.profit_factor,
            'total_return': backtest_result.total_return,
            'max_drawdown': backtest_result.max_drawdown,
            
            # Risk-adjusted returns
            'sharpe_ratio': backtest_result.sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,
            'mar_ratio': mar_ratio,
            
            # Trade statistics
            'avg_trade_duration': avg_trade_duration,
            'std_trade_duration': std_trade_duration,
            'avg_win': backtest_result.avg_win,
            'avg_loss': backtest_result.avg_loss,
            'win_loss_ratio': win_loss_ratio,
            'largest_win': backtest_result.largest_win,
            'largest_loss': backtest_result.largest_loss,
            
            # Risk metrics
            'consecutive_wins': backtest_result.consecutive_wins,
            'consecutive_losses': backtest_result.consecutive_losses,
            'expectancy': expectancy,
            'kelly_criterion': kelly_criterion,
            'recovery_factor': recovery_factor,
            'ulcer_index': ulcer_index,
            
            # Additional metrics
            'monthly_returns': monthly_returns,
            'equity_curve': backtest_result.equity_curve,
            'trade_history': backtest_result.trade_history,
            'parameter_set': backtest_result.parameter_set
        }
    
    def _calculate_monthly_returns(self, equity_curve: List[float], start_date, end_date) -> Dict[str, float]:
        """Calculate monthly returns."""
        if len(equity_curve) < 2:
            return {}
        
        # Create date range
        dates = pd.date_range(start=start_date, end=end_date, freq='M')
        monthly_returns = {}
        
        for i, date in enumerate(dates):
            if i < len(equity_curve) - 1:
                month_key = date.strftime('%Y-%m')
                if i == 0:
                    # First month: from initial balance
                    monthly_return = (equity_curve[i] - equity_curve[0]) / equity_curve[0]
                else:
                    # Subsequent months: from previous month end
                    monthly_return = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
                
                monthly_returns[month_key] = monthly_return
        
        return monthly_returns
