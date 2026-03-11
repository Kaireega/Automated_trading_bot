#!/usr/bin/env python3
"""
Unified Trading Bot Runner

Single entry point for all bot operations:
- Backtesting (standard, quiet, comparison)
- Mock testing
- Live trading
- Validation

Usage:
    python run.py backtest [options]
    python run.py backtest --days 30 --pairs EUR_USD GBP_USD
    python run.py backtest --quiet
    python run.py backtest --compare
    
    python run.py mock [options]
    python run.py mock --quick
    python run.py mock --stress-only
    
    python run.py validate
    python run.py live
"""

import asyncio
import sys
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Load .env file at startup (must happen before any config is read)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed; rely on environment variables being set manually

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Import comprehensive debugging utilities
from trading_bot.src.utils.debug_utils import (
    debug_tracker, debug_line, debug_variable, debug_context, 
    debug_performance, debug_data_flow, debug_api_call, 
    debug_trade_decision, debug_strategy_execution, debug_risk_calculation,
    debug_indicator_calculation, debug_backtest_step, debug_entry_point,
    debug_exit_point, debug_conditional, debug_loop_iteration,
    get_debug_summary, export_debug_report
)

from trading_bot.src.backtesting.backtest_engine import BacktestEngine
from trading_bot.src.utils.config import Config


# ============================================================================
# BACKTEST COMMANDS
# ============================================================================

@debug_performance
async def run_backtest(args):
    """Run standard backtest."""
    debug_entry_point("run_backtest")
    
    with debug_context("Standard backtest execution") as context:
        pairs = args.pairs if args.pairs else ['EUR_USD', 'GBP_USD']
        debug_variable("backtest_pairs", pairs, context)
        debug_variable("backtest_args", vars(args), context)
        
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=args.days)
        debug_variable("start_date", start_date, context)
        debug_variable("end_date", end_date, context)
        debug_variable("backtest_days", args.days, context)
        
        print("\n" + "="*80)
        print("🚀 BACKTEST ENGINE")
        print("="*80)
        print(f"Period:     {start_date.date()} to {end_date.date()} ({args.days} days)")
        print(f"Balance:    ${args.balance:,.2f}")
        print(f"Pairs:      {', '.join(pairs)}")
        print(f"Risk/Trade: {args.risk}%")
        print("="*80)
        print()
        
        debug_data_flow("config_loading", "loading", "backtest_config")
        config = Config()
        debug_variable("config_loaded", True, context)
        
        debug_data_flow("engine_creation", "creating", "backtest_engine")
        engine = BacktestEngine(config, use_historical_feed=True)
        debug_variable("engine_created", True, context)
        debug_variable("use_historical_feed", True, context)
        
        debug_data_flow("backtest_execution", "starting", "backtest_run")
        result = await engine.run_backtest(
            start_date=start_date,
            end_date=end_date,
            pairs=pairs,
            initial_balance=args.balance
        )
        debug_variable("backtest_result", result, context)
    
        # Print results
        debug_conditional(result is not None, "Backtest completed successfully", "Backtest failed", context)
        if result:
            debug_variable("result_start_date", result.start_date, context)
            debug_variable("result_end_date", result.end_date, context)
            debug_variable("result_starting_balance", result.initial_balance, context)
            debug_variable("result_ending_balance", result.final_balance, context)
            debug_variable("result_total_return_pct", result.total_return_pct, context)
            debug_variable("result_total_trades", result.total_trades, context)
            debug_variable("result_win_rate", result.win_rate, context)
            debug_variable("result_profit_factor", result.profit_factor, context)
            debug_variable("result_sharpe_ratio", result.sharpe_ratio, context)
            debug_variable("result_max_drawdown_pct", result.max_drawdown_pct, context)
            
            print("\n" + "="*80)
            print("📊 BACKTEST RESULTS")
            print("="*80)
            print(f"\nPeriod:           {result.start_date.date()} to {result.end_date.date()}")
            print(f"Initial Balance:  ${result.initial_balance:,.2f}")
            print(f"Final Balance:    ${result.final_balance:,.2f}")
            print(f"Total Return:     {result.total_return_pct:.2f}%")
            print(f"Total Trades:     {result.total_trades}")
            print(f"Win Rate:         {result.win_rate:.2f}%")
            print(f"Profit Factor:    {result.profit_factor:.2f}")
            print(f"Sharpe Ratio:     {result.sharpe_ratio:.2f}")
            print(f"Max Drawdown:     {result.max_drawdown_pct:.2f}%")
            print("="*80)
            
            debug_conditional(args.save, "Saving results to file", "Not saving results", context)
            if args.save:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"backtest_results_{timestamp}.txt"
                debug_variable("save_filename", filename, context)
                with open(filename, 'w') as f:
                    f.write(str(result))
                debug_variable("results_saved", True, context)
                print(f"\n✅ Results saved to: {filename}")
        
        debug_exit_point("run_backtest", result)
        return result


