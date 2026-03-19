"""
Strategy registration — A-5 Strategy Overhaul.

Two strategies only: DailyBreakout (trend regime) + StructureReversal (ranging regime).
Old strategies are archived in strategies/archived/ — not deleted, not imported.
"""
from .swing.daily_breakout import DailyBreakoutStrategy
from .swing.structure_reversal import StructureReversalStrategy


def get_registered_strategies():
    """Get list of active strategy names."""
    return ['Daily_Breakout', 'Structure_Reversal']


def get_strategy_count():
    """Get count of active strategies."""
    return 2


__all__ = [
    'DailyBreakoutStrategy',
    'StructureReversalStrategy',
    'get_registered_strategies',
    'get_strategy_count',
]
