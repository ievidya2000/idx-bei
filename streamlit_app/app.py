import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="IDX-BEI God Mode", layout="wide")
st.title("🇮🇩 IDX-BEI Quant Dashboard")

# --- Helper: Make HTML Sortable ---
def get_sortable_html(df):
    html = df.to_html(index=False, classes='table table-striped', border=0, table_id='myTable')
    js = """
    <script src="https://code.jquery.com/jquery-3.5.1.js"></script>
    <script src="https://cdn.datatables.net/1.10.22/js/jquery.dataTables.min.js"></script>
    <link rel="stylesheet" href="https://cdn.datatables.net/1.10.22/css/jquery.dataTables.min.css">
    <script>$(document).ready(function() { $('#myTable').DataTable(); });</script>
    """
    return html + js

@st.cache_data(ttl=300)
def query(table, params=""):
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_ANON_KEY"]
    r = requests.get(f"{url}/rest/v1/{table}?select=*{params}",
                     headers={"apikey": key, "Authorization": f"Bearer {key}"})
    r.raise_for_status()
    return pd.DataFrame(r.json())

# Load Data (Fixed column name to 'date')
try:
    df = query("stock_summary", "&order=date.desc&limit=2000")
    broker_df = query("broker_summary", "&order=date.desc&limit=2000")
except Exception as e:
    st.error(f"Database error: {e}")
    st.stop()

if df.empty:
    st.warning("No data yet — run the GitHub Workflow or Termux sync.")
    st.stop()

# Get latest date
latest_date = df["date"].max()
df = df[df["date"] == latest_date].copy()
broker_df = broker_df[broker_df["date"] == latest_date].copy()

# Calculations
df["foreign_net"] = df["foreign_buy"].fillna(0) - df["foreign_sell"].fillna(0)
df["change_pct"] = (df["change"] / df["previous"].replace(0, 1)) * 100

st.caption(f"Latest trading day: **{latest_date}** · {len(df)} stocks")

# --- Tabs ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 Market Screener", "💱 Foreign Flow", "🏦 Broker Flow", "🕵️ Stealth Accumulation", "📈 Chart"
])

# 1. MARKET SCREENER
with tab1:
    st.subheader("Top Volume & Value")
    view = df[["stock_code","stock_name","close","change_pct","volume","value"]].sort_values("value", ascending=False)
    
    st.download_button(
        label="⬇️ Download HTML (Sortable)",
        data=get_sortable_html(view),
        file_name=f"market_screener_{latest_date}.html",
        mime="text/html"
    )
    st.dataframe(view, use_container_width=True, height=400)

# 2. FOREIGN FLOW
with tab2:
    st.subheader("Net Foreign Flow (Top 20)")
    flow = df[["stock_code","stock_name","close","foreign_buy","foreign_sell","foreign_net"]].sort_values("foreign_net", ascending=False)
    
    st.download_button(
        label="⬇️ Download HTML (Sortable)",
        data=get_sortable_html(flow.head(50)),
        file_name=f"foreign_flow_{latest_date}.html",
        mime="text/html"
    )
    col1, col2 = st.columns(2)
    col1.write("**Top Net Foreign BUY**")
    col1.dataframe(flow.head(10), use_container_width=True, hide_index=True)
    col2.write("**Top Net Foreign SELL**")
    col2.dataframe(flow.tail(10), use_container_width=True, hide_index=True)

# 3. BROKER FLOW (Bandarmology)
with tab3:
    st.subheader("Top Broker Accumulation")
    if not broker_df.empty:
        broker_view = broker_df[["broker_id","firm_name","value","volume"]].sort_values("value", ascending=False)
        st.download_button(
            label="⬇️ Download HTML (Sortable)",
            data=get_sortable_html(broker_view),
            file_name=f"broker_flow_{latest_date}.html",
            mime="text/html"
        )
        st.dataframe(broker_view, use_container_width=True, height=400)
    else:
        st.info("Broker data requires the IDX EOD sync (Termux).")

# 4. STEALTH ACCUMULATION
with tab4:
    st.subheader("Stealth Accumulation (High Vol, Low Price Change)")
    # Logic: Volume > 10M, but price change is between -2% and +2%
    stealth = df[(df["volume"] > 10000000) & (df["change_pct"].between(-2, 2))]
    stealth = stealth[["stock_code","stock_name","close","change_pct","volume","foreign_net"]].sort_values("volume", ascending=False)
    
    if not stealth.empty:
        st.download_button(
            label="⬇️ Download HTML (Sortable)",
            data=get_sortable_html(stealth),
            file_name=f"stealth_accum_{latest_date}.html",
            mime="text/html"
        )
        st.dataframe(stealth, use_container_width=True, height=400)
    else:
        st.info("No stealth accumulation detected today.")

# 5. CHARTS
with tab5:
    tickers = sorted(df["stock_code"].unique())
    sel = st.multiselect("Select Tickers", tickers, default=tickers[:3])
    if sel:
        hist = query("stock_summary", f"&stock_code=in.({','.join(sel)})&order=date.asc")
        for t in sel:
            st.subheader(t)
            d = hist[hist["stock_code"] == t]
            if not d.empty:
                st.line_chart(d.set_index("date")["close"], height=250)
