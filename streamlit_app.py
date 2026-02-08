import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

st.set_page_config(page_title="專業級資產監控-觸控終極版", layout="wide")

# --- 1. 資料初始化與邏輯 (維持不變) ---
if 'clients' not in st.session_state:
    st.session_state.clients = {"客戶 A": [{"date": "2024-01-01", "stock": "2330.TW", "price": 600.0, "shares": 1000, "type": "買入"}]}

def calculate_portfolio(transactions):
    summary = {}
    for tx in transactions:
        s = tx['stock']
        if s not in summary: summary[s] = {"total_shares": 0, "total_cost": 0.0}
        if tx['type'] == "買入":
            summary[s]["total_shares"] += tx['shares']
            summary[s]["total_cost"] += tx['shares'] * tx['price']
        elif tx['type'] == "賣出":
            avg = summary[s]["total_cost"] / summary[s]["total_shares"] if summary[s]["total_shares"] > 0 else 0
            summary[s]["total_shares"] -= tx['shares']
            summary[s]["total_cost"] -= tx['shares'] * avg
    for s in summary:
        summary[s]["avg_price"] = summary[s]["total_cost"] / summary[s]["total_shares"] if summary[s]["total_shares"] > 0 else 0
    return summary

# --- 2. 側邊欄 ---
with st.sidebar:
    st.header("🏛️ 客戶資產中心")
    cur_client = st.selectbox("切換客戶", list(st.session_state.clients.keys()))
    portfolio = calculate_portfolio(st.session_state.clients[cur_client])
    for stock, data in portfolio.items():
        if data['total_shares'] > 0:
            with st.expander(f"📈 {stock}", expanded=True):
                st.write(f"成本: {data['avg_price']:.2f}")
                c1, c2 = st.columns(2)
                if c1.button("買進", key=f"b_{stock}"): st.session_state.pop_tx = {"client": cur_client, "stock": stock, "type": "買入"}
                if c2.button("賣出", key=f"s_{stock}"): st.session_state.pop_tx = {"client": cur_client, "stock": stock, "type": "賣出"}

if 'pop_tx' in st.session_state:
    with st.form("交易紀錄"):
        p = st.number_input("價格"); s = st.number_input("股數"); d = st.date_input("日期")
        if st.form_submit_button("確認"):
            st.session_state.clients[st.session_state.pop_tx['client']].append({"date": str(d), "stock": st.session_state.pop_tx['stock'], "price": p, "shares": s, "type": st.session_state.pop_tx['type']})
            del st.session_state.pop_tx
            st.rerun()

# --- 3. 主圖表 (解決縮放失蹤問題) ---
col_search, col_period = st.columns([1, 2])
with col_search: target_stock = st.text_input("股票查詢", "2330.TW")
with col_period: k_period = st.radio("週期", ["60分", "日線", "周線"], horizontal=True, index=1)

p_map = {"60分": ["60m", "2mo", [5, 35, 200]], "日線": ["1d", "2y", [20, 60, 124, 248]], "周線": ["1wk", "5y", [5, 35, 200]]}
interval, data_range, ma_list = p_map[k_period]

@st.cache_data(ttl=60)
def get_data(symbol, inv, rng):
    df = yf.Ticker(symbol).history(period=rng, interval=inv).dropna()
    if df.empty: return None
    # 計算指標
    e1 = df['Close'].ewm(span=12, adjust=False).mean()
    e2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'], df['Signal'] = e1 - e2, (e1 - e2).ewm(span=9, adjust=False).mean()
    df['Hist'] = df['MACD'] - df['Signal']
    for m in ma_list: df[f'MA{m}'] = df['Close'].rolling(window=m).mean()
    return df

df = get_data(target_stock, interval, data_range)

if df is not None:
    # 固定比例 2:1:1
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.5, 0.25, 0.25])
    
    # K線與均線 (shape='spline' 確保順滑)
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"), row=1, col=1)
    for m in ma_list: fig.add_trace(go.Scatter(x=df.index, y=df[f'MA{m}'], line=dict(width=1.5, shape='spline'), name=f'MA{m}'), row=1, col=1)
    
    # 成交量
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="量"), row=2, col=1)
    
    # MACD
    fig.add_trace(go.Bar(x=df.index, y=df['Hist'], name="MACD柱"), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], line=dict(shape='spline'), name="DIF"), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Signal'], line=dict(shape='spline'), name="DEA"), row=3, col=1)

    # --- 終極優化設定 ---
    fig.update_layout(
        height=800,
        template="plotly_white",
        xaxis_rangeslider_visible=False,
        margin=dict(l=5, r=50, t=5, b=5),
        hovermode='x unified',
        dragmode='pan', # 預設改為平移，防止觸控直接噴走
        uirevision='constant'
    )
    
    # 關鍵：禁止 Y 軸隨兩指縮放，強制自動適配價格
    fig.update_yaxes(side="right", fixedrange=True, autorange=True, row=1, col=1)
    fig.update_yaxes(side="right", fixedrange=True, row=2, col=1)
    fig.update_yaxes(side="right", fixedrange=True, row=3, col=1)
    
    # X 軸允許縮放
    fig.update_xaxes(fixedrange=False)

    st.plotly_chart(fig, use_container_width=True, config={
        'scrollZoom': True,      # 允許兩指/滾輪縮放
        'displayModeBar': False, # 隱藏造成灰色塊的工具列
        'editable': False
    })
else:
    st.error("查無數據")
