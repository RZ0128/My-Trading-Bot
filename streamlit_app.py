import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

st.set_page_config(page_title="專業級客戶資產監控系統", layout="wide")

# --- 1. 核心資料庫結構 (Session State) ---
if 'clients' not in st.session_state:
    st.session_state.clients = {
        "客戶 A": [
            {"date": "2024-01-01", "stock": "2330.TW", "price": 600.0, "shares": 1000, "type": "買入"},
            {"date": "2024-02-01", "stock": "2330.TW", "price": 650.0, "shares": 500, "type": "買入"}
        ]
    }

# --- 2. 資產計算邏輯函數 ---
def calculate_portfolio(transactions):
    summary = {}
    for tx in transactions:
        s = tx['stock']
        if s not in summary:
            summary[s] = {"total_shares": 0, "total_cost": 0.0}
        
        if tx['type'] == "買入":
            summary[s]["total_shares"] += tx['shares']
            summary[s]["total_cost"] += tx['shares'] * tx['price']
        elif tx['type'] == "賣出":
            # 賣出時按平均成本扣除 (會計移動平均法)
            avg_cost = summary[s]["total_cost"] / summary[s]["total_shares"] if summary[s]["total_shares"] > 0 else 0
            summary[s]["total_shares"] -= tx['shares']
            summary[s]["total_cost"] -= tx['shares'] * avg_cost
            
    # 計算平均單價
    for s in summary:
        if summary[s]["total_shares"] > 0:
            summary[s]["avg_price"] = summary[s]["total_cost"] / summary[s]["total_shares"]
        else:
            summary[s]["avg_price"] = 0
    return summary

# --- 3. 左側：資產管理介面 ---
with st.sidebar:
    st.header("🏛️ 客戶資產中心")
    col_add, col_sel = st.columns([1, 2])
    with col_add:
        if st.button("➕ 新客戶"):
            name = f"客戶 {chr(65 + len(st.session_state.clients))}"
            st.session_state.clients[name] = []
    with col_sel:
        cur_client = st.selectbox("切換客戶", list(st.session_state.clients.keys()))

    st.divider()
    
    # 顯示該客戶目前的持股總覽
    portfolio = calculate_portfolio(st.session_state.clients[cur_client])
    st.subheader(f"👤 {cur_client} 持股明細")
    
    for stock, data in portfolio.items():
        if data['total_shares'] > 0:
            with st.expander(f"📈 {stock} (餘 {data['total_shares']} 股)", expanded=True):
                # 獲取現價計算損益
                try:
                    current_p = yf.Ticker(stock).history(period="1d")['Close'].iloc[-1]
                except:
                    current_p = data['avg_price']
                
                pnl = (current_p - data['avg_price']) * data['total_shares']
                pnl_pct = ((current_p / data['avg_price']) - 1) * 100 if data['avg_price'] != 0 else 0
                
                st.write(f"平均成本: **{data['avg_price']:.2f}**")
                st.write(f"當前價格: **{current_p:.2f}**")
                color = "red" if pnl >= 0 else "green"
                st.markdown(f"損益: <span style='color:{color}'>{int(pnl):,} ({pnl_pct:.2f}%)</span>", unsafe_allow_html=True)
                
                # 買賣按鈕區域
                b1, b2 = st.columns(2)
                if b1.button(f"買進", key=f"buy_{stock}"):
                    st.session_state.target_tx = {"client": cur_client, "stock": stock, "type": "買入"}
                if b2.button(f"賣出", key=f"sell_{stock}"):
                    st.session_state.target_tx = {"client": cur_client, "stock": stock, "type": "賣出"}

    st.divider()
    if st.button("➕ 新增股票交易"):
        st.session_state.clients[cur_client].append({"date": str(datetime.now().date()), "stock": "2330.TW", "price": 0.0, "shares": 0, "type": "買入"})
        st.rerun()

