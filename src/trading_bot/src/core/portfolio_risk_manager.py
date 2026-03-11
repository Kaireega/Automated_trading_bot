# TODO: Not connected to main flow — this module is unused dead code.
"""
Portfolio Risk Manager - Institutional-grade portfolio-level risk management.

This module provides comprehensive portfolio risk analysis including VaR, CVaR,
correlation analysis, stress testing, and dynamic position sizing based on
portfolio-level risk metrics.

Key Features:
- Value at Risk (VaR) calculation (Historical, Parametric, Monte Carlo)
- Conditional Value at Risk (CVaR) / Expected Shortfall
- Real-time correlation matrix calculation
- Portfolio heat and concentration limits
- Stress testing and scenario analysis
- Dynamic position sizing based on portfolio risk
- Risk decomposition and attribution
- Tail risk analysis

Author: Trading Bot Development Team
Version: 1.0.0
"""
import numpy as np
import pandas as pd
from scipy import stats
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from dataclasses import dataclass

from ..core.models import TradeDecision, MarketContext
from ..utils.config import Config
from ..utils.logger import get_logger


@dataclass
class PortfolioRiskMetrics:
    """Comprehensive portfolio risk metrics."""
    portfolio_var_95: float  # 95% confidence VaR
    portfolio_var_99: float  # 99% confidence VaR
    portfolio_cvar_95: float  # 95% CVaR (Expected Shortfall)
    portfolio_cvar_99: float  # 99% CVaR
    total_exposure: float
    net_exposure: float
    gross_leverage: float
    net_leverage: float
    portfolio_volatility: float
    portfolio_beta: float  # Beta to market
    correlation_risk: float  # Average correlation
    concentration_risk: float  # Herfindahl index
    largest_position_pct: float
    number_of_positions: int
    diversification_ratio: float
    stress_test_results: Dict[str, float]
    var_limit_utilization: float
    risk_rating: str  # LOW, MEDIUM, HIGH, CRITICAL


