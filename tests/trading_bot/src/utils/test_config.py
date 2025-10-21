"""
Unit tests for Configuration management.
"""
import pytest
import os
import tempfile
import sys
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

# Add the src directory to the path
sys.path.append(str(Path(__file__).parent.parent.parent / "src" / "trading_bot" / "src"))

from utils.config import Config, TradingConfig, RiskManagementConfig, NotificationConfig


class TestTradingConfig:
    """Test TradingConfig functionality."""
    
    @pytest.mark.unit
    def test_trading_config_defaults(self):
        """Test TradingConfig default values."""
        config = TradingConfig()
        
        assert config.risk_percentage == 2.0
        assert config.max_trades_per_day == 10
        assert config.pairs == ['EUR_USD', 'USD_JPY', 'GBP_JPY']
    
    @pytest.mark.unit
    def test_trading_config_custom_values(self):
        """Test TradingConfig with custom values."""
        config = TradingConfig(
            risk_percentage=3.0,
            max_trades_per_day=15,
            pairs=['GBP_USD', 'AUD_USD']
        )
        
        assert config.risk_percentage == 3.0
        assert config.max_trades_per_day == 15
        assert config.pairs == ['GBP_USD', 'AUD_USD']


class TestRiskManagementConfig:
    """Test RiskManagementConfig functionality."""
    
    @pytest.mark.unit
    def test_risk_management_config_defaults(self):
        """Test RiskManagementConfig default values."""
        config = RiskManagementConfig()
        
        assert config.max_daily_loss == 5.0
        assert config.max_position_size == 10.0
        assert config.correlation_limit == 0.7
        assert config.max_open_trades == 3
        assert config.stop_loss_atr_multiplier == 0.5
        assert config.trailing_stop is True
        assert config.trailing_stop_atr_multiplier == 0.3
    
    @pytest.mark.unit
    def test_risk_management_config_custom_values(self):
        """Test RiskManagementConfig with custom values."""
        config = RiskManagementConfig(
            max_daily_loss=3.0,
            max_position_size=5.0,
            correlation_limit=0.5,
            max_open_trades=2
        )
        
        assert config.max_daily_loss == 3.0
        assert config.max_position_size == 5.0
        assert config.correlation_limit == 0.5
        assert config.max_open_trades == 2


class TestNotificationConfig:
    """Test NotificationConfig functionality."""
    
    @pytest.mark.unit
    def test_notification_config_defaults(self):
        """Test NotificationConfig default values."""
        config = NotificationConfig()
        
        assert config.telegram_enabled is True
        assert config.send_charts is True
        assert config.send_analysis is True
        assert config.email_enabled is True
        assert config.daily_summary is True
        assert config.trade_alerts is True
        assert config.notification_cooldown == 300
        assert config.manual_trade_approval is True
        assert config.pre_trade_cooldown_seconds == 0
        assert config.live_trade_enabled is False
    
    @pytest.mark.unit
    def test_notification_config_custom_values(self):
        """Test NotificationConfig with custom values."""
        config = NotificationConfig(
            telegram_enabled=False,
            email_enabled=False,
            notification_cooldown=600,
            manual_trade_approval=False
        )
        
        assert config.telegram_enabled is False
        assert config.email_enabled is False
        assert config.notification_cooldown == 600
        assert config.manual_trade_approval is False


