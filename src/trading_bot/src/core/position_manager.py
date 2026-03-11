"""
Position Management & Execution Layer - Real-time position monitoring and execution.
Uses existing OANDA API and trade management components.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from decimal import Decimal
import math

import sys
from pathlib import Path

# Add the project root to the path to import API modules
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.append(str(root_dir))

from api.oanda_api import OandaApi
from models.open_trade import OpenTrade
from ..core.models import TradeDecision, MarketContext, TimeFrame
from ..utils.config import Config
from ..utils.logger import get_logger


class PositionManager:
    """Real-time position monitoring and execution system."""
    
    def __init__(self, config: Config, oanda_api: OandaApi):
        self.config = config
        self.oanda_api = oanda_api
        self.logger = get_logger(__name__)
        
        # Position tracking
        self.active_positions: Dict[str, Dict[str, Any]] = {}
        self.position_history: List[Dict[str, Any]] = []
        self.scaling_levels: Dict[str, List[Dict[str, Any]]] = {}
        
        # Risk management
        self.max_daily_loss = config.risk_management.max_daily_loss
        self.max_open_trades = config.risk_management.max_open_trades
        self.daily_pnl = 0.0
        self.daily_trades = 0
        
        # Execution tracking
        self.execution_stats = {
            'total_trades': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'total_slippage': 0.0,
            'avg_slippage': 0.0
        }
        
        # Monitoring task
        self._monitoring_task = None
        self._is_running = False
    
        # Trade execution locks (prevent concurrent trades for same pair)
        self._execution_locks: Dict[str, asyncio.Lock] = {}
    
    async def start(self) -> None:
        """Start position monitoring."""
        print("💰 [DEBUG] Starting position manager...")
        self.logger.info("Starting position manager...")
        self._is_running = True
        self._monitoring_task = asyncio.create_task(self._position_monitoring_loop())
        print("✅ [DEBUG] Position manager started successfully")
        self.logger.info("Position manager started successfully")
    
    async def stop(self) -> None:
        """Stop position monitoring."""
        self.logger.info("Stopping position manager...")
        self._is_running = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Position manager stopped")
    
    async def execute_trade(self, decision: TradeDecision, market_context: MarketContext) -> Optional[str]:
        """Execute a trade based on the decision."""
        if not await self._can_execute_trade(decision):
            self.logger.warning("Trade blocked by safety checks")
            return None

        pair = decision.recommendation.pair

        # Get or create lock for this pair
        if pair not in self._execution_locks:
            self._execution_locks[pair] = asyncio.Lock()
        
        # Use lock to prevent concurrent execution for same pair
        async with self._execution_locks[pair]:
            self.logger.info(f"📈 Starting trade execution for {pair}...")
            self.logger.info(
                f"🎯 {pair}: Signal: {decision.recommendation.signal.value}, Entry: {decision.recommendation.entry_price}"
            )
            
            try:
                # Validate account balance before executing
                account_summary = self.oanda_api.get_account_summary()
                if not account_summary:
                    self.logger.error(f"❌ {pair}: Cannot get account summary - aborting trade")
                    return None
                
                account_balance = float(account_summary.get('balance', 0))
                margin_available = float(account_summary.get('marginAvailable', 0))
                
                self.logger.info(f"💰 {pair}: Account Balance: ${account_balance:.2f}, Available Margin: ${margin_available:.2f}")
                
                # Check if we have sufficient balance
                if account_balance <= 0:
                    self.logger.error(f"❌ {pair}: Insufficient account balance: ${account_balance:.2f}")
                    return None
                
                if margin_available <= 0:
                    self.logger.error(f"❌ {pair}: Insufficient margin available: ${margin_available:.2f}")
                    return None
                
                # Check if we already have a position for this pair
                self.logger.info(f"🔍 {pair}: Checking existing positions...")
                existing_position = await self._get_existing_position(pair)
                
                if existing_position:
                    self.logger.info(f"⚠️ {pair}: Found existing position, checking if we should close it...")
                    should_close = await self._should_close_position(existing_position, decision, market_context)
                    
                    if should_close:
                        self.logger.info(f"🔄 {pair}: Closing existing position...")
                        close_result = await self._close_position(existing_position)
                        if close_result:
                            self.logger.info(f"✅ {pair}: Position closed successfully")
                        else:
                            self.logger.error(f"❌ {pair}: Failed to close position")
                            return None
                    else:
                        self.logger.info(f"ℹ️ {pair}: Keeping existing position")
                        return existing_position['id']
                
                # Calculate position size
                self.logger.info(f"💰 {pair}: Calculating position size...")
                position_size = await self._calculate_position_size(decision, market_context)
                self.logger.info(f"💰 {pair}: Position size: {position_size}")
                
                # Auto-detect account type from account ID or URL
                is_demo = (
                    self.config.oanda_account_id.startswith('101-') or 
                    'fxpractice' in self.config.oanda_url.lower()
                )
                
                # Log appropriate message based on account type
                if is_demo:
                    self.logger.info(f"🎮 {pair}: DEMO ACCOUNT - Executing trade on practice account")
                else:
                    self.logger.warning(f"⚠️ 💰 {pair}: LIVE ACCOUNT - Executing REAL MONEY trade!")

                # Execute the trade (works for both demo and live)
                self.logger.info(f"🚀 {pair}: Executing trade...")
                trade_id = await self._execute_trade_order(decision, position_size)
                
                if trade_id:
                    self.logger.info(f"✅ {pair}: Trade executed successfully, ID: {trade_id}")
                    
                    # Record the trade
                    await self._record_trade(decision, trade_id, position_size)
                    
                    return trade_id
                else:
                    self.logger.error(f"❌ {pair}: Trade execution failed")
                    return None
                    
            except Exception as e:
                self.logger.error(f"❌ Error executing trade for {pair}: {e}")
                return None
    async def _get_existing_position(self, pair: str) -> Optional[Dict[str, Any]]:
        """Get existing position for a pair from OANDA."""
        try:
            open_trades = self.oanda_api.get_open_trades()
            if not open_trades:
                return None
            
            for trade in open_trades:
                if trade.instrument == pair:
                    return {
                        'id': trade.id,
                        'pair': trade.instrument,
                        'units': float(trade.currentUnits),
                        'price': float(trade.price),
                        'unrealized_pl': float(trade.unrealizedPL),
                        'margin_used': float(trade.marginUsed)
                    }
            return None
        except Exception as e:
            self.logger.error(f"Error getting existing position for {pair}: {e}")
            return None
    
    async def _should_close_position(self, existing_position: Dict[str, Any], 
                                     decision: TradeDecision, 
                                     market_context: MarketContext) -> bool:
        """Determine if existing position should be closed before opening new one."""
        try:
            # If new signal is opposite direction, close existing
            current_units = existing_position['units']
            new_signal = decision.recommendation.signal.value
            
            # Positive units = long, negative = short
            is_long = current_units > 0
            
            if (is_long and new_signal == 'sell') or (not is_long and new_signal == 'buy'):
                self.logger.info(f"New signal opposite to existing position - will close")
                return True
            
            return False
        except Exception as e:
            self.logger.error(f"Error in should_close_position: {e}")
            return False
    
    async def _close_position(self, position: Dict[str, Any]) -> bool:
        """Close an existing position."""
        try:
            trade_id = position['id']
            success = self.oanda_api.close_trade(trade_id)
            
            if success:
                # Remove from active positions
                pair = position['pair']
                if pair in self.active_positions:
                    del self.active_positions[pair]
                
                self.logger.info(f"✅ Closed position {trade_id} for {pair}")
                return True
            else:
                self.logger.error(f"❌ Failed to close position {trade_id}")
                return False
        except Exception as e:
            self.logger.error(f"Error closing position: {e}")
            return False
    
    async def _calculate_position_size(self, decision: TradeDecision, 
                                      market_context: MarketContext) -> float:
        """Calculate position size using FX position sizing with pip location."""
        try:
            from ..core.fx_position_sizing import compute_units_from_risk
            from infrastructure.instrument_collection import instrumentCollection as ic
            
            # Get account summary for balance
            account_summary = self.oanda_api.get_account_summary()
            if not account_summary:
                self.logger.error("Failed to get account summary")
                return 0.0
            
            account_balance = Decimal(str(account_summary.get('balance', 10000)))
            risk_percentage = Decimal(str(self.config.trading.risk_percentage))
            risk_amount = account_balance * (risk_percentage / Decimal('100'))
            
            self.logger.info(f"Account Balance: ${account_balance}, Risk Amount: ${risk_amount}")
            
            # Get instrument metadata for pip location
            pair = decision.recommendation.pair
            if pair not in ic.instruments_dict:
                self.logger.warning(f"Instrument {pair} not in collection, using default")
                # Default pip location for major pairs
                pip_location = 0.0001
            else:
                instrument = ic.instruments_dict[pair]
                pip_location = 10 ** instrument.pipLocation
            
            # Get home conversion rate
            prices = self.oanda_api.get_prices([pair])
            if not prices or len(prices) == 0:
                self.logger.error(f"Failed to get prices for {pair}")
                return 0.0
            
            price = prices[0]
            # Use buy conversion for buy orders, sell conversion for sell orders
            if decision.recommendation.signal.value == 'buy':
                conversion_rate = price.buyConversionRate if hasattr(price, 'buyConversionRate') else 1.0
            else:
                conversion_rate = price.sellConversionRate if hasattr(price, 'sellConversionRate') else 1.0
            
            # Calculate units using FX position sizing
            entry_price = decision.recommendation.entry_price
            stop_loss = decision.modified_stop_loss or decision.recommendation.stop_loss
            
            if not stop_loss:
                self.logger.error("No stop loss defined")
                return 0.0
            
            units = compute_units_from_risk(
                pip_location=pip_location,
                conversion_rate=conversion_rate,
                entry_price=entry_price,
                stop_loss=stop_loss,
                risk_amount=risk_amount
            )
            
            self.logger.info(f"Calculated position size: {units} units")
            return max(1.0, units)  # Minimum 1 unit
            
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return 0.0
    
    async def _execute_trade_order(self, decision: TradeDecision, position_size: float) -> Optional[str]:
        """Execute the trade order via OANDA API."""
        try:
            pair = decision.recommendation.pair
            signal = decision.recommendation.signal.value
            stop_loss = decision.modified_stop_loss or decision.recommendation.stop_loss
            take_profit = decision.modified_take_profit or decision.recommendation.take_profit
            
            # Convert signal to direction
            from constants import defs
            direction = defs.BUY if signal == 'buy' else defs.SELL
            
            # Execute trade
            trade_id = self.oanda_api.place_trade(
                pair_name=pair,
                units=position_size,
                direction=direction,
                stop_loss=float(stop_loss) if stop_loss else None,
                take_profit=float(take_profit) if take_profit else None
            )
            
            if trade_id:
                self.logger.info(f"✅ Trade executed successfully: ID={trade_id}")
                return trade_id
            else:
                self.logger.error("❌ Trade execution failed - no trade ID returned")
                return None
                
        except Exception as e:
            self.logger.error(f"Error executing trade order: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None
    
    async def _record_trade(self, decision: TradeDecision, trade_id: str, position_size: float) -> None:
        """Record trade details for tracking and analysis."""
        try:
            # Add to active positions
            self.active_positions[decision.recommendation.pair] = {
                'trade_id': trade_id,
                'pair': decision.recommendation.pair,
                'signal': decision.recommendation.signal.value,
                'entry_price': decision.recommendation.entry_price,
                'position_size': position_size,
                'stop_loss': decision.modified_stop_loss,
                'take_profit': decision.modified_take_profit,
                'entry_time': datetime.now(timezone.utc),
                'risk_amount': decision.risk_amount,
                'scaling_levels': [],
                'partial_exits': []
            }
            
            # Update daily stats
            self.daily_trades += 1
            
            # Log trade record
            self.position_history.append({
                'trade_id': trade_id,
                'pair': decision.recommendation.pair,
                'signal': decision.recommendation.signal.value,
                'entry_price': float(decision.recommendation.entry_price),
                'position_size': position_size,
                'stop_loss': float(decision.modified_stop_loss) if decision.modified_stop_loss else None,
                'take_profit': float(decision.modified_take_profit) if decision.modified_take_profit else None,
                'entry_time': datetime.now(timezone.utc).isoformat(),
                'status': 'open'
            })
            
            self.logger.info(f"📝 Trade recorded: {trade_id} for {decision.recommendation.pair}")
            
        except Exception as e:
            self.logger.error(f"Error recording trade: {e}")
    
    async def _can_execute_trade(self, decision: TradeDecision) -> bool:
        """Check if we can execute this trade based on risk management rules."""
        # Check daily loss limit — convert max_daily_loss (%) to dollars using account balance
        try:
            account_summary = self.oanda_api.get_account_summary()
            account_balance = float(account_summary.get('balance', 10000)) if account_summary else 10000
        except Exception:
            account_balance = 10000
        max_daily_loss_dollars = account_balance * (self.max_daily_loss / 100)
        if self.daily_pnl <= -max_daily_loss_dollars:
            self.logger.warning(f"Daily loss limit reached: ${self.daily_pnl:.2f} / -${max_daily_loss_dollars:.2f}")
            return False
        
        # Check max open trades
        if len(self.active_positions) >= self.max_open_trades:
            self.logger.warning(f"Max open trades reached: {len(self.active_positions)}")
            return False
        
        # Check if we already have a position in this pair
        if decision.recommendation.pair in self.active_positions:
            self.logger.info(f"Already have position in {decision.recommendation.pair}")
            return False
        
        return True
    
    async def _calculate_optimal_entry(self, decision: TradeDecision) -> tuple[Decimal, float]:
        """Calculate optimal entry price with slippage consideration."""
        # Get current market prices
        prices = self.oanda_api.get_prices([decision.recommendation.pair])
        if not prices:
            return decision.recommendation.entry_price, 0.0
        
        current_price = Decimal(str(prices[0].close))
        target_price = decision.recommendation.entry_price
        
        # Calculate slippage (difference between target and current)
        slippage = abs(float(current_price - target_price))
        
        # Use current price as entry (market order)
        return current_price, slippage
    
    async def _track_new_position(self, trade_id: str, decision: TradeDecision, 
                                 entry_price: Decimal, slippage: float, 
                                 market_context: MarketContext) -> None:
        """Track a new position."""
        position_data = {
            'trade_id': trade_id,
            'pair': decision.recommendation.pair,
            'signal': decision.recommendation.signal.value,
            'entry_price': entry_price,
            'position_size': decision.position_size,
            'stop_loss': decision.modified_stop_loss,
            'take_profit': decision.modified_take_profit,
            'entry_time': datetime.now(timezone.utc),
            'market_context': market_context,
            'slippage': slippage,
            'scaling_levels': [],
            'partial_exits': []
        }
        
        self.active_positions[decision.recommendation.pair] = position_data
        self.execution_stats['total_trades'] += 1
        self.execution_stats['successful_trades'] += 1
        self.execution_stats['total_slippage'] += slippage
        self.execution_stats['avg_slippage'] = (
            self.execution_stats['total_slippage'] / self.execution_stats['successful_trades']
        )
    
    async def _position_monitoring_loop(self) -> None:
        """Main position monitoring loop."""
        while self._is_running:
            try:
                await self._update_all_positions()
                await self._check_scaling_opportunities()
                await self._check_partial_exits()
                await self._adjust_stop_losses()
                
                # Update daily P&L
                await self._update_daily_pnl()
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in position monitoring loop: {e}")
                await asyncio.sleep(60)
    
    async def _update_all_positions(self) -> None:
        """Update all active positions with current P&L."""
        open_trades = self.oanda_api.get_open_trades()
        if not open_trades:
            return
        
        for trade in open_trades:
            if trade.instrument in self.active_positions:
                position = self.active_positions[trade.instrument]
                position['current_price'] = Decimal(str(trade.price))
                position['unrealized_pl'] = float(trade.unrealizedPL)
                position['margin_used'] = float(trade.marginUsed)
                position['last_update'] = datetime.now(timezone.utc)
    
    async def _check_scaling_opportunities(self) -> None:
        """Check for position scaling opportunities."""
        for pair, position in self.active_positions.items():
            if len(position['scaling_levels']) >= 3:  # Max 3 scaling levels
                continue
            
            # Check if price moved in our favor by 1R (risk-reward ratio)
            entry_price = position['entry_price']
            current_price = position.get('current_price', entry_price)
            stop_loss = position['stop_loss']
            
            if not stop_loss:
                continue
            
            # Calculate 1R move
            risk = abs(float(entry_price - stop_loss))
            if position['signal'] == 'buy':
                target_price = entry_price + Decimal(str(risk))
                if current_price >= target_price:
                    await self._scale_into_position(pair, position, 'long')
            else:
                target_price = entry_price - Decimal(str(risk))
                if current_price <= target_price:
                    await self._scale_into_position(pair, position, 'short')
    
    async def _scale_into_position(self, pair: str, position: Dict[str, Any], direction: str) -> None:
        """Scale into an existing position."""
        try:
            # Calculate scaling size (50% of original position)
            scaling_size = position['position_size'] * 0.5
            
            # Execute scaling trade
            trade_id = self.oanda_api.place_trade(
                pair_name=pair,
                units=float(scaling_size),
                direction=1 if direction == 'long' else -1,
                stop_loss=float(position['stop_loss']) if position['stop_loss'] else None,
                take_profit=float(position['take_profit']) if position['take_profit'] else None
            )
            
            if trade_id:
                scaling_level = {
                    'trade_id': trade_id,
                    'size': scaling_size,
                    'entry_price': position.get('current_price', position['entry_price']),
                    'entry_time': datetime.now(timezone.utc)
                }
                
                position['scaling_levels'].append(scaling_level)
                self.logger.info(f"📈 Scaled into {pair}: Size={scaling_size:.2f}")
            
        except Exception as e:
            self.logger.error(f"Error scaling into position {pair}: {e}")
    
    async def _check_partial_exits(self) -> None:
        """Check for partial profit taking opportunities."""
        for pair, position in self.active_positions.items():
            if len(position['partial_exits']) >= 3:  # Max 3 partial exits
                continue
            
            # Check profit targets (0.5R, 1R, 1.5R)
            entry_price = position['entry_price']
            current_price = position.get('current_price', entry_price)
            stop_loss = position['stop_loss']
            
            if not stop_loss:
                continue
            
            risk = abs(float(entry_price - stop_loss))
            profit_targets = [0.5, 1.0, 1.5]
            
            for target in profit_targets:
                if target in [exit['target'] for exit in position['partial_exits']]:
                    continue
                
                if position['signal'] == 'buy':
                    target_price = entry_price + Decimal(str(risk * target))
                    if current_price >= target_price:
                        await self._partial_exit(pair, position, target)
                else:
                    target_price = entry_price - Decimal(str(risk * target))
                    if current_price <= target_price:
                        await self._partial_exit(pair, position, target)
    
    async def _partial_exit(self, pair: str, position: Dict[str, Any], target: float) -> None:
        """Execute partial profit taking."""
        try:
            # Close 30% of position at each target
            exit_size = position['position_size'] * 0.3
            
            # Get open trades for this pair
            open_trades = self.oanda_api.get_open_trades()
            pair_trades = [t for t in open_trades if t.instrument == pair]
            
            if pair_trades:
                trade_id = pair_trades[0].id
                # Use partial close (units parameter) instead of closing 100%
                units_to_close = int(abs(exit_size))
                if units_to_close < 1:
                    units_to_close = 1
                try:
                    success = self.oanda_api.close_trade(trade_id, units=units_to_close)
                except TypeError:
                    # Fallback if close_trade doesn't support units parameter
                    success = self.oanda_api.close_trade(trade_id)
                
                if success:
                    partial_exit = {
                        'trade_id': trade_id,
                        'size': exit_size,
                        'exit_price': position.get('current_price', position['entry_price']),
                        'target': target,
                        'exit_time': datetime.now(timezone.utc)
                    }
                    
                    position['partial_exits'].append(partial_exit)
                    self.logger.info(f"💰 Partial exit {pair}: Target={target}R, Size={exit_size:.2f}")
            
        except Exception as e:
            self.logger.error(f"Error in partial exit {pair}: {e}")
    
    async def _adjust_stop_losses(self) -> None:
        """Dynamically adjust stop losses based on market conditions."""
        for pair, position in self.active_positions.items():
            # Only adjust if we have unrealized profit
            if position.get('unrealized_pl', 0) <= 0:
                continue
            
            # Move stop loss to breakeven after 0.5R profit
            entry_price = position['entry_price']
            current_price = position.get('current_price', entry_price)
            stop_loss = position['stop_loss']
            
            if not stop_loss:
                continue
            
            risk = abs(float(entry_price - stop_loss))
            profit = abs(float(current_price - entry_price))
            
            # Move to breakeven after 0.5R
            if profit >= risk * 0.5 and float(stop_loss) != float(entry_price):
                new_stop_loss = entry_price
                trade_id = position.get('trade_id')
                if trade_id:
                    try:
                        self.oanda_api.modify_trade(
                            trade_id=trade_id,
                            stop_loss=float(new_stop_loss)
                        )
                        position['stop_loss'] = new_stop_loss
                        self.logger.info(f"🔄 Stop loss moved to breakeven for {pair}: {new_stop_loss}")
                    except Exception as e:
                        self.logger.error(f"Failed to update stop loss for {pair}: {e}")
    
    async def _update_daily_pnl(self) -> None:
        """Update daily P&L tracking including both unrealized and realized P&L."""
        # Unrealized P&L from open positions
        unrealized_pnl = sum(p.get('unrealized_pl', 0) for p in self.active_positions.values())

        # Realized P&L from closed trades today
        from datetime import date
        today = date.today()
        realized_pnl = sum(
            t.get('pnl', 0)
            for t in self.position_history
            if t.get('status') == 'closed'
            and t.get('exit_time') is not None
            and (t['exit_time'].date() if hasattr(t['exit_time'], 'date') else today) == today
        )

        self.daily_pnl = unrealized_pnl + realized_pnl
    
    async def get_position_summary(self) -> Dict[str, Any]:
        """Get summary of all positions."""
        return {
            'active_positions': len(self.active_positions),
            'daily_pnl': self.daily_pnl,
            'daily_trades': self.daily_trades,
            'execution_stats': self.execution_stats,
            'positions': self.active_positions
        }
    
    async def close_all_positions(self) -> None:
        """Close all active positions."""
        self.logger.info("Closing all active positions...")
        
        for pair, position in self.active_positions.items():
            try:
                open_trades = self.oanda_api.get_open_trades()
                pair_trades = [t for t in open_trades if t.instrument == pair]
                
                for trade in pair_trades:
                    self.oanda_api.close_trade(trade.id)
                
                self.logger.info(f"Closed position: {pair}")
                
            except Exception as e:
                self.logger.error(f"Error closing position {pair}: {e}")
        
        self.active_positions.clear() 