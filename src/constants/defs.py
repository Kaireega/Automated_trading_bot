import os
from pathlib import Path

def load_env_from_file(file_path='config.env'):
    """Load environment variables from a config file"""
    # Try multiple possible locations for the config file
    possible_paths = [
        file_path,  # Current directory
        Path(__file__).parent.parent / file_path,  # Root directory (one level up from constants)
        Path(__file__).parent.parent.parent / file_path,  # Two levels up
        '.env',  # Standard .env file
        Path(__file__).parent.parent / '.env',  # .env in root directory
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"Loading environment from: {path}")
            with open(path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key] = value
            return True
    
    print("Warning: No config.env or .env file found")
    return False

# Load environment variables from config file (optional convenience)
load_env_from_file()

# API Configuration - Require environment variables for sensitive values
API_KEY = os.getenv('OANDA_API_KEY')
ACCOUNT_ID = os.getenv('OANDA_ACCOUNT_ID')
OANDA_URL = os.getenv('OANDA_URL', 'https://api-fxpractice.oanda.com/v3')

SECURE_HEADER = {
    "Authorization": f"Bearer {API_KEY}" if API_KEY else "",
    "Content-Type": "application/json"
}

SELL = -1
BUY = 1
NONE = 0

# Database connection string should be provided via environment only
MONGO_CONN_STR = os.getenv('MONGO_CONN_STR')
INVESTING_COM_PAIRS = {
   "EUR_USD":{
      "pair":"EUR_USD",
      "pair_id":1
   },
   "GBP_USD":{
      "pair":"GBP_USD",
      "pair_id":2
   },
   "USD_JPY":{
      "pair":"USD_JPY",
      "pair_id":3
   },
   "USD_CHF":{
      "pair":"USD_CHF",
      "pair_id":4
   },
   "AUD_USD":{
      "pair":"AUD_USD",
      "pair_id":5
   },
   "EUR_GBP":{
      "pair":"EUR_GBP",
      "pair_id":6
   },
   "USD_CAD":{
      "pair":"USD_CAD",
      "pair_id":7
   },
   "NZD_USD":{
      "pair":"NZD_USD",
      "pair_id":8
   },
   "EUR_JPY":{
      "pair":"EUR_JPY",
      "pair_id":9
   },
   "EUR_CHF":{
      "pair":"EUR_CHF",
      "pair_id":10
   },
   "GBP_JPY":{
      "pair":"GBP_JPY",
      "pair_id":11
   },
   "GBP_CHF":{
      "pair":"GBP_CHF",
      "pair_id":12
   },
   "CHF_JPY":{
      "pair":"CHF_JPY",
      "pair_id":13
   },
   "CAD_CHF":{
      "pair":"CAD_CHF",
      "pair_id":14
   },
   "EUR_AUD":{
      "pair":"EUR_AUD",
      "pair_id":15
   },
   "EUR_CAD":{
      "pair":"EUR_CAD",
      "pair_id":16
   },
   "USD_ZAR":{
      "pair":"USD_ZAR",
      "pair_id":17
   },
   "USD_TRY":{
      "pair":"USD_TRY",
      "pair_id":18
   },
   "EUR_NOK":{
      "pair":"EUR_NOK",
      "pair_id":37
   },
   "BTC_NZD":{
      "pair":"BTC_NZD",
      "pair_id":38
   },
   "USD_MXN":{
      "pair":"USD_MXN",
      "pair_id":39
   },
   "USD_PLN":{
      "pair":"USD_PLN",
      "pair_id":40
   },
   "USD_SEK":{
      "pair":"USD_SEK",
      "pair_id":41
   },
   "USD_SGD":{
      "pair":"USD_SGD",
      "pair_id":42
   },
   "USD_DKK":{
      "pair":"USD_DKK",
      "pair_id":43
   },
   "EUR_DKK":{
      "pair":"EUR_DKK",
      "pair_id":44
   },
   "EUR_PLN":{
      "pair":"EUR_PLN",
      "pair_id":46
   },
   "AUD_CAD":{
      "pair":"AUD_CAD",
      "pair_id":47
   },
   "AUD_CHF":{
      "pair":"AUD_CHF",
      "pair_id":48
   },
   "AUD_JPY":{
      "pair":"AUD_JPY",
      "pair_id":49
   },
   "AUD_NZD":{
      "pair":"AUD_NZD",
      "pair_id":50
   },
   "CAD_JPY":{
      "pair":"CAD_JPY",
      "pair_id":51
   },
   "EUR_NZD":{
      "pair":"EUR_NZD",
      "pair_id":52
   },
   "GBP_AUD":{
      "pair":"GBP_AUD",
      "pair_id":53
   },
   "GBP_CAD":{
      "pair":"GBP_CAD",
      "pair_id":54
   },
   "GBP_NZD":{
      "pair":"GBP_NZD",
      "pair_id":55
   },
   "NZD_CAD":{
      "pair":"NZD_CAD",
      "pair_id":56
   },
   "NZD_CHF":{
      "pair":"NZD_CHF",
      "pair_id":57
   },
   "NZD_JPY":{
      "pair":"NZD_JPY",
      "pair_id":58
   },
   "USD_NOK":{
      "pair":"USD_NOK",
      "pair_id":59
   }
}

TFS = {
   "M5": 300,
   "M15": 900,
   "H1": 3600,
   "D": 86400
}
