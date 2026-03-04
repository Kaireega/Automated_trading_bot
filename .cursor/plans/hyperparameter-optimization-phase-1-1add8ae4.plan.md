<!-- 1add8ae4-e7be-4d6d-bae4-7e3f9f3a784b 5409df70-758c-4a16-824f-bdb03cccb5a0 -->
# Phase 1: Enhanced Parameter Optimization System

## Overview

Implement enhanced parameter optimization with regime-specific capabilities, starting with single strategy validation before expanding to comprehensive optimization.

## Implementation Steps

### Step 1: Extend ParameterOptimizer with Regime Support

**File**: `src/trading_bot/src/backtesting/optimizer.py`

Add regime-specific optimization capabilities:

- Create `RegimeSpecificOptimizer` class that extends `ParameterOptimizer`
- Add method `optimize_by_regime()` that filters historical data by market regime
- Implement regime detection integration with `MarketRegimeDetector`
- Add scoring function that balances trade frequency + quality: `score = (sharpe_ratio * 0.4) + (profit_factor * 0.3) + (trade_frequency_score * 0.3)`

**Test**: Run unit test to verify regime filtering works correctly

### Step 2: Define Comprehensive Parameter Space

**File**: `src/trading_bot/src/backtesting/parameter_spaces.py` (new file)

Create parameter space definitions:

- Define `STRATEGY_PARAMETER_RANGES` dict for EMA Crossover strategy (ema_fast: [5,8,12,21], ema_slow: [21,26,34,50])
- Define `RISK_PARAMETER_RANGES` (risk_percentage, stop_loss_multiplier, take_profit_multiplier)
- Define `CONFIDENCE_THRESHOLDS_BY_REGIME` for 3 regimes (trending, ranging, volatile)
- Create `get_parameter_space()` function that returns complete parameter space for a strategy

**Test**: Verify parameter space generation returns expected ranges

### Step 3: Implement Enhanced Genetic Algorithm

**File**: `src/trading_bot/src/backtesting/optimizer.py`

Enhance existing `_genetic_algorithm_optimization()` method:

- Increase population size to 30 (from 20)
- Add adaptive mutation rate that decreases over generations: `mutation_rate = 0.15 * (1 - generation/max_iterations)`
- Implement elite preservation (keep top 20% of population)
- Add diversity preservation to prevent premature convergence
- Update scoring to use balanced metric (trade frequency + quality)

**Test**: Run optimization on 7 days of data for EMA Crossover strategy only, verify it completes and finds better parameters

### Step 4: Add Regime-Specific Optimization

**File**: `src/trading_bot/src/backtesting/optimizer.py`

Add new method `optimize_regime_specific()`:

- Detect market regimes in historical data using existing `MarketRegimeDetector`
- Segment data into 3 regime buckets: TRENDING (TRENDING_UP + TRENDING_DOWN), RANGING, VOLATILE (NEWS_REACTIONARY + BREAKOUT)
- Run genetic algorithm optimization separately for each regime
- Return dict mapping regime -> best_parameters
- Save regime-specific results to JSON file

**Test**: Run 14-day backtest with regime segmentation, verify different parameters for each regime

### Step 5: Create Validation Framework

**File**: `src/trading_bot/src/backtesting/validation.py` (new file)

Implement validation functions:

- `validate_optimization_result()`: Run backtest with optimized params on fresh data
- `compare_baseline_vs_optimized()`: Compare current config vs optimized config
- `calculate_improvement_metrics()`: Calculate improvement in trade count, Sharpe ratio, profit factor
- Generate validation report with before/after comparison

**Test**: Run validation on EMA Crossover strategy results, verify report generation

### Step 6: Single Strategy End-to-End Test

**File**: `run_optimization_test.py` (new file)

Create test script:

- Load 30 days of historical data for EUR_USD
- Run regime-specific optimization for EMA Crossover strategy only
- Validate results on additional 14 days out-of-sample
- Generate comparison report (baseline vs optimized)
- Print results showing trade count improvement and quality metrics

