#!/usr/bin/env python3
"""
Create instruments.json file by fetching from OANDA API
"""

import sys
from pathlib import Path

# Add the project root to the path
root_dir = Path(__file__).parent
sys.path.append(str(root_dir / "src"))

from api.oanda_api import OandaApi
from infrastructure.instrument_collection import InstrumentCollection

def main():
    print("🔧 Creating instruments.json file...")
    
    # Initialize OANDA API
    api = OandaApi()
    
    # Validate credentials
    if not api.validate_credentials():
        print("❌ OANDA API credentials are invalid. Please check config.env")
        return 1
    
    # Get account instruments
    instruments = api.get_account_instruments()
    
    if not instruments:
        print("❌ Failed to fetch instruments from OANDA")
        return 1
    
    # Create instruments file
    ic = InstrumentCollection()
    ic.CreateFile(instruments, "src/data")
    
    print(f"✅ Created instruments.json with {len(instruments)} instruments")
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

