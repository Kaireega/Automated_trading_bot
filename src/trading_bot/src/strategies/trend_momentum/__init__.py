"""Trend Momentum Strategies - EMA, MACD, ADX, Ichimoku."""

from .ema_crossover import EMACrossoverStrategy
from .macd_momentum import MACDMomentumStrategy
from .adx_trend import ADXTrendStrategy
from .fast_ichimoku import FastIchimokuStrategy

__all__ = [
    'EMACrossoverStrategy',
    'MACDMomentumStrategy',
    'ADXTrendStrategy',
    'FastIchimokuStrategy'
]









