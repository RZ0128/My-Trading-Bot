import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="專業交易管理系統-極致壓縮版", layout="wide")

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
    e1 = df['Close'].ewm(span=12, adjust=False).mean()
    e2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'], df['Signal'] = e1 - e2, (e1 - e2).ewm(span=9, adjust=False).mean()
    df['Hist'] = df['MACD'] - df['Signal']
    for m in [20, 60, 124, 248]:
        df[f'MA{m}'] = df['Close'].rolling(window=m).mean()
    return df

try:
    df = fetch_data(target_stock)
    c_up, c_down = '#FF0000', '#00B050'

    # --- 3. 繪製圖表 ---
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.01, 
                        row_heights=[0.7, 0.12, 0.18]) # 稍微拉高主圖比例

    # K線
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name="K線", increasing_line_color=c_up, decreasing_line_color=c_down,
        increasing_fillcolor=c_up, decreasing_fillcolor=c_down,
        line_width=1.3
    ), row=1, col=1)

    # 均線
    colors = ['#E11D74', '#1F4287', '#FF8C00', '#28B463']
    for i, m in enumerate([20, 60, 124, 248]):
        fig.add_trace(go.Scatter(x=df.index, y=df[f'MA{m}'], name=f'MA{m}',
                                 line=dict(color=colors[i], width=1.5)), row=1, col=1)

    # 副圖：成交量與 MACD
    vol_colors = [c_up if c >= o else c_down for o, c in zip(df['Open'], df['Close'])]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="成交量", marker_color=vol_colors), row=2, col=1)
    
    m_colors = [c_up if v >= 0 else c_down for v in df['Hist']]
    fig.add_trace(go.Bar(x=df.index, y=df['Hist'], name="MACD柱", marker_color=m_colors), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], name="DIF", line=dict(color='#0072BD', width=1.2)), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Signal'], name="DEA", line=dict(color='#D95319', width=1.2)), row=3, col=1)

    # --- 4. 佈局細節：垂直壓縮優化 ---
    last_60 = df.index[max(0, len(df)-60)]
    
    # 計算當前畫面的價格範圍以優化初次載入的壓縮感
    visible_df = df.iloc[-60:]
    y_min, y_max = visible_df['Low'].min(), visible_df['High'].max()
    y_range_padding = (y_max - y_min) * 0.15 # 增加留白但不撐開間距

    fig.update_layout(
        height=750, template="plotly_white", xaxis_rangeslider_visible=False,
        dragmode='pan',
        xaxis=dict(range=[last_60, df.index[-1]], type='date'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=10, r=60, t=50, b=10),
        hovermode='x unified'
    )
    
    # 主圖 Y 軸：垂直壓縮設定
    fig.update_yaxes(
        side="right", 
        autorange=True, 
        fixedrange=False,
        # 關鍵設定：透過 dtick 控制 100 級距，並縮減其視覺高度
        dtick=100,
        gridcolor='#F2F2F2',
        zeroline=False,
        row=1, col=1
    )

    # 副圖 Y 軸：嚴禁垂直移動與縮放
    fig.update_yaxes(fixedrange=True, showgrid=True, gridcolor='#F5F5F5', row=2, col=1)
    fig.update_yaxes(fixedrange=True, showgrid=True, gridcolor='#F5F5F5', row=3, col=1)

    st.plotly_chart(fig, use_container_width=True, config={
        'scrollZoom': True, 
        'displayModeBar': True,
        'displaylogo': False
    })

except Exception as e:
    st.info("正在連線至市場數據源...")
