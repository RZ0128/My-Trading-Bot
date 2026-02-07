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
manual_balance = st.sidebar.number_input(f"設定 {selected_name} 總資產", value=float(st.session_state.clients[selected_name]["balance"]))
st.session_state.clients[selected_name]["balance"] = manual_balance

# --- 2. 週期與均線定義 ---
st.sidebar.divider()
k_period_label = st.sidebar.radio("週期", ["60分線", "日線", "周線"], index=1)

if k_period_label == "60分線":
    ma_list, interval, data_range = [5, 35, 200], "60m", "2mo"
elif k_period_label == "日線":
    ma_list, interval, data_range = [20, 60, 124, 248], "1d", "2y"
else:
    ma_list, interval, data_range = [5, 35, 200], "1wk", "5y"

# --- 3. 數據計算 ---
target_stock = st.text_input("股票代碼", "2330.TW")

@st.cache_data(ttl=60)
def fetch_and_calc(symbol, inv, rng):
    df = yf.Ticker(symbol).history(period=rng, interval=inv)
    # MACD 計算
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['Hist'] = df['MACD'] - df['Signal']
    # 均線計算
    for m in ma_list:
        df[f'MA{m}'] = df['Close'].rolling(window=m).mean()
    return df

try:
    df = fetch_and_calc(target_stock, interval, data_range)
    
    # 定義紅綠配色 (深色系)
    color_up = '#B22222' # 深紅
    color_down = '#228B22' # 森林綠

    # --- 4. 繪製多圖層 ---
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, 
                        row_heights=[0.5, 0.15, 0.25])

    # K線主圖
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name="K線", increasing_line_color=color_up, decreasing_line_color=color_down,
        increasing_fillcolor=color_up, decreasing_fillcolor=color_down
    ), row=1, col=1)

    # 護眼均線配色 (莫蘭迪色)
    ma_colors = ['#8DA0CB', '#E78AC3', '#A6D854', '#FC8D62']
    for i, m in enumerate(ma_list):
        fig.add_trace(go.Scatter(x=df.index, y=df[f'MA{m}'], name=f'MA{m}',
                                 line=dict(color=ma_colors[i], width=1.5)), row=1, col=1)

    # 成交量 (收盤 > 開盤 為紅)
    vol_colors = [color_up if close >= open else color_down for open, close in zip(df['Open'], df['Close'])]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="成交量", marker_color=vol_colors), row=2, col=1)

    # MACD (0以上為紅，0以下為綠)
    macd_colors = [color_up if val >= 0 else color_down for val in df['Hist']]
    fig.add_trace(go.Bar(x=df.index, y=df['Hist'], name="MACD柱狀", marker_color=macd_colors), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], name="DIF", line=dict(color='#88CCEE', width=1.2)), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Signal'], name="DEA", line=dict(color='#FFCC99', width=1.2)), row=3, col=1)

    # --- 5. 圖表佈局 ---
    fig.update_layout(
        height=580,
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        dragmode='pan',
        legend=dict(orientation="h", yanchor="top", y=1.1, xanchor="left", x=0, font=dict(size=10)),
        margin=dict(l=10, r=10, t=40, b=10)
    )
    
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': True})

except Exception as e:
    st.error(f"資訊更新中... {e}")

# --- 6. 資產顯示 ---
st.divider()
st.info(f"當前帳戶：{selected_name} | 總資產設定：NT$ {int(st.session_state.clients[selected_name]['balance']):,}")
