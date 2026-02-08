import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

st.set_page_config(page_title="專業級客戶資產監控系統-穩定版", layout="wide")

# --- 1. 資料初始化 ---
if 'clients' not in st.session_state:
    st.session_state.clients = {
        "客戶 A": [
            {"date": "2024-01-01", "stock": "2330.TW", "price": 600.0, "shares": 1000, "type": "買入"},
        ]
    }

# --- 2. 資產管理邏輯 (含賣出與平均成本) ---
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
            # 移動平均法：賣出不改變平均成本，但減少總額
            avg_cost = summary[s]["total_cost"] / summary[s]["total_shares"] if summary[s]["total_shares"] > 0 else 0
            summary[s]["total_shares"] -= tx['shares']
            summary[s]["total_cost"] -= tx['shares'] * avg_cost
            
    for s in summary.keys():
        summary[s]["avg_price"] = summary[s]["total_cost"] / summary[s]["total_shares"] if summary[s]["total_shares"] > 0 else 0
    return summary

# --- 3. 左側：資產中心與買賣操作 ---
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
    portfolio = calculate_portfolio(st.session_state.clients[cur_client])
    st.subheader(f"👤 {cur_client} 持股明細")
    
    for stock, data in portfolio.items():
        if data['total_shares'] > 0:
            with st.expander(f"📈 {stock} (餘 {int(data['total_shares'])} 股)", expanded=True):
                # 獲取現價
                try:
                    price_df = yf.Ticker(stock).history(period="1d")
                    current_p = price_df['Close'].iloc[-1] if not price_df.empty else data['avg_price']
                except:
                    current_p = data['avg_price']
                
                pnl = (current_p - data['avg_price']) * data['total_shares']
                pnl_pct = ((current_p / data['avg_price']) - 1) * 100 if data['avg_price'] != 0 else 0
                
                st.write(f"平均成本: **{data['avg_price']:.2f}**")
                st.write(f"目前損益: {int(pnl):,} ({pnl_pct:.2f}%)")
                
                b1, b2 = st.columns(2)
                if b1.button("買進", key=f"buy_{stock}_{cur_client}"):
                    st.session_state.pop_tx = {"client": cur_client, "stock": stock, "type": "買入"}
                if b2.button("賣出", key=f"sell_{stock}_{cur_client}"):
                    st.session_state.pop_tx = {"client": cur_client, "stock": stock, "type": "賣出"}

    if st.button("➕ 新增股票交易代碼"):
        st.session_state.clients[cur_client].append({"date": str(datetime.now().date()), "stock": "2330.TW", "price": 0.0, "shares": 0, "type": "買入"})
        st.rerun()

# --- 4. 買賣交易彈出窗 ---
if 'pop_tx' in st.session_state:
    with st.form("tx_form"):
        st.info(f"紀錄交易: {st.session_state.pop_tx['type']} {st.session_state.pop_tx['stock']}")
        t_price = st.number_input("成交價格", value=0.0)
        t_shares = st.number_input("成交股數", value=0, step=100)
        t_date = st.date_input("日期")
        if st.form_submit_button("確認提交"):
            st.session_state.clients[st.session_state.pop_tx['client']].append({
                "date": str(t_date), "stock": st.session_state.pop_tx['stock'],
                "price": t_price, "shares": t_shares, "type": st.session_state.pop_tx['type']
            })
            del st.session_state.pop_tx
            st.rerun()

# --- 5. 主畫面：K 線圖 (修復 Bar 消失問題) ---
c_search, c_period = st.columns([1, 2])
with c_search:
    target_stock = st.text_input("股票查詢", "2330.TW")
with c_period:
    k_period = st.radio("週期", ["60分", "日線", "周線"], horizontal=True, index=1)

# 參數對應
p_map = {"60分": ["60m", "2mo", [5, 35, 200]], "日線": ["1d", "2y", [20, 60, 124, 248]], "周線": ["1wk", "5y", [5, 35, 200]]}
interval, data_range, ma_list = p_map[k_period]

@st.cache_data(ttl=60)
def fetch_and_clean(symbol, inv, rng):
    data = yf.Ticker(symbol).history(period=rng, interval=inv)
    if data.empty: return None
    # 強制清洗資料
    data = data.dropna(subset=['Open', 'High', 'Low', 'Close'])
    # 指標計算
    e1 = data['Close'].ewm(span=12, adjust=False).mean()
    e2 = data['Close'].ewm(span=26, adjust=False).mean()
    data['MACD'], data['Signal'] = e1 - e2, (e1 - e2).ewm(span=9, adjust=False).mean()
    data['Hist'] = data['MACD'] - data['Signal']
    for m in ma_list:
        data[f'MA{m}'] = data['Close'].rolling(window=m).mean()
    return data

df = fetch_and_clean(target_stock, interval, data_range)

if df is not None:
    # 2:1:1 比例
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.5, 0.25, 0.25])
    
    # 1. K線 (強制指定不含 NaN 的數據)
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        increasing_line_color='#FF0000', decreasing_line_color='#00AA00',
        increasing_fillcolor='#FF0000', decreasing_fillcolor='#00AA00', name="K線"
    ), row=1, col=1)

    # 2. 均線 (平滑 Spline)
    ma_colors = ['#E11D74', '#1F4287', '#FF8C00', '#28B463']
    for i, m in enumerate(ma_list):
        fig.add_trace(go.Scatter(x=df.index, y=df[f'MA{m}'], line=dict(width=1.5, color=ma_colors[i%4], shape='spline'), name=f'MA{m}'), row=1, col=1)

    # 3. 成交量
    v_colors = ['#FF0000' if c >= o else '#00AA00' for o, c in zip(df['Open'], df['Close'])]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=v_colors, name="成交量"), row=2, col=1)

    # 4. MACD (平滑 Spline)
    h_colors = ['#FF0000' if v >= 0 else '#00AA00' for v in df['Hist']]
    fig.add_trace(go.Bar(x=df.index, y=df['Hist'], marker_color=h_colors, name="MACD柱"), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], line=dict(color='#0072BD', width=1, shape='spline'), name="DIF"), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Signal'], line=dict(color='#D95319', width=1, shape='spline'), name="DEA"), row=3, col=1)

    fig.update_layout(height=750, template="plotly_white", xaxis_rangeslider_visible=False, margin=dict(l=10, r=60, t=10, b=10), hovermode='x unified')
    fig.update_yaxes(side="right", dtick=100, gridcolor='#F0F0F0', autorangeoptions=dict(paddingmin=0.2, paddingmax=0.2), row=1, col=1)
    fig.update_yaxes(side="right", row=2, col=1); fig.update_yaxes(side="right", row=3, col=1)
    
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("⚠️ 查無數據，請確認代碼（如：2330.TW）或稍後再試。")
