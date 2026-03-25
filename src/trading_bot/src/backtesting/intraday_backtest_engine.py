"""
Intraday Backtest Engine — M5 loop, session-based strategies.

Separate from the swing backtest engine. Simulates the three session strategies
(Asian Range Breakout, London ORB, NY Overlap Momentum) using M5 and M15
historical candles from OANDA.

Key design decisions:
- M5 loop but skips overnight (16:00–00:00 GMT) and weekends to cut runtime
- Candle windows: last 500 M5 + last 200 M15 passed to strategies
- Position management: TP/SL checked on each candle's high/low, close forced at 16:00
- Spread applied at open (added to buy entry, subtracted from sell entry)
- Per-strategy trade log for breakdown analysis
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ── Data structures ──────────────────────────────────────────────────────────

@dataclass
class IntradayTrade:
    pair: str
    strategy: str
    session: str
    direction: str          # 'buy' | 'sell'
    entry_time: datetime
    entry_price: float
    stop_loss: float
    take_profit: float
    size: int               # units
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: str = ""   # 'tp' | 'sl' | 'eod' (end-of-day close)
    pnl: float = 0.0
    pnl_pips: float = 0.0


@dataclass
class IntradayBacktestResult:
    initial_balance: float = 10000.0
    final_balance: float = 0.0
    total_return_pct: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    eod_closes: int = 0     # trades closed at 16:00 (not TP or SL)
    win_rate: float = 0.0
    profit_factor: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    avg_rr_achieved: float = 0.0
    trades: List[IntradayTrade] = field(default_factory=list)
    equity_curve: List[Tuple[datetime, float]] = field(default_factory=list)
    per_strategy: Dict[str, dict] = field(default_factory=dict)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


# ── Engine ───────────────────────────────────────────────────────────────────

class IntradayBacktestEngine:
    """
    Runs the three intraday strategies against M5/M15 historical data.

    Usage:
        engine = IntradayBacktestEngine(pairs=['EUR_USD', 'GBP_USD'],
                                         initial_balance=10000,
                                         spread_pips=0.7)
        result = asyncio.run(engine.run(start_date, end_date))
    """

    # Candle windows passed to strategies
    M5_WINDOW = 500    # ~40 hours of M5 data
    M15_WINDOW = 200   # ~50 hours of M15 data

    # Pip sizes
    PIP = {'JPY': 0.01}
    PIP_DEFAULT = 0.0001

    def __init__(
        self,
        pairs: List[str] = None,
        initial_balance: float = 10000.0,
        spread_pips: float = 0.7,
        risk_pct: float = 0.75,
    ):
        self.pairs = pairs or ['EUR_USD', 'GBP_USD']
        self.initial_balance = initial_balance
        self.spread_pips = spread_pips
        self.risk_pct = risk_pct

    def _pip_size(self, pair: str) -> float:
        return 0.01 if 'JPY' in pair else 0.0001

    def _spread(self, pair: str) -> float:
        return self.spread_pips * self._pip_size(pair)

    async def run(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> IntradayBacktestResult:
        """Run the full intraday backtest over the date range."""
        import logging
        logging.getLogger("debug_tracker").setLevel(logging.WARNING)

        result = IntradayBacktestResult(
            initial_balance=self.initial_balance,
            final_balance=self.initial_balance,
            start_date=start_date,
            end_date=end_date,
        )

        # Load data
        try:
            from .feeds_oanda import OandaHistoricalFeed
            from ..core.models import TimeFrame
        except ImportError:
            from feeds_oanda import OandaHistoricalFeed
            from core.models import TimeFrame

        logger.info(f"📡 Loading M5 and M15 data for {self.pairs}...")
        feed = OandaHistoricalFeed(use_cache=True)
        feed.load_pair_date_range(
            pairs=self.pairs,
            timeframes=[TimeFrame.M5, TimeFrame.M15],
            start=start_date,
            end=end_date,
        )

        # Run per-pair simulations (independent)
        balance = self.initial_balance
        all_trades: List[IntradayTrade] = []
        equity_curve: List[Tuple[datetime, float]] = [(start_date, balance)]

        for pair in self.pairs:
            pair_trades, pair_equity = await self._run_pair(
                pair=pair,
                feed=feed,
                start_date=start_date,
                end_date=end_date,
                starting_balance=balance,
            )
            all_trades.extend(pair_trades)

        # Compute metrics
        self._compute_metrics(result, all_trades, equity_curve)
        return result

    async def _run_pair(
        self,
        pair: str,
        feed,
        start_date: datetime,
        end_date: datetime,
        starting_balance: float,
    ) -> Tuple[List[IntradayTrade], List[Tuple[datetime, float]]]:
        """Simulate one pair over the date range. Returns (trades, equity_curve)."""
        try:
            from ..core.models import TimeFrame
            from ..strategies.intraday.intraday_manager import IntradayManager
        except ImportError:
            from core.models import TimeFrame
            from strategies.intraday.intraday_manager import IntradayManager

        manager = IntradayManager(config=None, initial_balance=starting_balance)

        # Get sorted candle lists
        m5_all: list = feed.data.get(pair, {}).get(TimeFrame.M5, [])
        m15_all: list = feed.data.get(pair, {}).get(TimeFrame.M15, [])

        if not m5_all:
            logger.warning(f"No M5 data for {pair}")
            return [], []

        # Filter to date range
        m5_all = [c for c in m5_all if start_date <= c.timestamp <= end_date]
        m15_all = [c for c in m15_all if start_date <= c.timestamp <= end_date]

        if not m5_all:
            logger.warning(f"No M5 data for {pair} in date range")
            return [], []

        logger.info(f"📊 {pair}: {len(m5_all)} M5 candles, {len(m15_all)} M15 candles")

        trades: List[IntradayTrade] = []
        equity: List[Tuple[datetime, float]] = []
        balance = starting_balance
        open_trade: Optional[IntradayTrade] = None
        m15_idx = 0  # pointer into m15_all

        pip_size = self._pip_size(pair)
        spread = self._spread(pair)

        for i, candle in enumerate(m5_all):
            ct = candle.timestamp

            # Skip weekends
            if ct.weekday() in (5, 6):
                continue

            current_high = float(candle.high)
            current_low = float(candle.low)
            current_close = float(candle.close)

            # ── Advance M15 pointer ──────────────────────────────────────────
            while m15_idx < len(m15_all) - 1 and m15_all[m15_idx + 1].timestamp <= ct:
                m15_idx += 1

            # ── Manage open position ─────────────────────────────────────────
            if open_trade is not None:
                # End-of-day close at 16:00 GMT
                if ct.hour >= 16 and open_trade.exit_time is None:
                    exit_price = current_close
                    pnl = self._calc_pnl(open_trade, exit_price, pair)
                    open_trade.exit_time = ct
                    open_trade.exit_price = exit_price
                    open_trade.exit_reason = 'eod'
                    open_trade.pnl = pnl
                    open_trade.pnl_pips = pnl / (open_trade.size * pip_size) if open_trade.size else 0
                    balance += pnl
                    manager.on_trade_closed(pnl)
                    trades.append(open_trade)
                    equity.append((ct, balance))
                    open_trade = None
                    manager.reset_daily()
                    continue

                # TP check first (same candle both possible — TP wins)
                tp_hit = (
                    (open_trade.direction == 'buy' and current_high >= open_trade.take_profit) or
                    (open_trade.direction == 'sell' and current_low <= open_trade.take_profit)
                )
                sl_hit = (
                    (open_trade.direction == 'buy' and current_low <= open_trade.stop_loss) or
                    (open_trade.direction == 'sell' and current_high >= open_trade.stop_loss)
                )

                if tp_hit:
                    exit_price = open_trade.take_profit
                    pnl = self._calc_pnl(open_trade, exit_price, pair)
                    open_trade.exit_time = ct
                    open_trade.exit_price = exit_price
                    open_trade.exit_reason = 'tp'
                    open_trade.pnl = pnl
                    open_trade.pnl_pips = (exit_price - open_trade.entry_price) / pip_size * (1 if open_trade.direction == 'buy' else -1)
                    balance += pnl
                    manager.on_trade_closed(pnl)
                    trades.append(open_trade)
                    equity.append((ct, balance))
                    open_trade = None
                    continue

                if sl_hit:
                    exit_price = open_trade.stop_loss
                    pnl = self._calc_pnl(open_trade, exit_price, pair)
                    open_trade.exit_time = ct
                    open_trade.exit_price = exit_price
                    open_trade.exit_reason = 'sl'
                    open_trade.pnl = pnl
                    open_trade.pnl_pips = (exit_price - open_trade.entry_price) / pip_size * (1 if open_trade.direction == 'buy' else -1)
                    balance += pnl
                    manager.on_trade_closed(pnl)
                    trades.append(open_trade)
                    equity.append((ct, balance))
                    open_trade = None
                    continue

            # ── New day reset for Asian range marking ────────────────────────
            if ct.hour == 0 and ct.minute < 5:
                manager.reset_daily()

            # ── Skip if position already open (max 1 per pair at a time) ────
            if open_trade is not None:
                continue

            # ── Skip non-trading hours (16:00–00:00 GMT) — speeds up loop ──
            if ct.hour >= 16:
                continue

            # ── Build candle windows ─────────────────────────────────────────
            m5_window = m5_all[max(0, i - self.M5_WINDOW + 1): i + 1]
            m15_window = m15_all[max(0, m15_idx - self.M15_WINDOW + 1): m15_idx + 1]

            # ── Feed to strategy manager ─────────────────────────────────────
            # Asian range marking happens inside manager.on_candle during 00:00–07:00
            signal = await manager.on_candle(
                pair=pair,
                m5_candles=m5_window,
                m15_candles=m15_window,
                current_time=ct,
            )

            if signal is None:
                continue

            # ── Open position from signal ────────────────────────────────────
            direction = signal['direction']
            entry = signal['entry_price']

            # Apply spread at entry
            if direction == 'buy':
                entry += spread  # buy at ask
            else:
                entry -= spread  # sell at bid

            sl = signal['stop_loss']
            tp = signal['take_profit']

            # Position size from risk manager
            size = manager.get_position_size(entry, sl, pair)
            if size <= 0:
                continue

            open_trade = IntradayTrade(
                pair=pair,
                strategy=signal.get('strategy', 'unknown'),
                session=signal.get('session', 'unknown'),
                direction=direction,
                entry_time=ct,
                entry_price=entry,
                stop_loss=sl,
                take_profit=tp,
                size=size,
            )

            logger.debug(
                f"{pair} OPEN {direction.upper()} | entry={entry:.5f} "
                f"SL={sl:.5f} TP={tp:.5f} | {signal.get('strategy')}"
            )

        # Close any still-open position at end of data
        if open_trade is not None:
            last_candle = m5_all[-1]
            exit_price = float(last_candle.close)
            pnl = self._calc_pnl(open_trade, exit_price, pair)
            open_trade.exit_time = last_candle.timestamp
            open_trade.exit_price = exit_price
            open_trade.exit_reason = 'eod'
            open_trade.pnl = pnl
            balance += pnl
            trades.append(open_trade)

        return trades, equity

    def _calc_pnl(self, trade: IntradayTrade, exit_price: float, pair: str) -> float:
        """Calculate P&L in account currency (assumes USD account, USD-quoted pairs)."""
        pip_size = self._pip_size(pair)
        if trade.direction == 'buy':
            price_diff = exit_price - trade.entry_price
        else:
            price_diff = trade.entry_price - exit_price
        # For USD-quoted pairs (EUR_USD, GBP_USD): P&L = price_diff * size
        return price_diff * trade.size

    def _compute_metrics(
        self,
        result: IntradayBacktestResult,
        trades: List[IntradayTrade],
        equity_curve: List[Tuple[datetime, float]],
    ):
        result.trades = trades
        result.total_trades = len(trades)

        if not trades:
            result.final_balance = self.initial_balance
            return

        wins = [t for t in trades if t.pnl > 0]
        losses = [t for t in trades if t.pnl <= 0]
        eod_closes = [t for t in trades if t.exit_reason == 'eod']

        result.winning_trades = len(wins)
        result.losing_trades = len(losses)
        result.eod_closes = len(eod_closes)
        result.win_rate = (len(wins) / len(trades) * 100) if trades else 0

        gross_profit = sum(t.pnl for t in wins)
        gross_loss = abs(sum(t.pnl for t in losses))
        result.profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')

        total_pnl = sum(t.pnl for t in trades)
        result.final_balance = self.initial_balance + total_pnl
        result.total_return_pct = (total_pnl / self.initial_balance) * 100

        # Max drawdown from running equity
        balance = self.initial_balance
        peak = balance
        max_dd = 0.0
        for t in sorted(trades, key=lambda x: x.exit_time or x.entry_time):
            balance += t.pnl
            if balance > peak:
                peak = balance
            dd = (peak - balance) / peak * 100
            if dd > max_dd:
                max_dd = dd
        result.max_drawdown_pct = max_dd

        # Per-strategy breakdown
        strategies = set(t.strategy for t in trades)
        for s in strategies:
            s_trades = [t for t in trades if t.strategy == s]
            s_wins = [t for t in s_trades if t.pnl > 0]
            s_gp = sum(t.pnl for t in s_wins)
            s_gl = abs(sum(t.pnl for t in s_trades if t.pnl <= 0))
            result.per_strategy[s] = {
                'trades': len(s_trades),
                'wins': len(s_wins),
                'win_rate': len(s_wins) / len(s_trades) * 100 if s_trades else 0,
                'profit_factor': s_gp / s_gl if s_gl > 0 else float('inf'),
                'total_pnl': sum(t.pnl for t in s_trades),
            }

        # Sharpe (daily returns approximation)
        if len(trades) > 1:
            import statistics
            pnls = [t.pnl / self.initial_balance * 100 for t in trades]
            avg = statistics.mean(pnls)
            std = statistics.stdev(pnls) if len(pnls) > 1 else 1
            result.sharpe_ratio = (avg / std * (252 ** 0.5)) if std > 0 else 0

        result.equity_curve = equity_curve

    def print_results(self, result: IntradayBacktestResult):
        """Print formatted backtest results to stdout."""
        print("\n" + "=" * 80)
        print("📊 INTRADAY BACKTEST RESULTS")
        print("=" * 80)
        print(f"Period:           {result.start_date.date()} to {result.end_date.date()}")
        print(f"Initial Balance:  ${result.initial_balance:,.2f}")
        print(f"Final Balance:    ${result.final_balance:,.2f}")
        print(f"Total Return:     {result.total_return_pct:.2f}%")
        print(f"Max Drawdown:     {result.max_drawdown_pct:.2f}%")
        print(f"Sharpe Ratio:     {result.sharpe_ratio:.2f}")
        print()
        print(f"Total Trades:     {result.total_trades}")
        print(f"  Wins:           {result.winning_trades}")
        print(f"  Losses:         {result.losing_trades}")
        print(f"  EoD Closes:     {result.eod_closes}")
        print(f"Win Rate:         {result.win_rate:.1f}%")
        print(f"Profit Factor:    {result.profit_factor:.2f}")
        print()

        if result.per_strategy:
            print("Per-Strategy Breakdown:")
            print(f"  {'Strategy':<30} {'Trades':>6} {'WR':>6} {'PF':>6} {'P&L':>10}")
            print(f"  {'-'*30} {'------':>6} {'------':>6} {'------':>6} {'----------':>10}")
            for name, s in result.per_strategy.items():
                pf = f"{s['profit_factor']:.2f}" if s['profit_factor'] != float('inf') else "∞"
                print(
                    f"  {name:<30} {s['trades']:>6} {s['win_rate']:>5.1f}% {pf:>6} "
                    f"${s['total_pnl']:>9.2f}"
                )
        print("=" * 80)
