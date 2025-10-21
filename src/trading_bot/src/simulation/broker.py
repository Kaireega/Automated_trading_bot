"""
Simple broker simulator with spread and slippage.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime, timezone


@dataclass
class SimOrder:
    oid: str
    pair: str
    direction: int  # 1 buy, -1 sell
    size: Decimal
    entry: Decimal
    stop: Optional[Decimal]
    take: Optional[Decimal]
    time: datetime


class BrokerSim:
    def __init__(self, spread_pips: float = 0.1, slippage_pips: float = 0.1, pip_location: float = 0.0001):
        self.spread_pips = Decimal(str(spread_pips))
        self.slippage_pips = Decimal(str(slippage_pips))
        self.pip_location = Decimal(str(pip_location))
        self.positions: List[SimOrder] = []

    def _pip_value(self) -> Decimal:
        return self.pip_location

    def open_market(self, pair: str, direction: int, size: Decimal, price: Decimal,
                    stop: Optional[Decimal], take: Optional[Decimal]) -> str:
        slip = self.slippage_pips * self._pip_value()
        spread = self.spread_pips * self._pip_value()
        if direction > 0:
            fill = price + slip + spread
        else:
            fill = price - slip - spread
        oid = f"SIM-{len(self.positions)+1}"
        self.positions.append(SimOrder(oid, pair, direction, size, fill, stop, take, datetime.now(timezone.utc)))
        return oid

    def step(self, pair: str, candle_open: Decimal, candle_high: Decimal, candle_low: Decimal, candle_close: Decimal) -> List[Dict[str, Any]]:
        """Advance simulation by one candle; close positions if SL/TP hit.
        Returns list of closed trade dicts with pnl information.
        """
        closed: List[Dict[str, Any]] = []
        remaining: List[SimOrder] = []
        for pos in self.positions:
            if pos.pair != pair:
                remaining.append(pos)
                continue
            exit_price = None
            reason = None
            # Check SL/TP hit within candle range (assumes worst-case fill)
            if pos.direction > 0:
                # Long: SL if low <= stop, TP if high >= take
                if pos.stop and candle_low <= pos.stop:
                    exit_price = Decimal(str(pos.stop))
                    reason = 'stop'
                elif pos.take and candle_high >= pos.take:
                    exit_price = Decimal(str(pos.take))
                    reason = 'take'
            else:
                # Short
                if pos.stop and candle_high >= pos.stop:
                    exit_price = Decimal(str(pos.stop))
                    reason = 'stop'
                elif pos.take and candle_low <= pos.take:
                    exit_price = Decimal(str(pos.take))
                    reason = 'take'
            if exit_price is None:
                remaining.append(pos)
                continue
            pnl = (exit_price - pos.entry) * (pos.size if pos.direction > 0 else -pos.size)
            closed.append({
                'id': pos.oid,
                'pair': pos.pair,
                'size': pos.size,
                'direction': pos.direction,
                'entry': pos.entry,
                'exit': exit_price,
                'pnl': pnl,
                'reason': reason,
                'opened_at': pos.time,
                'closed_at': datetime.now(timezone.utc)
            })
        self.positions = remaining
        return closed


