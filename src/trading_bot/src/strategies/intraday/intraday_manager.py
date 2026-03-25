"""
Intraday Strategy Manager — Session-Based Orchestrator
========================================================
No voting. No consensus. The session clock decides which strategy runs.
Each strategy independently decides whether to signal.

Session routing:
- Asian session (00:00–07:00): mark ranges only, no trades
- London open (07:00–10:00): Asian Range Breakout → London ORB (in order)
- London midday (10:00–13:00): no trades
- NY overlap (13:00–16:00): NY Overlap Momentum
- After 16:00: close all open positions

One trade per strategy per pair per day maximum.
FTMO risk manager is a hard gate on every trade.
"""

import logging
from datetime import datetime
from typing import Optional, List

from .session_clock import SessionClock, SessionState
from .asian_range_breakout import AsianRangeBreakoutStrategy
from .london_orb import LondonORBStrategy
from .ny_overlap_momentum import NYOverlapMomentumStrategy
from .ftmo_risk_manager import FTMORiskManager

logger = logging.getLogger(__name__)


class IntradayManager:

    def __init__(self, config=None, initial_balance: float = 10000):
        self.config = config
        self.session_clock = SessionClock()
        self.risk_manager = FTMORiskManager(initial_balance, config)

        self.asian_breakout = AsianRangeBreakoutStrategy(config)
        self.london_orb = LondonORBStrategy(config)
        self.ny_momentum = NYOverlapMomentumStrategy(config)

        # Track whether Asian breakout fired today (per pair) — prevents London ORB doubling up
        self._asian_breakout_fired = {}  # pair -> bool

    async def on_candle(
        self,
        pair: str,
        m5_candles: list,
        m15_candles: list,
        current_time: datetime,
    ) -> Optional[dict]:
        """
        Called on every M5 candle close.
        Routes to the correct strategy based on session clock.
        Returns a signal dict or None.
        """
        # Daily reset
        self.risk_manager.on_new_day(current_time)

        # Weekend / Friday close — no trading
        if self.session_clock.is_weekend(current_time):
            return None
        if self.session_clock.is_friday_close(current_time):
            return None

        # Hard risk gate
        can_trade, reason = self.risk_manager.can_open_trade()
        if not can_trade:
            logger.debug(f"{pair}: Trade blocked — {reason}")
            return None

        session = self.session_clock.get_session(current_time)

        # ── ASIAN SESSION: accumulate ranges, do not trade ──────────────────
        if session == SessionState.ASIAN_ACCUMULATION:
            self.asian_breakout.mark_asian_range(pair, m5_candles, current_time)
            return None

        # ── LONDON OPEN: breakout strategies ────────────────────────────────
        if session == SessionState.LONDON_OPEN:
            # Mark ORB range during the 07:00–07:30 window
            if current_time.hour == 7 and current_time.minute <= 30:
                self.london_orb.mark_opening_range(pair, m5_candles, current_time)
                self.ny_momentum.mark_london_open(pair, m5_candles, current_time)

            # 1. Try Asian Range Breakout first (primary)
            signal = await self.asian_breakout.generate_signal(
                pair=pair,
                m15_candles=m15_candles,
                current_time=current_time,
            )
            if signal:
                self._asian_breakout_fired[pair] = True
                logger.info(
                    f"{pair}: Asian Range Breakout → {signal['direction']} "
                    f"entry={signal['entry_price']:.5f} "
                    f"SL={signal['stop_loss']:.5f} TP={signal['take_profit']:.5f}"
                )
                self.risk_manager.on_trade_opened()
                return signal

            # 2. Try London ORB (secondary — skips if Asian Breakout fired)
            asian_fired = self._asian_breakout_fired.get(pair, False)
            signal = await self.london_orb.generate_signal(
                pair=pair,
                m5_candles=m5_candles,
                current_time=current_time,
                asian_breakout_triggered=asian_fired,
            )
            if signal:
                logger.info(
                    f"{pair}: London ORB → {signal['direction']} "
                    f"entry={signal['entry_price']:.5f} "
                    f"SL={signal['stop_loss']:.5f} TP={signal['take_profit']:.5f}"
                )
                self.risk_manager.on_trade_opened()
                return signal

            return None

        # ── LONDON MIDDAY: no trading ────────────────────────────────────────
        if session == SessionState.LONDON_MIDDAY:
            return None

        # ── NY OVERLAP: momentum continuation ───────────────────────────────
        if session == SessionState.NY_OVERLAP:
            signal = await self.ny_momentum.generate_signal(
                pair=pair,
                m15_candles=m15_candles,
                current_time=current_time,
                trades_today=self.risk_manager.trades_today,
            )
            if signal:
                logger.info(
                    f"{pair}: NY Overlap Momentum → {signal['direction']} "
                    f"entry={signal['entry_price']:.5f} "
                    f"SL={signal['stop_loss']:.5f} TP={signal['take_profit']:.5f}"
                )
                self.risk_manager.on_trade_opened()
                return signal

            return None

        return None

    def on_trade_closed(self, pnl: float):
        """Notify risk manager when a trade closes. Pass P&L in account currency."""
        self.risk_manager.on_trade_closed(pnl)

    def should_close_all(self, current_time: datetime) -> bool:
        """True at 16:00 GMT and on weekends — all positions must close."""
        return self.session_clock.should_close_all(current_time)

    def get_position_size(self, entry: float, stop_loss: float, pair: str) -> int:
        """Get position size in units from risk manager."""
        return self.risk_manager.get_position_size(entry, stop_loss, pair)

    def get_risk_stats(self) -> dict:
        """Current FTMO risk status."""
        return self.risk_manager.get_stats()

    def reset_daily(self):
        """End-of-day cleanup — call after 16:00 GMT."""
        self.asian_breakout.reset_daily()
        self.london_orb.reset_daily()
        self.ny_momentum.reset_daily()
        self._asian_breakout_fired = {}
