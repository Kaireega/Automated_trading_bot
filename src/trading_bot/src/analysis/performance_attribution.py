"""
Performance Attribution Engine - Track what works and what doesn't.

This module provides comprehensive performance attribution to understand
exactly where returns are coming from and identify improvement opportunities.

Key Features:
- Factor attribution (technical, fundamental, timing, execution)
- Strategy component attribution
- Market regime attribution
- Time-based attribution
- Instrument attribution
- Win/Loss analysis by category
- Continuous learning and optimization

Author: Trading Bot Development Team
Version: 1.0.0
"""
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

from ..utils.config import Config
from ..utils.logger import get_logger


@dataclass
class TradeAttribution:
    """Attribution breakdown for a single trade."""
    trade_id: str
    pair: str
    entry_time: datetime
    exit_time: Optional[datetime]
    pnl: float
    pnl_pct: float
    
    # Factor attribution
    technical_contribution: float
    fundamental_contribution: float
    timing_contribution: float
    execution_contribution: float
    luck_contribution: float
    
    # Strategy components
    entry_quality_score: float
    exit_quality_score: float
    risk_management_score: float
    
    # Market context
    market_regime: str
    volatility_regime: str
    liquidity_regime: str
    
    # Performance categorization
    category: str  # 'BIG_WIN', 'SMALL_WIN', 'SMALL_LOSS', 'BIG_LOSS'
    outlier: bool


@dataclass
class AttributionReport:
    """Comprehensive performance attribution report."""
    period_start: datetime
    period_end: datetime
    total_pnl: float
    total_trades: int
    
    # Factor attribution (sum to total PnL)
    technical_pnl: float
    fundamental_pnl: float
    timing_pnl: float
    execution_pnl: float
    unexplained_pnl: float
    
    # Win/Loss breakdown
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    largest_win: float
    largest_loss: float
    
    # By market regime
    regime_attribution: Dict[str, float]
    
    # By instrument
    instrument_attribution: Dict[str, float]
    
    # By strategy component
    component_scores: Dict[str, float]
    
    # Improvement opportunities
    top_strengths: List[str]
    top_weaknesses: List[str]
    actionable_insights: List[str]


