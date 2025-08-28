
import os, time, math, csv
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from dotenv import load_dotenv
import ccxt

from utils import log, to_bool
from strategy import compute_indicators, signal
from notifier import send_telegram
from notion_sync import add_trade_row

load_dotenv()

EXCHANGE = os.getenv('EXCHANGE','kraken').lower()
SYMBOL = os.getenv('SYMBOL','ETH/USD')
TIMEFRAME = os.getenv('TIMEFRAME','5m')
MAX_LOSS_USD = float(os.getenv('MAX_LOSS_USD','50'))
ATR_MULT_STOP = float(os.getenv('ATR_MULT_STOP','1.5'))
LEVERAGE = float(os.getenv('LEVERAGE','1'))
SLEEP_SECONDS = int(os.getenv('SLEEP_SECONDS','10'))
CANDLES_LIMIT = int(os.getenv('CANDLES_LIMIT','500'))
USE_EMA200_FILTER = to_bool(os.getenv('USE_EMA200_FILTER','true'))

PROFIT_TRIGGER_USD = float(os.getenv('PROFIT_TRIGGER_USD','100'))
TRAIL_AMOUNT_USD = float(os.getenv('TRAIL_AMOUNT_USD','15'))

def make_exchange():
    key = os.getenv('API_KEY','')
    secret = os.getenv('API_SECRET','')
    if EXCHANGE == 'krakenfutures':
        ex = ccxt.krakenfutures({'apiKey': key, 'secret': secret,'enableRateLimit': True})
    elif EXCHANGE == 'bybit':
        ex = ccxt.bybit({'apiKey': key, 'secret': secret,'enableRateLimit': True})
    else:
        ex = ccxt.kraken({'apiKey': key, 'secret': secret,'enableRateLimit': True})
    if hasattr(ex, 'set_sandbox_mode') and os.getenv('SANDBOX','').lower() in ('1','true','yes'):
        ex.set_sandbox_mode(True)
    if hasattr(ex, 'load_markets'):
        ex.load_markets()
    if hasattr(ex, 'options'):
        ex.options['defaultType'] = 'future' if EXCHANGE in ('krakenfutures','bybit') and LEVERAGE>1 else 'spot'
    return ex

