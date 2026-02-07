import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="專業交易管理系統", layout="wide")

# --- 1. 客戶資金設定 ---
if 'clients' not in st.session_state:
    st.session_state.clients = {
        "客戶 A": {"balance": 10000000.0},
        "客戶 B": {"balance": 500000.0},
        "客戶 C": {"balance": 2000000.0}
    }

st.sidebar.title("🏛️ 客戶帳戶管理")
selected_name = st.sidebar.selectbox("切換管理客戶", list(st.session_state.clients.keys()))

# 手動輸入該客戶資產
manual_balance = st.sidebar.number_input(f"輸入 {selected_name} 總資產金額 (TWD)", 
                                        value=float(st.session_state.clients[selected_name]["balance"]),
                                        step=1000.0)
st.session_state.clients[selected_name]["balance"] = manual_balance

# --- 2. 週期與均線參數設定 (嚴格依照您的要求) ---
st.sidebar.divider()
st.sidebar.subheader("📈 技術指標週期")
k_period_label = st.sidebar.radio("切換K線週期", ["60分線", "日線", "周線"], index=1)

# 根據選擇的標籤定義參數
if k_period_label == "60分線":
    ma_list = [5, 35, 200]
    interval = "60m"
    data_range = "2mo" # 60分線取近2個月數據
elif k_period_label == "日線":
    ma_list = [20, 60, 124, 248]
    interval = "1d"
    data_range = "2y" # 日線取2年數據
else: # 周線
    ma_list = [5, 35, 200]
    interval = "1wk"
    data_range = "5y" # 周線取5年數據

# --- 3. 抓取數據 ---
st.title(f"📊 {selected_name} - {k_period_label}監控")
target_stock = st.text_input("輸入股票代碼 (例如: 2330.TW)", "2330.TW")

@st.cache_data(ttl=60)
def fetch_stock_data(symbol, inv, rng):
    return yf.Ticker(symbol).history(period=rng, interval=inv)

try:
    df = fetch_stock_data(target_stock, interval, data_range)
    
    # 計算指定的均線
    for m in ma_list:
        df[f'MA{m}'] = df['Close'].rolling(window=m).mean()

    # --- 4. 繪製 K 線圖 (觸控優化) ---
    fig = go.Figure(data=[go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name="K線", increasing_line_color='#FF4B4B', decreasing_line_color='#00CC96'
    )])

    # 加入指定均線
    colors = ['#FFFFFF', '#F4D03F', '#58D68D', '#5DADE2'] # 白、黃、綠、藍
    for i, m in enumerate(ma_list):
        fig.add_trace(go.Scatter(x=df.index, y=df[f'MA{m}'], 
                                 line=dict(width=1.5, color=colors[i % len(colors)]), 
                                 name=f'MA{m}'))

    # 圖表配置
    fig.update_layout(
        height=700,
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        dragmode='pan', # iPad 上預設為平移，避免單指誤觸放大
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    # 觸控與縮放設定
    config = {
        'scrollZoom': True,  # 支援 iPad 雙指縮放
        'displayModeBar': True,
        'modeBarButtonsToRemove': ['select2d', 'lasso2d'],
        'displaylogo': False
    }

    st.plotly_chart(fig, use_container_width=True, config=config)

except Exception as e:
    st.error(f"數據加載中或發生錯誤: {e}")

# --- 5. 總結與資產顯示 ---
st.divider()
st.subheader("📋 帳戶即時結算")
total_val = st.session_state.clients[selected_name]["balance"]
st.info(f"當前管理客戶：{selected_name} | 設定總資產：NT$ {int(total_val):,}")
