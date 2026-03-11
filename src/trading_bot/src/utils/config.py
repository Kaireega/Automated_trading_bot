"""
Trading Bot Configuration Management - Production Ready Version.

This module provides comprehensive configuration management for the automated trading bot,
including environment variable loading, YAML configuration parsing, and validation.

Key Features:
- Environment variable loading with fallbacks
- YAML configuration file parsing
- Configuration validation and error handling
- Type-safe configuration access
- Multi-strategy portfolio configuration
- Risk management settings
- Technical analysis parameters

Author: Trading Bot Development Team
Version: 2.1.0 - Production Ready
Last Updated: 2024
"""
import os
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from decimal import Decimal
import logging

# Import comprehensive debugging utilities
from trading_bot.src.utils.debug_utils import (
    debug_tracker, debug_line, debug_variable, debug_context, 
    debug_performance, debug_data_flow, debug_api_call, 
    debug_trade_decision, debug_strategy_execution, debug_risk_calculation,
    debug_indicator_calculation, debug_backtest_step, debug_entry_point,
    debug_exit_point, debug_conditional, debug_loop_iteration,
    get_debug_summary, export_debug_report
)


@dataclass
class TradingConfig:
    """Trading configuration parameters."""
    risk_percentage: float = 2.0
    max_trades_per_day: int = 6
    default_timeframe: str = "M5"
    pairs: List[str] = field(default_factory=lambda: ["EUR_USD", "GBP_USD", "USD_JPY"])
    min_hold_time_minutes: int = 20
    max_hold_time_minutes: int = 240
    default_hold_time_minutes: int = 90
    force_close_enabled: bool = True
    force_close_time: str = "16:30"
    market_condition_hold_times: Dict[str, List[int]] = field(default_factory=lambda: {
        "news_reactionary": [20, 180],
        "reversal": [60, 240],
        "breakout": [90, 240],
        "ranging": [20, 180]
    })


@dataclass
class MultiTimeframeConfig:
    """Multi-timeframe analysis configuration."""
    enabled: bool = True
    timeframes: List[str] = field(default_factory=lambda: ["M5", "M15"])
    weights: Dict[str, float] = field(default_factory=lambda: {"M5": 0.4, "M15": 0.6})
    minimum_timeframes: int = 1
    consensus_threshold: float = 0.4


@dataclass
class MarketConditionsConfig:
    """Market conditions configuration."""
    volatility_threshold: float = 0.0008
    trend_strength_threshold: float = 0.60
    breakout_threshold: float = 0.0015
    ranging_threshold: float = 0.0008
    preferred_sessions: List[str] = field(default_factory=list)
    avoid_sessions: List[str] = field(default_factory=list)


@dataclass
class RiskManagementConfig:
    """Risk management configuration."""
    max_daily_loss: float = 5.0
    max_position_size: float = 2.0
    correlation_limit: float = 0.6
    max_open_trades: int = 2
    stop_loss_atr_multiplier: float = 1.5
    trailing_stop: bool = True
    trailing_stop_atr_multiplier: float = 1.0
    consecutive_loss_limit: int = 3
    daily_loss_cooldown_minutes: int = 60
    scale_down_after_losses: bool = True
    loss_scale_down_pct: int = 50
    max_risk_threshold: float = 0.7


@dataclass
class TechnicalAnalysisConfig:
    """Technical analysis configuration."""
    confidence_threshold: float = 0.45  # Lowered for more trades
    signal_strength_threshold: float = 0.003  # Lowered for more trades
    minimum_confidence: float = 0.40  # Lowered for more trades
    risk_reward_ratio_minimum: float = 1.0  # Lowered for more trades
    analysis_frequency: int = 300
    include_volume_analysis: bool = True
    include_market_context: bool = True
    min_signals_required: int = 1  # Lowered for more trades
    min_confluence_score: float = 0.3  # Lowered for more trades
    rsi_oversold: int = 30
    rsi_overbought: int = 70
    macd_signal_threshold: float = 0.0001
    bollinger_threshold: float = 0.05
    atr_multiplier: float = 2.0
    trade_cooldown_minutes: int = 30
    ranging_confidence_penalty: float = 0.05
    signal_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "strong_buy": 0.8,
        "buy": 0.6,
        "neutral": 0.4,
        "sell": 0.6,
        "strong_sell": 0.8
    })


