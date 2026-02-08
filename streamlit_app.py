import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="專業交易管理系統-自動適配版", layout="wide")

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
        total = st.number_input(f"{name} 總資產", value=float(data["balance"]), key=f"t_{name}")
        cost = st.number_input(f"{name} 成本", value=float(data["cost"]), key=f"c_{name}")
        p = total - cost
        p_pct = (p / cost * 100) if cost != 0 else 0
        st.markdown(f"**損益:** <span style='color:{'#FF0000' if p>=0 else '#00B050'}'>{int(p):,} ({p_pct:.2f}%)</span>", unsafe_allow_html=True)

# --- 2. 數據處理 ---
target_stock = st.text_input("股票代碼", "2330.TW")

@st.cache_data(ttl=60)
def fetch_data(symbol):
    df = yf.Ticker(symbol).history(period="2y", interval="1d")
    # MACD
    e1 = df['Close'].ewm(span=12, adjust=False).mean()
    e2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'], df['Signal'] = e1 - e2, (e1 - e2).ewm(span=9, adjust=False).mean()
    df['Hist'] = df['MACD'] - df['Signal']
    # 均線
    for m in [20, 60, 120, 240]:
        df[f'MA{m}'] = df['Close'].rolling(window=m).mean()
    return df

try:
    df = fetch_data(target_stock)
    c_up, c_down = '#FF0000', '#00B050'

    # --- 3. 繪製圖表 ---
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.015, # 縮小間距更緊湊
                        row_heights=[0.65, 0.15, 0.20])

    # K線：設定 line_width=1 確保極致清晰
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name="K線", increasing_line_color=c_up, decreasing_line_color=c_down,
        increasing_fillcolor=c_up, decreasing_fillcolor=c_down,
        line_width=1.2
    ), row=1, col=1)

    # 均線
    colors = ['#E11D74', '#1F4287', '#FF8C00', '#28B463']
    for i, m in enumerate([20, 60, 120, 240]):
        fig.add_trace(go.Scatter(x=df.index, y=df[f'MA{m}'], name=f'MA{m}',
                                 line=dict(color=colors[i], width=1.5)), row=1, col=1)

    # 成交量 (禁用 Y 軸移動)
    v_colors = [c_up if c >= o else c_down for o, c in zip(df['Open'], df['Close'])]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="成交量", marker_color=v_colors), row=2, col=1)

    # MACD (禁用 Y 軸移動)
    m_colors = [c_up if v >= 0 else c_down for v in df['Hist']]
    fig.add_trace(go.Bar(x=df.index, y=df['Hist'], name="MACD柱", marker_color=m_colors), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], name="DIF", line=dict(color='#0072BD', width=1.2)), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Signal'], name="DEA", line=dict(color='#D95319', width=1.2)), row=3, col=1)

    # --- 4. 關鍵佈局優化 ---
    # 預設看 60 天，級距寬大
    last_60 = df.index[max(0, len(df)-60)]

    fig.update_layout(
        height=720, template="plotly_white", xaxis_rangeslider_visible=False,
        dragmode='pan',
        xaxis=dict(range=[last_60, df.index[-1]], type='date'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=10, r=60, t=50, b=10),
        hovermode='x unified'
    )
    
    # 主圖 Y 軸：自動適配 (關鍵！)
    fig.update_yaxes(
        side="right", 
        autorange=True,     # 當左右滑動時，自動縮放高度
        fixedrange=False,   # 允許系統根據數據調整
        dtick=100 if df['Close'].max() > 1000 else 50, # 每 100 一個級距
        gridcolor='#F0F0F0',
        row=1, col=1
    )

    # 成交量與 MACD Y 軸：嚴禁上下移動
    fig.update_yaxes(fixedrange=True, showgrid=True, gridcolor='#F0F0F0', row=2, col=1)
    fig.update_yaxes(fixedrange=True, showgrid=True, gridcolor='#F0F0F0', row=3, col=1)

    st.plotly_chart(fig, use_container_width=True, config={
        'scrollZoom': True, 
        'displayModeBar': True,
        'displaylogo': False
    })

except Exception as e:
    st.info("數據載入中...")
