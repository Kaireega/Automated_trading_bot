"""
Advanced Risk Management - Kelly Criterion, portfolio heat, drawdown protection.
Uses existing technical indicators and market data.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
import math
import statistics

from ..core.models import TradeDecision, MarketContext, TechnicalIndicators
from ..utils.config import Config
from ..utils.logger import get_logger


class AdvancedRiskManager:
    """Advanced risk management using Kelly Criterion and portfolio heat management."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger(__name__)
        
        # Initialize OANDA API for account balance retrieval
        from api.oanda_api import OandaApi
        self.oanda_api = OandaApi()
        
        # Risk parameters
        self.max_daily_loss = config.risk_management.max_daily_loss
        self.max_drawdown = 0.05  # 5% max drawdown
        self.max_correlation_exposure = 0.7
        self.kelly_fraction = 0.25  # Use 25% of Kelly Criterion for safety
        
        # Portfolio tracking
        self.portfolio_history: List[Dict[str, Any]] = []
        self.daily_pnl_history: List[float] = []
        self.trade_history: List[Dict[str, Any]] = []
        self.current_drawdown = 0.0
        self.peak_equity = 0.0
        
        # Correlation tracking
        self.correlation_matrix: Dict[str, Dict[str, float]] = {}
        self.portfolio_heat = 0.0
        self.active_positions: Dict[str, Dict[str, Any]] = {}
        
        # Volatility tracking
        self.volatility_history: Dict[str, List[float]] = {}
        self.volatility_lookback = 20  # 20 periods for volatility calculation
        
        # Time-based risk decay
        self.event_risk_decay: Dict[str, Dict[str, Any]] = {}
        
        # Performance metrics
        self.win_rate = 0.0
        self.avg_win = 0.0
        self.avg_loss = 0.0
        self.profit_factor = 0.0
        self.max_consecutive_losses = 0
        self.current_consecutive_losses = 0
    
    def _get_account_balance(self) -> float:
        """Get current account balance from OANDA API."""
        try:
            account_summary = self.oanda_api.get_account_summary()
            if account_summary and 'balance' in account_summary:
                balance = float(account_summary['balance'])
                self.logger.debug(f"Retrieved account balance: ${balance}")
                return balance
            else:
                self.logger.warning("Failed to retrieve account balance, using default")
                return 10000.0
        except Exception as e:
            self.logger.error(f"Error retrieving account balance: {e}")
            return 10000.0
    
    async def start(self) -> None:
        """Start advanced risk management system."""
        print("⚠️ [DEBUG] Starting advanced risk manager...")
        self.logger.info("Starting advanced risk manager...")
        
        print("📊 [DEBUG] Loading historical data...")
        await self._load_historical_data()
        print("✅ [DEBUG] Historical data loaded")
        
        print("✅ [DEBUG] Advanced risk manager started successfully")
        self.logger.info("Advanced risk manager started successfully")
    
    async def stop(self) -> None:
        """Stop advanced risk management system."""
        self.logger.info("Stopping advanced risk manager...")
        self.logger.info("Advanced risk manager stopped")
    
    async def assess_trade_risk(self, recommendation: TradeDecision, 
                              market_context: MarketContext, 
                              technical_indicators: TechnicalIndicators,
                              fundamental_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Assess risk for a potential trade."""
        self.logger.info(f"⚠️ Starting risk assessment for {recommendation.recommendation.pair}...")
        
        try:
            # Calculate market risk
            self.logger.info(f"🌍 {recommendation.recommendation.pair}: Calculating market risk...")
            market_risk = await self._calculate_market_risk(market_context, technical_indicators)
            self.logger.info(f"🌍 {recommendation.recommendation.pair}: Market risk score: {market_risk:.3f}")
            
            # Calculate position risk
            self.logger.info(f"💰 {recommendation.recommendation.pair}: Calculating position risk...")
            position_risk = await self._calculate_position_risk(recommendation)
            self.logger.info(f"💰 {recommendation.recommendation.pair}: Position risk score: {position_risk:.3f}")
            
            # Calculate correlation risk
            self.logger.info(f"🔗 {recommendation.recommendation.pair}: Calculating correlation risk...")
            correlation_risk = await self._calculate_correlation_risk(recommendation.recommendation.pair)
            self.logger.info(f"🔗 {recommendation.recommendation.pair}: Correlation risk score: {correlation_risk:.3f}")
            
            # Calculate fundamental risk
            self.logger.info(f"📰 {recommendation.recommendation.pair}: Calculating fundamental risk...")
            fundamental_risk = await self._calculate_fundamental_risk(fundamental_analysis)
            self.logger.info(f"📰 {recommendation.recommendation.pair}: Fundamental risk score: {fundamental_risk:.3f}")
            
            # Calculate overall risk score
            self.logger.info(f"🧮 {recommendation.recommendation.pair}: Calculating overall risk score...")
            overall_risk = self._calculate_overall_risk(market_risk, position_risk, correlation_risk, fundamental_risk)
            self.logger.info(f"🧮 {recommendation.recommendation.pair}: Overall risk score: {overall_risk:.3f}")
            
            # Determine risk level
            risk_level = self._determine_risk_level(overall_risk)
            self.logger.info(f"📊 {recommendation.recommendation.pair}: Risk level: {risk_level}")
            
            # Check if trade should be approved
            approved = overall_risk <= self.config.risk_management.max_risk_threshold
            self.logger.info(f"✅ {recommendation.recommendation.pair}: Trade approved: {approved} (threshold: {self.config.risk_management.max_risk_threshold})")
            
            result = {
                'risk_score': overall_risk,
                'risk_level': risk_level,
                'approved': approved,
                'market_risk': market_risk,
                'position_risk': position_risk,
                'correlation_risk': correlation_risk,
                'fundamental_risk': fundamental_risk,
                'reason': 'Risk within acceptable limits' if approved else f'Risk {overall_risk:.3f} exceeds threshold {self.config.risk_management.max_risk_threshold}',
                'assessment_timestamp': datetime.now()
            }
            
            self.logger.info(f"✅ Risk assessment completed for {recommendation.recommendation.pair}")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Error in risk assessment for {recommendation.recommendation.pair}: {e}")
            return {
                'risk_score': 1.0,  # Maximum risk on error
                'risk_level': 'HIGH',
                'approved': False,
                'reason': f'Error in risk assessment: {str(e)}',
                'assessment_timestamp': datetime.now()
            }

    async def _calculate_market_risk(self, market_context: MarketContext, 
                                     technical_indicators: TechnicalIndicators) -> float:
        """Estimate market risk from volatility, trend strength, and momentum.
        Returns a score in [0,1], higher = riskier.
        """
        try:
            volatility = float(getattr(market_context, 'volatility', 0.0) or 0.0)
            trend_strength = float(getattr(market_context, 'trend_strength', 0.0) or 0.0)
            # Normalize metrics
            vol_component = max(0.0, min(1.0, volatility))
            trend_component = 1.0 - max(0.0, min(1.0, trend_strength))
            # Technical ATR can add to risk when high
            atr = float(getattr(technical_indicators, 'atr', 0.0) or 0.0)
            atr_component = max(0.0, min(1.0, atr * 100))  # heuristic normalization
            risk = 0.5 * vol_component + 0.3 * trend_component + 0.2 * atr_component
            return max(0.0, min(1.0, risk))
        except Exception:
            return 0.7

    async def _calculate_position_risk(self, decision: TradeDecision) -> float:
        """Estimate per-trade position risk from stop distance relative to price.
        Returns [0,1].
        """
        try:
            entry = decision.recommendation.entry_price
            stop = decision.modified_stop_loss or decision.recommendation.stop_loss
            if not entry or not stop:
                return 0.6
            rel_risk = abs(float(entry - stop)) / max(float(entry), 1e-6)
            # Normalize: 0.5% -> ~0.1, 2% -> ~0.4, 5% -> ~1.0
            score = min(1.0, rel_risk / 0.05)
            return score
        except Exception:
            return 0.6

    async def _calculate_correlation_risk(self, pair: str) -> float:
        """Estimate portfolio correlation heat risk. Uses current portfolio_heat.
        Returns [0,1].
        """
        try:
            return max(0.0, min(1.0, self.portfolio_heat))
        except Exception:
            return 0.3

    async def _calculate_fundamental_risk(self, fundamental_analysis: Dict[str, Any]) -> float:
        """Estimate fundamental risk from sentiment and event proximity.
        Returns [0,1].
        """
        try:
            sentiment_score = float(fundamental_analysis.get('sentiment_score', 0.0) or 0.0)
            high_impact_events = fundamental_analysis.get('high_impact_events', []) or []
            # Negative sentiment increases risk, more events increases risk
            sentiment_component = 0.5 * (1.0 - max(-1.0, min(1.0, sentiment_score)))
            event_component = min(1.0, len(high_impact_events) / 5.0)
            return max(0.0, min(1.0, 0.6 * sentiment_component + 0.4 * event_component))
        except Exception:
            return 0.4

    def _calculate_overall_risk(self, market_risk: float, position_risk: float,
                                 correlation_risk: float, fundamental_risk: float) -> float:
        """Combine components to overall risk score [0,1]."""
        try:
            weights = {
                'market': 0.35,
                'position': 0.35,
                'correlation': 0.15,
                'fundamental': 0.15,
            }
            score = (
                market_risk * weights['market'] +
                position_risk * weights['position'] +
                correlation_risk * weights['correlation'] +
                fundamental_risk * weights['fundamental']
            )
            return max(0.0, min(1.0, score))
        except Exception:
            return 0.8
    
    async def _basic_risk_check(self, decision: TradeDecision) -> Dict[str, Any]:
        """Basic risk management checks."""
        # Check daily loss limit
        if self._calculate_daily_pnl() <= -self.max_daily_loss:
            return {
                'approved': False,
                'reason': f"Daily loss limit reached: ${self._calculate_daily_pnl():.2f}"
            }
        
        # Check max open trades
        if len(self.active_positions) >= self.config.risk_management.max_open_trades:
            return {
                'approved': False,
                'reason': f"Max open trades reached: {len(self.active_positions)}"
            }
        
        # Check if we already have a position in this pair
        if decision.recommendation.pair in self.active_positions:
            return {
                'approved': False,
                'reason': f"Already have position in {decision.recommendation.pair}"
            }
        
        return {'approved': True}
    
    async def _calculate_kelly_position_size(self, decision: TradeDecision, 
                                           market_context: MarketContext) -> float:
        """Calculate optimal position size using Kelly Criterion."""
        # Get historical performance metrics
        if len(self.trade_history) < 10:
            # Not enough data, use conservative sizing
            return 0.02  # 2% of account
        
        # Calculate Kelly Criterion: f = (bp - q) / b
        # where: b = odds received, p = probability of win, q = probability of loss
        
        # Calculate win rate and average win/loss
        wins = [t for t in self.trade_history if t['pnl'] > 0]
        losses = [t for t in self.trade_history if t['pnl'] < 0]
        
        if not wins or not losses:
            return 0.02  # Conservative if no data
        
        p = len(wins) / len(self.trade_history)  # Probability of win
        q = 1 - p  # Probability of loss
        
        avg_win = statistics.mean([t['pnl'] for t in wins])
        avg_loss = abs(statistics.mean([t['pnl'] for t in losses]))
        
        if avg_loss == 0:
            return 0.02
        
        b = avg_win / avg_loss  # Odds received (risk-reward ratio)
        
        # Kelly Criterion formula
        kelly_fraction = (b * p - q) / b
        
        # Apply safety factor and cap
        safe_kelly = kelly_fraction * self.kelly_fraction
        safe_kelly = max(0.01, min(0.1, safe_kelly))  # Between 1% and 10%
        
        self.logger.debug(f"Kelly Criterion: {kelly_fraction:.3f}, Safe Kelly: {safe_kelly:.3f}")
        
        return safe_kelly
    
    async def _check_portfolio_heat(self, decision: TradeDecision) -> Dict[str, Any]:
        """Check portfolio correlation heat."""
        # Calculate current portfolio heat
        self.portfolio_heat = self._calculate_portfolio_heat()
        
        # Check if adding this trade would exceed correlation limits
        new_heat = self._calculate_new_portfolio_heat(decision)
        
        if new_heat > self.max_correlation_exposure:
            return {
                'approved': False,
                'reason': f"Portfolio heat too high: {new_heat:.2f} > {self.max_correlation_exposure}"
            }
        
        return {'approved': True, 'portfolio_heat': new_heat}
    
    def _calculate_portfolio_heat(self) -> float:
        """Calculate current portfolio correlation heat."""
        if len(self.active_positions) < 2:
            return 0.0
        
        # Simplified correlation calculation
        # In a real implementation, you'd calculate actual correlations
        total_exposure = sum(pos.get('size', 0) for pos in self.active_positions.values())
        
        # Assume some correlation based on position sizes
        heat = min(1.0, total_exposure / 100.0)  # Normalize to 0-1
        
        return heat
    
    def _calculate_new_portfolio_heat(self, decision: TradeDecision) -> float:
        """Calculate portfolio heat if we add this trade."""
        current_heat = self.portfolio_heat
        new_position_size = decision.position_size
        
        # Simplified: assume new position adds to heat
        new_heat = current_heat + (new_position_size / 100.0)
        
        return min(1.0, new_heat)
    
    async def _calculate_volatility_adjusted_size(self, decision: TradeDecision,
                                                technical_indicators: TechnicalIndicators,
                                                market_context: MarketContext) -> float:
        """Calculate volatility-adjusted position size."""
        # Get current volatility
        current_volatility = market_context.volatility
        
        # Get historical volatility for this pair
        pair = decision.recommendation.pair
        if pair not in self.volatility_history:
            self.volatility_history[pair] = []
        
        # Add current volatility to history
        self.volatility_history[pair].append(current_volatility)
        
        # Keep only recent history
        if len(self.volatility_history[pair]) > self.volatility_lookback:
            self.volatility_history[pair] = self.volatility_history[pair][-self.volatility_lookback:]
        
        # Calculate average volatility
        if len(self.volatility_history[pair]) > 0:
            avg_volatility = statistics.mean(self.volatility_history[pair])
        else:
            avg_volatility = current_volatility
        
        # Adjust position size based on volatility
        # Lower volatility = larger positions, Higher volatility = smaller positions
        if avg_volatility == 0:
            volatility_multiplier = 1.0
        else:
            volatility_ratio = current_volatility / avg_volatility
            volatility_multiplier = 1.0 / volatility_ratio
            volatility_multiplier = max(0.5, min(2.0, volatility_multiplier))  # Cap between 0.5 and 2.0
        
        # Use ATR for additional volatility adjustment
        atr = technical_indicators.atr if technical_indicators.atr else 0.001
        atr_multiplier = 1.0 / (atr * 1000)  # Normalize ATR
        atr_multiplier = max(0.5, min(2.0, atr_multiplier))
        
        # Combine volatility adjustments
        final_multiplier = (volatility_multiplier + atr_multiplier) / 2
        
        self.logger.debug(f"Volatility adjustment: {volatility_multiplier:.2f}, "
                         f"ATR adjustment: {atr_multiplier:.2f}, "
                         f"Final: {final_multiplier:.2f}")
        
        return final_multiplier
    
    async def _calculate_time_decay(self, decision: TradeDecision, 
                                  fundamental_analysis: Dict[str, Any]) -> float:
        """Calculate time-based risk decay."""
        # Check for upcoming high-impact events
        high_impact_events = fundamental_analysis.get('high_impact_events', [])
        
        if not high_impact_events:
            return 1.0  # No decay
        
        current_time = datetime.now(timezone.utc)
        min_time_to_event = float('inf')
        
        for event in high_impact_events:
            event_time = event.get('date')
            if event_time:
                if isinstance(event_time, str):
                    try:
                        event_time = datetime.fromisoformat(event_time.replace('Z', '+00:00'))
                    except:
                        continue
                
                time_diff = abs((event_time - current_time).total_seconds() / 3600)  # Hours
                min_time_to_event = min(min_time_to_event, time_diff)
        
        # Calculate decay based on time to event
        if min_time_to_event <= 1:  # Within 1 hour
            return 0.3  # 70% reduction
        elif min_time_to_event <= 4:  # Within 4 hours
            return 0.6  # 40% reduction
        elif min_time_to_event <= 24:  # Within 24 hours
            return 0.8  # 20% reduction
        else:
            return 1.0  # No decay
    
    async def _check_drawdown_risk(self) -> Dict[str, Any]:
        """Check drawdown protection."""
        if self.current_drawdown >= self.max_drawdown:
            return {
                'approved': False,
                'reason': f"Max drawdown reached: {self.current_drawdown:.2%}"
            }
        
        # Check consecutive losses
        if self.current_consecutive_losses >= 5:  # Max 5 consecutive losses
            return {
                'approved': False,
                'reason': f"Too many consecutive losses: {self.current_consecutive_losses}"
            }
        
        return {'approved': True}
    
    def _calculate_final_position_size(self, kelly_size: float, volatility_size: float,
                                     time_decay: float, fundamental_analysis: Dict[str, Any]) -> float:
        """Calculate final position size combining all factors."""
        # Base size from Kelly Criterion
        base_size = kelly_size
        
        # Apply volatility adjustment
        volatility_adjusted = base_size * volatility_size
        
        # Apply time decay
        time_adjusted = volatility_adjusted * time_decay
        
        # Apply fundamental multiplier
        fundamental_multiplier = fundamental_analysis.get('position_size_multiplier', 1.0)
        final_size = time_adjusted * fundamental_multiplier
        
        # Get real account size from OANDA API
        account_size = self._get_account_balance()
        max_position_value = account_size * 0.1  # Max 10% of account per trade
        
        # Convert to position size (simplified)
        position_size = min(final_size, max_position_value / 1000)  # Assume $1000 per unit
        
        return max(0.01, min(0.1, position_size))  # Between 1% and 10%
    
    async def _validate_risk_reward(self, decision: TradeDecision, position_size: float) -> Dict[str, Any]:
        """Validate risk-reward ratio."""
        entry_price = decision.recommendation.entry_price
        stop_loss = decision.modified_stop_loss
        take_profit = decision.modified_take_profit
        
        if not stop_loss or not take_profit:
            return {
                'approved': False,
                'reason': "Missing stop loss or take profit"
            }
        
        # Calculate risk and reward
        risk = abs(float(entry_price - stop_loss))
        reward = abs(float(take_profit - entry_price))
        
        if risk == 0:
            return {
                'approved': False,
                'reason': "Zero risk (invalid stop loss)"
            }
        
        risk_reward_ratio = reward / risk
        
        # Minimum risk-reward ratio
        min_rr_ratio = 1.5
        if risk_reward_ratio < min_rr_ratio:
            return {
                'approved': False,
                'reason': f"Risk-reward ratio too low: {risk_reward_ratio:.2f} < {min_rr_ratio}"
            }
        
        return {'approved': True, 'risk_reward_ratio': risk_reward_ratio}
    
    def _calculate_risk_per_share(self, decision: TradeDecision) -> float:
        """Calculate risk per share/unit."""
        entry_price = decision.recommendation.entry_price
        stop_loss = decision.modified_stop_loss
        
        if not stop_loss:
            return 0.01  # Default 1% risk
        
        risk = abs(float(entry_price - stop_loss))
        return risk
    
    def _calculate_risk_score(self, decision: TradeDecision, position_size: float) -> float:
        """Calculate overall risk score (0-1, lower is better)."""
        risk_score = 0.0
        
        # Position size risk (larger positions = higher risk)
        risk_score += position_size * 0.3
        
        # Market condition risk
        market_condition = decision.recommendation.market_condition.value
        if market_condition == 'news_reactionary':
            risk_score += 0.3
        elif market_condition == 'breakout':
            risk_score += 0.2
        elif market_condition == 'ranging':
            risk_score += 0.1
        
        # Portfolio heat risk
        risk_score += self.portfolio_heat * 0.2
        
        # Drawdown risk
        risk_score += self.current_drawdown * 0.2
        
        return min(1.0, risk_score)
    
    def _calculate_daily_pnl(self) -> float:
        """Calculate current daily P&L."""
        today = datetime.now(timezone.utc).date()
        daily_trades = [t for t in self.trade_history if t['date'].date() == today]
        return sum(t['pnl'] for t in daily_trades)
    
    async def _load_historical_data(self) -> None:
        """Load historical trade data for analysis."""
        # This would load from database or file
        # For now, initialize with empty data
        self.trade_history = []
        self.portfolio_history = []
    
    async def record_trade_result(self, trade_id: str, pair: str, entry_price: Decimal,
                                exit_price: Decimal, position_size: float, pnl: float) -> None:
        """Record trade result for performance tracking."""
        trade_result = {
            'trade_id': trade_id,
            'pair': pair,
            'entry_price': float(entry_price),
            'exit_price': float(exit_price),
            'position_size': position_size,
            'pnl': pnl,
            'date': datetime.now(timezone.utc),
            'win': pnl > 0
        }
        
        self.trade_history.append(trade_result)
        
        # Update performance metrics
        await self._update_performance_metrics()
        
        # Update drawdown
        await self._update_drawdown(pnl)
        
        # Update consecutive losses
        if pnl < 0:
            self.current_consecutive_losses += 1
        else:
            self.current_consecutive_losses = 0
    
    async def _update_performance_metrics(self) -> None:
        """Update performance metrics."""
        if len(self.trade_history) < 5:
            return
        
        wins = [t for t in self.trade_history if t['win']]
        losses = [t for t in self.trade_history if not t['win']]
        
        if wins:
            self.win_rate = len(wins) / len(self.trade_history)
            self.avg_win = statistics.mean([t['pnl'] for t in wins])
        
        if losses:
            self.avg_loss = statistics.mean([t['pnl'] for t in losses])
        
        if self.avg_loss != 0:
            self.profit_factor = abs(self.avg_win / self.avg_loss) if self.avg_win else 0
    
    async def _update_drawdown(self, pnl: float) -> None:
        """Update drawdown tracking."""
        # Update peak equity
        if pnl > 0:
            self.peak_equity = max(self.peak_equity, pnl)
        
        # Calculate current drawdown
        if self.peak_equity > 0:
            self.current_drawdown = (self.peak_equity - pnl) / self.peak_equity
        else:
            self.current_drawdown = 0.0
    
    async def get_risk_summary(self) -> Dict[str, Any]:
        """Get comprehensive risk summary."""
        return {
            'current_drawdown': self.current_drawdown,
            'portfolio_heat': self.portfolio_heat,
            'win_rate': self.win_rate,
            'profit_factor': self.profit_factor,
            'consecutive_losses': self.current_consecutive_losses,
            'daily_pnl': self._calculate_daily_pnl(),
            'active_positions': len(self.active_positions),
            'total_trades': len(self.trade_history)
        } 