async def run_quiet_backtest(args):
    """Run quiet backtest (minimal output)."""
    pairs = args.pairs if args.pairs else ['EUR_USD', 'GBP_USD']
    
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=args.days)
    
    print(f"Running backtest: {args.days} days, {len(pairs)} pairs...")
    
    config = Config()
    engine = BacktestEngine(config, use_historical_feed=True)
    
    result = await engine.run_backtest(
        start_date=start_date,
        end_date=end_date,
        pairs=pairs,
        initial_balance=args.balance
    )
    
    if result:
        print(f"\n✅ Complete | Return: {result.total_return_pct:.2f}% | Win Rate: {result.win_rate:.2f}% | Sharpe: {result.sharpe_ratio:.2f}")
    
    return result


async def run_comparison_backtest(args):
    """Run comparison backtest (multi-strategy vs single-strategy)."""
    print("\n" + "="*80)
    print("📊 COMPARISON BACKTEST: Multi-Strategy vs Single-Strategy")
    print("="*80)
    print()
    
    pairs = args.pairs if args.pairs else ['EUR_USD', 'GBP_USD']
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=args.days)
    
    # Run with multi-strategy enabled
    print("1️⃣ Running with MULTI-STRATEGY enabled...")
    config_multi = Config()
    config_multi._config['strategy_portfolio']['enabled'] = True
    engine_multi = BacktestEngine(config_multi, use_historical_feed=True)
    
    result_multi = await engine_multi.run_backtest(
        start_date=start_date,
        end_date=end_date,
        pairs=pairs,
        initial_balance=args.balance
    )
    
    # Run with single-strategy (legacy)
    print("\n2️⃣ Running with SINGLE-STRATEGY (legacy)...")
    config_single = Config()
    config_single._config['strategy_portfolio']['enabled'] = False
    engine_single = BacktestEngine(config_single, use_historical_feed=True)
    
    result_single = await engine_single.run_backtest(
        start_date=start_date,
        end_date=end_date,
        pairs=pairs,
        initial_balance=args.balance
    )
    
    # Compare results
    print("\n" + "="*80)
    print("📊 COMPARISON RESULTS")
    print("="*80)
    print(f"\n{'Metric':<25} {'Single-Strategy':<20} {'Multi-Strategy':<20} {'Improvement':<15}")
    print("-" * 80)
    
    if result_single and result_multi:
        metrics = [
            ('Total Return', result_single.total_return_pct, result_multi.total_return_pct, '%'),
            ('Win Rate', result_single.win_rate, result_multi.win_rate, '%'),
            ('Profit Factor', result_single.profit_factor, result_multi.profit_factor, 'x'),
            ('Sharpe Ratio', result_single.sharpe_ratio, result_multi.sharpe_ratio, ''),
            ('Max Drawdown', result_single.max_drawdown_pct, result_multi.max_drawdown_pct, '%'),
            ('Total Trades', result_single.total_trades, result_multi.total_trades, ''),
        ]
        
        for name, single_val, multi_val, unit in metrics:
            if single_val != 0:
                improvement = ((multi_val - single_val) / abs(single_val)) * 100
            else:
                improvement = 0
            
            print(f"{name:<25} {single_val:>15.2f}{unit:<5} {multi_val:>15.2f}{unit:<5} {improvement:>+10.1f}%")
    
    print("="*80)
    
    return result_multi, result_single


# ============================================================================
# MOCK TEST COMMANDS
# ============================================================================

async def run_mock_tests(args):
    """Run mock tests."""
    print("\n" + "="*80)
    print("🧪 MOCK TESTING SUITE")
    print("="*80)
    
    test_mode = 'quick' if args.quick else 'full'
    if args.stress_only:
        test_mode = 'stress'
    elif args.harmony_only:
        test_mode = 'harmony'
    
    print(f"Mode: {test_mode.upper()}")
    print("="*80)
    print()
    
    # Import mock test modules (adjust imports as needed)
    print(f"Running {test_mode} mock tests...")
    print("✅ Mock tests would run here (implementation depends on your mock test setup)")
    
    return True


# ============================================================================
# VALIDATION COMMAND
# ============================================================================

async def run_validation(args):
    """Run validation checks."""
    print("\n" + "="*80)
    print("🔍 VALIDATION CHECKS")
    print("="*80)
    
    # Import with proper path
    from trading_bot.src.strategies import register_all
    from trading_bot.src.strategies.strategy_registry import StrategyRegistry
    
    # Check strategies
    strategies = StrategyRegistry.list_strategies()
    print(f"\n✅ Strategies registered: {len(strategies)}")
    for s in sorted(strategies):
        print(f"   - {s}")
    
    # Check config
    config = Config()
    # Access strategy portfolio from config object
    strategy_portfolio = getattr(config, 'strategy_portfolio', {})
    enabled = strategy_portfolio.enabled if hasattr(strategy_portfolio, "enabled") else False
    config_strategies = strategy_portfolio.strategies if hasattr(strategy_portfolio, "strategies") else []
    
    print(f"\n✅ Configuration loaded")
    print(f"   - Multi-Strategy: {'ENABLED' if enabled else 'DISABLED'}")
    print(f"   - Strategies in config: {len(config_strategies)}")
    
    total_allocation = sum(s.get('allocation', 0) for s in config_strategies)
    print(f"   - Total allocation: {total_allocation}%")
    
    if total_allocation == 100:
        print(f"   ✅ Allocations sum to 100%")
    else:
        print(f"   ⚠️  Allocations sum to {total_allocation}% (should be 100%)")
    
    print("\n" + "="*80)
    print("✅ VALIDATION COMPLETE")
    print("="*80)
    
    return True


