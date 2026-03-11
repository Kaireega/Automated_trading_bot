"""
Register all strategies with the StrategyRegistry.

This module imports and registers all available strategies.
Import this module to automatically register all strategies.
"""
from .strategy_registry import StrategyRegistry

# Import all strategies to trigger @register decorators
from .trend_momentum import (
    EMACrossoverStrategy,
    MACDMomentumStrategy,
    ADXTrendStrategy,
)
from .trend_momentum.fast_ichimoku import FastIchimokuStrategy

from .mean_reversion import (
    BollingerBounceStrategy,
    RSIExtremesStrategy,
    
)

from .breakout import (
    ATRBreakoutStrategy,
    SupportResistanceBreakStrategy,
)
from .breakout.donchian_break import DonchianBreakStrategy

from .scalping import (
    PriceActionScalpStrategy,
)
from .scalping.spread_squeeze import SpreadSqueezeStrategy
from .scalping.order_flow_momentum import OrderFlowMomentumStrategy
   

from .session_based import (
    LondonOpenBreakStrategy,
    NYOpenMomentumStrategy
)

# Import comprehensive debugging utilities
from trading_bot.src.utils.debug_utils import (
    debug_tracker, debug_line, debug_variable, debug_context, 
    debug_performance, debug_data_flow, debug_api_call, 
    debug_trade_decision, debug_strategy_execution, debug_risk_calculation,
    debug_indicator_calculation, debug_backtest_step, debug_entry_point,
    debug_exit_point, debug_conditional, debug_loop_iteration,
    get_debug_summary, export_debug_report
)

# All strategies are now registered via @StrategyRegistry.register decorators

@debug_line
def get_registered_strategies():
    """Get list of all registered strategy names."""
    return StrategyRegistry.list_strategies()

@debug_line
def get_strategy_count():
    """Get count of registered strategies."""
    return len(StrategyRegistry.list_strategies())

__all__ = [
    'get_registered_strategies',
    'get_strategy_count'
]






