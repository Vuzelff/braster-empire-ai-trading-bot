
import time, os
from datetime import datetime, timezone

def log(txt, fp='data/log.txt', also_print=True):
    os.makedirs('data', exist_ok=True)
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    line = f"[{now}] {txt}"
    if also_print:
        print(line, flush=True)
    with open(fp, 'a') as f:
        f.write(line + "\n")

def clamp(n, min_v, max_v):
    return max(min(max_v, n), min_v)

def to_bool(v):
    return str(v).lower() in ('1','true','yes','y','on')

def now_ms():
    return int(time.time() * 1000)