# ============================================================================
# LIVE TRADING COMMAND
# ============================================================================

async def run_live(args):
    """Run live trading bot."""
    print("\n" + "="*80)
    print("🚀 STARTING LIVE TRADING BOT")
    print("="*80)
    print()
    
    # Import and run main bot
    from trading_bot.main import TradingBot
    
    bot = TradingBot()
    await bot.start()


# ============================================================================
# MAIN COMMAND ROUTER
# ============================================================================

@debug_performance
def main():
    """Main entry point with command routing."""
    debug_entry_point("main")
    
    with debug_context("Main function execution") as context:
        debug_variable("sys_argv", sys.argv, context)
        
        parser = argparse.ArgumentParser(
            description='Unified Trading Bot Runner',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s backtest --days 30
  %(prog)s backtest --days 90 --pairs EUR_USD GBP_USD USD_JPY
  %(prog)s backtest --quiet --days 7
  %(prog)s backtest --compare
  %(prog)s mock --quick
  %(prog)s validate
  %(prog)s live
            """
        )
        debug_variable("parser_created", True, context)
        
        subparsers = parser.add_subparsers(dest='command', help='Command to run')
        debug_variable("subparsers_created", True, context)
        
        # Backtest command
        backtest_parser = subparsers.add_parser('backtest', help='Run backtest')
        backtest_parser.add_argument('--days', type=int, default=30, help='Days to backtest (default: 30)')
        backtest_parser.add_argument('--pairs', nargs='+', help='Pairs to test (default: EUR_USD GBP_USD)')
        backtest_parser.add_argument('--risk', type=float, default=2.0, help='Risk per trade %% (default: 2.0)')
        backtest_parser.add_argument('--balance', type=float, default=10000.0, help='Initial balance (default: 10000)')
        backtest_parser.add_argument('--quiet', action='store_true', help='Minimal output')
        backtest_parser.add_argument('--compare', action='store_true', help='Compare multi vs single strategy')
        backtest_parser.add_argument('--save', action='store_true', help='Save results to file')
        debug_variable("backtest_parser_configured", True, context)
        
        # Mock test command
        mock_parser = subparsers.add_parser('mock', help='Run mock tests')
        mock_parser.add_argument('--quick', action='store_true', help='Quick tests (reduced load)')
        mock_parser.add_argument('--stress-only', action='store_true', help='Only stress tests')
        mock_parser.add_argument('--harmony-only', action='store_true', help='Only harmony tests')
        mock_parser.add_argument('--verbose', action='store_true', help='Verbose logging')
        debug_variable("mock_parser_configured", True, context)
        
        # Validate command
        validate_parser = subparsers.add_parser('validate', help='Run validation checks')
        debug_variable("validate_parser_configured", True, context)
        
        # Live command
        live_parser = subparsers.add_parser('live', help='Run live trading')
        debug_variable("live_parser_configured", True, context)
        
        debug_data_flow("argument_parsing", "parsing", "command_line_args")
        args = parser.parse_args()
        debug_variable("parsed_args", vars(args) if args else None, context)
        
        debug_conditional(args.command is not None, f"Command received: {args.command}", "No command provided", context)
        if not args.command:
            debug_variable("no_command_provided", True, context)
            parser.print_help()
            sys.exit(1)
        
        # Route to appropriate handler
        debug_data_flow("command_routing", "routing", f"command_{args.command}")
        debug_conditional(args.command == 'backtest', "Routing to backtest handler", "Not backtest command", context)
        if args.command == 'backtest':
            debug_conditional(args.compare, "Running comparison backtest", "Running standard backtest", context)
            if args.compare:
                debug_data_flow("comparison_backtest", "starting", "comparison_backtest")
                asyncio.run(run_comparison_backtest(args))
            elif args.quiet:
                debug_data_flow("quiet_backtest", "starting", "quiet_backtest")
                asyncio.run(run_quiet_backtest(args))
            else:
                debug_data_flow("standard_backtest", "starting", "standard_backtest")
                asyncio.run(run_backtest(args))
        elif args.command == 'mock':
            debug_data_flow("mock_tests", "starting", "mock_tests")
            asyncio.run(run_mock_tests(args))
        elif args.command == 'validate':
            debug_data_flow("validation", "starting", "validation")
            asyncio.run(run_validation(args))
        elif args.command == 'live':
            debug_data_flow("live_trading", "starting", "live_trading")
            asyncio.run(run_live(args))
        
        debug_exit_point("main")


if __name__ == "__main__":
    main()






