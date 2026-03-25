"""
Session Clock — Controls when each strategy is allowed to trade.

Trading windows (all times GMT/UTC):
- Asian accumulation: 00:00–07:00 — NO TRADING, only range marking
- London open:        07:00–10:00 — Asian Range Breakout + London ORB active
- London midday:      10:00–13:00 — NO TRADING (low volume, choppy)
- London/NY overlap:  13:00–16:00 — NY Overlap Momentum active
- After 16:00:        CLOSE ALL — no new trades, close any open positions

Why these windows:
- London open (07:00–10:00): 35% of daily FX volume. Institutional orders
  from European banks create directional moves. Breakout strategies thrive.
- London/NY overlap (13:00–16:00): Highest liquidity of the day. Two major
  centers trading simultaneously. Momentum strategies work best here.
- Asian session: Low volume, tight ranges. Perfect for marking S/R levels,
  terrible for trading. Let the range form, then trade the breakout.
- Midday London: Volume drops between sessions. Whipsaw kills strategies.
"""

from datetime import datetime, time
from enum import Enum


class SessionState(Enum):
    ASIAN_ACCUMULATION = "asian_accumulation"    # 00:00–07:00 — mark ranges
    LONDON_OPEN = "london_open"                  # 07:00–10:00 — breakout window
    LONDON_MIDDAY = "london_midday"              # 10:00–13:00 — no trading
    NY_OVERLAP = "ny_overlap"                    # 13:00–16:00 — momentum window
    CLOSED = "closed"                            # 16:00–00:00 — no trading


class SessionClock:

    # Session boundaries (GMT/UTC): (start, end, state)
    SESSIONS = [
        (time(0, 0),  time(7, 0),  SessionState.ASIAN_ACCUMULATION),
        (time(7, 0),  time(10, 0), SessionState.LONDON_OPEN),
        (time(10, 0), time(13, 0), SessionState.LONDON_MIDDAY),
        (time(13, 0), time(16, 0), SessionState.NY_OVERLAP),
        (time(16, 0), time(23, 59), SessionState.CLOSED),
    ]

    # Which strategies are active in which session
    ACTIVE_STRATEGIES = {
        SessionState.ASIAN_ACCUMULATION: [],
        SessionState.LONDON_OPEN: ['asian_range_breakout', 'london_orb'],
        SessionState.LONDON_MIDDAY: [],
        SessionState.NY_OVERLAP: ['ny_overlap_momentum'],
        SessionState.CLOSED: [],
    }

    def get_session(self, current_time: datetime) -> SessionState:
        """Get the current session state."""
        t = current_time.time()
        for start, end, session in self.SESSIONS:
            if start <= t < end:
                return session
        return SessionState.CLOSED

    def is_trading_allowed(self, current_time: datetime) -> bool:
        """Check if any trading is allowed right now."""
        session = self.get_session(current_time)
        return len(self.ACTIVE_STRATEGIES.get(session, [])) > 0

    def get_active_strategies(self, current_time: datetime) -> list:
        """Get list of strategy names active in current session."""
        session = self.get_session(current_time)
        return self.ACTIVE_STRATEGIES.get(session, [])

    def should_close_all(self, current_time: datetime) -> bool:
        """Check if we should close all open positions (16:00 GMT)."""
        return self.get_session(current_time) == SessionState.CLOSED

    def is_friday_close(self, current_time: datetime) -> bool:
        """Friday after 15:00 — close early to avoid weekend gaps."""
        return current_time.weekday() == 4 and current_time.hour >= 15

    def is_weekend(self, current_time: datetime) -> bool:
        """No trading Saturday/Sunday."""
        return current_time.weekday() in (5, 6)
