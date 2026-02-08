import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

st.set_page_config(page_title="專業級資產監控-操作優化版", layout="wide")

# --- 1. 資料初始化 ---
if 'zoom_level' not in st.session_state: st.session_state.zoom_level = 50 # 預設顯示 50 根 K 線

# --- 2. 側邊欄資產中心 (維持穩定版邏輯) ---
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

# --- 3. 主圖表控制區 ---
c_search, c_period, c_zoom = st.columns([1, 1, 1])
with c_search: target_stock = st.text_input("股票查詢", "2330.TW")
with c_period: k_period = st.radio("週期", ["60分", "日線", "周線"], horizontal=True, index=1)
with c_zoom:
    st.write("手動縮放控制")
    bz1, bz2, bz3 = st.columns(3)
    if bz1.button("➕ 放大"): st.session_state.zoom_level = max(10, st.session_state.zoom_level - 10)
    if bz2.button("➖ 縮小"): st.session_state.zoom_level = min(200, st.session_state.zoom_level + 10)
    if bz3.button("🏠 還原"): st.session_state.zoom_level = 50

# --- 4. 數據抓取 ---
p_map = {"60分": ["60m", "2mo", [5, 35, 200]], "日線": ["1d", "2y", [20, 60, 124, 248]], "周線": ["1wk", "5y", [5, 35, 200]]}
interval, data_range, ma_list = p_map[k_period]

@st.cache_data(ttl=60)
def get_data(symbol, inv, rng):
    df = yf.Ticker(symbol).history(period=rng, interval=inv).dropna()
    if df.empty: return None
    e1 = df['Close'].ewm(span=12, adjust=False).mean()
    e2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'], df['Signal'] = e1 - e2, (e1 - e2).ewm(span=9, adjust=False).mean()
    df['Hist'] = df['MACD'] - df['Signal']
    for m in ma_list: df[f'MA{m}'] = df['Close'].rolling(window=m).mean()
    return df

df = get_data(target_stock, interval, data_range)

if df is not None:
    # 建立畫布
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.5, 0.25, 0.25])
    
    # 配色邏輯：漲紅跌綠
    colors = ['#FF0000' if c >= o else '#00AA00' for o, c in zip(df['Open'], df['Close'])]

    # 1. K線 (強制紅漲綠跌)
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        increasing_line_color='#FF0000', decreasing_line_color='#00AA00',
        increasing_fillcolor='#FF0000', decreasing_fillcolor='#00AA00', name="K線"
    ), row=1, col=1)

    # 2. 均線 (平滑曲線)
    ma_colors = ['#E11D74', '#1F4287', '#FF8C00', '#28B463']
    for i, m in enumerate(ma_list):
        fig.add_trace(go.Scatter(x=df.index, y=df[f'MA{m}'], line=dict(width=1.5, color=ma_colors[i%4], shape='spline'), name=f'MA{m}'), row=1, col=1)

    # 3. 成交量 (顏色同步)
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, name="量"), row=2, col=1)

    # 4. MACD (配色同步)
    h_colors = ['#FF0000' if v >= 0 else '#00AA00' for v in df['Hist']]
    fig.add_trace(go.Bar(x=df.index, y=df['Hist'], marker_color=h_colors, name="MACD柱"), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], line=dict(color='#0072BD', width=1, shape='spline'), name="DIF"), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Signal'], line=dict(color='#D95319', width=1, shape='spline'), name="DEA"), row=3, col=1)

    # --- 縮放範圍控制 ---
    # 計算最後 N 根 K 線的範圍，實現手動縮放效果
    last_idx = len(df)
    start_idx = max(0, last_idx - st.session_state.zoom_level)
    x_range = [df.index[start_idx], df.index[-1]]

    fig.update_layout(
        height=800,
        template="plotly_white",
        xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=60, t=10, b=10),
        hovermode='x unified',
        dragmode='pan', 
        uirevision=st.session_state.zoom_level # 保持縮放狀態不重置
    )

    fig.update_xaxes(range=x_range, row=3, col=1)
    fig.update_yaxes(side="right", gridcolor='#F5F5F5', autorange=True, fixedrange=True, row=1, col=1)
    fig.update_yaxes(side="right", gridcolor='#F5F5F5', fixedrange=True, row=2, col=1)
    fig.update_yaxes(side="right", gridcolor='#F5F5F5', fixedrange=True, row=3, col=1)

    st.plotly_chart(fig, use_container_width=True, config={
        'scrollZoom': True,
        'displayModeBar': False,
        'doubleClick': 'reset+autosize' # 點兩下重設
    })
else:
    st.error("查無數據")