**Test**: Execute full optimization pipeline, verify trade count increases from ~3 to 15+ while maintaining positive Sharpe ratio

### Step 7: Expand to All Strategies

**File**: `src/trading_bot/src/backtesting/parameter_spaces.py`

Add parameter spaces for all strategies:

- MACD Momentum (fast, slow, signal, histogram_threshold)
- Bollinger Bounce (period, std_dev, touch_threshold)
- RSI Extremes (period, oversold, overbought)
- ADX Trend (period, threshold)
- All other registered strategies

**Test**: Run optimization for each strategy individually (7 days each), verify all complete successfully

### Step 8: Comprehensive Multi-Strategy Optimization

**File**: `run_comprehensive_optimization.py` (new file)

Create comprehensive optimization script:

- Optimize all strategies simultaneously with regime-specific parameters
- Use genetic algorithm with larger population (50)
- Run on 60 days of data across all 3 currency pairs (EUR_USD, GBP_USD, USD_JPY)
- Generate comprehensive report with regime-specific parameters for each strategy
- Save optimized configuration to `config/optimized_trading_config.yaml`

**Test**: Run full optimization (may take 2-4 hours), verify generates valid config file

### Step 9: Final Validation & Comparison

**File**: Extend `run_comprehensive_optimization.py`

Add final validation step:

- Run 30-day backtest with original config
- Run 30-day backtest with optimized config
- Compare: total trades, win rate, Sharpe ratio, profit factor, max drawdown
- Generate side-by-side comparison report
- Verify optimized config achieves: 30+ trades (vs ~3), Sharpe > 1.0, profit factor > 1.5

**Test**: Execute final validation, verify significant improvement in both trade frequency and quality

## Success Criteria

- Single strategy optimization completes in under 10 minutes
- Trade frequency increases from 3 trades/30 days to 15+ trades/30 days for single strategy
- Comprehensive optimization (all strategies) generates 30+ trades/30 days
- Sharpe ratio remains positive (> 0.5)
- Profit factor > 1.5
- Different optimal parameters identified for trending vs ranging vs volatile regimes
- All tests pass at each step

## Testing Strategy

After each step, run quick validation:

- Steps 1-2: Unit tests only
- Steps 3-5: 7-14 day backtests
- Steps 6-9: 30-60 day backtests

## Files to Create/Modify

**New Files:**

- `src/trading_bot/src/backtesting/parameter_spaces.py`
- `src/trading_bot/src/backtesting/validation.py`
- `run_optimization_test.py`
- `run_comprehensive_optimization.py`

**Modified Files:**

- `src/trading_bot/src/backtesting/optimizer.py`
- `src/trading_bot/src/backtesting/backtest_engine.py` (minor updates for regime tagging)

## Notes

- Each optimization run will be tested immediately with a quick backtest
- Focus on EMA Crossover strategy first to validate framework
- Regime-specific optimization will use 3 regimes initially (can expand to 6 later)
- Balanced scoring function prioritizes both trade frequency and quality
- All optimized configurations will be saved for comparison and rollback

### To-dos

- [ ] Extend ParameterOptimizer with regime-specific capabilities and balanced scoring function
- [ ] Create parameter_spaces.py with comprehensive parameter ranges for all strategies
- [ ] Enhance genetic algorithm with adaptive mutation, elite preservation, and diversity control
- [ ] Implement regime-specific optimization for 3 major regimes (trending, ranging, volatile)
- [ ] Create validation.py with before/after comparison and improvement metrics
- [ ] Test end-to-end optimization pipeline with EMA Crossover strategy only
- [ ] Add parameter spaces for all 8+ registered strategies
- [ ] Run comprehensive multi-strategy optimization across all pairs and regimes
- [ ] Validate optimized config vs baseline with 30-day backtest comparison