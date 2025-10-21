"""
Comprehensive Unit Tests for BrokerSim

This module provides comprehensive unit tests for the BrokerSim class,
ensuring 100% test coverage and following TDD principles.

Author: Trading Bot Development Team
Version: 1.0.0
"""

import pytest
import sys
import os
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock, patch

# Add project paths for imports
project_root = Path(__file__).parent.parent.parent.parent.parent.parent
src_path = project_root / "src"
sys.path.append(str(src_path))
sys.path.append(str(src_path / "trading_bot" / "src"))

# Import the modules under test
from trading_bot.src.backtesting.broker import BrokerSim, SimOrder


class TestSimOrder:
    """Test suite for SimOrder dataclass"""
    
    def test_sim_order_creation(self):
        """Test SimOrder creation with all parameters"""
        order = SimOrder(
            oid="TEST-001",
            pair="EUR_USD",
            direction=1,  # Buy
            size=Decimal('0.1'),
            entry=Decimal('1.1000'),
            stop=Decimal('1.0950'),
            take=Decimal('1.1050'),
            time=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        )
        
        assert order.oid == "TEST-001"
        assert order.pair == "EUR_USD"
        assert order.direction == 1
        assert order.size == Decimal('0.1')
        assert order.entry == Decimal('1.1000')
        assert order.stop == Decimal('1.0950')
        assert order.take == Decimal('1.1050')
        assert order.time == datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    def test_sim_order_creation_without_stop_take(self):
        """Test SimOrder creation without stop loss and take profit"""
        order = SimOrder(
            oid="TEST-002",
            pair="GBP_USD",
            direction=-1,  # Sell
            size=Decimal('0.05'),
            entry=Decimal('1.2500'),
            stop=None,
            take=None,
            time=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        )
        
        assert order.oid == "TEST-002"
        assert order.pair == "GBP_USD"
        assert order.direction == -1
        assert order.size == Decimal('0.05')
        assert order.entry == Decimal('1.2500')
        assert order.stop is None
        assert order.take is None