class PerformanceAttributionEngine:
    """
    Professional performance attribution and continuous improvement.
    
    This class tracks every aspect of trading performance to identify:
    - What's working well (double down on strengths)
    - What's not working (fix or remove weaknesses)
    - Hidden patterns (market regimes, time of day, etc.)
    - Optimization opportunities
    
    Key Insights:
    - Which signals generate best returns?
    - Which market conditions favor the strategy?
    - Is execution quality costing money?
    - Are we entering/exiting at optimal times?
    - Which instruments should we focus on?
    
    Continuous Learning:
    - Adapt to changing market conditions
    - Identify strategy decay
    - Optimize parameters based on what works
    - Remove components that don't add value
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger(__name__)
        
        # Trade attribution history
        self.trade_attributions: List[TradeAttribution] = []
        
        # Performance tracking
        self.daily_pnl: Dict[str, float] = {}
        self.monthly_pnl: Dict[str, float] = {}
        
        # Factor weights for attribution
        self.attribution_weights = {
            'technical': 0.4,
            'fundamental': 0.2,
            'timing': 0.2,
            'execution': 0.2
        }
        
    def attribute_trade(
        self,
        trade_details: Dict,
        signals: Dict,
        execution_details: Dict,
        market_context: Dict
    ) -> TradeAttribution:
        """
        Perform attribution analysis on a completed trade.
        
        Args:
            trade_details: Trade execution details (entry, exit, PnL)
            signals: Technical and fundamental signals that triggered trade
            execution_details: Execution quality metrics
            market_context: Market regime and conditions
            
        Returns:
            TradeAttribution with detailed breakdown
        """
        self.logger.info(f"📊 Attributing trade: {trade_details.get('trade_id')}")
        
        try:
            # Extract trade info
            trade_id = trade_details.get('trade_id', 'UNKNOWN')
            pair = trade_details.get('pair', 'UNKNOWN')
            entry_time = trade_details.get('entry_time', datetime.now(timezone.utc))
            exit_time = trade_details.get('exit_time')
            pnl = float(trade_details.get('pnl', 0.0))
            pnl_pct = float(trade_details.get('pnl_pct', 0.0))
            
            # 1. Calculate factor contributions
            technical_contrib = self._calculate_technical_contribution(
                pnl, signals.get('technical', {}), market_context
            )
            
            fundamental_contrib = self._calculate_fundamental_contribution(
                pnl, signals.get('fundamental', {}), market_context
            )
            
            timing_contrib = self._calculate_timing_contribution(
                pnl, trade_details, execution_details
            )
            
            execution_contrib = self._calculate_execution_contribution(
                pnl, execution_details
            )
            
            # Unexplained = luck/noise
            explained = (technical_contrib + fundamental_contrib + 
                        timing_contrib + execution_contrib)
            luck_contrib = pnl - explained
            
            # 2. Calculate quality scores
            entry_score = self._calculate_entry_quality(signals, execution_details)
            exit_score = self._calculate_exit_quality(trade_details, execution_details)
            risk_score = self._calculate_risk_management_quality(trade_details)
            
            # 3. Categorize trade
            category = self._categorize_trade(pnl_pct)
            outlier = abs(pnl_pct) > 0.05  # >5% is outlier
            
            # 4. Build attribution
            attribution = TradeAttribution(
                trade_id=trade_id,
                pair=pair,
                entry_time=entry_time,
                exit_time=exit_time,
                pnl=pnl,
                pnl_pct=pnl_pct,
                technical_contribution=technical_contrib,
                fundamental_contribution=fundamental_contrib,
                timing_contribution=timing_contrib,
                execution_contribution=execution_contrib,
                luck_contribution=luck_contrib,
                entry_quality_score=entry_score,
                exit_quality_score=exit_score,
                risk_management_score=risk_score,
                market_regime=market_context.get('regime', 'UNKNOWN'),
                volatility_regime=market_context.get('volatility', 'NORMAL'),
                liquidity_regime=market_context.get('liquidity', 'NORMAL'),
                category=category,
                outlier=outlier
            )
            
            # Store attribution
            self.trade_attributions.append(attribution)
            
            self._log_trade_attribution(attribution)
            
            return attribution
            
        except Exception as e:
            self.logger.error(f"❌ Trade attribution error: {e}")
            return self._get_default_attribution(trade_details)
    
    def generate_attribution_report(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> AttributionReport:
        """
        Generate comprehensive attribution report for period.
        
        Args:
            start_date: Report start date (default: 30 days ago)
            end_date: Report end date (default: now)
            
        Returns:
            AttributionReport with insights and recommendations
        """
        if start_date is None:
            start_date = datetime.now(timezone.utc) - timedelta(days=30)
        if end_date is None:
            end_date = datetime.now(timezone.utc)
        
        self.logger.info(f"📊 Generating attribution report: {start_date.date()} to {end_date.date()}")
        
        # Filter trades in period
        period_trades = [
            t for t in self.trade_attributions
            if start_date <= t.entry_time <= end_date
        ]
        
        if not period_trades:
            return self._get_empty_report(start_date, end_date)
        
        # Calculate aggregate metrics
        total_pnl = sum(t.pnl for t in period_trades)
        total_trades = len(period_trades)
        
        # Factor attribution
        technical_pnl = sum(t.technical_contribution for t in period_trades)
        fundamental_pnl = sum(t.fundamental_contribution for t in period_trades)
        timing_pnl = sum(t.timing_contribution for t in period_trades)
        execution_pnl = sum(t.execution_contribution for t in period_trades)
        unexplained_pnl = sum(t.luck_contribution for t in period_trades)
        
        # Win/Loss metrics
        wins = [t for t in period_trades if t.pnl > 0]
        losses = [t for t in period_trades if t.pnl < 0]
        
        win_rate = len(wins) / total_trades if total_trades > 0 else 0
        avg_win = np.mean([t.pnl for t in wins]) if wins else 0
        avg_loss = np.mean([t.pnl for t in losses]) if losses else 0
        
        gross_profit = sum(t.pnl for t in wins)
        gross_loss = abs(sum(t.pnl for t in losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        largest_win = max([t.pnl for t in wins]) if wins else 0
        largest_loss = min([t.pnl for t in losses]) if losses else 0
        
        # Regime attribution
        regime_attribution = self._calculate_regime_attribution(period_trades)
        
        # Instrument attribution
        instrument_attribution = self._calculate_instrument_attribution(period_trades)
        
        # Component scores
        component_scores = self._calculate_component_scores(period_trades)
        
        # Identify strengths and weaknesses
        strengths, weaknesses = self._identify_strengths_weaknesses(
            period_trades, regime_attribution, instrument_attribution, component_scores
        )
        
        # Generate actionable insights
        insights = self._generate_insights(
            period_trades, regime_attribution, component_scores
        )
        
        report = AttributionReport(
            period_start=start_date,
            period_end=end_date,
            total_pnl=total_pnl,
            total_trades=total_trades,
            technical_pnl=technical_pnl,
            fundamental_pnl=fundamental_pnl,
            timing_pnl=timing_pnl,
            execution_pnl=execution_pnl,
            unexplained_pnl=unexplained_pnl,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            largest_win=largest_win,
            largest_loss=largest_loss,
            regime_attribution=regime_attribution,
            instrument_attribution=instrument_attribution,
            component_scores=component_scores,
            top_strengths=strengths,
            top_weaknesses=weaknesses,
            actionable_insights=insights
        )
        
        self._log_attribution_report(report)
        
        return report
    
    def _calculate_technical_contribution(
        self,
        pnl: float,
        technical_signals: Dict,
        market_context: Dict
    ) -> float:
        """Calculate PnL contribution from technical signals."""
        
        # Signal strength
        signal_strength = technical_signals.get('confluence_score', 0.5)
        
        # If profitable and high signal strength, attribute to technical
        if pnl > 0:
            contribution = pnl * signal_strength * self.attribution_weights['technical']
        else:
            # If losing trade, technical might have saved money or caused loss
            contribution = pnl * signal_strength * self.attribution_weights['technical']
        
        return contribution
    
    def _calculate_fundamental_contribution(
        self,
        pnl: float,
        fundamental_signals: Dict,
        market_context: Dict
    ) -> float:
        """Calculate PnL contribution from fundamental analysis."""
        
        # Fundamental alignment score
        fundamental_score = fundamental_signals.get('overall_score', 0.5)
        
        contribution = pnl * fundamental_score * self.attribution_weights['fundamental']
        
        return contribution
    
    def _calculate_timing_contribution(
        self,
        pnl: float,
        trade_details: Dict,
        execution_details: Dict
    ) -> float:
        """Calculate PnL contribution from entry/exit timing."""
        
        # Timing quality based on entry/exit relative to highs/lows
        timing_score = execution_details.get('timing_quality', 0.5)
        
        contribution = pnl * timing_score * self.attribution_weights['timing']
        
        return contribution
    
    def _calculate_execution_contribution(
        self,
        pnl: float,
        execution_details: Dict
    ) -> float:
        """Calculate PnL contribution/cost from execution quality."""
        
        # Slippage and execution costs
        slippage_bps = execution_details.get('slippage_bps', 2.0)
        
        # Negative contribution if poor execution
        execution_cost = -(slippage_bps / 10000) * abs(pnl) * 2  # Approximate
        
        return execution_cost
    
    def _calculate_entry_quality(
        self,
        signals: Dict,
        execution_details: Dict
    ) -> float:
        """Calculate entry quality score (0-1)."""
        
        technical = signals.get('technical', {})
        fundamental = signals.get('fundamental', {})
        
        # Combine signal strengths
        tech_score = technical.get('confluence_score', 0.5)
        fund_score = fundamental.get('overall_score', 0.5)
        exec_score = 1.0 - (execution_details.get('slippage_bps', 2.0) / 10.0)
        
        entry_score = (tech_score * 0.5 + fund_score * 0.3 + exec_score * 0.2)
        
        return max(0.0, min(1.0, entry_score))
    
    def _calculate_exit_quality(
        self,
        trade_details: Dict,
        execution_details: Dict
    ) -> float:
        """Calculate exit quality score (0-1)."""
        
        # Exit type
        exit_type = trade_details.get('exit_type', 'UNKNOWN')
        
        if exit_type == 'TAKE_PROFIT':
            return 0.9
        elif exit_type == 'STOP_LOSS':
            return 0.3
        elif exit_type == 'SIGNAL_REVERSAL':
            return 0.7
        elif exit_type == 'MANUAL':
            return 0.5
        else:
            return 0.5
    
    def _calculate_risk_management_quality(
        self,
        trade_details: Dict
    ) -> float:
        """Calculate risk management quality (0-1)."""
        
        # Risk/reward ratio
        risk_reward = trade_details.get('risk_reward_ratio', 1.0)
        
        # Position sizing appropriateness
        position_size_pct = trade_details.get('position_size_pct', 0.02)
        
        # Good if R:R >= 1.5 and position size <= 3%
        rr_score = min(1.0, risk_reward / 1.5)
        size_score = 1.0 if position_size_pct <= 0.03 else 0.7
        
        return (rr_score * 0.6 + size_score * 0.4)
    
    def _categorize_trade(self, pnl_pct: float) -> str:
        """Categorize trade by PnL magnitude."""
        
        if pnl_pct > 0.03:
            return 'BIG_WIN'
        elif pnl_pct > 0:
            return 'SMALL_WIN'
        elif pnl_pct > -0.02:
            return 'SMALL_LOSS'
        else:
            return 'BIG_LOSS'
    
    def _calculate_regime_attribution(
        self,
        trades: List[TradeAttribution]
    ) -> Dict[str, float]:
        """Calculate PnL by market regime."""
        
        regime_pnl = defaultdict(float)
        
        for trade in trades:
            regime_pnl[trade.market_regime] += trade.pnl
        
        return dict(regime_pnl)
    
    def _calculate_instrument_attribution(
        self,
        trades: List[TradeAttribution]
    ) -> Dict[str, float]:
        """Calculate PnL by instrument."""
        
        instrument_pnl = defaultdict(float)
        
        for trade in trades:
            instrument_pnl[trade.pair] += trade.pnl
        
        return dict(instrument_pnl)
    
    def _calculate_component_scores(
        self,
        trades: List[TradeAttribution]
    ) -> Dict[str, float]:
        """Calculate average scores for strategy components."""
        
        if not trades:
            return {}
        
        return {
            'avg_entry_quality': np.mean([t.entry_quality_score for t in trades]),
            'avg_exit_quality': np.mean([t.exit_quality_score for t in trades]),
            'avg_risk_management': np.mean([t.risk_management_score for t in trades]),
            'technical_effectiveness': sum(t.technical_contribution for t in trades) / len(trades),
            'fundamental_effectiveness': sum(t.fundamental_contribution for t in trades) / len(trades),
        }
    
    def _identify_strengths_weaknesses(
        self,
        trades: List[TradeAttribution],
        regime_attribution: Dict,
        instrument_attribution: Dict,
        component_scores: Dict
    ) -> Tuple[List[str], List[str]]:
        """Identify top strengths and weaknesses."""
        
        strengths = []
        weaknesses = []
        
        # Check regime performance
        for regime, pnl in regime_attribution.items():
            if pnl > 0:
                strengths.append(f"Strong in {regime} market (+${pnl:.2f})")
            else:
                weaknesses.append(f"Weak in {regime} market (-${abs(pnl):.2f})")
        
        # Check component scores
        for component, score in component_scores.items():
            if score > 0.7:
                strengths.append(f"High {component}: {score:.2f}")
            elif score < 0.4:
                weaknesses.append(f"Low {component}: {score:.2f}")
        
        # Check instrument performance
        sorted_instruments = sorted(instrument_attribution.items(), key=lambda x: x[1], reverse=True)
        if sorted_instruments:
            best_pair, best_pnl = sorted_instruments[0]
            if best_pnl > 0:
                strengths.append(f"Best instrument: {best_pair} (+${best_pnl:.2f})")
            
            worst_pair, worst_pnl = sorted_instruments[-1]
            if worst_pnl < 0:
                weaknesses.append(f"Worst instrument: {worst_pair} (-${abs(worst_pnl):.2f})")
        
        return strengths[:5], weaknesses[:5]
    
    def _generate_insights(
        self,
        trades: List[TradeAttribution],
        regime_attribution: Dict,
        component_scores: Dict
    ) -> List[str]:
        """Generate actionable insights."""
        
        insights = []
        
        # Entry quality insight
        if component_scores.get('avg_entry_quality', 0.5) < 0.5:
            insights.append("⚠️ Low entry quality - consider stricter signal filters")
        
        # Exit quality insight
        if component_scores.get('avg_exit_quality', 0.5) < 0.5:
            insights.append("⚠️ Poor exit execution - review exit rules")
        
        # Regime-specific insights
        for regime, pnl in regime_attribution.items():
            if pnl < 0:
                insights.append(f"⚠️ Avoid trading in {regime} market - consistently negative")
        
        # Execution quality
        avg_execution = np.mean([t.execution_contribution for t in trades])
        if avg_execution < -50:
            insights.append("⚠️ High execution costs - optimize entry timing")
        
        # Risk management
        if component_scores.get('avg_risk_management', 0.5) < 0.6:
            insights.append("⚠️ Improve risk management - tighter stops or better R:R")
        
        return insights
    
    def _get_default_attribution(self, trade_details: Dict) -> TradeAttribution:
        """Return default attribution for error cases."""
        
        return TradeAttribution(
            trade_id=trade_details.get('trade_id', 'UNKNOWN'),
            pair=trade_details.get('pair', 'UNKNOWN'),
            entry_time=trade_details.get('entry_time', datetime.now(timezone.utc)),
            exit_time=trade_details.get('exit_time'),
            pnl=float(trade_details.get('pnl', 0.0)),
            pnl_pct=float(trade_details.get('pnl_pct', 0.0)),
            technical_contribution=0.0,
            fundamental_contribution=0.0,
            timing_contribution=0.0,
            execution_contribution=0.0,
            luck_contribution=0.0,
            entry_quality_score=0.5,
            exit_quality_score=0.5,
            risk_management_score=0.5,
            market_regime='UNKNOWN',
            volatility_regime='NORMAL',
            liquidity_regime='NORMAL',
            category='SMALL_LOSS',
            outlier=False
        )
    
    def _get_empty_report(self, start_date: datetime, end_date: datetime) -> AttributionReport:
        """Return empty report when no trades."""
        
        return AttributionReport(
            period_start=start_date,
            period_end=end_date,
            total_pnl=0.0,
            total_trades=0,
            technical_pnl=0.0,
            fundamental_pnl=0.0,
            timing_pnl=0.0,
            execution_pnl=0.0,
            unexplained_pnl=0.0,
            win_rate=0.0,
            avg_win=0.0,
            avg_loss=0.0,
            profit_factor=0.0,
            largest_win=0.0,
            largest_loss=0.0,
            regime_attribution={},
            instrument_attribution={},
            component_scores={},
            top_strengths=[],
            top_weaknesses=[],
            actionable_insights=["No trades in period"]
        )
    
    def _log_trade_attribution(self, attribution: TradeAttribution):
        """Log trade attribution results."""
        
        self.logger.info(f"📊 Trade Attribution - {attribution.trade_id}:")
        self.logger.info(f"   PnL: ${attribution.pnl:.2f} ({attribution.pnl_pct:+.2%})")
        self.logger.info(f"   Technical: ${attribution.technical_contribution:.2f}")
        self.logger.info(f"   Fundamental: ${attribution.fundamental_contribution:.2f}")
        self.logger.info(f"   Timing: ${attribution.timing_contribution:.2f}")
        self.logger.info(f"   Execution: ${attribution.execution_contribution:.2f}")
        self.logger.info(f"   Entry Quality: {attribution.entry_quality_score:.2f}")
        self.logger.info(f"   Exit Quality: {attribution.exit_quality_score:.2f}")
        self.logger.info(f"   Category: {attribution.category}")
    
    def _log_attribution_report(self, report: AttributionReport):
        """Log attribution report summary."""
        
        self.logger.info("📊 ═══════════════════════════════════════════════════════")
        self.logger.info("📊 PERFORMANCE ATTRIBUTION REPORT")
        self.logger.info(f"📊 Period: {report.period_start.date()} to {report.period_end.date()}")
        self.logger.info("📊 ═══════════════════════════════════════════════════════")
        self.logger.info(f"   Total PnL: ${report.total_pnl:.2f}")
        self.logger.info(f"   Total Trades: {report.total_trades}")
        self.logger.info(f"   Win Rate: {report.win_rate:.1%}")
        self.logger.info(f"   Profit Factor: {report.profit_factor:.2f}")
        self.logger.info("")
        self.logger.info("   Factor Attribution:")
        self.logger.info(f"     Technical:    ${report.technical_pnl:.2f}")
        self.logger.info(f"     Fundamental:  ${report.fundamental_pnl:.2f}")
        self.logger.info(f"     Timing:       ${report.timing_pnl:.2f}")
        self.logger.info(f"     Execution:    ${report.execution_pnl:.2f}")
        self.logger.info("")
        self.logger.info("   Top Strengths:")
        for strength in report.top_strengths:
            self.logger.info(f"     ✅ {strength}")
        self.logger.info("")
        self.logger.info("   Top Weaknesses:")
        for weakness in report.top_weaknesses:
            self.logger.info(f"     ⚠️  {weakness}")
        self.logger.info("")
        self.logger.info("   Actionable Insights:")
        for insight in report.actionable_insights:
            self.logger.info(f"     💡 {insight}")
        self.logger.info("📊 ═══════════════════════════════════════════════════════")

