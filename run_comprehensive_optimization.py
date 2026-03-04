#!/usr/bin/env python3
"""
Comprehensive Multi-Strategy Optimization Script

This script runs comprehensive optimization across all strategies, pairs, and regimes
as specified in Step 8 of the hyperparameter optimization plan.
"""

import asyncio
import sys
import json
import yaml
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import traceback

# Add the project root to the path to import API modules
root_dir = Path(__file__).parent
sys.path.append(str(root_dir))

from src.trading_bot.src.backtesting.optimizer import RegimeSpecificOptimizer
from src.trading_bot.src.backtesting.validation import OptimizationValidator
from src.trading_bot.src.backtesting.parameter_spaces import PARAMETER_SPACES, get_optimization_priorities
from src.trading_bot.src.utils.config import Config
from src.trading_bot.src.core.models import CandleData, TimeFrame
from src.trading_bot.src.strategies.strategy_registry import StrategyRegistry

class ComprehensiveOptimizer:
    """Comprehensive optimization orchestrator."""
    
    def __init__(self, config: Config):
        self.config = config
        self.optimizer = RegimeSpecificOptimizer(config)
        self.validator = OptimizationValidator(config)
        self.results_dir = Path("results/comprehensive_optimization")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Load historical data
        self.historical_data = self._load_historical_data()
        
        # Get strategy priorities
        self.strategy_priorities = get_optimization_priorities()
        
        # Results storage
        self.optimization_results = {}
        self.regime_results = {}
        
    def _load_historical_data(self) -> Dict[str, Dict[str, List[Any]]]:
        """Load historical data for all currency pairs."""
        print("📊 Loading historical data...")
        
        # For now, create mock data for testing
        # In production, this would load real historical data
        historical_data = {}
        
        pairs = ['EUR_USD', 'GBP_USD', 'USD_JPY']
        timeframes = ['M5', 'M15', 'H1']
        
        for pair in pairs:
            historical_data[pair] = {}
            for timeframe in timeframes:
                # Generate 60 days of mock data
                candles = self._generate_mock_data(pair, timeframe, days=60)
                historical_data[pair][timeframe] = candles
        
        print(f"✅ Loaded data for {len(pairs)} pairs across {len(timeframes)} timeframes")
        return historical_data
    
    def _generate_mock_data(self, pair: str, timeframe: str, days: int) -> List[CandleData]:
        """Generate mock historical data for testing."""
        candles = []
        current_price = 1.1000 if 'EUR' in pair else 1.2500 if 'GBP' in pair else 110.0
        
        # Calculate minutes per candle based on timeframe
        minutes_per_candle = {'M5': 5, 'M15': 15, 'H1': 60}[timeframe]
        total_candles = days * 24 * 60 // minutes_per_candle
        
        for i in range(total_candles):
            # Simulate realistic price movement
            price_change = (i % 100 - 50) * 0.0001 * (0.5 if 'JPY' in pair else 1.0)
            current_price += price_change
            
            candle = CandleData(
                timestamp=datetime.now() - timedelta(minutes=minutes_per_candle*i),
                open=current_price - 0.0001,
                high=current_price + 0.0002,
                low=current_price - 0.0002,
                close=current_price,
                volume=1000,
                pair=pair,
                timeframe=getattr(TimeFrame, timeframe)
            )
            candles.append(candle)
        
        return candles
    
    async def optimize_strategy(self, strategy_name: str, pair: str = 'EUR_USD') -> Dict[str, Any]:
        """Optimize a single strategy across all regimes."""
        print(f"\n🎯 Optimizing {strategy_name} for {pair}...")
        
        try:
            # Get parameter space for the strategy
            parameter_ranges = PARAMETER_SPACES["strategies"][strategy_name]
            
            # Add risk management parameters
            risk_params = PARAMETER_SPACES["global_settings"]["risk_management"]
            parameter_ranges.update(risk_params)
            
            # Run regime-specific optimization
            start_date = datetime.now() - timedelta(days=30)
            end_date = datetime.now()
            
            result = await self.optimizer.optimize_by_regime(
                historical_data={pair: self.historical_data[pair]},
                start_date=start_date,
                end_date=end_date,
                parameter_ranges=parameter_ranges,
                optimization_target='balanced',
                method='genetic_algorithm',
                max_iterations=50
            )
            
            print(f"✅ {strategy_name} optimization completed")
            print(f"   - Best overall score: {result.overall_best_score:.4f}")
            print(f"   - Regimes optimized: {list(result.regime_results.keys())}")
            
            return {
                'strategy_name': strategy_name,
                'pair': pair,
                'result': result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Error optimizing {strategy_name}: {e}")
            traceback.print_exc()
            return {
                'strategy_name': strategy_name,
                'pair': pair,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def run_comprehensive_optimization(self) -> Dict[str, Any]:
        """Run comprehensive optimization across all strategies and pairs."""
        print("🚀 Starting Comprehensive Multi-Strategy Optimization")
        print("=" * 60)
        
        # Get all strategy names sorted by priority
        strategy_names = sorted(
            self.strategy_priorities.keys(),
            key=lambda x: self.strategy_priorities[x],
            reverse=True
        )
        
        print(f"📋 Optimizing {len(strategy_names)} strategies:")
        for i, strategy in enumerate(strategy_names, 1):
            priority = self.strategy_priorities[strategy]
            print(f"   {i:2d}. {strategy} (priority: {priority})")
        
        # Run optimization for each strategy
        optimization_results = {}
        
        for strategy_name in strategy_names:
            print(f"\n{'='*60}")
            print(f"🎯 OPTIMIZING: {strategy_name}")
            print(f"{'='*60}")
            
            # Optimize for EUR_USD first (primary pair)
            result = await self.optimize_strategy(strategy_name, 'EUR_USD')
            optimization_results[strategy_name] = result
            
            # Save intermediate results
            await self._save_intermediate_results(optimization_results)
        
        # Generate comprehensive report
        report = await self._generate_comprehensive_report(optimization_results)
        
        # Save final results
        await self._save_final_results(optimization_results, report)
        
        return {
            'optimization_results': optimization_results,
            'report': report,
            'timestamp': datetime.now().isoformat()
        }
    
    async def _save_intermediate_results(self, results: Dict[str, Any]):
        """Save intermediate results to prevent data loss."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"intermediate_results_{timestamp}.json"
        filepath = self.results_dir / filename
        
        # Convert results to JSON-serializable format
        serializable_results = {}
        for strategy, result in results.items():
            if 'result' in result and hasattr(result['result'], '__dict__'):
                # Convert complex objects to dict
                serializable_results[strategy] = {
                    'strategy_name': result['strategy_name'],
                    'pair': result['pair'],
                    'timestamp': result['timestamp'],
                    'overall_best_score': getattr(result['result'], 'overall_best_score', None),
                    'regime_results_count': len(getattr(result['result'], 'regime_results', {})),
                    'execution_time': getattr(result['result'], 'execution_time', None)
                }
            else:
                serializable_results[strategy] = result
        
        with open(filepath, 'w') as f:
            json.dump(serializable_results, f, indent=2, default=str)
        
        print(f"💾 Intermediate results saved to {filepath}")
    
    async def _generate_comprehensive_report(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive optimization report."""
        print("\n📊 Generating Comprehensive Report...")
        
        report = {
            'summary': {
                'total_strategies': len(results),
                'successful_optimizations': len([r for r in results.values() if 'error' not in r]),
                'failed_optimizations': len([r for r in results.values() if 'error' in r]),
                'optimization_date': datetime.now().isoformat()
            },
            'strategy_results': {},
            'regime_analysis': {},
            'recommendations': []
        }
        
        # Analyze each strategy
        for strategy_name, result in results.items():
            if 'error' in result:
                report['strategy_results'][strategy_name] = {
                    'status': 'failed',
                    'error': result['error']
                }
                continue
            
            opt_result = result['result']
            report['strategy_results'][strategy_name] = {
                'status': 'success',
                'overall_score': opt_result.overall_best_score,
                'best_parameters': opt_result.overall_best_parameters,
                'regime_count': len(opt_result.regime_results),
                'execution_time': opt_result.execution_time
            }
        
        # Analyze regime performance
        regime_performance = {}
        for strategy_name, result in results.items():
            if 'error' in result:
                continue
            
            opt_result = result['result']
            for regime, regime_result in opt_result.regime_results.items():
                if regime not in regime_performance:
                    regime_performance[regime] = []
                
                regime_performance[regime].append({
                    'strategy': strategy_name,
                    'score': regime_result.best_score,
                    'parameters': regime_result.best_parameters
                })
        
        report['regime_analysis'] = regime_performance
        
        # Generate recommendations
        successful_strategies = [
            (name, data) for name, data in report['strategy_results'].items()
            if data['status'] == 'success'
        ]
        
        if successful_strategies:
            # Sort by score
            successful_strategies.sort(key=lambda x: x[1]['overall_score'], reverse=True)
            
            report['recommendations'] = [
                f"Top performing strategy: {successful_strategies[0][0]} (score: {successful_strategies[0][1]['overall_score']:.4f})",
                f"Consider implementing regime-specific parameters for better performance",
                f"Focus on top 3 strategies: {', '.join([s[0] for s in successful_strategies[:3]])}"
            ]
        
        print("✅ Comprehensive report generated")
        return report
    
    async def _save_final_results(self, results: Dict[str, Any], report: Dict[str, Any]):
        """Save final optimization results."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save detailed results
        results_file = self.results_dir / f"comprehensive_optimization_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        # Save report
        report_file = self.results_dir / f"optimization_report_{timestamp}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Generate optimized config
        await self._generate_optimized_config(results, report)
        
        print(f"💾 Final results saved:")
        print(f"   - Results: {results_file}")
        print(f"   - Report: {report_file}")
    
    async def _generate_optimized_config(self, results: Dict[str, Any], report: Dict[str, Any]):
        """Generate optimized trading configuration."""
        print("\n⚙️ Generating Optimized Configuration...")
        
        # Load current config
        config_path = Path("src/trading_bot/config/trading_config.yaml")
        if config_path.exists():
            with open(config_path, 'r') as f:
                current_config = yaml.safe_load(f)
        else:
            current_config = {}
        
        # Create optimized config
        optimized_config = current_config.copy()
        
        # Update strategy configurations with optimized parameters
        if 'strategies' not in optimized_config:
            optimized_config['strategies'] = []
        
        # Clear existing strategies
        optimized_config['strategies'] = []
        
        # Add optimized strategies
        for strategy_name, result in results.items():
            if 'error' in result:
                continue
            
            opt_result = result['result']
            strategy_config = {
                'name': strategy_name,
                'type': 'trend_momentum',  # Default type
                'enabled': True,
                'allocation': 10,  # Equal allocation
                'parameters': opt_result.overall_best_parameters
            }
            optimized_config['strategies'].append(strategy_config)
        
        # Update risk management
        if 'risk_management' not in optimized_config:
            optimized_config['risk_management'] = {}
        
        # Use parameters from best performing strategy
        best_strategy = None
        best_score = -1
        for strategy_name, result in results.items():
            if 'error' not in result and result['result'].overall_best_score > best_score:
                best_strategy = result['result']
                best_score = result['result'].overall_best_score
        
        if best_strategy:
            risk_params = best_strategy.overall_best_parameters
            optimized_config['risk_management'].update({
                'risk_percentage': risk_params.get('risk_percentage', 1.0),
                'stop_loss_multiplier': risk_params.get('stop_loss_multiplier', 2.0),
                'take_profit_multiplier': risk_params.get('take_profit_multiplier', 2.0),
                'max_trades_per_day': risk_params.get('max_trades_per_day', 3),
                'max_daily_loss': risk_params.get('max_daily_loss', 0.03)
            })
        
        # Save optimized config
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        config_file = self.results_dir / f"optimized_trading_config_{timestamp}.yaml"
        
        with open(config_file, 'w') as f:
            yaml.dump(optimized_config, f, default_flow_style=False, indent=2)
        
        print(f"✅ Optimized configuration saved to {config_file}")
    
    def print_summary(self, results: Dict[str, Any], report: Dict[str, Any]):
        """Print optimization summary."""
        print("\n" + "="*80)
        print("📊 COMPREHENSIVE OPTIMIZATION SUMMARY")
        print("="*80)
        
        summary = report['summary']
        print(f"\n📈 Overall Results:")
        print(f"   - Total strategies: {summary['total_strategies']}")
        print(f"   - Successful: {summary['successful_optimizations']}")
        print(f"   - Failed: {summary['failed_optimizations']}")
        print(f"   - Success rate: {summary['successful_optimizations']/summary['total_strategies']*100:.1f}%")
        
        print(f"\n🏆 Top Performing Strategies:")
        successful_strategies = [
            (name, data) for name, data in report['strategy_results'].items()
            if data['status'] == 'success'
        ]
        successful_strategies.sort(key=lambda x: x[1]['overall_score'], reverse=True)
        
        for i, (strategy, data) in enumerate(successful_strategies[:5], 1):
            print(f"   {i}. {strategy}: {data['overall_score']:.4f}")
        
        print(f"\n🏛️ Regime Analysis:")
        for regime, strategies in report['regime_analysis'].items():
            if strategies:
                avg_score = sum(s['score'] for s in strategies) / len(strategies)
                print(f"   - {regime}: {len(strategies)} strategies, avg score: {avg_score:.4f}")
        
        print(f"\n💡 Recommendations:")
        for rec in report['recommendations']:
            print(f"   - {rec}")
        
        print("\n" + "="*80)


async def main():
    """Main optimization function."""
    print("🚀 Comprehensive Multi-Strategy Optimization")
    print("=" * 60)
    
    try:
        # Load configuration
        config = Config()
        print("✅ Configuration loaded")
        
        # Create optimizer
        optimizer = ComprehensiveOptimizer(config)
        print("✅ Comprehensive optimizer initialized")
        
        # Run optimization
        results = await optimizer.run_comprehensive_optimization()
        
        # Print summary
        optimizer.print_summary(results['optimization_results'], results['report'])
        
        print("\n🎉 Comprehensive optimization completed successfully!")
        
    except Exception as e:
        print(f"❌ Error in comprehensive optimization: {e}")
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
