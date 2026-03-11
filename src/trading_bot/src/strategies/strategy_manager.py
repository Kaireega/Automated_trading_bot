"""
Strategy Manager - Orchestrates multiple strategies and generates consensus signals.

This module manages the portfolio of strategies, collects signals, and generates
weighted consensus recommendations.
"""
import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Any
from decimal import Decimal
import statistics

from ..core.models import (
    CandleData, TechnicalIndicators, TradeSignal, MarketCondition,
    TradeRecommendation
)
from ..utils.config import Config
from ..utils.logger import get_logger
from .strategy_base import BaseStrategy, StrategySignal
from .strategy_registry import StrategyRegistry

# Import comprehensive debugging utilities
from trading_bot.src.utils.debug_utils import (
    debug_tracker, debug_line, debug_variable, debug_context, 
    debug_performance, debug_data_flow, debug_api_call, 
    debug_trade_decision, debug_strategy_execution, debug_risk_calculation,
    debug_indicator_calculation, debug_backtest_step, debug_entry_point,
    debug_exit_point, debug_conditional, debug_loop_iteration,
    get_debug_summary, export_debug_report
)


class StrategyManager:
    """
    Manages multiple trading strategies and generates consensus signals.
    
    Responsibilities:
    - Load and initialize strategies from config
    - Collect signals from all applicable strategies
    - Calculate weighted consensus
    - Track strategy performance
    - Dynamic rebalancing (future)
    """
    
    @debug_line

    
    def __init__(self, config: Config):
        """
        Initialize Strategy Manager.
        
        Args:
            config: Trading configuration
        """
        self.config = config
        self.logger = get_logger(__name__)
        
        # Strategy portfolio
        self.strategies: List[BaseStrategy] = []
        self.strategy_performance: Dict[str, Dict[str, Any]] = {}
        
        # Load strategy portfolio settings
        self.portfolio_config = config.get('strategy_portfolio', {})
        self.enabled = self.portfolio_config.get('enabled', False)
        self.selection_mode = self.portfolio_config.get('selection', {}).get('mode', 'weighted_ensemble')
        self.min_strategies_agreeing = self.portfolio_config.get('selection', {}).get('min_strategies_agreeing', 2)
        self.confidence_weighting = self.portfolio_config.get('selection', {}).get('confidence_weighting', True)
        
        # Initialize strategies
        if self.enabled:
            self._initialize_strategies()
        else:
            self.logger.warning("⚠️ Multi-strategy framework is DISABLED in config")
    
    @debug_line

    
    def _initialize_strategies(self):
        """Load and initialize all strategies from config."""
        strategy_configs = self.portfolio_config.get('strategies', [])
        
        if not strategy_configs:
            self.logger.warning("⚠️ No strategies defined in config")
            return
        
        self.logger.info(f"🔄 Initializing {len(strategy_configs)} strategies...")
        
        for strategy_config in strategy_configs:
            try:
                strategy_name = strategy_config.get('name')
                strategy_type = strategy_config.get('type')
                
                # Get strategy class from registry
                strategy_class = StrategyRegistry.get_strategy_class(strategy_name)
                
                if strategy_class:
                    # Instantiate strategy
                    strategy = strategy_class(
                        name=strategy_name,
                        strategy_type=strategy_type,
                        config=strategy_config
                    )
                    self.strategies.append(strategy)
                    
                    # Initialize performance tracking
                    self.strategy_performance[strategy_name] = {
                        'signals_generated': 0,
                        'signals_accepted': 0,
                        'win_count': 0,
                        'loss_count': 0,
                        'total_pnl': 0.0,
                        'allocation': strategy.allocation
                    }
                    
                    self.logger.info(f"✅ Loaded: {strategy_name} ({strategy_type}, {strategy.allocation}%)")
                else:
                    self.logger.warning(f"⚠️ Strategy class not found: {strategy_name}")
                    
            except Exception as e:
                self.logger.error(f"❌ Error loading strategy {strategy_config.get('name')}: {e}")
        
        total_allocation = sum(s.allocation for s in self.strategies)
        self.logger.info(f"✅ Loaded {len(self.strategies)} strategies (Total allocation: {total_allocation}%)")
    
    async def generate_consensus_signal(
        self,
        pair: str,
        candles: List[CandleData],
        indicators: TechnicalIndicators,
        market_condition: MarketCondition,
        current_time: Optional[datetime] = None,
        regime: Optional[str] = None
    ) -> Optional[TradeRecommendation]:
        """
        Generate consensus signal from all applicable strategies.

        Args:
            pair: Currency pair
            candles: List of candle data
            indicators: Technical indicators
            market_condition: Current market condition
            current_time: Current time (for session-based strategies)
            regime: Market regime string from MarketRegimeDetector

        Returns:
            TradeRecommendation with consensus signal or None
        """
        if not self.enabled:
            return None

        if not self.strategies:
            self.logger.warning("⚠️ No strategies loaded")
            return None

        # --- REGIME-BASED ELIGIBILITY GATE ---
        REGIME_ALLOWED_TYPES = {
            'TRENDING_UP':    ['trend_momentum', 'session_based', 'breakout'],
            'TRENDING_DOWN':  ['trend_momentum', 'session_based', 'breakout'],
            'RANGING':        ['mean_reversion'],
            'VOLATILE':       ['breakout', 'session_based'],
            'BREAKOUT':       ['breakout', 'session_based', 'trend_momentum'],
            'CONSOLIDATION':  ['mean_reversion'],
            'REVERSAL':       ['mean_reversion', 'trend_momentum'],
            'UNKNOWN':        ['trend_momentum', 'session_based', 'breakout', 'mean_reversion'],
        }

        current_regime = (regime or 'UNKNOWN').upper()
        allowed_types = REGIME_ALLOWED_TYPES.get(current_regime, REGIME_ALLOWED_TYPES['UNKNOWN'])

        eligible_strategies = [
            s for s in self.strategies
            if s.allocation > 0 and s.strategy_type in allowed_types
        ]

        self.logger.debug(
            f"Regime: {current_regime} | Eligible: {[s.name for s in eligible_strategies]}"
        )
        # --- END REGIME GATE ---

        # Collect signals from eligible strategies
        strategy_signals: List[Dict[str, Any]] = []

        for strategy in eligible_strategies:
            try:
                # Check if strategy is active now (session-based)
                if not strategy.is_active_now(current_time):
                    continue
                
                # Generate signal
                signal = await strategy.generate_signal(
                    candles=candles,
                    indicators=indicators,
                    market_condition=market_condition,
                    current_time=current_time
                )
                
                # Validate and collect signal
                if signal and strategy.validate_signal(signal):
                    strategy_signals.append({
                        'strategy_name': strategy.name,
                        'strategy_type': strategy.strategy_type,
                        'allocation': strategy.allocation,
                        'signal': signal
                    })
                    
                    # Track performance
                    self.strategy_performance[strategy.name]['signals_generated'] += 1
                    
            except Exception as e:
                self.logger.error(f"❌ Error in strategy {strategy.name}: {e}")
        
        # Check minimum strategies requirement
        if len(strategy_signals) < self.min_strategies_agreeing:
            self.logger.debug(
                f"Not enough strategies agreeing: {len(strategy_signals)} < {self.min_strategies_agreeing}"
            )
            return None
        
        # Calculate consensus based on selection mode
        if self.selection_mode == 'weighted_ensemble':
            return self._calculate_weighted_consensus(pair, strategy_signals)
        elif self.selection_mode == 'best_fit':
            return self._select_best_fit(pair, strategy_signals)
        elif self.selection_mode == 'democratic':
            return self._democratic_vote(pair, strategy_signals)
        else:
            self.logger.error(f"Unknown selection mode: {self.selection_mode}")
            return None
    
    def _calculate_weighted_consensus(
        self,
        pair: str,
        signals: List[Dict[str, Any]]
    ) -> Optional[TradeRecommendation]:
        """
        Calculate weighted consensus from multiple strategy signals.
        
        Args:
            pair: Currency pair
            signals: List of strategy signals with metadata
            
        Returns:
            Consensus TradeRecommendation or None
        """
        buy_weight = 0.0
        sell_weight = 0.0
        total_weight = 0.0
        
        buy_signals = []
        sell_signals = []
        
        for sig_data in signals:
            allocation = sig_data['allocation']
            signal = sig_data['signal']
            confidence = signal.confidence
            
            # Calculate weight (allocation * confidence if weighting enabled)
            if self.confidence_weighting:
                weight = (allocation / 100.0) * confidence
            else:
                weight = allocation / 100.0
            
            if signal.signal == TradeSignal.BUY:
                buy_weight += weight
                buy_signals.append(sig_data)
            elif signal.signal == TradeSignal.SELL:
                sell_weight += weight
                sell_signals.append(sig_data)
            
            total_weight += (allocation / 100.0)
        
        # Normalize weights
        if total_weight == 0:
            return None
        
        buy_score = buy_weight / total_weight
        sell_score = sell_weight / total_weight
        
        # Determine consensus — read from config (YAML has 0.75)
        consensus_threshold = getattr(self.config.multi_timeframe, 'consensus_threshold', 0.30)
        
        if buy_score > consensus_threshold and buy_score > sell_score:
            return self._create_consensus_recommendation(
                pair=pair,
                signal_type=TradeSignal.BUY,
                confidence=buy_score,
                signals=buy_signals
            )
        elif sell_score > consensus_threshold and sell_score > buy_score:
            return self._create_consensus_recommendation(
                pair=pair,
                signal_type=TradeSignal.SELL,
                confidence=sell_score,
                signals=sell_signals
            )
        
        return None
    
    def _select_best_fit(
        self,
        pair: str,
        signals: List[Dict[str, Any]]
    ) -> Optional[TradeRecommendation]:
        """
        Select the single best signal based on confidence and allocation.
        
        Args:
            pair: Currency pair
            signals: List of strategy signals
            
        Returns:
            Best signal as TradeRecommendation
        """
        if not signals:
            return None
        
        # Sort by confidence * allocation
        best_signal_data = max(
            signals,
            key=lambda s: s['signal'].confidence * (s['allocation'] / 100.0)
        )
        
        signal = best_signal_data['signal']
        
        if signal.signal == TradeSignal.HOLD:
            return None
        
        return self._create_consensus_recommendation(
            pair=pair,
            signal_type=signal.signal,
            confidence=signal.confidence,
            signals=[best_signal_data]
        )
    
    def _democratic_vote(
        self,
        pair: str,
        signals: List[Dict[str, Any]]
    ) -> Optional[TradeRecommendation]:
        """
        Democratic voting - each strategy gets one vote.
        
        Args:
            pair: Currency pair
            signals: List of strategy signals
            
        Returns:
            Majority vote as TradeRecommendation
        """
        buy_votes = sum(1 for s in signals if s['signal'].signal == TradeSignal.BUY)
        sell_votes = sum(1 for s in signals if s['signal'].signal == TradeSignal.SELL)
        
        total_votes = len(signals)
        
        if buy_votes > sell_votes and buy_votes >= self.min_strategies_agreeing:
            buy_signals = [s for s in signals if s['signal'].signal == TradeSignal.BUY]
            avg_confidence = statistics.mean(s['signal'].confidence for s in buy_signals)
            
            return self._create_consensus_recommendation(
                pair=pair,
                signal_type=TradeSignal.BUY,
                confidence=avg_confidence,
                signals=buy_signals
            )
        elif sell_votes > buy_votes and sell_votes >= self.min_strategies_agreeing:
            sell_signals = [s for s in signals if s['signal'].signal == TradeSignal.SELL]
            avg_confidence = statistics.mean(s['signal'].confidence for s in sell_signals)
            
            return self._create_consensus_recommendation(
                pair=pair,
                signal_type=TradeSignal.SELL,
                confidence=avg_confidence,
                signals=sell_signals
            )
        
        return None
    
    def _create_consensus_recommendation(
        self,
        pair: str,
        signal_type: TradeSignal,
        confidence: float,
        signals: List[Dict[str, Any]]
    ) -> TradeRecommendation:
        """
        Create a TradeRecommendation from consensus signals.
        
        Args:
            pair: Currency pair
            signal_type: BUY or SELL
            confidence: Consensus confidence
            signals: Contributing signals
            
        Returns:
            TradeRecommendation
        """
        # Aggregate entry, stop, target from contributing signals
        entries = []
        stops = []
        targets = []
        reasoning_parts = []
        
        for sig_data in signals:
            signal = sig_data['signal']
            strategy_name = sig_data['strategy_name']
            
            if signal.entry_price:
                entries.append(float(signal.entry_price))
            if signal.stop_loss:
                stops.append(float(signal.stop_loss))
            if signal.take_profit:
                targets.append(float(signal.take_profit))
            
            reasoning_parts.append(f"{strategy_name}: {signal.reasoning}")
        
        # Calculate averages
        entry_price = Decimal(str(statistics.mean(entries))) if entries else None
        stop_loss = Decimal(str(statistics.mean(stops))) if stops else None
        take_profit = Decimal(str(statistics.mean(targets))) if targets else None
        
        # Combine reasoning
        strategy_names = [s['strategy_name'] for s in signals]
        reasoning = f"Multi-strategy consensus ({len(signals)} strategies: {', '.join(strategy_names[:3])})"
        if len(strategy_names) > 3:
            reasoning += f" +{len(strategy_names) - 3} more"
        
        return TradeRecommendation(
            pair=pair,
            signal=signal_type,
            confidence=confidence,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            reasoning=reasoning,
            metadata={
                'strategy_count': len(signals),
                'strategies': strategy_names,
                'detailed_reasoning': reasoning_parts
            }
        )
    
    def get_strategy_count(self) -> int:
        """Get number of loaded strategies."""
        return len(self.strategies)
    
    def get_strategy_performance(self) -> Dict[str, Dict[str, Any]]:
        """Get performance metrics for all strategies."""
        return self.strategy_performance.copy()
    
    @debug_line

    
    def update_strategy_performance(self, strategy_name: str, won: bool, pnl: float):
        """
        Update strategy performance after trade completion.
        
        Args:
            strategy_name: Name of strategy
            won: Whether trade was profitable
            pnl: Profit/loss amount
        """
        if strategy_name in self.strategy_performance:
            perf = self.strategy_performance[strategy_name]
            perf['signals_accepted'] += 1
            if won:
                perf['win_count'] += 1
            else:
                perf['loss_count'] += 1
            perf['total_pnl'] += pnl