@dataclass
class NotificationsConfig:
    """Notifications configuration."""
    telegram_enabled: bool = False
    send_charts: bool = True
    send_analysis: bool = True
    email_enabled: bool = False
    daily_summary: bool = True
    trade_alerts: bool = True
    loop_reports_enabled: bool = True
    send_on_error: bool = True
    include_performance: bool = True
    notification_cooldown: int = 300
    manual_trade_approval: bool = True
    pre_trade_cooldown_seconds: int = 0


@dataclass
class DataCollectionConfig:
    """Data collection configuration."""
    historical_days: int = 30
    update_frequency: int = 300
    store_raw_data: bool = True
    compression: bool = True
    backup_frequency: int = 24


@dataclass
class SimulationConfig:
    """Simulation configuration."""
    enabled: bool = True
    data_source: str = "db"
    csv_dir: str = "data"
    spread_pips: float = 1.5
    slippage_pips: float = 0.5


@dataclass
class PerformanceConfig:
    """Performance tracking configuration."""
    track_metrics: bool = True
    save_trades: bool = True
    generate_reports: bool = True
    report_frequency: str = "daily"


@dataclass
class StrategyPortfolioConfig:
    """Strategy portfolio configuration."""
    enabled: bool = True
    mode: str = "intraday"
    selection: Dict[str, Any] = field(default_factory=lambda: {
        "mode": "weighted_ensemble",
        "min_strategies_agreeing": 2,
        "confidence_weighting": True,
        "timeframe_priority": ["M5", "M15", "M1"]
    })
    strategies: List[Dict[str, Any]] = field(default_factory=lambda: [
        # Trend Momentum Strategies (30% allocation)
        {
            "name": "Fast_EMA_Cross_M5",
            "type": "trend_momentum",
            "allocation": 8,
            "timeframes": ["M5", "M15"],
            "parameters": {"ema_fast": 8, "ema_slow": 21},
            "conditions": ["TRENDING_UP", "TRENDING_DOWN"],
            "min_confidence": 0.65
        },
        {
            "name": "MACD_Momentum_M5",
            "type": "trend_momentum",
            "allocation": 8,
            "timeframes": ["M5"],
            "parameters": {"fast": 12, "slow": 26, "signal": 9, "histogram_threshold": 0.00005},
            "conditions": ["TRENDING_UP", "TRENDING_DOWN"],
            "min_confidence": 0.60
        },
        {
            "name": "ADX_Trend_M5",
            "type": "trend_momentum",
            "allocation": 7,
            "timeframes": ["M5", "M15"],
            "parameters": {"period": 14, "threshold": 20},
            "conditions": ["TRENDING_UP", "TRENDING_DOWN"],
            "min_confidence": 0.65
        },
        {
            "name": "Fast_Ichimoku",
            "type": "trend_momentum",
            "allocation": 7,
            "timeframes": ["M5", "M15"],
            "parameters": {"tenkan": 5, "kijun": 13, "senkou": 26},
            "conditions": ["TRENDING_UP", "TRENDING_DOWN", "BREAKOUT"],
            "min_confidence": 0.70
        },
        # Mean Reversion Strategies (25% allocation)
        {
            "name": "BB_Bounce_M5",
            "type": "mean_reversion",
            "allocation": 10,
            "timeframes": ["M5"],
            "parameters": {"period": 20, "std_dev": 2, "touch_threshold": 0.001},
            "conditions": ["RANGING"],
            "min_confidence": 0.60
        },
        {
            "name": "RSI_Extremes",
            "type": "mean_reversion",
            "allocation": 8,
            "timeframes": ["M5"],
            "parameters": {"period": 14, "oversold": 35, "overbought": 65, "extreme_oversold": 25, "extreme_overbought": 75},
            "conditions": ["RANGING"],
            "min_confidence": 0.65
        },
        {
            "name": "Fast_Stochastic",
            "type": "mean_reversion",
            "allocation": 7,
            "timeframes": ["M5"],
            "parameters": {"k_period": 5, "d_period": 3, "smooth": 3},
            "conditions": ["RANGING"],
            "min_confidence": 0.60
        },
        # Breakout Strategies (20% allocation)
        {
            "name": "ATR_Breakout",
            "type": "breakout",
            "allocation": 7,
            "timeframes": ["M5", "M15"],
            "parameters": {"atr_period": 14, "multiplier": 1.5, "lookback": 20},
            "conditions": ["VOLATILE", "BREAKOUT"],
            "min_confidence": 0.70
        },
        {
            "name": "Support_Resistance_Break",
            "type": "breakout",
            "allocation": 7,
            "timeframes": ["M5", "M15"],
            "parameters": {"lookback_periods": 50, "break_threshold": 0.0005, "confirmation_candles": 1},
            "conditions": ["BREAKOUT"],
            "min_confidence": 0.65
        },
        {
            "name": "Donchian_Break",
            "type": "breakout",
            "allocation": 6,
            "timeframes": ["M5"],
            "parameters": {"period": 10, "exit_period": 5},
            "conditions": ["BREAKOUT", "RANGING"],
            "min_confidence": 0.65
        },
        # Scalping Strategies (15% allocation)
        {
            "name": "Price_Action_Scalp",
            "type": "scalping",
            "allocation": 5,
            "timeframes": ["M1", "M5"],
            "parameters": {"min_body_ratio": 0.6, "min_wick_ratio": 2.0},
            "conditions": ["ALL"],
            "min_confidence": 0.70,
            "hold_time_override": [5, 30]
        },
        {
            "name": "Spread_Squeeze",
            "type": "scalping",
            "allocation": 5,
            "timeframes": ["M1", "M5"],
            "parameters": {"max_spread_pips": 1.5, "volume_spike_threshold": 1.5},
            "conditions": ["ALL"],
            "min_confidence": 0.65,
            "hold_time_override": [5, 45]
        },
        {
            "name": "Order_Flow_Momentum",
            "type": "scalping",
            "allocation": 5,
            "timeframes": ["M1", "M5"],
            "parameters": {"imbalance_threshold": 0.6, "lookback": 5},
            "conditions": ["ALL"],
            "min_confidence": 0.70,
            "hold_time_override": [10, 60]
        },
        # Session-Based Strategies (10% allocation)
        {
            "name": "London_Open_Break",
            "type": "session_based",
            "allocation": 5,
            "timeframes": ["M5", "M15"],
            "parameters": {"session_start": "08:00", "range_period_minutes": 60, "min_range_pips": 10},
            "conditions": ["BREAKOUT"],
            "min_confidence": 0.70,
            "active_hours": ["08:00-16:00"]
        },
        {
            "name": "NY_Open_Momentum",
            "type": "session_based",
            "allocation": 5,
            "timeframes": ["M5"],
            "parameters": {"session_start": "13:00", "momentum_period_minutes": 30, "min_momentum_pips": 8},
            "conditions": ["TRENDING_UP", "TRENDING_DOWN"],
            "min_confidence": 0.70,
            "active_hours": ["13:00-14:00"]
        }
    ])
    intraday_rules: Dict[str, Any] = field(default_factory=lambda: {
        "max_hold_minutes": 240,
        "force_close_time": "16:30",
        "avoid_news_minutes": 15,
        "min_time_between_trades": 10,
        "max_trades_per_session": 3
    })
    rebalancing: Dict[str, Any] = field(default_factory=lambda: {
        "enabled": False,
        "frequency_days": 30,
        "method": "performance_based",
        "min_allocation": 5,
        "max_allocation": 25
    })


