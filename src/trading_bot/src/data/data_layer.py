"""
Data Layer - Market Data Collection and Management System.

This module provides comprehensive market data collection, storage, and management
capabilities for the trading bot. It integrates with the OANDA API to fetch real-time
and historical market data, manages data caching, and provides market context analysis.

Key Features:
- Real-time market data collection via OANDA API
- Historical data retrieval and caching
- Multi-timeframe data management
- Market context analysis and volatility calculation
- Data validation and error handling
- Automatic data refresh and updates

Architecture:
- DataLayer: Main class for data collection and management
- OANDA API integration for real market data
- In-memory caching for performance optimization
- Market context generation for decision making

The data layer is a critical component that feeds all other analysis layers
with accurate, up-to-date market information.

Author: Trading Bot Development Team
Version: 2.0.0
Last Updated: 2024
"""
import asyncio
import traceback
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from decimal import Decimal
import random
import sys
from pathlib import Path
import pandas as pd

from ..core.models import CandleData, TimeFrame, MarketContext, MarketCondition
from ..utils.config import Config
from ..utils.logger import get_logger
from .scraping_data_integration import ScrapingDataIntegration

# Import OANDA API
try:
    # Import from the project root using proper relative imports
    import sys
    from pathlib import Path
    
    # Add project root to path for external modules
    project_root = Path(__file__).parent.parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    from api.oanda_api import OandaApi
    from constants import defs
    OANDA_AVAILABLE = True
except ImportError as e:
    OANDA_AVAILABLE = False
    print(f"⚠️ OANDA API not available: {e}")
    print("⚠️ Using mock data")


