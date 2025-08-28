
# Braster Empire — AI Trading Bot (Kraken/Bybit via CCXT)

**Features**
- Kraken (spot) + Kraken Futures + Bybit via CCXT
- High‑conviction momentum strategy (RSI + MACD + ADX + EMA200 filter)
- Risk capped: **MAX_LOSS_USD** per trade (ATR‑based stop)
- **Trailing take‑profit**: arms after `PROFIT_TRIGGER_USD`, trails by `TRAIL_AMOUNT_USD`
- CSV logging (`data/trades.csv`) + Telegram notifications + optional Notion sync
- Render‑ready

## Quick start
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env (set keys & prefs)
python bot.py
```

**Render**
- Build: `pip install -r requirements.txt`
- Start: `python bot.py`
- Zet alle `.env` variabelen in Render (upload je `.env` nooit naar GitHub).

**Disclaimer**: Gebruik op eigen risico. Geen financieel advies.
