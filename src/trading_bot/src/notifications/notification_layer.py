"""
Notification Layer - Sends trade alerts via multiple channels.
"""
import asyncio
import traceback
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from decimal import Decimal
import json
import base64
import io

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

from ..core.models import TradeDecision, NotificationMessage, UserResponse
from ..utils.config import Config
from ..utils.logger import get_logger
from .chart_generator import ChartGenerator
from .callback_handler import CallbackHandler


class NotificationLayer:
    """Handles sending trade notifications via multiple channels."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger(__name__)
        
        # Initialize notification channels
        self._init_telegram()
        self._init_email()
        
        # Initialize chart generator
        self.chart_generator = ChartGenerator()
        
        # Initialize callback handler
        self.callback_handler = CallbackHandler(config, self)
        
        # Notification tracking
        self._sent_notifications: Dict[str, NotificationMessage] = {}
        self._notification_queue: List[NotificationMessage] = []
        
        # Rate limiting
        self._last_notification_time: Dict[str, datetime] = {}

        # External trade executor (set by main) for manual approvals
        self._trade_executor = None

    def set_trade_executor(self, executor):
        """Register an async executor callable(decision) -> trade_id used by manual approvals."""
        self._trade_executor = executor
    
    def _init_telegram(self) -> None:
        """Initialize Telegram bot."""
        try:
            if self.config.telegram_enabled:
                self.telegram_bot = Bot(token=self.config.telegram_bot_token)
                self.logger.info("Telegram bot initialized")
            else:
                self.telegram_bot = None
        except Exception as e:
            self.logger.error(f"Failed to initialize Telegram bot: {e}")
            self.telegram_bot = None
    
    def _init_email(self) -> None:
        """Initialize email configuration."""
        try:
            print(f"📧 [DEBUG] Email enabled: {self.config.email_enabled}")
            print(f"📧 [DEBUG] SMTP server: {self.config.smtp_server}")
            print(f"📧 [DEBUG] SMTP port: {self.config.smtp_port}")
            print(f"📧 [DEBUG] Email username: {self.config.email_username}")
            print(f"📧 [DEBUG] Email password: {'*' * len(self.config.email_password) if self.config.email_password else 'None'}")
            
            if self.config.email_enabled:
                self.smtp_server = self.config.smtp_server
                self.smtp_port = self.config.smtp_port
                self.email_username = self.config.email_username
                self.email_password = self.config.email_password
                self.logger.info("Email configuration initialized")
                print(f"✅ [DEBUG] Email configuration initialized successfully")
            else:
                self.smtp_server = None
                print(f"❌ [DEBUG] Email is disabled in configuration")
        except Exception as e:
            self.logger.error(f"Failed to initialize email configuration: {e}")
            self.smtp_server = None
            print(f"❌ [DEBUG] Failed to initialize email configuration: {e}")
    
    async def send_trade_alert(self, trade_decision: TradeDecision, chart_data: Optional[Dict] = None, custom_message: Optional[str] = None) -> bool:
        """Send trade alert notification."""
        
        try:
            # Rate limit per pair
            try:
                if not self.can_send_notification(trade_decision.recommendation.pair):
                    self.logger.info(f"Cooldown active for {trade_decision.recommendation.pair}; skipping alert")
                    return False
            except Exception:
                pass

            # Create notification message
            notification = self._create_trade_notification(trade_decision, chart_data, custom_message)
            
            # Add to queue
            self._notification_queue.append(notification)
            
            # Send notifications
            success = True
            
            if self.config.telegram_enabled and self.telegram_bot:
                telegram_success = await self._send_telegram_notification(notification)
                success = success and telegram_success
            
            if self.config.email_enabled and self.smtp_server:
                email_success = await self._send_email_notification(notification)
                success = success and email_success
            
            # Track sent notification
            if success:
                self._sent_notifications[notification.id] = notification
                from datetime import datetime, timezone
                self._last_notification_time[trade_decision.recommendation.pair] = datetime.now(timezone.utc)
                
                # Register notification for callback handling
                self.callback_handler.register_notification(notification)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending trade alert: {e}")
            return False
    
    def _create_trade_notification(
        self, 
        trade_decision: TradeDecision, 
        chart_data: Optional[Dict] = None,
        custom_message: Optional[str] = None
    ) -> NotificationMessage:
        """Create notification message from trade decision."""
        
        recommendation = trade_decision.recommendation
        
        # Create title
        title = f"🚨 {recommendation.signal.value.upper()} Signal: {recommendation.pair}"
        
        # Create message - use custom message if provided, otherwise use default formatting
        message = custom_message if custom_message else self._format_trade_message(trade_decision)
        
        # Create interactive buttons
        buttons = [
            [
                InlineKeyboardButton("✅ Accept", callback_data=f"accept_{trade_decision.recommendation.id}"),
                InlineKeyboardButton("✏️ Edit", callback_data=f"edit_{trade_decision.recommendation.id}"),
                InlineKeyboardButton("❌ Deny", callback_data=f"deny_{trade_decision.recommendation.id}")
            ]
        ]
        
        # Charts are generated on demand in channel-specific senders
        
        return NotificationMessage(
            title=title,
            message=message,
            trade_decision=trade_decision,
            chart_data=chart_data,
            buttons=buttons,
            priority="high" if recommendation.confidence > 0.8 else "normal"
        )
    
    def _format_trade_message(self, trade_decision: TradeDecision) -> str:
        """Format trade decision into readable message."""
        
        rec = trade_decision.recommendation
        # Safe numeric formatting
        entry_str = f"{rec.entry_price:.5f}" if rec.entry_price is not None else "N/A"
        sl_str = f"{rec.stop_loss:.5f}" if rec.stop_loss is not None else "N/A"
        tp_str = f"{rec.take_profit:.5f}" if rec.take_profit is not None else "N/A"
        conf_str = f"{rec.confidence:.1%}" if rec.confidence is not None else "N/A"
        rr_str = f"{rec.risk_reward_ratio:.2f}" if rec.risk_reward_ratio is not None else "N/A"
        
        message = f"""
