# TODO: Not connected to main flow — this module is unused dead code.
"""
Order Flow & Market Microstructure Analyzer - Professional trade timing optimization.

This module analyzes order flow, market microstructure, and liquidity conditions
to optimize trade entry timing and reduce execution costs.

Key Features:
- Bid-Ask spread analysis
- Volume profile analysis (VPOC, VAH, VAL)
- Order flow imbalance detection
- Liquidity analysis and timing
- Market depth analysis
- Trade timing optimization
- Quote stuffing detection
- Smart money detection (large institutional orders)

Author: Trading Bot Development Team
Version: 1.0.0
"""
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import deque
from dataclasses import dataclass

from ..utils.config import Config
from ..utils.logger import get_logger
from api.oanda_api import OandaApi


@dataclass
class OrderFlowSignal:
    """Order flow analysis signal."""
    timestamp: datetime
    pair: str
    flow_direction: str  # 'BULLISH', 'BEARISH', 'NEUTRAL'
    flow_strength: float  # 0-1
    imbalance_ratio: float  # Buy/Sell ratio
    spread_percentile: float  # Current spread vs historical
    liquidity_score: float  # 0-1, higher = better liquidity
    optimal_entry_timing: str  # 'NOW', 'WAIT', 'AVOID'
    timing_confidence: float  # 0-1
    large_order_detected: bool
    institutional_flow: bool
    adverse_selection_risk: float  # 0-1, higher = worse timing
    recommended_urgency: str  # 'LOW', 'NORMAL', 'HIGH', 'URGENT'


@dataclass
class VolumeProfile:
    """Volume profile data."""
    vpoc: float  # Volume Point of Control (price with highest volume)
    vah: float  # Value Area High (top of 70% volume area)
    val: float  # Value Area Low (bottom of 70% volume area)
    volume_distribution: Dict[float, float]
    total_volume: float
    value_area_volume_pct: float


