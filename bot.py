import os, ccxt, time

api_key = os.getenv("KRAKEN_API_KEY")
api_secret = os.getenv("KRAKEN_API_SECRET")
pairs = os.getenv("PAIRS", "BTC/USD,ETH/USD").split(",")
timeframe = os.getenv("TIMEFRAME", "15m")
fast_ema = int(os.getenv("FAST_EMA", 20))
slow_ema = int(os.getenv("SLOW_EMA", 50))
require_ema200 = os.getenv("REQUIRE_EMA200", "true").lower() == "true"
base_size = float(os.getenv("BASE_SIZE_USD", 25))
tp_pct = float(os.getenv("TP_PCT", 1.5)) / 100
sl_pct = float(os.getenv("SL_PCT", 0.5)) / 100
trail_pct = float(os.getenv("TRAIL_PCT", 0.3)) / 100
cooldown = int(os.getenv("COOLDOWN_S", 90))

exchange = ccxt.kraken({
    "apiKey": api_key,
    "secret": api_secret,
    "enableRateLimit": True,
})

def ema(values, period):
    if len(values) < period:
        return None
    k = 2 / (period + 1)
    ema_val = values[0]
    for v in values[1:]:
        ema_val = v * k + ema_val * (1 - k)
    return ema_val

positions = {}

while True:
    for pair in pairs:
        try:
            ohlcv = exchange.fetch_ohlcv(pair, timeframe, limit=200)
            closes = [c[4] for c in ohlcv]

            ema_fast = ema(closes, fast_ema)
            ema_slow = ema(closes, slow_ema)
            ema200 = ema(closes, 200)
            price = closes[-1]

            if pair not in positions:
                if ema_fast > ema_slow and (not require_ema200 or price > ema200):
                    print(f"Kopen {pair} @ {price}")
                    positions[pair] = {"entry": price, "highest": price}
            else:
                pos = positions[pair]
                pos["highest"] = max(pos["highest"], price)

                tp_level = pos["entry"] * (1 + tp_pct)
                sl_level = pos["entry"] * (1 - sl_pct)
                trail_sl = pos["highest"] * (1 - trail_pct)

                if price >= tp_level or price <= sl_level or price <= trail_sl:
                    print(f"Sluit {pair} @ {price} | Entry {pos['entry']}")
                    del positions[pair]

        except Exception as e:
            print("Error:", e)
    time.sleep(cooldown)
