"""
Validation framework for optimization results.
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

from .optimizer import OptimizationResult, RegimeOptimizationResult
from .backtest_engine import BacktestResult
from ..utils.config import Config
from ..utils.logger import get_logger


@dataclass
class ValidationMetrics:
    """Metrics for validation comparison."""
    sharpe_ratio: float
    profit_factor: float
    max_drawdown: float
    total_trades: int
    win_rate: float
    total_return: float
    calmar_ratio: float
    sortino_ratio: float
    avg_trade_duration: float
    trades_per_day: float


@dataclass
class ValidationResult:
    """Results from validation comparison."""
    baseline_metrics: ValidationMetrics
    optimized_metrics: ValidationMetrics
    improvement_percentages: Dict[str, float]
    is_improvement: bool
    overall_score: float
    validation_date: datetime
    test_period_days: int


class OptimizationValidator:
    """Validation framework for optimization results."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger(__name__)
        self.results_dir = Path("results/optimization_validation")
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def _extract_metrics(self, result: BacktestResult) -> ValidationMetrics:
        """Extract validation metrics from backtest result."""
        return ValidationMetrics(
            sharpe_ratio=result.sharpe_ratio,
            profit_factor=result.profit_factor,
            max_drawdown=result.max_drawdown,
            total_trades=result.total_trades,
            win_rate=result.win_rate,
            total_return=result.total_return,
            calmar_ratio=result.calmar_ratio,
            sortino_ratio=result.sortino_ratio,
            avg_trade_duration=result.avg_trade_duration,
            trades_per_day=result.trades_per_day
        )
    
    def _calculate_improvement_percentages(
        self, 
        baseline: ValidationMetrics, 
        optimized: ValidationMetrics
    ) -> Dict[str, float]:
        """Calculate improvement percentages for each metric."""
        improvements = {}
        
        # Higher is better metrics
        higher_better = [
            'sharpe_ratio', 'profit_factor', 'win_rate', 'total_return', 
            'calmar_ratio', 'sortino_ratio', 'trades_per_day'
        ]
        
        # Lower is better metrics
        lower_better = ['max_drawdown', 'avg_trade_duration']
        
        for metric in higher_better:
            baseline_val = getattr(baseline, metric)
            optimized_val = getattr(optimized, metric)
            
            if baseline_val != 0:
                improvement = ((optimized_val - baseline_val) / abs(baseline_val)) * 100
            else:
                improvement = 100.0 if optimized_val > 0 else 0.0
            
            improvements[metric] = improvement
        
        for metric in lower_better:
            baseline_val = getattr(baseline, metric)
            optimized_val = getattr(optimized, metric)
            
            if baseline_val != 0:
                improvement = ((baseline_val - optimized_val) / abs(baseline_val)) * 100
            else:
                improvement = 100.0 if optimized_val == 0 else 0.0
            
            improvements[metric] = improvement
        
        return improvements
    
    def _calculate_overall_score(self, improvements: Dict[str, float]) -> float:
        """Calculate overall improvement score."""
        # Weighted scoring based on importance
        weights = {
            'sharpe_ratio': 0.25,
            'profit_factor': 0.20,
            'max_drawdown': 0.15,
            'win_rate': 0.15,
            'total_return': 0.10,
            'calmar_ratio': 0.05,
            'sortino_ratio': 0.05,
            'trades_per_day': 0.05
        }
        
        weighted_score = 0.0
        total_weight = 0.0
        
        for metric, improvement in improvements.items():
            if metric in weights:
                weighted_score += improvement * weights[metric]
                total_weight += weights[metric]
        
        return weighted_score / total_weight if total_weight > 0 else 0.0
    
    async def validate_optimization(
        self,
        baseline_result: BacktestResult,
        optimized_result: BacktestResult,
        test_period_days: int = 30
    ) -> ValidationResult:
        """Validate optimization results against baseline."""
        
        self.logger.info("🔍 Starting optimization validation...")
        
        # Extract metrics
        baseline_metrics = self._extract_metrics(baseline_result)
        optimized_metrics = self._extract_metrics(optimized_result)
        
        # Calculate improvements
        improvements = self._calculate_improvement_percentages(baseline_metrics, optimized_metrics)
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(improvements)
        
        # Determine if it's an improvement
        is_improvement = overall_score > 0
        
        validation_result = ValidationResult(
            baseline_metrics=baseline_metrics,
            optimized_metrics=optimized_metrics,
            improvement_percentages=improvements,
            is_improvement=is_improvement,
            overall_score=overall_score,
            validation_date=datetime.now(),
            test_period_days=test_period_days
        )
        
        # Save validation results
        await self._save_validation_results(validation_result)
        
        self.logger.info(f"✅ Validation completed. Overall score: {overall_score:.2f}%")
        
        return validation_result
    
    async def validate_regime_optimization(
        self,
        baseline_results: Dict[str, BacktestResult],
        regime_results: RegimeOptimizationResult,
        test_period_days: int = 30
    ) -> Dict[str, ValidationResult]:
        """Validate regime-specific optimization results."""
        
        self.logger.info("🔍 Starting regime-specific optimization validation...")
        
        validation_results = {}
        
        for regime, optimization_result in regime_results.regime_results.items():
            if regime in baseline_results:
                baseline_result = baseline_results[regime]
                optimized_result = optimization_result.best_result
                
                if optimized_result:
                    validation_result = await self.validate_optimization(
                        baseline_result, optimized_result, test_period_days
                    )
                    validation_results[regime] = validation_result
                    
                    self.logger.info(f"✅ {regime} regime validation: {validation_result.overall_score:.2f}% improvement")
        
        return validation_results
    
    async def _save_validation_results(self, validation_result: ValidationResult):
        """Save validation results to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"validation_results_{timestamp}.json"
        filepath = self.results_dir / filename
        
        # Convert to dict for JSON serialization
        result_dict = asdict(validation_result)
        
        # Convert datetime to string
        result_dict['validation_date'] = result_dict['validation_date'].isoformat()
        
        with open(filepath, 'w') as f:
            json.dump(result_dict, f, indent=2, default=str)
        
        self.logger.info(f"💾 Validation results saved to {filepath}")
    
    def print_validation_summary(self, validation_result: ValidationResult):
        """Print a summary of validation results."""
        print("\n" + "="*60)
        print("📊 OPTIMIZATION VALIDATION SUMMARY")
        print("="*60)
        
        print(f"\n📅 Validation Date: {validation_result.validation_date}")
        print(f"📈 Test Period: {validation_result.test_period_days} days")
        print(f"🎯 Overall Score: {validation_result.overall_score:.2f}%")
        print(f"✅ Is Improvement: {'Yes' if validation_result.is_improvement else 'No'}")
        
        print("\n📊 METRIC COMPARISON:")
        print("-" * 40)
        
        baseline = validation_result.baseline_metrics
        optimized = validation_result.optimized_metrics
        improvements = validation_result.improvement_percentages
        
        metrics = [
            ('Sharpe Ratio', 'sharpe_ratio'),
            ('Profit Factor', 'profit_factor'),
            ('Max Drawdown', 'max_drawdown'),
            ('Win Rate', 'win_rate'),
            ('Total Return', 'total_return'),
            ('Calmar Ratio', 'calmar_ratio'),
            ('Sortino Ratio', 'sortino_ratio'),
            ('Trades/Day', 'trades_per_day')
        ]
        
        for name, key in metrics:
            baseline_val = getattr(baseline, key)
            optimized_val = getattr(optimized, key)
            improvement = improvements.get(key, 0.0)
            
            status = "📈" if improvement > 0 else "📉" if improvement < 0 else "➡️"
            
            print(f"{status} {name:15}: {baseline_val:8.4f} → {optimized_val:8.4f} ({improvement:+6.2f}%)")
        
        print("\n📈 TRADE STATISTICS:")
        print("-" * 40)
        print(f"Total Trades: {baseline.total_trades} → {optimized.total_trades} ({improvements.get('total_trades', 0):+.1f}%)")
        print(f"Avg Duration: {baseline.avg_trade_duration:.2f} → {optimized.avg_trade_duration:.2f} ({improvements.get('avg_trade_duration', 0):+.1f}%)")
        
        print("\n" + "="*60)
    
    def print_regime_validation_summary(self, validation_results: Dict[str, ValidationResult]):
        """Print a summary of regime-specific validation results."""
        print("\n" + "="*80)
        print("📊 REGIME-SPECIFIC OPTIMIZATION VALIDATION SUMMARY")
        print("="*80)
        
        total_score = 0.0
        regime_count = 0
        
        for regime, result in validation_results.items():
            print(f"\n🏛️  {regime.upper()} REGIME:")
            print("-" * 40)
            print(f"Overall Score: {result.overall_score:.2f}%")
            print(f"Is Improvement: {'Yes' if result.is_improvement else 'No'}")
            
            # Key metrics
            baseline = result.baseline_metrics
            optimized = result.optimized_metrics
            improvements = result.improvement_percentages
            
            print(f"Sharpe Ratio: {baseline.sharpe_ratio:.4f} → {optimized.sharpe_ratio:.4f} ({improvements.get('sharpe_ratio', 0):+.1f}%)")
            print(f"Profit Factor: {baseline.profit_factor:.4f} → {optimized.profit_factor:.4f} ({improvements.get('profit_factor', 0):+.1f}%)")
            print(f"Max Drawdown: {baseline.max_drawdown:.4f} → {optimized.max_drawdown:.4f} ({improvements.get('max_drawdown', 0):+.1f}%)")
            print(f"Total Trades: {baseline.total_trades} → {optimized.total_trades} ({improvements.get('total_trades', 0):+.1f}%)")
            
            total_score += result.overall_score
            regime_count += 1
        
        if regime_count > 0:
            avg_score = total_score / regime_count
            print(f"\n📊 AVERAGE SCORE ACROSS ALL REGIMES: {avg_score:.2f}%")
        
        print("\n" + "="*80)


# Example usage and testing functions
async def test_validation_framework():
    """Test the validation framework with mock data."""
    print("🧪 Testing Validation Framework...")
    
    # Mock backtest results
    baseline_result = BacktestResult(
        start_date=datetime.now() - timedelta(days=30),
        end_date=datetime.now(),
        total_trades=50,
        winning_trades=30,
        losing_trades=20,
        total_profit=1000.0,
        total_loss=500.0,
        max_drawdown=0.05,
        sharpe_ratio=1.5,
        profit_factor=2.0,
        win_rate=0.6,
        total_return=0.1,
        calmar_ratio=2.0,
        sortino_ratio=1.8,
        avg_trade_duration=2.5,
        trades_per_day=1.67
    )
    
    optimized_result = BacktestResult(
        start_date=datetime.now() - timedelta(days=30),
        end_date=datetime.now(),
        total_trades=60,
        winning_trades=40,
        losing_trades=20,
        total_profit=1500.0,
        total_loss=400.0,
        max_drawdown=0.04,
        sharpe_ratio=2.0,
        profit_factor=3.75,
        win_rate=0.67,
        total_return=0.15,
        calmar_ratio=3.75,
        sortino_ratio=2.5,
        avg_trade_duration=2.2,
        trades_per_day=2.0
    )
    
    # Test validation
    config = Config()
    validator = OptimizationValidator(config)
    
    validation_result = await validator.validate_optimization(
        baseline_result, optimized_result, test_period_days=30
    )
    
    # Print summary
    validator.print_validation_summary(validation_result)
    
    print("✅ Validation framework test completed successfully!")
    return validation_result


if __name__ == "__main__":
    asyncio.run(test_validation_framework())
