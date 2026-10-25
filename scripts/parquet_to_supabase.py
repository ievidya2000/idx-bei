#!/usr/bin/env python3
"""Push IDX-BEI parquet + json to Supabase. Schema-aware."""
import os, glob, csv, io, json, subprocess, requests

URL = os.environ["SUPABASE_URL"]
KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}",
     "Content-Type": "application/json",
     "Prefer": "resolution=merge-duplicates"}

def clean_date(s):
    return s.split("T")[0] if s else None

def duck(path):
    q = f"COPY (SELECT * FROM read_parquet('{path}')) TO STDOUT (HEADER, FORMAT CSV)"
    out = subprocess.check_output(["duckdb", "-c", q], text=True)
    return list(csv.DictReader(io.StringIO(out)))

def upsert(table, rows, batch=500):
    if not rows:
        print(f"→ {table}: 0 rows (skipped)"); return
    total = 0
    for i in range(0, len(rows), batch):
        chunk = rows[i:i+batch]
        r = requests.post(f"{URL}/rest/v1/{table}", headers=H, json=chunk)
        if not r.ok:
            print(f"❌ {table} {r.status_code}: {r.text[:400]}"); return
        total += len(chunk)
        print(f"  {table}: {total}/{len(rows)}", flush=True)
    print(f"→ {table}: {total} rows ✅")

base = os.path.expanduser("~/idx-bei/data/timeseries")

# ---- stock_summary (parquet) ----
rows = []
for p in glob.glob(f"{base}/stock_summary/*.parquet"):
    for r in duck(p):
        rows.append({
            "date": clean_date(r["Date"]),
            "stock_code": r["StockCode"],
            "stock_name": r["StockName"],
            "previous": float(r["Previous"] or 0),
            "open_price": float(r["OpenPrice"] or 0),
            "high": float(r["High"] or 0),
            "low": float(r["Low"] or 0),
            "close": float(r["Close"] or 0),
            "change": float(r["Change"] or 0),
            "volume": float(r["Volume"] or 0),
            "value": float(r["Value"] or 0),
            "frequency": float(r["Frequency"] or 0),
            "foreign_sell": float(r["ForeignSell"] or 0),
            "foreign_buy": float(r["ForeignBuy"] or 0),
            "non_regular_volume": float(r["NonRegularVolume"] or 0),
            "non_regular_value": float(r["NonRegularValue"] or 0),
            "non_regular_frequency": float(r["NonRegularFrequency"] or 0),
        })
upsert("stock_summary", rows)

# ---- broker_summary (json) ----
rows = []
for p in glob.glob(f"{base}/broker_summary/*.json"):
    for r in json.load(open(p)):
        rows.append({
            "date": clean_date(r["Date"]),
            "broker_id": r["IDFirm"],
            "firm_name": r.get("FirmName"),
            "frequency": float(r.get("Frequency") or 0),
            "value": float(r.get("Value") or 0),
            "volume": float(r.get("Volume") or 0),
        })
upsert("broker_summary", rows)

# ---- index_summary (json) ----
rows = []
for p in glob.glob(f"{base}/index_summary/*.json"):
    for r in json.load(open(p)):
        rows.append({
            "date": clean_date(r["Date"]),
            "index_code": r["IndexCode"],
            "close": float(r.get("Close") or 0),
            "change": float(r.get("Change") or 0),
            "highest": float(r.get("Highest") or 0),
            "lowest": float(r.get("Lowest") or 0),
            "market_capital": float(r.get("MarketCapital") or 0),
            "number_of_stock": int(r.get("NumberOfStock") or 0),
            "previous": float(r.get("Previous") or 0),
            "value": float(r.get("Value") or 0),
            "volume": float(r.get("Volume") or 0),
            "frequency": float(r.get("Frequency") or 0),
        })
upsert("index_summary", rows)
