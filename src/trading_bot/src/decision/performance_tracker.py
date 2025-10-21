"""
Performance Tracker - Tracks trading performance metrics.
"""
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal
import statistics

from ..core.models import TradeDecision, PerformanceMetrics, TradeExecution
from ..utils.logger import get_logger


class PerformanceTracker:
    """Tracks and calculates trading performance metrics."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Performance data
        self._trades: List[TradeExecution] = []
        self._performance_metrics = PerformanceMetrics()
        from datetime import datetime, timezone
        self._last_calculation = datetime.now(timezone.utc)
        
        # Time periods for analysis
        self._periods = {
            'daily': timedelta(days=1),
            'weekly': timedelta(days=7),
            'monthly': timedelta(days=30)
        }
    
    def add_trade(self, trade_execution: TradeExecution) -> None:
        """Add a completed trade to the tracker."""
        print(f"📊 [DEBUG] Adding trade to performance tracker: {trade_execution.pair} - {trade_execution.action.value}")
        self._trades.append(trade_execution)
        self._update_metrics()
        print(f"📊 [DEBUG] Performance metrics updated - Total trades: {len(self._trades)}")
    
    def get_performance_metrics(self, period: str = 'all') -> PerformanceMetrics:
        """Get performance metrics for the specified period."""
        if period == 'all':
            return self._performance_metrics
        
        # Filter trades by period
        from datetime import datetime, timezone
        cutoff_time = datetime.now(timezone.utc) - self._periods.get(period, timedelta(days=30))
        period_trades = [t for t in self._trades if t.execution_time >= cutoff_time]
        
        return self._calculate_metrics(period_trades)
    
    def get_win_rate(self, period: str = 'all') -> float:
        """Get win rate for the specified period."""
        metrics = self.get_performance_metrics(period)
        return metrics.win_rate
    
    def get_profit_factor(self, period: str = 'all') -> float:
        """Get profit factor for the specified period."""
        metrics = self.get_performance_metrics(period)
        return metrics.profit_factor
    
    def get_sharpe_ratio(self, period: str = 'all') -> float:
        """Get Sharpe ratio for the specified period."""
        metrics = self.get_performance_metrics(period)
        return metrics.sharpe_ratio
    
    def get_max_drawdown(self, period: str = 'all') -> Decimal:
        """Get maximum drawdown for the specified period."""
        metrics = self.get_performance_metrics(period)
        return metrics.max_drawdown
    
    def get_trade_summary(self, period: str = 'all') -> Dict[str, Any]:
        """Get a summary of trading performance."""
        metrics = self.get_performance_metrics(period)
        
        return {
            'total_trades': metrics.total_trades,
            'winning_trades': metrics.winning_trades,
            'losing_trades': metrics.losing_trades,
            'win_rate': f"{metrics.win_rate:.2%}",
            'total_profit': float(metrics.total_profit),
            'total_loss': float(metrics.total_loss),
            'net_profit': float(metrics.net_profit),
            'average_win': float(metrics.average_win),
            'average_loss': float(metrics.average_loss),
            'profit_factor': metrics.profit_factor,
            'max_drawdown': float(metrics.max_drawdown),
            'sharpe_ratio': metrics.sharpe_ratio
        }

    def get_breakdown_by_pair(self, period: str = 'all') -> Dict[str, Dict[str, Any]]:
        from datetime import datetime, timezone
        if period == 'all':
            trades = self._trades
        else:
            cutoff_time = datetime.now(timezone.utc) - self._periods.get(period, timedelta(days=30))
            trades = [t for t in self._trades if t.execution_time >= cutoff_time]

        by_pair: Dict[str, List[TradeExecution]] = {}
        for t in trades:
            pair = t.trade_decision.recommendation.pair if t.trade_decision and t.trade_decision.recommendation else 'UNKNOWN'
            by_pair.setdefault(pair, []).append(t)
        breakdown: Dict[str, Dict[str, Any]] = {}
        for pair, pts in by_pair.items():
            m = self._calculate_metrics(pts)
            breakdown[pair] = {
                'total_trades': m.total_trades,
                'win_rate': f"{m.win_rate:.2%}",
                'net_profit': float(m.net_profit),
                'profit_factor': m.profit_factor,
                'max_drawdown': float(m.max_drawdown),
            }
        return breakdown
    
    async def get_daily_metrics(self) -> PerformanceMetrics:
        """Get daily performance metrics (async wrapper for compatibility)."""
        return self.get_performance_metrics('daily')
    
    def _update_metrics(self) -> None:
        """Update performance metrics."""
        self._performance_metrics = self._calculate_metrics(self._trades)
        from datetime import datetime, timezone
        self._last_calculation = datetime.now(timezone.utc)
    
    def _calculate_metrics(self, trades: List[TradeExecution]) -> PerformanceMetrics:
        """Calculate performance metrics from trades."""
        if not trades:
            return PerformanceMetrics()
        
        # Calculate basic metrics
        total_trades = len(trades)
        winning_trades = len([t for t in trades if self._calculate_trade_pnl(t) > 0])
        losing_trades = total_trades - winning_trades
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        
        # Calculate profit/loss
        profits = [self._calculate_trade_pnl(t) for t in trades if self._calculate_trade_pnl(t) > 0]
        losses = [self._calculate_trade_pnl(t) for t in trades if self._calculate_trade_pnl(t) < 0]
        
        total_profit = sum(profits) if profits else Decimal('0')
        total_loss = abs(sum(losses)) if losses else Decimal('0')
        net_profit = total_profit - total_loss
        
        # Calculate averages
        average_win = total_profit / len(profits) if profits else Decimal('0')
        average_loss = total_loss / len(losses) if losses else Decimal('0')
        
        # Calculate profit factor
        profit_factor = float(total_profit / total_loss) if total_loss > 0 else float('inf')
        
        # Calculate maximum drawdown
        max_drawdown = self._calculate_max_drawdown(trades)
        
        # Calculate Sharpe ratio (simplified)
        sharpe_ratio = self._calculate_sharpe_ratio(trades)
        
        # Set time period
        if trades:
            period_start = min(t.execution_time for t in trades)
            period_end = max(t.execution_time for t in trades)
        else:
            from datetime import datetime, timezone
            period_start = datetime.now(timezone.utc)
            period_end = datetime.now(timezone.utc)
        
        return PerformanceMetrics(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_profit=total_profit,
            total_loss=total_loss,
            net_profit=net_profit,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            average_win=average_win,
            average_loss=average_loss,
            profit_factor=profit_factor,
            period_start=period_start,
            period_end=period_end
        )
    
    def _calculate_trade_pnl(self, trade: TradeExecution) -> Decimal:
        """Calculate profit/loss for a trade."""
        try:
            # This is a simplified calculation
            # In a real implementation, you'd get the actual P&L from the broker
            entry_price = trade.trade_decision.recommendation.entry_price
            exit_price = trade.execution_price
            
            if trade.trade_decision.recommendation.signal.value == 'buy':
                return exit_price - entry_price
            else:
                return entry_price - exit_price
        except Exception:
            return Decimal('0')
    
    def _calculate_max_drawdown(self, trades: List[TradeExecution]) -> Decimal:
        """Calculate maximum drawdown."""
        if not trades:
            return Decimal('0')
        
        # Sort trades by execution time
        sorted_trades = sorted(trades, key=lambda t: t.execution_time)
        
        peak = Decimal('0')
        max_drawdown = Decimal('0')
        running_balance = Decimal('0')
        
        for trade in sorted_trades:
            pnl = self._calculate_trade_pnl(trade)
            running_balance += pnl
            
            if running_balance > peak:
                peak = running_balance
            
            drawdown = peak - running_balance
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        return max_drawdown
    
    def _calculate_sharpe_ratio(self, trades: List[TradeExecution], risk_free_rate: float = 0.02) -> float:
        """Calculate annualized Sharpe ratio.
        
        Args:
            trades: List of executed trades
            risk_free_rate: Annual risk-free rate (default 2%)
            
        Returns:
            Annualized Sharpe ratio
        """
        if not trades or len(trades) < 2:
            return 0.0
        
        # Calculate returns
        returns = []
        for trade in trades:
            pnl = self._calculate_trade_pnl(trade)
            # Convert to percentage return
            entry_price = trade.trade_decision.recommendation.entry_price
            if entry_price > 0:
                returns.append(float(pnl / entry_price))
        
        if not returns or len(returns) < 2:
            return 0.0
        
        # Calculate excess returns (assuming daily returns)
        returns_array = [r - (risk_free_rate / 252) for r in returns]
        
        mean_return = statistics.mean(returns_array)
        std_return = statistics.stdev(returns_array)
        
        if std_return == 0:
            return 0.0
        
        # Annualize (assuming daily returns)
        sharpe_ratio = (mean_return / std_return) * (252 ** 0.5)
        
        return sharpe_ratio
    
    def get_recent_trades(self, limit: int = 10) -> List[TradeExecution]:
        """Get the most recent trades."""
        sorted_trades = sorted(self._trades, key=lambda t: t.execution_time, reverse=True)
        return sorted_trades[:limit]
    
    def get_trades_by_pair(self, pair: str) -> List[TradeExecution]:
        """Get all trades for a specific pair."""
        return [t for t in self._trades if t.trade_decision.recommendation.pair == pair]
    
    def clear_old_data(self, days: int = 90) -> None:
        """Clear old trade data."""
        from datetime import datetime, timezone
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
        self._trades = [t for t in self._trades if t.execution_time >= cutoff_time]
        self._update_metrics()
    
    async def start(self) -> None:
        """Start the performance tracker."""
        print("📊 [DEBUG] Starting performance tracker...")
        self.logger.info("Performance tracker started")
        print("✅ [DEBUG] Performance tracker started successfully")
    
    async def close(self) -> None:
        """Close the performance tracker."""
        self.logger.info("Performance tracker closed")
    
    def reset_metrics(self) -> None:
        """Reset all performance metrics."""
        self._trades = []
        self._performance_metrics = PerformanceMetrics()
        from datetime import datetime, timezone
        self._last_calculation = datetime.now(timezone.utc) 