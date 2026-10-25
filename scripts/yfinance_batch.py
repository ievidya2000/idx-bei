import os, requests
import pandas as pd
import yfinance as yf
from datetime import datetime

URL = os.environ["SUPABASE_URL"]
KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
HEADERS = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates"}
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

today = datetime.now().strftime("%Y-%m-%d")
print(f"Fetching Yahoo Finance intraday data for {today}...")

# (Using the 10 bluechips for testing)
tickers = ["BBCA.JK", "BBRI.JK", "BMRI.JK", "BBNI.JK", "TLKM.JK", "ASII.JK", "UNVR.JK", "ICBP.JK", "INDF.JK", "KLBF.JK"]

all_data = []
for i in range(0, len(tickers), 50):
    batch = tickers[i:i+50]
    data = yf.download(batch, period="1d", interval="1d", group_by="ticker", progress=False)
    
    for ticker in batch:
        try:
            df_ticker = data[ticker].dropna()
            if not df_ticker.empty:
                latest = df_ticker.iloc[-1]
                all_data.append({
                    "date": today,
                    "stock_code": ticker.replace(".JK", ""),
                    "stock_name": ticker.replace(".JK", ""),
                    "open_price": float(latest["Open"]),
                    "high": float(latest["High"]),
                    "low": float(latest["Low"]),
                    "close": float(latest["Close"]),
                    "volume": float(latest["Volume"]),
                    "change": float(latest["Close"] - latest["Open"]),
                    "value": float(latest["Volume"] * latest["Close"]),
                    "previous": float(latest["Open"]),
                    "foreign_buy": 0.0,
                    "foreign_sell": 0.0,
                })
        except Exception:
            continue

if all_data:
    print(f"Pushing {len(all_data)} YF records to Supabase...")
    requests.post(f"{URL}/rest/v1/stock_summary", headers=HEADERS, json=all_data)
    print("✅ Supabase updated via YF.")

    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        df = pd.DataFrame(all_data)
        df["change_pct"] = (df["change"] / df["previous"].replace(0, 1)) * 100
        top_picks = df.nlargest(10, 'value')[['stock_code', 'close', 'change_pct', 'volume']]
        
        html_table = top_picks.to_html(index=False, classes='table table-striped', border=1)
        html_content = f"<html><head><style>table {{border-collapse: collapse; width: 100%;}} th, td {{border: 1px solid #ddd; padding: 8px;}}</style></head><body><h2>📊 Top 10 Market Picks</h2>{html_table}</body></html>"
        
        with open("yf_top_picks.html", "w") as f: f.write(html_content)
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
        with open("yf_top_picks.html", "rb") as doc:
            r = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "caption": f"YF Report {today}"}, files={"document": doc})
        print("Telegram HTML sent:", r.status_code)
