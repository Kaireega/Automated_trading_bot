# PROMPT: Parallelize the 730-Day Backtest for Performance

## Who You Are

You are a **Senior Python Performance Engineer**. You understand the GIL, `multiprocessing` vs `asyncio`, and how to split a CPU-bound simulation across cores without introducing race conditions or result inconsistencies. You keep things simple — no distributed computing frameworks, no Celery, no Dask. Just `multiprocessing` from the standard library.

---

## Context

The 730-day backtest for this Forex swing trading bot is pegging one CPU core at ~95% and taking a long time to run. The bot backtests 3 currency pairs (EUR_USD, GBP_USD, USD_JPY) over 730 days with H4, H1, and M15 candle data.

**Current architecture:** Single-threaded. One loop iterates through every hour of 730 days, processing all 3 pairs sequentially at each time step.

**The problem:** Python's GIL means `asyncio` won't help here — this is CPU-bound number crunching (indicator calculations, signal generation, position evaluation), not I/O-bound. Only `multiprocessing` (separate processes with separate GILs) will actually use multiple cores.

**Read these files for architecture context:**
- `DEBUG_JOURNAL.md` — original data flow
- `18_SESSION6_REPORT.md` — current backtest configuration

---

## Step 0: Create Your Tracker

Create `BACKTEST_PERF_TRACKER.md` in the project root:

```markdown
# Backtest Performance Tracker
> Parallelizing the 730-day backtest.
> Started: [date/time]

## Timing
| Run | Config | Wall Clock Time | CPU Usage | Notes |
|-----|--------|----------------|-----------|-------|
| Before (single-threaded) | 730d, 3 pairs, H4+H1+M15 | — | ~95% 1 core | Baseline |
| After (parallel by pair) | Same | — | — | — |

## Changes
| # | Description | File | Status |
|---|-------------|------|--------|
| 1 | Split backtest by pair into separate processes | backtest_engine.py | ⬜ |
| 2 | Merge results from all processes | backtest_engine.py | ⬜ |
| 3 | Verify merged results match single-threaded output | — | ⬜ |
```

---

## The Approach: Parallelize by Currency Pair

The cleanest split for this bot is **by pair**. Each pair's backtest is almost entirely independent:
- Each pair has its own candle data
- Each pair has its own open positions
- Each pair has its own consecutive loss counter
- The only shared state is account balance (for position sizing)

### Why by pair (not by date range):

Splitting by date range is harder because:
- Positions can span the split boundary (opened in chunk 1, closed in chunk 2)
- Consecutive loss tracking breaks across boundaries
- EMA/ADX indicators need warmup period at the start of each chunk

Splitting by pair avoids all of these. Each pair runs its full 730-day simulation independently, then results are merged.

### The shared state problem: Account Balance

The one complication: position sizing uses account balance, and if EUR_USD takes a loss, that should affect GBP_USD's next position size. In parallel, each process has its own copy of the balance.

**Practical solution:** Use the starting balance for ALL position sizing in all processes. For a small account with 1% risk per trade, the balance change over the backtest is small enough that it won't meaningfully affect position sizes. This is a standard simplification in parallel backtests.

If you want exact balance tracking later, you can add a sequential reconciliation pass, but for now the approximation is fine.

---

## Implementation

### Step 1: Find the Main Backtest Loop

```bash
grep -n "run_backtest\|run_simulation\|_run_simulation\|for.*pair\|pairs" src/trading_bot/src/backtesting/backtest_engine.py | head -20
```

Find where the backtest iterates over pairs. It likely looks something like:

```python
async def run_backtest(self, pairs, start_date, end_date, ...):
    results = {}
    for pair in pairs:
        result = await self._run_simulation(pair, candles, ...)
        results[pair] = result
    return self._merge_results(results)
```

### Step 2: Create a Worker Function

The worker function runs ONE pair's full simulation in a separate process. It must be a top-level function (not a method) because `multiprocessing` pickles it.

```python
import multiprocessing
from multiprocessing import Process, Queue

def _run_pair_backtest(pair, config, candles_by_tf, start_date, end_date, initial_balance, result_queue):
    """
    Worker function for parallel backtest. Runs one pair's full simulation.
    Must be a top-level function (not a method) for multiprocessing pickling.
    """
    import asyncio
    
    # Create a fresh engine instance for this process
    engine = BacktestEngine(config)
    engine.initial_balance = initial_balance
    
    # Run the simulation for this single pair
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            engine._run_simulation(pair, candles_by_tf, start_date, end_date)
        )
        result_queue.put((pair, result))
    except Exception as e:
        result_queue.put((pair, {'error': str(e)}))
    finally:
        loop.close()
```

