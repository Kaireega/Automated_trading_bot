"""
Parameter Space Definitions for Hyperparameter Optimization

This module defines comprehensive parameter ranges for all trading strategies
to enable systematic hyperparameter optimization across different market regimes.
"""
from typing import Dict, Any, List
from datetime import timedelta

# Comprehensive parameter spaces for all strategies
PARAMETER_SPACES: Dict[str, Any] = {
    "global_settings": {
        "optimization_priorities": {
            "Fast_EMA_Cross_M5": 10,
            "MACD_Momentum_M5": 9,
            "BB_Bounce_M5": 8,
            "RSI_Extremes": 8,
            "ADX_Trend_M5": 7,
            "Fast_Ichimoku": 7,
            "ATR_Breakout": 6,
            "Support_Resistance_Break": 6,
            "Donchian_Break": 5,
            "Price_Action_Scalp": 4,
            "Spread_Squeeze": 3,
            "Order_Flow_Momentum": 3,
            "London_Open_Break": 2,
            "NY_Open_Momentum": 2,
        },
        "risk_management": {
            "risk_percentage": [2.0, 3.0, 4.0, 5.0, 6.0],  # INCREASED from [0.5, 1.0, 1.5, 2.0, 2.5]
            "stop_loss_multiplier": [1.5, 2.0, 2.5, 3.0, 3.5],
            "take_profit_multiplier": [1.8, 2.0, 2.5, 3.0, 3.5],  # INCREASED minimum from 1.0 to 1.8
            "max_trades_per_day": [5, 8, 10, 12, 15],  # REALISTIC RANGE
            "max_daily_loss": [0.02, 0.03, 0.04, 0.05],
        },
        "regime_specific_confidence": {
            "TRENDING": [0.60, 0.65, 0.70, 0.75],  # INCREASED from [0.5, 0.55, 0.6, 0.65]
            "RANGING": [0.70, 0.75, 0.80, 0.85],  # INCREASED from [0.6, 0.65, 0.7, 0.75]
            "VOLATILE": [0.60, 0.65, 0.70, 0.75],  # INCREASED from [0.5, 0.55, 0.6, 0.65]
        },
        "timeframe_weights": {
            "M5": 0.4,   # SYNCHRONIZED with live bot
            "M15": 0.6,  # SYNCHRONIZED with live bot
            "H1": 0.0,   # Disabled for intraday focus
        },
        "hold_time_settings": {
            "min_hold_time": [timedelta(minutes=5), timedelta(minutes=15), timedelta(minutes=30)],
            "max_hold_time": [timedelta(hours=1), timedelta(hours=2), timedelta(hours=4)],
        },
    },
    "strategies": {
        "Fast_EMA_Cross_M5": {
            "ema_fast": [5, 8, 12, 21, 34],
            "ema_slow": [21, 26, 34, 50, 89],
            "min_confidence": [0.70, 0.75, 0.80, 0.85],  # INCREASED from [0.5, 0.6, 0.65, 0.7, 0.75]
        },
        "MACD_Momentum_M5": {
            "fast": [8, 12, 16],
            "slow": [18, 26, 34],
            "signal": [7, 9, 12],
            "histogram_threshold": [0.00001, 0.00005, 0.0001],
            "min_confidence": [0.65, 0.70, 0.75, 0.80],  # INCREASED from [0.5, 0.6, 0.65, 0.7]
        },
        "BB_Bounce_M5": {
            "period": [15, 20, 25],
            "std_dev": [1.5, 2.0, 2.5],
            "touch_threshold": [0.0005, 0.001, 0.0015],
            "min_confidence": [0.65, 0.70, 0.75, 0.80],  # INCREASED from [0.5, 0.6, 0.65, 0.7]
        },
        "RSI_Extremes": {
            "period": [10, 14, 20],
            "oversold": [30, 35, 40],
            "overbought": [60, 65, 70],
            "extreme_oversold": [20, 25, 30],
            "extreme_overbought": [70, 75, 80],
            "min_confidence": [0.65, 0.70, 0.75, 0.80],  # INCREASED from [0.5, 0.6, 0.65, 0.7]
        },
        "ADX_Trend_M5": {
            "adx_period": [10, 14, 20],
            "adx_threshold": [20, 25, 30],
            "min_confidence": [0.65, 0.70, 0.75, 0.80],  # INCREASED from [0.5, 0.6, 0.65, 0.7]
        },
        "Fast_Ichimoku": {
            "tenkan_period": [7, 9, 12],
            "kijun_period": [22, 26, 30],
            "senkou_span_b_period": [44, 52, 60],
            "min_confidence": [0.65, 0.70, 0.75, 0.80],  # INCREASED from [0.5, 0.6, 0.65, 0.7]
        },
        "ATR_Breakout": {
            "atr_period": [10, 14, 20],
            "atr_multiplier": [1.0, 1.5, 2.0],
            "min_confidence": [0.65, 0.70, 0.75, 0.80],  # INCREASED from [0.5, 0.6, 0.65, 0.7]
        },
        "Support_Resistance_Break": {
            "lookback_period": [20, 30, 40],
            "breakout_threshold": [0.0001, 0.0002, 0.0003],
            "min_confidence": [0.65, 0.70, 0.75, 0.80],  # INCREASED from [0.5, 0.6, 0.65, 0.7]
        },
        "Donchian_Break": {
            "period": [20, 30, 40],
            "min_confidence": [0.65, 0.70, 0.75, 0.80],  # INCREASED from [0.5, 0.6, 0.65, 0.7]
        },
        "Price_Action_Scalp": {
            "candle_pattern_strength": [0.6, 0.7, 0.8],
            "reversal_strength": [0.5, 0.6, 0.7],
            "min_confidence": [0.75, 0.80, 0.85, 0.90],  # INCREASED for scalping
            "risk_reward_minimum": [1.5, 2.0, 2.5],  # NEW: Higher R:R for scalping
        },
        "Spread_Squeeze": {
            "spread_threshold_multiplier": [1.5, 2.0, 2.5],
            "volume_increase_factor": [1.5, 2.0, 2.5],
            "min_confidence": [0.70, 0.75, 0.80, 0.85],  # INCREASED for scalping
            "risk_reward_minimum": [1.5, 2.0, 2.5],  # NEW: Higher R:R for scalping
        },
        "Order_Flow_Momentum": {
            "order_flow_imbalance_threshold": [0.6, 0.7, 0.8],
            "volume_profile_strength": [0.5, 0.6, 0.7],
            "min_confidence": [0.75, 0.80, 0.85, 0.90],  # INCREASED for scalping
            "risk_reward_minimum": [1.5, 2.0, 2.5],  # NEW: Higher R:R for scalping
        },
        "London_Open_Break": {
            "pre_london_range_period": [60, 90, 120],
            "breakout_atr_multiplier": [1.0, 1.5, 2.0],
            "min_confidence": [0.75, 0.80, 0.85, 0.90],  # INCREASED for session-based
        },
        "NY_Open_Momentum": {
            "pre_ny_range_period": [30, 60, 90],
            "momentum_threshold": [0.0001, 0.0002, 0.0003],
            "min_confidence": [0.75, 0.80, 0.85, 0.90],  # INCREASED for session-based
        },
    },
}


