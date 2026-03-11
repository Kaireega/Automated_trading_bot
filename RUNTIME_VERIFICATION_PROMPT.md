# PROMPT: Runtime Verification — Post-Fix Trading Bot Validation

## Who You Are

You are a **Senior QA Engineer** validating a Forex trading bot after 25 fixes were applied. Syntax checks passed, but **syntax checks prove nothing about runtime behavior**. Your job is to prove every fix actually works by running the code, tracing real execution paths, and catching any issues that `py_compile` cannot detect.

---

## Context

Read these files first — they are your source of truth:
1. `DEBUG_JOURNAL.md` — the original audit (40 issues found)
2. `FIX_TRACKER.md` — the 25 fixes that were applied

All 25 fixes passed `py_compile`. That only means no syntax errors. It does NOT mean:
- Imports resolve at runtime
- Attributes exist on the objects that access them
- Logic produces correct results
- Data flows through the fixed path (not a fallback)
- Config values are actually read (not silently defaulting)

**Your job is to prove each fix works at runtime, or find the ones that don't.**

---

## Step 0: Create Your Verification Log

Create `VERIFICATION_LOG.md` in the project root:

```markdown
# Runtime Verification Log
> Post-fix validation of all 25 applied fixes.
> Started: [date/time]
> Last updated: [date/time]

## Environment
- Python version: [output of python3 --version]
- Working directory: [pwd]
- Config loaded from: [path]

## Test Results
| Test # | What Was Tested | Fix(es) Validated | Result | Details |
|--------|-----------------|-------------------|--------|---------|
| — | — | — | — | — |

## Failures Found
| # | Fix # | Expected | Actual | Root Cause | Resolution |
|---|-------|----------|--------|------------|------------|
| — | — | — | — | — | — |

## Backtest Comparison
| Metric | Before Fixes | After Fixes |
|--------|-------------|-------------|
| Win rate | ~4% | — |
| Total trades | — | — |
| Errors/Exceptions | — | — |

## Final Assessment
[To be filled after all tests]
```

---

## Step 1: Environment & Import Chain Validation

These tests catch missing imports, circular dependencies, wrong paths, and missing attributes at the module level.

### Test 1.1 — Full import chain (live trading path)
```python
import sys, os
# Adjust sys.path as the bot does at startup — check run.py for how it sets paths
# Then:
try:
    from src.trading_bot.main import TradingBot
    print("✅ TradingBot imported successfully")
except Exception as e:
    print(f"❌ TradingBot import failed: {type(e).__name__}: {e}")
```

### Test 1.2 — Full import chain (backtest path)
```python
try:
    from src.trading_bot.src.backtesting.backtest_engine import BacktestEngine
    print("✅ BacktestEngine imported successfully")
except Exception as e:
    print(f"❌ BacktestEngine import failed: {type(e).__name__}: {e}")
```

### Test 1.3 — Strategy registry completeness
```python
# Import register_all and verify all strategies are registered
try:
    from src.trading_bot.src.strategies.register_all import *
    from src.trading_bot.src.strategies.strategy_registry import StrategyRegistry
    
    registry = StrategyRegistry()
    # Or however the registry is accessed — check the actual code
    
    expected_strategies = [
        "EMA_Crossover", "ADX_Trend", "MACD_Momentum", "Fast_Ichimoku",
        "London_Open_Break", "NY_Open_Momentum",
        "BB_Bounce", "RSI_Extremes", "Fast_Stochastic",
        "ATR_Breakout", "Support_Resistance", "Donchian_Break",
        "Price_Action_Scalp", "Order_Flow_Momentum", "Spread_Squeeze"
    ]
    
    for name in expected_strategies:
        result = registry.get(name)  # or however lookup works
        status = "✅" if result is not None else "❌ NOT REGISTERED"
        print(f"  {status} — {name}")
        
except Exception as e:
    print(f"❌ Strategy registry test failed: {type(e).__name__}: {e}")
```
This validates **Fixes 5 and 19** (FastIchimoku, DonchianBreak, SpreadSqueeze, OrderFlowMomentum imports).

### Test 1.4 — Config loading with new fields
```python
try:
    from src.trading_bot.src.utils.config import load_config  # or however config loads
    config = load_config("src/trading_bot/src/config/trading_config.yaml")
    
    # Fix 2: max_risk_threshold exists
    assert hasattr(config.risk_management, 'max_risk_threshold'), "❌ max_risk_threshold missing from config"
    print(f"✅ max_risk_threshold = {config.risk_management.max_risk_threshold}")
    
    # Fix 12: confluence and consensus thresholds
    print(f"✅ min_confluence_score = {config.technical_analysis.min_confluence_score}")
    print(f"✅ consensus_threshold = {config.multi_timeframe.consensus_threshold}")
    
    # Fix 25: minimum_timeframes
    print(f"✅ minimum_timeframes = {config.multi_timeframe.minimum_timeframes}")
    
except Exception as e:
    print(f"❌ Config test failed: {type(e).__name__}: {e}")
```

