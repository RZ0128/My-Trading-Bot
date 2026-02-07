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
def fetch_high_res_data(symbol, inv, rng):
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
    df = fetch_high_res_data(target_stock, interval, data_range)
    
    # 調校後的紅綠配色 (高對比度)
    color_up = '#FF0000'   
    color_down = '#00B050' 

    # --- 4. 繪製高清圖表 ---
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.01, 
                        row_heights=[0.6, 0.15, 0.25])

    # K線主圖 (銳利化處理)
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name="K線", 
        increasing_line_color=color_up, decreasing_line_color=color_down,
        increasing_fillcolor=color_up, decreasing_fillcolor=color_down,
        increasing_line_width=1,  # 增加邊框寬度提升清晰度
        decreasing_line_width=1,
        whiskerwidth=0.8          # 上下影線加粗
    ), row=1, col=1)

    # 均線配色 (多彩且清晰)
    ma_colors = ['#E11D74', '#1F4287', '#FF8C00', '#28B463'] 
    for i, m in enumerate(ma_list):
        fig.add_trace(go.Scatter(x=df.index, y=df[f'MA{m}'], name=f'MA{m}',
                                 line=dict(color=ma_colors[i % 4], width=1.8), # 增加寬度
                                 mode='lines'), row=1, col=1)

    # 成交量
    vol_colors = [color_up if c >= o else color_down for o, c in zip(df['Open'], df['Close'])]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="成交量", marker_color=vol_colors), row=2, col=1)

    # MACD
    macd_hist_colors = [color_up if val >= 0 else color_down for val in df['Hist']]
    fig.add_trace(go.Bar(x=df.index, y=df['Hist'], name="MACD柱", marker_color=macd_hist_colors), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], name="DIF", line=dict(color='#0072BD', width=1.5)), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Signal'], name="DEA", line=dict(color='#D95319', width=1.5)), row=3, col=1)

    # --- 5. 佈局細節與畫質設定 ---
    # 設定初始顯示最後 55 根 K 線，級距適中且清晰
    last_idx = df.index[max(0, len(df)-55)]
    now_idx = df.index[-1]

    fig.update_layout(
        height=620,
        template="plotly_white",
        xaxis_rangeslider_visible=False,
        dragmode='pan',
        xaxis=dict(range=[last_idx, now_idx], linecolor='#333333', linewidth=1),
        legend=dict(orientation="h", yanchor="top", y=1.08, xanchor="left", x=0, font=dict(size=11, color="#333333")),
        margin=dict(l=10, r=10, t=30, b=10),
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    # 網格線設定 (淡化，突出主圖)
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#F2F2F2')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#F2F2F2', row=1, col=1)
    fig.update_yaxes(fixedrange=True, row=2, col=1)
    fig.update_yaxes(fixedrange=True, row=3, col=1)

    # 針對 WebGL 渲染的高清輸出配置
    st.plotly_chart(fig, use_container_width=True, config={
        'scrollZoom': True, 
        'displayModeBar': False,
        'staticPlot': False,
        'responsive': True,
        'toImageButtonOptions': {'format': 'png', 'scale': 2} # 輸出畫質翻倍
    })

except Exception as e:
    st.error(f"正在載入數據中...")

# --- 6. 客戶資產資訊 ---
st.divider()
st.markdown(f"#### 🏦 客戶：{selected_name} | 總資產：TWD **{int(st.session_state.clients[selected_name]['balance']):,}**")