**Key points:**
- Each process creates its own `BacktestEngine` instance (no shared state)
- Each process gets its own asyncio event loop
- Results are passed back via a `multiprocessing.Queue`
- If the engine uses logging, each process will write to the same log — this is fine for debugging but may interleave. Consider per-pair log files if needed.

### Step 3: Parallel Dispatch

Replace the sequential pair loop with parallel dispatch:

```python
import multiprocessing
import time

def run_backtest_parallel(self, pairs, start_date, end_date):
    """Run backtest for all pairs in parallel, one process per pair."""
    
    start_time = time.time()
    result_queue = multiprocessing.Queue()
    processes = []
    
    # Pre-fetch all candle data (this is I/O — do it before forking)
    all_candles = {}
    for pair in pairs:
        all_candles[pair] = self._fetch_candles(pair, start_date, end_date)
    
    # Launch one process per pair
    for pair in pairs:
        p = multiprocessing.Process(
            target=_run_pair_backtest,
            args=(pair, self.config, all_candles[pair], start_date, end_date, 
                  self.initial_balance, result_queue)
        )
        processes.append(p)
        p.start()
        print(f"  Started {pair} backtest (PID {p.pid})")
    
    # Collect results
    results = {}
    for _ in pairs:
        pair, result = result_queue.get()  # blocks until a result arrives
        results[pair] = result
        print(f"  Completed {pair}")
    
    # Wait for all processes to finish
    for p in processes:
        p.join()
    
    elapsed = time.time() - start_time
    print(f"\nParallel backtest completed in {elapsed:.1f}s ({len(pairs)} pairs)")
    
    # Merge results
    return self._merge_pair_results(results)
```

### Step 4: Merge Results

After all processes complete, merge the per-pair results into a single backtest report:

```python
def _merge_pair_results(self, results_by_pair):
    """Merge per-pair backtest results into a single report."""
    
    all_trades = []
    total_pnl = 0
    total_wins = 0
    total_losses = 0
    
    for pair, result in results_by_pair.items():
        if 'error' in result:
            print(f"  ⚠️ {pair} failed: {result['error']}")
            continue
        
        pair_trades = result.get('trades', [])
        all_trades.extend(pair_trades)
        
        for trade in pair_trades:
            pnl = trade.get('pnl', 0)
            total_pnl += pnl
            if pnl > 0:
                total_wins += 1
            else:
                total_losses += 1
    
    # Sort all trades by close time for proper sequencing
    all_trades.sort(key=lambda t: t.get('close_time', t.get('exit_time', '')))
    
    # Calculate aggregate metrics
    total_trades = total_wins + total_losses
    win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
    
    gross_profit = sum(t['pnl'] for t in all_trades if t['pnl'] > 0)
    gross_loss = abs(sum(t['pnl'] for t in all_trades if t['pnl'] < 0))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')
    
    # Recalculate drawdown on merged equity curve
    equity = self.initial_balance
    peak = equity
    max_dd = 0
    for trade in all_trades:
        equity += trade['pnl']
        peak = max(peak, equity)
        dd = (peak - equity) / peak * 100
        max_dd = max(max_dd, dd)
    
    return {
        'trades': all_trades,
        'total_trades': total_trades,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'total_pnl': total_pnl,
        'return_pct': (total_pnl / self.initial_balance) * 100,
        'max_drawdown': max_dd,
        'per_pair': {pair: result for pair, result in results_by_pair.items() if 'error' not in result}
    }
```

**Critical: Drawdown must be recalculated on the merged equity curve**, not summed from per-pair drawdowns. A loss on EUR_USD followed by a loss on GBP_USD in the same hour compounds in ways that per-pair DD can't capture. The merged trade list sorted by time gives you the correct sequential equity curve.

### Step 5: Handle Pickling Issues

`multiprocessing` requires all arguments to be picklable. Common issues:

```python
# These WON'T pickle:
# - Lambda functions
# - Open file handles
# - Logger objects
# - asyncio event loops
# - Some dataclass instances with complex defaults

# Fix: pass only serializable data to the worker
# - Config: convert to dict before passing, reconstruct in worker
# - Candles: list of dicts or list of namedtuples (both pickle fine)
# - Logger: create a new one in the worker
```

If you get `pickle` errors, the most likely culprit is the config object or the engine instance. Don't pass the engine — have the worker create its own:

