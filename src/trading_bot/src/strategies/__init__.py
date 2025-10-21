"""
Multi-Strategy Framework for Intraday Trading.

This module provides a comprehensive strategy framework with 15-20 specialized
trading strategies optimized for M1/M5/M15 intraday forex trading.

Architecture:
- BaseStrategy: Abstract base class for all strategies
- StrategyManager: Orchestrates multiple strategies and generates consensus
- Individual strategies organized by type (trend, mean reversion, breakout, etc.)

Author: Trading Bot Development Team
Version: 1.0.0
"""

from .strategy_base import BaseStrategy, StrategySignal
from .strategy_manager import StrategyManager
from .strategy_registry import StrategyRegistry

__all__ = [
    'BaseStrategy',
    'StrategySignal',
    'StrategyManager',
    'StrategyRegistry'
]









