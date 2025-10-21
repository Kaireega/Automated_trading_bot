"""
Simulation Broker - Simulates real trading conditions with slippage, fees, and execution delays.
"""
import asyncio
import random
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from decimal import Decimal
import uuid

try:
    from ..core.models import TradeSignal
    from ..utils.config import Config
    from ..utils.logger import get_logger
except ImportError:
    # Fallback for when running as standalone module
    from core.models import TradeSignal
    from utils.config import Config
    from utils.logger import get_logger


class SimulationBroker:
    """Simulates a real broker with realistic trading conditions."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger(__name__)
        
        # Broker settings
        self.spread_pips = config.backtesting.spread_pips
        self.slippage_pips = config.backtesting.slippage_pips
        self.commission_rate = config.backtesting.commission_rate
        self.execution_delay_ms = config.backtesting.execution_delay_ms
        
        # Trade tracking
        self.trades = {}
        self.trade_counter = 0
        
        # Market conditions simulation
        self.volatility_multiplier = 1.0
        self.liquidity_conditions = 'normal'  # normal, low, high
        
    async def execute_trade(
        self,
        pair: str,
        signal: TradeSignal,
        size: float,
        entry_price: Decimal,
        stop_loss: Decimal,
        take_profit: Decimal,
        timestamp: datetime
    ) -> str:
        """Execute a trade with realistic conditions."""
        
        try:
            # Simulate execution delay
            if self.execution_delay_ms > 0:
                await asyncio.sleep(self.execution_delay_ms / 1000)
            
            # Generate trade ID
            trade_id = str(uuid.uuid4())
            
            # Apply slippage
            execution_price = self._apply_slippage(entry_price, signal, size)
            
            # Calculate spread cost
            spread_cost = self._calculate_spread_cost(execution_price, size)
            
            # Calculate commission
            commission = self._calculate_commission(size, execution_price)
            
            # Record trade
            self.trades[trade_id] = {
                'pair': pair,
                'signal': signal,
                'size': size,
                'requested_price': entry_price,
                'execution_price': execution_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'spread_cost': spread_cost,
                'commission': commission,
                'timestamp': timestamp,
                'status': 'open'
            }
            
            self.trade_counter += 1
            
            self.logger.debug(f"Executed trade {trade_id}: {pair} {signal.value} "
                            f"Size: {size:.2f}, Price: {execution_price} "
                            f"(Slippage: {execution_price - entry_price:.6f})")
            
            return trade_id
            
        except Exception as e:
            self.logger.error(f"Error executing trade: {e}")
            raise
    
    def _apply_slippage(self, price: Decimal, signal: TradeSignal, size: float) -> Decimal:
        """Apply slippage based on order size and market conditions."""
        
        # Base slippage in pips
        base_slippage = self.slippage_pips / 10000  # Convert pips to decimal
        
        # Size-based slippage (larger orders = more slippage)
        size_multiplier = min(size / 10000, 2.0)  # Cap at 2x for very large orders
        
        # Volatility-based slippage
        volatility_multiplier = self.volatility_multiplier
        
        # Liquidity-based slippage
        liquidity_multiplier = {
            'normal': 1.0,
            'low': 1.5,
            'high': 0.7
        }.get(self.liquidity_conditions, 1.0)
        
        # Calculate total slippage
        total_slippage = base_slippage * size_multiplier * volatility_multiplier * liquidity_multiplier
        
        # Convert slippage to Decimal for arithmetic with price
        slippage_decimal = Decimal(str(total_slippage))
        
        # Apply slippage (worse for buy orders, better for sell orders)
        if signal == TradeSignal.BUY:
            execution_price = price + slippage_decimal
        else:
            execution_price = price - slippage_decimal
        
        return execution_price
    
    def _calculate_spread_cost(self, price: Decimal, size: float) -> float:
        """Calculate spread cost."""
        spread_pips = self.spread_pips / 10000
        spread_cost = float(spread_pips * size)
        return spread_cost
    
    def _calculate_commission(self, size: float, price: Decimal) -> float:
        """Calculate commission cost."""
        notional_value = size * float(price)
        commission = notional_value * self.commission_rate
        return commission
    
    def calculate_fees(self, size: float, price: Decimal) -> float:
        """Calculate total fees for a trade."""
        spread_cost = self._calculate_spread_cost(price, size)
        commission = self._calculate_commission(size, price)
        return spread_cost + commission
    
    async def close_trade(self, trade_id: str, exit_price: Decimal, timestamp: datetime) -> Dict[str, Any]:
        """Close a trade and return P&L details."""
        
        if trade_id not in self.trades:
            raise ValueError(f"Trade {trade_id} not found")
        
        trade = self.trades[trade_id]
        
        # Apply slippage to exit
        exit_signal = TradeSignal.SELL if trade['signal'] == TradeSignal.BUY else TradeSignal.BUY
        execution_exit_price = self._apply_slippage(exit_price, exit_signal, trade['size'])
        
        # Calculate P&L
        if trade['signal'] == TradeSignal.BUY:
            pnl = (execution_exit_price - trade['execution_price']) * trade['size']
        else:
            pnl = (trade['execution_price'] - execution_exit_price) * trade['size']
        
        # Subtract fees
        entry_fees = trade['spread_cost'] + trade['commission']
        exit_fees = self.calculate_fees(trade['size'], execution_exit_price)
        total_fees = entry_fees + exit_fees
        
        # Convert to float for consistent arithmetic
        net_pnl = float(pnl) - total_fees
        
        # Update trade record
        trade['exit_price'] = execution_exit_price
        trade['exit_timestamp'] = timestamp
        trade['pnl'] = net_pnl
        trade['total_fees'] = total_fees
        trade['status'] = 'closed'
        
        return {
            'trade_id': trade_id,
            'pair': trade['pair'],
            'signal': trade['signal'],
            'entry_price': trade['execution_price'],
            'exit_price': execution_exit_price,
            'size': trade['size'],
            'pnl': net_pnl,
            'fees': total_fees,
            'duration': (timestamp - trade['timestamp']).total_seconds() / 60
        }
    
    def set_market_conditions(self, volatility: float = 1.0, liquidity: str = 'normal'):
        """Set market conditions for more realistic simulation."""
        self.volatility_multiplier = volatility
        self.liquidity_conditions = liquidity
        
        self.logger.info(f"Market conditions updated: Volatility={volatility}, Liquidity={liquidity}")
    
    def get_trade_statistics(self) -> Dict[str, Any]:
        """Get statistics about executed trades."""
        
        if not self.trades:
            return {
                'total_trades': 0,
                'open_trades': 0,
                'closed_trades': 0,
                'total_fees': 0.0,
                'avg_slippage': 0.0
            }
        
        total_trades = len(self.trades)
        open_trades = len([t for t in self.trades.values() if t['status'] == 'open'])
        closed_trades = len([t for t in self.trades.values() if t['status'] == 'closed'])
        
        total_fees = sum(t.get('total_fees', 0) for t in self.trades.values())
        
        # Calculate average slippage
        slippages = []
        for trade in self.trades.values():
            if 'execution_price' in trade and 'requested_price' in trade:
                slippage = abs(trade['execution_price'] - trade['requested_price'])
                slippages.append(float(slippage))
        
        avg_slippage = sum(slippages) / len(slippages) if slippages else 0.0
        
        return {
            'total_trades': total_trades,
            'open_trades': open_trades,
            'closed_trades': closed_trades,
            'total_fees': total_fees,
            'avg_slippage': avg_slippage
        }
    
    def reset(self):
        """Reset broker state for new backtest."""
        self.trades = {}
        self.trade_counter = 0
        self.volatility_multiplier = 1.0
        self.liquidity_conditions = 'normal'
        
        self.logger.info("Broker state reset")
