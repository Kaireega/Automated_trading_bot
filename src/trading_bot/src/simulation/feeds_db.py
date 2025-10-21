"""
MongoDB-backed historical data feed for simulation.
Loads last 3 years up to the previous week from DB if available; if missing,
fetches from OANDA in chunks (using collect_data.py approach), stores to DB,
then serves to the simulator as CandleData, stepped like live.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List
from decimal import Decimal
from datetime import datetime, timedelta, timezone

import pandas as pd

from ..core.models import CandleData, TimeFrame
from api.oanda_api import OandaApi
from db.db import DataDB
from pymongo import errors as mongo_errors


class DBHistoricalFeed:
    COLLECTION = "forex_candles"

    def __init__(self):
        self.db = DataDB()
        self.api = OandaApi()
        self.data: Dict[str, Dict[TimeFrame, List[CandleData]]] = {}
        # Ensure unique index to avoid duplicates on re-runs
        try:
            print("[DBFeed] Ensuring unique index on (pair,timeframe,time)...")
            self.db.db[self.COLLECTION].create_index(
                [("pair", 1), ("timeframe", 1), ("time", 1)], unique=True
            )
        except Exception as e:
            print(f"[DBFeed] Index ensure warning: {e}")

    def _to_df(self, docs: List[dict]) -> pd.DataFrame:
        if not docs:
            return pd.DataFrame()
        df = pd.DataFrame(docs)
        # Normalize time to pandas datetime UTC
        if 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time'], utc=True)
        return df

    def _df_to_candles(self, df: pd.DataFrame, pair: str, tf: TimeFrame) -> List[CandleData]:
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

    def _query_db_range(self, pair: str, tf: TimeFrame, start: datetime, end: datetime) -> pd.DataFrame:
        filt = {
            'pair': pair,
            'timeframe': tf.value,
            'time': { '$gte': start, '$lt': end }
        }
        docs = self.db.query_all(self.COLLECTION, **filt) or []
        return self._to_df(docs)

    def _insert_df(self, pair: str, tf: TimeFrame, df: pd.DataFrame) -> None:
        if df is None or df.empty:
            return
        records = []
        for _, row in df.iterrows():
            records.append({
                'pair': pair,
                'timeframe': tf.value,
                'time': pd.to_datetime(row['time'], utc=True).to_pydatetime(),
                'mid_o': float(row['mid_o']),
                'mid_h': float(row['mid_h']),
                'mid_l': float(row['mid_l']),
                'mid_c': float(row['mid_c']),
                'volume': float(row['volume']) if 'volume' in df.columns else None,
            })
        if records:
            print(f"[DBFeed] Inserting {len(records)} records into {self.COLLECTION} for {pair} {tf.value}...")
            try:
                # Bulk insert; ignore duplicates thanks to unique index
                self.db.db[self.COLLECTION].insert_many(records, ordered=False)
            except mongo_errors.BulkWriteError as bwe:
                # Ignore duplicate key errors
                dup = sum(1 for err in bwe.details.get('writeErrors', []) if err.get('code') == 11000)
                print(f"[DBFeed] Bulk insert encountered {dup} duplicates (ignored)")
            except Exception as e:
                print(f"[DBFeed] Insert warning: {e}")

    def _fetch_chunks(self, pair: str, tf: TimeFrame, start: datetime, end: datetime) -> pd.DataFrame:
        # Similar to infrastructure/collect_data.py logic
        increments_min = {
            'M5': 5 * 3000,
            'M15': 15 * 3000,
            'H1': 60 * 3000,
            'H4': 240 * 3000,
            'M1': 1 * 3000,
        }
        step = timedelta(minutes=increments_min.get(tf.value, 60 * 3000))
        cursor = start
        chunks: List[pd.DataFrame] = []
        while cursor < end:
            to_date = min(cursor + step, end)
            print(f"[DBFeed] Fetching {pair} {tf.value} {cursor.isoformat()} -> {to_date.isoformat()} ...")
            df = self.api.get_candles_df(pair, granularity=tf.value, date_f=cursor, date_t=to_date)
            if df is not None and not df.empty:
                print(f"[DBFeed]   fetched {len(df)} candles")
                chunks.append(df)
            cursor = to_date
        if not chunks:
            return pd.DataFrame()
        out = pd.concat(chunks, ignore_index=True)
        out = out.drop_duplicates(subset=['time']).sort_values('time').reset_index(drop=True)
        return out

    def load_last_3y_until_prev_week(self, pairs: List[str], timeframes: List[TimeFrame]) -> None:
        end = datetime.now(timezone.utc) - timedelta(days=7)
        start = end - timedelta(days=365*3)
        self.data.clear()
        for pair in pairs:
            self.data.setdefault(pair, {})
            for tf in timeframes:
                print(f"[DBFeed] Loading {pair} {tf.value} for window {start.date()} -> {end.date()}")
                # Try DB first
                df = self._query_db_range(pair, tf, start, end)
                if not df.empty:
                    print(f"[DBFeed]   DB returned {len(df)} candles")
                # If DB insufficient (empty), fetch and store
                if df.empty:
                    fetched = self._fetch_chunks(pair, tf, start, end)
                    if not fetched.empty:
                        self._insert_df(pair, tf, fetched)
                        df = fetched
                # Convert to candles
                candles = self._df_to_candles(df, pair, tf)
                self.data[pair][tf] = candles
                print(f"[DBFeed]   loaded {len(candles)} candles into feed for {pair} {tf.value}")

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