# --- 4. 主畫面：交易輸入視窗 (如果有按下按鈕) ---
if 'target_tx' in st.session_state:
    with st.container(border=True):
        st.info(f"正在紀錄: {st.session_state.target_tx['client']} - {st.session_state.target_tx['type']} {st.session_state.target_tx['stock']}")
        c1, c2, c3 = st.columns(3)
        t_date = c1.date_input("交易日期")
        t_price = c2.number_input("成交單價", step=0.1)
        t_shares = c3.number_input("成交股數", step=100)
        if st.button("確認提交交易"):
            new_tx = {
                "date": str(t_date),
                "stock": st.session_state.target_tx['stock'],
                "price": t_price,
                "shares": t_shares,
                "type": st.session_state.target_tx['type']
            }
            st.session_state.clients[st.session_state.target_tx['client']].append(new_tx)
            del st.session_state.target_tx
            st.rerun()

# --- 5. 主畫面：專業 K 線圖 (2:1:1 比例 + 平滑曲線) ---
col_search, col_period = st.columns([1, 2])
with col_search:
    target_stock = st.text_input("股票代碼查詢", "2330.TW")
with col_period:
    k_period = st.radio("週期切換", ["60分", "日線", "周線"], horizontal=True, index=1)

if k_period == "60分":
    ma_list, interval, data_range = [5, 35, 200], "60m", "2mo"
elif k_period == "日線":
    ma_list, interval, data_range = [20, 60, 124, 248], "1d", "2y"
else:
    ma_list, interval, data_range = [5, 35, 200], "1wk", "5y"

@st.cache_data(ttl=60)
def get_smooth_data(symbol, inv, rng):
    df = yf.Ticker(symbol).history(period=rng, interval=inv)
    e1 = df['Close'].ewm(span=12, adjust=False).mean()
    e2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'], df['Signal'] = e1 - e2, (e1 - e2).ewm(span=9, adjust=False).mean()
    df['Hist'] = df['MACD'] - df['Signal']
    for m in ma_list:
        df[f'MA{m}'] = df['Close'].rolling(window=m).mean()
    return df

try:
    df = get_smooth_data(target_stock, interval, data_range)
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.04, 
                        row_heights=[0.5, 0.25, 0.25])

    # K線
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        increasing_line_color='#FF0000', decreasing_line_color='#00AA00',
        increasing_fillcolor='#FF0000', decreasing_fillcolor='#00AA00', name="K線"
    ), row=1, col=1)

    # 均線 - 使用 Spline 平滑
    ma_colors = ['#E11D74', '#1F4287', '#FF8C00', '#28B463']
    for i, m in enumerate(ma_list):
        fig.add_trace(go.Scatter(x=df.index, y=df[f'MA{m}'], name=f'MA{m}', 
                                 line=dict(width=1.5, color=ma_colors[i%4], shape='spline')), row=1, col=1)

    # 成交量
    v_colors = ['#FF0000' if c >= o else '#00AA00' for o, c in zip(df['Open'], df['Close'])]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=v_colors, name="成交量"), row=2, col=1)

    # MACD - 使用 Spline 平滑
    h_colors = ['#FF0000' if v >= 0 else '#00AA00' for v in df['Hist']]
    fig.add_trace(go.Bar(x=df.index, y=df['Hist'], marker_color=h_colors, name="MACD柱"), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], line=dict(color='#0072BD', width=1.2, shape='spline'), name="DIF"), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Signal'], line=dict(color='#D95319', width=1.2, shape='spline'), name="DEA"), row=3, col=1)

    fig.update_layout(height=780, template="plotly_white", xaxis_rangeslider_visible=False,
                      margin=dict(l=10, r=60, t=10, b=10), hovermode='x unified', dragmode='pan')
    fig.update_yaxes(side="right", dtick=100, gridcolor='#F0F0F0', autorangeoptions=dict(paddingmin=0.2, paddingmax=0.2), row=1, col=1)
    fig.update_yaxes(side="right", fixedrange=True, row=2, col=1)
    fig.update_yaxes(side="right", fixedrange=True, row=3, col=1)

    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

except Exception as e:
    st.error(f"數據讀取中...")