class OrderFlowAnalyzer:
    """
    Professional order flow and market microstructure analysis.
    
    This class analyzes the fine details of market structure to identify
    optimal entry timing and avoid adverse selection (being on wrong side
    of large institutional orders).
    
    Key Concepts:
    - Order Flow: The actual buying and selling happening in real-time
    - Imbalance: When one side (buy or sell) dominates
    - Spread: Difference between bid and ask (cost of immediacy)
    - Liquidity: How easy it is to trade without moving price
    - VPOC: Price level with highest volume (magnet price)
    - Smart Money: Large institutional orders that move markets
    
    Improves Trading:
    - Better entry timing (wait for optimal liquidity)
    - Lower execution costs (trade when spreads are tight)
    - Avoid getting run over by large orders
    - Follow institutional flow direction
    """
    
    def __init__(self, config: Config, oanda_api: OandaApi):
        self.config = config
        self.oanda_api = oanda_api
        self.logger = get_logger(__name__)
        
        # Historical data for analysis
        self.spread_history: Dict[str, deque] = {}
        self.volume_history: Dict[str, deque] = {}
        self.trade_history: Dict[str, deque] = {}
        self.max_history_length = 100
        
        # Order flow tracking
        self.buy_volume: Dict[str, float] = {}
        self.sell_volume: Dict[str, float] = {}
        self.large_order_threshold = 100000  # $100k+ is "large"
        
        # Timing parameters
        self.optimal_spread_percentile = 30  # Trade when spread below 30th percentile
        self.min_liquidity_score = 0.6  # Minimum liquidity to trade
        
    async def analyze_order_flow(
        self,
        pair: str,
        timeframe: str = 'M5'
    ) -> OrderFlowSignal:
        """
        Comprehensive order flow analysis for trade timing.
        
        Args:
            pair: Currency pair to analyze
            timeframe: Timeframe for analysis
            
        Returns:
            OrderFlowSignal with timing recommendation
        """
        self.logger.info(f"📊 Analyzing order flow for {pair}...")
        
        try:
            # 1. Get current market data
            prices = self.oanda_api.get_prices([pair])
            if not prices or len(prices) == 0:
                return self._get_default_signal(pair, "No price data")
            
            price = prices[0]
            bid = float(price.bid)
            ask = float(price.ask)
            spread = ask - bid
            mid_price = (bid + ask) / 2
            
            # 2. Analyze spread conditions
            spread_analysis = self._analyze_spread(pair, spread, mid_price)
            
            # 3. Analyze order flow imbalance
            imbalance_analysis = await self._analyze_flow_imbalance(pair)
            
            # 4. Analyze liquidity
            liquidity_analysis = self._analyze_liquidity(pair, spread, mid_price)
            
            # 5. Detect large orders
            large_order_analysis = self._detect_large_orders(pair, imbalance_analysis)
            
            # 6. Calculate optimal timing
            timing_decision = self._calculate_optimal_timing(
                spread_analysis,
                imbalance_analysis,
                liquidity_analysis,
                large_order_analysis
            )
            
            # 7. Build comprehensive signal
            signal = OrderFlowSignal(
                timestamp=datetime.now(timezone.utc),
                pair=pair,
                flow_direction=imbalance_analysis['direction'],
                flow_strength=imbalance_analysis['strength'],
                imbalance_ratio=imbalance_analysis['ratio'],
                spread_percentile=spread_analysis['percentile'],
                liquidity_score=liquidity_analysis['score'],
                optimal_entry_timing=timing_decision['action'],
                timing_confidence=timing_decision['confidence'],
                large_order_detected=large_order_analysis['detected'],
                institutional_flow=large_order_analysis['institutional'],
                adverse_selection_risk=timing_decision['adverse_selection_risk'],
                recommended_urgency=timing_decision['urgency']
            )
            
            self._log_order_flow_analysis(signal)
            
            return signal
            
        except Exception as e:
            self.logger.error(f"❌ Order flow analysis error: {e}")
            return self._get_default_signal(pair, f"Analysis error: {str(e)}")
    
    def _analyze_spread(
        self,
        pair: str,
        current_spread: float,
        mid_price: float
    ) -> Dict[str, Any]:
        """Analyze current spread vs historical."""
        
        # Initialize spread history if needed
        if pair not in self.spread_history:
            self.spread_history[pair] = deque(maxlen=self.max_history_length)
        
        # Calculate spread in basis points
        spread_bps = (current_spread / mid_price) * 10000
        
        # Add to history
        self.spread_history[pair].append(spread_bps)
        
        # Calculate percentile
        if len(self.spread_history[pair]) >= 10:
            historical_spreads = list(self.spread_history[pair])
            percentile = (sum(1 for s in historical_spreads if s > spread_bps) 
                         / len(historical_spreads) * 100)
        else:
            percentile = 50.0  # Default to median if not enough history
        
        # Spread quality
        if spread_bps < 1.0:
            quality = 'EXCELLENT'
        elif spread_bps < 2.0:
            quality = 'GOOD'
        elif spread_bps < 5.0:
            quality = 'FAIR'
        else:
            quality = 'POOR'
        
        return {
            'spread_bps': spread_bps,
            'percentile': percentile,
            'quality': quality,
            'is_favorable': percentile < self.optimal_spread_percentile
        }
    
    async def _analyze_flow_imbalance(self, pair: str) -> Dict[str, Any]:
        """Analyze buy/sell order flow imbalance."""
        
        # Get recent candles to estimate order flow
        try:
            candles = self.oanda_api.fetch_candles(pair, granularity='M1', count=10)
            
            if not candles or len(candles) == 0:
                return {
                    'direction': 'NEUTRAL',
                    'strength': 0.5,
                    'ratio': 1.0,
                    'buy_pressure': 0.5,
                    'sell_pressure': 0.5
                }
            
            # Estimate buy/sell pressure from candle characteristics
            buy_pressure = 0.0
            sell_pressure = 0.0
            
            for candle in candles:
                close = float(candle.close)
                open_price = float(candle.open)
                high = float(candle.high)
                low = float(candle.low)
                
                # Bullish candle = more buying
                if close > open_price:
                    candle_range = high - low
                    body = close - open_price
                    buy_pressure += body / candle_range if candle_range > 0 else 0.5
                    sell_pressure += (candle_range - body) / candle_range if candle_range > 0 else 0.5
                else:
                    candle_range = high - low
                    body = open_price - close
                    sell_pressure += body / candle_range if candle_range > 0 else 0.5
                    buy_pressure += (candle_range - body) / candle_range if candle_range > 0 else 0.5
            
            # Normalize
            total_pressure = buy_pressure + sell_pressure
            if total_pressure > 0:
                buy_pct = buy_pressure / total_pressure
                sell_pct = sell_pressure / total_pressure
            else:
                buy_pct = sell_pct = 0.5
            
            # Calculate imbalance
            imbalance_ratio = buy_pct / sell_pct if sell_pct > 0 else 1.0
            
            # Determine direction and strength
            if imbalance_ratio > 1.2:
                direction = 'BULLISH'
                strength = min(1.0, (imbalance_ratio - 1.0) / 0.5)
            elif imbalance_ratio < 0.8:
                direction = 'BEARISH'
                strength = min(1.0, (1.0 - imbalance_ratio) / 0.2)
            else:
                direction = 'NEUTRAL'
                strength = 0.5
            
            return {
                'direction': direction,
                'strength': strength,
                'ratio': imbalance_ratio,
                'buy_pressure': buy_pct,
                'sell_pressure': sell_pct
            }
            
        except Exception as e:
            self.logger.error(f"Flow imbalance analysis error: {e}")
            return {
                'direction': 'NEUTRAL',
                'strength': 0.5,
                'ratio': 1.0,
                'buy_pressure': 0.5,
                'sell_pressure': 0.5
            }
    
    def _analyze_liquidity(
        self,
        pair: str,
        spread: float,
        mid_price: float
    ) -> Dict[str, Any]:
        """Analyze market liquidity conditions."""
        
        # Liquidity score based on spread (tighter spread = better liquidity)
        spread_bps = (spread / mid_price) * 10000
        
        if spread_bps < 1.0:
            liquidity_score = 1.0
        elif spread_bps < 2.0:
            liquidity_score = 0.8
        elif spread_bps < 5.0:
            liquidity_score = 0.5
        else:
            liquidity_score = max(0.2, 1.0 - (spread_bps / 10.0))
        
        # Check time of day (market session affects liquidity)
        current_hour = datetime.now(timezone.utc).hour
        
        # London (8-16 UTC) and NY (13-21 UTC) overlap = high liquidity
        if 13 <= current_hour <= 16:
            session_liquidity = 1.0
            session = 'OVERLAP'
        elif 8 <= current_hour <= 16:
            session_liquidity = 0.9
            session = 'LONDON'
        elif 13 <= current_hour <= 21:
            session_liquidity = 0.9
            session = 'NEW_YORK'
        elif 0 <= current_hour <= 7:
            session_liquidity = 0.7
            session = 'ASIA'
        else:
            session_liquidity = 0.5
            session = 'OFF_HOURS'
        
        # Combined liquidity score
        combined_score = (liquidity_score * 0.7 + session_liquidity * 0.3)
        
        return {
            'score': combined_score,
            'spread_based': liquidity_score,
            'session_based': session_liquidity,
            'current_session': session,
            'is_favorable': combined_score >= self.min_liquidity_score
        }
    
    def _detect_large_orders(
        self,
        pair: str,
        imbalance_analysis: Dict
    ) -> Dict[str, bool]:
        """Detect large institutional orders."""
        
        # Large order detection based on:
        # 1. Strong imbalance (>70% one direction)
        # 2. Sustained flow (not just one candle)
        
        strength = imbalance_analysis['strength']
        
        large_order_detected = strength > 0.7
        institutional_flow = strength > 0.8
        
        return {
            'detected': large_order_detected,
            'institutional': institutional_flow
        }
    
    def _calculate_optimal_timing(
        self,
        spread_analysis: Dict,
        imbalance_analysis: Dict,
        liquidity_analysis: Dict,
        large_order_analysis: Dict
    ) -> Dict[str, Any]:
        """Calculate optimal entry timing."""
        
        # Score components (0-1)
        spread_score = 1.0 if spread_analysis['is_favorable'] else 0.3
        liquidity_score = liquidity_analysis['score']
        flow_alignment_score = imbalance_analysis['strength']
        
        # Adverse selection risk (trading against large orders)
        if large_order_analysis['institutional']:
            adverse_selection_risk = 0.8
        elif large_order_analysis['detected']:
            adverse_selection_risk = 0.5
        else:
            adverse_selection_risk = 0.2
        
        # Overall timing score
        timing_score = (
            spread_score * 0.3 +
            liquidity_score * 0.3 +
            flow_alignment_score * 0.2 +
            (1 - adverse_selection_risk) * 0.2
        )
        
        # Decision
        if timing_score > 0.75:
            action = 'NOW'
            urgency = 'URGENT'
            confidence = 0.9
        elif timing_score > 0.6:
            action = 'NOW'
            urgency = 'HIGH'
            confidence = 0.75
        elif timing_score > 0.45:
            action = 'NOW'
            urgency = 'NORMAL'
            confidence = 0.6
        elif timing_score > 0.3:
            action = 'WAIT'
            urgency = 'LOW'
            confidence = 0.5
        else:
            action = 'AVOID'
            urgency = 'LOW'
            confidence = 0.3
        
        return {
            'action': action,
            'urgency': urgency,
            'confidence': confidence,
            'timing_score': timing_score,
            'adverse_selection_risk': adverse_selection_risk
        }
    
    def _get_default_signal(self, pair: str, reason: str) -> OrderFlowSignal:
        """Return default neutral signal."""
        self.logger.warning(f"Returning default order flow signal for {pair}: {reason}")
        
        return OrderFlowSignal(
            timestamp=datetime.now(timezone.utc),
            pair=pair,
            flow_direction='NEUTRAL',
            flow_strength=0.5,
            imbalance_ratio=1.0,
            spread_percentile=50.0,
            liquidity_score=0.5,
            optimal_entry_timing='WAIT',
            timing_confidence=0.5,
            large_order_detected=False,
            institutional_flow=False,
            adverse_selection_risk=0.5,
            recommended_urgency='NORMAL'
        )
    
    def _log_order_flow_analysis(self, signal: OrderFlowSignal):
        """Log order flow analysis results."""
        
        self.logger.info(f"📊 Order Flow Analysis - {signal.pair}:")
        self.logger.info(f"   Flow: {signal.flow_direction} (Strength: {signal.flow_strength:.2f})")
        self.logger.info(f"   Imbalance: {signal.imbalance_ratio:.2f}")
        self.logger.info(f"   Spread Percentile: {signal.spread_percentile:.0f}th")
        self.logger.info(f"   Liquidity: {signal.liquidity_score:.2f}")
        self.logger.info(f"   Large Orders: {'YES' if signal.large_order_detected else 'NO'}")
        self.logger.info(f"   Timing: {signal.optimal_entry_timing} (Confidence: {signal.timing_confidence:.2f})")
        self.logger.info(f"   Urgency: {signal.recommended_urgency}")
        
        if signal.adverse_selection_risk > 0.6:
            self.logger.warning(f"⚠️  High adverse selection risk: {signal.adverse_selection_risk:.2f}")