class TestBrokerSim:
    """Test suite for BrokerSim class"""
    
    def test_initialization_default_parameters(self):
        """Test BrokerSim initialization with default parameters"""
        broker = BrokerSim()
        
        assert broker.spread_pips == Decimal('0.1')
        assert broker.slippage_pips == Decimal('0.1')
        assert broker.pip_location == Decimal('0.0001')
        assert broker.positions == []
    
    def test_initialization_custom_parameters(self):
        """Test BrokerSim initialization with custom parameters"""
        broker = BrokerSim(
            spread_pips=0.5,
            slippage_pips=0.3,
            pip_location=0.00001
        )
        
        assert broker.spread_pips == Decimal('0.5')
        assert broker.slippage_pips == Decimal('0.3')
        assert broker.pip_location == Decimal('0.00001')
        assert broker.positions == []
    
    def test_pip_value(self):
        """Test pip value calculation"""
        broker = BrokerSim(pip_location=0.0001)
        assert broker._pip_value() == Decimal('0.0001')
        
        broker = BrokerSim(pip_location=0.00001)
        assert broker._pip_value() == Decimal('0.00001')
    
    def test_open_market_buy_order(self):
        """Test opening a buy market order"""
        broker = BrokerSim(spread_pips=0.1, slippage_pips=0.1)
        
        order_id = broker.open_market(
            pair="EUR_USD",
            direction=1,  # Buy
            size=Decimal('0.1'),
            price=Decimal('1.1000'),
            stop=Decimal('1.0950'),
            take=Decimal('1.1050')
        )
        
        # Verify order was created
        assert order_id == "SIM-1"
        assert len(broker.positions) == 1
        
        order = broker.positions[0]
        assert order.oid == "SIM-1"
        assert order.pair == "EUR_USD"
        assert order.direction == 1
        assert order.size == Decimal('0.1')
        assert order.stop == Decimal('1.0950')
        assert order.take == Decimal('1.1050')
        
        # Verify fill price includes spread and slippage
        expected_fill = Decimal('1.1000') + Decimal('0.0001') + Decimal('0.0001')  # price + slippage + spread
        assert order.entry == expected_fill
    
    def test_open_market_sell_order(self):
        """Test opening a sell market order"""
        broker = BrokerSim(spread_pips=0.1, slippage_pips=0.1)
        
        order_id = broker.open_market(
            pair="EUR_USD",
            direction=-1,  # Sell
            size=Decimal('0.1'),
            price=Decimal('1.1000'),
            stop=Decimal('1.1050'),
            take=Decimal('1.0950')
        )
        
        # Verify order was created
        assert order_id == "SIM-1"
        assert len(broker.positions) == 1
        
        order = broker.positions[0]
        assert order.direction == -1
        
        # Verify fill price includes spread and slippage (subtracted for sell)
        expected_fill = Decimal('1.1000') - Decimal('0.0001') - Decimal('0.0001')  # price - slippage - spread
        assert order.entry == expected_fill
    
    def test_open_market_multiple_orders(self):
        """Test opening multiple market orders"""
        broker = BrokerSim()
        
        # Open first order
        order_id_1 = broker.open_market(
            pair="EUR_USD",
            direction=1,
            size=Decimal('0.1'),
            price=Decimal('1.1000'),
            stop=None,
            take=None
        )
        
        # Open second order
        order_id_2 = broker.open_market(
            pair="GBP_USD",
            direction=-1,
            size=Decimal('0.05'),
            price=Decimal('1.2500'),
            stop=None,
            take=None
        )
        
        # Verify both orders were created
        assert order_id_1 == "SIM-1"
        assert order_id_2 == "SIM-2"
        assert len(broker.positions) == 2
        
        assert broker.positions[0].oid == "SIM-1"
        assert broker.positions[0].pair == "EUR_USD"
        assert broker.positions[1].oid == "SIM-2"
        assert broker.positions[1].pair == "GBP_USD"
    
    def test_step_no_positions(self):
        """Test step method with no open positions"""
        broker = BrokerSim()
        
        closed_trades = broker.step(
            pair="EUR_USD",
            candle_open=Decimal('1.1000'),
            candle_high=Decimal('1.1010'),
            candle_low=Decimal('1.0990'),
            candle_close=Decimal('1.1005')
        )
        
        assert closed_trades == []
        assert len(broker.positions) == 0
    
    def test_step_buy_order_stop_loss_hit(self):
        """Test step method with buy order hitting stop loss"""
        broker = BrokerSim()
        
        # Open buy order with stop loss
        broker.open_market(
            pair="EUR_USD",
            direction=1,
            size=Decimal('0.1'),
            price=Decimal('1.1000'),
            stop=Decimal('1.0950'),  # Stop loss
            take=Decimal('1.1050')
        )
        
        # Step with candle that hits stop loss
        closed_trades = broker.step(
            pair="EUR_USD",
            candle_open=Decimal('1.1000'),
            candle_high=Decimal('1.1005'),
            candle_low=Decimal('1.0940'),  # Hits stop loss
            candle_close=Decimal('1.0945')
        )
        
        # Verify trade was closed
        assert len(closed_trades) == 1
        assert len(broker.positions) == 0
        
        trade = closed_trades[0]
        assert trade['pair'] == 'EUR_USD'
        assert trade['direction'] == 1
        assert trade['size'] == Decimal('0.1')
        assert trade['entry'] > Decimal('1.1000')  # Includes spread/slippage
        assert trade['exit'] == Decimal('1.0950')  # Stop loss price
        assert trade['pnl'] < 0  # Loss
    
    def test_step_buy_order_take_profit_hit(self):
        """Test step method with buy order hitting take profit"""
        broker = BrokerSim()
        
        # Open buy order with take profit
        broker.open_market(
            pair="EUR_USD",
            direction=1,
            size=Decimal('0.1'),
            price=Decimal('1.1000'),
            stop=Decimal('1.0950'),
            take=Decimal('1.1050')  # Take profit
        )
        
        # Step with candle that hits take profit
        closed_trades = broker.step(
            pair="EUR_USD",
            candle_open=Decimal('1.1000'),
            candle_high=Decimal('1.1060'),  # Hits take profit
            candle_low=Decimal('1.0990'),
            candle_close=Decimal('1.1055')
        )
        
        # Verify trade was closed
        assert len(closed_trades) == 1
        assert len(broker.positions) == 0
        
        trade = closed_trades[0]
        assert trade['pair'] == 'EUR_USD'
        assert trade['direction'] == 1
        assert trade['size'] == Decimal('0.1')
        assert trade['entry'] > Decimal('1.1000')  # Includes spread/slippage
        assert trade['exit'] == Decimal('1.1050')  # Take profit price
        assert trade['pnl'] > 0  # Profit
    
    def test_step_sell_order_stop_loss_hit(self):
        """Test step method with sell order hitting stop loss"""
        broker = BrokerSim()
        
        # Open sell order with stop loss
        broker.open_market(
            pair="EUR_USD",
            direction=-1,
            size=Decimal('0.1'),
            price=Decimal('1.1000'),
            stop=Decimal('1.1050'),  # Stop loss (higher for sell)
            take=Decimal('1.0950')
        )
        
        # Step with candle that hits stop loss
        closed_trades = broker.step(
            pair="EUR_USD",
            candle_open=Decimal('1.1000'),
            candle_high=Decimal('1.1060'),  # Hits stop loss
            candle_low=Decimal('1.0990'),
            candle_close=Decimal('1.1055')
        )
        
        # Verify trade was closed
        assert len(closed_trades) == 1
        assert len(broker.positions) == 0
        
        trade = closed_trades[0]
        assert trade['pair'] == 'EUR_USD'
        assert trade['direction'] == -1
        assert trade['size'] == Decimal('0.1')
        assert trade['entry'] < Decimal('1.1000')  # Includes spread/slippage
        assert trade['exit'] == Decimal('1.1050')  # Stop loss price
        assert trade['pnl'] < 0  # Loss
    
    def test_step_sell_order_take_profit_hit(self):
        """Test step method with sell order hitting take profit"""
        broker = BrokerSim()
        
        # Open sell order with take profit
        broker.open_market(
            pair="EUR_USD",
            direction=-1,
            size=Decimal('0.1'),
            price=Decimal('1.1000'),
            stop=Decimal('1.1050'),
            take=Decimal('1.0950')  # Take profit (lower for sell)
        )
        
        # Step with candle that hits take profit
        closed_trades = broker.step(
            pair="EUR_USD",
            candle_open=Decimal('1.1000'),
            candle_high=Decimal('1.1005'),
            candle_low=Decimal('1.0940'),  # Hits take profit
            candle_close=Decimal('1.0945')
        )
        
        # Verify trade was closed
        assert len(closed_trades) == 1
        assert len(broker.positions) == 0
        
        trade = closed_trades[0]
        assert trade['pair'] == 'EUR_USD'
        assert trade['direction'] == -1
        assert trade['size'] == Decimal('0.1')
        assert trade['entry'] < Decimal('1.1000')  # Includes spread/slippage
        assert trade['exit'] == Decimal('1.0950')  # Take profit price
        assert trade['pnl'] > 0  # Profit
    
    def test_step_no_stop_take_orders_remain_open(self):
        """Test step method with orders that have no stop/take remain open"""
        broker = BrokerSim()
        
        # Open order without stop/take
        broker.open_market(
            pair="EUR_USD",
            direction=1,
            size=Decimal('0.1'),
            price=Decimal('1.1000'),
            stop=None,
            take=None
        )
        
        # Step with any candle
        closed_trades = broker.step(
            pair="EUR_USD",
            candle_open=Decimal('1.1000'),
            candle_high=Decimal('1.1010'),
            candle_low=Decimal('1.0990'),
            candle_close=Decimal('1.1005')
        )
        
        # Verify no trades were closed
        assert len(closed_trades) == 0
        assert len(broker.positions) == 1
    
    def test_step_multiple_orders_different_pairs(self):
        """Test step method with multiple orders on different pairs"""
        broker = BrokerSim()
        
        # Open orders on different pairs
        broker.open_market(
            pair="EUR_USD",
            direction=1,
            size=Decimal('0.1'),
            price=Decimal('1.1000'),
            stop=Decimal('1.0950'),
            take=Decimal('1.1050')
        )
        
        broker.open_market(
            pair="GBP_USD",
            direction=-1,
            size=Decimal('0.05'),
            price=Decimal('1.2500'),
            stop=Decimal('1.2550'),
            take=Decimal('1.2450')
        )
        
        # Step EUR_USD (should close first order)
        closed_trades = broker.step(
            pair="EUR_USD",
            candle_open=Decimal('1.1000'),
            candle_high=Decimal('1.1005'),
            candle_low=Decimal('1.0940'),  # Hits stop loss
            candle_close=Decimal('1.0945')
        )
        
        # Verify only EUR_USD order was closed
        assert len(closed_trades) == 1
        assert len(broker.positions) == 1
        assert closed_trades[0]['pair'] == 'EUR_USD'
        assert broker.positions[0].pair == 'GBP_USD'
    
    def test_step_candle_does_not_hit_levels(self):
        """Test step method when candle doesn't hit stop/take levels"""
        broker = BrokerSim()
        
        # Open order with stop/take
        broker.open_market(
            pair="EUR_USD",
            direction=1,
            size=Decimal('0.1'),
            price=Decimal('1.1000'),
            stop=Decimal('1.0950'),
            take=Decimal('1.1050')
        )
        
        # Step with candle that doesn't hit levels
        closed_trades = broker.step(
            pair="EUR_USD",
            candle_open=Decimal('1.1000'),
            candle_high=Decimal('1.1005'),  # Below take profit
            candle_low=Decimal('1.0995'),   # Above stop loss
            candle_close=Decimal('1.1002')
        )
        
        # Verify no trades were closed
        assert len(closed_trades) == 0
        assert len(broker.positions) == 1
    
    def test_pnl_calculation_buy_order(self):
        """Test PnL calculation for buy orders"""
        broker = BrokerSim()
        
        # Open buy order
        broker.open_market(
            pair="EUR_USD",
            direction=1,
            size=Decimal('0.1'),
            price=Decimal('1.1000'),
            stop=Decimal('1.0950'),
            take=Decimal('1.1050')
        )
        
        # Get the order to check entry price
        order = broker.positions[0]
        entry_price = order.entry
        
        # Step with take profit hit
        closed_trades = broker.step(
            pair="EUR_USD",
            candle_open=Decimal('1.1000'),
            candle_high=Decimal('1.1060'),
            candle_low=Decimal('1.0990'),
            candle_close=Decimal('1.1055')
        )
        
        # Verify PnL calculation
        trade = closed_trades[0]
        expected_pnl = (Decimal('1.1050') - entry_price) * Decimal('0.1')
        assert trade['pnl'] == expected_pnl
        assert trade['pnl'] > 0  # Should be profit
    
    def test_pnl_calculation_sell_order(self):
        """Test PnL calculation for sell orders"""
        broker = BrokerSim()
        
        # Open sell order
        broker.open_market(
            pair="EUR_USD",
            direction=-1,
            size=Decimal('0.1'),
            price=Decimal('1.1000'),
            stop=Decimal('1.1050'),
            take=Decimal('1.0950')
        )
        
        # Get the order to check entry price
        order = broker.positions[0]
        entry_price = order.entry
        
        # Step with take profit hit
        closed_trades = broker.step(
            pair="EUR_USD",
            candle_open=Decimal('1.1000'),
            candle_high=Decimal('1.1005'),
            candle_low=Decimal('1.0940'),
            candle_close=Decimal('1.0945')
        )
        
        # Verify PnL calculation
        trade = closed_trades[0]
        expected_pnl = (entry_price - Decimal('1.0950')) * Decimal('0.1')
        assert trade['pnl'] == expected_pnl
        assert trade['pnl'] > 0  # Should be profit


