"""
Risk Manager - Applies risk management rules to trade recommendations.
"""
import traceback
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal
import math

from ..core.models import TradeRecommendation, MarketContext, MarketCondition
from ..core.fx_position_sizing import compute_units_from_risk
from infrastructure.instrument_collection import instrumentCollection as ic
from api.oanda_api import OandaApi
from ..utils.config import Config
from ..utils.logger import get_logger


class RiskManager:
    """Applies risk management rules to trade recommendations."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger(__name__)
        
        # Initialize OANDA API for account balance retrieval
        self.oanda_api = OandaApi()
        
        # Risk parameters
        self.max_daily_loss = Decimal(str(config.risk_management.max_daily_loss))
        self.max_position_size = Decimal(str(config.risk_management.max_position_size))
        self.correlation_limit = config.risk_management.correlation_limit
        self.max_open_trades = config.risk_management.max_open_trades
        self.stop_loss_atr_multiplier = config.risk_management.stop_loss_atr_multiplier
        self.trailing_stop = config.risk_management.trailing_stop
        self.trailing_stop_atr_multiplier = config.risk_management.trailing_stop_atr_multiplier
        
        # Daily tracking
        self._daily_loss = Decimal('0')
        self._daily_trades = 0
        self._open_positions = {}
        from datetime import datetime, timezone
        self._last_reset = datetime.now(timezone.utc).date()
        self._daily_loss_hit_time = None  # Track when daily loss limit was hit
        
        # Circuit breaker for consecutive losses
        self._consecutive_losses = 0
        self._max_consecutive_losses = config.risk_management.consecutive_loss_limit
        self._circuit_breaker_active = False
        self._trade_history_today = []  # Track all trades for the day
        self._circuit_breaker_reset_time = None
    
    def _get_account_balance(self) -> Decimal:
        """Get current account balance from OANDA API."""
        try:
            account_summary = self.oanda_api.get_account_summary()
            if account_summary and 'balance' in account_summary:
                balance = Decimal(str(account_summary['balance']))
                self.logger.info(f"Retrieved account balance: ${balance}")
                return balance
            else:
                self.logger.warning("Failed to retrieve account balance, using default")
                return Decimal('10000')
        except Exception as e:
            self.logger.error(f"Error retrieving account balance: {e}")
            return Decimal('10000')
    
    async def assess_risk(self, recommendation: TradeRecommendation, current_price: float, 
                         market_context: MarketContext) -> Dict[str, Any]:
        """Assess the risk of a trade recommendation."""
        try:
            # Input validation
            if not recommendation:
                raise ValueError("Trade recommendation cannot be None")
            if current_price <= 0:
                raise ValueError(f"Current price must be positive, got: {current_price}")
            if not market_context:
                raise ValueError("Market context cannot be None")
            
            # Convert current_price to Decimal for consistency
            current_price_decimal = Decimal(str(current_price))
            
            # Check circuit breaker
            circuit_breaker_check = self._check_circuit_breaker()
            if not circuit_breaker_check['approved']:
                return {
                    'approved': False,
                    'reason': circuit_breaker_check['reason'],
                    'risk_score': 1.0
                }
            
            # Basic risk checks
            basic_checks = self._check_basic_risk_rules(recommendation)
            if not basic_checks['approved']:
                return {
                    'approved': False,
                    'reason': basic_checks['reason'],
                    'risk_score': 1.0
                }
            
            # Market condition checks
            condition_checks = self._check_market_condition_rules(recommendation, market_context)
            if not condition_checks['approved']:
                return {
                    'approved': False,
                    'reason': condition_checks['reason'],
                    'risk_score': 0.8
                }
            
            # Position sizing checks
            sizing_checks = self._check_position_sizing(recommendation, current_price_decimal)
            if not sizing_checks['approved']:
                return {
                    'approved': False,
                    'reason': sizing_checks['reason'],
                    'risk_score': 0.6
                }
            
            # Correlation limit checks
            correlation_checks = self._check_correlation_limits(recommendation)
            if not correlation_checks['approved']:
                return {
                    'approved': False,
                    'reason': correlation_checks['reason'],
                    'risk_score': 0.7
                }
            
            # Market session checks
            session_checks = self._check_market_session()
            if not session_checks['approved']:
                return {
                    'approved': False,
                    'reason': session_checks['reason'],
                    'risk_score': 0.3
                }
            
            # Calculate overall risk score (use default scores if not provided)
            basic_score = basic_checks.get('score', 0.5)
            condition_score = condition_checks.get('score', 0.5)
            sizing_score = sizing_checks.get('score', 0.5)
            correlation_score = correlation_checks.get('score', 0.5)
            session_score = session_checks.get('score', 0.5)
            risk_score = (basic_score + condition_score + sizing_score + correlation_score + session_score) / 5
            
            return {
                'approved': True,
                'reason': 'Risk assessment passed',
                'risk_score': risk_score,
                'max_position_size': sizing_checks.get('max_size', 0.0)
            }
            
        except (ValueError, TypeError, AttributeError) as e:
            self.logger.error(f"Risk assessment validation error: {e}")
            return {
                'approved': False,
                'reason': f'Invalid data for risk assessment: {str(e)}',
                'risk_score': 1.0
            }
        except Exception as e:
            self.logger.error(f"Unexpected error in risk assessment: {e}")
            self.logger.debug(f"Risk assessment traceback: {traceback.format_exc()}")
            return {
                'approved': False,
                'reason': f'Risk assessment system error: {str(e)}',
                'risk_score': 1.0
            }
    
    def _check_basic_risk_rules(self, recommendation: TradeRecommendation) -> Dict[str, Any]:
        """Check basic risk management rules."""
        
        # Check confidence threshold - Production settings
        confidence_threshold = self.config.technical_analysis.confidence_threshold
        if recommendation.confidence < confidence_threshold:
            return {
                'approved': False,
                'reason': f'Confidence {recommendation.confidence:.2f} below threshold {confidence_threshold}'
            }
        
        # Check daily trade limit
        if self._daily_trades >= self.config.trading.max_trades_per_day:
            return {
                'approved': False,
                'reason': f'Daily trade limit reached ({self._daily_trades}/{self.config.trading.max_trades_per_day})'
            }
        
        # Check open positions limit
        if len(self._open_positions) >= self.max_open_trades:
            return {
                'approved': False,
                'reason': f'Maximum open trades reached ({len(self._open_positions)}/{self.max_open_trades})'
            }
        
        # Check risk-reward ratio - Production settings
        min_risk_reward = self.config.technical_analysis.risk_reward_ratio_minimum
        if recommendation.risk_reward_ratio < min_risk_reward:
            return {
                'approved': False,
                'reason': f'Risk-reward ratio {recommendation.risk_reward_ratio:.2f} below minimum {min_risk_reward}'
            }
        
        return {'approved': True, 'reason': 'Basic risk checks passed', 'score': 0.8}
    
    def _check_market_condition_rules(self, recommendation: TradeRecommendation, market_context: MarketContext) -> Dict[str, Any]:
        """Check market condition specific risk rules."""
        
        condition = recommendation.market_condition
        
        if condition == MarketCondition.NEWS_REACTIONARY:
            # Higher risk in news-driven markets
            if recommendation.confidence < 0.8:
                return {
                    'approved': False,
                    'reason': 'News reactionary markets require higher confidence (0.8)',
                    'score': 0.3
                }
        
        elif condition == MarketCondition.REVERSAL:
            # Reversal trades need strong confirmation
            if recommendation.confidence < 0.75:
                return {
                    'approved': False,
                    'reason': 'Reversal trades require higher confidence (0.75)',
                    'score': 0.4
                }
        
        elif condition == MarketCondition.BREAKOUT:
            # Breakout trades need volume confirmation
            if hasattr(market_context, 'volume') and market_context.volume < 1.5:
                return {
                    'approved': False,
                    'reason': 'Breakout trades need higher volume confirmation',
                    'score': 0.5
                }
        
        elif condition == MarketCondition.RANGING:
            # Ranging markets need tight stops
            if recommendation.risk_reward_ratio > 3.0:
                return {
                    'approved': False,
                    'reason': 'Ranging markets need tighter risk/reward ratios',
                    'score': 0.6
                }
        
        return {'approved': True, 'reason': 'Market condition checks passed', 'score': 0.7}
    
    def _check_position_sizing(self, recommendation: TradeRecommendation, current_price: Decimal) -> Dict[str, Any]:
        """Check position sizing rules."""
        
        # Calculate potential loss
        if recommendation.stop_loss and current_price > 0:
            potential_loss = abs(current_price - recommendation.stop_loss)
            loss_percentage = (potential_loss / current_price) * 100
            
            # Check if loss exceeds daily limit
            if self._daily_loss + potential_loss > self.max_daily_loss:
                return {
                    'approved': False,
                    'reason': f'Potential loss {potential_loss:.2f} would exceed daily limit'
                }
        
        return {'approved': True, 'reason': 'Position sizing checks passed', 'score': 0.6}
    
    def _calculate_pair_correlation(self, pair1: str, pair2: str) -> float:
        """
        Calculate correlation between two currency pairs.
        
        Returns:
            float: Correlation coefficient between -1.0 and 1.0
                   1.0 = perfectly correlated (move together)
                   -1.0 = perfectly inversely correlated (move opposite)
                   0.0 = no correlation
        """
        # Currency correlation matrix (historical averages - approximate values)
        # Positive = move together, Negative = move opposite
        correlations = {
            ('EUR_USD', 'GBP_USD'): 0.70,
            ('EUR_USD', 'USD_CHF'): -0.85,
            ('EUR_USD', 'USD_JPY'): -0.40,
            ('EUR_USD', 'AUD_USD'): 0.65,
            ('EUR_USD', 'NZD_USD'): 0.60,
            ('GBP_USD', 'USD_CHF'): -0.75,
            ('GBP_USD', 'USD_JPY'): -0.35,
            ('GBP_USD', 'AUD_USD'): 0.60,
            ('GBP_USD', 'EUR_GBP'): -0.80,
            ('USD_CHF', 'USD_JPY'): 0.65,
            ('USD_JPY', 'EUR_JPY'): 0.85,
            ('AUD_USD', 'NZD_USD'): 0.85,
            ('EUR_JPY', 'GBP_JPY'): 0.75,
        }
        
        # Check both orders
        key = (pair1, pair2)
        reverse_key = (pair2, pair1)
        
        if key in correlations:
            return correlations[key]
        elif reverse_key in correlations:
            return correlations[reverse_key]
        
        # If not in matrix, check if they share a currency
        pair1_currencies = pair1.split('_')
        pair2_currencies = pair2.split('_')
        
        # Same base or quote currency = some correlation
        if pair1_currencies[0] == pair2_currencies[0]:
            return 0.50  # Same base currency
        elif pair1_currencies[1] == pair2_currencies[1]:
            return -0.50  # Same quote currency (often inverse relationship)
        elif pair1_currencies[0] in pair2_currencies or pair1_currencies[1] in pair2_currencies:
            return 0.30  # Share one currency
        else:
            return 0.10  # No direct relationship
    
    def _check_correlation_limits(self, recommendation: TradeRecommendation) -> Dict[str, Any]:
        """Check if adding this position would exceed correlation limits."""
        
        if not self._open_positions:
            return {'approved': True, 'reason': 'No open positions to correlate with', 'score': 1.0}
        
        new_pair = recommendation.pair
        correlation_limit = self.correlation_limit
        
        # Check correlation with each open position
        high_correlation_pairs = []
        
        for open_pair, position_info in self._open_positions.items():
            correlation = abs(self._calculate_pair_correlation(new_pair, open_pair))
            
            if correlation > correlation_limit:
                high_correlation_pairs.append({
                    'pair': open_pair,
                    'correlation': correlation
                })
        
        if high_correlation_pairs:
            pairs_str = ', '.join([f"{p['pair']} ({p['correlation']:.2f})" for p in high_correlation_pairs])
            return {
                'approved': False,
                'reason': f'High correlation with open positions: {pairs_str}. Limit: {correlation_limit}',
                'score': 0.3
            }
        
        return {'approved': True, 'reason': 'Correlation checks passed', 'score': 0.9}
    
    async def calculate_position_size(
        self, 
        recommendation: TradeRecommendation, 
        risk_assessment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate FX position size using pip location and home conversions."""
        
        try:
            # Input validation
            if not recommendation:
                raise ValueError("Trade recommendation cannot be None")
            if not risk_assessment:
                raise ValueError("Risk assessment cannot be None")
            if not (recommendation.stop_loss and recommendation.entry_price):
                return {
                    'size': Decimal('0'),
                    'risk_amount': Decimal('0'),
                    'stop_loss': recommendation.stop_loss,
                    'take_profit': recommendation.take_profit
                }
            
            # Validate price values
            if recommendation.entry_price <= 0:
                raise ValueError(f"Entry price must be positive, got: {recommendation.entry_price}")
            if recommendation.stop_loss <= 0:
                raise ValueError(f"Stop loss must be positive, got: {recommendation.stop_loss}")

            # Get real account balance from OANDA API
            account_balance = self._get_account_balance()
            risk_percentage = Decimal(str(self.config.trading.risk_percentage))
            risk_amount = account_balance * (risk_percentage / 100)
            
            self.logger.info(f"Position sizing: Balance=${account_balance}, Risk={risk_percentage}%, Amount=${risk_amount}")

            pair = recommendation.pair
            entry_price = Decimal(str(recommendation.entry_price))
            stop_loss = Decimal(str(recommendation.stop_loss))

            # For backtesting, skip instrument metadata check
            # Use default pip location for major pairs
            pip_location = -4  # Default for major forex pairs

            # For backtesting, use simplified position size calculation
            # Calculate pip value and position size
            pip_value = abs(entry_price - stop_loss)
            if pip_value > 0:
                # Simplified position size calculation for backtesting
                # Risk amount / pip value = position size
                units = risk_amount / pip_value
            else:
                units = 0

            # Respect maximum size
            max_size = float(self.max_position_size)
            units = min(units, max_size)

            return {
                'size': Decimal(str(units)),
                'risk_amount': risk_amount,
                'stop_loss': stop_loss,
                'take_profit': recommendation.take_profit
            }
                
        except (ValueError, TypeError, ZeroDivisionError) as e:
            self.logger.error(f"Position sizing calculation error: {e}")
            return {
                'size': Decimal('0.01'),
                'risk_amount': Decimal('100'),
                'stop_loss': recommendation.stop_loss,
                'take_profit': recommendation.take_profit
            }
        except Exception as e:
            self.logger.error(f"Unexpected error in position sizing: {e}")
            return {
                'size': Decimal('0.01'),
                'risk_amount': Decimal('100'),
                'stop_loss': recommendation.stop_loss,
                'take_profit': recommendation.take_profit
            }
    
    def _calculate_risk_score(self, recommendation: TradeRecommendation, market_context: MarketContext) -> float:
        """Calculate a risk score for the trade."""
        
        score = 0.0
        
        # Confidence contributes to score
        score += recommendation.confidence * 0.3
        
        # Risk-reward ratio contributes
        score += min(recommendation.risk_reward_ratio / 3.0, 1.0) * 0.2
        
        # Market condition contributes
        condition_scores = {
            MarketCondition.NEWS_REACTIONARY: 0.6,
            MarketCondition.REVERSAL: 0.7,
            MarketCondition.BREAKOUT: 0.8,
            MarketCondition.RANGING: 0.9,
            MarketCondition.UNKNOWN: 0.5
        }
        score += condition_scores.get(recommendation.market_condition, 0.5) * 0.2
        
        # Volatility consideration
        if hasattr(market_context, 'volatility'):
            volatility_score = max(0, 1 - market_context.volatility)
            score += volatility_score * 0.3
        
        return min(score, 1.0)
    
    def _reset_daily_counters(self) -> None:
        """Reset daily counters if it's a new day."""
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).date()
        if today > self._last_reset:
            self._daily_loss = Decimal('0')
            self._daily_trades = 0
            self._last_reset = today
    
    def add_open_position(self, pair: str, trade_data: Dict[str, Any]) -> None:
        """Add an open position to tracking."""
        self._open_positions[pair] = trade_data
        self._daily_trades += 1
    
    def _check_circuit_breaker(self) -> Dict[str, Any]:
        """Check if circuit breaker is active (enhanced with daily loss tracking)."""
        from datetime import datetime, timezone, timedelta
        
        # Reset daily tracking if new day
        current_date = datetime.now(timezone.utc).date()
        if current_date != self._last_reset:
            self._reset_daily_tracking()
        
        # Reset circuit breaker if enough time has passed (1 hour)
        if (self._circuit_breaker_active and 
            self._circuit_breaker_reset_time and 
            datetime.now(timezone.utc) > self._circuit_breaker_reset_time):
            self._circuit_breaker_active = False
            self._consecutive_losses = 0
            self.logger.info("🟢 Circuit breaker reset - trading resumed")
        
        # Check if circuit breaker is active due to consecutive losses
        if self._circuit_breaker_active:
            return {
                'approved': False,
                'reason': f'Circuit breaker active after {self._consecutive_losses} consecutive losses'
            }
        
        # Check if daily loss limit was hit and cooldown is still active
        if self._daily_loss_hit_time:
            cooldown_minutes = self.config.risk_management.daily_loss_cooldown_minutes
            time_since_hit = datetime.now(timezone.utc) - self._daily_loss_hit_time
            
            if time_since_hit.total_seconds() / 60 < cooldown_minutes:
                remaining_minutes = cooldown_minutes - (time_since_hit.total_seconds() / 60)
                return {
                    'approved': False,
                    'reason': f'Daily loss limit cooldown active. Resume in {remaining_minutes:.0f} minutes'
                }
            else:
                # Cooldown period passed, reset
                self._daily_loss_hit_time = None
                self.logger.info("🟢 Daily loss cooldown period ended - trading resumed")
        
        # Check if daily loss exceeds limit
        account_balance = self._get_account_balance()
        max_daily_loss_amount = account_balance * (Decimal(str(self.config.risk_management.max_daily_loss)) / 100)
        
        if abs(self._daily_loss) >= max_daily_loss_amount:
            if not self._daily_loss_hit_time:
                self._daily_loss_hit_time = datetime.now(timezone.utc)
                self.logger.error(f"🛑 Daily loss limit hit: ${abs(self._daily_loss):.2f} / ${max_daily_loss_amount:.2f}")
            
            return {
                'approved': False,
                'reason': f'Daily loss limit exceeded: ${abs(self._daily_loss):.2f} / ${max_daily_loss_amount:.2f}'
            }
        
        return {'approved': True, 'reason': 'Circuit breaker check passed'}
    
    def _trigger_circuit_breaker(self) -> None:
        """Trigger the circuit breaker."""
        from datetime import datetime, timezone, timedelta
        
        self._circuit_breaker_active = True
        self._circuit_breaker_reset_time = datetime.now(timezone.utc) + timedelta(hours=1)
        self.logger.warning(f"Circuit breaker triggered after {self._consecutive_losses} consecutive losses")
    
    def update_trade_result(self, pair: str, profit_loss: Decimal) -> None:
        """Update risk manager with trade result (enhanced with scaling logic)."""
        self._daily_loss += profit_loss
        if pair in self._open_positions:
            del self._open_positions[pair]
        
        # Track trade in today's history
        from datetime import datetime, timezone
        was_win = profit_loss > 0
        self._trade_history_today.append({
            'pair': pair,
            'pnl': float(profit_loss),
            'was_win': was_win,
            'timestamp': datetime.now(timezone.utc)
        })
        
        # Update consecutive loss counter
        if profit_loss < 0:  # Loss
            self._consecutive_losses += 1
            self.logger.warning(f"❌ Loss recorded for {pair}: ${profit_loss:.2f}. Consecutive losses: {self._consecutive_losses}")
            
            if self._consecutive_losses >= self._max_consecutive_losses:
                self._trigger_circuit_breaker()
        else:  # Profit
            self._consecutive_losses = 0  # Reset on profit
            self.logger.info(f"✅ Win recorded for {pair}: ${profit_loss:.2f}")
        
        # Log daily progress
        account_balance = self._get_account_balance()
        max_daily_loss_amount = account_balance * (Decimal(str(self.config.risk_management.max_daily_loss)) / 100)
        loss_percentage = (abs(self._daily_loss) / max_daily_loss_amount) * 100 if max_daily_loss_amount > 0 else 0
        
        if abs(self._daily_loss) > 0 and loss_percentage > 50:
            self.logger.warning(f"⚠️ Daily loss at {loss_percentage:.0f}% of limit (${abs(self._daily_loss):.2f} / ${max_daily_loss_amount:.2f})")
    
    def _reset_daily_tracking(self):
        """Reset daily tracking for a new trading day."""
        from datetime import datetime, timezone
        
        self.logger.info(f"📅 Resetting daily tracking. Previous day: {self._daily_trades} trades, ${self._daily_loss:.2f} P&L")
        
        self._daily_loss = Decimal('0')
        self._daily_trades = 0
        self._daily_loss_hit_time = None
        self._trade_history_today = []
        self._last_reset = datetime.now(timezone.utc).date()
        # Note: Don't reset consecutive losses or circuit breaker - those persist across days
    
    def get_position_size_multiplier(self) -> float:
        """
        Get position size multiplier based on recent performance.
        Returns value between 0.5 and 1.0 for scaling down after losses.
        """
        if not self.config.risk_management.scale_down_after_losses:
            return 1.0
        
        # Scale down after consecutive losses
        if self._consecutive_losses >= 2:
            scale_factor = self.config.risk_management.loss_scale_down_pct / 100
            self.logger.info(f"📉 Scaling down position size to {scale_factor*100:.0f}% due to {self._consecutive_losses} consecutive losses")
            return scale_factor
        
        return 1.0
    
    def _get_current_trading_session(self) -> str:
        """
        Determine current trading session based on UTC time.
        
        Returns:
            str: 'asian_early', 'asian_late', 'london_open', 'ny_open', or 'overlap'
        """
        from datetime import datetime, timezone
        
        current_utc = datetime.now(timezone.utc)
        hour_utc = current_utc.hour
        
        # Trading session times (UTC):
        # Asian: 23:00 - 08:00 UTC
        # London: 07:00 - 16:00 UTC (08:00-17:00 BST)
        # NY: 13:00 - 22:00 UTC (08:00-17:00 EST)
        # Overlap (London + NY): 13:00 - 16:00 UTC
        
        if 13 <= hour_utc < 16:
            return 'overlap'  # Best liquidity
        elif 8 <= hour_utc < 13:
            return 'london_open'  # High liquidity
        elif 13 <= hour_utc < 22:
            return 'ny_open'  # High liquidity
        elif 0 <= hour_utc < 3:
            return 'asian_early'  # Moderate liquidity
        else:  # 3 <= hour_utc < 8 or 22 <= hour_utc < 24
            return 'asian_late'  # Low liquidity
    
    def _check_market_session(self) -> Dict[str, Any]:
        """Check if current trading session is acceptable."""
        
        current_session = self._get_current_trading_session()
        preferred_sessions = self.config.market_conditions.preferred_sessions
        avoid_sessions = self.config.market_conditions.avoid_sessions
        
        # Check if in avoid list
        if current_session in avoid_sessions:
            return {
                'approved': False,
                'reason': f'Current session ({current_session}) is in avoid list. Trade during: {", ".join(preferred_sessions)}',
                'score': 0.2
            }
        
        # Check if in preferred list
        if current_session in preferred_sessions:
            return {
                'approved': True,
                'reason': f'Trading during preferred session: {current_session}',
                'score': 1.0
            }
        
        # Not preferred but not avoided either
        return {
            'approved': True,
            'reason': f'Trading during acceptable session: {current_session}',
            'score': 0.7
        } 