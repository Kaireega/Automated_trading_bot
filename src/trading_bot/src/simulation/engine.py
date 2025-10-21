"""
Simulation engine that reuses AIAnalysisLayer -> DecisionLayer -> RiskManager.
Consumes HistoricalDataFeed and steps through candles synchronously.
"""
from __future__ import annotations

from typing import Dict, List
from datetime import datetime, timezone
from decimal import Decimal

from ..core.models import TimeFrame, CandleData, TradeExecution
from ..utils.config import Config
from ..ai.technical_analysis_layer import TechnicalAnalysisLayer
from ..decision.technical_decision_layer import TechnicalDecisionLayer
from ..core.market_regime_detector import MarketRegimeDetector
from ..core.advanced_risk_manager import AdvancedRiskManager
from ..core.fundamental_analyzer import FundamentalAnalyzer
from ..core.position_manager import PositionManager
from ..decision.performance_tracker import PerformanceTracker
from .broker import BrokerSim
from ..notifications.notification_layer import NotificationLayer
from ..data.data_layer import DataLayer
from ..core.models import TradeDecision
from ..core.position_manager import OandaApi  # type: ignore


class SimulationEngine:
    def __init__(self, config: Config, feed):
        self.config = config
        self.feed = feed
        self.technical_analysis = TechnicalAnalysisLayer(config)
        self.decision = TechnicalDecisionLayer(config)
        self.risk_adv = AdvancedRiskManager(config)
        self.regime = MarketRegimeDetector(config)
        self.fundamentals = FundamentalAnalyzer(config)
        self.notifs = NotificationLayer(config)
        # Position manager for dry-run path
        self.pm = PositionManager(config, OandaApi())
        self.broker = BrokerSim(spread_pips=config.simulation.spread_pips,
                                slippage_pips=config.simulation.slippage_pips)
        self.perf = PerformanceTracker()
        # Map simulated order ids to decisions for PnL attribution
        self._order_to_decision: Dict[str, TradeDecision] = {}

    async def start(self):
        await self.technical_analysis.start()
        await self.decision.start()
        await self.risk_adv.start()
        await self.regime.start()
        await self.fundamentals.start()
        await self.notifs.start()
        await self.pm.start()
        await self.perf.start()

    async def stop(self):
        await self.decision.close()
        await self.notifs.close()
        await self.pm.stop()

    async def run(self, pairs: List[str], timeframes: List[TimeFrame]):
        # Load data
        self.feed.load(pairs, timeframes)
        # Use min length across tfs to determine steps
        # Filter pairs that actually have data
        available = [(p, self.feed.min_length_across_timeframes(p)) for p in pairs]
        available = [(p, n) for p, n in available if n > 50]
        if not available:
            print("No sufficient historical data found for configured pairs/timeframes.")
            return
        steps = min(n for _, n in available)
        pairs = [p for p, _ in available]
        for idx in range(50, steps):  # warm-up 50 bars
            for pair in pairs:
                candles_by_tf = self.feed.step_candles(pair, idx)
                if len(candles_by_tf) < 2:
                    continue
                # Build a simple market context placeholder
                market_context = await self._mk_context(pair)
                rec, tech = await self.technical_analysis.analyze_multiple_timeframes(pair, candles_by_tf, market_context)
                if rec:
                    decision = await self.decision.make_enhanced_decision(pair, rec, tech, {}, {}, market_context)
                    if decision:
                        # Auto-detection in PositionManager handles demo vs live account
                        await self.pm.execute_trade(decision, market_context)
                        # Also simulate broker execution for PnL tracking when SL/TP hit
                        last = list(candles_by_tf.values())[0][-1]
                        # open simulated order at close for simplicity
                        oid = self.broker.open_market(
                            pair,
                            1 if rec.signal.value == 'buy' else -1,
                            decision.position_size or Decimal('0'),
                            last.close,
                            decision.modified_stop_loss,
                            decision.modified_take_profit,
                        )
                        self._order_to_decision[oid] = decision
                # step broker with this candle
                last = list(candles_by_tf.values())[0][-1]
                closed = self.broker.step(pair, last.open, last.high, last.low, last.close)
                for c in closed:
                    decision = self._order_to_decision.pop(c.get('id', ''), None)
                    if decision is None:
                        # Fallback: cannot attribute, skip
                        continue
                    trade_exec = TradeExecution(
                        trade_decision=decision,
                        execution_price=Decimal(str(c['exit'])),
                        execution_time=c['closed_at'],
                        trade_id=c.get('id'),
                        broker_response={'reason': c['reason'], 'pnl': float(c['pnl'])},
                        status='filled',
                    )
                    self.perf.add_trade(trade_exec)

        # End of simulation: print summary
        summary_all = self.perf.get_trade_summary('all')
        print("\n===== SIMULATION SUMMARY (ALL) =====")
        for k, v in summary_all.items():
            print(f"{k}: {v}")
        print("\n===== BREAKDOWN BY PAIR =====")
        for pair, stats in self.perf.get_breakdown_by_pair('all').items():
            print(f"{pair}: {stats}")

    async def _mk_context(self, pair: str):
        # For simulation, reuse DataLayer-like context from fundamentals/regime if needed
        return await self.fundamentals.get_market_session_info()  # simple stub