def get_parameter_space(strategy_name: str, regime: str = "GLOBAL") -> Dict[str, List[Any]]:
    """
    Get parameter space for a specific strategy and regime.
    
    Args:
        strategy_name: Name of the strategy
        regime: Market regime (TRENDING, RANGING, VOLATILE, GLOBAL)
    
    Returns:
        Dictionary mapping parameter names to their possible values
    """
    if strategy_name not in PARAMETER_SPACES["strategies"]:
        raise ValueError(f"Unknown strategy: {strategy_name}")
    
    strategy_params = PARAMETER_SPACES["strategies"][strategy_name].copy()
    
    # Apply regime-specific confidence thresholds
    if regime != "GLOBAL" and regime in PARAMETER_SPACES["global_settings"]["regime_specific_confidence"]:
        if "min_confidence" in strategy_params:
            strategy_params["min_confidence"] = PARAMETER_SPACES["global_settings"]["regime_specific_confidence"][regime]
    
    return strategy_params


def get_risk_parameter_space() -> Dict[str, List[Any]]:
    """Get risk management parameter space."""
    return PARAMETER_SPACES["global_settings"]["risk_management"].copy()


def get_consensus_parameter_space() -> Dict[str, List[Any]]:
    """Get consensus and confluence parameter space."""
    return {
        "min_strategies_agreeing": [2, 3, 4, 5],
        "min_confluence_score": [0.5, 0.6, 0.7, 0.8],
    }


def get_combined_parameter_space(strategy_name: str, regime: str = "GLOBAL", 
                                include_risk: bool = True) -> Dict[str, List[Any]]:
    """
    Get combined parameter space including strategy and risk parameters.
    
    Args:
        strategy_name: Name of the strategy
        regime: Market regime
        include_risk: Whether to include risk management parameters
    
    Returns:
        Combined parameter space
    """
    combined_space = get_parameter_space(strategy_name, regime)
    
    if include_risk:
        risk_space = get_risk_parameter_space()
        combined_space.update(risk_space)
    
    return combined_space


def get_all_strategy_names() -> List[str]:
    """Get list of all available strategy names."""
    return list(PARAMETER_SPACES["strategies"].keys())


def get_optimization_priorities() -> Dict[str, int]:
    """Get optimization priorities for different strategies."""
    return PARAMETER_SPACES["global_settings"]["optimization_priorities"].copy()


def validate_parameter_values(strategy_name: str, parameters: Dict[str, Any]) -> bool:
    """
    Validate parameter values against their defined ranges.
    
    Args:
        strategy_name: Name of the strategy
        parameters: Dictionary of parameter values to validate
    
    Returns:
        True if all parameters are valid, False otherwise
    """
    if strategy_name not in PARAMETER_SPACES["strategies"]:
        return False
    
    strategy_params = PARAMETER_SPACES["strategies"][strategy_name]
    
    for param_name, value in parameters.items():
        if param_name not in strategy_params:
            continue
        
        allowed_values = strategy_params[param_name]
        if value not in allowed_values:
            return False
    
    return True