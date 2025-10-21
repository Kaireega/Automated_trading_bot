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
        """Genetic algorithm optimization."""
        
        population_size = 20
        mutation_rate = 0.1
        crossover_rate = 0.8
        
        # Initialize population
        population = self._initialize_population(parameter_ranges, population_size)
        results = []
        
        self.logger.info(f"Genetic algorithm: {max_iterations} generations, population size {population_size}")
        
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
                    
                except Exception as e:
                    self.logger.error(f"Error evaluating individual: {e}")
                    continue
            
            if not generation_results:
                continue
            
            # Sort by fitness
            generation_results.sort(key=lambda x: x[1], reverse=True)
            
            # Selection and reproduction
            new_population = []
            
            # Elitism: keep best individuals
            elite_size = max(1, population_size // 10)
            new_population.extend([ind[0] for ind in generation_results[:elite_size]])
            
            # Generate rest of population through crossover and mutation
            while len(new_population) < population_size:
                parent1 = self._tournament_selection(generation_results)
                parent2 = self._tournament_selection(generation_results)
                
                if random.random() < crossover_rate:
                    child = self._crossover(parent1, parent2, parameter_ranges)
                else:
                    child = parent1.copy()
                
                if random.random() < mutation_rate:
                    child = self._mutate(child, parameter_ranges)
                
                new_population.append(child)
            
            population = new_population
            
            if (generation + 1) % 10 == 0:
                best_score = generation_results[0][1]
                self.logger.info(f"Generation {generation + 1}: Best score = {best_score:.4f}")
        
        # Find best result
        best_result = self._find_best_result(results, optimization_target)
        
        return OptimizationResult(
            best_parameters=best_result[0],
            best_score=best_result[1],
            best_result=best_result[2],
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
        
        if target == 'sharpe_ratio':
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