class Config:
    """
    Main configuration class for the trading bot.
    
    This class provides comprehensive configuration management including:
    - Environment variable loading
    - YAML configuration file parsing
    - Configuration validation
    - Type-safe access to all configuration parameters
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration.
        
        Args:
            config_path: Optional path to configuration file
        """
        debug_entry_point("Config.__init__")
        
        with debug_context("Configuration initialization") as context:
            self.logger = logging.getLogger(__name__)
            
            # Load environment variables
            debug_data_flow("env_loading", "starting", "environment_variables")
            self._load_environment_variables()
            debug_variable("env_variables_loaded", True, context)
            
            # Load YAML configuration
            debug_data_flow("yaml_loading", "starting", "yaml_configuration")
            self._config = self._load_yaml_config(config_path)
            debug_variable("yaml_config_loaded", True, context)
            
            # Initialize configuration sections
            debug_data_flow("config_sections", "initializing", "configuration_sections")
            self._initialize_config_sections()
            debug_variable("config_sections_initialized", True, context)
            
            debug_exit_point("Config.__init__")
    
    def _load_environment_variables(self):
        """Load environment variables with fallbacks."""
        # API Configuration
        self.oanda_api_key = os.getenv('OANDA_API_KEY', '')
        self.oanda_account_id = os.getenv('OANDA_ACCOUNT_ID', '')
        self.oanda_url = os.getenv('OANDA_URL', 'https://api-fxpractice.oanda.com/v3')
        
        # OpenAI API Configuration
        self.openai_api_key = os.getenv('OPENAI_API_KEY', '')
        
        # MongoDB Configuration
        self.mongodb_uri = os.getenv('MONGODB_URI', '')
        
        # Trading Configuration
        self.risk_percentage = float(os.getenv('RISK_PERCENTAGE', '2.0'))
        self.max_trades_per_day = int(os.getenv('MAX_TRADES_PER_DAY', '6'))
        self.default_timeframe = os.getenv('DEFAULT_TIMEFRAME', 'M5')
        
        # Technical Analysis Configuration
        self.technical_confidence_threshold = float(os.getenv('TECHNICAL_CONFIDENCE_THRESHOLD', '0.45'))
        self.technical_risk_reward_minimum = float(os.getenv('TECHNICAL_RISK_REWARD_MINIMUM', '1.0'))
        
        # AI Analysis Configuration
        self.ai_confidence_threshold = float(os.getenv('AI_CONFIDENCE_THRESHOLD', '0.5'))
        self.ai_analysis_frequency = int(os.getenv('AI_ANALYSIS_FREQUENCY', '300'))
        
        # Logging Configuration
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.log_file = os.getenv('LOG_FILE', 'logs/trading_bot.log')
        
        # Production Configuration
        self.debug = os.getenv('DEBUG', 'True').lower() == 'true'
        self.environment = os.getenv('ENVIRONMENT', 'production')
        
        # Notification Configuration
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
        self.email_username = os.getenv('EMAIL_USERNAME', '')
        self.email_password = os.getenv('EMAIL_PASSWORD', '')
    
    def _load_yaml_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load YAML configuration file."""
        if config_path is None:
            config_path = Path(__file__).parent.parent / 'config' / 'trading_config.yaml'
        
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                return config or {}
        except FileNotFoundError:
            self.logger.warning(f"Configuration file not found: {config_path}")
            return {}
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing YAML configuration: {e}")
            return {}
    
    def _initialize_config_sections(self):
        """Initialize configuration sections."""
        # Trading configuration
        trading_config = self._config.get('trading', {})
        self.trading = TradingConfig(
            risk_percentage=trading_config.get('risk_percentage', 2.0),
            max_trades_per_day=trading_config.get('max_trades_per_day', 6),
            default_timeframe=trading_config.get('default_timeframe', 'M5'),
            pairs=trading_config.get('pairs', ["EUR_USD", "GBP_USD", "USD_JPY"]),
            min_hold_time_minutes=trading_config.get('hold_time_settings', {}).get('min_hold_time_minutes', 20),
            max_hold_time_minutes=trading_config.get('hold_time_settings', {}).get('max_hold_time_minutes', 240),
            default_hold_time_minutes=trading_config.get('hold_time_settings', {}).get('default_hold_time_minutes', 90),
            force_close_enabled=trading_config.get('hold_time_settings', {}).get('force_close_enabled', True),
            force_close_time=trading_config.get('hold_time_settings', {}).get('force_close_time', '16:30'),
            market_condition_hold_times=trading_config.get('hold_time_settings', {}).get('market_condition_hold_times', {
                "news_reactionary": [20, 180],
                "reversal": [60, 240],
                "breakout": [90, 240],
                "ranging": [20, 180]
            })
        )
        
        # Multi-timeframe configuration
        mtf_config = self._config.get('multi_timeframe', {})
        self.multi_timeframe = MultiTimeframeConfig(
            enabled=mtf_config.get('enabled', True),
            timeframes=mtf_config.get('timeframes', ["M5", "M15"]),
            weights=mtf_config.get('weights', {"M5": 0.4, "M15": 0.6}),
            minimum_timeframes=mtf_config.get('minimum_timeframes', 1),
            consensus_threshold=mtf_config.get('consensus_threshold', 0.4)
        )
        
        # Market conditions configuration
        market_config = self._config.get('market_conditions', {})
        self.market_conditions = MarketConditionsConfig(
            volatility_threshold=market_config.get('volatility_threshold', 0.0008),
            trend_strength_threshold=market_config.get('trend_strength_threshold', 0.60),
            breakout_threshold=market_config.get('breakout_threshold', 0.0015),
            ranging_threshold=market_config.get('ranging_threshold', 0.0008),
            preferred_sessions=market_config.get('preferred_sessions', []),
            avoid_sessions=market_config.get('avoid_sessions', [])
        )
        
        # Risk management configuration
        risk_config = self._config.get('risk_management', {})
        self.risk_management = RiskManagementConfig(
            max_daily_loss=risk_config.get('max_daily_loss', 5.0),
            max_position_size=risk_config.get('max_position_size', 2.0),
            correlation_limit=risk_config.get('correlation_limit', 0.6),
            max_open_trades=risk_config.get('max_open_trades', 2),
            stop_loss_atr_multiplier=risk_config.get('stop_loss_atr_multiplier', 1.5),
            trailing_stop=risk_config.get('trailing_stop', True),
            trailing_stop_atr_multiplier=risk_config.get('trailing_stop_atr_multiplier', 1.0),
            consecutive_loss_limit=risk_config.get('consecutive_loss_limit', 3),
            daily_loss_cooldown_minutes=risk_config.get('daily_loss_cooldown_minutes', 60),
            scale_down_after_losses=risk_config.get('scale_down_after_losses', True),
            loss_scale_down_pct=risk_config.get('loss_scale_down_pct', 50),
            max_risk_threshold=risk_config.get('max_risk_threshold', 0.7)
        )
        
        # Technical analysis configuration
        tech_config = self._config.get('technical_analysis', {})
        self.technical_analysis = TechnicalAnalysisConfig(
            confidence_threshold=tech_config.get('confidence_threshold', 0.45),
            signal_strength_threshold=tech_config.get('signal_strength_threshold', 0.003),
            minimum_confidence=tech_config.get('minimum_confidence', 0.40),
            risk_reward_ratio_minimum=tech_config.get('risk_reward_ratio_minimum', 1.0),
            analysis_frequency=tech_config.get('analysis_frequency', 300),
            include_volume_analysis=tech_config.get('include_volume_analysis', True),
            include_market_context=tech_config.get('include_market_context', True),
            min_signals_required=tech_config.get('min_signals_required', 1),
            min_confluence_score=tech_config.get('min_confluence_score', 0.3),
            rsi_oversold=tech_config.get('rsi_oversold', 30),
            rsi_overbought=tech_config.get('rsi_overbought', 70),
            macd_signal_threshold=tech_config.get('macd_signal_threshold', 0.0001),
            bollinger_threshold=tech_config.get('bollinger_threshold', 0.05),
            atr_multiplier=tech_config.get('atr_multiplier', 2.0),
            trade_cooldown_minutes=tech_config.get('trade_cooldown_minutes', 30),
            ranging_confidence_penalty=tech_config.get('ranging_confidence_penalty', 0.05),
            signal_thresholds=tech_config.get('signal_thresholds', {
                "strong_buy": 0.8,
                "buy": 0.6,
                "neutral": 0.4,
                "sell": 0.6,
                "strong_sell": 0.8
            })
        )
        
        # Notifications configuration
        notif_config = self._config.get('notifications', {})
        self.notifications = NotificationsConfig(
            telegram_enabled=notif_config.get('telegram', {}).get('enabled', False),
            send_charts=notif_config.get('telegram', {}).get('send_charts', True),
            send_analysis=notif_config.get('telegram', {}).get('send_analysis', True),
            email_enabled=notif_config.get('email', {}).get('enabled', False),
            daily_summary=notif_config.get('email', {}).get('daily_summary', True),
            trade_alerts=notif_config.get('email', {}).get('trade_alerts', True),
            loop_reports_enabled=notif_config.get('loop_reports', {}).get('enabled', True),
            send_on_error=notif_config.get('loop_reports', {}).get('send_on_error', True),
            include_performance=notif_config.get('loop_reports', {}).get('include_performance', True),
            notification_cooldown=notif_config.get('notification_cooldown', 300),
            manual_trade_approval=notif_config.get('manual_trade_approval', True),
            pre_trade_cooldown_seconds=notif_config.get('pre_trade_cooldown_seconds', 0)
        )
        
        # Data collection configuration
        data_config = self._config.get('data_collection', {})
        self.data_collection = DataCollectionConfig(
            historical_days=data_config.get('historical_days', 30),
            update_frequency=data_config.get('update_frequency', 300),
            store_raw_data=data_config.get('store_raw_data', True),
            compression=data_config.get('compression', True),
            backup_frequency=data_config.get('backup_frequency', 24)
        )
        
        # Simulation configuration
        sim_config = self._config.get('simulation', {})
        self.simulation = SimulationConfig(
            enabled=sim_config.get('enabled', True),
            data_source=sim_config.get('data_source', 'db'),
            csv_dir=sim_config.get('csv_dir', 'data'),
            spread_pips=sim_config.get('spread_pips', 1.5),
            slippage_pips=sim_config.get('slippage_pips', 0.5)
        )
        
        # Performance configuration
        perf_config = self._config.get('performance', {})
        self.performance = PerformanceConfig(
            track_metrics=perf_config.get('track_metrics', True),
            save_trades=perf_config.get('save_trades', True),
            generate_reports=perf_config.get('generate_reports', True),
            report_frequency=perf_config.get('report_frequency', 'daily')
        )
        
        # Strategy portfolio configuration
        strategy_config = self._config.get('strategy_portfolio', {})
        self.strategy_portfolio = StrategyPortfolioConfig(
            enabled=strategy_config.get('enabled', True),
            mode=strategy_config.get('mode', 'intraday'),
            selection=strategy_config.get('selection', {
                "mode": "weighted_ensemble",
                "min_strategies_agreeing": 2,
                "confidence_weighting": True,
                "timeframe_priority": ["M5", "M15", "M1"]
            }),
            strategies=strategy_config.get('strategies', []),
            intraday_rules=strategy_config.get('intraday_rules', {
                "max_hold_minutes": 240,
                "force_close_time": "16:30",
                "avoid_news_minutes": 15,
                "min_time_between_trades": 10,
                "max_trades_per_session": 3
            }),
            rebalancing=strategy_config.get('rebalancing', {
                "enabled": False,
                "frequency_days": 30,
                "method": "performance_based",
                "min_allocation": 5,
                "max_allocation": 25
            })
        )
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.
        
        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    # Convenience properties for backward compatibility
    @property
    def trading_pairs(self) -> List[str]:
        """Get trading pairs."""
        return self.trading.pairs
    
    @property
    def timeframes(self) -> List[str]:
        """Get timeframes."""
        return self.multi_timeframe.timeframes
    
    @property
    def data_update_frequency(self) -> int:
        """Get data update frequency."""
        return self.data_collection.update_frequency
    
    @property
    def is_demo_account(self) -> bool:
        """Check if using demo account."""
        return (
            self.oanda_account_id.startswith('101-') or 
            'fxpractice' in self.oanda_url.lower()
        )
    
    @property
    def enable_db(self) -> bool:
        """Check if database is enabled."""
        return bool(self.mongodb_uri)
    
    @property
    def enable_news(self) -> bool:
        """Check if news integration is enabled."""
        return bool(self.openai_api_key)