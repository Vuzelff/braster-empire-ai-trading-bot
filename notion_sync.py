
import os, requests, json
from utils import log

NOTION_TOKEN = os.getenv('NOTION_TOKEN')
NOTION_DB_ID = os.getenv('NOTION_DB_ID')
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
} if NOTION_TOKEN else None

def add_trade_row(trade):
    if not (NOTION_TOKEN and NOTION_DB_ID):
        return
    try:
        payload = {
            "parent": {"database_id": NOTION_DB_ID},
            "properties": {
                "Time": {"date": {"start": trade.get("timestamp")}},
                "Symbol": {"title": [{"text": {"content": trade.get("symbol","")}}]},
                "Side": {"select": {"name": trade.get("side","")}},
                "Qty": {"number": float(trade.get("amount",0))},
                "Entry": {"number": float(trade.get("entry_price",0))},
                "Exit": {"number": float(trade.get("exit_price",0))},
                "PnL_USD": {"number": float(trade.get("pnl_usd",0))},
            }
        }
        r = requests.post("https://api.notion.com/v1/pages", headers=HEADERS, json=payload, timeout=20)
        if r.status_code >= 300:
            log(f"Notion error {r.status_code}: {r.text}")
    except Exception as e:
        log(f"Notion exception: {e}")
