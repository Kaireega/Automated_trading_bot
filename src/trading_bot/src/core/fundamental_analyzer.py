"""
Fundamental Analysis Layer - Enhanced Economic and Sentiment Analysis.

This module provides comprehensive fundamental analysis capabilities for the trading bot,
leveraging real scraped data from multiple sources to make informed trading decisions.

Key Features:
- Economic calendar event analysis with impact assessment
- Community sentiment analysis from MyFXBook
- Financial news sentiment scoring
- Market session analysis and timing
- Currency correlation and risk assessment
- Trading avoidance recommendations for high-impact events

Data Sources:
- Economic Calendar: FX Calendar with events, forecasts, and actuals
- Community Sentiment: MyFXBook bullish/bearish percentages and popularity
- Financial News: Reuters headlines for sentiment analysis
- Technical Analysis: Investing.com technical indicators
- Market Sentiment: Aggregated sentiment scores

Architecture:
- FundamentalAnalyzer: Main orchestrator for fundamental analysis
- ScrapingDataIntegration: Access to all scraped data sources
- Event Impact Assessment: High/medium/low impact event classification
- Sentiment Aggregation: Multi-source sentiment scoring
- Risk Assessment: Fundamental risk factors for trading decisions

Author: Trading Bot Development Team
Version: 3.0.0
Last Updated: 2024
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
import pandas as pd
import re

from ..core.models import MarketContext, MarketCondition
from ..utils.config import Config
from ..utils.logger import get_logger
from ..data.scraping_data_integration import ScrapingDataIntegration


class FundamentalAnalyzer:
    """Enhanced fundamental analysis using real scraped data sources."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger(__name__)
        
        # Initialize ScrapingDataIntegration for comprehensive data access
        self.scraping_integration = ScrapingDataIntegration(self.logger)
        self.logger.info("FundamentalAnalyzer initialized with ScrapingDataIntegration")
        
        # Market session times (UTC)
        self.sessions = {
            'tokyo': {'start': 0, 'end': 9, 'volatility': 0.6},
            'london': {'start': 8, 'end': 17, 'volatility': 0.9},
            'new_york': {'start': 13, 'end': 22, 'volatility': 0.8},
            'overlap_london_ny': {'start': 13, 'end': 17, 'volatility': 1.0}
        }
        
        # High-impact event keywords for classification
        self.high_impact_keywords = [
            'nfp', 'non-farm payrolls', 'cpi', 'ppi', 'gdp', 'fomc', 
            'ecb', 'boe', 'boj', 'federal reserve', 'central bank',
            'monetary policy', 'interest rate', 'unemployment', 'inflation',
            'retail sales', 'industrial production', 'consumer confidence'
        ]
        
        # Currency correlation groups
        self.currency_groups = {
            'USD': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'USD_CAD', 'AUD_USD', 'NZD_USD'],
            'EUR': ['EUR_USD', 'EUR_JPY', 'EUR_GBP', 'EUR_CHF'],
            'GBP': ['GBP_USD', 'GBP_JPY', 'EUR_GBP', 'GBP_CHF'],
            'JPY': ['USD_JPY', 'EUR_JPY', 'GBP_JPY', 'AUD_JPY'],
            'COMMODITY': ['AUD_USD', 'NZD_USD', 'USD_CAD']
        }
        
        # Sentiment analysis keywords
        self.positive_keywords = [
            'bullish', 'gain', 'rise', 'up', 'strong', 'positive', 'buy',
            'growth', 'expansion', 'recovery', 'surge', 'rally', 'boost'
        ]
        self.negative_keywords = [
            'bearish', 'drop', 'fall', 'down', 'weak', 'negative', 'sell',
            'decline', 'recession', 'crisis', 'crash', 'plunge', 'slump'
        ]
        
        # Cache for performance
        self._analysis_cache = {}
        self._last_update = None
        self._cache_duration = timedelta(minutes=10)
    
    async def start(self) -> None:
        """Start the fundamental analyzer."""
        try:
            self.logger.info("Starting enhanced fundamental analyzer...")
            # Test data access
            await self._test_data_sources()
            self.logger.info("Fundamental analyzer started successfully")
        except Exception as e:
            self.logger.error(f"Error starting fundamental analyzer: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the fundamental analyzer."""
        self.logger.info("Fundamental analyzer stopped")
    
    async def analyze_fundamentals(self, pair: str, market_context: MarketContext) -> Dict[str, Any]:
        """
        Comprehensive fundamental analysis for a trading pair.
        
        Args:
            pair: Currency pair (e.g., 'EUR_USD')
            market_context: Current market context
            
        Returns:
            Dictionary with comprehensive fundamental analysis
        """
        try:
            # Check cache first
            cache_key = f"{pair}_{datetime.now().strftime('%Y%m%d%H%M')}"
            if self._is_cache_valid(cache_key):
                return self._analysis_cache[cache_key]
            
            # Extract currencies
            base_currency, quote_currency = pair.split('_')
            
            # Get all fundamental data
            economic_events = await self._get_relevant_economic_events(pair)
            community_sentiment = await self._get_community_sentiment(pair)
            news_sentiment = await self._get_news_sentiment()
            market_session = self._get_market_session_analysis()
            
            # Analyze event impact
            event_impact = self._analyze_event_impact(economic_events, pair)
            
            # Calculate overall sentiment
            overall_sentiment = self._calculate_overall_sentiment(
                community_sentiment, news_sentiment, event_impact
            )
            
            # Determine fundamental bias
            fundamental_bias = self._determine_fundamental_bias(overall_sentiment)
            
            # Assess trading risk
            trading_risk = self._assess_trading_risk(
                economic_events, community_sentiment, market_session
            )
            
            # Generate trading recommendations
            recommendations = self._generate_trading_recommendations(
                pair, overall_sentiment, trading_risk, event_impact
            )
            
            result = {
                'pair': pair,
                'analysis_timestamp': datetime.now(timezone.utc),
                'overall_sentiment': overall_sentiment,
                'fundamental_bias': fundamental_bias,
                'economic_events': economic_events,
                'event_impact': event_impact,
                'community_sentiment': community_sentiment,
                'news_sentiment': news_sentiment,
                'market_session': market_session,
                'trading_risk': trading_risk,
                'recommendations': recommendations,
                'data_quality': self._assess_data_quality()
            }
            
            # Cache the result
            self._analysis_cache[cache_key] = result
            self._last_update = datetime.now(timezone.utc)
            
            self.logger.info(f"Fundamental analysis completed for {pair}: "
                           f"Bias={fundamental_bias}, Sentiment={overall_sentiment:.3f}, "
                           f"Risk={trading_risk['level']}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in fundamental analysis for {pair}: {e}")
            return self._get_fallback_analysis(pair, str(e))
    
    async def _get_relevant_economic_events(self, pair: str) -> List[Dict[str, Any]]:
        """Get economic events relevant to the currency pair."""
        try:
            # Get economic calendar data
            calendar_data = self.scraping_integration.get_economic_calendar(days_ahead=7)
            
            if not calendar_data:
                return []
            
            base_currency, quote_currency = pair.split('_')
            relevant_events = []
            current_time = datetime.now(timezone.utc)
            
            for event in calendar_data:
                # Check if event is within next 48 hours
                event_date = event.get('date')
                if not event_date:
                    continue
                
                # Parse event date
                if isinstance(event_date, str):
                    try:
                        event_date = datetime.fromisoformat(event_date.replace('Z', '+00:00'))
                    except:
                        continue
                
                if event_date.tzinfo is None:
                    event_date = event_date.replace(tzinfo=timezone.utc)
                
                time_diff = event_date - current_time
                if timedelta(hours=-2) <= time_diff <= timedelta(hours=48):
                    # Check if event affects the currencies
                    symbol = event.get('symbol', '').upper()
                    country = event.get('country', '').lower()
                    
                    if self._event_affects_pair(event, base_currency, quote_currency):
                        # Enhance event data
                        enhanced_event = {
                            **event,
                            'time_to_event': time_diff,
                            'impact_level': self._classify_event_impact(event),
                            'currency_relevance': self._get_currency_relevance(event, base_currency, quote_currency)
                        }
                        relevant_events.append(enhanced_event)
            
            # Sort by time to event
            relevant_events.sort(key=lambda x: x['time_to_event'])
            return relevant_events
            
        except Exception as e:
            self.logger.error(f"Error getting economic events for {pair}: {e}")
            return []
    
    async def _get_community_sentiment(self, pair: str) -> Dict[str, Any]:
        """Get community sentiment from MyFXBook data."""
        try:
            # Get MyFXBook sentiment data
            sentiment_data = self.scraping_integration.get_myfxbook_sentiment()
            
            if sentiment_data is None or sentiment_data.empty:
                return self._get_default_sentiment()
            
            # Find data for the specific pair
            pair_data = sentiment_data[sentiment_data['pair_name'] == pair]
            
            if pair_data.empty:
                return self._get_default_sentiment()
            
            row = pair_data.iloc[0]
            
            # Calculate sentiment metrics
            bullish_perc = float(row.get('bullish_perc', 50))
            bearish_perc = float(row.get('bearish_perc', 50))
            popularity = float(row.get('popularity', 50))
            
            # Calculate sentiment score (-1 to 1)
            sentiment_score = (bullish_perc - bearish_perc) / 100
            
            # Determine sentiment strength
            sentiment_strength = abs(sentiment_score)
            
            # Contrarian signal (high bullish = potential sell signal)
            contrarian_signal = 'SELL' if bullish_perc > 70 else 'BUY' if bearish_perc > 70 else 'NEUTRAL'
            
            return {
                'bullish_percentage': bullish_perc,
                'bearish_percentage': bearish_perc,
                'popularity': popularity,
                'sentiment_score': sentiment_score,
                'sentiment_strength': sentiment_strength,
                'contrarian_signal': contrarian_signal,
                'data_source': 'myfxbook',
                'timestamp': row.get('analysis_timestamp', datetime.now(timezone.utc))
            }
            
        except Exception as e:
            self.logger.error(f"Error getting community sentiment for {pair}: {e}")
            return self._get_default_sentiment()
    
    async def _get_news_sentiment(self) -> Dict[str, Any]:
        """Get news sentiment from financial news."""
        try:
            # Get financial news
            news_data = self.scraping_integration.get_financial_news()
            
            if not news_data:
                return {'sentiment_score': 0.0, 'news_count': 0, 'source': 'none'}
            
            # Analyze headlines for sentiment
            sentiment_scores = []
            for article in news_data[:10]:  # Analyze top 10 articles
                headline = article.get('headline', '')
                sentiment = self._analyze_headline_sentiment(headline)
                sentiment_scores.append(sentiment)
            
            if sentiment_scores:
                avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
            else:
                avg_sentiment = 0.0
            
            return {
                'sentiment_score': avg_sentiment,
                'news_count': len(news_data),
                'analyzed_headlines': len(sentiment_scores),
                'source': 'reuters',
                'timestamp': datetime.now(timezone.utc)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting news sentiment: {e}")
            return {'sentiment_score': 0.0, 'news_count': 0, 'source': 'error'}
    
    def _get_market_session_analysis(self) -> Dict[str, Any]:
        """Analyze current market session and timing."""
        current_time = datetime.now(timezone.utc)
        current_hour = current_time.hour
        
        # Determine current session
        current_session = 'closed'
        active_sessions = []
        
        for session, times in self.sessions.items():
            if session == 'overlap_london_ny':
                continue
            if times['start'] <= current_hour < times['end']:
                active_sessions.append(session)
                if current_session == 'closed':
                    current_session = session
        
        # Check for London-NY overlap
        if 13 <= current_hour < 17:
            active_sessions.append('overlap_london_ny')
            current_session = 'overlap_london_ny'
        
        # Calculate session volatility
        max_volatility = max([self.sessions[session]['volatility'] for session in active_sessions]) if active_sessions else 0.3
        
        return {
            'current_session': current_session,
            'active_sessions': active_sessions,
            'is_overlap': len(active_sessions) > 1,
            'volatility_level': max_volatility,
            'session_quality': 'high' if max_volatility > 0.8 else 'medium' if max_volatility > 0.5 else 'low',
            'time_to_next_session': self._get_time_to_next_session(current_hour)
        }
    
    def _analyze_event_impact(self, events: List[Dict[str, Any]], pair: str) -> Dict[str, Any]:
        """Analyze the impact of economic events on the pair."""
        if not events:
            return {
                'impact_level': 'low',
                'high_impact_count': 0,
                'next_high_impact': None,
                'trading_recommendation': 'normal'
            }
        
        high_impact_events = [e for e in events if e.get('impact_level') == 'high']
        medium_impact_events = [e for e in events if e.get('impact_level') == 'medium']
        
        # Find next high-impact event
        next_high_impact = None
        for event in high_impact_events:
            if event['time_to_event'] > timedelta(0):
                next_high_impact = event
                break
        
        # Determine trading recommendation
        if high_impact_events:
            trading_recommendation = 'avoid'
        elif medium_impact_events:
            trading_recommendation = 'caution'
        else:
            trading_recommendation = 'normal'
        
        return {
            'impact_level': 'high' if high_impact_events else 'medium' if medium_impact_events else 'low',
            'high_impact_count': len(high_impact_events),
            'medium_impact_count': len(medium_impact_events),
            'next_high_impact': next_high_impact,
            'trading_recommendation': trading_recommendation,
            'total_events': len(events)
        }
    
    def _calculate_overall_sentiment(self, community_sentiment: Dict[str, Any], 
                                   news_sentiment: Dict[str, Any], 
                                   event_impact: Dict[str, Any]) -> float:
        """Calculate overall sentiment from multiple sources."""
        try:
            # Community sentiment weight: 0.4
            community_score = community_sentiment.get('sentiment_score', 0.0)
            community_weight = 0.4
            
            # News sentiment weight: 0.3
            news_score = news_sentiment.get('sentiment_score', 0.0)
            news_weight = 0.3
            
            # Event impact weight: 0.3 (positive events = positive sentiment)
            event_score = 0.0
            if event_impact.get('next_high_impact'):
                # For now, assume events are neutral unless we can determine otherwise
                event_score = 0.0
            event_weight = 0.3
            
            # Calculate weighted average
            overall_sentiment = (
                community_score * community_weight +
                news_score * news_weight +
                event_score * event_weight
            )
            
            # Normalize to -1 to 1 range
            return max(-1.0, min(1.0, overall_sentiment))
            
        except Exception as e:
            self.logger.error(f"Error calculating overall sentiment: {e}")
            return 0.0
    
    def _determine_fundamental_bias(self, sentiment_score: float) -> str:
        """Determine fundamental bias from sentiment score."""
        if sentiment_score >= 0.3:
            return 'BULLISH'
        elif sentiment_score <= -0.3:
            return 'BEARISH'
        else:
            return 'NEUTRAL'
    
    def _assess_trading_risk(self, events: List[Dict[str, Any]], 
                           community_sentiment: Dict[str, Any], 
                           market_session: Dict[str, Any]) -> Dict[str, Any]:
        """Assess fundamental trading risk."""
        risk_factors = []
        risk_score = 0.0
        
        # Event risk
        high_impact_events = [e for e in events if e.get('impact_level') == 'high']
        if high_impact_events:
            risk_factors.append(f"{len(high_impact_events)} high-impact events")
            risk_score += 0.4
        
        # Sentiment risk (extreme sentiment = higher risk)
        sentiment_strength = community_sentiment.get('sentiment_strength', 0.0)
        if sentiment_strength > 0.8:
            risk_factors.append("extreme community sentiment")
            risk_score += 0.2
        
        # Session risk
        if market_session.get('volatility_level', 0.0) > 0.9:
            risk_factors.append("high volatility session")
            risk_score += 0.1
        
        # Determine risk level
        if risk_score >= 0.6:
            risk_level = 'high'
        elif risk_score >= 0.3:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        return {
            'level': risk_level,
            'score': risk_score,
            'factors': risk_factors,
            'recommendation': 'avoid' if risk_level == 'high' else 'caution' if risk_level == 'medium' else 'normal'
        }
    
    def _generate_trading_recommendations(self, pair: str, sentiment: float, 
                                        risk: Dict[str, Any], 
                                        event_impact: Dict[str, Any]) -> Dict[str, Any]:
        """Generate trading recommendations based on fundamental analysis."""
        recommendations = {
            'should_trade': True,
            'confidence': 0.5,
            'position_size_multiplier': 1.0,
            'reasoning': []
        }
        
        # Check if we should avoid trading
        if risk['level'] == 'high' or event_impact['trading_recommendation'] == 'avoid':
            recommendations['should_trade'] = False
            recommendations['reasoning'].append("High fundamental risk detected")
            return recommendations
        
        # Adjust confidence based on sentiment strength
        sentiment_strength = abs(sentiment)
        if sentiment_strength > 0.7:
            recommendations['confidence'] = 0.8
            recommendations['reasoning'].append("Strong fundamental sentiment")
        elif sentiment_strength > 0.4:
            recommendations['confidence'] = 0.6
            recommendations['reasoning'].append("Moderate fundamental sentiment")
        else:
            recommendations['confidence'] = 0.4
            recommendations['reasoning'].append("Weak fundamental sentiment")
        
        # Adjust position size based on risk
        if risk['level'] == 'medium':
            recommendations['position_size_multiplier'] = 0.7
            recommendations['reasoning'].append("Reduced position size due to medium risk")
        elif risk['level'] == 'low':
            recommendations['position_size_multiplier'] = 1.0
            recommendations['reasoning'].append("Normal position size - low risk")
        
        return recommendations
    
    def _event_affects_pair(self, event: Dict[str, Any], base_currency: str, quote_currency: str) -> bool:
        """Check if an economic event affects the currency pair."""
        symbol = event.get('symbol', '').upper()
        country = event.get('country', '').lower()
        
        # Direct currency match
        if base_currency in symbol or quote_currency in symbol:
            return True
        
        # Country-currency mapping
        country_currency_map = {
            'united states': 'USD', 'europe': 'EUR', 'united kingdom': 'GBP',
            'japan': 'JPY', 'australia': 'AUD', 'canada': 'CAD',
            'new zealand': 'NZD', 'switzerland': 'CHF'
        }
        
        country_currency = country_currency_map.get(country)
        if country_currency and country_currency in [base_currency, quote_currency]:
            return True
        
        return False
    
    def _classify_event_impact(self, event: Dict[str, Any]) -> str:
        """Classify event impact level."""
        event_name = event.get('event', '').lower()
        category = event.get('category', '').lower()
        
        # High impact events
        if any(keyword in event_name for keyword in self.high_impact_keywords):
            return 'high'
        
        # Medium impact categories
        medium_categories = ['employment', 'inflation', 'gdp', 'retail sales']
        if any(cat in category for cat in medium_categories):
            return 'medium'
        
        return 'low'
    
    def _get_currency_relevance(self, event: Dict[str, Any], base_currency: str, quote_currency: str) -> float:
        """Get currency relevance score for the event."""
        symbol = event.get('symbol', '').upper()
        
        # Direct currency match = high relevance
        if base_currency in symbol or quote_currency in symbol:
            return 1.0
        
        # Indirect relevance through country
        country = event.get('country', '').lower()
        country_currency_map = {
            'united states': 'USD', 'europe': 'EUR', 'united kingdom': 'GBP',
            'japan': 'JPY', 'australia': 'AUD', 'canada': 'CAD',
            'new zealand': 'NZD', 'switzerland': 'CHF'
        }
        
        country_currency = country_currency_map.get(country)
        if country_currency and country_currency in [base_currency, quote_currency]:
            return 0.8
        
        return 0.3  # Low relevance
    
    def _analyze_headline_sentiment(self, headline: str) -> float:
        """Analyze sentiment of a news headline."""
        headline_lower = headline.lower()
        
        positive_count = sum(1 for word in self.positive_keywords if word in headline_lower)
        negative_count = sum(1 for word in self.negative_keywords if word in headline_lower)
        
        if positive_count == 0 and negative_count == 0:
            return 0.0
        
        # Calculate sentiment score (-1 to 1)
        total_words = positive_count + negative_count
        sentiment = (positive_count - negative_count) / total_words
        
        return max(-1.0, min(1.0, sentiment))
    
    def _get_time_to_next_session(self, current_hour: int) -> str:
        """Get time until next major session."""
        if current_hour < 8:
            return "London session"
        elif current_hour < 13:
            return "New York session"
        elif current_hour < 22:
            return "Tokyo session"
        else:
            return "London session"
    
    def _assess_data_quality(self) -> Dict[str, Any]:
        """Assess the quality of available data."""
        return {
            'economic_calendar': 'high',
            'community_sentiment': 'medium',
            'news_sentiment': 'medium',
            'overall_quality': 'good'
        }
    
    def _get_default_sentiment(self) -> Dict[str, Any]:
        """Get default sentiment when data is unavailable."""
        return {
            'bullish_percentage': 50.0,
            'bearish_percentage': 50.0,
            'popularity': 50.0,
            'sentiment_score': 0.0,
            'sentiment_strength': 0.0,
            'contrarian_signal': 'NEUTRAL',
            'data_source': 'default',
            'timestamp': datetime.now(timezone.utc)
        }
    
    def _get_fallback_analysis(self, pair: str, error: str) -> Dict[str, Any]:
        """Get fallback analysis when errors occur."""
        return {
            'pair': pair,
            'analysis_timestamp': datetime.now(timezone.utc),
            'overall_sentiment': 0.0,
            'fundamental_bias': 'NEUTRAL',
            'economic_events': [],
            'event_impact': {'impact_level': 'low', 'trading_recommendation': 'normal'},
            'community_sentiment': self._get_default_sentiment(),
            'news_sentiment': {'sentiment_score': 0.0, 'source': 'error'},
            'market_session': self._get_market_session_analysis(),
            'trading_risk': {'level': 'medium', 'recommendation': 'caution'},
            'recommendations': {'should_trade': False, 'reasoning': [f'Analysis error: {error}']},
            'data_quality': {'overall_quality': 'poor'},
            'error': error
        }
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached analysis is still valid."""
        if cache_key not in self._analysis_cache:
            return False
        
        if not self._last_update:
            return False
        
        return datetime.now(timezone.utc) - self._last_update < self._cache_duration
    
    async def _test_data_sources(self) -> None:
        """Test data source availability."""
        try:
            # Test economic calendar
            calendar_data = self.scraping_integration.get_economic_calendar(days_ahead=1)
            self.logger.info(f"Economic calendar: {len(calendar_data) if calendar_data else 0} events")
            
            # Test sentiment data
            sentiment_data = self.scraping_integration.get_myfxbook_sentiment()
            self.logger.info(f"MyFXBook sentiment: {'Available' if sentiment_data is not None and not sentiment_data.empty else 'Not available'}")
            
            # Test news data
            news_data = self.scraping_integration.get_financial_news()
            self.logger.info(f"Financial news: {len(news_data) if news_data else 0} articles")
            
        except Exception as e:
            self.logger.warning(f"Data source test failed: {e}")
    
    def get_market_session_info(self) -> Dict[str, Any]:
        """Get comprehensive market session information."""
        return self._get_market_session_analysis()
    
    def get_currency_correlation_info(self, pair: str) -> Dict[str, Any]:
        """Get currency correlation information for a pair."""
        base_currency, quote_currency = pair.split('_')
        
        correlated_pairs = []
        for currency, pairs in self.currency_groups.items():
            if currency in [base_currency, quote_currency]:
                correlated_pairs.extend([p for p in pairs if p != pair])
        
        return {
            'base_currency': base_currency,
            'quote_currency': quote_currency,
            'correlated_pairs': list(set(correlated_pairs)),
            'currency_group': self._get_currency_group(pair)
        }
    
    def _get_currency_group(self, pair: str) -> str:
        """Get the currency group for a pair."""
        for group, pairs in self.currency_groups.items():
            if pair in pairs:
                return group
        return 'OTHER'