🎯 {rec.signal.value.upper()} Signal Detected

📊 Pair: {rec.pair}
💰 Entry Price: {entry_str}
🛑 Stop Loss: {sl_str}
🎯 Take Profit: {tp_str}

📈 Confidence: {conf_str}
⚖️ Risk/Reward: {rr_str}
⏱️ Hold Time: {rec.estimated_hold_time}
🌍 Market Condition: {rec.market_condition.value.replace('_', ' ').title()}

💡 AI Reasoning:
{rec.reasoning}

🔒 Risk Management:
• Position Size: {trade_decision.position_size if trade_decision.position_size else 'N/A'}
• Risk Amount: {trade_decision.risk_amount if trade_decision.risk_amount else 'N/A'}
• Notes: {trade_decision.risk_management_notes}

⏰ Timestamp: {rec.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}
"""
        
        return message.strip()
    
    async def _send_telegram_notification(self, notification: NotificationMessage) -> bool:
        """Send notification via Telegram."""
        
        try:
            # Create inline keyboard
            keyboard = InlineKeyboardMarkup(notification.buttons)
            
            # Send message
            # Sanitize to avoid markdown parse errors
            clean_message = notification.message.replace('*', '').replace('_', '').replace('`', '').replace('[', '').replace(']', '')
            await self.telegram_bot.send_message(
                chat_id=self.config.telegram_chat_id,
                text=clean_message,
                parse_mode=None,
                reply_markup=keyboard
            )
            
            # Send chart if available
            if notification.chart_data and self.config.send_charts:
                chart_image = self.chart_generator.generate_chart(notification.chart_data)
                if chart_image:
                    await self.telegram_bot.send_photo(
                        chat_id=self.config.telegram_chat_id,
                        photo=chart_image,
                        caption=f"📊 Chart for {notification.trade_decision.recommendation.pair}"
                    )
            
            self.logger.info(f"Telegram notification sent for {notification.trade_decision.recommendation.pair}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending Telegram notification: {e}")
            return False
    
    async def _send_email_notification(self, notification: NotificationMessage) -> bool:
        """Send notification via email."""
        
        try:
            # Create email message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = notification.title
            msg['From'] = self.email_username
            msg['To'] = self.config.email_username  # Send to self for now
            
            # Create HTML version
            html_message = self._create_html_email(notification)
            html_part = MIMEText(html_message, 'html')
            msg.attach(html_part)
            
            # Create plain text version
            text_part = MIMEText(notification.message, 'plain')
            msg.attach(text_part)
            
            # Attach chart if available
            if notification.chart_data and self.config.send_charts:
                chart_image = self.chart_generator.generate_chart(notification.chart_data)
                if chart_image:
                    image_part = MIMEImage(chart_image)
                    image_part.add_header('Content-ID', '<chart>')
                    image_part.add_header('Content-Disposition', 'inline', filename='chart.png')
                    msg.attach(image_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_username, self.email_password)
                server.send_message(msg)
            
            self.logger.info(f"Email notification sent for {notification.trade_decision.recommendation.pair}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending email notification: {e}")
            return False
    
    def _create_html_email(self, notification: NotificationMessage) -> str:
        """Create HTML version of email."""
        
        rec = notification.trade_decision.recommendation
        entry_str = f"{rec.entry_price:.5f}" if rec.entry_price is not None else "N/A"
        sl_str = f"{rec.stop_loss:.5f}" if rec.stop_loss is not None else "N/A"
        tp_str = f"{rec.take_profit:.5f}" if rec.take_profit is not None else "N/A"
        conf_str = f"{rec.confidence:.1%}" if rec.confidence is not None else "N/A"
        rr_str = f"{rec.risk_reward_ratio:.2f}" if rec.risk_reward_ratio is not None else "N/A"
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; }}
                .signal {{ font-size: 24px; font-weight: bold; color: {'#28a745' if rec.signal.value == 'buy' else '#dc3545'}; }}
                .details {{ margin: 20px 0; }}
                .detail-row {{ display: flex; justify-content: space-between; margin: 10px 0; }}
                .label {{ font-weight: bold; }}
                .reasoning {{ background-color: #e9ecef; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .buttons {{ margin: 20px 0; }}
                .button {{ display: inline-block; padding: 10px 20px; margin: 5px; text-decoration: none; border-radius: 5px; }}
                .accept {{ background-color: #28a745; color: white; }}
                .edit {{ background-color: #ffc107; color: black; }}
                .deny {{ background-color: #dc3545; color: white; }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="signal">{rec.signal.value.upper()} Signal: {rec.pair}</div>
                <p>AI-powered trading recommendation</p>
            </div>
            
            <div class="details">
                <div class="detail-row">
                    <span class="label">Entry Price:</span>
                    <span>{entry_str}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Stop Loss:</span>
                    <span>{sl_str}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Take Profit:</span>
                    <span>{tp_str}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Confidence:</span>
                    <span>{conf_str}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Risk/Reward:</span>
                    <span>{rr_str}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Market Condition:</span>
                    <span>{rec.market_condition.value.replace('_', ' ').title()}</span>
                </div>
            </div>
            
            <div class="reasoning">
                <h3>AI Reasoning:</h3>
                <p>{rec.reasoning}</p>
            </div>
            
            <div class="buttons">
                <a href="mailto:?subject=Accept Trade {rec.id}&body=I accept this trade recommendation" class="button accept">✅ Accept</a>
                <a href="mailto:?subject=Edit Trade {rec.id}&body=I want to edit this trade" class="button edit">✏️ Edit</a>
                <a href="mailto:?subject=Deny Trade {rec.id}&body=I deny this trade recommendation" class="button deny">❌ Deny</a>
            </div>
            
            <p><small>Timestamp: {rec.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</small></p>
        </body>
        </html>
        """
        
        return html
    
    async def send_daily_summary(self, performance_metrics: Any) -> bool:
        """Send daily performance summary."""
        
        try:
            title = "📊 Daily Trading Summary"
            message = self._format_daily_summary(performance_metrics)
            
            notification = NotificationMessage(
                title=title,
                message=message,
                priority="normal"
            )
            
            success = True
            
            if self.config.telegram_enabled and self.telegram_bot:
                await self.telegram_bot.send_message(
                    chat_id=self.config.telegram_chat_id,
                    text=notification.message,
                    parse_mode='Markdown'
                )
            
            if self.config.email_enabled and self.smtp_server:
                await self._send_email_notification(notification)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending daily summary: {e}")
            return False
    
    def _format_daily_summary(self, metrics: Any) -> str:
        """Format daily performance metrics."""
        
        message = f"""
📊 Daily Trading Summary

📈 Performance:
• Total Trades: {metrics.total_trades}
• Winning Trades: {metrics.winning_trades}
• Losing Trades: {metrics.losing_trades}
• Win Rate: {metrics.win_rate:.1%}

💰 P&L:
• Total Profit: {metrics.total_profit:.2f}
• Total Loss: {metrics.total_loss:.2f}
• Net Profit: {metrics.net_profit:.2f}
• Profit Factor: {metrics.profit_factor:.2f}

📉 Risk Metrics:
• Max Drawdown: {metrics.max_drawdown:.2f}
• Average Win: {metrics.average_win:.2f}
• Average Loss: {metrics.average_loss:.2f}
• Sharpe Ratio: {metrics.sharpe_ratio:.2f}

⏰ Period: {metrics.period_start.strftime('%Y-%m-%d')} to {metrics.period_end.strftime('%Y-%m-%d')}
"""
        
        return message.strip()
    
    async def send_error_alert(self, error_message: str, context: str = "") -> bool:
        """Send error alert notification."""
        
        try:
            title = "🚨 System Error Alert"
            message = f"""
🚨 System Error Detected

📍 Context: {context}
❌ Error: {error_message}
⏰ Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

Please check the system logs for more details.
"""
            
            notification = NotificationMessage(
                title=title,
                message=message,
                priority="urgent"
            )
            
            success = True
            
            if self.config.telegram_enabled and self.telegram_bot:
                await self.telegram_bot.send_message(
                    chat_id=self.config.telegram_chat_id,
                    text=notification.message,
                    parse_mode='Markdown'
                )
            
            if self.config.email_enabled and self.smtp_server:
                await self._send_email_notification(notification)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending error alert: {e}")
            return False
    
    def can_send_notification(self, pair: str) -> bool:
        """Check if we can send a notification for this pair (rate limiting)."""
        
        if pair not in self._last_notification_time:
            return True
        
        from datetime import datetime, timezone
        time_since_last = datetime.now(timezone.utc) - self._last_notification_time[pair]
        return time_since_last.total_seconds() >= self.config.notification_cooldown
    
    async def _initialize_email_config(self):
        """Initialize email configuration."""
        try:
            if self.config.email_enabled:
                print(f"📧 [DEBUG] Email enabled: {self.config.email_enabled}")
                print(f"📧 [DEBUG] SMTP server: {self.config.smtp_server}")
                print(f"📧 [DEBUG] SMTP port: {self.config.smtp_port}")
                print(f"📧 [DEBUG] Email username: {self.config.email_username}")
                print(f"📧 [DEBUG] Email password: {'*' * len(self.config.email_password) if self.config.email_password else 'None'}")
                
                # Test email configuration
                self.smtp_server = self.config.smtp_server
                self.smtp_port = self.config.smtp_port
                self.email_username = self.config.email_username
                self.email_password = self.config.email_password
                
                print(f"✅ [DEBUG] Email configuration initialized successfully")
                self.logger.info("Email configuration initialized")
            else:
                print(f"❌ [DEBUG] Email is disabled in configuration")
        except Exception as e:
            print(f"❌ [DEBUG] Failed to initialize email configuration: {e}")
            self.logger.error(f"Failed to initialize email configuration: {e}")

    async def start(self) -> None:
        """Start the notification layer."""
        try:
            # Initialize Telegram bot
            if self.config.telegram_enabled and self.config.telegram_bot_token:
                self.telegram_bot = Bot(token=self.config.telegram_bot_token)
                self.logger.info("Telegram bot initialized")
            
            # Initialize email configuration
            if self.config.email_enabled:
                await self._initialize_email_config()
            
            self.logger.info("Notification layer started successfully")

            # Start callback handler to process Accept/Edit/Deny actions
            try:
                await self.callback_handler.start()
            except Exception as e:
                self.logger.error(f"Failed to start callback handler: {e}")
            
        except Exception as e:
            print(f"❌ [DEBUG] Error starting notification layer: {e}")
            print(f"❌ [DEBUG] Traceback: {traceback.format_exc()}")
            self.logger.error(f"Error starting notification layer: {e}")
            raise
    
    async def close(self) -> None:
        """Close notification layer."""
        try:
            # Clear queues
            self._notification_queue.clear()
            self._sent_notifications.clear()
            
            self.logger.info("Notification layer closed")
        except Exception as e:
            self.logger.error(f"Error closing notification layer: {e}") 

    async def send_notification(self, notification_type: str, data: Dict[str, Any]) -> bool:
        """Send notification based on type and data."""
        self.logger.info(f"📢 Starting notification process: {notification_type}")
        self.logger.info(f"📊 Notification data keys: {list(data.keys())}")
        
        try:
            if notification_type == "STARTUP":
                self.logger.info("🚀 Sending startup notification...")
                success = await self._send_startup_notification(data)
                self.logger.info(f"✅ Startup notification result: {success}")
                return success
                
            elif notification_type == "TRADE_ALERT":
                self.logger.info("📈 Sending trade alert notification...")
                success = await self._send_trade_alert(data)
                self.logger.info(f"✅ Trade alert result: {success}")
                return success
                
            elif notification_type == "LOOP_REPORT":
                self.logger.info("📊 Sending loop report notification...")
                success = await self._send_loop_report(data)
                self.logger.info(f"✅ Loop report result: {success}")
                return success
                
            elif notification_type == "ERROR_ALERT":
                self.logger.info("⚠️ Sending error alert notification...")
                success = await self._send_error_alert(data)
                self.logger.info(f"✅ Error alert result: {success}")
                return success
                
            else:
                self.logger.warning(f"⚠️ Unknown notification type: {notification_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error sending notification {notification_type}: {e}")
            return False
    
    async def _send_startup_notification(self, data: Dict[str, Any]) -> bool:
        """Send startup notification."""
        try:
            message = data.get('message', 'Bot started successfully')
            
            if self.telegram_bot:
                # Clean message for Telegram (remove special characters that cause parsing issues)
                clean_message = message.replace('*', '').replace('_', '').replace('`', '').replace('[', '').replace(']', '')
                await self.telegram_bot.send_message(
                    chat_id=self.config.telegram_chat_id,
                    text=clean_message,
                    parse_mode=None  # Disable markdown parsing to avoid entity errors
                )
                self.logger.info("Telegram startup message sent successfully")
            
            print(f"📧 [DEBUG] Checking email condition: smtp_server={self.smtp_server}, email_enabled={self.config.email_enabled}")
            if self.smtp_server and self.config.email_enabled:
                print(f"📧 [DEBUG] Email condition met, sending startup email...")
                await self._send_email(
                    subject="🤖 Trading Bot Started",
                    body=message
                )
                self.logger.info("Email startup message sent successfully")
                print(f"✅ [DEBUG] Email startup message sent successfully")
            else:
                print(f"❌ [DEBUG] Email condition not met: smtp_server={self.smtp_server}, email_enabled={self.config.email_enabled}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending startup notification: {e}")
            return False
    
    async def _send_trade_alert(self, data: Dict[str, Any]) -> bool:
        """Send trade alert notification."""
        try:
            # This would be called with trade decision data
            # For now, just log that it was called
            self.logger.info("Trade alert notification requested")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending trade alert: {e}")
            return False
    
    async def _send_loop_report(self, data: Dict[str, Any]) -> bool:
        """Send loop report notification."""
        try:
            message = data.get('message', 'Loop report')
            
            if self.telegram_bot:
                # Clean message for Telegram (remove special characters that cause parsing issues)
                clean_message = message.replace('*', '').replace('_', '').replace('`', '').replace('[', '').replace(']', '')
                await self.telegram_bot.send_message(
                    chat_id=self.config.telegram_chat_id,
                    text=clean_message,
                    parse_mode=None  # Disable markdown parsing to avoid entity errors
                )
                self.logger.info("Telegram loop report sent successfully")
            
            if self.smtp_server and self.config.email_enabled:
                await self._send_email(
                    subject="📊 Trading Loop Report",
                    body=message
                )
                self.logger.info("Email loop report sent successfully")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending loop report: {e}")
            return False
    
    async def _send_error_alert(self, data: Dict[str, Any]) -> bool:
        """Send error alert notification."""
        try:
            error_message = data.get('message', 'Unknown error')
            
            if self.telegram_bot:
                await self.telegram_bot.send_message(
                    chat_id=self.config.telegram_chat_id,
                    text=f"⚠️ ERROR ALERT\n\n{error_message}",
                    parse_mode='Markdown'
                )
                self.logger.info("Telegram error alert sent successfully")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending error alert: {e}")
            return False

    async def execute_approved_trade(self, trade_decision: TradeDecision) -> Optional[str]:
        """Execute a trade after manual approval using the registered executor."""
        try:
            if self._trade_executor is None:
                self.logger.error("Trade executor not set; cannot execute approved trade")
                return None
            trade_id = await self._trade_executor(trade_decision)
            return trade_id
        except Exception as e:
            self.logger.error(f"Error executing approved trade: {e}")
            return None

    async def _send_email(self, subject: str, body: str) -> bool:
        """Send a simple email message."""
        try:
            if not self.smtp_server or not self.email_username or not self.email_password:
                self.logger.error("Email configuration incomplete")
                return False
            
            # Create email message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.email_username
            msg['To'] = self.email_username  # Send to self for now
            
            # Create HTML version
            html_body = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .header {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; }}
                    .content {{ margin: 20px 0; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h2>Trading Bot Notification</h2>
                </div>
                <div class="content">
                    {body.replace(chr(10), '<br>')}
                </div>
            </body>
            </html>
            """
            
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
            
            # Create plain text version
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_username, self.email_password)
                server.send_message(msg)
            
            self.logger.info(f"Email sent successfully: {subject}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending email: {e}")
            return False

    def get_telegram_chat_id_help(self):
        """Print instructions for getting the correct Telegram chat ID."""
        help_text = """
🔧 TELEGRAM SETUP HELP:

To get your correct Telegram Chat ID:

1. Start a chat with your bot (@your_bot_name)
2. Send any message to the bot (like "hello")
3. Visit this URL in your browser:
   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
4. Look for "chat":{"id":123456789} in the response
5. Copy that number and update your .env file:
   TELEGRAM_CHAT_ID=123456789

Current bot token: {self.config.telegram_bot_token}
Current chat ID: {self.config.telegram_chat_id}
"""
        self.logger.info(help_text) 