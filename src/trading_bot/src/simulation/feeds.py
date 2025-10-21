"""
Historical data feed for simulation.
Loads pickled pandas DataFrames from a directory.
Expected columns: time, mid_o, mid_h, mid_l, mid_c, volume (optional)
File naming: {PAIR}_{TF}.pkl e.g., EUR_USD_M5.pkl
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List
from decimal import Decimal

import pandas as pd

from ..core.models import CandleData, TimeFrame


class HistoricalDataFeed:
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.data: Dict[str, Dict[TimeFrame, List[CandleData]]] = {}

    def _load_pair_tf(self, pair: str, tf: TimeFrame) -> List[CandleData]:
        file_path = self.data_dir / f"{pair}_{tf.value}.pkl"
        if not file_path.exists():
            return []
        df: pd.DataFrame = pd.read_pickle(file_path)
        # Normalize expected columns
        col_map = {
            'open': 'mid_o', 'high': 'mid_h', 'low': 'mid_l', 'close': 'mid_c',
            'o': 'mid_o', 'h': 'mid_h', 'l': 'mid_l', 'c': 'mid_c'
        }
        for old, new in col_map.items():
            if old in df.columns and new not in df.columns:
                df[new] = df[old]
        candles: List[CandleData] = []
        for _, row in df.iterrows():
            ts = pd.to_datetime(row.get('time'), utc=True)
            candles.append(
                CandleData(
                    timestamp=ts.to_pydatetime(),
                    open=Decimal(str(row.get('mid_o'))),
                    high=Decimal(str(row.get('mid_h'))),
                    low=Decimal(str(row.get('mid_l'))),
                    close=Decimal(str(row.get('mid_c'))),
                    volume=Decimal(str(row.get('volume'))) if 'volume' in df.columns else None,
                    pair=pair,
                    timeframe=tf,
                )
            )
        return candles

    def load(self, pairs: List[str], timeframes: List[TimeFrame]) -> None:
        for pair in pairs:
            self.data.setdefault(pair, {})
            for tf in timeframes:
                self.data[pair][tf] = self._load_pair_tf(pair, tf)

    def get_pair_timeframes(self, pair: str) -> Dict[TimeFrame, List[CandleData]]:
        return self.data.get(pair, {})

    def min_length_across_timeframes(self, pair: str) -> int:
        tfs = self.get_pair_timeframes(pair)
        if not tfs:
            return 0
        lengths = [len(lst) for lst in tfs.values() if lst]
        return min(lengths) if lengths else 0

    def step_candles(self, pair: str, step: int) -> Dict[TimeFrame, List[CandleData]]:
        tfs = self.get_pair_timeframes(pair)
        return {tf: candles[: step + 1] for tf, candles in tfs.items() if len(candles) > step}