def fetch_ohlcv(ex):
    candles = ex.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=CANDLES_LIMIT)
    df = pd.DataFrame(candles, columns=['timestamp','open','high','low','close','volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    return df

def write_trade(trade):
    os.makedirs('data', exist_ok=True)
    path = 'data/trades.csv'
    write_header = not os.path.exists(path)
    with open(path, 'a', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['timestamp','symbol','side','amount','entry_price','exit_price','pnl_usd','fees','notes'])
        if write_header: w.writeheader()
        w.writerow(trade)

def run():
    ex = make_exchange()
    log(f"Connected to {EXCHANGE}. Markets loaded: {len(ex.markets)}")
    position = None
    highest_pnl = 0.0

    while True:
        try:
            df = fetch_ohlcv(ex)
            df = compute_indicators(df)
            side, atr = signal(df, use_ema200=USE_EMA200_FILTER)
            last = df.iloc[-1]
            price = float(last['close'])

            if position:
                if position['side']=='long':
                    if price <= position['stop']:
                        order = ex.create_order(SYMBOL, 'market', 'sell', position['amount'])
                        exit_price = order.get('average', price) or price
                        pnl = (exit_price - position['entry']) * position['amount'] * (LEVERAGE if LEVERAGE>0 else 1)
                        write_trade({'timestamp': datetime.now(timezone.utc).isoformat(),
                                     'symbol': SYMBOL, 'side':'long', 'amount': position['amount'],
                                     'entry_price': position['entry'], 'exit_price': exit_price,
                                     'pnl_usd': pnl, 'fees': order.get('fee',''), 'notes':'SL'})
                        send_telegram(f"Exited LONG {SYMBOL} at {exit_price} via SL. PnL ${pnl:.2f}")
                        add_trade_row({'timestamp': datetime.now(timezone.utc).isoformat(),'symbol':SYMBOL,'side':'Long','amount':position['amount'],'entry_price':position['entry'],'exit_price':exit_price,'pnl_usd':pnl})
                        position=None; highest_pnl=0.0
                    else:
                        pnl_unreal = (price - position['entry']) * position['amount'] * (LEVERAGE if LEVERAGE>0 else 1)
                        highest_pnl = max(highest_pnl, pnl_unreal)
                        if pnl_unreal >= PROFIT_TRIGGER_USD and (highest_pnl - pnl_unreal) >= TRAIL_AMOUNT_USD:
                            order = ex.create_order(SYMBOL, 'market', 'sell', position['amount'])
                            exit_price = order.get('average', price) or price
                            pnl = (exit_price - position['entry']) * position['amount'] * (LEVERAGE if LEVERAGE>0 else 1)
                            write_trade({'timestamp': datetime.now(timezone.utc).isoformat(),
                                         'symbol': SYMBOL, 'side':'long', 'amount': position['amount'],
                                         'entry_price': position['entry'], 'exit_price': exit_price,
                                         'pnl_usd': pnl, 'fees': order.get('fee',''), 'notes':'Trailing TP'})
                            send_telegram(f"Exited LONG {SYMBOL} at {exit_price} via TRAIL. PnL ${pnl:.2f}")
                            add_trade_row({'timestamp': datetime.now(timezone.utc).isoformat(),'symbol':SYMBOL,'side':'Long','amount':position['amount'],'entry_price':position['entry'],'exit_price':exit_price,'pnl_usd':pnl})
                            position=None; highest_pnl=0.0

                elif position['side']=='short':
                    if price >= position['stop']:
                        order = ex.create_order(SYMBOL, 'market', 'buy', position['amount'])
                        exit_price = order.get('average', price) or price
                        pnl = (position['entry'] - exit_price) * position['amount'] * (LEVERAGE if LEVERAGE>0 else 1)
                        write_trade({'timestamp': datetime.now(timezone.utc).isoformat(),
                                     'symbol': SYMBOL, 'side':'short', 'amount': position['amount'],
                                     'entry_price': position['entry'], 'exit_price': exit_price,
                                     'pnl_usd': pnl, 'fees': order.get('fee',''), 'notes':'SL'})
                        send_telegram(f"Exited SHORT {SYMBOL} at {exit_price} via SL. PnL ${pnl:.2f}")
                        add_trade_row({'timestamp': datetime.now(timezone.utc).isoformat(),'symbol':SYMBOL,'side':'Short','amount':position['amount'],'entry_price':position['entry'],'exit_price':exit_price,'pnl_usd':pnl})
                        position=None; highest_pnl=0.0
                    else:
                        pnl_unreal = (position['entry'] - price) * position['amount'] * (LEVERAGE if LEVERAGE>0 else 1)
                        highest_pnl = max(highest_pnl, pnl_unreal)
                        if pnl_unreal >= PROFIT_TRIGGER_USD and (highest_pnl - pnl_unreal) >= TRAIL_AMOUNT_USD:
                            order = ex.create_order(SYMBOL, 'market', 'buy', position['amount'])
                            exit_price = order.get('average', price) or price
                            pnl = (position['entry'] - exit_price) * position['amount'] * (LEVERAGE if LEVERAGE>0 else 1)
                            write_trade({'timestamp': datetime.now(timezone.utc).isoformat(),
                                         'symbol': SYMBOL, 'side':'short', 'amount': position['amount'],
                                         'entry_price': position['entry'], 'exit_price': exit_price,
                                         'pnl_usd': pnl, 'fees': order.get('fee',''), 'notes':'Trailing TP'})
                            send_telegram(f"Exited SHORT {SYMBOL} at {exit_price} via TRAIL. PnL ${pnl:.2f}")
                            add_trade_row({'timestamp': datetime.now(timezone.utc).isoformat(),'symbol':SYMBOL,'side':'Short','amount':position['amount'],'entry_price':position['entry'],'exit_price':exit_price,'pnl_usd':pnl})
                            position=None; highest_pnl=0.0

            if not position and side:
                stop_distance = atr * ATR_MULT_STOP
                stop = price - stop_distance if side=='long' else price + stop_distance
                risk_per_unit = stop_distance
                amount = (MAX_LOSS_USD / risk_per_unit) / (LEVERAGE if LEVERAGE>1 else 1)
                market = ex.market(SYMBOL)
                try:
                    amount = float(ex.amount_to_precision(SYMBOL, amount))
                except Exception:
                    pass

                side_ccxt = 'buy' if side=='long' else 'sell'
                order = ex.create_order(SYMBOL, 'market', side_ccxt, amount)
                entry = order.get('average', price) or price
                position = {'side': side, 'amount': amount, 'entry': entry, 'stop': stop}
                highest_pnl = 0.0
                send_telegram(f"Entered {side.upper()} {SYMBOL} amount {amount} at {entry}. Stop at {stop}. Max risk ≈ ${MAX_LOSS_USD}")
                log(f"Entered {side} {SYMBOL} amount {amount:.6f} at {entry}. Stop {stop}.")

        except Exception as e:
            log(f"Loop error: {e}")
        time.sleep(SLEEP_SECONDS)

if __name__ == '__main__':
    os.makedirs('data', exist_ok=True)
    run()
