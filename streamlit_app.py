import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="專業交易管理系統", layout="wide")

# --- 1. 客戶資金設定 ---
if 'clients' not in st.session_state:
    st.session_state.clients = {
        "客戶 A": {"balance": 10000000.0}, "客戶 B": {"balance": 500000.0}, "客戶 C": {"balance": 2000000.0}
    }

st.sidebar.title("🏛️ 客戶帳戶管理")
selected_name = st.sidebar.selectbox("切換管理客戶", list(st.session_state.clients.keys()))
manual_balance = st.sidebar.number_input(f"輸入 {selected_name} 總資產金額 (TWD)", 
                                        value=float(st.session_state.clients[selected_name]["balance"]))
st.session_state.clients[selected_name]["balance"] = manual_balance

# --- 2. 週期與均線定義 ---
st.sidebar.divider()
k_period_label = st.sidebar.radio("切換K線週期", ["60分線", "日線", "周線"], index=1)

if k_period_label == "60分線":
    ma_list, interval, data_range = [5, 35, 200], "60m", "2mo"
elif k_period_label == "日線":
    ma_list, interval, data_range = [20, 60, 124, 248], "1d", "2y"
else:
    ma_list, interval, data_range = [5, 35, 200], "1wk", "5y"

# --- 3. 抓取與計算數據 ---
target_stock = st.text_input("輸入股票代碼 (例如: 2330.TW)", "2330.TW")

@st.cache_data(ttl=60)
def fetch_full_data(symbol, inv, rng):
    df = yf.Ticker(symbol).history(period=rng, interval=inv)
    # 計算 MACD
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['Hist'] = df['MACD'] - df['Signal']
    # 計算 均線
    for m in ma_list:
        df[f'MA{m}'] = df['Close'].rolling(window=m).mean()
    return df

try:
    df = fetch_full_data(target_stock, interval, data_range)

    # --- 4. 建立多圖表 (K線 + 成交量 + MACD) ---
    # row_heights 設定為 [0.5, 0.2, 0.3]，顯著縮減主要 K 線高度
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.05, 
                        row_heights=[0.5, 0.15, 0.25])

    # K線主圖
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                                 name="K線", increasing_line_color='#FF3333', decreasing_line_color='#00FF99'), row=1, col=1)

    # 均線 (使用高對比配色：亮黃、粉紅、青藍、亮橘)
    ma_colors = ['#FFFF00', '#FF00FF', '#00FFFF', '#FF9900']
    for i, m in enumerate(ma_list):
        fig.add_trace(go.Scatter(x=df.index, y=df[f'MA{m}'], name=f'MA{m}',
                                 line=dict(color=ma_colors[i], width=1.5)), row=1, col=1)

    # 成交量
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="成交量", marker_color='#444444'), row=2, col=1)

    # MACD
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], name="MACD", line=dict(color='#00CCFF', width=1)), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Signal'], name="Signal", line=dict(color='#FFA500', width=1)), row=3, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df['Hist'], name="柱狀圖", marker_color='#888888'), row=3, col=1)

    # --- 5. 圖表佈局優化 ---
    fig.update_layout(
        height=550, # 總高度大幅減半
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        dragmode='pan',
        # 將圖例(Legend)移至左上方，避開右上角功能鈕
        legend=dict(orientation="h", yanchor="top", y=1.12, xanchor="left", x=0),
        margin=dict(l=10, r=10, t=50, b=10)
    )
    
    config = {'scrollZoom': True, 'displayModeBar': True, 'displaylogo': False}
    st.plotly_chart(fig, use_container_width=True, config=config)

except Exception as e:
    st.error(f"讀取失敗: {e}")

# --- 6. 資產清單 ---
st.subheader(f"📋 {selected_name} 結算資訊")
st.info(f"設定資產：NT$ {int(st.session_state.clients[selected_name]['balance']):,}")