```python
def _run_pair_backtest(pair, config_dict, candles_data, start_date, end_date, balance, result_queue):
    # Reconstruct config from dict
    config = Config.from_dict(config_dict)  # or however config is built
    
    # Create fresh engine
    engine = BacktestEngine(config)
    # ...
```

If `Config` doesn't have a `from_dict` method, the simplest fix is to pass the YAML file path and have each worker load config from the file.

---

## Step 6: Verify Results Match

**This is critical.** After implementing parallel execution, run BOTH single-threaded and parallel backtests on a short period (30 days) and compare:

```python
# Single-threaded result:
#   Trades: X, WR: Y%, PF: Z, Return: W%

# Parallel result:
#   Trades: X, WR: Y%, PF: Z, Return: W%
#   (should match exactly, except drawdown may differ slightly due to 
#    trade ordering within the same hour across pairs)
```

If trade count and total P&L match but drawdown differs slightly, that's expected — the sequential ordering of same-hour trades across pairs changes the equity curve shape. If trade count or P&L doesn't match, there's a bug in the parallelization.

---

## Expected Performance Improvement

| Pairs | Cores Used | Speedup |
|-------|-----------|---------|
| 3 pairs | 3 cores | ~2.5–3x (near-linear) |

On your Mac, if the single-threaded backtest takes ~15 minutes, parallel should take ~5–6 minutes. The speedup won't be a perfect 3x due to process startup overhead, data serialization, and result merging, but 2.5x is typical.

**If you add more pairs later**, the speedup scales — 6 pairs across 6 cores ≈ 5x faster.

---

## Alternative: If Multiprocessing Is Too Complex

If pickling issues or async complications make full multiprocessing difficult, here's a simpler approach that still helps:

### Option B: Sequential But Faster (Profile and Optimize)

```bash
# Profile the backtest to find the bottleneck
python -m cProfile -s cumtime run.py --backtest 2>&1 | head -30
```

Common bottlenecks in backtests:
1. **Indicator recalculation every iteration** — if EMA/ADX/RSI are recalculated from scratch on every candle instead of incrementally updated, this wastes massive CPU. Fix: use incremental/online calculation.
2. **Pandas operations in the loop** — if the engine converts to DataFrame on every iteration, that's slow. Fix: work with raw lists/arrays inside the loop.
3. **400 M15 candles × indicator calculations** — M15 added 4x the data points. If indicators run on all 400 M15 candles every hour, consider caching or reducing the window.

### Option C: Run Pairs as Separate Script Invocations

The absolute simplest parallelization — no code changes to the engine:

```bash
# Terminal 1:
python run.py --backtest --pair EUR_USD > results_eur.log 2>&1 &

# Terminal 2:
python run.py --backtest --pair GBP_USD > results_gbp.log 2>&1 &

# Terminal 3:
python run.py --backtest --pair USD_JPY > results_jpy.log 2>&1 &

# Wait for all to finish, then manually merge results
wait
echo "All done"
```

This requires the backtest to support a `--pair` flag. If it doesn't, adding one is trivial:

```python
# In run.py:
import argparse
parser.add_argument('--pair', type=str, help='Run backtest for a single pair')
# Then pass to BacktestEngine
```

---

## Rules

1. **Fix pickling issues before running.** If the worker function can't receive its arguments, nothing works. Test with a 7-day backtest first.
2. **Verify results match single-threaded before trusting parallel results.** Use a 30-day comparison.
3. **Don't share mutable state between processes.** Each process gets its own engine, its own positions, its own indicators. The only shared thing is the result queue (read-only from the parent).
4. **Pre-fetch candle data before forking.** Data fetching is I/O-bound and should happen once in the parent process, then passed to workers. Don't have each worker fetch its own data from OANDA — that's 3x the API calls.
5. **Account balance is approximate in parallel mode.** Each process uses the starting balance. Document this simplification. For 1% risk trades on a $500 account, the position size difference between $500 and $480 is negligible.
6. **Log to separate files per pair if console output is garbled.** Three processes writing to stdout simultaneously will interleave.
7. **Start with Option C (separate script invocations) if Option A (multiprocessing) proves difficult.** Option C gives the same speedup with zero code changes to the engine — you just need a `--pair` flag.
8. **Update `BACKTEST_PERF_TRACKER.md` with before/after timing.**

**Begin now. Read the backtest engine to understand the current loop structure, then choose the simplest approach that works (Option C first, then Option A if you want it cleaner).**
