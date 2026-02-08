import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="專業交易管理系統-極限壓縮版", layout="wide")

# --- 1. 左側欄位：獨立客戶資產 ---
st.sidebar.title("🏛️ 客戶帳戶監控")
if 'client_data' not in st.session_state:
    st.session_state.client_data = {
        "客戶 A": {"balance": 10000000, "cost": 8500000},
        "客戶 B": {"balance": 500000, "cost": 450000},
        "客戶 C": {"balance": 2000000, "cost": 2100000}
    }

for name, data in st.session_state.client_data.items():
    with st.sidebar.expander(f"👤 {name} 詳情", expanded=True):
        t = st.number_input(f"{name} 總資產", value=float(data["balance"]), key=f"t_{name}")
        c = st.number_input(f"{name} 成本", value=float(data["cost"]), key=f"c_{name}")
        p = t - c
        p_pct = (p / c * 100) if c != 0 else 0
        st.markdown(f"**損益:** <span style='color:{'#FF0000' if p>=0 else '#00B050'}'>{int(p):,} ({p_pct:.2f}%)</span>", unsafe_allow_html=True)

# --- 2. 週期切換與數據抓取 ---
col1, col2 = st.columns([1, 2])
with col1:
    target_stock = st.text_input("股票代碼", "2330.TW")
with col2:
    # 確保週期切換按鈕永遠存在
    k_period = st.radio("週期切換", ["60分", "日線", "周線"], horizontal=True, index=1)

if k_period == "60分":
    ma_list, interval, data_range = [5, 35, 200], "60m", "2mo"
elif k_period == "日線":
    ma_list, interval, data_range = [20, 60, 124, 248], "1d", "2y"
else:
    ma_list, interval, data_range = [5, 35, 200], "1wk", "5y"

@st.cache_data(ttl=60)
def fetch_data(symbol, inv, rng):
    df = yf.Ticker(symbol).history(period=rng, interval=inv)
    e1 = df['Close'].ewm(span=12, adjust=False).mean()
    e2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'], df['Signal'] = e1 - e2, (e1 - e2).ewm(span=9, adjust=False).mean()
    df['Hist'] = df['MACD'] - df['Signal']
    for m in ma_list:
        df[f'MA{m}'] = df['Close'].rolling(window=m).mean()
    return df

try:
    df = fetch_data(target_stock, interval, data_range)
    c_up, c_down = '#FF0000', '#00B050'

    # --- 3. 繪製圖表 ---
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.01, 
                        row_heights=[0.75, 0.1, 0.15]) # 進一步壓縮副圖空間

    # K線
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name="K線", increasing_line_color=c_up, decreasing_line_color=c_down,
        increasing_fillcolor=c_up, decreasing_fillcolor=c_down,
        line_width=1.5
    ), row=1, col=1)

    # 均線
    ma_colors = ['#E11D74', '#1F4287', '#FF8C00', '#28B463']
    for i, m in enumerate(ma_list):
        fig.add_trace(go.Scatter(x=df.index, y=df[f'MA{m}'], name=f'MA{m}',
                                 line=dict(color=ma_colors[i % 4], width=1.2)), row=1, col=1)

    # 副圖
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="成交量", marker_color='#D3D3D3'), row=2, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df['Hist'], name="MACD柱", marker_color='#E5E5E5'), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], name="DIF", line=dict(color='#0072BD', width=1)), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Signal'], name="DEA", line=dict(color='#D95319', width=1)), row=3, col=1)

    # --- 4. 關鍵 Y 軸極限壓縮邏輯 ---
    fig.update_layout(
        height=800, template="plotly_white", xaxis_rangeslider_visible=False,
        dragmode='pan',
        margin=dict(l=10, r=60, t=20, b=10),
        hovermode='x unified',
        # 禁用 Y 軸的自由縮放，強制由程式邏輯控制比例
        yaxis_fixedrange=False 
    )

    # 主圖 Y 軸：核心修復就在這裡
    fig.update_yaxes(
        side="right", 
        autorange=True,
        # 移除過大的 Padding，讓 K 線佔滿空間
        autorangeoptions=dict(clipmin=0, clipmax=0, minallowed=df['Low'].min()*0.9, maxallowed=df['High'].max()*1.1),
        dtick=100, # 維持 100 級距
        gridcolor='#F0F0F0',
        tickfont=dict(size=11),
        # 這一行是解決您「間距太遠」的關鍵：設定縮放比例限制
        scaleanchor="x", scaleratio=0.01, # 數值越小，Y 軸被壓得越扁
        constrain="domain",
        row=1, col=1
    )

    # 副圖鎖定
    fig.update_yaxes(fixedrange=True, row=2, col=1)
    fig.update_yaxes(fixedrange=True, row=3, col=1)

    st.plotly_chart(fig, use_container_width=True, config={
        'scrollZoom': True, 
        'displayModeBar': True,
        'displaylogo': False
    })

except Exception as e:
    st.info("數據載入中...")