class DataLayer:
    """
    Market data collection and management system.
    
    This class is responsible for collecting, storing, and managing market data
    from various sources. It provides a unified interface for accessing real-time
    and historical market data, market context analysis, and data caching.
    
    Key Responsibilities:
    - Fetch real-time market data from OANDA API
    - Manage historical data storage and retrieval
    - Provide multi-timeframe data access
    - Generate market context and volatility analysis
    - Handle data validation and error recovery
    - Optimize data access through intelligent caching
    
    Data Storage:
    - _candles: Multi-timeframe candle data storage
    - _market_contexts: Market context cache
    - Real-time data updates and synchronization
    
    The DataLayer is designed to be the single source of truth for all market
    data used by the trading bot's analysis and decision-making components.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the DataLayer with configuration and API setup.
        
        Args:
            config: Configuration object containing API keys and settings
            
        Raises:
            ValueError: If OANDA API key is not provided (real data required)
            
        The initialization process:
        1. Sets up data storage structures
        2. Validates OANDA API availability and credentials
        3. Initializes scraping data integration
        3. Initializes real-time data collection
        4. Prepares for multi-timeframe data management
        """
        self.config = config
        self.logger = get_logger(__name__)
        
        # Data storage structures
        self._candles: Dict[str, Dict[TimeFrame, List[CandleData]]] = {}
        self._market_contexts: Dict[str, MarketContext] = {}
        
        # Initialize scraping data integration
        self.scraping_integration = ScrapingDataIntegration(self.logger)
        self.logger.info("✅ Scraping data integration initialized")
        
        # OANDA API integration - REQUIRED for real data
        if OANDA_AVAILABLE and config.oanda_api_key:
            self.oanda_api = OandaApi()
            self.use_real_data = True
            self.logger.info("✅ Using real OANDA API data")
        else:
            self.logger.error("❌ OANDA API not available - cannot run without real data")
            raise ValueError("OANDA API key required - mock data generation disabled")
        
        # Real data only - no mock data generation
        self._is_running = False
        self._update_task = None
    
    async def _validate_oanda_credentials(self) -> bool:
        """
        Validate OANDA API credentials and connection.
        
        Returns:
            bool: True if credentials are valid and API is accessible
            
        This method ensures that the OANDA API credentials are valid and
        the API is accessible before starting data collection.
        """
        try:
            if self.use_real_data and self.oanda_api:
                return self.oanda_api.validate_credentials()
            return True
        except Exception as e:
            self.logger.error(f"Error validating OANDA credentials: {e}")
            return False

    async def start(self):
        """
        Start the data layer and begin data collection.
        
        This method initializes the data layer by:
        1. Validating OANDA API credentials
        2. Initializing data for all configured trading pairs
        3. Starting the background data update loop
        
        Raises:
            Exception: If OANDA credentials are invalid or initialization fails
        """
        try:
            # Validate OANDA credentials
            if not await self._validate_oanda_credentials():
                raise Exception("Invalid OANDA credentials")
            
            # Initialize data for all trading pairs
            for pair in self.config.trading_pairs:
                await self._initialize_pair_data(pair)
            
            # Start data update loop
            asyncio.create_task(self._data_update_loop())
            
            self.logger.info("✅ Data layer started successfully")
            
        except Exception as e:
            print(f"❌ [DEBUG] Error starting data layer: {e}")
            self.logger.error(f"Error starting data layer: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the data layer."""
        self.logger.info("Stopping data layer...")
        self._is_running = False
        
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Data layer stopped")
    
    async def get_candles(
        self, 
        pair: str, 
        timeframe: TimeFrame, 
        count: int = 100
    ) -> List[CandleData]:
        """Get candle data for a pair and timeframe."""
        
        if self.use_real_data and self.oanda_api:
            return await self._get_real_candles(pair, timeframe, count)
        else:
            self.logger.error("Cannot get candles - OANDA API not available")
            return []
    
    async def get_market_context(self, pair: str) -> MarketContext:
        """Get market context for a pair."""
        return self._market_contexts.get(pair, MarketContext())
    
    async def get_current_price(self, pair: str) -> Optional[Decimal]:
        """
        Get the current market price for a currency pair.
        
        Args:
            pair: Currency pair symbol (e.g., 'EUR_USD')
            
        Returns:
            Optional[Decimal]: Current price or None if unavailable
            
        This method first checks cached data for efficiency, then falls back
        to a real-time API call if needed. The M5 timeframe is used as the
        primary source for current prices.
        """
        # First try to get from cached candle data (most efficient)
        if pair in self._candles and TimeFrame.M5 in self._candles[pair]:
            candles = self._candles[pair][TimeFrame.M5]
            if candles:
                return candles[-1].close
        
        # If no cached data, try real API call
        if self.use_real_data and self.oanda_api:
            return await self._get_real_current_price(pair)
        
        return None
    
    async def _initialize_pair_data(self, pair: str) -> None:
        """Initialize data for a trading pair."""
        print(f"📊 [DEBUG] Initializing data for {pair}")
        self.logger.info(f"Initializing data for {pair}")
        
        # Initialize candle storage
        if pair not in self._candles:
            self._candles[pair] = {}
            print(f"📊 [DEBUG] {pair}: Created candle storage")
        
        # Get historical data for each timeframe
        print(f"📊 [DEBUG] {pair}: Getting data for {len(self.config.timeframes)} timeframes: {[tf.value for tf in self.config.timeframes]}")
        for timeframe in self.config.timeframes:
            print(f"📊 [DEBUG] {pair}: Getting {timeframe.value} data...")
            if self.use_real_data and self.oanda_api:
                # Get real data from API
                print(f"📊 [DEBUG] {pair}: Using real OANDA API data")
                candles = await self._get_real_candles(pair, timeframe, 200)
            else:
                self.logger.error(f"Cannot initialize {pair} - OANDA API not available")
                raise ValueError("OANDA API required for data initialization")
            
            self._candles[pair][timeframe] = candles
            print(f"📊 [DEBUG] {pair}: {timeframe.value} - {len(candles)} candles loaded")
        
        # Initialize market context
        print(f"🌍 [DEBUG] {pair}: Initializing market context...")
        self._market_contexts[pair] = MarketContext(
            condition=MarketCondition.RANGING,
            volatility=0.001,
            trend_strength=0.5,
            news_sentiment=0.0,
            timestamp=datetime.now(timezone.utc)
        )
        print(f"✅ [DEBUG] {pair}: Market context initialized")
    
    
    async def _data_update_loop(self) -> None:
        """Main data update loop."""
        print("🔄 [DEBUG] Data update loop started")
        update_count = 0
        while self._is_running:
            try:
                update_count += 1
                print(f"🔄 [DEBUG] Data update iteration {update_count}")
                await self._update_all_data()
                print(f"⏰ [DEBUG] Waiting {self.config.data_update_frequency} seconds for next update...")
                await asyncio.sleep(self.config.data_update_frequency)
            except Exception as e:
                print(f"❌ [DEBUG] Error in data update loop: {e}")
                print(f"❌ [DEBUG] Traceback: {traceback.format_exc()}")
                self.logger.error(f"Error in data update loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _update_all_data(self) -> None:
        """Update data for all pairs."""
        print(f"📊 [DEBUG] Updating data for {len(self.config.trading_pairs)} pairs")
        for pair in self.config.trading_pairs:
            print(f"📊 [DEBUG] Updating data for {pair}...")
            await self._update_pair_data(pair)
            print(f"✅ [DEBUG] Data updated for {pair}")
    
    async def _update_pair_data(self, pair: str) -> None:
        """Update data for a specific pair."""
        try:
            print(f"📊 [DEBUG] {pair}: Starting data update...")
            
            # Update candles for each timeframe
            for timeframe in self.config.timeframes:
                print(f"📊 [DEBUG] {pair}: Updating {timeframe.value} data...")
                if self.use_real_data and self.oanda_api:
                    # Get fresh real data from API
                    print(f"📊 [DEBUG] {pair}: Getting fresh real data for {timeframe.value}")
                    new_candles = await self._get_real_candles(pair, timeframe, 50)
                    if new_candles:
                        # Replace with fresh data, keeping only the latest candles
                        self._candles[pair][timeframe] = new_candles[-1000:]  # Keep last 1000
                        print(f"📊 [DEBUG] {pair}: {timeframe.value} - Updated with {len(new_candles)} candles")
                    else:
                        print(f"⚠️ [DEBUG] {pair}: {timeframe.value} - No new candles received")
                else:
                    # No new data available - this is normal for real data
                    print(f"📊 [DEBUG] {pair}: {timeframe.value} - No new data available")
            
            # Update market context
            print(f"🌍 [DEBUG] {pair}: Updating market context...")
            await self._update_market_context(pair)
            print(f"✅ [DEBUG] {pair}: Market context updated")
                
        except Exception as e:
            print(f"❌ [DEBUG] {pair}: Error updating data: {e}")
            print(f"❌ [DEBUG] {pair}: Traceback: {traceback.format_exc()}")
            self.logger.error(f"Error updating data for {pair}: {e}")
    
    
    async def _update_market_context(self, pair: str) -> None:
        """Update market context for a pair."""
        try:
            # Get recent candles for analysis
            recent_candles = await self.get_candles(pair, TimeFrame.M5, 20)
            if not recent_candles:
                self.logger.warning(f"No recent candles available for {pair} market context update")
                return
            
            # Calculate volatility
            prices = [float(c.close) for c in recent_candles]
            volatility = self._calculate_volatility(prices)
        
            # Determine market condition
            condition = self._determine_market_condition(recent_candles, volatility)
        
            # Calculate trend strength
            trend_strength = self._calculate_trend_strength(recent_candles)
        
            # Update market context
            self._market_contexts[pair] = MarketContext(
                condition=condition,
                volatility=volatility,
                trend_strength=trend_strength,
                news_sentiment=0.0,  # Real news sentiment would be integrated here
                timestamp=datetime.now(timezone.utc)
            )
            
            # Log market context update
            self.logger.debug(f"📊 Market context updated for {pair}: "
                            f"Condition={condition.value}, "
                            f"Volatility={volatility:.3f}%, "
                            f"Trend Strength={trend_strength:.3f}")
            
        except Exception as e:
            self.logger.error(f"Error updating market context for {pair}: {e}")
    
    def _calculate_volatility(self, prices: List[float]) -> float:
        """Calculate price volatility using standard deviation of returns.
        
        Args:
            prices: List of price values
            
        Returns:
            Volatility as percentage (standard deviation * 100)
        """
        if len(prices) < 2:
            return 0.0
        
        # Calculate percentage returns
        returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
        
        if len(returns) < 2:
            return 0.0
        
        # Calculate standard deviation of returns
        import statistics
        volatility_std = statistics.stdev(returns)
        
        # Convert to percentage (multiply by 100 for display)
        volatility_percentage = volatility_std * 100
        
        # Debug logging
        if len(prices) > 0:
            self.logger.debug(f"Volatility calculation: {len(prices)} prices, "
                            f"range: {min(prices):.5f}-{max(prices):.5f}, "
                            f"returns: {[f'{r:.6f}' for r in returns[:3]]}..., "
                            f"volatility: {volatility_percentage:.6f}%")
        
        return volatility_percentage
    
    def _determine_market_condition(self, candles: List[CandleData], volatility: float) -> MarketCondition:
        """Determine market condition based on price action with market-tested thresholds."""
        # Volatility is in percentage (0.1 = 0.1%)
        # Market-tested thresholds for forex pairs
        
        # Calculate trend strength to improve market condition detection
        trend_strength = self._calculate_trend_strength(candles)
        
        # More realistic volatility thresholds for forex
        if volatility > 0.5:  # > 0.5% - Very high volatility, likely news-driven
            return MarketCondition.NEWS_REACTIONARY
        elif volatility > 0.3:  # > 0.3% - High volatility, potential breakout
            return MarketCondition.BREAKOUT
        elif volatility > 0.2:  # > 0.2% - Moderate volatility, potential reversal
            return MarketCondition.REVERSAL
        elif volatility > 0.1 and trend_strength > 0.6:  # Trending with moderate volatility
            return MarketCondition.TRENDING
        elif volatility > 0.05:  # > 0.05% - Low volatility, ranging
            return MarketCondition.RANGING
        else:  # < 0.05% - Very low volatility, consolidation
            return MarketCondition.CONSOLIDATION
    
    def _calculate_trend_strength(self, candles: List[CandleData]) -> float:
        """Calculate trend strength."""
        if len(candles) < 10:
            return 0.5
        
        # Calculate trend using linear regression slope
        prices = [float(c.close) for c in candles]
        n = len(prices)
        
        if n < 2:
            return 0.0
        
        # Calculate linear regression slope
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(prices) / n
        
        numerator = sum((x[i] - x_mean) * (prices[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0.0
        
        slope = numerator / denominator
        
        # Normalize slope to trend strength (0-1)
        # Use price range to normalize
        price_range = max(prices) - min(prices)
        if price_range == 0:
            return 0.0
        
        # Calculate trend strength based on slope relative to price range
        trend_strength = min(abs(slope * n / price_range), 1.0)
        
        return trend_strength
    
    async def get_all_data(self) -> Dict[str, Dict[TimeFrame, List[CandleData]]]:
        """Get candles data for all pairs and timeframes."""
        result = {}
        
        for pair in self.config.trading_pairs:
            try:
                # Get candles for all timeframes
                candles = {}
                for timeframe in self.config.timeframes:
                    timeframe_candles = await self.get_candles(pair, timeframe, 50)
                    candles[timeframe] = timeframe_candles
                
                result[pair] = candles
                
            except Exception as e:
                self.logger.error(f"Error getting data for {pair}: {e}")
                result[pair] = {}
        
        return result

    async def get_all_pairs_data(self) -> Dict[str, Dict[str, Any]]:
        """Get data for all pairs."""
        result = {}
        
        for pair in self.config.trading_pairs:
            try:
                # Get current price
                current_price = await self.get_current_price(pair)
                
                # Get market context
                market_context = await self.get_market_context(pair)
                
                # Get candles for all timeframes
                candles = {}
                for timeframe in self.config.timeframes:
                    timeframe_candles = await self.get_candles(pair, timeframe, 50)
                    candles[timeframe.value] = timeframe_candles
                
                result[pair] = {
                    'current_price': current_price,
                    'market_context': market_context,
                    'candles': candles
                }
                
            except Exception as e:
                self.logger.error(f"❌ Error getting data for {pair}: {e}")
                result[pair] = {
                    'current_price': None,
                    'market_context': None,
                    'candles': {}
                }
        
        return result

    async def _get_real_candles(self, pair: str, timeframe: TimeFrame, count: int) -> List[CandleData]:
        """Get real candle data from OANDA API."""
        try:
            # Convert TimeFrame enum to OANDA granularity
            granularity_map = {
                TimeFrame.M1: "M1",
                TimeFrame.M5: "M5", 
                TimeFrame.M15: "M15",
                TimeFrame.M30: "M30",
                TimeFrame.H1: "H1",
                TimeFrame.H4: "H4",
                TimeFrame.D1: "D"
            }
            
            granularity = granularity_map.get(timeframe, "M5")
            
            # Fetch candles from OANDA
            candles_data = self.oanda_api.fetch_candles(pair, count=count, granularity=granularity)
            
            if not candles_data:
                self.logger.warning(f"No candle data received for {pair} {timeframe}")
                return []
            
            # Convert OANDA data to CandleData objects
            candles = []
            for candle_data in candles_data:
                if candle_data.get('complete', False):  # Only complete candles
                    candle = CandleData(
                        timestamp=datetime.fromisoformat(candle_data['time'].replace('Z', '+00:00')),
                        open=Decimal(str(candle_data['mid']['o'])),
                        high=Decimal(str(candle_data['mid']['h'])),
                        low=Decimal(str(candle_data['mid']['l'])),
                        close=Decimal(str(candle_data['mid']['c'])),
                        volume=Decimal(str(candle_data.get('volume', 0))),
                        pair=pair,
                        timeframe=timeframe
                    )
                    candles.append(candle)
            
            self.logger.info(f"Fetched {len(candles)} real candles for {pair} {timeframe}")
            return candles
            
        except Exception as e:
            self.logger.error(f"Error fetching real candles for {pair} {timeframe}: {e}")
            return []
    
    async def _get_real_current_price(self, pair: str) -> Optional[Decimal]:
        """Get real current price from OANDA API."""
        try:
            # Get the latest candle to get current price
            candles = await self._get_real_candles(pair, TimeFrame.M5, 1)
            if candles:
                return candles[-1].close
            
            # Fallback: try to get prices endpoint
            prices_data = self.oanda_api.get_prices([pair])
            if prices_data:
                for price_obj in prices_data:
                    if price_obj.instrument == pair:
                        # Use bid price as current price
                        return Decimal(str(price_obj.bid))
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching real current price for {pair}: {e}")
            return None 
    
    # Scraping Data Integration Methods
    
    def get_economic_calendar(self, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """
        Get economic calendar data for the specified number of days ahead
        
        Args:
            days_ahead: Number of days to look ahead (default: 7)
            
        Returns:
            List of economic calendar events
        """
        return self.scraping_integration.get_economic_calendar(days_ahead)
    
    def get_technical_analysis(self, pair_name: str, timeframe: str = "H1") -> Optional[Dict[str, Any]]:
        """
        Get technical analysis data for a specific currency pair
        
        Args:
            pair_name: Currency pair name (e.g., 'EUR_USD')
            timeframe: Timeframe for analysis (default: 'H1')
            
        Returns:
            Technical analysis data or None if failed
        """
        return self.scraping_integration.get_technical_analysis(pair_name, timeframe)
    
    def get_market_sentiment(self) -> pd.DataFrame:
        """
        Get market sentiment data from DailyFX
        
        Returns:
            DataFrame with sentiment data
        """
        return self.scraping_integration.get_market_sentiment()
    
    def get_financial_news(self) -> List[Dict[str, Any]]:
        """
        Get financial news from Bloomberg/Reuters
        
        Returns:
            List of news articles
        """
        return self.scraping_integration.get_financial_news()
    
    def get_comprehensive_market_data(self, pair_name: str, timeframe: str = "H1") -> Dict[str, Any]:
        """
        Get comprehensive market data combining all sources
        
        Args:
            pair_name: Currency pair name
            timeframe: Analysis timeframe
            
        Returns:
            Dictionary with all market data
        """
        return self.scraping_integration.get_comprehensive_market_data(pair_name, timeframe)
    
    def clear_scraping_cache(self) -> None:
        """Clear all cached scraping data"""
        self.scraping_integration.clear_cache()
    
    def get_scraping_cache_status(self) -> Dict[str, Any]:
        """Get scraping cache status information"""
        return self.scraping_integration.get_cache_status()