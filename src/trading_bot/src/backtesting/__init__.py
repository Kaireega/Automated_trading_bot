"""
Backtesting module for the market adaptive bot with integrated simulation capabilities.
"""
from .backtest_engine import BacktestEngine, BacktestResult
from .performance_metrics import PerformanceMetrics
from .optimizer import ParameterOptimizer
from .simulation_broker import SimulationBroker
from .broker import BrokerSim
from .feeds import HistoricalDataFeed

__all__ = ['BacktestEngine', 'BacktestResult', 'PerformanceMetrics', 'ParameterOptimizer', 'SimulationBroker', 'BrokerSim', 'HistoricalDataFeed']


