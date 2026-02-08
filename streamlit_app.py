import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="專業交易管理系統-高清版", layout="wide")

# --- 1. 左側欄位：獨立客戶資產與損益計算 ---
st.sidebar.title("🏛️ 客戶帳戶即時監控")

if 'client_data' not in st.session_state:
    st.session_state.client_data = {
        "客戶 A": {"balance": 10000000, "cost": 8500000},
        "客戶 B": {"balance": 500000, "cost": 450000},
        "客戶 C": {"balance": 2000000, "cost": 2100000}
    }

for name, data in st.session_state.client_data.items():
    with st.sidebar.expander(f"👤 {name} 帳戶詳情", expanded=True):
        total = st.number_input(f"{name} 總資產", value=float(data["balance"]), key=f"t_{name}")
        cost = st.number_input(f"{name} 持股成本", value=float(data["cost"]), key=f"c_{name}")
        profit = total - cost
        p_pct = (profit / cost * 100) if cost != 0 else 0
        p_color = "#FF0000" if profit >= 0 else "#00B050"
        st.markdown(f"**損益:** <span style='color:{p_color}'>{int(profit):,} ({p_pct:.2f}%)</span>", unsafe_allow_html=True)
        st.markdown(f"**餘額:** {int(total):,}")

# --- 2. 數據抓取 ---
st.sidebar.divider()
target_stock = st.text_input("輸入股票代碼", "2330.TW")

@st.cache_data(ttl=60)
def fetch_pro_data(symbol):
    # 預設抓取 2 年，方便縮放看長期
    df = yf.Ticker(symbol).history(period="2y", interval="1d")
    # MACD 計算
    e1 = df['Close'].ewm(span=12, adjust=False).mean()
    e2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = e1 - e2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['Hist'] = df['MACD'] - df['Signal']
    # 均線
    for m in [20, 60, 120, 240]:
        df[f'MA{m}'] = df['Close'].rolling(window=m).mean()
    return df

try:
    df = fetch_pro_data(target_stock)
    c_up, c_down = '#FF0000', '#00B050'

    # --- 3. 繪製高清連動圖表 ---
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.02, 
                        row_heights=[0.6, 0.15, 0.25])

    # K線：重點在於 line_width 和 whiskerwidth 的微調
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name="K線", increasing_line_color=c_up, decreasing_line_color=c_down,
        increasing_fillcolor=c_up, decreasing_fillcolor=c_down,
        line_width=1.2,  # 確保半年尺度依然界線分明
        whiskerwidth=0.3
    ), row=1, col=1)

    # 均線
    colors = ['#E11D74', '#1F4287', '#FF8C00', '#28B463']
    for i, m in enumerate([20, 60, 120, 240]):
        fig.add_trace(go.Scatter(x=df.index, y=df[f'MA{m}'], name=f'MA{m}',
                                 line=dict(color=colors[i], width=1.5)), row=1, col=1)

    # 成交量
    v_colors = [c_up if c >= o else c_down for o, c in zip(df['Open'], df['Close'])]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="成交量", marker_color=v_colors, marker_line_width=0), row=2, col=1)

    # MACD
    m_colors = [c_up if v >= 0 else c_down for v in df['Hist']]
    fig.add_trace(go.Bar(x=df.index, y=df['Hist'], name="MACD柱", marker_color=m_colors), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], name="DIF", line=dict(color='#0072BD', width=1.2)), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Signal'], name="DEA", line=dict(color='#D95319', width=1.2)), row=3, col=1)

    # --- 4. 佈局設定 (仿市面專業模板) ---
    # 預設顯示 6 個月 (約 120 根)
    start_view = df.index[max(0, len(df)-120)]
    end_view = df.index[-1]

    fig.update_layout(
        height=700, template="plotly_white", 
        xaxis_rangeslider_visible=False,
        dragmode='pan',
        # 同步縮放核心設定
        xaxis=dict(range=[start_view, end_view], type='date', showspikes=True, spikemode='across'),
        yaxis=dict(side="right", nticks=15, gridcolor='#F0F0F0', zeroline=False), # 價格在右
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=10, r=50, t=50, b=10),
        hovermode='x unified'
    )
    
    # 子圖格線同步與連動
    fig.update_yaxes(gridcolor='#F0F0F0', row=2, col=1)
    fig.update_yaxes(gridcolor='#F0F0F0', row=3, col=1)

    # 確保右上角按鈕顯示
    st.plotly_chart(fig, use_container_width=True, config={
        'scrollZoom': True, 
        'displayModeBar': True,
        'displaylogo': False,
        'modeBarButtonsToAdd': ['drawline', 'drawcircle', 'eraseshape'] # 增加畫線功能
    })

except Exception as e:
    st.info("請輸入正確股票代碼（如 2330.TW）載入高清圖表")
