"""
Enhanced Technical Analyzer - Uses existing technical indicators from technicals/indicators.py
"""
import numpy as np
import pandas as pd
import traceback
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from decimal import Decimal
import sys
from pathlib import Path

# Add the root directory to the path to import technicals
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.append(str(root_dir))

# Add the src directory to the path for absolute imports
src_dir = Path(__file__).parent.parent
sys.path.append(str(src_dir))

# Use absolute imports
try:
    from ..core.models import CandleData, TechnicalIndicators, TimeFrame
except ImportError:
    from core.models import CandleData, TechnicalIndicators, TimeFrame
from technicals.indicators import RSI, MACD, BollingerBands, ATR, KeltnerChannels, Stochastic, EMA
from technicals.patterns import apply_candle_props, set_candle_patterns


class TechnicalAnalyzer:
    """Enhanced technical analyzer using existing technical indicators."""
    
    def __init__(self):
        """Initialize the technical analyzer."""
        self.logger = None  # Will be set by parent class
    
    def calculate_indicators(self, candles: List[CandleData]) -> TechnicalIndicators:
        """Calculate technical indicators using existing technicals/indicators.py functions."""
        if self.logger:
            self.logger.info(f"📈 Starting technical indicator calculation for {len(candles)} candles...")
        
        if len(candles) < 20:
            if self.logger:
                self.logger.info(f"❌ Insufficient candles for technical analysis: {len(candles)} < 20")
            return TechnicalIndicators()
        
        # FILTER OUT CANDLES THAT ARE TOO CLOSE IN TIME
        filtered_candles = self._filter_candles_by_time(candles)
        if len(filtered_candles) < 20:
            if self.logger:
                self.logger.info(f"❌ After time filtering, insufficient candles: {len(filtered_candles)} < 20")
            return TechnicalIndicators()
        
        if self.logger:
            self.logger.info(f"📈 Using {len(filtered_candles)} filtered candles for analysis")
        
        # VALIDATE PRICE MOVEMENTS - Ensure we have meaningful data
        if not self._validate_price_movements(filtered_candles):
            if self.logger:
                self.logger.info("❌ Insufficient price movement for meaningful technical analysis")
            return TechnicalIndicators()
        
        try:
            # Convert candles to DataFrame format expected by technicals
            df = self._candles_to_dataframe(filtered_candles)
            
            # Apply indicators one by one and extract values immediately
            indicators = TechnicalIndicators()
            
            # RSI - FIXED CALCULATION
            try:
                df_rsi = RSI(df, n=14)
                rsi_column = f'RSI_14'
                if rsi_column in df_rsi.columns:
                    latest_rsi = df_rsi.iloc[-1][rsi_column]
                    if pd.notna(latest_rsi) and latest_rsi != 0:
                        indicators.rsi = float(latest_rsi)
                        indicators.rsi_14 = float(latest_rsi)
                        if self.logger:
                            self.logger.debug(f"RSI calculated: {indicators.rsi:.2f}")
                    else:
                        if self.logger:
                            self.logger.warning(f"RSI value is NaN or 0: {latest_rsi}")
                else:
                    if self.logger:
                        self.logger.warning(f"RSI column '{rsi_column}' not found. Available columns: {list(df_rsi.columns)}")
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error calculating RSI: {e}")
                import traceback
                if self.logger:
                    self.logger.error(traceback.format_exc())
            
            # MACD - FIXED CALCULATION
            try:
                df_macd = MACD(df, n_slow=26, n_fast=12, n_signal=9)
                
                # MACD Line
                if 'MACD' in df_macd.columns:
                    latest_macd = df_macd.iloc[-1]['MACD']
                    if pd.notna(latest_macd) and abs(latest_macd) > 1e-10:  # Check for non-zero
                        indicators.macd = float(latest_macd)
                        indicators.macd_line = float(latest_macd)
                        if self.logger:
                            self.logger.debug(f"MACD calculated: {indicators.macd:.6f}")
                    else:
                        if self.logger:
                            self.logger.warning(f"MACD value is NaN or near zero: {latest_macd}")
                else:
                    if self.logger:
                        self.logger.warning(f"MACD column not found. Available columns: {list(df_macd.columns)}")
                
                # MACD Signal
                if 'SIGNAL' in df_macd.columns:
                    latest_signal = df_macd.iloc[-1]['SIGNAL']
                    if pd.notna(latest_signal) and abs(latest_signal) > 1e-10:
                        indicators.macd_signal = float(latest_signal)
                        indicators.macd_signal_line = float(latest_signal)
                        if self.logger:
                            self.logger.debug(f"MACD Signal calculated: {indicators.macd_signal:.6f}")
                    else:
                        if self.logger:
                            self.logger.warning(f"MACD Signal value is NaN or near zero: {latest_signal}")
                else:
                    if self.logger:
                        self.logger.warning(f"MACD Signal column not found. Available columns: {list(df_macd.columns)}")
                
                # MACD Histogram
                if 'HIST' in df_macd.columns:
                    latest_hist = df_macd.iloc[-1]['HIST']
                    if pd.notna(latest_hist):
                        indicators.macd_histogram = float(latest_hist)
                        indicators.macd_histogram_line = float(latest_hist)
                        if self.logger:
                            self.logger.debug(f"MACD Histogram calculated: {indicators.macd_histogram:.6f}")
                    else:
                        if self.logger:
                            self.logger.warning(f"MACD Histogram value is NaN: {latest_hist}")
                else:
                    if self.logger:
                        self.logger.warning(f"MACD Histogram column not found. Available columns: {list(df_macd.columns)}")
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error calculating MACD: {e}")
                import traceback
                if self.logger:
                    self.logger.error(traceback.format_exc())
            
            # Bollinger Bands - FIXED CALCULATION
            try:
                df_bb = BollingerBands(df, n=20, s=2)
                
                # Bollinger Upper
                if 'BB_UP' in df_bb.columns:
                    latest_bb_upper = df_bb.iloc[-1]['BB_UP']
                    if pd.notna(latest_bb_upper) and latest_bb_upper > 0:
                        indicators.bollinger_upper = float(latest_bb_upper)
                        if self.logger:
                            self.logger.debug(f"Bollinger Upper calculated: {indicators.bollinger_upper:.5f}")
                    else:
                        if self.logger:
                            self.logger.warning(f"Bollinger Upper value is NaN or <= 0: {latest_bb_upper}")
                else:
                    if self.logger:
                        self.logger.warning(f"BB_UP column not found. Available columns: {list(df_bb.columns)}")
                
                # Bollinger Lower
                if 'BB_LW' in df_bb.columns:
                    latest_bb_lower = df_bb.iloc[-1]['BB_LW']
                    if pd.notna(latest_bb_lower) and latest_bb_lower > 0:
                        indicators.bollinger_lower = float(latest_bb_lower)
                        if self.logger:
                            self.logger.debug(f"Bollinger Lower calculated: {indicators.bollinger_lower:.5f}")
                    else:
                        if self.logger:
                            self.logger.warning(f"Bollinger Lower value is NaN or <= 0: {latest_bb_lower}")
                else:
                    if self.logger:
                        self.logger.warning(f"BB_LW column not found. Available columns: {list(df_bb.columns)}")
                
                # Bollinger Middle
                if 'BB_MA' in df_bb.columns:
                    latest_bb_middle = df_bb.iloc[-1]['BB_MA']
                    if pd.notna(latest_bb_middle) and latest_bb_middle > 0:
                        indicators.bollinger_middle = float(latest_bb_middle)
                        indicators.bb_ma = float(latest_bb_middle)
                        if self.logger:
                            self.logger.debug(f"Bollinger Middle calculated: {indicators.bollinger_middle:.5f}")
                    else:
                        if self.logger:
                            self.logger.warning(f"Bollinger Middle value is NaN or <= 0: {latest_bb_middle}")
                else:
                    if self.logger:
                        self.logger.warning(f"BB_MA column not found. Available columns: {list(df_bb.columns)}")
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error calculating Bollinger Bands: {e}")
                import traceback
                if self.logger:
                    self.logger.error(traceback.format_exc())
            
            # ATR - FIXED CALCULATION
            try:
                df_atr = ATR(df, n=14)
                
                if 'ATR_14' in df_atr.columns:
                    latest_atr = df_atr.iloc[-1]['ATR_14']
                    if pd.notna(latest_atr) and latest_atr > 0:
                        indicators.atr = float(latest_atr)
                        indicators.atr_14 = float(latest_atr)
                        if self.logger:
                            self.logger.debug(f"ATR calculated: {indicators.atr:.6f}")
                    else:
                        if self.logger:
                            self.logger.warning(f"ATR value is NaN or <= 0: {latest_atr}")
                else:
                    if self.logger:
                        self.logger.warning(f"ATR_14 column not found. Available columns: {list(df_atr.columns)}")
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error calculating ATR: {e}")
                import traceback
                if self.logger:
                    self.logger.error(traceback.format_exc())
                else:
                    if self.logger:
                        self.logger.warning("ATR_14 column not found in DataFrame")
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error calculating ATR: {e}")
            
            # Keltner Channels
            try:
                df_keltner = KeltnerChannels(df, n_ema=20, n_atr=10)
                if 'KeUp' in df_keltner.columns:
                    latest_keltner_upper = df_keltner.iloc[-1]['KeUp']
                    if pd.notna(latest_keltner_upper):
                        indicators.keltner_upper = float(latest_keltner_upper)
                
                if 'KeLo' in df_keltner.columns:
                    latest_keltner_lower = df_keltner.iloc[-1]['KeLo']
                    if pd.notna(latest_keltner_lower):
                        indicators.keltner_lower = float(latest_keltner_lower)
                
                if 'EMA' in df_keltner.columns:
                    latest_ema = df_keltner.iloc[-1]['EMA']
                    if pd.notna(latest_ema):
                        indicators.keltner_middle = float(latest_ema)
                        indicators.ema_fast = float(latest_ema)
                        indicators.ema_slow = float(latest_ema)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error calculating Keltner Channels: {e}")
            
            # Stochastic Oscillator
            try:
                df_stoch = Stochastic(df, n=14, k=3, d=3)
                if 'STOCH_K' in df_stoch.columns:
                    latest_stoch_k = df_stoch.iloc[-1]['STOCH_K']
                    if pd.notna(latest_stoch_k):
                        indicators.stoch_k = float(latest_stoch_k)
                
                if 'STOCH_D' in df_stoch.columns:
                    latest_stoch_d = df_stoch.iloc[-1]['STOCH_D']
                    if pd.notna(latest_stoch_d):
                        indicators.stoch_d = float(latest_stoch_d)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error calculating Stochastic: {e}")
            
            # EMA (Fast and Slow)
            try:
                df_ema = EMA(df, n=12, column='mid_c')  # Fast EMA
                df_ema = EMA(df_ema, n=26, column='mid_c')  # Slow EMA
                
                if 'EMA_12' in df_ema.columns:
                    latest_ema_fast = df_ema.iloc[-1]['EMA_12']
                    if pd.notna(latest_ema_fast):
                        indicators.ema_fast = float(latest_ema_fast)
                
                if 'EMA_26' in df_ema.columns:
                    latest_ema_slow = df_ema.iloc[-1]['EMA_26']
                    if pd.notna(latest_ema_slow):
                        indicators.ema_slow = float(latest_ema_slow)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error calculating EMA: {e}")
            
            # Support/Resistance (simple min/max of recent data)
            try:
                if len(df) > 0:
                    indicators.support_level = float(df['mid_l'].min())
                    indicators.resistance_level = float(df['mid_h'].max())
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error calculating support/resistance: {e}")
            
            # Return the calculated indicators
            return indicators
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ Error calculating technical indicators: {e}")
            return TechnicalIndicators()
    
    async def calculate_all_indicators(self, candles_by_timeframe: Dict[str, List[CandleData]], 
                                     market_context: Any) -> TechnicalIndicators:
        """Calculate all technical indicators for multiple timeframes."""
        try:
            # Get the primary timeframe (usually M5)
            primary_timeframe = list(candles_by_timeframe.keys())[0]
            primary_candles = candles_by_timeframe[primary_timeframe]
            
            if len(primary_candles) < 20:
                return TechnicalIndicators()
            
            # Calculate indicators using the existing method
            indicators = self.calculate_indicators(primary_candles)
            
            return indicators
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ Error calculating multi-timeframe technical indicators: {e}")
            return TechnicalIndicators()
    
    def _candles_to_dataframe(self, candles: List[CandleData]) -> pd.DataFrame:
        """Convert CandleData list to DataFrame format expected by technicals."""
        data = []
        for candle in candles:
            data.append({
                'mid_o': float(candle.open),
                'mid_h': float(candle.high),
                'mid_l': float(candle.low),
                'mid_c': float(candle.close),
                'volume': float(candle.volume) if candle.volume else 0
            })
        
        df = pd.DataFrame(data)
        return df
    
    def calculate_volatility(self, candles: List[CandleData], period: int = 20) -> float:
        """Calculate volatility using existing ATR indicator."""
        if len(candles) < period:
            return 0.0
        
        try:
            df = self._candles_to_dataframe(candles)
            df = ATR(df, n=period)
            latest_atr = df.iloc[-1].get(f'ATR_{period}', 0)
            return float(latest_atr) if pd.notna(latest_atr) else 0.0
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error calculating volatility: {e}")
            return 0.0
    
    def calculate_momentum(self, candles: List[CandleData], period: int = 10) -> float:
        """Calculate momentum using RSI."""
        if len(candles) < period:
            return 0.0
        
        try:
            df = self._candles_to_dataframe(candles)
            df = RSI(df, n=period)
            latest_rsi = df.iloc[-1].get(f'RSI_{period}', 50)
            return float(latest_rsi) if pd.notna(latest_rsi) else 50.0
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error calculating momentum: {e}")
            return 50.0
    
    def detect_patterns(self, candles: List[CandleData]) -> dict:
        """Detect candlestick patterns using existing patterns."""
        if len(candles) < 3:
            return {}
        
        try:
            df = self._candles_to_dataframe(candles)
            df = apply_candle_props(df)
            df = set_candle_patterns(df)
            
            latest = df.iloc[-1]
            patterns = {}
            
            # Check for various patterns
            pattern_columns = [col for col in df.columns if col.startswith('pattern_')]
            for col in pattern_columns:
                if latest.get(col, False):
                    pattern_name = col.replace('pattern_', '')
                    patterns[pattern_name] = True
            
            return patterns
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error detecting patterns: {e}")
            return {}
    
    def get_trend_analysis(self, candles: List[CandleData]) -> Dict[str, Any]:
        """Get comprehensive trend analysis using existing indicators."""
        if len(candles) < 20:
            return {}
        
        try:
            df = self._candles_to_dataframe(candles)
            
            # Apply all indicators
            df = RSI(df, n=14)
            df = MACD(df, n_slow=26, n_fast=12, n_signal=9)
            df = BollingerBands(df, n=20, s=2)
            df = ATR(df, n=14)
            df = KeltnerChannels(df, n_ema=20, n_atr=10)
            df = Stochastic(df, n=14, k=3, d=3)
            df = EMA(df, n=12, column='mid_c')
            df = EMA(df, n=26, column='mid_c')
            df = apply_candle_props(df)
            df = set_candle_patterns(df)
            
            latest = df.iloc[-1]
            
            # Determine trend direction
            current_price = latest['mid_c']
            bb_upper = latest.get('BB_UP', current_price)
            bb_lower = latest.get('BB_LW', current_price)
            bb_middle = latest.get('BB_MA', current_price)
            
            # Trend analysis
            if current_price > bb_upper:
                trend = "strong_uptrend"
            elif current_price > bb_middle:
                trend = "uptrend"
            elif current_price < bb_lower:
                trend = "strong_downtrend"
            elif current_price < bb_middle:
                trend = "downtrend"
            else:
                trend = "sideways"
            
            return {
                'trend': trend,
                'rsi': float(latest.get('RSI_14', 50)),
                'macd': float(latest.get('MACD', 0)),
                'macd_signal': float(latest.get('SIGNAL', 0)),
                'macd_histogram': float(latest.get('HIST', 0)),
                'bollinger_upper': float(bb_upper),
                'bollinger_middle': float(bb_middle),
                'bollinger_lower': float(bb_lower),
                'atr': float(latest.get('ATR_14', 0)),
                'volatility': float(latest.get('ATR_14', 0)),
                'stoch_k': float(latest.get('STOCH_K', 50)),
                'stoch_d': float(latest.get('STOCH_D', 50)),
                'ema_fast': float(latest.get('EMA_12', current_price)),
                'ema_slow': float(latest.get('EMA_26', current_price)),
                'support': float(df['mid_l'].min()),
                'resistance': float(df['mid_h'].max())
            }
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error in trend analysis: {e}")
            return {}
    
    def _filter_candles_by_time(self, candles: List[CandleData]) -> List[CandleData]:
        """Filter out candles that are too close in time to prevent calculation errors."""
        if len(candles) < 2:
            return candles
        
        filtered_candles = [candles[0]]  # Always include the first candle
        min_time_diff = 60  # 1 minute in seconds - only filter out very close duplicates
        
        for i in range(1, len(candles)):
            current_candle = candles[i]
            last_filtered_candle = filtered_candles[-1]
            
            # Calculate time difference in seconds
            time_diff = (current_candle.timestamp - last_filtered_candle.timestamp).total_seconds()
            
            # Only filter out candles that are less than 1 minute apart (duplicates/errors)
            # This allows M5, M15, M30, H1, etc. data to pass through normally
            if time_diff >= min_time_diff:
                filtered_candles.append(current_candle)
                if self.logger:
                    self.logger.debug(f"✅ Included candle at {current_candle.timestamp} (diff: {time_diff:.0f}s)")
            else:
                if self.logger:
                    self.logger.debug(f"⏰ Skipped duplicate candle at {current_candle.timestamp} (diff: {time_diff:.0f}s < {min_time_diff}s)")
        
        if self.logger:
            if len(filtered_candles) != len(candles):
                self.logger.info(f"📊 Filtered {len(candles)} candles to {len(filtered_candles)} candles (removed duplicates)")
        
        return filtered_candles
    
    def _validate_price_movements(self, candles: List[CandleData]) -> bool:
        """Validate that we have sufficient price movement for meaningful analysis."""
        if len(candles) < 5:
            return False
        
        try:
            # Calculate price range
            prices = [float(c.close) for c in candles]
            min_price = min(prices)
            max_price = max(prices)
            
            # Calculate price range as percentage
            if min_price > 0:
                price_range_pct = ((max_price - min_price) / min_price) * 100
            else:
                return False
            
            # Calculate average price movement between consecutive candles
            price_changes = []
            for i in range(1, len(prices)):
                if prices[i-1] > 0:
                    change_pct = abs((prices[i] - prices[i-1]) / prices[i-1]) * 100
                    price_changes.append(change_pct)
            
            avg_change = sum(price_changes) / len(price_changes) if price_changes else 0
            
            # Require minimum price movement
            min_range_pct = 0.01  # 0.01% minimum range
            min_avg_change = 0.001  # 0.001% minimum average change
            
            has_sufficient_movement = (price_range_pct >= min_range_pct and avg_change >= min_avg_change)
            
            if self.logger:
                self.logger.debug(f"📊 Price validation: range={price_range_pct:.4f}%, avg_change={avg_change:.4f}%, sufficient={has_sufficient_movement}")
            
            return has_sufficient_movement
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error validating price movements: {e}")
            return False 