### Test 1.5 — Model instantiation (Fix 3)
```python
try:
    from src.trading_bot.src.core.models import TradeRecommendation
    
    # Test with metadata (the field that was missing)
    rec = TradeRecommendation(
        pair="EUR_USD",
        direction="BUY",
        confidence=0.8,
        entry_price=1.1000,
        stop_loss=1.0950,
        take_profit=1.1100,
        metadata={"strategy": "test", "timeframe": "M5"}
    )
    assert hasattr(rec, 'metadata'), "❌ metadata field missing"
    assert rec.metadata == {"strategy": "test", "timeframe": "M5"}, "❌ metadata not stored correctly"
    print(f"✅ TradeRecommendation with metadata: {rec.metadata}")
    
    # Test without metadata (should default to empty dict)
    rec2 = TradeRecommendation(
        pair="EUR_USD",
        direction="BUY",
        confidence=0.8,
        entry_price=1.1000,
        stop_loss=1.0950,
        take_profit=1.1100
    )
    assert rec2.metadata == {}, "❌ metadata default is not empty dict"
    print("✅ TradeRecommendation without metadata defaults to {}")
    
except Exception as e:
    print(f"❌ Model test failed: {type(e).__name__}: {e}")
```

---

## Step 2: Unit-Level Fix Validation

Each test below targets a specific fix. **Read the actual source code** before writing each test — the examples below show the intent, but class names, method signatures, and import paths may differ from what's in the codebase.

### Test 2.1 — Session strategies use candle.timestamp (Fix 4)
```python
# Create a mock CandleData with timestamp (not time)
# Pass it to LondonOpenBreakStrategy.generate_signal() and NYOpenMomentumStrategy.generate_signal()
# If they access candle.time they crash with AttributeError
# If they access candle.timestamp they proceed normally

from src.trading_bot.src.core.models import CandleData  # or wherever it lives
from datetime import datetime

# Build a minimal candle — check CandleData fields
mock_candle = CandleData(
    timestamp=datetime(2026, 3, 11, 8, 0, 0),  # 8 AM UTC = London session
    open=1.1000,
    high=1.1050,
    low=1.0950,
    close=1.1020,
    volume=1000
)

# Test London Open
try:
    from src.trading_bot.src.strategies.session_based.london_open_break import LondonOpenBreakStrategy
    strategy = LondonOpenBreakStrategy()  # may need config
    # Call with enough candles — check what generate_signal expects
    # The point is: it should NOT raise AttributeError on candle.time
    print("✅ LondonOpenBreak imported and instantiated without AttributeError")
except AttributeError as e:
    if "time" in str(e):
        print(f"❌ Fix 4 FAILED — still using candle.time: {e}")
    else:
        print(f"❌ Other AttributeError: {e}")
except Exception as e:
    print(f"⚠️ LondonOpenBreak test inconclusive: {type(e).__name__}: {e}")

# Repeat for NY Open
```

### Test 2.2 — Position manager initializes scaling_levels/partial_exits (Fix 6)
```python
# Instantiate PositionManager (may need config + oanda_api mock)
# Call _record_trade() with a mock trade
# Verify the resulting position dict has 'scaling_levels' and 'partial_exits' keys

# After _record_trade(), check:
# position = self.active_positions[trade_id]
# assert 'scaling_levels' in position, "❌ scaling_levels missing"
# assert 'partial_exits' in position, "❌ partial_exits missing"
```

### Test 2.3 — Risk manager uses max_risk_threshold (Fix 2)
```python
# Instantiate AdvancedRiskManager with config
# Call assess_trade_risk() with a valid trade recommendation
# If it still crashes with AttributeError on max_risk_threshold, Fix 2 failed
# If it returns a result (approved=True or False), it's working

try:
    from src.trading_bot.src.core.advanced_risk_manager import AdvancedRiskManager
    # ... instantiate with config
    # ... call assess_trade_risk()
    print("✅ assess_trade_risk() did not crash on max_risk_threshold")
except AttributeError as e:
    if "max_risk_threshold" in str(e):
        print(f"❌ Fix 2 FAILED — max_risk_threshold still missing: {e}")
    else:
        print(f"❌ Other AttributeError: {e}")
```

