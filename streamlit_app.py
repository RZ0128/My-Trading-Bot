import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

st.set_page_config(page_title="專業交易管理系統-三竹版", layout="wide")

# --- 1. 左側欄位優化：獨立客戶資產管理 ---
st.sidebar.title("🏛️ 客戶帳戶即時監控")

# 初始化客戶數據 (若無則設定預設值)
if 'client_data' not in st.session_state:
    st.session_state.client_data = {
        "客戶 A": {"balance": 10000000, "cost": 8500000},
        "客戶 B": {"balance": 500000, "cost": 450000},
        "客戶 C": {"balance": 2000000, "cost": 2100000}
    }

# 獨立安排每個客戶的欄位 (直觀顯示)
for name, data in st.session_state.client_data.items():
    with st.sidebar.expander(f"👤 {name} 帳戶詳情", expanded=True):
        total = st.number_input(f"{name} 總資產", value=float(data["balance"]), key=f"total_{name}")
        cost = st.number_input(f"{name} 持股成本", value=float(data["cost"]), key=f"cost_{name}")
        
        # 即時計算
        profit = total - cost
        profit_pct = (profit / cost * 100) if cost != 0 else 0
        color = "red" if profit >= 0 else "green"
        
        st.markdown(f"**目前損益:** <span style='color:{color}'>{int(profit):,} ({profit_pct:.2f}%)</span>", unsafe_allow_html=True)
        st.markdown(f"**銀行餘額:** {int(total):,}")
        st.session_state.client_data[name]["balance"] = total
        st.session_state.client_data[name]["cost"] = cost

# --- 2. 週期與均線參數 ---
st.sidebar.divider()
k_period_label = st.sidebar.radio("圖表週期", ["60分線", "日線", "周線"], index=1)
if k_period_label == "60分線":
    ma_list, interval, data_range = [5, 35, 200], "60m", "2mo"
elif k_period_label == "日線":
    ma_list, interval, data_range = [20, 60, 124, 248], "1d", "2y"
else:
    ma_list, interval, data_range = [5, 35, 200], "1wk", "5y"

# --- 3. 數據抓取 ---
target_stock = st.text_input("輸入股票代碼", "2330.TW")

@st.cache_data(ttl=60)
def fetch_pro_data(symbol, inv, rng):
    df = yf.Ticker(symbol).history(period=rng, interval=inv)
    # MACD
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['Hist'] = df['MACD'] - df['Signal']
    # MA
    for m in ma_list:
        df[f'MA{m}'] = df['Close'].rolling(window=m).mean()
    return df

try:
    df = fetch_pro_data(target_stock, interval, data_range)
    
    # 經典紅綠配
    c_up, c_down = '#FF0000', '#00B050'

    # --- 4. 繪製三連圖 ---
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.01, 
                        row_heights=[0.6, 0.15, 0.25])

    # K線：增加 line_width 讓根根分明
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name="K線", increasing_line_color=c_up, decreasing_line_color=c_down,
        increasing_fillcolor=c_up, decreasing_fillcolor=c_down,
        increasing_line_width=1.5, decreasing_line_width=1.5
    ), row=1, col=1)

    # 均線
    ma_colors = ['#E11D74', '#1F4287', '#FF8C00', '#28B463']
    for i, m in enumerate(ma_list):
        fig.add_trace(go.Scatter(x=df.index, y=df[f'MA{m}'], name=f'MA{m}',
                                 line=dict(color=ma_colors[i % 4], width=1.5)), row=1, col=1)

    # 成交量
    vol_colors = [c_up if c >= o else c_down for o, c in zip(df['Open'], df['Close'])]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="成交量", marker_color=vol_colors), row=2, col=1)

    # MACD
    m_colors = [c_up if v >= 0 else c_down for v in df['Hist']]
    fig.add_trace(go.Bar(x=df.index, y=df['Hist'], name="MACD柱", marker_color=m_colors), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], name="DIF", line=dict(color='#0072BD', width=1.2)), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Signal'], name="DEA", line=dict(color='#D95319', width=1.2)), row=3, col=1)

    # --- 5. 初始級距優化：只顯示四周 (約 20 根) ---
    total_points = len(df)
    start_view = df.index[max(0, total_points - 20)] # 一開始只顯示 20 根
    end_view = df.index[-1]

    fig.update_layout(
        height=650, template="plotly_white", xaxis_rangeslider_visible=False,
        dragmode='pan',
        xaxis=dict(range=[start_view, end_view], type='date', dtick="D1"), # D1 確保間距寬大
        legend=dict(orientation="h", yanchor="top", y=1.08, xanchor="left", x=0),
        margin=dict(l=10, r=50, t=30, b=10),
        yaxis=dict(side="right") # 仿效三竹將價格放在右邊
    )
    
    # 鎖定子圖 Y 軸
    fig.update_yaxes(fixedrange=True, row=2, col=1)
    fig.update_yaxes(fixedrange=True, row=3, col=1)

    # 恢復功能按鈕 (displayModeBar=True)
    st.plotly_chart(fig, use_container_width=True, config={
        'scrollZoom': True, 
        'displayModeBar': True, # 按鈕回歸
        'displaylogo': False,
        'modeBarButtonsToRemove': ['lasso2d', 'select2d']
    })

except Exception as e:
    st.info("請輸入正確的股票代碼以顯示圖表")

