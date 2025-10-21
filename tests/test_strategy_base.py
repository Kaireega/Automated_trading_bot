"""
Tests for BaseStrategy class.
"""
import pytest
from datetime import datetime
from decimal import Decimal
import sys
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent.parent.parent.parent
src_path = project_root / "src" / "trading_bot" / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from strategies.strategy_base import BaseStrategy, StrategySignal
from core.models import TradeSignal, MarketCondition


# Create a concrete implementation for testing
class TestStrategy(BaseStrategy):
    """Test strategy implementation."""
    
    async def generate_signal(self, candles, indicators, market_condition, current_time=None):
        return StrategySignal(
            signal=TradeSignal.BUY,
            confidence=0.75,
            strength=0.80,
            reasoning="Test signal",
            entry_price=Decimal("1.10000"),
            stop_loss=Decimal("1.09950"),
            take_profit=Decimal("1.10050")
        )


def test_strategy_initialization(strategy_config):
    """Test strategy initialization."""
    strategy = TestStrategy(
        name="Test_Strategy",
        strategy_type="test",
        config=strategy_config
    )
    
    assert strategy.name == "Test_Strategy"
    assert strategy.strategy_type == "test"
    assert strategy.allocation == 10
    assert strategy.min_confidence == 0.6


def test_strategy_is_applicable(strategy_config):
    """Test is_applicable method."""
    strategy = TestStrategy(
        name="Test_Strategy",
        strategy_type="test",
        config=strategy_config
    )
    
    # Should be applicable for configured conditions
    assert strategy.is_applicable(MarketCondition.TRENDING_UP)
    assert strategy.is_applicable(MarketCondition.TRENDING_DOWN)
    
    # Should not be applicable for non-configured conditions
    assert not strategy.is_applicable(MarketCondition.RANGING)


def test_strategy_is_active_now(strategy_config):
    """Test is_active_now method."""
    # Without active_hours, should always be active
    strategy = TestStrategy(
        name="Test_Strategy",
        strategy_type="test",
        config=strategy_config
    )
    
    assert strategy.is_active_now(datetime(2024, 1, 1, 10, 0))
    
    # With active_hours
    strategy_config['active_hours'] = ["08:00-16:00"]
    strategy = TestStrategy(
        name="Test_Strategy",
        strategy_type="test",
        config=strategy_config
    )
    
    assert strategy.is_active_now(datetime(2024, 1, 1, 10, 0))  # Within hours
    assert not strategy.is_active_now(datetime(2024, 1, 1, 20, 0))  # Outside hours


def test_strategy_signal_validation(strategy_config):
    """Test signal validation."""
    strategy = TestStrategy(
        name="Test_Strategy",
        strategy_type="test",
        config=strategy_config
    )
    
    # Valid signal
    valid_signal = StrategySignal(
        signal=TradeSignal.BUY,
        confidence=0.70,
        strength=0.75,
        reasoning="Valid test signal",
        entry_price=Decimal("1.10000"),
        stop_loss=Decimal("1.09950"),
        take_profit=Decimal("1.10050")
    )
    
    assert strategy.validate_signal(valid_signal)
    
    # Invalid signal (low confidence)
    invalid_signal = StrategySignal(
        signal=TradeSignal.BUY,
        confidence=0.50,  # Below min_confidence of 0.6
        strength=0.75,
        reasoning="Invalid test signal",
        entry_price=Decimal("1.10000")
    )
    
    assert not strategy.validate_signal(invalid_signal)


def test_strategy_risk_reward_ratio(strategy_config):
    """Test risk-reward ratio calculation."""
    strategy = TestStrategy(
        name="Test_Strategy",
        strategy_type="test",
        config=strategy_config
    )
    
    signal = StrategySignal(
        signal=TradeSignal.BUY,
        confidence=0.70,
        strength=0.75,
        reasoning="Test signal",
        entry_price=Decimal("1.10000"),
        stop_loss=Decimal("1.09950"),  # Risk: 50 pips
        take_profit=Decimal("1.10100")  # Reward: 100 pips
    )
    
    rr = strategy.get_risk_reward_ratio(signal)
    assert rr == pytest.approx(2.0, rel=0.01)  # 2:1 R:R


def test_strategy_signal_dataclass():
    """Test StrategySignal dataclass."""
    signal = StrategySignal(
        signal=TradeSignal.BUY,
        confidence=0.75,
        strength=0.80,
        reasoning="Test",
        entry_price=Decimal("1.10000"),
        stop_loss=Decimal("1.09950"),
        take_profit=Decimal("1.10050")
    )
    
    assert signal.signal == TradeSignal.BUY
    assert signal.confidence == 0.75
    assert signal.strength == 0.80
    assert signal.entry_price == Decimal("1.10000")
    assert signal.metadata == {}


def test_strategy_signal_validation_bounds():
    """Test StrategySignal validation of confidence/strength bounds."""
    # Valid bounds
    signal = StrategySignal(
        signal=TradeSignal.BUY,
        confidence=0.5,
        strength=0.5,
        reasoning="Test"
    )
    assert signal.confidence == 0.5
    
    # Invalid bounds should raise assertion
    with pytest.raises(AssertionError):
        StrategySignal(
            signal=TradeSignal.BUY,
            confidence=1.5,  # > 1.0
            strength=0.5,
            reasoning="Test"
        )
    
    with pytest.raises(AssertionError):
        StrategySignal(
            signal=TradeSignal.BUY,
            confidence=0.5,
            strength=-0.1,  # < 0.0
            reasoning="Test"
        )


@pytest.mark.asyncio
async def test_strategy_generate_signal(strategy_config, sample_candles, sample_indicators):
    """Test signal generation."""
    strategy = TestStrategy(
        name="Test_Strategy",
        strategy_type="test",
        config=strategy_config
    )
    
    signal = await strategy.generate_signal(
        candles=sample_candles,
        indicators=sample_indicators,
        market_condition=MarketCondition.TRENDING_UP
    )
    
    assert signal is not None
    assert signal.signal == TradeSignal.BUY
    assert signal.confidence == 0.75
    assert strategy.validate_signal(signal)

