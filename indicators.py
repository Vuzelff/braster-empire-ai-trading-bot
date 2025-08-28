
import numpy as np
import pandas as pd

def ema(series, window):
    return series.ewm(span=window, adjust=False).mean()

def rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))

def macd(series, fast=12, slow=26, signal=9):
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

def atr(df, period=14):
    high = df['high']; low = df['low']; close = df['close']
    prev_close = close.shift(1)
    tr = pd.concat([high-low, (high-prev_close).abs(), (low-prev_close).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def adx(df, period=14):
    high = df['high']; low = df['low']; close = df['close']
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    trur = atr(df, period)
    plus_di = 100 * (plus_dm.rolling(period).sum() / (trur.rolling(period).sum() + 1e-9))
    minus_di = 100 * (minus_dm.rolling(period).sum() / (trur.rolling(period).sum() + 1e-9))
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9)) * 100
    adx = dx.rolling(period).mean()
    return adx, plus_di, minus_di
