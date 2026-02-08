import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="專業交易管理系統-直觀監控版", layout="wide")

# --- 1. 模擬資料庫 (保持左側欄位邏輯不變) ---
if 'clients' not in st.session_state:
    st.session_state.clients = {
        "客戶 A": [{"stock": "2330.TW", "price": 600.0, "shares": 1000}],
        "客戶 B": [{"stock": "2317.TW", "price": 105.0, "shares": 2000}]
    }

# --- 2. 左側欄位：客戶與持股管理 (維持您的好評版) ---
with st.sidebar:
    st.title("🏛️ 客戶管理系統")
    col_add, col_sel = st.columns([1, 2])
    with col_add:
        if st.button("➕ 新客戶"):
            new_name = f"客戶 {chr(65 + len(st.session_state.clients))}"
            st.session_state.clients[new_name] = []
    with col_sel:
        current_client = st.selectbox("切換客戶", list(st.session_state.clients.keys()))

    st.divider()
    st.subheader(f"👤 {current_client} 持股明細")
    holdings = st.session_state.clients[current_client]
    
    total_cost = 0.0
    for i, item in enumerate(holdings):
        with st.expander(f"持股 {i+1}: {item['stock']}", expanded=True):
            c1, c2 = st.columns(2)
            item['stock'] = c1.text_input(f"代碼", item['stock'], key=f"s_{current_client}_{i}")
            item['shares'] = c2.number_input(f"股數", value=int(item['shares']), key=f"sh_{current_client}_{i}")
            item['price'] = st.number_input(f"購入價格", value=float(item['price']), key=f"p_{current_client}_{i}")
            total_cost += item['price'] * item['shares']
    
    if st.button("➕ 添購持股/新增交易"):
        st.session_state.clients[current_client].append({"stock": "2330.TW", "price": 0.0, "shares": 0})
        st.rerun()

    st.metric("該客戶總投入成本", f"{int(total_cost):,}")

# --- 3. 主畫面：週期與數據 ---
col_t, col_p = st.columns([1, 2])
with col_t:
    target_stock = st.text_input("股票查詢", "2330.TW")
with col_p:
    k_period = st.radio("週期調整", ["60分", "日線", "周線"], horizontal=True, index=1)

# 週期參數設定
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
    df['MACD'] = e1 - e2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['Hist'] = df['MACD'] - df['Signal']
    for m in ma_list:
        df[f'MA{m}'] = df['Close'].rolling(window=m).mean()
    return df

try:
    df = fetch_data(target_stock, interval, data_range)
    
    # --- 4. 繪製圖表：大幅壓縮主圖高度，騰出空間 ---
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, 
                        row_heights=[0.45, 0.2, 0.35]) # 重新分配：主圖變扁，成交量與MACD清晰可見

    # K線 (三竹色彩)
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        increasing_line_color='#FF0000', decreasing_line_color='#00AA00',
        increasing_fillcolor='#FF0000', decreasing_fillcolor='#00AA00',
        name="K線"
    ), row=1, col=1)

    # 均線
    ma_colors = ['#E11D74', '#1F4287', '#FF8C00', '#28B463']
    for i, m in enumerate(ma_list):
        fig.add_trace(go.Scatter(x=df.index, y=df[f'MA{m}'], name=f'MA{m}', 
                                 line=dict(width=1.2, color=ma_colors[i%4])), row=1, col=1)

    # 成交量 (與K線漲跌同步)
    v_colors = ['#FF0000' if c >= o else '#00AA00' for o, c in zip(df['Open'], df['Close'])]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=v_colors, name="成交量"), row=2, col=1)

    # MACD (DIF藍, DEA橘, 柱狀紅綠)
    h_colors = ['#FF0000' if v >= 0 else '#00AA00' for v in df['Hist']]
    fig.add_trace(go.Bar(x=df.index, y=df['Hist'], marker_color=h_colors, name="MACD柱"), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], line=dict(color='#0072BD', width=1), name="DIF"), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Signal'], line=dict(color='#D95319', width=1), name="DEA"), row=3, col=1)

    # --- 5. 佈局與垂直壓縮關鍵設定 ---
    start_view = df.index[max(0, len(df)-60)]

    fig.update_layout(
        height=680, # 稍微降低總高度，確保筆電螢幕能一眼看完
        template="plotly_white", xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=60, t=10, b=10),
        hovermode='x unified', dragmode='pan'
    )
    
    # 主圖 Y 軸：極致壓縮
    fig.update_yaxes(
        side="right", 
        dtick=100, 
        gridcolor='#F0F0F0',
        autorange=True,
        autorangeoptions=dict(paddingmin=0.4, paddingmax=0.4), # 強制 K 線縮小並置中
        fixedrange=False,
        row=1, col=1
    )
    
    # 副圖鎖定
    fig.update_yaxes(fixedrange=True, row=2, col=1)
    fig.update_yaxes(fixedrange=True, row=3, col=1)

    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

except Exception as e:
    st.error(f"數據載入失敗，請確認代碼格式: {e}")
