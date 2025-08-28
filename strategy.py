
import pandas as pd
from indicators import ema, rsi, macd, adx, atr

def compute_indicators(df):
    df = df.copy()
    df['ema50'] = ema(df['close'], 50)
    df['ema200'] = ema(df['close'], 200)
    df['rsi'] = rsi(df['close'], 14)
    m_line, s_line, hist = macd(df['close'], 12, 26, 9)
    df['macd'] = m_line; df['macd_signal'] = s_line; df['macd_hist'] = hist
    df['atr'] = atr(df, 14)
    df['adx'], df['plus_di'], df['minus_di'] = adx(df, 14)
    return df

def signal(df, use_ema200=True):
    last = df.iloc[-1]
    trend_up = last['ema50'] > last['ema200'] if use_ema200 else True
    trend_down = last['ema50'] < last['ema200'] if use_ema200 else True

    long_cond = trend_up and last['rsi'] > 55 and last['macd'] > last['macd_signal'] and last['adx'] > 18 and last['close'] > df['high'].rolling(20).max().iloc[-2]
    short_cond = trend_down and last['rsi'] < 45 and last['macd'] < last['macd_signal'] and last['adx'] > 18 and last['close'] < df['low'].rolling(20).min().iloc[-2]

    side = 'long' if long_cond else ('short' if short_cond else None)
    return side, last['atr']
