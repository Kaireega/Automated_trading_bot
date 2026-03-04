"""
Parameter Optimizer - Optimizes trading strategy parameters using various optimization algorithms.
"""
import asyncio
import itertools
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass
import numpy as np
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed
import json

from ..utils.config import Config
from ..utils.logger import get_logger
from .backtest_engine import BacktestEngine, BacktestResult
from .performance_metrics import PerformanceMetrics
from ..core.market_regime_detector import MarketRegimeDetector
from ..core.models import MarketCondition


@dataclass
class OptimizationResult:
    """Results from parameter optimization."""
    best_parameters: Dict[str, Any]
    best_score: float
    best_result: BacktestResult
    all_results: List[Tuple[Dict[str, Any], BacktestResult]]
    optimization_method: str
    iterations: int
    execution_time: float


@dataclass
class RegimeOptimizationResult:
    """Results from regime-specific optimization."""
    regime_results: Dict[str, OptimizationResult]
    overall_best_parameters: Dict[str, Any]
    overall_best_score: float
    regime_performance: Dict[str, float]
    execution_time: float


class ParameterOptimizer:
    """Optimizes trading strategy parameters using various algorithms."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger(__name__)
        self.performance_metrics = PerformanceMetrics()
        
    async def optimize_parameters(
        self,
        historical_data: Dict[str, Dict[str, List[Any]]],  # Simplified for brevity
        start_date: datetime,
        end_date: datetime,
        parameter_ranges: Dict[str, List[Any]],
        optimization_target: str = 'sharpe_ratio',
        method: str = 'grid_search',
        max_iterations: int = 100,
        parallel: bool = True
    ) -> OptimizationResult:
        """Optimize parameters using specified method."""
        
        self.logger.info(f"Starting parameter optimization using {method}")
        start_time = datetime.now()
        
        if method == 'grid_search':
            result = await self._grid_search_optimization(
                historical_data, start_date, end_date, parameter_ranges, 
                optimization_target, parallel
            )
        elif method == 'random_search':
            result = await self._random_search_optimization(
                historical_data, start_date, end_date, parameter_ranges,
                optimization_target, max_iterations, parallel
            )
        elif method == 'genetic_algorithm':
            result = await self._genetic_algorithm_optimization(
                historical_data, start_date, end_date, parameter_ranges,
                optimization_target, max_iterations
            )
        else:
            raise ValueError(f"Unknown optimization method: {method}")
        
        execution_time = (datetime.now() - start_time).total_seconds()
        result.execution_time = execution_time
        
        self.logger.info(f"Optimization completed in {execution_time:.2f} seconds")
        self.logger.info(f"Best score: {result.best_score:.4f}")
        self.logger.info(f"Best parameters: {result.best_parameters}")
        
        return result
    
    async def _grid_search_optimization(
        self,
        historical_data: Dict[str, Dict[str, List[Any]]],
        start_date: datetime,
        end_date: datetime,
        parameter_ranges: Dict[str, List[Any]],
        optimization_target: str,
        parallel: bool
    ) -> OptimizationResult:
        """Grid search optimization - tests all parameter combinations."""
        
        # Generate all parameter combinations
        param_names = list(parameter_ranges.keys())
        param_values = list(parameter_ranges.values())
        combinations = list(itertools.product(*param_values))
        
        self.logger.info(f"Grid search: testing {len(combinations)} parameter combinations")
        
        if parallel and len(combinations) > 1:
            results = await self._run_parallel_backtests(
                historical_data, start_date, end_date, combinations, param_names
            )
        else:
            results = await self._run_sequential_backtests(
                historical_data, start_date, end_date, combinations, param_names
            )
        
        # Find best result
        best_result = self._find_best_result(results, optimization_target)
        
        return OptimizationResult(
            best_parameters=best_result[0],
            best_score=best_result[1],
            best_result=best_result[2],
            all_results=results,
            optimization_method='grid_search',
            iterations=len(combinations),
            execution_time=0.0  # Will be set by caller
        )
    
    async def _random_search_optimization(
        self,
        historical_data: Dict[str, Dict[str, List[Any]]],
        start_date: datetime,
        end_date: datetime,
        parameter_ranges: Dict[str, List[Any]],
        optimization_target: str,
        max_iterations: int,
        parallel: bool
    ) -> OptimizationResult:
        """Random search optimization - tests random parameter combinations."""
        
        param_names = list(parameter_ranges.keys())
        results = []
        
        self.logger.info(f"Random search: testing {max_iterations} random combinations")
        
        for i in range(max_iterations):
            # Generate random parameter combination
            params = {}
            for name, values in parameter_ranges.items():
                if isinstance(values[0], int):
                    params[name] = random.randint(values[0], values[-1])
                elif isinstance(values[0], float):
                    params[name] = random.uniform(values[0], values[-1])
                else:
                    params[name] = random.choice(values)
            
            # Run backtest
            try:
                backtest_engine = BacktestEngine(self.config)
                result = await backtest_engine.run_backtest(
                    historical_data, start_date, end_date, params
                )
                
                score = self._calculate_score(result, optimization_target)
                results.append((params, score, result))
                
                if (i + 1) % 10 == 0:
                    self.logger.info(f"Completed {i + 1}/{max_iterations} iterations")
                    
            except Exception as e:
                self.logger.error(f"Error in iteration {i}: {e}")
                continue
        
        # Find best result
        best_result = self._find_best_result(results, optimization_target)
        
        return OptimizationResult(
            best_parameters=best_result[0],
            best_score=best_result[1],
            best_result=best_result[2],
            all_results=results,
            optimization_method='random_search',
            iterations=max_iterations,
            execution_time=0.0
        )
    
    async def _genetic_algorithm_optimization(
        self,
        historical_data: Dict[str, Dict[str, List[Any]]],
        start_date: datetime,
        end_date: datetime,
        parameter_ranges: Dict[str, List[Any]],
        optimization_target: str,
        max_iterations: int
    ) -> OptimizationResult:
        """Enhanced genetic algorithm optimization with adaptive mutation and elite preservation."""
        
        # Enhanced parameters
        population_size = 30  # Increased from 20
        elite_size = int(population_size * 0.2)  # Top 20% preserved
        mutation_rate = 0.15  # Initial mutation rate
        min_mutation_rate = 0.05  # Minimum mutation rate
        crossover_rate = 0.8
        diversity_threshold = 0.1  # Diversity threshold for population
        
        # Initialize population
        population = self._initialize_population(parameter_ranges, population_size)
        results = []
        
        self.logger.info(f"Enhanced genetic algorithm: {max_iterations} generations, population size {population_size}")
        
        best_score = -float('inf')
        best_parameters = None
        best_result = None
        stagnation_count = 0
        last_best_score = -float('inf')
        
        for generation in range(max_iterations):
            # Evaluate population
            generation_results = []
            for individual in population:
                try:
                    backtest_engine = BacktestEngine(self.config)
                    result = await backtest_engine.run_backtest(
                        historical_data, start_date, end_date, individual
                    )
                    
                    score = self._calculate_score(result, optimization_target)
                    generation_results.append((individual, score, result))
                    results.append((individual, score, result))
                    
                    if score > best_score:
                        best_score = score
                        best_parameters = individual.copy()
                        best_result = result
                    
                except Exception as e:
                    self.logger.error(f"Error evaluating individual: {e}")
                    continue
            
            if not generation_results:
                continue
            
            # Sort by fitness
            generation_results.sort(key=lambda x: x[1], reverse=True)
            
            # Check for stagnation
            if abs(best_score - last_best_score) < 0.001:
                stagnation_count += 1
            else:
                stagnation_count = 0
            last_best_score = best_score
            
            # Adaptive mutation rate
            if stagnation_count > 5:
                mutation_rate = min(0.3, mutation_rate * 1.2)  # Increase mutation when stuck
            else:
                # Gradually decrease mutation rate
                mutation_rate = max(min_mutation_rate, mutation_rate * 0.95)
            
            # Diversity check
            population_diversity = self._calculate_population_diversity(population)
            if population_diversity < diversity_threshold:
                # Inject diversity by replacing worst individuals with random ones
                num_replacements = int(population_size * 0.3)
                for i in range(num_replacements):
                    population[-(i+1)] = self._generate_random_individual(parameter_ranges)
            
            # Selection and reproduction
            new_population = []
            
            # Enhanced elitism: keep top 20% of individuals
            new_population.extend([ind[0] for ind in generation_results[:elite_size]])
            
            # Generate rest of population through crossover and mutation
            while len(new_population) < population_size:
                parent1 = self._tournament_selection(generation_results, tournament_size=3)
                parent2 = self._tournament_selection(generation_results, tournament_size=3)
                
                if random.random() < crossover_rate:
                    child = self._crossover(parent1, parent2, parameter_ranges)
                else:
                    child = parent1.copy()
                
                if random.random() < mutation_rate:
                    child = self._mutate(child, parameter_ranges)
                
                new_population.append(child)
            
            population = new_population
            
            if (generation + 1) % 5 == 0:  # More frequent logging
                self.logger.info(f"Generation {generation + 1}: Best score = {best_score:.4f}, "
                               f"Mutation rate = {mutation_rate:.3f}, "
                               f"Diversity = {population_diversity:.3f}")
        
        # Find best result
        if best_result is None:
            best_result = self._find_best_result(results, optimization_target)
            best_parameters = best_result[0]
            best_score = best_result[1]
            best_result = best_result[2]
        
        return OptimizationResult(
            best_parameters=best_parameters,
            best_score=best_score,
            best_result=best_result,
            all_results=results,
            optimization_method='genetic_algorithm',
            iterations=max_iterations,
            execution_time=0.0
        )
    
    def _initialize_population(self, parameter_ranges: Dict[str, List[Any]], size: int) -> List[Dict[str, Any]]:
        """Initialize population for genetic algorithm."""
        population = []
        
        for _ in range(size):
            individual = {}
            for name, values in parameter_ranges.items():
                if isinstance(values[0], int):
                    individual[name] = random.randint(values[0], values[-1])
                elif isinstance(values[0], float):
                    individual[name] = random.uniform(values[0], values[-1])
                else:
                    individual[name] = random.choice(values)
            population.append(individual)
        
        return population
    
    def _tournament_selection(self, population: List[Tuple[Dict[str, Any], float, Any]], tournament_size: int = 3) -> Dict[str, Any]:
        """Tournament selection for genetic algorithm."""
        tournament = random.sample(population, min(tournament_size, len(population)))
        return max(tournament, key=lambda x: x[1])[0]
    
    def _calculate_population_diversity(self, population: List[Dict[str, Any]]) -> float:
        """Calculate population diversity based on parameter variance."""
        if len(population) < 2:
            return 0.0
        
        diversity_scores = []
        for param_name in population[0].keys():
            values = [ind[param_name] for ind in population if param_name in ind]
            if len(values) < 2:
                continue
                
            if isinstance(values[0], (int, float)):
                # Calculate coefficient of variation for numeric parameters
                mean_val = sum(values) / len(values)
                if mean_val != 0:
                    variance = sum((v - mean_val) ** 2 for v in values) / len(values)
                    std_dev = variance ** 0.5
                    diversity_scores.append(std_dev / abs(mean_val))
            else:
                # For categorical parameters, calculate unique value ratio
                unique_values = len(set(str(v) for v in values))
                diversity_scores.append(unique_values / len(values))
        
        return sum(diversity_scores) / len(diversity_scores) if diversity_scores else 0.0
    
    def _generate_random_individual(self, parameter_ranges: Dict[str, List[Any]]) -> Dict[str, Any]:
        """Generate a single random individual for genetic algorithm."""
        individual = {}
        for name, values in parameter_ranges.items():
            if isinstance(values[0], int):
                individual[name] = random.randint(values[0], values[-1])
            elif isinstance(values[0], float):
                individual[name] = random.uniform(values[0], values[-1])
            else:
                individual[name] = random.choice(values)
        return individual
    
    def _crossover(self, parent1: Dict[str, Any], parent2: Dict[str, Any], parameter_ranges: Dict[str, List[Any]]) -> Dict[str, Any]:
        """Crossover operation for genetic algorithm."""
        child = {}
        
        for param in parent1.keys():
            if random.random() < 0.5:
                child[param] = parent1[param]
            else:
                child[param] = parent2[param]
        
        return child
    
    def _mutate(self, individual: Dict[str, Any], parameter_ranges: Dict[str, List[Any]]) -> Dict[str, Any]:
        """Mutation operation for genetic algorithm."""
        mutated = individual.copy()
        
        # Randomly mutate one parameter
        param_name = random.choice(list(parameter_ranges.keys()))
        values = parameter_ranges[param_name]
        
        if isinstance(values[0], int):
            mutated[param_name] = random.randint(values[0], values[-1])
        elif isinstance(values[0], float):
            mutated[param_name] = random.uniform(values[0], values[-1])
        else:
            mutated[param_name] = random.choice(values)
        
        return mutated
    
    async def _run_parallel_backtests(
        self,
        historical_data: Dict[str, Dict[str, List[Any]]],
        start_date: datetime,
        end_date: datetime,
        combinations: List[Tuple],
        param_names: List[str]
    ) -> List[Tuple[Dict[str, Any], float, BacktestResult]]:
        """Run backtests in parallel."""
        
        # Note: This is a simplified version. In practice, you'd need to handle
        # the complexity of sharing historical data across processes
        
        results = []
        chunk_size = max(1, len(combinations) // 4)  # Use 4 processes
        
        for i in range(0, len(combinations), chunk_size):
            chunk = combinations[i:i + chunk_size]
            chunk_results = await self._run_sequential_backtests(
                historical_data, start_date, end_date, chunk, param_names
            )
            results.extend(chunk_results)
        
        return results
    
    async def _run_sequential_backtests(
        self,
        historical_data: Dict[str, Dict[str, List[Any]]],
        start_date: datetime,
        end_date: datetime,
        combinations: List[Tuple],
        param_names: List[str]
    ) -> List[Tuple[Dict[str, Any], float, BacktestResult]]:
        """Run backtests sequentially."""
        
        results = []
        
        for i, combination in enumerate(combinations):
            # Convert combination to parameter dict
            params = dict(zip(param_names, combination))
            
            try:
                backtest_engine = BacktestEngine(self.config)
                result = await backtest_engine.run_backtest(
                    historical_data, start_date, end_date, params
                )
                
                score = self._calculate_score(result, 'sharpe_ratio')
                results.append((params, score, result))
                
                if (i + 1) % 10 == 0:
                    self.logger.info(f"Completed {i + 1}/{len(combinations)} backtests")
                    
            except Exception as e:
                self.logger.error(f"Error in backtest {i}: {e}")
                continue
        
        return results
    
    def _calculate_score(self, result: BacktestResult, target: str) -> float:
        """Calculate optimization score based on target metric."""
        
        if target == 'balanced':
            # Use balanced scoring for regime-specific optimization
            return self._calculate_balanced_score(result, target)
        elif target == 'sharpe_ratio':
            return result.sharpe_ratio
        elif target == 'total_return':
            return result.total_return
        elif target == 'profit_factor':
            return result.profit_factor
        elif target == 'win_rate':
            return result.win_rate
        elif target == 'calmar_ratio':
            if result.max_drawdown > 0:
                return result.total_return / result.max_drawdown
            return 0.0
        elif target == 'custom':
            # Custom scoring function
            return (result.sharpe_ratio * 0.4 + 
                   result.total_return * 0.3 + 
                   result.profit_factor * 0.2 + 
                   result.win_rate * 0.1)
        else:
            return result.sharpe_ratio  # Default
    
    def _calculate_balanced_score(self, result: BacktestResult, target: str = 'balanced') -> float:
        """Calculate balanced score considering both trade frequency and quality."""
        
        if target == 'balanced':
            # Balanced scoring: 40% Sharpe + 30% Profit Factor + 30% Trade Frequency
            sharpe_score = max(0, result.sharpe_ratio) / 3.0  # Normalize to 0-1 (3.0 is excellent)
            profit_factor_score = min(1.0, result.profit_factor / 2.0)  # Normalize to 0-1 (2.0 is good)
            
            # Trade frequency score (normalize based on expected trades per day)
            expected_trades_per_day = 1.0  # Target: 1 trade per day
            actual_trades_per_day = result.total_trades / max(1, (result.end_date - result.start_date).days)
            trade_frequency_score = min(1.0, actual_trades_per_day / expected_trades_per_day)
            
            balanced_score = (sharpe_score * 0.4) + (profit_factor_score * 0.3) + (trade_frequency_score * 0.3)
            return balanced_score
        else:
            # Fall back to original scoring
            return self._calculate_score(result, target)
    
    def _find_best_result(
        self, 
        results: List[Tuple[Dict[str, Any], float, BacktestResult]], 
        optimization_target: str
    ) -> Tuple[Dict[str, Any], float, BacktestResult]:
        """Find the best result from optimization."""
        
        if not results:
            raise ValueError("No results to evaluate")
        
        # Sort by score (higher is better)
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[0]
    
    def generate_optimization_report(self, result: OptimizationResult) -> Dict[str, Any]:
        """Generate comprehensive optimization report."""
        
        # Calculate statistics across all results
        scores = [r[1] for r in result.all_results]
        parameters = [r[0] for r in result.all_results]
        
        # Parameter statistics
        param_stats = {}
        for param_name in result.best_parameters.keys():
            param_values = [p[param_name] for p in parameters if param_name in p]
            if param_values:
                param_stats[param_name] = {
                    'min': min(param_values),
                    'max': max(param_values),
                    'mean': np.mean(param_values),
                    'std': np.std(param_values),
                    'best': result.best_parameters[param_name]
                }
        
        # Score statistics
        score_stats = {
            'min': min(scores),
            'max': max(scores),
            'mean': np.mean(scores),
            'std': np.std(scores),
            'median': np.median(scores)
        }
        
        # Top 10 results
        top_results = sorted(result.all_results, key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'optimization_method': result.optimization_method,
            'iterations': result.iterations,
            'execution_time': result.execution_time,
            'best_parameters': result.best_parameters,
            'best_score': result.best_score,
            'score_statistics': score_stats,
            'parameter_statistics': param_stats,
            'top_10_results': top_results,
            'all_results': result.all_results
        }


class RegimeSpecificOptimizer(ParameterOptimizer):
    """Enhanced optimizer with regime-specific capabilities."""
    
    def __init__(self, config: Config):
        super().__init__(config)
        self.regime_detector = MarketRegimeDetector(config)
        self.regime_mapping = {
            'TRENDING': [MarketCondition.BREAKOUT],  # Use BREAKOUT as trending indicator
            'RANGING': [MarketCondition.RANGING],
            'VOLATILE': [MarketCondition.NEWS_REACTIONARY, MarketCondition.REVERSAL]
        }
    
    def _calculate_balanced_score(self, result: BacktestResult, target: str = 'balanced') -> float:
        """Calculate balanced score considering both trade frequency and quality."""
        
        if target == 'balanced':
            # Balanced scoring: 40% Sharpe + 30% Profit Factor + 30% Trade Frequency
            sharpe_score = max(0, result.sharpe_ratio) / 3.0  # Normalize to 0-1 (3.0 is excellent)
            profit_factor_score = min(1.0, result.profit_factor / 2.0)  # Normalize to 0-1 (2.0 is good)
            
            # Trade frequency score (normalize based on expected trades per day)
            expected_trades_per_day = 1.0  # Target: 1 trade per day
            actual_trades_per_day = result.total_trades / max(1, (result.end_date - result.start_date).days)
            trade_frequency_score = min(1.0, actual_trades_per_day / expected_trades_per_day)
            
            balanced_score = (sharpe_score * 0.4) + (profit_factor_score * 0.3) + (trade_frequency_score * 0.3)
            return balanced_score
        else:
            # Fall back to original scoring
            return self._calculate_score(result, target)
    
    async def optimize_by_regime(
        self,
        historical_data: Dict[str, Dict[str, List[Any]]],
        start_date: datetime,
        end_date: datetime,
        parameter_ranges: Dict[str, List[Any]],
        optimization_target: str = 'balanced',
        method: str = 'genetic_algorithm',
        max_iterations: int = 50
    ) -> RegimeOptimizationResult:
        """Optimize parameters separately for each market regime."""
        
        self.logger.info("Starting regime-specific optimization")
        start_time = datetime.now()
        
        # Detect regimes in historical data
        regime_data = await self._segment_data_by_regime(historical_data, start_date, end_date)
        
        regime_results = {}
        regime_performance = {}
        
        # Optimize for each regime
        for regime_name, regime_conditions in self.regime_mapping.items():
            if regime_name not in regime_data or not regime_data[regime_name]:
                self.logger.warning(f"No data found for regime: {regime_name}")
                continue
                
            self.logger.info(f"Optimizing for regime: {regime_name}")
            
            # Run optimization for this regime
            result = await self.optimize_parameters(
                regime_data[regime_name],
                start_date,
                end_date,
                parameter_ranges,
                optimization_target,
                method,
                max_iterations,
                parallel=False  # Disable parallel for regime-specific optimization
            )
            
            regime_results[regime_name] = result
            regime_performance[regime_name] = result.best_score
            
            self.logger.info(f"Regime {regime_name} - Best score: {result.best_score:.4f}")
        
        # Find overall best parameters
        overall_best_score = -float('inf')
        overall_best_parameters = {}
        
        for regime_name, result in regime_results.items():
            if result.best_score > overall_best_score:
                overall_best_score = result.best_score
                overall_best_parameters = result.best_parameters
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Save regime-specific results
        await self._save_regime_results(regime_results, execution_time)
        
        return RegimeOptimizationResult(
            regime_results=regime_results,
            overall_best_parameters=overall_best_parameters,
            overall_best_score=overall_best_score,
            regime_performance=regime_performance,
            execution_time=execution_time
        )
    
    async def _segment_data_by_regime(
        self, 
        historical_data: Dict[str, Dict[str, List[Any]]], 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, Dict[str, Dict[str, List[Any]]]]:
        """Segment historical data by market regime."""
        
        regime_data = {regime: {} for regime in self.regime_mapping.keys()}
        
        # For each currency pair, detect regimes and segment data
        for pair, timeframe_data in historical_data.items():
            for timeframe, candles in timeframe_data.items():
                if not candles:
                    continue
                
                # Detect regime for each candle
                regime_candles = {regime: [] for regime in self.regime_mapping.keys()}
                
                for i, candle in enumerate(candles):
                    # Use a window of candles for regime detection
                    window_start = max(0, i - 20)  # 20 candle window
                    window_candles = candles[window_start:i+1]
                    
                    if len(window_candles) < 10:  # Need minimum candles for regime detection
                        continue
                    
                    # Detect regime for this window
                    regime_analysis = await self.regime_detector.detect_regime(
                        pair, window_candles, None, None
                    )
                    
                    detected_regime = regime_analysis.get('regime', 'RANGING')
                    
                    # Map to our regime categories
                    if detected_regime == 'BREAKOUT':
                        regime_candles['TRENDING'].append(candle)
                    elif detected_regime in ['NEWS_REACTIONARY', 'REVERSAL']:
                        regime_candles['VOLATILE'].append(candle)
                    else:  # RANGING, UNKNOWN, etc.
                        regime_candles['RANGING'].append(candle)
                
                # Add regime-specific candles to regime_data
                for regime, candles_list in regime_candles.items():
                    if candles_list:
                        if pair not in regime_data[regime]:
                            regime_data[regime][pair] = {}
                        regime_data[regime][pair][timeframe] = candles_list
        
        # Log regime data statistics
        for regime, pair_data in regime_data.items():
            total_candles = sum(len(candles) for pair_data in pair_data.values() for candles in pair_data.values())
            self.logger.info(f"Regime {regime}: {total_candles} candles across {len(pair_data)} pairs")
        
        return regime_data
    
    async def _save_regime_results(self, regime_results: Dict[str, OptimizationResult], execution_time: float):
        """Save regime-specific optimization results to JSON file."""
        
        results_data = {
            'timestamp': datetime.now().isoformat(),
            'execution_time': execution_time,
            'regime_results': {}
        }
        
        for regime_name, result in regime_results.items():
            results_data['regime_results'][regime_name] = {
                'best_parameters': result.best_parameters,
                'best_score': result.best_score,
                'iterations': result.iterations,
                'optimization_method': result.optimization_method,
                'total_trades': result.best_result.total_trades,
                'sharpe_ratio': result.best_result.sharpe_ratio,
                'profit_factor': result.best_result.profit_factor,
                'win_rate': result.best_result.win_rate
            }
        
        # Save to file
        results_file = f"logs/regime_optimization_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(results_data, f, indent=2, default=str)
        
        self.logger.info(f"Regime optimization results saved to: {results_file}")
