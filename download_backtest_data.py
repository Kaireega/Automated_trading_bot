#!/usr/bin/env python3
"""
Download Historical Data for Backtesting

This script uses your existing collect_data.py to download historical
candle data for backtesting. It will download 90 days of data for
all required pairs and timeframes.

Usage:
    python download_backtest_data.py
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from infrastructure.instrument_collection import InstrumentCollection
from infrastructure.collect_data import collect_data
from api.oanda_api import OandaApi


def main():
    print("\n" + "="*80)
    print("  DOWNLOADING HISTORICAL DATA FOR BACKTESTING")
    print("="*80)
    print()
    
    # Initialize API and instrument collection
    print("⚙️  Initializing OANDA API...")
    api = OandaApi()
    
    print("📊 Loading instrument collection...")
    ic = InstrumentCollection()
    
    # Define parameters
    pairs = ["EUR_USD", "GBP_USD", "USD_JPY"]
    granularities = ["M5", "M15"]  # M1 is optional, often too much data
    days_to_collect = 90
    
    # Calculate dates
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days_to_collect)
    
    date_from = start_date.strftime("%Y-%m-%d")
    date_to = end_date.strftime("%Y-%m-%d")
    
    print(f"\n📅 Collection Parameters:")
    print(f"   Pairs: {', '.join(pairs)}")
    print(f"   Timeframes: {', '.join(granularities)}")
    print(f"   Date Range: {date_from} to {date_to}")
    print(f"   Days: {days_to_collect}")
    print(f"   Output: data/ directory")
    print()
    
    # Confirm
    print("⚠️  This will download historical data from OANDA.")
    print("   This may take 5-10 minutes depending on your connection.")
    print("   Starting download...")
    
    print()
    print("="*80)
    print("  DOWNLOADING DATA...")
    print("="*80)
    print()
    
    # Collect data for each pair and granularity
    total_collections = len(pairs) * len(granularities)
    current = 0
    
    for pair in pairs:
        for granularity in granularities:
            current += 1
            print(f"\n[{current}/{total_collections}] Collecting {pair} {granularity}...")
            print("-" * 80)
            
            try:
                collect_data(
                    pair=pair,
                    granularity=granularity,
                    date_f=date_from,
                    date_t=date_to,
                    file_prefix="data/",
                    api=api
                )
                print(f"✅ {pair} {granularity} completed")
                
            except Exception as e:
                print(f"❌ Error collecting {pair} {granularity}: {e}")
                continue
    
    print()
    print("="*80)
    print("  DOWNLOAD COMPLETE")
    print("="*80)
    print()
    
    # List downloaded files
    print("📁 Downloaded Files:")
    data_dir = Path("data")
    pkl_files = sorted(data_dir.glob("*.pkl"))
    
    if pkl_files:
        for pkl_file in pkl_files:
            size_mb = pkl_file.stat().st_size / (1024 * 1024)
            print(f"   ✅ {pkl_file.name} ({size_mb:.2f} MB)")
        print()
        print(f"   Total: {len(pkl_files)} files")
    else:
        print("   ⚠️  No files found. Check for errors above.")
    
    print()
    print("="*80)
    print("  NEXT STEPS")
    print("="*80)
    print()
    print("Now you can run the backtest:")
    print()
    print("   python run_comprehensive_backtest.py --days 90 --pairs EUR_USD,GBP_USD,USD_JPY")
    print()
    print("="*80)
    print()


if __name__ == "__main__":
    main()

