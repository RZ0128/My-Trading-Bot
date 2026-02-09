import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="客戶資產精確管理系統", layout="wide")

# --- 1. 資料庫初始化 ---
if 'clients' not in st.session_state:
    st.session_state.clients = {
        "客戶 A": [
            {"date": "2024-01-01", "stock": "2330.TW", "price": 600.0, "shares": 1000, "type": "買入"}
        ]
    }

# --- 2. 核心計算邏輯 (移動平均成本) ---
def get_portfolio_analysis(transactions):
    analysis = {}
    for tx in transactions:
        s = tx['stock']
        if s not in analysis:
            analysis[s] = {"shares": 0, "total_cost": 0.0, "history": []}
        
        analysis[s]["history"].append(tx)
        
        if tx['type'] == "買入":
            # 買入：增加股數，增加總成本
            analysis[s]["shares"] += tx['shares']
            analysis[s]["total_cost"] += tx['shares'] * tx['price']
        elif tx['type'] == "賣出":
            # 賣出：減少股數，按比例減少成本（平均成本不變）
            if analysis[s]["shares"] > 0:
                avg_cost = analysis[s]["total_cost"] / analysis[s]["shares"]
                analysis[s]["shares"] -= tx['shares']
                analysis[s]["total_cost"] -= tx['shares'] * avg_cost
                
    # 計算最終平均單價
    for s in analysis:
        if analysis[s]["shares"] > 0:
            analysis[s]["avg_price"] = analysis[s]["total_cost"] / analysis[s]["shares"]
        else:
            analysis[s]["avg_price"] = 0
    return analysis

# --- 3. 介面設計 ---
st.title("💼 專業投資人資產管理系統")

# 客戶選擇器
all_clients = list(st.session_state.clients.keys())
col_c1, col_c2 = st.columns([2, 1])
with col_c1:
    cur_client = st.selectbox("📁 選擇管理客戶", all_clients)
with col_c2:
    if st.button("➕ 新增客戶"):
        new_name = f"客戶 {chr(65 + len(all_clients))}"
        st.session_state.clients[new_name] = []
        st.rerun()

st.divider()

# 獲取該客戶分析數據
portfolio = get_portfolio_analysis(st.session_state.clients[cur_client])

# --- 4. 資產總覽卡片 ---
st.subheader(f"📊 {cur_client} - 現有持股明細")

if not portfolio or all(v['shares'] == 0 for v in portfolio.values()):
    st.info("目前尚無持股紀錄，請點擊下方「新增交易」。")
else:
    for stock, data in portfolio.items():
        if data['shares'] > 0:
            with st.container():
                # 抓取即時市價
                try:
                    ticker = yf.Ticker(stock)
                    current_price = ticker.history(period="1d")['Close'].iloc[-1]
                except:
                    current_price = data['avg_price']
                
                # 計算損益
                market_value = current_price * data['shares']
                total_pnl = market_value - data['total_cost']
                pnl_pct = (total_pnl / data['total_cost'] * 100) if data['total_cost'] > 0 else 0
                
                # 顯示 UI
                c1, c2, c3, c4, c5 = st.columns([1.5, 1.5, 1.5, 2, 1.5])
                c1.metric("代碼", stock)
                c2.metric("持股數", f"{int(data['shares']):,}")
                c3.metric("平均成本", f"{data['avg_price']:.2f}")
                c4.metric("即時損益", f"{int(total_pnl):,}", f"{pnl_pct:.2f}%")
                
                with c5:
                    st.write("") # 間距
                    if st.button(f"➕ 買入/➖ 賣出", key=f"act_{stock}"):
                        st.session_state.edit_stock = stock
            st.divider()

# --- 5. 交易明細紀錄表 ---
with st.expander("📝 查看原始交易歷史帳簿"):
    if st.session_state.clients[cur_client]:
        df_history = pd.DataFrame(st.session_state.clients[cur_client])
        st.table(df_history)
    else:
        st.write("暫無紀錄")

# --- 6. 互動彈出視窗：新增交易 ---
st.sidebar.header("📥 快速新增交易")
with st.sidebar.form("add_tx"):
    new_stock = st.text_input("股票代碼", value=st.session_state.get('edit_stock', '2330.TW'))
    new_type = st.radio("交易類型", ["買入", "賣出"], horizontal=True)
    new_price = st.number_input("成交單價", min_value=0.0, step=0.1)
    new_shares = st.number_input("成交股數", min_value=1, step=100)
    new_date = st.date_input("交易日期")
    
    if st.form_submit_button("確認提交紀錄"):
        st.session_state.clients[cur_client].append({
            "date": str(new_date),
            "stock": new_stock.upper(),
            "price": new_price,
            "shares": new_shares,
            "type": new_type
        })
        st.success(f"已紀錄 {new_stock}")
        st.rerun()

# 重置選中股票
if st.sidebar.button("清空輸入欄"):
    if 'edit_stock' in st.session_state:
        del st.session_state.edit_stock
    st.rerun()