class TestConfig:
    """Test main Config class functionality."""
    
    @pytest.fixture
    def temp_env_file(self):
        """Create a temporary environment file for testing."""
        content = """
OANDA_API_KEY=test_api_key_123
OANDA_ACCOUNT_ID=test_account_456
OANDA_URL=https://api-fxpractice.oanda.com/v3
TELEGRAM_BOT_TOKEN=test_telegram_token
TELEGRAM_CHAT_ID=test_chat_id
EMAIL_USERNAME=test@example.com
EMAIL_PASSWORD=test_password
RISK_PERCENTAGE=3.0
MAX_TRADES_PER_DAY=15
DEFAULT_TIMEFRAME=M15
TECHNICAL_CONFIDENCE_THRESHOLD=0.7
LOG_LEVEL=DEBUG
DEBUG=True
ENVIRONMENT=test
LIVE_TRADE_ENABLED=False
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write(content)
            return f.name
    
    @pytest.mark.unit
    def test_config_initialization_defaults(self):
        """Test Config initialization with defaults."""
        with patch('utils.config.load_dotenv'), \
             patch('utils.config.Path.exists', return_value=False), \
             patch.dict(os.environ, {
                 'OANDA_API_KEY': 'test_api_key',
                 'OANDA_ACCOUNT_ID': 'test_account_id',
                 'TELEGRAM_BOT_TOKEN': 'test_telegram_token'
             }):
            
            config = Config()
            
            assert config.trading.risk_percentage == 2.0
            assert config.trading.max_trades_per_day == 10
            assert config.risk_management.max_daily_loss == 5.0
            assert config.notifications.telegram_enabled is True
    
    @pytest.mark.unit
    def test_config_initialization_with_env_file(self, temp_env_file):
        """Test Config initialization with environment file."""
        with patch('utils.config.load_dotenv') as mock_load_dotenv, \
             patch('utils.config.Path.exists', return_value=True) as mock_exists, \
             patch('utils.config.Path') as mock_path:
            
            # Mock the path to return our temp file
            mock_path.return_value = Path(temp_env_file)
            mock_path.return_value.exists.return_value = True
            
            # Mock environment variables
            with patch.dict(os.environ, {
                'OANDA_API_KEY': 'test_api_key_123',
                'OANDA_ACCOUNT_ID': 'test_account_456',
                'RISK_PERCENTAGE': '3.0',
                'MAX_TRADES_PER_DAY': '15',
                'DEFAULT_TIMEFRAME': 'M15',
                'TECHNICAL_CONFIDENCE_THRESHOLD': '0.7',
                'LOG_LEVEL': 'DEBUG',
                'DEBUG': 'True',
                'ENVIRONMENT': 'test',
                'LIVE_TRADE_ENABLED': 'False'
            }):
                config = Config()
                
                assert config.oanda_api_key == 'test_api_key_123'
                assert config.oanda_account_id == 'test_account_456'
                assert config.trading.risk_percentage == 3.0
                assert config.trading.max_trades_per_day == 15
                assert config.technical_analysis.confidence_threshold == 0.7
                assert config.log_level == 'DEBUG'
                assert config.debug is True
                assert config.environment == 'test'
                assert config.notifications.live_trade_enabled is False
    
    @pytest.mark.unit
    def test_config_validation_success(self):
        """Test successful configuration validation."""
        with patch('utils.config.load_dotenv'), \
             patch('utils.config.Path.exists', return_value=False), \
             patch.dict(os.environ, {
                 'OANDA_API_KEY': 'valid_key',
                 'OANDA_ACCOUNT_ID': 'valid_account'
             }):
            
            config = Config()
            
            # Should not raise any validation errors
            assert config.oanda_api_key == 'valid_key'
            assert config.oanda_account_id == 'valid_account'
    
    @pytest.mark.unit
    def test_config_validation_missing_api_key(self):
        """Test configuration validation with missing API key."""
        with patch('utils.config.load_dotenv'), \
             patch('utils.config.Path.exists', return_value=False), \
             patch.dict(os.environ, {
                 'OANDA_ACCOUNT_ID': 'valid_account'
                 # Missing OANDA_API_KEY
             }, clear=True):
            
            with pytest.raises(ValueError, match="OANDA_API_KEY is required"):
                Config()
    
    @pytest.mark.unit
    def test_config_validation_missing_account_id(self):
        """Test configuration validation with missing account ID."""
        with patch('utils.config.load_dotenv'), \
             patch('utils.config.Path.exists', return_value=False), \
             patch.dict(os.environ, {
                 'OANDA_API_KEY': 'valid_key'
                 # Missing OANDA_ACCOUNT_ID
             }, clear=True):
            
            with pytest.raises(ValueError, match="OANDA_ACCOUNT_ID is required"):
                Config()
    
    @pytest.mark.unit
    def test_config_validation_invalid_risk_percentage(self):
        """Test configuration validation with invalid risk percentage."""
        with patch('utils.config.load_dotenv'), \
             patch('utils.config.Path.exists', return_value=False), \
             patch.dict(os.environ, {
                 'OANDA_API_KEY': 'valid_key',
                 'OANDA_ACCOUNT_ID': 'valid_account',
                 'RISK_PERCENTAGE': '150.0'  # Invalid: > 100
             }):
            
            with pytest.raises(ValueError, match="RISK_PERCENTAGE must be between 0 and 100"):
                Config()
    
    @pytest.mark.unit
    def test_config_validation_invalid_confidence_threshold(self):
        """Test configuration validation with invalid confidence threshold."""
        with patch('utils.config.load_dotenv'), \
             patch('utils.config.Path.exists', return_value=False), \
             patch.dict(os.environ, {
                 'OANDA_API_KEY': 'valid_key',
                 'OANDA_ACCOUNT_ID': 'valid_account',
                 'TECHNICAL_CONFIDENCE_THRESHOLD': '1.5'  # Invalid: > 1
             }):
            
            with pytest.raises(ValueError, match="TECHNICAL_CONFIDENCE_THRESHOLD must be between 0 and 1"):
                Config()
    
    @pytest.mark.unit
    def test_config_properties(self):
        """Test Config property methods."""
        with patch('utils.config.load_dotenv'), \
             patch('utils.config.Path.exists', return_value=False), \
             patch.dict(os.environ, {
                 'OANDA_API_KEY': 'valid_key',
                 'OANDA_ACCOUNT_ID': 'valid_account'
             }):
            
            config = Config()
            
            assert config.trading_pairs == ['EUR_USD', 'USD_JPY', 'GBP_JPY']
            assert config.technical_confidence_threshold == 0.6
            assert config.data_update_frequency == 60
            assert config.max_trades_per_day == 10
            assert config.notification_cooldown == 300
    
    @pytest.mark.unit
    def test_config_to_dict(self):
        """Test Config to_dict method."""
        with patch('utils.config.load_dotenv'), \
             patch('utils.config.Path.exists', return_value=False), \
             patch.dict(os.environ, {
                 'OANDA_API_KEY': 'valid_key',
                 'OANDA_ACCOUNT_ID': 'valid_account',
                 'TELEGRAM_BOT_TOKEN': 'test_telegram_token'
             }):
            
            config = Config()
            config_dict = config.to_dict()
            
            assert 'trading' in config_dict
            assert 'risk_management' in config_dict
            assert 'notifications' in config_dict
            assert 'technical_analysis' in config_dict
            
            assert config_dict['trading']['risk_percentage'] == 2.0
            assert config_dict['trading']['max_trades_per_day'] == 10
            assert config_dict['risk_management']['max_daily_loss'] == 5.0
            assert config_dict['notifications']['telegram_enabled'] is True
    
    @pytest.mark.unit
    def test_config_yaml_loading(self):
        """Test Config YAML loading."""
        yaml_content = """
