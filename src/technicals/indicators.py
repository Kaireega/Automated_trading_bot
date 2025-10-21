import pandas as pd

def BollingerBands(df: pd.DataFrame, n=20, s=2):
    typical_p = ( df.mid_c + df.mid_h + df.mid_l ) / 3
    stddev = typical_p.rolling(window=n).std()
    df['BB_MA'] = typical_p.rolling(window=n).mean()
    df['BB_UP'] = df['BB_MA'] + stddev * s
    df['BB_LW'] = df['BB_MA'] - stddev * s
    return df

def ATR(df: pd.DataFrame, n=14):
    try:
        prev_c = df.mid_c.shift(1)
        tr1 = df.mid_h - df.mid_l
        tr2 = abs(df.mid_h - prev_c)
        tr3 = abs(prev_c - df.mid_l)
        
        # Handle NaN values before max operation
        tr1 = tr1.fillna(0)
        tr2 = tr2.fillna(0)
        tr3 = tr3.fillna(0)
        
        tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
        df[f"ATR_{n}"] = tr.rolling(window=n).mean()
        return df
    except Exception as e:
        # Return original DataFrame if ATR calculation fails
        print(f"Error in ATR calculation: {e}")
        df[f"ATR_{n}"] = 0.0
        return df

def KeltnerChannels(df: pd.DataFrame, n_ema=20, n_atr=10):
    df['EMA'] = df.mid_c.ewm(span=n_ema, min_periods=n_ema).mean()
    df = ATR(df, n=n_atr)
    c_atr = f"ATR_{n_atr}"
    df['KeUp'] = df[c_atr] * 2 + df.EMA
    df['KeLo'] = df.EMA - df[c_atr] * 2
    df.drop(c_atr, axis=1, inplace=True)
    return df


def RSI(df: pd.DataFrame, n=14):
    alpha = 1.0 / n
    gains = df.mid_c.diff()

    wins = pd.Series([ x if x >= 0 else 0.0 for x in gains ], name="wins")
    losses = pd.Series([ x * -1 if x < 0 else 0.0 for x in gains ], name="losses")

    wins_rma = wins.ewm(min_periods=n, alpha=alpha).mean()
    losses_rma = losses.ewm(min_periods=n, alpha=alpha).mean()

    rs = wins_rma / losses_rma

    df[f"RSI_{n}"] = 100.0 - (100.0 / (1.0 + rs))
    return df

def MACD(df: pd.DataFrame, n_slow=26, n_fast=12, n_signal=9):

    ema_long = df.mid_c.ewm(min_periods=n_slow, span=n_slow).mean()
    ema_short = df.mid_c.ewm(min_periods=n_fast, span=n_fast).mean()

    df['MACD'] = ema_short - ema_long
    df['SIGNAL'] = df.MACD.ewm(min_periods=n_signal, span=n_signal).mean()
    df['HIST'] = df.MACD - df.SIGNAL

    return df

def Stochastic(df: pd.DataFrame, n=14, k=3, d=3):
    """Calculate Stochastic Oscillator."""
    try:
        # Calculate %K
        lowest_low = df.mid_l.rolling(window=n).min()
        highest_high = df.mid_h.rolling(window=n).max()
        
        # Handle division by zero
        denominator = (highest_high - lowest_low)
        denominator = denominator.replace(0, 1)  # Replace 0 with 1 to avoid division by zero
        
        # %K = (Current Close - Lowest Low) / (Highest High - Lowest Low) * 100
        stoch_k = ((df.mid_c - lowest_low) / denominator) * 100
        
        # Handle NaN values
        stoch_k = stoch_k.fillna(50)  # Fill NaN with neutral value
        
        df['STOCH_K'] = stoch_k
        
        # %D is the 3-period SMA of %K
        df['STOCH_D'] = df['STOCH_K'].rolling(window=k).mean().fillna(50)
        
        return df
    except Exception as e:
        print(f"Error in Stochastic calculation: {e}")
        # Return original DataFrame with default values
        df['STOCH_K'] = 50.0
        df['STOCH_D'] = 50.0
        return df

def EMA(df: pd.DataFrame, n=20, column='mid_c'):
    """Calculate Exponential Moving Average."""
    df[f'EMA_{n}'] = df[column].ewm(span=n, min_periods=n).mean()
    return df





























