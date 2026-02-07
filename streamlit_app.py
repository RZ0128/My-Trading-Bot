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
selected_name = st.sidebar.selectbox("管理客戶", list(st.session_state.clients.keys()))
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
target_stock = st.text_input("股票代碼 (例: 2330.TW)", "2330.TW")

@st.cache_data(ttl=60)
def fetch_classic_data(symbol, inv, rng):
    df = yf.Ticker(symbol).history(period=rng, interval=inv)
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['Hist'] = df['MACD'] - df['Signal']
    for m in ma_list:
        df[f'MA{m}'] = df['Close'].rolling(window=m).mean()
    return df

try:
    df = fetch_classic_data(target_stock, interval, data_range)
    
    # 經典台股配色 (亮紅/亮綠)
    color_up = '#FF0000'   # 正紅
    color_down = '#00B050' # 翠綠

    # --- 4. 繪製圖表 (仿圖 12 佈局) ---
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.01, 
                        row_heights=[0.6, 0.15, 0.25])

    # K線主圖
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name="K線", increasing_line_color=color_up, decreasing_line_color=color_down,
        increasing_fillcolor=color_up, decreasing_fillcolor=color_down
    ), row=1, col=1)

    # 均線配色 (仿圖 12 多彩風格)
    ma_colors = ['#E11D74', '#1F4287', '#FF8C00', '#28B463'] # 桃紅、深藍、亮橘、綠
    for i, m in enumerate(ma_list):
        fig.add_trace(go.Scatter(x=df.index, y=df[f'MA{m}'], name=f'MA{m}',
                                 line=dict(color=ma_colors[i % 4], width=1.5)), row=1, col=1)

    # 成交量 (與 K 線漲跌顏色同步)
    vol_colors = [color_up if c >= o else color_down for o, c in zip(df['Open'], df['Close'])]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="成交量", marker_color=vol_colors), row=2, col=1)

    # MACD (仿圖 12 配色)
    macd_hist_colors = [color_up if val >= 0 else color_down for val in df['Hist']]
    fig.add_trace(go.Bar(x=df.index, y=df['Hist'], name="MACD柱", marker_color=macd_hist_colors), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], name="DIF", line=dict(color='#0072BD', width=1.2)), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Signal'], name="DEA", line=dict(color='#D95319', width=1.2)), row=3, col=1)

    # --- 5. 佈局細節優化 ---
    # 設定初始顯示最後 60 根 K 線，級距超大
    last_60_days = df.index[max(0, len(df)-60)]
    last_day = df.index[-1]

    fig.update_layout(
        height=600,
        template="plotly_white", # 改為白底模式
        xaxis_rangeslider_visible=False,
        dragmode='pan',
        xaxis=dict(range=[last_60_days, last_day]),
        legend=dict(orientation="h", yanchor="top", y=1.08, xanchor="left", x=0, font=dict(size=10)),
        margin=dict(l=10, r=10, t=30, b=10),
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    # 鎖定子圖 y 軸，不讓它們上下晃動
    fig.update_yaxes(fixedrange=False, gridcolor='#EEEEEE', row=1, col=1)
    fig.update_yaxes(fixedrange=True, gridcolor='#EEEEEE', row=2, col=1)
    fig.update_yaxes(fixedrange=True, gridcolor='#EEEEEE', row=3, col=1)

    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': False})

except Exception as e:
    st.error(f"數據讀取中... {e}")

# --- 6. 客戶資產資訊 ---
st.divider()
st.markdown(f"#### 🏛️ 目前帳戶：{selected_name} | 總資產：TWD **{int(st.session_state.clients[selected_name]['balance']):,}**")