trading:
  risk_percentage: 3.0
  max_trades_per_day: 15
  pairs: ['GBP_USD', 'AUD_USD']

risk_management:
  max_daily_loss: 3.0
  max_position_size: 5.0
  correlation_limit: 0.5

notifications:
  telegram_enabled: false
  email_enabled: false
  notification_cooldown: 600
"""
        
        with patch('utils.config.load_dotenv'), \
             patch('utils.config.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=yaml_content)), \
             patch('utils.config.yaml.safe_load', return_value={
                 'trading': {
                     'risk_percentage': 3.0,
                     'max_trades_per_day': 15,
                     'pairs': ['GBP_USD', 'AUD_USD']
                 },
                 'risk_management': {
                     'max_daily_loss': 3.0,
                     'max_position_size': 5.0,
                     'correlation_limit': 0.5
                 },
                 'notifications': {
                     'telegram_enabled': False,
                     'email_enabled': False,
                     'notification_cooldown': 600
                 }
             }), \
             patch.dict(os.environ, {
                 'OANDA_API_KEY': 'valid_key',
                 'OANDA_ACCOUNT_ID': 'valid_account'
             }):
            
            config = Config()
            
            assert config.trading.risk_percentage == 3.0
            assert config.trading.max_trades_per_day == 15
            assert config.trading.pairs == ['GBP_USD', 'AUD_USD']
            assert config.risk_management.max_daily_loss == 3.0
            assert config.risk_management.max_position_size == 5.0
            assert config.risk_management.correlation_limit == 0.5
            assert config.notifications.telegram_enabled is False
            assert config.notifications.email_enabled is False
            assert config.notifications.notification_cooldown == 600
    
    def teardown_method(self):
        """Clean up temporary files."""
        # Clean up any temporary files created during tests
        pass

