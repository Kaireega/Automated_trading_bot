"""
Chart Generator - Creates trading charts for notifications.
"""
import traceback
from typing import List, Dict, Optional, Any
from datetime import datetime
import plotly.graph_objects as go
import plotly.io as pio
import base64
import io
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from mplfinance.original_flavor import candlestick_ohlc

from ..core.models import CandleData, TradeRecommendation


class ChartGenerator:
    """Generates trading charts for notifications."""
    
    def __init__(self):
        """Initialize the chart generator."""
        # Set default chart style
        pio.templates.default = "plotly_white"
    
    def create_candlestick_chart(self, candles: List[CandleData], trade_recommendation: Optional[TradeRecommendation] = None) -> str:
        """Create a candlestick chart with optional trade signals."""
        try:
            # Prepare data
            dates = [candle.timestamp for candle in candles]
            opens = [float(candle.open) for candle in candles]
            highs = [float(candle.high) for candle in candles]
            lows = [float(candle.low) for candle in candles]
            closes = [float(candle.close) for candle in candles]
            
            # Create the chart
            fig, ax = plt.subplots(figsize=(12, 8))
            
            # Plot candlesticks
            candlestick_ohlc(ax, list(zip(mdates.date2num(dates), opens, highs, lows, closes)), 
                           width=0.6, colorup='green', colordown='red', alpha=0.8)
            
            # Add trade signals if available
            if trade_recommendation:
                # Add entry point
                if trade_recommendation.entry_price:
                    ax.axhline(y=float(trade_recommendation.entry_price), color='blue', linestyle='--', 
                             label=f'Entry: {trade_recommendation.entry_price}')
                
                # Add stop loss
                if trade_recommendation.stop_loss:
                    ax.axhline(y=float(trade_recommendation.stop_loss), color='red', linestyle='--', 
                             label=f'Stop Loss: {trade_recommendation.stop_loss}')
                
                # Add take profit
                if trade_recommendation.take_profit:
                    ax.axhline(y=float(trade_recommendation.take_profit), color='green', linestyle='--', 
                             label=f'Take Profit: {trade_recommendation.take_profit}')
                
                ax.legend()
            
            # Format the chart
            ax.set_title('Price Chart with Trade Signals')
            ax.set_xlabel('Date')
            ax.set_ylabel('Price')
            ax.grid(True, alpha=0.3)
            
            # Format x-axis dates
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
            plt.xticks(rotation=45)
            
            # Convert to base64
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', bbox_inches='tight', dpi=100)
            buffer.seek(0)
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            plt.close()
            
            return img_base64
            
        except Exception as e:
            print(f"❌ [DEBUG] Failed to create chart: {e}")
            print(f"❌ [DEBUG] Traceback: {traceback.format_exc()}")
            return ""
    
    def create_technical_chart(
        self, 
        candles: List[CandleData],
        indicators: Dict[str, Any],
        trade_recommendation: Optional[TradeRecommendation] = None
    ) -> Dict[str, Any]:
        """Create a chart with technical indicators."""
        
        try:
            # Prepare data
            dates = [c.timestamp for c in candles]
            closes = [float(c.close) for c in candles]
            
            # Create figure with secondary y-axis
            fig = go.Figure()
            
            # Add price line
            fig.add_trace(go.Scatter(
                x=dates,
                y=closes,
                mode='lines',
                name='Price',
                line=dict(color='blue')
            ))
            
            # Add technical indicators
            if 'ema_fast' in indicators and indicators['ema_fast']:
                fig.add_trace(go.Scatter(
                    x=dates,
                    y=[indicators['ema_fast']] * len(dates),
                    mode='lines',
                    name='EMA Fast',
                    line=dict(color='orange', dash='dash')
                ))
            
            if 'ema_slow' in indicators and indicators['ema_slow']:
                fig.add_trace(go.Scatter(
                    x=dates,
                    y=[indicators['ema_slow']] * len(dates),
                    mode='lines',
                    name='EMA Slow',
                    line=dict(color='red', dash='dash')
                ))
            
            if 'bollinger_upper' in indicators and indicators['bollinger_upper']:
                fig.add_trace(go.Scatter(
                    x=dates,
                    y=[indicators['bollinger_upper']] * len(dates),
                    mode='lines',
                    name='BB Upper',
                    line=dict(color='gray', dash='dot')
                ))
            
            if 'bollinger_lower' in indicators and indicators['bollinger_lower']:
                fig.add_trace(go.Scatter(
                    x=dates,
                    y=[indicators['bollinger_lower']] * len(dates),
                    mode='lines',
                    name='BB Lower',
                    line=dict(color='gray', dash='dot')
                ))
            
            # Add trade recommendation if provided
            if trade_recommendation:
                self._add_trade_signals(fig, trade_recommendation)
            
            # Update layout
            fig.update_layout(
                title="Technical Analysis Chart",
                xaxis_title="Time",
                yaxis_title="Price",
                height=400,
                width=600
            )
            
            # Convert to image
            img_bytes = fig.to_image(format="png")
            img_base64 = base64.b64encode(img_bytes).decode()
            
            return {
                'image_data': img_base64,
                'image_format': 'png',
                'chart_type': 'technical',
                'data_points': len(candles),
                'indicators': list(indicators.keys())
            }
            
        except Exception as e:
            return {
                'error': f"Failed to create technical chart: {e}",
                'chart_type': 'technical'
            }
    
    def create_performance_chart(self, performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a performance summary chart."""
        
        try:
            # Create bar chart for performance metrics
            metrics = ['Win Rate', 'Profit Factor', 'Sharpe Ratio']
            values = [
                performance_data.get('win_rate', 0) * 100,
                performance_data.get('profit_factor', 0),
                performance_data.get('sharpe_ratio', 0)
            ]
            
            fig = go.Figure(data=[go.Bar(
                x=metrics,
                y=values,
                marker_color=['green', 'blue', 'orange']
            )])
            
            fig.update_layout(
                title="Performance Metrics",
                xaxis_title="Metric",
                yaxis_title="Value",
                height=300,
                width=500
            )
            
            # Convert to image
            img_bytes = fig.to_image(format="png")
            img_base64 = base64.b64encode(img_bytes).decode()
            
            return {
                'image_data': img_base64,
                'image_format': 'png',
                'chart_type': 'performance',
                'metrics': metrics
            }
            
        except Exception as e:
            return {
                'error': f"Failed to create performance chart: {e}",
                'chart_type': 'performance'
            }
    
    def _add_trade_signals(self, fig: go.Figure, recommendation: TradeRecommendation) -> None:
        """Add trade signals to the chart."""
        
        try:
            if recommendation.entry_price:
                # Add entry point
                fig.add_trace(go.Scatter(
                    x=[recommendation.timestamp],
                    y=[float(recommendation.entry_price)],
                    mode='markers',
                    name='Entry',
                    marker=dict(
                        symbol='triangle-up' if recommendation.signal.value == 'buy' else 'triangle-down',
                        size=15,
                        color='green' if recommendation.signal.value == 'buy' else 'red'
                    )
                ))
            
            if recommendation.stop_loss:
                # Add stop loss line
                fig.add_hline(
                    y=float(recommendation.stop_loss),
                    line_dash="dash",
                    line_color="red",
                    annotation_text="Stop Loss"
                )
            
            if recommendation.take_profit:
                # Add take profit line
                fig.add_hline(
                    y=float(recommendation.take_profit),
                    line_dash="dash",
                    line_color="green",
                    annotation_text="Take Profit"
                )
                
        except Exception as e:
            # Silently fail if we can't add signals
            pass
    
    def create_simple_chart(self, data: List[float], labels: List[str], title: str = "Chart") -> Dict[str, Any]:
        """Create a simple line chart."""
        
        try:
            fig = go.Figure(data=[go.Scatter(
                x=labels,
                y=data,
                mode='lines+markers',
                name='Data'
            )])
            
            fig.update_layout(
                title=title,
                xaxis_title="Time",
                yaxis_title="Value",
                height=300,
                width=500
            )
            
            # Convert to image
            img_bytes = fig.to_image(format="png")
            img_base64 = base64.b64encode(img_bytes).decode()
            
            return {
                'image_data': img_base64,
                'image_format': 'png',
                'chart_type': 'simple',
                'data_points': len(data)
            }
            
        except Exception as e:
            return {
                'error': f"Failed to create simple chart: {e}",
                'chart_type': 'simple'
            } 