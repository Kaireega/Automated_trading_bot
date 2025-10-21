"""
OANDA historical data feed for simulation.
Fetches candles for a dynamic date range (e.g., last 3 years up to previous week),
optionally caches to disk, and converts to CandleData by timeframe.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple
from decimal import Decimal
from datetime import datetime, timedelta, timezone

import pandas as pd

from ..core.models import CandleData, TimeFrame
from api.oanda_api import OandaApi


TF_TO_OANDA = {
    TimeFrame.M1: "M1",
    TimeFrame.M5: "M5",
    TimeFrame.M15: "M15",
    TimeFrame.M30: "M30",
    TimeFrame.H1: "H1",
    TimeFrame.H4: "H4",
    TimeFrame.D1: "D",
}


class OandaHistoricalFeed:
    def __init__(self, cache_dir: str = "data/historical_cache", use_cache: bool = True):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.use_cache = use_cache
        self.api = OandaApi()
        self.data: Dict[str, Dict[TimeFrame, List[CandleData]]] = {}

    def _cache_path(self, pair: str, tf: TimeFrame) -> Path:
        return self.cache_dir / f"{pair}_{tf.value}.pkl"

    def _window_days(self, tf: TimeFrame) -> int:
        # Conservative window sizes to avoid large responses
        if tf in (TimeFrame.M1, TimeFrame.M5):
            return 7
        if tf in (TimeFrame.M15, TimeFrame.M30):
            return 30
        if tf == TimeFrame.H1:
            return 60
        if tf == TimeFrame.H4:
            return 90
        return 180

    def _fetch_range(self, pair: str, tf: TimeFrame, start: datetime, end: datetime) -> pd.DataFrame:
        # Fetch in chunks to respect API limits
        all_chunks: List[pd.DataFrame] = []
        cursor = start
        step = timedelta(days=self._window_days(tf))
        granularity = TF_TO_OANDA[tf]
        while cursor < end:
            window_end = min(cursor + step, end)
            df = self.api.get_candles_df(pair, granularity=granularity, date_f=cursor, date_t=window_end)
            if df is not None and not df.empty:
                all_chunks.append(df)
            cursor = window_end
        if not all_chunks:
            return pd.DataFrame()
        df_all = pd.concat(all_chunks, ignore_index=True)
        # Drop duplicates and sort by time
        df_all = df_all.drop_duplicates(subset=["time"]).sort_values("time").reset_index(drop=True)
        return df_all

    def _to_candles(self, df: pd.DataFrame, pair: str, tf: TimeFrame) -> List[CandleData]:
        candles: List[CandleData] = []
        if df is None or df.empty:
            return candles
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

    def _save_cache(self, pair: str, tf: TimeFrame, df: pd.DataFrame) -> None:
        path = self._cache_path(pair, tf)
        if df is not None and not df.empty:
            df.to_pickle(path)

    def _load_cache(self, pair: str, tf: TimeFrame) -> pd.DataFrame:
        path = self._cache_path(pair, tf)
        if path.exists():
            return pd.read_pickle(path)
        return pd.DataFrame()

    def load_last_3y_until_prev_week(self, pairs: List[str], timeframes: List[TimeFrame]) -> None:
        end = datetime.now(timezone.utc) - timedelta(days=7)
        start = end - timedelta(days=365*3)
        self.data.clear()
        for pair in pairs:
            self.data.setdefault(pair, {})
            for tf in timeframes:
                df = pd.DataFrame()
                if self.use_cache:
                    df = self._load_cache(pair, tf)
                    # If cache stale (doesn't reach 'end' by at least 1 day), top-up
                    if not df.empty:
                        last_time = pd.to_datetime(df['time'].iloc[-1], utc=True).to_pydatetime()
                        if last_time < end - timedelta(days=1):
                            topup = self._fetch_range(pair, tf, last_time, end)
                            if not topup.empty:
                                df = pd.concat([df, topup], ignore_index=True)
                                df = df.drop_duplicates(subset=["time"]).sort_values("time").reset_index(drop=True)
                                self._save_cache(pair, tf, df)
                if df.empty:
                    df = self._fetch_range(pair, tf, start, end)
                    if self.use_cache and not df.empty:
                        self._save_cache(pair, tf, df)
                self.data[pair][tf] = self._to_candles(df, pair, tf)

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


