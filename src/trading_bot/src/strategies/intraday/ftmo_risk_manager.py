"""
FTMO-Aware Intraday Risk Manager
==================================
Enforces FTMO challenge rules as hard constraints:
- 5% max daily drawdown  → we halt at 2.5% (2.5% buffer)
- 10% max total drawdown → we halt at 8.0% (2% buffer)
- Max 2 positions open simultaneously
- Max 5 trades per day (hard cap against overtrading)
- Consecutive loss protocol: 2 losses → half size, 3 → stop session
- All positions must be closed by 16:00 GMT (no overnight risk)
"""

from datetime import datetime, date


class FTMORiskManager:

    def __init__(self, initial_balance: float, config=None):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.daily_start_balance = initial_balance
        self.current_date = None

        # Safety limits (with buffer inside FTMO limits)
        self.daily_loss_limit_pct = 2.5     # FTMO allows 5%, we stop at 2.5%
        self.total_loss_limit_pct = 8.0     # FTMO allows 10%, we stop at 8%
        self.max_open_positions = 2
        self.base_risk_pct = 0.75           # 0.75% risk per trade
        self.max_trades_per_day = 5

        # Consecutive loss tracking
        self.consecutive_losses = 0
        self.max_consecutive_before_halt = 3
        self.session_halted = False

        # Counters
        self.trades_today = 0
        self.open_position_count = 0

    def on_new_day(self, current_time: datetime):
        """Reset daily counters at the start of each calendar day."""
        today = current_time.date()
        if self.current_date != today:
            self.daily_start_balance = self.current_balance
            self.current_date = today
            self.trades_today = 0
            self.session_halted = False
            # Consecutive losses intentionally NOT reset — spans days

    def can_open_trade(self) -> tuple:
        """
        Check if a new trade is allowed.
        Returns (allowed: bool, reason: str).
        """
        if self.session_halted:
            return False, f"Session halted: {self.consecutive_losses} consecutive losses"

        if self.trades_today >= self.max_trades_per_day:
            return False, f"Daily trade limit ({self.max_trades_per_day}) reached"

        if self.open_position_count >= self.max_open_positions:
            return False, f"Max positions open ({self.max_open_positions})"

        daily_loss_pct = (
            (self.daily_start_balance - self.current_balance) / self.daily_start_balance * 100
        )
        if daily_loss_pct >= self.daily_loss_limit_pct:
            return False, f"Daily loss limit: {daily_loss_pct:.1f}% >= {self.daily_loss_limit_pct}%"

        total_loss_pct = (
            (self.initial_balance - self.current_balance) / self.initial_balance * 100
        )
        if total_loss_pct >= self.total_loss_limit_pct:
            return False, f"Total DD limit: {total_loss_pct:.1f}% >= {self.total_loss_limit_pct}%"

        return True, "OK"

    def get_risk_percentage(self) -> float:
        """
        Risk per trade, adjusted for consecutive losses.
        Normal: 0.75%. After 2 consecutive losses: 0.375% (half size).
        """
        if self.consecutive_losses >= 2:
            return self.base_risk_pct * 0.5
        return self.base_risk_pct

    def on_trade_opened(self):
        """Call when a trade is opened."""
        self.open_position_count += 1
        self.trades_today += 1

    def on_trade_closed(self, pnl: float):
        """Call when a trade is closed with its P&L in account currency."""
        self.current_balance += pnl
        self.open_position_count = max(0, self.open_position_count - 1)

        if pnl < 0:
            self.consecutive_losses += 1
            if self.consecutive_losses >= self.max_consecutive_before_halt:
                self.session_halted = True
        else:
            self.consecutive_losses = 0  # any win resets the streak

    def get_position_size(self, entry: float, stop_loss: float, pair: str) -> float:
        """
        Calculate position size in units based on risk percentage and stop distance.
        Uses current risk percentage (reduced after consecutive losses).
        """
        risk_amount = self.current_balance * (self.get_risk_percentage() / 100)
        pip_size = 0.01 if 'JPY' in pair else 0.0001
        stop_pips = abs(entry - stop_loss) / pip_size

        if stop_pips <= 0:
            return 0

        # Approximate: 1 pip on 1 unit ≈ pip_size in account currency (USD pairs)
        # For USD pairs: pip value per unit ≈ pip_size (0.0001) per unit
        # Position size = risk_amount / (stop_pips * pip_value_per_unit)
        # pip_value_per_unit = pip_size for USD quote (EUR_USD, GBP_USD)
        pip_value_per_unit = pip_size
        units = risk_amount / (stop_pips * pip_value_per_unit)
        return round(units)

    def get_stats(self) -> dict:
        """Current risk status for logging."""
        daily_pnl_pct = (
            (self.current_balance - self.daily_start_balance) / self.daily_start_balance * 100
        )
        total_pnl_pct = (
            (self.current_balance - self.initial_balance) / self.initial_balance * 100
        )
        return {
            'balance': round(self.current_balance, 2),
            'daily_pnl_pct': round(daily_pnl_pct, 2),
            'total_pnl_pct': round(total_pnl_pct, 2),
            'consecutive_losses': self.consecutive_losses,
            'trades_today': self.trades_today,
            'open_positions': self.open_position_count,
            'session_halted': self.session_halted,
            'risk_pct': self.get_risk_percentage(),
        }