### Test 2.4 — Market condition detection is not always RANGING (Fix 13)
```python
# Get or create candle data for a strongly trending pair
# Call the market condition detection
# Verify it does NOT always return RANGING

# Create candles with a clear uptrend (each close higher than previous)
import pandas as pd
trending_candles = []
for i in range(50):
    trending_candles.append(CandleData(
        timestamp=datetime(2026, 3, 11, 0, i, 0),
        open=1.1000 + i * 0.001,
        high=1.1010 + i * 0.001,
        low=1.0990 + i * 0.001,
        close=1.1005 + i * 0.001,
        volume=1000
    ))

# Pass to data_layer._create_market_context_from_candles() or equivalent
# Check that condition != RANGING for obvious trend data
# If it still returns RANGING, Fix 13 didn't work
```

### Test 2.5 — Hardcoded values replaced with config (Fix 12)
```python
# This requires reading the actual source after fixes
# In technical_analysis_layer.py, find where min_confluence_score is set
# Verify it reads from self.config, not hardcoded 0.2

# In strategy_manager.py, find where consensus_threshold is set  
# Verify it reads from self.config, not hardcoded 0.30

# Approach: grep the source files
import subprocess
result = subprocess.run(
    ["grep", "-n", "min_confluence_score", "src/trading_bot/src/ai/technical_analysis_layer.py"],
    capture_output=True, text=True
)
print("min_confluence_score references:")
print(result.stdout)
# Look for: self.config... NOT: = 0.2

result2 = subprocess.run(
    ["grep", "-n", "consensus_threshold", "src/trading_bot/src/strategies/strategy_manager.py"],
    capture_output=True, text=True
)
print("consensus_threshold references:")
print(result2.stdout)
# Look for: self.config... NOT: = 0.30
```

### Test 2.6 — _can_execute_trade() is called (Fix 10)
```python
# Read position_manager.py execute_trade() method
# Verify _can_execute_trade() is called before any trade execution
# Grep approach:
import subprocess
result = subprocess.run(
    ["grep", "-n", "_can_execute_trade\|execute_trade", "src/trading_bot/src/core/position_manager.py"],
    capture_output=True, text=True
)
print(result.stdout)
# Verify _can_execute_trade appears INSIDE execute_trade, before the trade logic
```

### Test 2.7 — Daily loss comparison units match (Fix 11)
```python
# Read _can_execute_trade() in position_manager.py
# Verify the comparison converts percentage to dollars:
# max_daily_loss_dollars = account_balance * (max_daily_loss / 100)
# daily_pnl <= -max_daily_loss_dollars

# Grep:
import subprocess
result = subprocess.run(
    ["grep", "-n", "-A5", "daily_pnl.*max_daily_loss\|max_daily_loss.*daily_pnl\|max_daily_loss_dollars",
     "src/trading_bot/src/core/position_manager.py"],
    capture_output=True, text=True
)
print(result.stdout)
```

### Test 2.8 — Notification failure prevents trade (Fix 7)
```python
# Read main.py — find the except block after _send_pre_trade_notification
# Verify there is a `continue` statement so execution doesn't fall through to execute_trade

import subprocess
result = subprocess.run(
    ["grep", "-n", "-A3", "pre_trade_notification\|Pre-trade notification failed",
     "src/trading_bot/main.py"],
    capture_output=True, text=True
)
print(result.stdout)
# Must see "continue" in the except block
```

### Test 2.9 — Backtest detect_regime() call signature (Fix 8)
```python
# Read backtest_engine.py — find the detect_regime call
# Verify it passes 4 arguments, not 2

import subprocess
result = subprocess.run(
    ["grep", "-n", "-B2", "-A2", "detect_regime",
     "src/trading_bot/src/backtesting/backtest_engine.py"],
    capture_output=True, text=True
)
print(result.stdout)
# Must see 4 arguments: pair, candles, market_context, technical_indicators
```

### Test 2.10 — MarketCondition.BREAKOUT not hardcoded (Fix 9)
```python
import subprocess
result = subprocess.run(
    ["grep", "-n", "MarketCondition.BREAKOUT",
     "src/trading_bot/src/ai/technical_analysis_layer.py"],
    capture_output=True, text=True
)
print("BREAKOUT references in technical_analysis_layer.py:")
print(result.stdout if result.stdout else "(none — good, hardcoded reference removed)")
# Should NOT appear in recommendation creation. May appear in enum definition — that's fine.
```

---

## Step 3: Integration Test — Run The Backtest

This is the most important test. The debug journal documented a ~4% win rate caused by the compound failure chain. If the fixes work, the backtest should produce dramatically different results.