class TestBrokerSimEdgeCases:
    """Test edge cases and error conditions for BrokerSim"""
    
    def test_initialization_with_zero_parameters(self):
        """Test initialization with zero spread and slippage"""
        broker = BrokerSim(spread_pips=0.0, slippage_pips=0.0)
        
        assert broker.spread_pips == Decimal('0.0')
        assert broker.slippage_pips == Decimal('0.0')
        
        # Test that orders still work
        order_id = broker.open_market(
            pair="EUR_USD",
            direction=1,
            size=Decimal('0.1'),
            price=Decimal('1.1000'),
            stop=None,
            take=None
        )
        
        assert order_id == "SIM-1"
        assert len(broker.positions) == 1
        assert broker.positions[0].entry == Decimal('1.1000')  # No spread/slippage
    
    def test_initialization_with_negative_parameters(self):
        """Test initialization with negative spread and slippage"""
        broker = BrokerSim(spread_pips=-0.1, slippage_pips=-0.1)
        
        assert broker.spread_pips == Decimal('-0.1')
        assert broker.slippage_pips == Decimal('-0.1')
        
        # Test that orders still work (negative spread/slippage)
        order_id = broker.open_market(
            pair="EUR_USD",
            direction=1,
            size=Decimal('0.1'),
            price=Decimal('1.1000'),
            stop=None,
            take=None
        )
        
        assert order_id == "SIM-1"
        # Entry price should be better than market price due to negative spread/slippage
        assert broker.positions[0].entry < Decimal('1.1000')
    
    def test_open_market_with_zero_size(self):
        """Test opening order with zero size"""
        broker = BrokerSim()
        
        order_id = broker.open_market(
            pair="EUR_USD",
            direction=1,
            size=Decimal('0.0'),
            price=Decimal('1.1000'),
            stop=None,
            take=None
        )
        
        assert order_id == "SIM-1"
        assert len(broker.positions) == 1
        assert broker.positions[0].size == Decimal('0.0')
    
    def test_open_market_with_negative_size(self):
        """Test opening order with negative size"""
        broker = BrokerSim()
        
        order_id = broker.open_market(
            pair="EUR_USD",
            direction=1,
            size=Decimal('-0.1'),
            price=Decimal('1.1000'),
            stop=None,
            take=None
        )
        
        assert order_id == "SIM-1"
        assert len(broker.positions) == 1
        assert broker.positions[0].size == Decimal('-0.1')
    
    def test_step_with_zero_candle_values(self):
        """Test step method with zero candle values"""
        broker = BrokerSim()
        
        # Open order
        broker.open_market(
            pair="EUR_USD",
            direction=1,
            size=Decimal('0.1'),
            price=Decimal('1.1000'),
            stop=Decimal('1.0950'),
            take=Decimal('1.1050')
        )
        
        # Step with zero values
        closed_trades = broker.step(
            pair="EUR_USD",
            candle_open=Decimal('0.0'),
            candle_high=Decimal('0.0'),
            candle_low=Decimal('0.0'),
            candle_close=Decimal('0.0')
        )
        
        # Should not close any trades (zero values won't hit levels)
        assert len(closed_trades) == 0
        assert len(broker.positions) == 1
    
    def test_step_with_identical_stop_take_levels(self):
        """Test step method with identical stop loss and take profit levels"""
        broker = BrokerSim()
        
        # Open order with identical stop/take
        broker.open_market(
            pair="EUR_USD",
            direction=1,
            size=Decimal('0.1'),
            price=Decimal('1.1000'),
            stop=Decimal('1.1000'),  # Same as take
            take=Decimal('1.1000')   # Same as stop
        )
        
        # Step with candle that hits the level
        closed_trades = broker.step(
            pair="EUR_USD",
            candle_open=Decimal('1.1000'),
            candle_high=Decimal('1.1005'),
            candle_low=Decimal('0.9995'),
            candle_close=Decimal('1.1000')
        )
        
        # Should close the trade
        assert len(closed_trades) == 1
        assert len(broker.positions) == 0
        assert closed_trades[0]['exit'] == Decimal('1.1000')
        assert closed_trades[0]['pnl'] == Decimal('0.0')  # No profit/loss
    
    def test_large_number_of_orders(self):
        """Test handling large number of orders"""
        broker = BrokerSim()
        
        # Open many orders
        for i in range(100):
            broker.open_market(
                pair="EUR_USD",
                direction=1,
                size=Decimal('0.01'),
                price=Decimal('1.1000'),
                stop=None,
                take=None
            )
        
        assert len(broker.positions) == 100
        
        # Verify order IDs are sequential
        for i, order in enumerate(broker.positions):
            assert order.oid == f"SIM-{i+1}"
    
    def test_step_with_extreme_price_movements(self):
        """Test step method with extreme price movements"""
        broker = BrokerSim()
        
        # Open order
        broker.open_market(
            pair="EUR_USD",
            direction=1,
            size=Decimal('0.1'),
            price=Decimal('1.1000'),
            stop=Decimal('1.0950'),
            take=Decimal('1.1050')
        )
        
        # Step with extreme movement (should hit both stop and take)
        closed_trades = broker.step(
            pair="EUR_USD",
            candle_open=Decimal('1.1000'),
            candle_high=Decimal('1.2000'),  # Way above take profit
            candle_low=Decimal('0.9000'),   # Way below stop loss
            candle_close=Decimal('1.1500')
        )
        
        # Should close the trade (stop loss hit first)
        assert len(closed_trades) == 1
        assert len(broker.positions) == 0
        assert closed_trades[0]['exit'] == Decimal('1.0950')  # Stop loss


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

