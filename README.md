# Automated Trading Bot

Professional intraday forex trading bot with multi-strategy framework.

## 🚀 Quick Start

### 1. Run Backtest
```bash
python run.py backtest --days 30
```

### 2. Validate System
```bash
python run.py validate
```

### 3. Run Live Trading
```bash
python run.py live
```

## 📊 Features

- **15 Professional Strategies** - Trend, mean reversion, breakout, scalping, session-based
- **Multi-Strategy Consensus** - Weighted ensemble voting system
- **Intraday Optimized** - M1/M5/M15 timeframes, 20-240 minute holds
- **Auto Market Adaptation** - Right strategy for right conditions
- **Session-Aware** - London/NY session trading
- **Risk Management** - 1.5% per trade, 2.5% daily max loss
- **Force Close** - All positions closed before 16:30 EST

## 📁 Project Structure

```
├── src/trading_bot/          # Main bot code
│   ├── config/               # Configuration files
│   ├── src/
│   │   ├── strategies/       # 15 trading strategies
│   │   ├── ai/               # Technical analysis
│   │   ├── core/             # Core models and managers
│   │   ├── decision/         # Risk management
│   │   └── backtesting/      # Backtest engine
│   └── main.py               # Bot entry point
│
├── tests/                    # Test suite
├── data/                     # Market data
├── logs/                     # Trading logs
├── run.py                    # Unified runner
└── validate_strategies.py    # Validation script
```

## 🎯 Commands

### Backtesting
```bash
# Standard backtest
python run.py backtest --days 30

# With specific pairs
python run.py backtest --days 90 --pairs EUR_USD GBP_USD USD_JPY

# Quiet mode (minimal output)
python run.py backtest --quiet --days 7

# Compare multi-strategy vs single-strategy
python run.py backtest --compare
```

### Validation
```bash
# Validate all strategies and config
python run.py validate
```

### Testing
```bash
# Run tests
pytest tests/ -v
```

### Live Trading
```bash
# Start live trading
python run.py live
```

## ⚙️ Configuration

Main config: `src/trading_bot/config/trading_config.yaml`

### Enable/Disable Multi-Strategy
```yaml
strategy_portfolio:
  enabled: true  # Set to false for single-strategy mode
```

### Adjust Strategy Allocations
Edit lines 139-310 in `trading_config.yaml`

## 📈 Performance Expectations

| Metric | Target |
|--------|--------|
| Win Rate | 55-60% |
| Sharpe Ratio | 1.8-2.2 |
| Max Drawdown | 8-10% |
| Profit Factor | 1.7-2.0 |

## 📚 Documentation

- **Complete Guide**: `MULTI_STRATEGY_COMPLETE.md` - Everything you need to know
- **Production Summary**: `PRODUCTION_READY_SUMMARY.md` - Current status and features

## 🔧 Environment Setup

1. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure API keys in `config.env`:
```env
OANDA_API_KEY=your_key_here
OANDA_ACCOUNT_ID=your_account_id
```

## ⚠️ Important Notes

- **Paper Trade First** - Test on demo account before live
- **Monitor Performance** - Watch for "Multi-strategy consensus" messages
- **Risk Management** - Strict limits: 1.5% per trade, 2.5% daily max
- **Intraday Only** - All positions closed before 16:30 EST

## 📞 Support

- Configuration issues: Check `trading_config.yaml`
- Strategy issues: Run `python run.py validate`
- API issues: Verify `config.env` settings

## 🎓 Multi-Strategy System

The bot uses **15 specialized strategies** that vote on each trade:

**Trend (30%):** EMA, MACD, ADX, Ichimoku  
**Mean Reversion (25%):** Bollinger, RSI, Stochastic  
**Breakout (20%):** ATR, S/R, Donchian  
**Scalping (15%):** Price Action, Spread, Order Flow  
**Session (10%):** London Open, NY Open  

Requires minimum 2 strategies to agree before trading.

## 📊 Status

✅ Production-ready  
✅ 15 strategies implemented  
✅ Full integration complete  
✅ Comprehensive testing  
⏳ Backtest validation recommended  
⏳ Paper trading recommended  

---

*For complete documentation, see `MULTI_STRATEGY_COMPLETE.md`*









