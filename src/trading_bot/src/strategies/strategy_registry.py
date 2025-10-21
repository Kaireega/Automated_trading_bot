"""
Strategy Registry - Auto-discovery and registration of strategies.

This module provides automatic strategy registration and discovery.
"""
from typing import Dict, List, Type, Optional
from ..utils.logger import get_logger
from .strategy_base import BaseStrategy

# Import comprehensive debugging utilities
from trading_bot.src.utils.debug_utils import (
    debug_tracker, debug_line, debug_variable, debug_context, 
    debug_performance, debug_data_flow, debug_api_call, 
    debug_trade_decision, debug_strategy_execution, debug_risk_calculation,
    debug_indicator_calculation, debug_backtest_step, debug_entry_point,
    debug_exit_point, debug_conditional, debug_loop_iteration,
    get_debug_summary, export_debug_report
)


class StrategyRegistry:
    """
    Registry for all available trading strategies.
    
    Strategies are auto-registered via class decorators or manual registration.
    """
    
    _strategies: Dict[str, Type[BaseStrategy]] = {}
    _logger = get_logger(__name__)
    
    @classmethod
    @debug_line

    def register(cls, name: str):
        """
        Decorator to register a strategy class.
        
        Usage:
            @StrategyRegistry.register("Fast_EMA_Cross")
            class EMAStrategy(BaseStrategy):
                pass
        """
        @debug_line

        def wrapper(strategy_class: Type[BaseStrategy]):
            cls._strategies[name] = strategy_class
            cls._logger.debug(f"Registered strategy: {name}")
            return strategy_class
        return wrapper
    
    @classmethod
    @debug_line

    def register_class(cls, name: str, strategy_class: Type[BaseStrategy]):
        """
        Manually register a strategy class.
        
        Args:
            name: Strategy identifier
            strategy_class: Strategy class to register
        """
        cls._strategies[name] = strategy_class
        cls._logger.debug(f"Manually registered strategy: {name}")
    
    @classmethod
    def get_strategy_class(cls, name: str) -> Optional[Type[BaseStrategy]]:
        """
        Get strategy class by name.
        
        Args:
            name: Strategy identifier
            
        Returns:
            Strategy class or None if not found
        """
        return cls._strategies.get(name)
    
    @classmethod
    def list_strategies(cls) -> List[str]:
        """
        List all registered strategy names.
        
        Returns:
            List of strategy names
        """
        return list(cls._strategies.keys())
    
    @classmethod
    def get_all_strategies(cls) -> Dict[str, Type[BaseStrategy]]:
        """
        Get all registered strategies.
        
        Returns:
            Dictionary of strategy name -> strategy class
        """
        return cls._strategies.copy()
    
    @classmethod
    @debug_line

    def clear(cls):
        """Clear all registered strategies (mainly for testing)."""
        cls._strategies.clear()









