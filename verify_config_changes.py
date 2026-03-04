#!/usr/bin/env python3
"""
Configuration Verification Script
Verify that all the backtest configuration changes have been applied correctly.
"""

import yaml
import os

def verify_config_changes():
    """Verify that all configuration changes have been applied."""
    
    config_path = "src/trading_bot/config/trading_config.yaml"
    
    if not os.path.exists(config_path):
        print("❌ Configuration file not found!")
        return False
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    print("🔍 VERIFYING BACKTEST CONFIGURATION CHANGES")
    print("=" * 60)
    
    # Check trading limitations removed
    print("\n📊 TRADING LIMITATIONS REMOVED:")
    
    # Max trades per day
    max_trades = config.get('trading', {}).get('max_trades_per_day', 0)
    if max_trades >= 999:
        print(f"✅ max_trades_per_day: {max_trades} (unlimited)")
    else:
        print(f"❌ max_trades_per_day: {max_trades} (should be 999)")
    
    # Force close disabled
    force_close = config.get('trading', {}).get('hold_time_settings', {}).get('force_close_enabled', True)
    if not force_close:
        print("✅ force_close_enabled: false (24/7 trading)")
    else:
        print("❌ force_close_enabled: true (should be false)")
    
    # Trade cooldown
    cooldown = config.get('technical_analysis', {}).get('trade_cooldown_minutes', 30)
    if cooldown == 0:
        print(f"✅ trade_cooldown_minutes: {cooldown} (no cooldown)")
    else:
        print(f"❌ trade_cooldown_minutes: {cooldown} (should be 0)")
    
    # Daily loss cooldown
    daily_cooldown = config.get('risk_management', {}).get('daily_loss_cooldown_minutes', 60)
    if daily_cooldown == 0:
        print(f"✅ daily_loss_cooldown_minutes: {daily_cooldown} (no cooldown)")
    else:
        print(f"❌ daily_loss_cooldown_minutes: {daily_cooldown} (should be 0)")
    
    # Intraday rules
    min_time = config.get('strategy_portfolio', {}).get('intraday_rules', {}).get('min_time_between_trades', 10)
    max_session = config.get('strategy_portfolio', {}).get('intraday_rules', {}).get('max_trades_per_session', 3)
    avoid_news = config.get('strategy_portfolio', {}).get('intraday_rules', {}).get('avoid_news_minutes', 15)
    
    if min_time == 0:
        print(f"✅ min_time_between_trades: {min_time} (no delay)")
    else:
        print(f"❌ min_time_between_trades: {min_time} (should be 0)")
    
    if max_session >= 999:
        print(f"✅ max_trades_per_session: {max_session} (unlimited)")
    else:
        print(f"❌ max_trades_per_session: {max_session} (should be 999)")
    
    if avoid_news == 0:
        print(f"✅ avoid_news_minutes: {avoid_news} (trade during news)")
    else:
        print(f"❌ avoid_news_minutes: {avoid_news} (should be 0)")
    
    print("\n🎯 SIGNAL QUALITY THRESHOLDS LOWERED:")
    
    # Confidence thresholds
    conf_threshold = config.get('technical_analysis', {}).get('confidence_threshold', 0.45)
    min_conf = config.get('technical_analysis', {}).get('minimum_confidence', 0.40)
    
    if conf_threshold <= 0.35:
        print(f"✅ confidence_threshold: {conf_threshold} (lowered)")
    else:
        print(f"❌ confidence_threshold: {conf_threshold} (should be <= 0.35)")
    
    if min_conf <= 0.30:
        print(f"✅ minimum_confidence: {min_conf} (lowered)")
    else:
        print(f"❌ minimum_confidence: {min_conf} (should be <= 0.30)")
    
    # Signal strength
    signal_strength = config.get('technical_analysis', {}).get('signal_strength_threshold', 0.005)
    if signal_strength <= 0.002:
        print(f"✅ signal_strength_threshold: {signal_strength} (lowered)")
    else:
        print(f"❌ signal_strength_threshold: {signal_strength} (should be <= 0.002)")
    
    # Risk/reward ratio
    risk_reward = config.get('technical_analysis', {}).get('risk_reward_ratio_minimum', 1.0)
    if risk_reward <= 0.8:
        print(f"✅ risk_reward_ratio_minimum: {risk_reward} (lowered)")
    else:
        print(f"❌ risk_reward_ratio_minimum: {risk_reward} (should be <= 0.8)")
    
    # Volatility threshold
    volatility = config.get('market_conditions', {}).get('volatility_threshold', 0.0008)
    if volatility <= 0.0005:
        print(f"✅ volatility_threshold: {volatility} (lowered)")
    else:
        print(f"❌ volatility_threshold: {volatility} (should be <= 0.0005)")
    
    print("\n🌍 SESSION RESTRICTIONS DISABLED:")
    
    # Check if session-based strategies have active_hours commented out
    strategies = config.get('strategy_portfolio', {}).get('strategies', [])
    london_break = None
    ny_momentum = None
    
    for strategy in strategies:
        if strategy.get('name') == 'London_Open_Break':
            london_break = strategy
        elif strategy.get('name') == 'NY_Open_Momentum':
            ny_momentum = strategy
    
    if london_break and 'active_hours' not in london_break:
        print("✅ London_Open_Break: active_hours removed (24/7 trading)")
    elif london_break and london_break.get('active_hours') == []:
        print("✅ London_Open_Break: active_hours empty (24/7 trading)")
    else:
        print("❌ London_Open_Break: active_hours still restricted")
    
    if ny_momentum and 'active_hours' not in ny_momentum:
        print("✅ NY_Open_Momentum: active_hours removed (24/7 trading)")
    elif ny_momentum and ny_momentum.get('active_hours') == []:
        print("✅ NY_Open_Momentum: active_hours empty (24/7 trading)")
    else:
        print("❌ NY_Open_Momentum: active_hours still restricted")
    
    print("\n" + "=" * 60)
    print("📋 SUMMARY:")
    print("=" * 60)
    
    # Count successful changes
    changes_applied = 0
    total_changes = 12
    
    if max_trades >= 999: changes_applied += 1
    if not force_close: changes_applied += 1
    if cooldown == 0: changes_applied += 1
    if daily_cooldown == 0: changes_applied += 1
    if min_time == 0: changes_applied += 1
    if max_session >= 999: changes_applied += 1
    if avoid_news == 0: changes_applied += 1
    if conf_threshold <= 0.35: changes_applied += 1
    if min_conf <= 0.30: changes_applied += 1
    if signal_strength <= 0.002: changes_applied += 1
    if risk_reward <= 0.8: changes_applied += 1
    if volatility <= 0.0005: changes_applied += 1
    
    print(f"✅ Configuration changes applied: {changes_applied}/{total_changes}")
    
    if changes_applied >= 10:
        print("🎉 EXCELLENT: Most configuration changes have been applied!")
        print("🚀 Your backtester should now generate significantly more trades.")
        print("📊 Expected: 30+ trades instead of 3")
    elif changes_applied >= 8:
        print("✅ GOOD: Most configuration changes have been applied.")
        print("🔧 A few minor adjustments may be needed.")
    else:
        print("⚠️  PARTIAL: Some configuration changes may not have been applied.")
        print("🔧 Please check the configuration file manually.")
    
    print("\n💡 NEXT STEPS:")
    print("1. Run the backtest to verify increased trade count")
    print("2. Check rejection statistics in the output")
    print("3. If still getting < 30 trades, further lower thresholds")
    print("4. Once achieving 30+ trades, evaluate quality metrics")
    
    return changes_applied >= 8

if __name__ == "__main__":
    verify_config_changes()





