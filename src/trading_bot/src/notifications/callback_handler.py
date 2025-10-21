"""
Callback Handler - Processes user responses to trade notifications.
"""
import asyncio
import threading
import logging
import traceback
from datetime import datetime
from typing import Dict, Optional, Any
from decimal import Decimal

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, MessageHandler, filters, ContextTypes

from ..core.models import UserResponse, TradeDecision, NotificationMessage
from ..utils.config import Config
from ..utils.logger import get_logger


class CallbackHandler:
    """Handles user responses to trade notifications."""
    
    def __init__(self, config: Config, notification_layer):
        self.config = config
        self.notification_layer = notification_layer
        self.logger = get_logger(__name__)
        
        # Store active notifications
        self.active_notifications: Dict[str, NotificationMessage] = {}
        
        # Initialize Telegram application
        self._init_telegram_app()
        # Polling thread state
        self._polling_thread: Optional[threading.Thread] = None
        self._polling_started: bool = False
    
    def _init_telegram_app(self):
        """Initialize Telegram application with handlers."""
        try:
            if self.config.telegram_enabled:
                self.app = Application.builder().token(self.config.telegram_bot_token).build()
                
                # Add callback query handler for inline buttons
                self.app.add_handler(CallbackQueryHandler(self._handle_callback_query))
                
                # Add message handler for text responses
                self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text_message))
                
                self.logger.info("Telegram callback handlers initialized")
            else:
                self.app = None
        except Exception as e:
            self.logger.error(f"Failed to initialize Telegram app: {e}")
            self.app = None
    
    async def start(self):
        """Start the callback handler."""
        try:
            # Initialize the webhook
            await self._setup_webhook()
            self.logger.info("Callback handler started successfully")
            
        except Exception as e:
            print(f"❌ [DEBUG] Error starting callback handler: {e}")
            print(f"❌ [DEBUG] Traceback: {traceback.format_exc()}")
            self.logger.error(f"Error starting callback handler: {e}")
            raise
    
    async def _start_polling(self):
        """Start polling in a dedicated background thread to avoid event-loop conflicts."""
        try:
            if self.app and not self._polling_started:
                # Launch a daemon thread that blocks in run_polling()
                def _worker():
                    try:
                        # run_polling is a blocking lifecycle helper in PTB v20
                        self.app.run_polling()
                    except Exception as e:
                        # Log inside thread
                        try:
                            self.logger.error(f"Polling thread error: {e}")
                        except Exception:
                            pass
                self._polling_thread = threading.Thread(target=_worker, name="telegram-polling", daemon=True)
                self._polling_thread.start()
                self._polling_started = True
                self.logger.info("Started polling for trade responses (background thread)")
        except Exception as e:
            self.logger.error(f"Error starting polling: {e}")
    
    async def _stop_polling(self):
        """Stop polling for updates and join the background thread."""
        try:
            if self.app and self._polling_started:
                try:
                    # Schedule stop inside Application's loop
                    self.app.create_task(self.app.stop())
                except Exception:
                    pass
                # Join thread briefly
                if self._polling_thread and self._polling_thread.is_alive():
                    self._polling_thread.join(timeout=5)
                self._polling_started = False
                self._polling_thread = None
                self.logger.info("Stopped polling (no active trade notifications)")
        except Exception as e:
            self.logger.error(f"Error stopping polling: {e}")
    
    async def stop(self):
        """Stop the callback handler."""
        try:
            if self.app:
                if getattr(self, '_polling_started', False):
                    await self._stop_polling()
                self.logger.info("Callback handler stopped")
        except Exception as e:
            self.logger.error(f"Error stopping callback handler: {e}")

    async def _setup_webhook(self):
        """Setup Telegram webhook if configured, otherwise start polling."""
        try:
            # If webhook URL is provided, try to set it, else fallback to polling
            webhook_url = getattr(self.config, 'telegram_webhook_url', None)
            if self.app and webhook_url:
                try:
                    await self.app.bot.set_webhook(url=webhook_url)
                    self.logger.info("Telegram webhook set successfully")
                    return
                except Exception as e:
                    self.logger.warning(f"Failed to set webhook, falling back to polling: {e}")
            # Fallback to polling
            await self._start_polling()
        except Exception as e:
            self.logger.error(f"Error setting up webhook/polling: {e}")
            # Ensure we attempt polling as a last resort
            try:
                await self._start_polling()
            except Exception:
                pass
    
    def register_notification(self, notification: NotificationMessage):
        """Register a notification for response handling."""
        self.active_notifications[notification.trade_decision.recommendation.id] = notification
        self.logger.info(f"Registered notification for trade {notification.trade_decision.recommendation.id}")
        
        # Start polling when we have active notifications
        if not hasattr(self, '_polling_started') or not self._polling_started:
            asyncio.create_task(self._start_polling())
    
    def unregister_notification(self, trade_id: str):
        """Unregister a notification after response."""
        if trade_id in self.active_notifications:
            del self.active_notifications[trade_id]
            self.logger.info(f"Unregistered notification for trade {trade_id}")
            
            # Stop polling if no more active notifications
            if len(self.active_notifications) == 0:
                asyncio.create_task(self._stop_polling())
    
    async def _handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button callbacks."""
        try:
            query = update.callback_query
            await query.answer()
            
            # Parse callback data
            data = query.data
            user_id = str(query.from_user.id)
            
            self.logger.info(f"Received callback: {data} from user {user_id}")
            
            # Process the callback
            await self._process_user_response(data, user_id, query.message.chat_id)
            
        except Exception as e:
            self.logger.error(f"Error handling callback query: {e}")
            if update.callback_query:
                await update.callback_query.answer("Error processing response")
    
    async def _handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text message responses."""
        try:
            message = update.message.text
            user_id = str(update.message.from_user.id)
            chat_id = update.message.chat_id
            
            self.logger.info(f"Received text message: {message} from user {user_id}")
            
            # Process text response
            await self._process_text_response(message, user_id, chat_id)
            
        except Exception as e:
            self.logger.error(f"Error handling text message: {e}")
    
    async def _process_user_response(self, data: str, user_id: str, chat_id: int):
        """Process user response from callback or text."""
        try:
            # Parse action and trade ID
            if data.startswith(('accept_', 'edit_', 'deny_')):
                action, trade_id = data.split('_', 1)
            else:
                # Handle text format: "accept abc123" or "edit abc123 1.08100 1.08900"
                parts = data.split()
                if len(parts) < 2:
                    await self._send_error_message(chat_id, "Invalid response format. Use: accept/edit/deny [trade_id]")
                    return
                
                action = parts[0].lower()
                trade_id = parts[1]
            
            # Validate action
            if action not in ['accept', 'edit', 'deny']:
                await self._send_error_message(chat_id, "Invalid action. Use: accept, edit, or deny")
                return
            
            # Get notification
            if trade_id not in self.active_notifications:
                await self._send_error_message(chat_id, f"Trade {trade_id} not found or expired")
                return
            
            notification = self.active_notifications[trade_id]
            
            # Create user response
            from datetime import datetime, timezone
            user_response = UserResponse(
                notification_id=notification.id,
                action=action,
                user_id=user_id,
                timestamp=datetime.now(timezone.utc)
            )
            
            # Handle edit action
            if action == 'edit' and len(data.split()) > 2:
                parts = data.split()
                if len(parts) >= 5:  # edit trade_id stop_loss take_profit position_size
                    try:
                        user_response.modified_params = {
                            'stop_loss': Decimal(parts[2]),
                            'take_profit': Decimal(parts[3]),
                            'position_size': Decimal(parts[4])
                        }
                    except (ValueError, IndexError):
                        await self._send_error_message(chat_id, "Invalid edit format. Use: edit [trade_id] [stop_loss] [take_profit] [position_size]")
                        return
            
            # Process the response
            await self._execute_user_response(user_response, notification, chat_id)
            
        except Exception as e:
            self.logger.error(f"Error processing user response: {e}")
            await self._send_error_message(chat_id, "Error processing response")
    
    async def _process_text_response(self, message: str, user_id: str, chat_id: int):
        """Process text message response."""
        try:
            # Check if this is a response to a trade notification
            parts = message.split()
            if len(parts) >= 2:
                action = parts[0].lower()
                if action in ['accept', 'edit', 'deny']:
                    await self._process_user_response(message, user_id, chat_id)
                else:
                    # Not a trade response, ignore
                    pass
        except Exception as e:
            self.logger.error(f"Error processing text response: {e}")
    
    async def _execute_user_response(self, user_response: UserResponse, notification: NotificationMessage, chat_id: int):
        """Execute the user's response to a trade notification."""
        try:
            trade_decision = notification.trade_decision
            trade_id = trade_decision.recommendation.id
            
            if user_response.action == 'accept':
                # Accept the trade
                await self._accept_trade(user_response, notification, chat_id)
                
            elif user_response.action == 'edit':
                # Edit the trade parameters
                await self._edit_trade(user_response, notification, chat_id)
                
            elif user_response.action == 'deny':
                # Deny the trade
                await self._deny_trade(user_response, notification, chat_id)
            
            # Unregister the notification
            self.unregister_notification(trade_id)
            
        except Exception as e:
            self.logger.error(f"Error executing user response: {e}")
            await self._send_error_message(chat_id, "Error executing trade action")
    
    async def _accept_trade(self, user_response: UserResponse, notification: NotificationMessage, chat_id: int):
        """Accept and execute the trade."""
        try:
            trade_decision = notification.trade_decision
            
            # Execute trade through notification layer's executor if available
            trade_id = None
            if hasattr(self.notification_layer, 'execute_approved_trade'):
                trade_id = await self.notification_layer.execute_approved_trade(trade_decision)
            
            from datetime import datetime, timezone
            message = f"""
✅ Trade Accepted!

📊 Pair: {trade_decision.recommendation.pair}
💰 Entry Price: {trade_decision.recommendation.entry_price:.5f}
🛑 Stop Loss: {trade_decision.recommendation.stop_loss:.5f}
🎯 Take Profit: {trade_decision.recommendation.take_profit:.5f}
📈 Position Size: {trade_decision.position_size}

⏰ Executed: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

Trade {'executed' if trade_id else 'execution requested'}...
"""
            
            await self._send_message(chat_id, message)
            self.logger.info(f"Trade {trade_decision.recommendation.id} accepted by user {user_response.user_id}")
            
        except Exception as e:
            self.logger.error(f"Error accepting trade: {e}")
            raise
    
    async def _edit_trade(self, user_response: UserResponse, notification: NotificationMessage, chat_id: int):
        """Edit trade parameters and execute."""
        try:
            trade_decision = notification.trade_decision
            original_rec = trade_decision.recommendation
            
            # Apply modifications
            if user_response.modified_params:
                if 'stop_loss' in user_response.modified_params:
                    original_rec.stop_loss = user_response.modified_params['stop_loss']
                if 'take_profit' in user_response.modified_params:
                    original_rec.take_profit = user_response.modified_params['take_profit']
                if 'position_size' in user_response.modified_params:
                    trade_decision.position_size = user_response.modified_params['position_size']
            
            from datetime import datetime, timezone
            message = f"""
✏️ Trade Modified and Accepted!

📊 Pair: {original_rec.pair}
💰 Entry Price: {original_rec.entry_price:.5f}
🛑 Stop Loss: {original_rec.stop_loss:.5f}
🎯 Take Profit: {original_rec.take_profit:.5f}
📈 Position Size: {trade_decision.position_size}

⏰ Executed: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

Modified trade is being executed...
"""
            
            await self._send_message(chat_id, message)
            self.logger.info(f"Trade {original_rec.id} modified and accepted by user {user_response.user_id}")
            
        except Exception as e:
            self.logger.error(f"Error editing trade: {e}")
            raise
    
    async def _deny_trade(self, user_response: UserResponse, notification: NotificationMessage, chat_id: int):
        """Deny the trade."""
        try:
            trade_decision = notification.trade_decision
            
            from datetime import datetime, timezone
            message = f"""
❌ Trade Denied

📊 Pair: {trade_decision.recommendation.pair}
⏰ Denied: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

Trade has been cancelled.
"""
            
            await self._send_message(chat_id, message)
            self.logger.info(f"Trade {trade_decision.recommendation.id} denied by user {user_response.user_id}")
            
        except Exception as e:
            self.logger.error(f"Error denying trade: {e}")
            raise
    
    async def _send_message(self, chat_id: int, message: str):
        """Send a message to the user."""
        try:
            if self.app:
                await self.app.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode='Markdown'
                )
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
    
    async def _send_error_message(self, chat_id: int, error_message: str):
        """Send an error message to the user."""
        try:
            message = f"❌ Error: {error_message}"
            await self._send_message(chat_id, message)
        except Exception as e:
            self.logger.error(f"Error sending error message: {e}") 