```bash
# Run the backtest with the same config
# Check run.py for how to invoke backtest mode
python run.py --backtest  # or however backtest mode is triggered
```

**Capture and compare:**

| Metric | Before (from debug journal) | After |
|--------|---------------------------|-------|
| Win rate | ~4% | ? |
| Total trades executed | very few (most blocked) | ? |
| TypeErrors during run | frequent (detect_regime, consensus) | should be 0 |
| AttributeErrors during run | frequent (candle.time, max_risk_threshold) | should be 0 |
| Strategies that produced signals | only BB_Bounce + RSI_Extremes | should be many more |
| Market conditions detected | always RANGING | should vary |

**If the win rate is still ~4%, something in the fix chain didn't take effect.** Trace the data flow again:
1. Is market condition detection returning varied results? (Fix 13)
2. Are more than just mean_reversion strategies being allowed? (Fix 13 + 5 + 19)
3. Is consensus recommendation being created without TypeError? (Fix 3)
4. Is risk manager approving valid trades? (Fix 2)
5. Are config values being used, not hardcoded? (Fix 12)

---

## Step 4: Live Path Smoke Test (No Real Trades)

If the project has a demo/paper mode, or if you can instantiate `TradingBot` without actually connecting to OANDA:

```python
# Attempt to instantiate TradingBot with config
# This tests the full init chain: config loading, strategy registration, 
# risk manager setup, position manager setup, notification layer

try:
    config = load_config("src/trading_bot/src/config/trading_config.yaml")
    bot = TradingBot(config)  # or however it's constructed
    print("✅ TradingBot instantiated successfully")
    
    # Check that key components are initialized
    assert bot.position_manager is not None
    assert bot.risk_manager is not None  # or advanced_risk_manager
    assert bot.strategy_manager is not None
    print("✅ All core components initialized")
    
except Exception as e:
    print(f"❌ TradingBot instantiation failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
```

---

## Step 5: New Issues From Fixes (Validate Resolutions)

The FIX_TRACKER noted 2 new issues found during fixes. Verify they were actually resolved:

### New Issue 1 — RSI fallback values
```python
# In technical_analysis_layer.py, check RSI oversold/overbought defaults
import subprocess
result = subprocess.run(
    ["grep", "-n", "rsi_oversold\|rsi_overbought",
     "src/trading_bot/src/ai/technical_analysis_layer.py"],
    capture_output=True, text=True
)
print(result.stdout)
# oversold fallback should be 30 (not 55)
# overbought fallback should be 70 (not 65)
```

### New Issue 2 — MarketCondition enum members
```python
# Check that MarketCondition enum has the values used in data_layer.py
import subprocess
result = subprocess.run(
    ["grep", "-n", "TRENDING\|CONSOLIDATION\|RANGING\|BREAKOUT\|VOLATILE\|UNKNOWN",
     "src/trading_bot/src/core/models.py"],  # or wherever the enum is defined
    capture_output=True, text=True
)
print("MarketCondition enum members:")
print(result.stdout)

# Then check what data_layer references:
result2 = subprocess.run(
    ["grep", "-n", "MarketCondition\.",
     "src/trading_bot/src/data/data_layer.py"],
    capture_output=True, text=True
)
print("data_layer.py MarketCondition references:")
print(result2.stdout)
# Every MarketCondition.X in data_layer must exist in the enum
```

---

## Rules

1. **Run actual code, don't just read it.** The whole point is runtime validation.
2. **Adapt the test code to the actual codebase.** The examples above show intent — class names, import paths, method signatures, and constructor arguments may be different. Read the source first, then write the test.
3. **If a test fails, diagnose why.** Is the fix incomplete? Was it applied to the wrong line? Did it introduce a new bug?
4. **Log everything in `VERIFICATION_LOG.md`.** Every test, every result, every failure.
5. **If you find a fix that didn't work, fix it.** Then re-run verification.
6. **The backtest comparison (Step 3) is the most important test.** If the win rate hasn't changed, the core fix chain is broken somewhere. Find where.
7. **Don't mock what you can run.** If you can instantiate real objects with the real config, do that instead of mocking.
8. **Check stderr and logs.** Many failures in this bot are silently caught by `except Exception`. Look for logged errors, not just crashes.

---

## When You Are Done

`VERIFICATION_LOG.md` should contain:
- Every test run with pass/fail
- Backtest before/after comparison
- Any fixes that didn't work at runtime (with resolution)
- Any new issues discovered
- Final assessment: is the bot ready for paper trading?

**Begin now. Create `VERIFICATION_LOG.md`, then start with Step 1.**
