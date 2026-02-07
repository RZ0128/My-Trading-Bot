import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 網頁基本設定
st.set_page_config(page_title="Elite-Trading-SaaS", layout="wide")

# --- 數據初始化：客戶 A/B/C ---
if 'clients' not in st.session_state:
    st.session_state.clients = {
        "客戶 A (大資產)": {"balance": 10000000.0, "portfolio": {"2330.TW": 10000, "3023.TW": 5000}},
        "客戶 B (小資產)": {"balance": 500000.0, "portfolio": {"2317.TW": 2000}},
        "客戶 C (新開戶)": {"balance": 2000000.0, "portfolio": {}}
    }

# --- 功能函式：獲取即時價格 ---
def get_last_price(symbol):
    try:
        data = yf.Ticker(symbol).history(period="1d")
        return data['Close'].iloc[-1]
    except:
        return 0.0

# --- 側邊欄控制項 ---
st.sidebar.title("🏛️ 創業基金管理中心")
selected_name = st.sidebar.selectbox("切換管理客戶", list(st.session_state.clients.keys()))
k_period = st.sidebar.radio("K 線週期切換", ["1h", "1d", "1wk"], index=1)
client = st.session_state.clients[selected_name]

# --- 頁面標題 ---
st.title(f"📊 {selected_name} - 即時管理後台")

# --- 第一區塊：資產統計卡片 ---
st.subheader("💰 帳戶資產概況")
total_market_val = 0
portfolio_data = []

for sym, shares in client["portfolio"].items():
    price = get_last_price(sym)
    mv = price * shares
    total_market_val += mv
    portfolio_data.append({"代碼": sym, "持股數": shares, "現價": round(price, 1), "市值": int(mv)})

total_assets = total_market_val + client["balance"]
c1, c2, c3 = st.columns(3)
c1.metric("總權益 (現金+股票)", f"NT$ {int(total_assets):,}")
c2.metric("剩餘可用資金", f"NT$ {int(client['balance']):,}")
c3.metric("持股市值", f"NT$ {int(total_market_val):,}")

# --- 第二區塊：互動 K 線圖 ---
st.divider()
st.subheader("🔍 即時技術分析 (K線圖)")
target_stock = st.text_input("輸入股票代碼觀看 (需加 .TW)", "2330.TW")

# 繪製 Plotly K線
df = yf.Ticker(target_stock).history(period="1y", interval=k_period)
fig = go.Figure(data=[go.Candlestick(
    x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name=target_stock
)])
# 增加 MA20 均線
df['MA20'] = df['Close'].rolling(window=20).mean()
fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='orange', width=1.5), name='MA20'))
fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False)
st.plotly_chart(fig, use_container_width=True)

# --- 第三區塊：下單與配置建議 ---
st.divider()
col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("⚡ 虛擬模擬下單")
    order_sym = st.text_input("下單代碼", value=target_stock)
    order_shares = st.number_input("購買股數", min_value=1, value=100)
    if st.button("確認買入"):
        price = get_last_price(order_sym)
        cost = price * order_shares * 1.001425 # 含手續費
        if client["balance"] >= cost:
            client["balance"] -= cost
            client["portfolio"][order_sym] = client["portfolio"].get(order_sym, 0) + order_shares
            st.success(f"已存入系統：{order_sym} 買入成功")
            st.rerun()
        else:
            st.error("現金不足！")

with col_right:
    st.subheader("💡 系統配置建議")
    st.write(f"當前策略：**{'積極進攻' if total_assets > 5000000 else '穩健防禦'}**")
    st.info("系統偵測：週五費半強勢。建議調整「半導體」佔比至 40%，並針對高乖離個股進行分批減碼。")

# 顯示持股清單表
if portfolio_data:
    st.table(pd.DataFrame(portfolio_data))
