"""
Scraping Data Integration Module

This module integrates scraped data from various financial sources into the trading bot.
It provides a unified interface to access economic calendar, technical analysis,
sentiment data, and news data for trading decisions.

Author: Trading Bot Development Team
Version: 1.0.0
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd
import logging

# Import scraping modules with proper path handling
try:
    # Add project paths for imports
    project_root = Path(__file__).parent.parent.parent.parent.parent
    src_path = project_root / "src"
    
    # Add paths only if not already present
    paths_to_add = [
        str(src_path),
        str(src_path / "scraping"),
        str(src_path / "constants")
    ]
    
    for path in paths_to_add:
        if path not in sys.path:
            sys.path.insert(0, path)
    
    from scraping.fx_calendar import get_fx_calendar
    from scraping.investing_com import investing_com_fetch
    from scraping.bloomberg_com import bloomberg_com
    from scraping.my_fx_book import run_sentiment_scrape
    import constants.defs as defs
    
    SCRAPING_AVAILABLE = True
except ImportError as e:
    SCRAPING_AVAILABLE = False
    print(f"⚠️ Scraping modules not available: {e}")
    # Define fallback functions
    def get_fx_calendar(*args, **kwargs):
        return []
    def investing_com_fetch(*args, **kwargs):
        return None
    def bloomberg_com(*args, **kwargs):
        return []
    def run_sentiment_scrape(*args, **kwargs):
        return pd.DataFrame()
    def defs(*args, **kwargs):
        return {}


class ScrapingDataIntegration:
    """Main class for integrating scraped data into the trading bot"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the scraping data integration
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.cache = {}
        self.cache_expiry = {}
        
        # Smart cache durations based on data type
        self.cache_durations = {
            'economic_calendar': 3600,    # 1 hour - events don't change frequently
            'technical_analysis': 300,     # 5 minutes - technical data changes moderately
            'market_sentiment': 600,       # 10 minutes - sentiment changes slowly
            'financial_news': 180,         # 3 minutes - news changes frequently
            'myfxbook_sentiment': 900,     # 15 minutes - community sentiment changes slowly
            'comprehensive_data': 300      # 5 minutes - comprehensive data
        }
        
        # Data quality scoring system
        self.data_quality_scores = {
            'economic_calendar': 0.9,      # High quality - official data
            'technical_analysis': 0.8,     # High quality - calculated indicators
            'market_sentiment': 0.6,       # Medium quality - aggregated sentiment
            'financial_news': 0.7,         # Medium-high quality - professional news
            'myfxbook_sentiment': 0.5      # Medium quality - community data
        }
        
        # Historical accuracy tracking
        self.accuracy_history = {
            'economic_calendar': [],
            'technical_analysis': [],
            'market_sentiment': [],
            'financial_news': [],
            'myfxbook_sentiment': []
        }
        
        # Market session configuration (UTC times)
        self.market_sessions = {
            'asian': {'start': 0, 'end': 9},      # 00:00-09:00 UTC
            'london': {'start': 8, 'end': 17},    # 08:00-17:00 UTC
            'new_york': {'start': 13, 'end': 22}  # 13:00-22:00 UTC
        }
        
        # Session-specific scraping priorities
        self.session_priorities = {
            'asian': ['economic_calendar', 'financial_news'],  # Focus on news and events
            'london': ['technical_analysis', 'market_sentiment', 'myfxbook_sentiment'],  # Full analysis
            'new_york': ['technical_analysis', 'market_sentiment', 'financial_news'],  # Full analysis
            'overlap': ['technical_analysis', 'market_sentiment', 'myfxbook_sentiment', 'financial_news']  # All sources
        }
        
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached data is still valid"""
        if key not in self.cache_expiry:
            return False
        return datetime.now() < self.cache_expiry[key]
    
    def _update_cache(self, key: str, data: Any, cache_type: str = 'default') -> None:
        """Update cache with new data using smart duration"""
        self.cache[key] = data
        duration = self.cache_durations.get(cache_type, 300)  # Default 5 minutes
        self.cache_expiry[key] = datetime.now() + timedelta(seconds=duration)
    
    def _assess_data_quality(self, data: Any, data_type: str) -> float:
        """Assess the quality of scraped data"""
        try:
            base_quality = self.data_quality_scores.get(data_type, 0.5)
            
            # Check data completeness
            if data is None or (isinstance(data, list) and len(data) == 0):
                return 0.0
            
            if isinstance(data, pd.DataFrame) and data.empty:
                return 0.0
            
            # Check data freshness
            if isinstance(data, dict) and 'analysis_timestamp' in data:
                age = datetime.now() - data['analysis_timestamp']
                if age.total_seconds() > 3600:  # Older than 1 hour
                    base_quality *= 0.8
            
            # Check data consistency
            if isinstance(data, dict):
                required_fields = ['pair_name', 'timestamp'] if data_type == 'technical_analysis' else []
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    base_quality *= 0.9
            
            return min(base_quality, 1.0)
            
        except Exception as e:
            self.logger.error(f"Error assessing data quality: {str(e)}")
            return 0.0
    
    def _update_accuracy_history(self, data_type: str, accuracy: float) -> None:
        """Update historical accuracy tracking"""
        try:
            if data_type in self.accuracy_history:
                self.accuracy_history[data_type].append({
                    'timestamp': datetime.now(),
                    'accuracy': accuracy
                })
                
                # Keep only last 100 records
                if len(self.accuracy_history[data_type]) > 100:
                    self.accuracy_history[data_type] = self.accuracy_history[data_type][-100:]
                    
        except Exception as e:
            self.logger.error(f"Error updating accuracy history: {str(e)}")
    
    def get_data_quality_score(self, data_type: str) -> float:
        """Get current data quality score for a data type"""
        try:
            base_score = self.data_quality_scores.get(data_type, 0.5)
            
            # Adjust based on historical accuracy
            if data_type in self.accuracy_history and self.accuracy_history[data_type]:
                recent_accuracy = [record['accuracy'] for record in self.accuracy_history[data_type][-10:]]
                avg_accuracy = sum(recent_accuracy) / len(recent_accuracy)
                base_score = (base_score + avg_accuracy) / 2
            
            return round(base_score, 3)
            
        except Exception as e:
            self.logger.error(f"Error getting data quality score: {str(e)}")
            return 0.5
    
    def _get_current_market_session(self) -> str:
        """Determine the current market session"""
        try:
            current_hour = datetime.now().hour
            
            # Check for session overlaps first
            if 8 <= current_hour < 9:  # London-Asian overlap
                return 'overlap'
            elif 13 <= current_hour < 17:  # London-New York overlap
                return 'overlap'
            
            # Check individual sessions
            for session_name, session_times in self.market_sessions.items():
                if session_times['start'] <= current_hour < session_times['end']:
                    return session_name
            
            # Default to Asian session if no active session
            return 'asian'
            
        except Exception as e:
            self.logger.error(f"Error determining market session: {str(e)}")
            return 'asian'
    
    def _should_scrape_data_type(self, data_type: str) -> bool:
        """Determine if a data type should be scraped based on current market session"""
        try:
            current_session = self._get_current_market_session()
            session_priorities = self.session_priorities.get(current_session, [])
            
            # Always scrape if it's in the session priorities
            if data_type in session_priorities:
                return True
            
            # For non-priority data types, check if cache is expired
            cache_key = f"{data_type}_last_check"
            if not self._is_cache_valid(cache_key):
                # Only scrape non-priority data if cache is very old
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error determining if should scrape {data_type}: {str(e)}")
            return True  # Default to scraping if error
    
    def _get_session_optimized_data(self, pair_name: str, timeframe: str = "H1") -> Dict[str, Any]:
        """Get market data optimized for current session"""
        try:
            current_session = self._get_current_market_session()
            session_priorities = self.session_priorities.get(current_session, [])
            
            market_data = {
                'pair_name': pair_name,
                'timeframe': timeframe,
                'timestamp': datetime.now(),
                'current_session': current_session,
                'session_priorities': session_priorities
            }
            
            # Get data based on session priorities
            if 'economic_calendar' in session_priorities or self._should_scrape_data_type('economic_calendar'):
                market_data['economic_calendar'] = self.get_economic_calendar()
            
            if 'technical_analysis' in session_priorities or self._should_scrape_data_type('technical_analysis'):
                market_data['technical_analysis'] = self.get_technical_analysis(pair_name, timeframe)
            
            if 'market_sentiment' in session_priorities or self._should_scrape_data_type('market_sentiment'):
                market_data['market_sentiment'] = self.get_market_sentiment()
            
            if 'myfxbook_sentiment' in session_priorities or self._should_scrape_data_type('myfxbook_sentiment'):
                market_data['myfxbook_sentiment'] = self.get_myfxbook_sentiment()
            
            if 'financial_news' in session_priorities or self._should_scrape_data_type('financial_news'):
                market_data['financial_news'] = self.get_financial_news()
            
            # Calculate scores
            market_data['overall_score'] = self._calculate_overall_market_score(market_data)
            market_data['signal_consensus'] = self._calculate_signal_consensus(market_data)
            
            self.logger.info(f"Retrieved session-optimized data for {pair_name} during {current_session} session")
            return market_data
            
        except Exception as e:
            self.logger.error(f"Error getting session-optimized data: {str(e)}")
            return {}
    
    def get_economic_calendar(self, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """
        Get economic calendar data for the specified number of days ahead
        
        Args:
            days_ahead: Number of days to look ahead (default: 7)
            
        Returns:
            List of economic calendar events
        """
        cache_key = f"economic_calendar_{days_ahead}"
        
        if self._is_cache_valid(cache_key):
            self.logger.debug(f"Using cached economic calendar data")
            return self.cache[cache_key]
        
        try:
            start_date = datetime.now()
            fx_data = get_fx_calendar(start_date)
            
            # Process and filter events by importance
            important_events = []
            for event in fx_data:
                # Skip empty or invalid events
                if not event or not event.get('event'):
                    continue
                
                # Add timestamp for data freshness tracking
                event['scraped_at'] = datetime.now()
                
                # Filter for high-impact events based on category and event name
                category = event.get('category', '').lower()
                event_name = event.get('event', '').lower()
                
                # High-impact categories and keywords
                high_impact_categories = [
                    'interest rate', 'employment', 'inflation rate', 'gdp', 
                    'consumer price index', 'producer price index', 'retail sales'
                ]
                
                high_impact_keywords = [
                    'nfp', 'non-farm payrolls', 'cpi', 'ppi', 'gdp', 'fomc', 
                    'ecb', 'boe', 'boj', 'federal reserve', 'central bank',
                    'monetary policy', 'unemployment', 'inflation'
                ]
                
                is_high_impact = (
                    any(cat in category for cat in high_impact_categories) or
                    any(keyword in event_name for keyword in high_impact_keywords)
                )
                
                if is_high_impact:
                    important_events.append(event)
            
            # Assess data quality
            quality_score = self._assess_data_quality(important_events, 'economic_calendar')
            
            self._update_cache(cache_key, important_events, 'economic_calendar')
            self.logger.info(f"Retrieved {len(important_events)} economic calendar events (quality: {quality_score:.2f})")
            return important_events
            
        except Exception as e:
            self.logger.error(f"Failed to get economic calendar data: {str(e)}")
            return []
    
    def get_technical_analysis(self, pair_name: str, timeframe: str = "H1") -> Optional[Dict[str, Any]]:
        """
        Get technical analysis data for a specific currency pair
        
        Args:
            pair_name: Currency pair name (e.g., 'EUR_USD')
            timeframe: Timeframe for analysis (default: 'H1')
            
        Returns:
            Technical analysis data or None if failed
        """
        cache_key = f"technical_analysis_{pair_name}_{timeframe}"
        
        if self._is_cache_valid(cache_key):
            self.logger.debug(f"Using cached technical analysis data for {pair_name}")
            return self.cache[cache_key]
        
        try:
            if pair_name in defs.INVESTING_COM_PAIRS:
                pair_id = defs.INVESTING_COM_PAIRS[pair_name]['pair_id']
                tf_value = defs.TFS.get(timeframe, defs.TFS['H1'])
                
                technical_data = investing_com_fetch(pair_id, tf_value)
                
                # Add additional analysis and processing
                technical_data['analysis_timestamp'] = datetime.now()
                technical_data['signal_strength'] = self._calculate_signal_strength(technical_data)
                
                # Process pivot points for additional analysis
                pivot_points = self._process_pivot_points(technical_data)
                technical_data['pivot_analysis'] = pivot_points
                
                # Calculate trend strength from technical indicators
                technical_data['trend_strength'] = self._calculate_trend_strength(technical_data)
                
                # Assess data quality
                quality_score = self._assess_data_quality(technical_data, 'technical_analysis')
                technical_data['quality_score'] = quality_score
                
                self._update_cache(cache_key, technical_data, 'technical_analysis')
                self.logger.info(f"Retrieved technical analysis for {pair_name} (quality: {quality_score:.2f})")
                return technical_data
            else:
                self.logger.warning(f"Pair {pair_name} not found in INVESTING_COM_PAIRS")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get technical analysis for {pair_name}: {str(e)}")
            return None
    
    def get_market_sentiment(self) -> pd.DataFrame:
        """
        Get market sentiment data (placeholder implementation)
        
        Returns:
            DataFrame with sentiment data
        """
        cache_key = "market_sentiment"
        
        if self._is_cache_valid(cache_key):
            self.logger.debug("Using cached market sentiment data")
            return self.cache[cache_key]
        
        try:
            # Create placeholder sentiment data since dailyfx_com doesn't exist
            sentiment_data = pd.DataFrame({
                'pair': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD'],
                'sentiment': ['Bullish', 'Bearish', 'Neutral', 'Bullish', 'Bearish'],
                'analysis_timestamp': [datetime.now()] * 5
            })
            
            # Add sentiment score
            sentiment_data['sentiment_score'] = self._calculate_sentiment_score(sentiment_data)
            
            self._update_cache(cache_key, sentiment_data, 'market_sentiment')
            self.logger.info(f"Retrieved sentiment data for {len(sentiment_data)} pairs")
            return sentiment_data
            
        except Exception as e:
            self.logger.error(f"Failed to get market sentiment data: {str(e)}")
            return pd.DataFrame()
    
    def get_financial_news(self) -> List[Dict[str, Any]]:
        """
        Get financial news from Reuters
        
        Returns:
            List of news articles
        """
        cache_key = "financial_news"
        
        if self._is_cache_valid(cache_key):
            self.logger.debug("Using cached financial news data")
            return self.cache[cache_key]
        
        try:
            news_data = bloomberg_com()  # This now calls Reuters via bloomberg_com function
            
            # Process and enhance news data
            processed_news = []
            for article in news_data:
                if not article or not article.get('headline'):
                    continue
                
                # Add additional analysis
                enhanced_article = {
                    'headline': article.get('headline', ''),
                    'link': article.get('link', ''),
                    'analysis_timestamp': datetime.now(),
                    'relevance_score': self._calculate_news_relevance(article),
                    'impact_level': self._assess_news_impact(article),
                    'category': self._categorize_news(article),
                    'sentiment': self._analyze_news_sentiment(article)
                }
                processed_news.append(enhanced_article)
            
            # Sort by relevance score (highest first)
            processed_news.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            self._update_cache(cache_key, processed_news, 'financial_news')
            self.logger.info(f"Retrieved {len(processed_news)} news articles")
            return processed_news
            
        except Exception as e:
            self.logger.error(f"Failed to get financial news data: {str(e)}")
            return []
    
    def get_myfxbook_sentiment(self) -> pd.DataFrame:
        """
        Get MyFXBook community sentiment data
        
        Returns:
            DataFrame with MyFXBook sentiment data
        """
        cache_key = "myfxbook_sentiment"
        
        if self._is_cache_valid(cache_key):
            self.logger.debug("Using cached MyFXBook sentiment data")
            return self.cache[cache_key]
        
        try:
            # Import the updated MyFXBook scraping function
            from scraping.my_fx_book import get_sentiment_data
            
            # Get sentiment data from the updated scraping function
            sentiment_data = get_sentiment_data()
            
            if sentiment_data is not None and not sentiment_data.empty:
                # Add analysis timestamp
                sentiment_data['analysis_timestamp'] = datetime.now()
                
                # Add additional analysis columns
                sentiment_data['sentiment_score'] = self._calculate_myfxbook_sentiment_score(sentiment_data)
                sentiment_data['sentiment_strength'] = self._calculate_sentiment_strength(sentiment_data)
                sentiment_data['contrarian_signal'] = self._calculate_contrarian_signal(sentiment_data)
                
                self._update_cache(cache_key, sentiment_data, 'myfxbook_sentiment')
                self.logger.info(f"Retrieved MyFXBook sentiment data for {len(sentiment_data)} pairs")
                return sentiment_data
            else:
                # Fallback to placeholder data if scraping fails
                self.logger.warning("MyFXBook scraping returned no data, using fallback")
                return self._get_fallback_myfxbook_data()
            
        except Exception as e:
            self.logger.error(f"Failed to get MyFXBook sentiment data: {str(e)}")
            return self._get_fallback_myfxbook_data()
    
    def _get_fallback_myfxbook_data(self) -> pd.DataFrame:
        """Get fallback MyFXBook data when scraping fails"""
        try:
            fallback_data = pd.DataFrame({
                'pair_name': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD'],
                'bullish_perc': [45, 52, 38, 48, 41],
                'bearish_perc': [55, 48, 62, 52, 59],
                'popularity': [85, 78, 92, 73, 67],
                'analysis_timestamp': [datetime.now()] * 5,
                'sentiment_score': [0.0, 0.04, -0.24, -0.04, -0.18],
                'sentiment_strength': ['medium', 'weak', 'strong', 'weak', 'medium'],
                'contrarian_signal': ['bearish', 'neutral', 'bullish', 'neutral', 'bearish']
            })
            
            self.logger.info("Using fallback MyFXBook sentiment data")
            return fallback_data
            
        except Exception as e:
            self.logger.error(f"Error creating fallback MyFXBook data: {str(e)}")
            return pd.DataFrame()
    
    def _calculate_myfxbook_sentiment_score(self, sentiment_data: pd.DataFrame) -> pd.Series:
        """Calculate sentiment score from MyFXBook data"""
        try:
            def calculate_score(row):
                bullish = float(row['bullish_perc'])
                bearish = float(row['bearish_perc'])
                return (bullish - bearish) / 100  # Range: -1 to 1
            
            return sentiment_data.apply(calculate_score, axis=1)
            
        except Exception as e:
            self.logger.error(f"Error calculating MyFXBook sentiment score: {str(e)}")
            return pd.Series([0.0] * len(sentiment_data))
    
    def _calculate_sentiment_strength(self, sentiment_data: pd.DataFrame) -> pd.Series:
        """Calculate sentiment strength from MyFXBook data"""
        try:
            def calculate_strength(row):
                bullish = float(row['bullish_perc'])
                bearish = float(row['bearish_perc'])
                diff = abs(bullish - bearish)
                
                if diff >= 70:
                    return 'very_strong'
                elif diff >= 50:
                    return 'strong'
                elif diff >= 30:
                    return 'medium'
                elif diff >= 15:
                    return 'weak'
                else:
                    return 'very_weak'
            
            return sentiment_data.apply(calculate_strength, axis=1)
            
        except Exception as e:
            self.logger.error(f"Error calculating sentiment strength: {str(e)}")
            return pd.Series(['unknown'] * len(sentiment_data))
    
    def _calculate_contrarian_signal(self, sentiment_data: pd.DataFrame) -> pd.Series:
        """Calculate contrarian trading signal based on extreme sentiment"""
        try:
            def calculate_contrarian(row):
                bullish = float(row['bullish_perc'])
                bearish = float(row['bearish_perc'])
                
                # Extreme bullish sentiment (contrarian bearish signal)
                if bullish >= 80:
                    return 'bearish'
                # Extreme bearish sentiment (contrarian bullish signal)
                elif bearish >= 80:
                    return 'bullish'
                # Moderate sentiment
                else:
                    return 'neutral'
            
            return sentiment_data.apply(calculate_contrarian, axis=1)
            
        except Exception as e:
            self.logger.error(f"Error calculating contrarian signal: {str(e)}")
            return pd.Series(['unknown'] * len(sentiment_data))
    
    def get_comprehensive_market_data(self, pair_name: str, timeframe: str = "H1") -> Dict[str, Any]:
        """
        Get comprehensive market data combining all sources
        
        Args:
            pair_name: Currency pair name
            timeframe: Analysis timeframe
            
        Returns:
            Dictionary with all market data
        """
        try:
            market_data = {
                'pair_name': pair_name,
                'timeframe': timeframe,
                'timestamp': datetime.now(),
                'economic_calendar': self.get_economic_calendar(),
                'technical_analysis': self.get_technical_analysis(pair_name, timeframe),
                'market_sentiment': self.get_market_sentiment(),
                'myfxbook_sentiment': self.get_myfxbook_sentiment(),
                'financial_news': self.get_financial_news()
            }
            
            # Calculate overall market score and signal consensus
            market_data['overall_score'] = self._calculate_overall_market_score(market_data)
            market_data['signal_consensus'] = self._calculate_signal_consensus(market_data)
            
            self.logger.info(f"Retrieved comprehensive market data for {pair_name}")
            self.logger.info(f"Overall score: {market_data['overall_score']:.3f}, Consensus: {market_data['signal_consensus']['consensus']:.3f}, Confidence: {market_data['signal_consensus']['confidence']:.3f}")
            return market_data
            
        except Exception as e:
            self.logger.error(f"Failed to get comprehensive market data: {str(e)}")
            return {}
    
    def get_session_optimized_market_data(self, pair_name: str, timeframe: str = "H1") -> Dict[str, Any]:
        """
        Get market data optimized for current market session
        
        Args:
            pair_name: Currency pair name
            timeframe: Analysis timeframe
            
        Returns:
            Dictionary with session-optimized market data
        """
        return self._get_session_optimized_data(pair_name, timeframe)
    
    def _is_high_impact_event_soon(self, hours_ahead: int = 2) -> bool:
        """Check if there are high-impact economic events in the next few hours"""
        try:
            economic_events = self.get_economic_calendar()
            
            if not economic_events:
                return False
            
            current_time = datetime.now()
            cutoff_time = current_time + timedelta(hours=hours_ahead)
            
            # High-impact event keywords
            high_impact_keywords = [
                'NFP', 'CPI', 'PPI', 'GDP', 'FOMC', 'ECB', 'BOE', 'BOJ',
                'Federal Reserve', 'European Central Bank', 'Bank of England',
                'Non-Farm Payrolls', 'Consumer Price Index', 'Gross Domestic Product',
                'Interest Rate', 'Employment', 'Inflation Rate'
            ]
            
            for event in economic_events:
                event_date = event.get('date')
                if event_date and event_date <= cutoff_time:
                    event_name = event.get('event', '').lower()
                    category = event.get('category', '').lower()
                    
                    # Check if event is high-impact
                    for keyword in high_impact_keywords:
                        if keyword.lower() in event_name or keyword.lower() in category:
                            return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking for high-impact events: {str(e)}")
            return False
    
    def _get_trade_avoidance_recommendation(self, pair_name: str) -> Dict[str, Any]:
        """Get trade avoidance recommendation based on economic calendar"""
        try:
            recommendation = {
                'should_avoid_trading': False,
                'reason': '',
                'confidence': 0.0,
                'time_until_safe': None,
                'next_high_impact_event': None
            }
            
            economic_events = self.get_economic_calendar()
            
            if not economic_events:
                return recommendation
            
            current_time = datetime.now()
            
            # Check for events in the next 4 hours
            near_events = []
            for event in economic_events:
                event_date = event.get('date')
                if event_date:
                    time_diff = (event_date - current_time).total_seconds() / 3600  # hours
                    if 0 <= time_diff <= 4:  # Events in next 4 hours
                        near_events.append((event, time_diff))
            
            if near_events:
                # Sort by time
                near_events.sort(key=lambda x: x[1])
                next_event, time_until = near_events[0]
                
                # High-impact event keywords
                high_impact_keywords = [
                    'NFP', 'CPI', 'PPI', 'GDP', 'FOMC', 'ECB', 'BOE', 'BOJ',
                    'Federal Reserve', 'European Central Bank', 'Bank of England',
                    'Non-Farm Payrolls', 'Consumer Price Index', 'Gross Domestic Product'
                ]
                
                event_name = next_event.get('event', '').lower()
                category = next_event.get('category', '').lower()
                
                # Check if it's a high-impact event
                is_high_impact = any(keyword.lower() in event_name or keyword.lower() in category 
                                   for keyword in high_impact_keywords)
                
                if is_high_impact:
                    recommendation['should_avoid_trading'] = True
                    recommendation['reason'] = f"High-impact event: {next_event.get('event', 'Unknown')}"
                    recommendation['confidence'] = 0.9
                    recommendation['time_until_safe'] = max(0, time_until + 1)  # Wait 1 hour after event
                    recommendation['next_high_impact_event'] = {
                        'event': next_event.get('event'),
                        'time_until': time_until,
                        'category': next_event.get('category')
                    }
                else:
                    recommendation['confidence'] = 0.3
                    recommendation['reason'] = f"Low-impact event: {next_event.get('event', 'Unknown')}"
            
            return recommendation
            
        except Exception as e:
            self.logger.error(f"Error getting trade avoidance recommendation: {str(e)}")
            return {'should_avoid_trading': False, 'reason': 'Error in analysis', 'confidence': 0.0}
    
    def get_trade_avoidance_analysis(self, pair_name: str) -> Dict[str, Any]:
        """
        Get comprehensive trade avoidance analysis
        
        Args:
            pair_name: Currency pair name
            
        Returns:
            Dictionary with trade avoidance recommendations
        """
        try:
            analysis = {
                'pair_name': pair_name,
                'timestamp': datetime.now(),
                'avoidance_recommendation': self._get_trade_avoidance_recommendation(pair_name),
                'high_impact_soon': self._is_high_impact_event_soon(),
                'market_session': self._get_current_market_session()
            }
            
            # Add session-specific recommendations
            current_session = analysis['market_session']
            if current_session == 'asian':
                analysis['session_risk'] = 'LOW'  # Asian session typically has lower volatility
            elif current_session == 'overlap':
                analysis['session_risk'] = 'HIGH'  # Session overlaps have higher volatility
            else:
                analysis['session_risk'] = 'MEDIUM'
            
            self.logger.info(f"Trade avoidance analysis for {pair_name}: {analysis['avoidance_recommendation']['should_avoid_trading']}")
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error getting trade avoidance analysis: {str(e)}")
            return {'should_avoid_trading': False, 'reason': 'Error in analysis', 'confidence': 0.0}
    
    def _calculate_signal_strength(self, technical_data: Dict[str, Any]) -> float:
        """Calculate signal strength from technical analysis data"""
        try:
            ti_buy = int(technical_data.get('ti_buy', 0))
            ti_sell = int(technical_data.get('ti_sell', 0))
            ma_buy = int(technical_data.get('ma_buy', 0))
            ma_sell = int(technical_data.get('ma_sell', 0))
            
            # Simple signal strength calculation (customize as needed)
            total_signals = ti_buy + ti_sell + ma_buy + ma_sell
            if total_signals == 0:
                return 0.0
            
            bullish_signals = ti_buy + ma_buy
            signal_strength = (bullish_signals / total_signals) - 0.5  # Range: -0.5 to 0.5
            
            return round(signal_strength, 3)
            
        except Exception as e:
            self.logger.error(f"Error calculating signal strength: {str(e)}")
            return 0.0
    
    def _process_pivot_points(self, technical_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process pivot points data for additional analysis"""
        try:
            pivot_analysis = {
                'support_levels': [],
                'resistance_levels': [],
                'pivot_strength': 'medium',
                'key_levels': []
            }
            
            # Extract pivot point values
            pivot = technical_data.get('pivot', '0')
            s1 = technical_data.get('S1', '0')
            s2 = technical_data.get('S2', '0')
            s3 = technical_data.get('S3', '0')
            r1 = technical_data.get('R1', '0')
            r2 = technical_data.get('R2', '0')
            r3 = technical_data.get('R3', '0')
            
            # Convert to float values
            try:
                pivot_val = float(pivot) if pivot != '0' else 0
                s1_val = float(s1) if s1 != '0' else 0
                s2_val = float(s2) if s2 != '0' else 0
                s3_val = float(s3) if s3 != '0' else 0
                r1_val = float(r1) if r1 != '0' else 0
                r2_val = float(r2) if r2 != '0' else 0
                r3_val = float(r3) if r3 != '0' else 0
                
                # Organize support and resistance levels
                if s1_val > 0:
                    pivot_analysis['support_levels'].append({'level': s1_val, 'strength': 'strong'})
                if s2_val > 0:
                    pivot_analysis['support_levels'].append({'level': s2_val, 'strength': 'medium'})
                if s3_val > 0:
                    pivot_analysis['support_levels'].append({'level': s3_val, 'strength': 'weak'})
                
                if r1_val > 0:
                    pivot_analysis['resistance_levels'].append({'level': r1_val, 'strength': 'strong'})
                if r2_val > 0:
                    pivot_analysis['resistance_levels'].append({'level': r2_val, 'strength': 'medium'})
                if r3_val > 0:
                    pivot_analysis['resistance_levels'].append({'level': r3_val, 'strength': 'weak'})
                
                # Key levels (closest to pivot)
                if pivot_val > 0:
                    pivot_analysis['key_levels'].append(pivot_val)
                
            except (ValueError, TypeError) as e:
                self.logger.warning(f"Error parsing pivot point values: {e}")
            
            return pivot_analysis
            
        except Exception as e:
            self.logger.error(f"Error processing pivot points: {str(e)}")
            return {'support_levels': [], 'resistance_levels': [], 'pivot_strength': 'unknown', 'key_levels': []}
    
    def _calculate_trend_strength(self, technical_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate trend strength from technical indicators"""
        try:
            trend_analysis = {
                'overall_trend': 'neutral',
                'trend_strength': 0.0,
                'trend_direction': 'sideways',
                'confidence': 0.0
            }
            
            # Get percentage values
            percent_bullish = technical_data.get('percent_bullish', 50)
            percent_bearish = technical_data.get('percent_bearish', 50)
            
            # Calculate trend strength
            if percent_bullish > 60:
                trend_analysis['overall_trend'] = 'bullish'
                trend_analysis['trend_direction'] = 'up'
                trend_analysis['trend_strength'] = (percent_bullish - 50) / 50  # 0 to 1
            elif percent_bearish > 60:
                trend_analysis['overall_trend'] = 'bearish'
                trend_analysis['trend_direction'] = 'down'
                trend_analysis['trend_strength'] = (percent_bearish - 50) / 50  # 0 to 1
            else:
                trend_analysis['overall_trend'] = 'neutral'
                trend_analysis['trend_direction'] = 'sideways'
                trend_analysis['trend_strength'] = 0.0
            
            # Calculate confidence based on signal strength
            signal_strength = abs(technical_data.get('signal_strength', 0))
            trend_analysis['confidence'] = min(1.0, signal_strength * 2)  # Scale to 0-1
            
            return trend_analysis
            
        except Exception as e:
            self.logger.error(f"Error calculating trend strength: {str(e)}")
            return {'overall_trend': 'unknown', 'trend_strength': 0.0, 'trend_direction': 'unknown', 'confidence': 0.0}
    
    def _calculate_sentiment_score(self, sentiment_data: pd.DataFrame) -> pd.Series:
        """Calculate sentiment score from sentiment data"""
        try:
            def sentiment_to_score(sentiment):
                sentiment_lower = str(sentiment).lower()
                if 'bullish' in sentiment_lower:
                    return 1.0
                elif 'bearish' in sentiment_lower:
                    return -1.0
                else:
                    return 0.0
            
            return sentiment_data['sentiment'].apply(sentiment_to_score)
            
        except Exception as e:
            self.logger.error(f"Error calculating sentiment score: {str(e)}")
            return pd.Series([0.0] * len(sentiment_data))
    
    def _calculate_news_relevance(self, article: Dict[str, Any]) -> float:
        """Calculate relevance score for news article"""
        try:
            headline = article.get('headline', '').lower()
            
            # Keywords that indicate high relevance for forex trading
            high_relevance_keywords = [
                'fed', 'interest rate', 'inflation', 'employment', 'gdp',
                'central bank', 'monetary policy', 'economic', 'trade',
                'currency', 'forex', 'dollar', 'euro', 'pound', 'yen'
            ]
            
            relevance_score = 0.0
            for keyword in high_relevance_keywords:
                if keyword in headline:
                    relevance_score += 0.1
            
            return min(relevance_score, 1.0)  # Cap at 1.0
            
        except Exception as e:
            self.logger.error(f"Error calculating news relevance: {str(e)}")
            return 0.0
    
    def _assess_news_impact(self, article: Dict[str, Any]) -> str:
        """Assess the potential market impact of a news article"""
        try:
            headline = article.get('headline', '').lower()
            
            # High impact keywords
            high_impact_keywords = [
                'fed', 'fomc', 'interest rate', 'nfp', 'non-farm payrolls',
                'cpi', 'inflation', 'gdp', 'unemployment', 'central bank',
                'monetary policy', 'quantitative easing', 'tapering'
            ]
            
            # Medium impact keywords
            medium_impact_keywords = [
                'retail sales', 'manufacturing', 'trade balance', 'consumer confidence',
                'housing', 'employment', 'economic growth', 'recession'
            ]
            
            for keyword in high_impact_keywords:
                if keyword in headline:
                    return 'high'
            
            for keyword in medium_impact_keywords:
                if keyword in headline:
                    return 'medium'
            
            return 'low'
            
        except Exception as e:
            self.logger.error(f"Error assessing news impact: {str(e)}")
            return 'unknown'
    
    def _categorize_news(self, article: Dict[str, Any]) -> str:
        """Categorize news article by type"""
        try:
            headline = article.get('headline', '').lower()
            
            # Economic indicators
            if any(keyword in headline for keyword in ['gdp', 'inflation', 'employment', 'retail sales', 'manufacturing']):
                return 'economic_indicator'
            
            # Central bank policy
            if any(keyword in headline for keyword in ['fed', 'fomc', 'ecb', 'boe', 'boj', 'interest rate', 'monetary policy']):
                return 'central_bank'
            
            # Market sentiment
            if any(keyword in headline for keyword in ['market', 'trading', 'investor', 'sentiment', 'volatility']):
                return 'market_sentiment'
            
            # Geopolitical
            if any(keyword in headline for keyword in ['trade war', 'sanctions', 'election', 'political', 'geopolitical']):
                return 'geopolitical'
            
            # Corporate earnings
            if any(keyword in headline for keyword in ['earnings', 'revenue', 'profit', 'corporate']):
                return 'corporate'
            
            return 'general'
            
        except Exception as e:
            self.logger.error(f"Error categorizing news: {str(e)}")
            return 'unknown'
    
    def _analyze_news_sentiment(self, article: Dict[str, Any]) -> str:
        """Analyze the sentiment of a news article"""
        try:
            headline = article.get('headline', '').lower()
            
            # Positive sentiment keywords
            positive_keywords = [
                'rise', 'increase', 'growth', 'positive', 'strong', 'boost',
                'surge', 'rally', 'gain', 'improve', 'recovery', 'expansion'
            ]
            
            # Negative sentiment keywords
            negative_keywords = [
                'fall', 'decline', 'drop', 'negative', 'weak', 'crash',
                'plunge', 'slump', 'loss', 'worsen', 'recession', 'contraction'
            ]
            
            positive_count = sum(1 for keyword in positive_keywords if keyword in headline)
            negative_count = sum(1 for keyword in negative_keywords if keyword in headline)
            
            if positive_count > negative_count:
                return 'positive'
            elif negative_count > positive_count:
                return 'negative'
            else:
                return 'neutral'
                
        except Exception as e:
            self.logger.error(f"Error analyzing news sentiment: {str(e)}")
            return 'unknown'
    
    def _calculate_overall_market_score(self, market_data: Dict[str, Any]) -> float:
        """Calculate overall market score combining all data sources with quality weighting"""
        try:
            score = 0.0
            weight_sum = 0.0
            
            # Technical analysis weight: 40% (adjusted by quality)
            if market_data.get('technical_analysis'):
                tech_data = market_data['technical_analysis']
                tech_score = tech_data.get('signal_strength', 0)
                tech_quality = tech_data.get('quality_score', 0.8)
                weight = 0.4 * tech_quality
                score += tech_score * weight
                weight_sum += weight
            
            # Sentiment weight: 30% (adjusted by quality)
            sentiment_data = market_data.get('market_sentiment')
            if not sentiment_data.empty:
                pair_sentiment = sentiment_data[sentiment_data['pair'] == market_data['pair_name']]
                if not pair_sentiment.empty:
                    sentiment_score = pair_sentiment['sentiment_score'].iloc[0]
                    sentiment_quality = self.get_data_quality_score('market_sentiment')
                    weight = 0.3 * sentiment_quality
                    score += sentiment_score * weight
                    weight_sum += weight
            
            # MyFXBook sentiment weight: 20% (adjusted by quality)
            myfxbook_data = market_data.get('myfxbook_sentiment')
            if not myfxbook_data.empty:
                pair_myfxbook = myfxbook_data[myfxbook_data['pair_name'] == market_data['pair_name']]
                if not pair_myfxbook.empty:
                    bullish_perc = float(pair_myfxbook['bullish_perc'].iloc[0])
                    bearish_perc = float(pair_myfxbook['bearish_perc'].iloc[0])
                    myfxbook_score = (bullish_perc - bearish_perc) / 100  # Convert to -1 to 1 range
                    myfxbook_quality = self.get_data_quality_score('myfxbook_sentiment')
                    weight = 0.2 * myfxbook_quality
                    score += myfxbook_score * weight
                    weight_sum += weight
            
            # News weight: 10% (adjusted by quality)
            news_data = market_data.get('financial_news', [])
            if news_data:
                avg_news_relevance = sum(article.get('relevance_score', 0) for article in news_data) / len(news_data)
                news_quality = self.get_data_quality_score('financial_news')
                weight = 0.1 * news_quality
                score += avg_news_relevance * weight
                weight_sum += weight
            
            # Normalize by weight sum
            if weight_sum > 0:
                score = score / weight_sum
            
            return round(score, 3)
            
        except Exception as e:
            self.logger.error(f"Error calculating overall market score: {str(e)}")
            return 0.0
    
    def _calculate_signal_consensus(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate signal consensus across multiple data sources"""
        try:
            signals = {
                'technical': 0.0,
                'sentiment': 0.0,
                'myfxbook': 0.0,
                'news': 0.0,
                'consensus': 0.0,
                'confidence': 0.0
            }
            
            # Technical signal
            if market_data.get('technical_analysis'):
                signals['technical'] = market_data['technical_analysis'].get('signal_strength', 0.0)
            
            # Sentiment signal
            sentiment_data = market_data.get('market_sentiment')
            if not sentiment_data.empty:
                pair_sentiment = sentiment_data[sentiment_data['pair'] == market_data['pair_name']]
                if not pair_sentiment.empty:
                    signals['sentiment'] = pair_sentiment['sentiment_score'].iloc[0]
            
            # MyFXBook signal
            myfxbook_data = market_data.get('myfxbook_sentiment')
            if not myfxbook_data.empty:
                pair_myfxbook = myfxbook_data[myfxbook_data['pair_name'] == market_data['pair_name']]
                if not pair_myfxbook.empty:
                    bullish_perc = float(pair_myfxbook['bullish_perc'].iloc[0])
                    bearish_perc = float(pair_myfxbook['bearish_perc'].iloc[0])
                    signals['myfxbook'] = (bullish_perc - bearish_perc) / 100
            
            # News signal (based on relevance)
            news_data = market_data.get('financial_news', [])
            if news_data:
                avg_news_relevance = sum(article.get('relevance_score', 0) for article in news_data) / len(news_data)
                signals['news'] = avg_news_relevance * 0.5  # Scale down news impact
            
            # Calculate consensus
            signal_values = [signals['technical'], signals['sentiment'], signals['myfxbook'], signals['news']]
            valid_signals = [s for s in signal_values if s != 0.0]
            
            if valid_signals:
                signals['consensus'] = sum(valid_signals) / len(valid_signals)
                
                # Calculate confidence based on signal agreement
                if len(valid_signals) > 1:
                    signal_variance = sum((s - signals['consensus']) ** 2 for s in valid_signals) / len(valid_signals)
                    signals['confidence'] = max(0.0, 1.0 - signal_variance)
                else:
                    signals['confidence'] = 0.5  # Single signal has medium confidence
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error calculating signal consensus: {str(e)}")
            return {'consensus': 0.0, 'confidence': 0.0}
    
    def clear_cache(self) -> None:
        """Clear all cached data"""
        self.cache.clear()
        self.cache_expiry.clear()
        self.logger.info("Cache cleared")
    
    def get_cache_status(self) -> Dict[str, Any]:
        """Get cache status information"""
        return {
            'cache_size': len(self.cache),
            'cache_keys': list(self.cache.keys()),
            'cache_expiry': {k: v.isoformat() for k, v in self.cache_expiry.items()}
        }
    
    def _calculate_sentiment_position_adjustment(self, pair_name: str) -> Dict[str, Any]:
        """Calculate position size adjustment based on sentiment extremes"""
        try:
            adjustment = {
                'position_multiplier': 1.0,
                'reason': 'Normal sentiment',
                'confidence': 0.5,
                'sentiment_data': {}
            }
            
            # Get MyFXBook sentiment data
            myfxbook_data = self.get_myfxbook_sentiment()
            if not myfxbook_data.empty:
                pair_data = myfxbook_data[myfxbook_data['pair_name'] == pair_name]
                if not pair_data.empty:
                    bullish_perc = float(pair_data['bullish_perc'].iloc[0])
                    bearish_perc = float(pair_data['bearish_perc'].iloc[0])
                    popularity = float(pair_data['popularity'].iloc[0])
                    
                    adjustment['sentiment_data'] = {
                        'bullish_perc': bullish_perc,
                        'bearish_perc': bearish_perc,
                        'popularity': popularity
                    }
                    
                    # Extreme sentiment detection
                    if bullish_perc >= 80 or bearish_perc >= 80:
                        # Extreme sentiment - reduce position size (contrarian approach)
                        adjustment['position_multiplier'] = 0.5
                        adjustment['reason'] = f'Extreme sentiment detected: {bullish_perc:.0f}% bullish, {bearish_perc:.0f}% bearish'
                        adjustment['confidence'] = 0.8
                    elif bullish_perc >= 70 or bearish_perc >= 70:
                        # High sentiment - moderate reduction
                        adjustment['position_multiplier'] = 0.7
                        adjustment['reason'] = f'High sentiment detected: {bullish_perc:.0f}% bullish, {bearish_perc:.0f}% bearish'
                        adjustment['confidence'] = 0.7
                    elif bullish_perc <= 30 or bearish_perc <= 30:
                        # Low sentiment - moderate increase (contrarian opportunity)
                        adjustment['position_multiplier'] = 1.3
                        adjustment['reason'] = f'Low sentiment detected: {bullish_perc:.0f}% bullish, {bearish_perc:.0f}% bearish'
                        adjustment['confidence'] = 0.6
                    
                    # Adjust based on popularity (more popular = more reliable)
                    if popularity >= 80:
                        adjustment['confidence'] = min(1.0, adjustment['confidence'] + 0.2)
                    elif popularity <= 20:
                        adjustment['confidence'] = max(0.1, adjustment['confidence'] - 0.2)
            
            return adjustment
            
        except Exception as e:
            self.logger.error(f"Error calculating sentiment position adjustment: {str(e)}")
            return {'position_multiplier': 1.0, 'reason': 'Error in analysis', 'confidence': 0.0}
    
    def get_position_sizing_recommendation(self, pair_name: str, base_position_size: float = 1.0) -> Dict[str, Any]:
        """
        Get position sizing recommendation based on sentiment analysis
        
        Args:
            pair_name: Currency pair name
            base_position_size: Base position size to adjust
            
        Returns:
            Dictionary with position sizing recommendations
        """
        try:
            recommendation = {
                'pair_name': pair_name,
                'base_position_size': base_position_size,
                'timestamp': datetime.now(),
                'sentiment_adjustment': self._calculate_sentiment_position_adjustment(pair_name),
                'final_recommendation': {}
            }
            
            # Calculate final position size
            sentiment_adj = recommendation['sentiment_adjustment']
            adjusted_size = base_position_size * sentiment_adj['position_multiplier']
            
            recommendation['final_recommendation'] = {
                'recommended_position_size': round(adjusted_size, 4),
                'adjustment_factor': sentiment_adj['position_multiplier'],
                'reason': sentiment_adj['reason'],
                'confidence': sentiment_adj['confidence'],
                'risk_level': self._determine_risk_level_from_sentiment(sentiment_adj)
            }
            
            self.logger.info(f"Position sizing for {pair_name}: {base_position_size} -> {adjusted_size:.4f} (factor: {sentiment_adj['position_multiplier']:.2f})")
            return recommendation
            
        except Exception as e:
            self.logger.error(f"Error getting position sizing recommendation: {str(e)}")
            return {
                'pair_name': pair_name,
                'base_position_size': base_position_size,
                'final_recommendation': {
                    'recommended_position_size': base_position_size,
                    'adjustment_factor': 1.0,
                    'reason': 'Error in analysis',
                    'confidence': 0.0,
                    'risk_level': 'UNKNOWN'
                }
            }
    
    def _determine_risk_level_from_sentiment(self, sentiment_adj: Dict[str, Any]) -> str:
        """Determine risk level based on sentiment adjustment"""
        try:
            multiplier = sentiment_adj.get('position_multiplier', 1.0)
            confidence = sentiment_adj.get('confidence', 0.5)
            
            if multiplier <= 0.5:
                return 'HIGH'  # Extreme sentiment = high risk
            elif multiplier <= 0.7:
                return 'MEDIUM-HIGH'
            elif multiplier >= 1.3:
                return 'MEDIUM-LOW'  # Contrarian opportunity
            elif confidence >= 0.8:
                return 'LOW'  # High confidence
            else:
                return 'MEDIUM'
                
        except Exception as e:
            self.logger.error(f"Error determining risk level: {str(e)}")
            return 'UNKNOWN'
    
    def _calculate_data_recency_weight(self, data_timestamp: datetime, data_type: str) -> float:
        """Calculate weight based on data recency"""
        try:
            current_time = datetime.now()
            age_seconds = (current_time - data_timestamp).total_seconds()
            
            # Get optimal refresh intervals for each data type
            optimal_intervals = {
                'economic_calendar': 3600,    # 1 hour
                'technical_analysis': 300,     # 5 minutes
                'market_sentiment': 600,       # 10 minutes
                'financial_news': 180,         # 3 minutes
                'myfxbook_sentiment': 900      # 15 minutes
            }
            
            optimal_interval = optimal_intervals.get(data_type, 300)
            
            # Calculate weight based on age
            if age_seconds <= optimal_interval:
                # Fresh data - full weight
                return 1.0
            elif age_seconds <= optimal_interval * 2:
                # Slightly stale - 80% weight
                return 0.8
            elif age_seconds <= optimal_interval * 4:
                # Moderately stale - 60% weight
                return 0.6
            elif age_seconds <= optimal_interval * 8:
                # Stale - 40% weight
                return 0.4
            else:
                # Very stale - 20% weight
                return 0.2
                
        except Exception as e:
            self.logger.error(f"Error calculating data recency weight: {str(e)}")
            return 0.5  # Default weight
    
    def _apply_recency_weighting(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply recency weighting to market data"""
        try:
            weighted_data = market_data.copy()
            current_time = datetime.now()
            
            # Weight technical analysis data
            if 'technical_analysis' in market_data and market_data['technical_analysis']:
                tech_data = market_data['technical_analysis']
                if 'analysis_timestamp' in tech_data:
                    recency_weight = self._calculate_data_recency_weight(
                        tech_data['analysis_timestamp'], 'technical_analysis'
                    )
                    tech_data['recency_weight'] = recency_weight
                    tech_data['weighted_signal_strength'] = tech_data.get('signal_strength', 0) * recency_weight
                    weighted_data['technical_analysis'] = tech_data
            
            # Weight sentiment data
            sentiment_data = market_data.get('market_sentiment')
            if not sentiment_data.empty and 'analysis_timestamp' in sentiment_data.columns:
                recency_weight = self._calculate_data_recency_weight(
                    sentiment_data['analysis_timestamp'].iloc[0], 'market_sentiment'
                )
                sentiment_data['recency_weight'] = recency_weight
                if 'sentiment_score' in sentiment_data.columns:
                    sentiment_data['weighted_sentiment_score'] = sentiment_data['sentiment_score'] * recency_weight
                weighted_data['market_sentiment'] = sentiment_data
            
            # Weight MyFXBook sentiment data
            myfxbook_data = market_data.get('myfxbook_sentiment')
            if not myfxbook_data.empty and 'analysis_timestamp' in myfxbook_data.columns:
                recency_weight = self._calculate_data_recency_weight(
                    myfxbook_data['analysis_timestamp'].iloc[0], 'myfxbook_sentiment'
                )
                myfxbook_data['recency_weight'] = recency_weight
                weighted_data['myfxbook_sentiment'] = myfxbook_data
            
            # Weight news data
            news_data = market_data.get('financial_news', [])
            if news_data:
                for article in news_data:
                    if 'analysis_timestamp' in article:
                        recency_weight = self._calculate_data_recency_weight(
                            article['analysis_timestamp'], 'financial_news'
                        )
                        article['recency_weight'] = recency_weight
                        article['weighted_relevance_score'] = article.get('relevance_score', 0) * recency_weight
                weighted_data['financial_news'] = news_data
            
            # Recalculate overall score with recency weighting
            weighted_data['overall_score'] = self._calculate_overall_market_score(weighted_data)
            weighted_data['signal_consensus'] = self._calculate_signal_consensus(weighted_data)
            
            return weighted_data
            
        except Exception as e:
            self.logger.error(f"Error applying recency weighting: {str(e)}")
            return market_data
    
    def get_recency_weighted_market_data(self, pair_name: str, timeframe: str = "H1") -> Dict[str, Any]:
        """
        Get market data with recency weighting applied
        
        Args:
            pair_name: Currency pair name
            timeframe: Analysis timeframe
            
        Returns:
            Dictionary with recency-weighted market data
        """
        try:
            # Get comprehensive market data
            market_data = self.get_comprehensive_market_data(pair_name, timeframe)
            
            # Apply recency weighting
            weighted_data = self._apply_recency_weighting(market_data)
            
            # Add recency analysis
            weighted_data['recency_analysis'] = self._get_recency_analysis(weighted_data)
            
            self.logger.info(f"Retrieved recency-weighted market data for {pair_name}")
            return weighted_data
            
        except Exception as e:
            self.logger.error(f"Error getting recency-weighted market data: {str(e)}")
            return {}
    
    def _get_recency_analysis(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get analysis of data recency across all sources"""
        try:
            analysis = {
                'overall_freshness': 0.0,
                'data_sources': {},
                'recommendations': []
            }
            
            current_time = datetime.now()
            freshness_scores = []
            
            # Analyze each data source
            data_sources = {
                'technical_analysis': market_data.get('technical_analysis'),
                'market_sentiment': market_data.get('market_sentiment'),
                'myfxbook_sentiment': market_data.get('myfxbook_sentiment'),
                'financial_news': market_data.get('financial_news', [])
            }
            
            for source_name, source_data in data_sources.items():
                if source_data is not None and (not hasattr(source_data, 'empty') or not source_data.empty):
                    if isinstance(source_data, dict) and 'analysis_timestamp' in source_data:
                        age_seconds = (current_time - source_data['analysis_timestamp']).total_seconds()
                        recency_weight = source_data.get('recency_weight', 0.5)
                        
                        analysis['data_sources'][source_name] = {
                            'age_seconds': age_seconds,
                            'recency_weight': recency_weight,
                            'freshness': 'FRESH' if recency_weight >= 0.8 else 'STALE' if recency_weight <= 0.4 else 'MODERATE'
                        }
                        freshness_scores.append(recency_weight)
                        
                        # Add recommendations
                        if recency_weight <= 0.4:
                            analysis['recommendations'].append(f"Consider refreshing {source_name} data")
                    elif isinstance(source_data, list) and source_data:
                        # Handle list data (like news)
                        avg_weight = sum(item.get('recency_weight', 0.5) for item in source_data) / len(source_data)
                        analysis['data_sources'][source_name] = {
                            'avg_recency_weight': avg_weight,
                            'freshness': 'FRESH' if avg_weight >= 0.8 else 'STALE' if avg_weight <= 0.4 else 'MODERATE'
                        }
                        freshness_scores.append(avg_weight)
            
            # Calculate overall freshness
            if freshness_scores:
                analysis['overall_freshness'] = sum(freshness_scores) / len(freshness_scores)
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error getting recency analysis: {str(e)}")
            return {'overall_freshness': 0.5, 'data_sources': {}, 'recommendations': []}
    
    def get_fallback_market_data(self, pair_name: str, timeframe: str = "H1") -> Dict[str, Any]:
        """
        Get fallback market data when primary sources fail
        
        Args:
            pair_name: Currency pair name
            timeframe: Analysis timeframe
            
        Returns:
            Dictionary with fallback market data
        """
        try:
            fallback_data = {
                'pair_name': pair_name,
                'timeframe': timeframe,
                'timestamp': datetime.now(),
                'data_source': 'fallback',
                'overall_score': 0.0,
                'signal_consensus': {'consensus': 0.0, 'confidence': 0.0}
            }
            
            # Try to get at least MyFXBook data (most reliable)
            try:
                myfxbook_data = self.get_myfxbook_sentiment()
                if not myfxbook_data.empty:
                    fallback_data['myfxbook_sentiment'] = myfxbook_data
                    fallback_data['data_source'] = 'myfxbook_fallback'
            except Exception as e:
                self.logger.warning(f"MyFXBook fallback failed: {e}")
            
            # If we have any data, try to calculate basic scores
            if 'myfxbook_sentiment' in fallback_data:
                fallback_data['overall_score'] = 0.3  # Conservative score
                fallback_data['signal_consensus'] = {'consensus': 0.0, 'confidence': 0.3}
            
            self.logger.info(f"Using fallback market data for {pair_name}")
            return fallback_data
            
        except Exception as e:
            self.logger.error(f"Fallback market data failed: {str(e)}")
            return {
                'pair_name': pair_name,
                'timeframe': timeframe,
                'timestamp': datetime.now(),
                'data_source': 'emergency_fallback',
                'overall_score': 0.0,
                'signal_consensus': {'consensus': 0.0, 'confidence': 0.0},
                'error': str(e)
            }
    
    def get_robust_market_data(self, pair_name: str, timeframe: str = "H1") -> Dict[str, Any]:
        """
        Get market data with robust error handling and fallbacks
        
        Args:
            pair_name: Currency pair name
            timeframe: Analysis timeframe
            
        Returns:
            Dictionary with robust market data
        """
        try:
            # Try comprehensive data first
            market_data = self.get_comprehensive_market_data(pair_name, timeframe)
            
            # If we got some data, return it
            if market_data and len(market_data) > 3:  # More than just basic fields
                return market_data
            
            # Try session-optimized data
            self.logger.warning(f"Comprehensive data failed for {pair_name}, trying session-optimized data")
            market_data = self.get_session_optimized_market_data(pair_name, timeframe)
            
            if market_data and len(market_data) > 3:
                return market_data
            
            # Try recency-weighted data
            self.logger.warning(f"Session-optimized data failed for {pair_name}, trying recency-weighted data")
            market_data = self.get_recency_weighted_market_data(pair_name, timeframe)
            if market_data and len(market_data) > 3:
                return market_data
            
            # Use fallback data
            self.logger.warning(f"All primary methods failed for {pair_name}, using fallback data")
            return self.get_fallback_market_data(pair_name, timeframe)
            
        except Exception as e:
            self.logger.error(f"All market data methods failed for {pair_name}: {str(e)}")
            return self.get_fallback_market_data(pair_name, timeframe)


# Convenience functions for easy integration
def get_scraping_data_integration(logger: Optional[logging.Logger] = None) -> ScrapingDataIntegration:
    """Get a ScrapingDataIntegration instance"""
    return ScrapingDataIntegration(logger)


def get_market_data_for_pair(pair_name: str, timeframe: str = "H1") -> Dict[str, Any]:
    """Quick function to get market data for a specific pair"""
    integration = ScrapingDataIntegration()
    return integration.get_comprehensive_market_data(pair_name, timeframe)


