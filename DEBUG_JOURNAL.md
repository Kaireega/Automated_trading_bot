# Debug Journal
> Auto-generated during full project audit.
> Last updated: 2026-03-11

---

## Project Overview
- **Project type:** Automated Forex trading bot (live + backtesting)
- **Language/Runtime:** Python 3.13
- **Entry point:** `run.py` → dispatches to `src/trading_bot/main.py` for live, `src/trading_bot/src/backtesting/backtest_engine.py` for backtest
- **Key dependencies:** oandapyV20, pandas, numpy, pyyaml, python-telegram-bot, aiohttp, openpyxl
- **Active config:** `src/trading_bot/src/config/trading_config.yaml`
- **Dead config (0 bytes):** `src/trading_bot/config/trading_config.yaml`

---

## File Inventory

| # | File Path | Status | Issues Found |
|---|-----------|--------|--------------|
| 1 | `run.py` | ✅ Reviewed | 🔴 `bot.run()` call but method doesn't exist |
| 2 | `src/trading_bot/main.py` | ✅ Reviewed | 🔴 Manual approval bypass on exception; 🟡 2-timeframe gate contradicts config |
| 3 | `src/trading_bot/src/utils/config.py` | ✅ Reviewed | 🟡 `max_risk_threshold` missing from dataclass |
| 4 | `src/trading_bot/src/utils/logger.py` | ✅ Reviewed | ✅ OK |
| 5 | `src/trading_bot/src/utils/debug_utils.py` | ✅ Reviewed | 🔵 Debug decorators with blank lines before def (Python 3.12+ only) |
| 6 | `src/trading_bot/src/core/models.py` | ✅ Reviewed | 🔴 `TradeRecommendation` has no `metadata` field |
| 7 | `src/trading_bot/src/core/position_manager.py` | ✅ Reviewed | 🔴 `_can_execute_trade()` never called; 🔴 `scaling_levels`/`partial_exits` KeyError; 🔴 daily loss type mismatch; 🟡 stop-loss adjustment never sent to OANDA; 🟡 partial exit closes full position |
| 8 | `src/trading_bot/src/core/advanced_risk_manager.py` | ✅ Reviewed | 🔴 `config.risk_management.max_risk_threshold` doesn't exist → AttributeError every call |
| 9 | `src/trading_bot/src/core/portfolio_risk_manager.py` | ✅ Reviewed | 🟡 Duplicate risk manager not connected to main flow |
| 10 | `src/trading_bot/src/core/fx_position_sizing.py` | ✅ Reviewed | ✅ OK |
| 11 | `src/trading_bot/src/core/market_regime_detector.py` | ✅ Reviewed | 🟡 `detect_regime()` signature mismatch used in backtest |
| 12 | `src/trading_bot/src/core/smart_execution_engine.py` | ✅ Reviewed | 🟡 Exists but not connected to main flow |
| 13 | `src/trading_bot/src/core/exceptions.py` | ✅ Reviewed | ✅ OK |
| 14 | `src/trading_bot/src/core/fundamental_analyzer.py` | ✅ Reviewed | 🟡 Returns stub data; external APIs not connected |
| 15 | `src/trading_bot/src/ai/technical_analysis_layer.py` | ✅ Reviewed | 🔴 `market_condition=MarketCondition.BREAKOUT` hardcoded; 🟡 `min_confluence_score=0.2` hardcoded ignoring config |
| 16 | `src/trading_bot/src/ai/technical_analyzer.py` | ✅ Reviewed | ✅ OK (indicator math appears correct) |
| 17 | `src/trading_bot/src/ai/multi_timeframe_analyzer.py` | ✅ Reviewed | 🟡 `market_context=None` passed into `_analyze_technical_signals()` which doesn't null-check it |
| 18 | `src/trading_bot/src/ai/order_flow_analyzer.py` | ✅ Reviewed | 🔵 Unused module |
| 19 | `src/trading_bot/src/strategies/strategy_manager.py` | ✅ Reviewed | 🔴 `consensus_threshold=0.30` hardcoded; 🟡 `config.get('strategy_portfolio',{})` uses raw YAML not structured obj |
| 20 | `src/trading_bot/src/strategies/strategy_base.py` | ✅ Reviewed | ✅ OK |
| 21 | `src/trading_bot/src/strategies/strategy_registry.py` | ✅ Reviewed | ✅ OK |
| 22 | `src/trading_bot/src/strategies/register_all.py` | ✅ Reviewed | 🔴 `FastIchimokuStrategy` not imported → never registered |
| 23 | `src/trading_bot/src/strategies/trend_momentum/ema_crossover.py` | ✅ Reviewed | ✅ OK |
| 24 | `src/trading_bot/src/strategies/trend_momentum/adx_trend.py` | ✅ Reviewed | ✅ OK |
| 25 | `src/trading_bot/src/strategies/trend_momentum/macd_momentum.py` | ✅ Reviewed | ✅ OK |
| 26 | `src/trading_bot/src/strategies/trend_momentum/fast_ichimoku.py` | ✅ Reviewed | 🔴 Not imported by register_all.py or __init__.py |
| 27 | `src/trading_bot/src/strategies/session_based/london_open_break.py` | ✅ Reviewed | 🔴 `candle.time` → should be `candle.timestamp` → AttributeError every call |
| 28 | `src/trading_bot/src/strategies/session_based/ny_open_momentum.py` | ✅ Reviewed | 🔴 `candle.time` → should be `candle.timestamp` → AttributeError every call |
| 29 | `src/trading_bot/src/strategies/mean_reversion/bollinger_bounce.py` | ✅ Reviewed | ✅ OK |
| 30 | `src/trading_bot/src/strategies/mean_reversion/rsi_extremes.py` | ✅ Reviewed | ✅ OK |
| 31 | `src/trading_bot/src/strategies/mean_reversion/stochastic_reversal.py` | ✅ Reviewed | 🟡 Registered as "Fast_Stochastic" but not in YAML strategy config |
| 32 | `src/trading_bot/src/strategies/breakout/atr_breakout.py` | ✅ Reviewed | ✅ OK |
| 33 | `src/trading_bot/src/strategies/breakout/support_resistance.py` | ✅ Reviewed | ✅ OK |
| 34 | `src/trading_bot/src/strategies/breakout/donchian_break.py` | ✅ Reviewed | 🟡 Not exported from `breakout/__init__.py` — only loads if register_all imports it directly (it doesn't) |
| 35 | `src/trading_bot/src/strategies/scalping/price_action_scalp.py` | ✅ Reviewed | ✅ OK |
| 36 | `src/trading_bot/src/strategies/scalping/order_flow_momentum.py` | ✅ Reviewed | 🟡 Not imported in register_all.py |
| 37 | `src/trading_bot/src/strategies/scalping/spread_squeeze.py` | ✅ Reviewed | 🟡 Not imported in register_all.py |
| 38 | `src/trading_bot/src/decision/risk_manager.py` | ✅ Reviewed | 🟡 Duplicate risk manager, not connected to main flow |
| 39 | `src/trading_bot/src/decision/technical_decision_layer.py` | ✅ Reviewed | 🟡 Confidence gating may double-filter signals already gated upstream |
| 40 | `src/trading_bot/src/decision/performance_tracker.py` | ✅ Reviewed | ✅ OK |
| 41 | `src/trading_bot/src/decision/enhanced_excel_trade_recorder.py` | ✅ Reviewed | ✅ OK |
| 42 | `src/trading_bot/src/data/data_layer.py` | ✅ Reviewed | 🟡 Market context always returns `RANGING` condition — affects regime gate |
| 43 | `src/trading_bot/src/data/scraping_data_integration.py` | ✅ Reviewed | 🔵 Not connected to main flow |
| 44 | `src/trading_bot/src/backtesting/backtest_engine.py` | ✅ Reviewed | 🔴 `detect_regime()` called with wrong number of args |
| 45 | `src/trading_bot/src/backtesting/simulation_broker.py` | ✅ Reviewed | ✅ OK |
| 46 | `src/trading_bot/src/backtesting/feeds_oanda.py` | ✅ Reviewed | ✅ OK |
| 47 | `src/trading_bot/src/backtesting/performance_metrics.py` | ✅ Reviewed | ✅ OK |
| 48 | `src/trading_bot/src/notifications/notification_layer.py` | ✅ Reviewed | 🟡 `.env` not auto-loaded; Telegram token may be missing at runtime |
| 49 | `src/trading_bot/src/simulation/engine.py` | ✅ Reviewed | ✅ OK |
| 50 | `.env` | ✅ Reviewed | 🔴 Real credentials present — verify not committed to git |
| 51 | `src/trading_bot/config/trading_config.yaml` | ✅ Reviewed | 🔴 Empty file (0 bytes) — dead config, creates confusion |

---

## Issues Found

| # | Severity | File | Location | Description | Status |
|---|----------|------|----------|-------------|--------|
| 1 | 🔴 Critical | `run.py` | line 318 | `await bot.run()` — `TradingBot` has no `run()` method, only `start()`. Live mode crashes immediately on startup. | ⬜ Open |
| 2 | 🔴 Critical | `core/advanced_risk_manager.py` | line 132-143 | References `config.risk_management.max_risk_threshold` which does not exist in `RiskManagementConfig` dataclass or either YAML. Every call to `assess_trade_risk()` raises `AttributeError` → returns `approved=False`. No trade ever passes risk assessment. | ⬜ Open |
| 3 | 🔴 Critical | `core/models.py` | `TradeRecommendation` | `TradeRecommendation` dataclass has no `metadata` field. `strategy_manager._create_consensus_recommendation()` passes `metadata={...}` → `TypeError` on every consensus recommendation. Multi-strategy framework silently fails. | ⬜ Open |
| 4 | 🔴 Critical | `core/position_manager.py` | line 84-174 | `_can_execute_trade()` (lines 377-394) is never called inside `execute_trade()`. Max open trades and daily loss limits are completely bypassed. | ⬜ Open |
| 5 | 🔴 Critical | `core/position_manager.py` | line 380 | `self.daily_pnl <= -self.max_daily_loss`: `daily_pnl` is in dollars (e.g. `-50.0`) but `max_daily_loss` is a percentage (e.g. `5.0`). Even if #4 were fixed, this comparison is always wrong. | ⬜ Open |
| 6 | 🔴 Critical | `core/position_manager.py` | line 439-455 | Monitoring loop calls `_check_scaling_opportunities()` and `_check_partial_exits()` which access `position['scaling_levels']` and `position['partial_exits']` keys. `_record_trade()` (the only path that creates positions) never initializes these keys → `KeyError` crash every 30 seconds. | ⬜ Open |
| 7 | 🔴 Critical | `main.py` | line 417-430 | If `_send_pre_trade_notification()` raises an exception, the `except` block at line 426 logs it but does NOT `continue`. Execution falls through to `position_manager.execute_trade()` at line 429 — trade executes without user approval. | ⬜ Open |
| 8 | 🔴 Critical | `ai/technical_analysis_layer.py` | line 591 | `market_condition=MarketCondition.BREAKOUT` is hardcoded in every `TradeRecommendation`. Every trade is tagged as "BREAKOUT" regardless of actual market. Corrupts all downstream market condition filtering. | ⬜ Open |
| 9 | 🔴 Critical | `strategies/register_all.py` | all | `FastIchimokuStrategy` is not imported. Also not in `trend_momentum/__init__.py`. Strategy registered via decorator in `fast_ichimoku.py` only fires if the file is imported — it never is. Config allocates 7% to it; registry returns `None`; it silently never runs. | ⬜ Open |
| 10 | 🔴 Critical | `strategies/session_based/london_open_break.py` | line 72 | `candle.time` — `CandleData` has `candle.timestamp`, not `candle.time`. Every call raises `AttributeError`. London Open strategy always silently returns `None`. | ⬜ Open |
| 11 | 🔴 Critical | `strategies/session_based/ny_open_momentum.py` | line 79 | Same `candle.time` vs `candle.timestamp` bug. NY Open strategy always silently returns `None`. | ⬜ Open |
| 12 | 🔴 Critical | `backtesting/backtest_engine.py` | `run_simulation()` | Calls `market_regime_detector.detect_regime(pair, candles_by_tf)` with 2 args. Actual signature is `detect_regime(pair, candles, market_context, technical_indicators)` — 4 required args. Every backtest step raises `TypeError`. | ⬜ Open |
| 13 | 🔴 Critical | `src/trading_bot/config/trading_config.yaml` | whole file | File is **0 bytes** (empty). If this path is ever used as the config source, all settings are blank/default. Any code using this path gets nothing. | ⬜ Open |
| 14 | 🟡 Warning | `ai/technical_analysis_layer.py` | line 441-442 | `min_confluence_score = 0.2` and `min_signals_required = 1` are hardcoded inside `_calculate_signal_confluence()`, ignoring `config.technical_analysis.min_confluence_score` (set to 0.6). Signal generation is much looser than configured. | ⬜ Open |
| 15 | 🟡 Warning | `strategies/strategy_manager.py` | line 280 | `consensus_threshold = 0.30` is hardcoded, ignoring `config.multi_timeframe.consensus_threshold` (0.75 in YAML). Consensus bar is far lower than configured. | ⬜ Open |
| 16 | 🟡 Warning | `core/position_manager.py` | line 604-607 | `_adjust_stop_losses()` calculates `new_stop_loss = entry_price` but never sends it to OANDA. Stop-loss breakeven management is completely non-functional. The variable is computed and discarded. | ⬜ Open |
| 17 | 🟡 Warning | `core/position_manager.py` | line 555-580 | `_partial_exit()` calculates `exit_size = position_size * 0.3` but calls `oanda_api.close_trade(trade_id)` which closes the **entire** trade. Partial exits always close 100% of the position. | ⬜ Open |
| 18 | 🟡 Warning | `core/position_manager.py` | line 609-616 | `_update_daily_pnl()` sums only **unrealized P&L** from open positions. Closed (realized) trade P&L is never counted. Daily loss limit check always uses incomplete data. | ⬜ Open |
| 19 | 🟡 Warning | `main.py` | line 211-232 | `if len(candles_by_timeframe) < 2: continue` requires at least 2 timeframes with 20+ candles. Config says `minimum_timeframes: 1`. Pairs with only one timeframe of data are silently skipped. | ⬜ Open |
| 20 | 🟡 Warning | `data/data_layer.py` | `_create_market_context_from_candles()` | Market context always returns `MarketCondition.RANGING` with `volatility=0.001`. Combined with Issue #8 (hardcoded BREAKOUT recommendation), the regime gate in `strategy_manager.py` only allows mean_reversion strategies (RANGING → only BB_Bounce and RSI_Extremes). Explains the ~4% win rate in backtests. | ⬜ Open |
| 21 | 🟡 Warning | `ai/technical_analysis_layer.py` | line 133 | `rsi_oversold` fallback default is `55` (should be `30`). `rsi_overbought` fallback is `65` (should be `70`). If config fails to load, RSI signals fire incorrectly. | ⬜ Open |
| 22 | 🟡 Warning | `strategies/register_all.py` | all | `DonchianBreakStrategy` not imported (not in `breakout/__init__.py` either). Strategy config references "Donchian_Break" — lookup returns `None`, strategy silently not loaded. | ⬜ Open |
| 23 | 🟡 Warning | `strategies/register_all.py` | all | `SpreadSqueezeStrategy` and `OrderFlowMomentumStrategy` not imported. Both are in YAML strategy config and exist as files, but are never registered. | ⬜ Open |
| 24 | 🟡 Warning | `.env` | whole file | Real OANDA API key, account ID, Telegram token, and MongoDB password are stored in `.env`. Verify this file is in `.gitignore` and has not been committed. Run `git log --all -- .env` to check. | ⬜ Open |
| 25 | 🟡 Warning | `src/trading_bot/main.py` | line 39-40 | Imports `from infrastructure.instrument_collection import ...` and `from api.oanda_api import OandaApi` — these are the **old** pre-refactor modules from `src/infrastructure/` and `src/api/`. These paths are only on `sys.path` if you run from exactly the right directory. Fragile path dependency. | ⬜ Open |
| 26 | 🟡 Warning | `core/position_manager.py` | line 147 | `is_demo` detection uses `config.oanda_account_id.startswith('101-')`. This is not a reliable way to detect demo accounts — live accounts can also start with `101-`. | ⬜ Open |
| 27 | 🟡 Warning | `strategies/strategy_manager.py` | line 213-217 | Requires `len(strategy_signals) >= self.min_strategies_agreeing` (default 2) strategies to agree. With Issues #10, #11, #9 killing London Open, NY Open, and Fast Ichimoku, and Issue #20 keeping market in RANGING (only mean_reversion allowed), it is structurally impossible for 2 strategies to agree in most conditions. | ⬜ Open |
| 28 | 🟡 Warning | `notifications/notification_layer.py` | startup | `python-dotenv` is never called to load `.env`. Telegram bot token and chat ID must be exported manually in the shell session, or the bot won't send notifications. | ⬜ Open |
| 29 | 🔵 Info | `strategies/strategy_manager.py` | line 45-47 | `@debug_line` decorator placed with 2 blank lines before `def __init__`. Valid in Python 3.12+ (PEG parser), but would break on Python < 3.12. Consistent throughout strategy files. | ⬜ Open |
| 30 | 🔵 Info | `src/trading_bot/config/trading_config.yaml` | dead file | This empty file at `src/trading_bot/config/` is never loaded (config loads from `src/trading_bot/src/config/`). Causes confusion — contributors might edit the wrong file. Delete it or add a comment. | ⬜ Open |
| 31 | 🔵 Info | `config/trading_config.yaml` comments | throughout | Many config comments contradict the values they describe. E.g., `risk_percentage: 1.5  # 4.0% per trade`, `max_open_trades: 3  # One per pair (was 2)`. Risk of future bugs from copy-paste edits. | ⬜ Open |
| 32 | 🔵 Info | `core/smart_execution_engine.py` | whole file | File exists but is never instantiated or called from any other module. Dead code. | ⬜ Open |
| 33 | 🔵 Info | `core/portfolio_risk_manager.py` | whole file | Duplicate risk manager, not connected to main flow. Dead code. | ⬜ Open |
| 34 | 🔵 Info | `decision/risk_manager.py` | whole file | Third risk manager implementation. Not connected to main flow. Dead code. | ⬜ Open |
| 35 | 🔵 Info | `ai/order_flow_analyzer.py` | whole file | Not imported or used anywhere. Dead code. | ⬜ Open |
| 36 | 🔵 Info | `analysis/performance_attribution.py` | whole file | Not imported or used anywhere. Dead code. | ⬜ Open |
| 37 | 🔵 Info | Multiple files | various | `ScrapingDataIntegration` is imported in `backtest_engine.py` but the `scraping/` modules use Selenium and appear incompatible with async context. Not tested. | ⬜ Open |
| 38 | 🔵 Info | `core/position_manager.py` | line 412-437 | `_track_new_position()` exists and properly initializes `scaling_levels` and `partial_exits`, but is **never called** from anywhere. `_record_trade()` is called instead (which doesn't initialize them). | ⬜ Open |
| 39 | 🔵 Info | `strategies/mean_reversion/stochastic_reversal.py` | decorator | Registered as "Fast_Stochastic" in registry but the YAML config references "Fast_Stochastic" only in the default `StrategyPortfolioConfig` — the actual loaded YAML does NOT include it. Mismatch between hardcoded defaults and live config. | ⬜ Open |
| 40 | 🔵 Info | `backtest_report_*.txt` | project root | 18+ backtest report files in project root. Should be in `results/` or `.gitignore`d. Many are untracked. | ⬜ Open |

---

## Architecture Notes

### Data Flow (Live Trading)
```
run.py → TradingBot.__init__() → TradingBot.start() → _enhanced_trading_loop()
  └→ DataLayer.get_all_data()                     [fetches OANDA candles for all pairs/timeframes]
  └→ DataLayer.get_market_context()               ⚠️ ALWAYS returns RANGING condition
  └→ FundamentalAnalyzer.analyze_fundamentals()   (stub, non-functional)
  └→ TechnicalAnalysisLayer.analyze_multiple_timeframes()
        └→ StrategyManager.generate_consensus_signal()
              └→ Regime gate (RANGING → only mean_reversion allowed) ← caused by Issue #20
              └→ Strategy.generate_signal()
                    └→ LondonOpen/NYOpen: ❌ crashes on candle.time  (Issues #10, #11)
                    └→ BB_Bounce / RSI_Extremes: ✅ only ones that work
              └→ _create_consensus_recommendation() ❌ crashes (Issue #3)
        └→ Fallback: legacy signal analysis (runs if consensus crashes)
              └→ Returns recommendation with hardcoded BREAKOUT condition (Issue #8)
  └→ TechnicalDecisionLayer.make_technical_decision()
  └→ AdvancedRiskManager.assess_trade_risk()       ❌ crashes (Issue #2) → approved=False
  └→ [trade never executes via risk path]
  └→ manual_trade_approval=True → notification sent → user approves → execute
        └→ PositionManager.execute_trade()         ← position recorded without scaling_levels/partial_exits
        └→ Monitoring loop: ❌ KeyError every 30s   (Issue #6)
```

### Data Flow (Backtest)
```
run.py → BacktestEngine.run_backtest()
  └→ OandaHistoricalFeed for candles
  └→ TechnicalAnalysisLayer (same as live)
  └→ MarketRegimeDetector.detect_regime() ← called with wrong arity (Issue #12) → TypeError every step
```

### Key Anti-Patterns Found
1. **Three separate risk manager implementations** — `advanced_risk_manager.py`, `portfolio_risk_manager.py`, `decision/risk_manager.py`. Only `advanced_risk_manager.py` is connected to the main flow, and it crashes.
2. **Two config files** — active one is `src/trading_bot/src/config/`, the outer `src/trading_bot/config/` is empty and unused.
3. **Silent failures masked by try/except** — nearly every analysis step is wrapped in broad `except Exception` that logs and continues. Crashes in AdvancedRiskManager and StrategyManager silently degrade to `approved=False` or `None` without surfacing to the user.
4. **Hardcoded values overriding config** — `min_confluence_score`, `consensus_threshold`, `market_condition` are all hardcoded in method bodies, not read from config.
5. **Dead code accumulation** — 4 unused files (smart_execution_engine, portfolio_risk_manager, order_flow_analyzer, performance_attribution) and 2 unused scalping strategies are never imported or called.

---

## Config Inconsistencies

| # | Location | Value | Comment Says | Actual Effect |
|---|----------|-------|--------------|---------------|
| 1 | `trading.risk_percentage: 1.5` | 1.5% | `# 4.0% per trade` | 1.5% used |
| 2 | `risk_management.max_open_trades: 3` | 3 | `# One per pair (was 2)` | 3 allowed |
| 3 | `technical_analysis.min_signals_required: 1` | 1 | `# INCREASED from 1 to 3` | Still 1 |
| 4 | `notifications.loop_reports.enabled: true` | true | `# Disabled to reduce notification spam` | Enabled |
| 5 | `trading.hold_time_settings.force_close_enabled: false` | false | Intended for 24/7 but disables force-close | Force close OFF |
| 6 | Default `StrategyPortfolioConfig` in `config.py` | 14 strategies | Active YAML has different strategy list | Config.py defaults never used; YAML always loaded |
| 7 | `RiskManagementConfig.max_risk_threshold` | MISSING | Used in `advanced_risk_manager.py` line 132 | AttributeError |
| 8 | `consensus_threshold` in strategy_manager.py | 0.30 (hardcoded) | Config YAML has 0.75 | Ignored |
| 9 | `min_confluence_score` in technical_analysis_layer.py | 0.2 (hardcoded) | Config has 0.6 | Ignored |

---

## Prioritized Fix List

### Must Fix First (Bot Cannot Run)

**Fix 1 — `run.py:318`: rename `bot.run()` to `bot.start()`**
```python
# run.py line 318
await bot.start()   # was: await bot.run()
```

**Fix 2 — `RiskManagementConfig`: add `max_risk_threshold` field**
```python
# core/advanced_risk_manager.py line 132 references:
config.risk_management.max_risk_threshold
# Add to RiskManagementConfig dataclass in config.py:
max_risk_threshold: float = 0.7
# AND add to YAML:
risk_management:
  max_risk_threshold: 0.7
```

**Fix 3 — `TradeRecommendation`: add `metadata` field**
```python
# Add to TradeRecommendation dataclass in models.py:
metadata: Dict[str, Any] = field(default_factory=dict)
```

**Fix 4 — Session strategies: `candle.time` → `candle.timestamp`**
```python
# london_open_break.py line 72
candle_time = candle.timestamp.time() if hasattr(candle.timestamp, 'time') else candle.timestamp
# ny_open_momentum.py line 79 — same fix
candle_time = candle.timestamp.time() if hasattr(candle.timestamp, 'time') else candle.timestamp
```

**Fix 5 — `register_all.py`: import `FastIchimokuStrategy`**
```python
# Add to register_all.py:
from .trend_momentum.fast_ichimoku import FastIchimokuStrategy
```

**Fix 6 — `position_manager._record_trade()`: initialize missing keys**
```python
# In _record_trade(), add to active_positions dict:
'scaling_levels': [],
'partial_exits': [],
```

**Fix 7 — `main.py:426`: add `continue` after notification exception**
```python
except Exception as e:
    self.logger.error(f"Pre-trade notification failed: {e}")
    continue   # ADD THIS — prevent trade executing without approval
```

**Fix 8 — Backtest `detect_regime()` call: pass required args**
Pass `market_context` and `technical_indicators` to `detect_regime()` in backtest engine's simulation loop.

---

### Fix Next (Bot Trades But Incorrectly)

**Fix 9 — `technical_analysis_layer.py:591`: use actual market condition**
```python
# Replace hardcoded:
market_condition=MarketCondition.BREAKOUT,
# With:
market_condition=market_context.condition if market_context else MarketCondition.UNKNOWN,
```

**Fix 10 — `position_manager.py`: call `_can_execute_trade()` in `execute_trade()`**
Add `if not await self._can_execute_trade(decision): return None` as the first check inside `execute_trade()`.

**Fix 11 — Daily P&L type mismatch**
Convert `max_daily_loss` to dollars before comparing: `max_daily_loss_dollars = account_balance * (self.max_daily_loss / 100)` then compare `self.daily_pnl <= -max_daily_loss_dollars`.

**Fix 12 — Read `min_confluence_score` and `consensus_threshold` from config, not hardcoded values.**

**Fix 13 — `data_layer._create_market_context_from_candles()`: implement real market condition detection** (currently always returns RANGING).

---

### Fix Later (Quality / Safety)

**Fix 14** — `_adjust_stop_losses()`: actually call OANDA API to update stop loss.
**Fix 15** — `_partial_exit()`: use OANDA's partial close API instead of `close_trade()`.
**Fix 16** — `_update_daily_pnl()`: add realized P&L from closed trades.
**Fix 17** — Add `max_risk_threshold: 0.7` to YAML config.
**Fix 18** — Delete or populate `src/trading_bot/config/trading_config.yaml`.
**Fix 19** — Import `DonchianBreakStrategy`, `SpreadSqueezeStrategy`, `OrderFlowMomentumStrategy` in `register_all.py`.
**Fix 20** — Verify `.env` is in `.gitignore` and not committed: `git log --all -- .env`.
**Fix 21** — Call `python-dotenv`'s `load_dotenv()` at startup, or document manual `export` requirement.
**Fix 22** — Remove dead code files: smart_execution_engine, portfolio_risk_manager, order_flow_analyzer, performance_attribution (or connect them).
**Fix 23** — Fix config comment contradictions throughout YAML.
**Fix 24** — Move backtest report files to `results/` and add `backtest_report_*.txt` to `.gitignore`.
**Fix 25** — `main.py` line 232: change `< 2` to `< 1` (or read from `config.multi_timeframe.minimum_timeframes`).

---

## Root Cause of 4% Win Rate in Backtests

The compounding chain that killed backtest performance:

1. `DataLayer._create_market_context_from_candles()` always returns `MarketCondition.RANGING`
2. Regime gate in `StrategyManager` maps RANGING → only `mean_reversion` strategies allowed
3. Only `BB_Bounce_M5` and `RSI_Extremes` are eligible (allocation 10% + 8% = 18% total)
4. `min_strategies_agreeing=2` requires BOTH to agree simultaneously on the same candle → very rare
5. The few signals that do fire: `_create_consensus_recommendation()` crashes (Issue #3, `metadata` TypeError)
6. Fallback to legacy analysis gives hardcoded `BREAKOUT` condition on every recommendation
7. Those recommendations hit `AdvancedRiskManager` which crashes (Issue #2, `max_risk_threshold`)
8. `approved=False` → no trades execute through the normal path
9. Trades only execute when notifications are manually approved (with `manual_trade_approval=true`)
10. Backtest doesn't have Telegram, so zero trades execute in backtesting

Fix Issues #2, #3, #8, #12, #20 and re-run the backtest — the results should change dramatically.

---

## Session History
- **2026-03-11 06:47** — Full audit started. All 50+ source files read systematically.
- **2026-03-11 07:10** — 40 issues catalogued. DEBUG_JOURNAL.md written.