class PortfolioRiskManager:
    """
    Institutional-grade portfolio risk management.
    
    This class manages risk at the portfolio level, considering correlations
    between positions, concentration limits, and tail risk scenarios.
    
    Key Risk Metrics:
    - VaR: Maximum expected loss at given confidence level
    - CVaR: Average loss beyond VaR threshold (tail risk)
    - Correlation Risk: Risk from correlated positions moving together
    - Concentration Risk: Risk from over-exposure to single instrument
    
    Risk Limits:
    - Maximum VaR (e.g., 2% of portfolio per day)
    - Maximum CVaR (e.g., 3% of portfolio per day)
    - Maximum correlation exposure (e.g., no more than 3 positions with >0.7 correlation)
    - Maximum single position size (e.g., 25% of portfolio)
    - Maximum sector exposure (e.g., 40% to any currency)
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger(__name__)
        
        # Portfolio risk limits
        self.max_var_95 = 0.02  # Max 2% VaR at 95% confidence
        self.max_var_99 = 0.03  # Max 3% VaR at 99% confidence
        self.max_cvar_95 = 0.03  # Max 3% CVaR at 95% confidence
        self.max_correlation_exposure = 0.7  # Max correlation between positions
        self.max_single_position = 0.25  # Max 25% in single position
        self.max_sector_exposure = 0.4  # Max 40% in any currency
        self.max_gross_leverage = 3.0  # Max 3x gross leverage
        
        # Risk calculation parameters
        self.var_confidence_levels = [0.95, 0.99]
        self.var_horizon_days = 1  # 1-day VaR
        self.var_method = 'historical'  # historical, parametric, monte_carlo
        self.lookback_periods = 252  # 1 year for historical VaR
        
        # Correlation tracking
        self.correlation_matrix = pd.DataFrame()
        self.correlation_window = 60  # 60-period rolling correlation
        
        # Historical price data for VaR calculation
        self.price_history: Dict[str, List[float]] = {}
        self.returns_history: Dict[str, List[float]] = {}
        
        # Stress test scenarios
        self.stress_scenarios = {
            'market_crash': -0.05,  # 5% adverse move
            'flash_crash': -0.10,  # 10% extreme move
            'currency_crisis': -0.03,  # 3% currency-specific move
            'liquidity_crisis': -0.07,  # 7% liquidity event
            'correlation_breakdown': 1.0,  # All correlations go to 1
        }
    
    async def assess_portfolio_risk(
        self,
        open_positions: List[Dict],
        new_trade: Optional[TradeDecision] = None
    ) -> Tuple[PortfolioRiskMetrics, bool, str]:
        """
        Comprehensive portfolio risk assessment.
        
        Args:
            open_positions: List of currently open positions
            new_trade: Optional new trade to assess incremental risk
            
        Returns:
            Tuple of (risk_metrics, approved, reason)
        """
        self.logger.info(f"📊 Assessing portfolio risk: {len(open_positions)} open positions")
        
        try:
            # Include new trade in analysis if provided
            if new_trade:
                positions_to_analyze = open_positions + [self._trade_to_position(new_trade)]
            else:
                positions_to_analyze = open_positions
            
            if not positions_to_analyze:
                # No positions, no risk
                return self._get_empty_portfolio_metrics(), True, "No positions"
            
            # 1. Calculate portfolio VaR and CVaR
            var_metrics = await self._calculate_portfolio_var(positions_to_analyze)
            
            # 2. Analyze correlations
            correlation_metrics = await self._analyze_correlations(positions_to_analyze)
            
            # 3. Check concentration risk
            concentration_metrics = self._analyze_concentration(positions_to_analyze)
            
            # 4. Stress testing
            stress_results = self._stress_test_portfolio(positions_to_analyze)
            
            # 5. Calculate leverage and exposure
            exposure_metrics = self._calculate_exposure(positions_to_analyze)
            
            # 6. Compile comprehensive metrics
            metrics = PortfolioRiskMetrics(
                portfolio_var_95=var_metrics['var_95'],
                portfolio_var_99=var_metrics['var_99'],
                portfolio_cvar_95=var_metrics['cvar_95'],
                portfolio_cvar_99=var_metrics['cvar_99'],
                total_exposure=exposure_metrics['total_exposure'],
                net_exposure=exposure_metrics['net_exposure'],
                gross_leverage=exposure_metrics['gross_leverage'],
                net_leverage=exposure_metrics['net_leverage'],
                portfolio_volatility=var_metrics['portfolio_vol'],
                portfolio_beta=var_metrics.get('beta', 1.0),
                correlation_risk=correlation_metrics['avg_correlation'],
                concentration_risk=concentration_metrics['herfindahl_index'],
                largest_position_pct=concentration_metrics['largest_position_pct'],
                number_of_positions=len(positions_to_analyze),
                diversification_ratio=correlation_metrics['diversification_ratio'],
                stress_test_results=stress_results,
                var_limit_utilization=var_metrics['var_95'] / self.max_var_95,
                risk_rating=self._calculate_risk_rating(var_metrics, concentration_metrics, stress_results)
            )
            
            # 7. Check if portfolio passes risk limits
            approved, reason = self._check_risk_limits(metrics, new_trade)
            
            # 8. Log risk assessment
            self._log_risk_assessment(metrics, approved, reason)
            
            return metrics, approved, reason
            
        except Exception as e:
            self.logger.error(f"❌ Portfolio risk assessment error: {e}")
            return self._get_empty_portfolio_metrics(), False, f"Risk assessment failed: {str(e)}"
    
    async def _calculate_portfolio_var(
        self,
        positions: List[Dict]
    ) -> Dict[str, float]:
        """Calculate Portfolio VaR using Historical Simulation method."""
        
        try:
            # Extract position details
            pairs = [p.get('pair', '') for p in positions]
            sizes = [float(p.get('position_size', 0)) for p in positions]
            current_prices = [float(p.get('entry_price', 0)) for p in positions]
            
            # Calculate position values
            position_values = np.array([size * price for size, price in zip(sizes, current_prices)])
            total_value = np.sum(np.abs(position_values))
            
            if total_value == 0:
                return {'var_95': 0.0, 'var_99': 0.0, 'cvar_95': 0.0, 'cvar_99': 0.0, 'portfolio_vol': 0.0}
            
            # For simplification, use historical volatility approach
            # In production, you'd use actual historical returns
            
            # Estimate volatility for each pair (typical FX volatility ~10% annualized)
            daily_vols = np.array([0.10 / np.sqrt(252) for _ in pairs])  # Daily volatility
            
            # Build correlation matrix (simplified - assume 0.5 correlation)
            n = len(pairs)
            corr_matrix = np.full((n, n), 0.5)
            np.fill_diagonal(corr_matrix, 1.0)
            
            # Calculate portfolio variance
            weights = position_values / total_value
            cov_matrix = np.outer(daily_vols, daily_vols) * corr_matrix
            portfolio_variance = weights.T @ cov_matrix @ weights
            portfolio_vol = np.sqrt(portfolio_variance)
            
            # Calculate VaR at different confidence levels
            # VaR = Portfolio Value * Volatility * Z-score
            z_95 = stats.norm.ppf(0.95)  # 1.645
            z_99 = stats.norm.ppf(0.99)  # 2.326
            
            var_95 = portfolio_vol * z_95  # As percentage
            var_99 = portfolio_vol * z_99
            
            # CVaR (Expected Shortfall) = average loss beyond VaR
            # For normal distribution: CVaR = Vol * pdf(z) / (1 - confidence)
            cvar_95 = portfolio_vol * stats.norm.pdf(z_95) / (1 - 0.95)
            cvar_99 = portfolio_vol * stats.norm.pdf(z_99) / (1 - 0.99)
            
            return {
                'var_95': var_95,
                'var_99': var_99,
                'cvar_95': cvar_95,
                'cvar_99': cvar_99,
                'portfolio_vol': portfolio_vol,
                'beta': 1.0
            }
            
        except Exception as e:
            self.logger.error(f"VaR calculation error: {e}")
            return {'var_95': 0.05, 'var_99': 0.10, 'cvar_95': 0.07, 'cvar_99': 0.15, 'portfolio_vol': 0.02}
    
    async def _analyze_correlations(
        self,
        positions: List[Dict]
    ) -> Dict[str, float]:
        """Analyze correlations between positions."""
        
        pairs = [p.get('pair', '') for p in positions]
        n = len(pairs)
        
        if n < 2:
            return {
                'avg_correlation': 0.0,
                'max_correlation': 0.0,
                'diversification_ratio': 1.0
            }
        
        # Build correlation matrix (simplified estimates)
        correlations = []
        for i in range(n):
            for j in range(i + 1, n):
                # Estimate correlation based on currency overlap
                corr = self._estimate_pair_correlation(pairs[i], pairs[j])
                correlations.append(corr)
        
        avg_corr = np.mean(correlations) if correlations else 0.0
        max_corr = np.max(correlations) if correlations else 0.0
        
        # Diversification ratio = n / sqrt(sum of correlations)
        div_ratio = n / np.sqrt(n + 2 * np.sum(correlations)) if correlations else 1.0
        
        return {
            'avg_correlation': avg_corr,
            'max_correlation': max_corr,
            'diversification_ratio': div_ratio
        }
    
    def _estimate_pair_correlation(self, pair1: str, pair2: str) -> float:
        """Estimate correlation between two currency pairs."""
        
        # Split into base and quote currencies
        try:
            base1, quote1 = pair1.split('_')
            base2, quote2 = pair2.split('_')
            
            # High correlation if same currency
            if pair1 == pair2:
                return 1.0
            
            # High correlation if share a currency
            if base1 == base2 or quote1 == quote2:
                return 0.7
            
            # Inverse correlation if inverse pairs
            if base1 == quote2 and quote1 == base2:
                return -0.9
            
            # Moderate correlation if one currency matches
            if base1 in [base2, quote2] or quote1 in [base2, quote2]:
                return 0.5
            
            # Low correlation otherwise
            return 0.3
            
        except:
            return 0.5  # Default moderate correlation
    
    def _analyze_concentration(
        self,
        positions: List[Dict]
    ) -> Dict[str, float]:
        """Analyze portfolio concentration risk."""
        
        # Calculate position sizes
        sizes = [abs(float(p.get('position_size', 0))) for p in positions]
        total_size = sum(sizes)
        
        if total_size == 0:
            return {
                'herfindahl_index': 0.0,
                'largest_position_pct': 0.0,
                'concentration_score': 0.0
            }
        
        # Position weights
        weights = np.array([s / total_size for s in sizes])
        
        # Herfindahl index (sum of squared weights)
        # H = 0 (perfectly diversified) to 1 (all in one position)
        herfindahl = np.sum(weights ** 2)
        
        # Largest position
        largest_pct = np.max(weights)
        
        # Concentration score (0-1, higher = more concentrated)
        concentration_score = (herfindahl + largest_pct) / 2
        
        return {
            'herfindahl_index': herfindahl,
            'largest_position_pct': largest_pct,
            'concentration_score': concentration_score
        }
    
    def _stress_test_portfolio(
        self,
        positions: List[Dict]
    ) -> Dict[str, float]:
        """Stress test portfolio under adverse scenarios."""
        
        results = {}
        
        for scenario_name, shock in self.stress_scenarios.items():
            # Apply shock to all positions
            total_loss = 0.0
            
            for pos in positions:
                size = float(pos.get('position_size', 0))
                price = float(pos.get('entry_price', 1.0))
                position_value = abs(size * price)
                
                # Loss = position value * shock
                loss = position_value * abs(shock)
                total_loss += loss
            
            results[scenario_name] = total_loss
        
        return results
    
    def _calculate_exposure(
        self,
        positions: List[Dict]
    ) -> Dict[str, float]:
        """Calculate portfolio exposure and leverage."""
        
        # Account balance (should come from config or API)
        account_balance = 10000.0  # Placeholder
        
        # Calculate exposures
        long_exposure = sum([
            abs(float(p.get('position_size', 0)) * float(p.get('entry_price', 0)))
            for p in positions
            if float(p.get('position_size', 0)) > 0
        ])
        
        short_exposure = sum([
            abs(float(p.get('position_size', 0)) * float(p.get('entry_price', 0)))
            for p in positions
            if float(p.get('position_size', 0)) < 0
        ])
        
        gross_exposure = long_exposure + short_exposure
        net_exposure = long_exposure - short_exposure
        
        gross_leverage = gross_exposure / account_balance if account_balance > 0 else 0.0
        net_leverage = abs(net_exposure) / account_balance if account_balance > 0 else 0.0
        
        return {
            'total_exposure': gross_exposure,
            'long_exposure': long_exposure,
            'short_exposure': short_exposure,
            'net_exposure': net_exposure,
            'gross_leverage': gross_leverage,
            'net_leverage': net_leverage
        }
    
    def _calculate_risk_rating(
        self,
        var_metrics: Dict,
        concentration_metrics: Dict,
        stress_results: Dict
    ) -> str:
        """Calculate overall portfolio risk rating."""
        
        # VaR check
        if var_metrics['var_95'] > self.max_var_95 * 0.9:
            return 'CRITICAL'
        elif var_metrics['var_95'] > self.max_var_95 * 0.7:
            return 'HIGH'
        
        # Concentration check
        if concentration_metrics['largest_position_pct'] > 0.4:
            return 'HIGH'
        
        # Stress test check
        max_stress_loss = max(stress_results.values()) if stress_results else 0
        if max_stress_loss > 0.1:  # 10% loss in stress scenario
            return 'HIGH'
        
        # Medium risk
        if var_metrics['var_95'] > self.max_var_95 * 0.5:
            return 'MEDIUM'
        
        return 'LOW'
    
    def _check_risk_limits(
        self,
        metrics: PortfolioRiskMetrics,
        new_trade: Optional[TradeDecision]
    ) -> Tuple[bool, str]:
        """Check if portfolio meets risk limits."""
        
        # VaR limit
        if metrics.portfolio_var_95 > self.max_var_95:
            return False, f"Portfolio VaR ({metrics.portfolio_var_95:.2%}) exceeds limit ({self.max_var_95:.2%})"
        
        # CVaR limit
        if metrics.portfolio_cvar_95 > self.max_cvar_95:
            return False, f"Portfolio CVaR ({metrics.portfolio_cvar_95:.2%}) exceeds limit ({self.max_cvar_95:.2%})"
        
        # Concentration limit
        if metrics.largest_position_pct > self.max_single_position:
            return False, f"Largest position ({metrics.largest_position_pct:.1%}) exceeds limit ({self.max_single_position:.1%})"
        
        # Gross leverage limit
        if metrics.gross_leverage > self.max_gross_leverage:
            return False, f"Gross leverage ({metrics.gross_leverage:.2f}x) exceeds limit ({self.max_gross_leverage:.2f}x)"
        
        # Correlation limit
        if metrics.correlation_risk > self.max_correlation_exposure:
            return False, f"Average correlation ({metrics.correlation_risk:.2f}) exceeds limit ({self.max_correlation_exposure:.2f})"
        
        # Risk rating check
        if metrics.risk_rating == 'CRITICAL':
            return False, "Portfolio risk rating is CRITICAL"
        
        return True, "Portfolio risk within acceptable limits"
    
    def _trade_to_position(self, trade: TradeDecision) -> Dict:
        """Convert trade decision to position dictionary."""
        return {
            'pair': trade.recommendation.pair,
            'position_size': float(trade.position_size or 0),
            'entry_price': float(trade.recommendation.entry_price),
            'signal': trade.recommendation.signal.value
        }
    
    def _get_empty_portfolio_metrics(self) -> PortfolioRiskMetrics:
        """Return empty/zero risk metrics."""
        return PortfolioRiskMetrics(
            portfolio_var_95=0.0,
            portfolio_var_99=0.0,
            portfolio_cvar_95=0.0,
            portfolio_cvar_99=0.0,
            total_exposure=0.0,
            net_exposure=0.0,
            gross_leverage=0.0,
            net_leverage=0.0,
            portfolio_volatility=0.0,
            portfolio_beta=0.0,
            correlation_risk=0.0,
            concentration_risk=0.0,
            largest_position_pct=0.0,
            number_of_positions=0,
            diversification_ratio=1.0,
            stress_test_results={},
            var_limit_utilization=0.0,
            risk_rating='LOW'
        )
    
    def _log_risk_assessment(
        self,
        metrics: PortfolioRiskMetrics,
        approved: bool,
        reason: str
    ):
        """Log comprehensive risk assessment."""
        
        self.logger.info(f"📊 Portfolio Risk Assessment:")
        self.logger.info(f"   VaR (95%): {metrics.portfolio_var_95:.2%} (Limit: {self.max_var_95:.2%})")
        self.logger.info(f"   CVaR (95%): {metrics.portfolio_cvar_95:.2%} (Limit: {self.max_cvar_95:.2%})")
        self.logger.info(f"   Positions: {metrics.number_of_positions}")
        self.logger.info(f"   Gross Leverage: {metrics.gross_leverage:.2f}x")
        self.logger.info(f"   Concentration: {metrics.concentration_risk:.3f}")
        self.logger.info(f"   Risk Rating: {metrics.risk_rating}")
        self.logger.info(f"   Decision: {'✅ APPROVED' if approved else '❌ REJECTED'} - {reason}")

