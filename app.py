import streamlit as st, requests, pandas as pd
st.set_page_config(page_title="IDX-BEI", layout="wide")
st.title("🇮🇩 IDX-BEI Screener & Charts")

@st.cache_data(ttl=600)
def fetch(table="stock_summary", limit=5000):
    url, key = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"]
    r = requests.get(f"{url}/rest/v1/{table}?select=*&order=trade_date.desc&limit={limit}",
                     headers={"apikey": key, "Authorization": f"Bearer {key}"})
    r.raise_for_status()
    return r.json()

raw = fetch()
if not raw:
    st.warning("No data yet — run idx-sync + bridge.")
else:
    df = pd.DataFrame([r["data"] for r in raw])
    df["trade_date"] = [r["trade_date"] for r in raw]
    st.sidebar.header("Filters")
    tickers = sorted(df.get("StockCode", pd.Series()).dropna().unique())
    sel = st.sidebar.multiselect("Tickers", tickers, default=tickers[:3])
    if sel and "StockCode" in df:
        sub = df[df["StockCode"].isin(sel)].sort_values("trade_date")
        for t in sel:
            st.subheader(t)
            if "Close" in sub.columns:
                st.line_chart(sub[sub["StockCode"]==t].set_index("trade_date")["Close"])
    st.subheader("All data")
    st.dataframe(df, use_container_width=True)
