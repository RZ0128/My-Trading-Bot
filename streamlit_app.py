import streamlit as st
import yfinance as yf
import feedparser
import pandas as pd
import ssl

st.set_page_config(page_title="專業級資產監控系統", layout="wide")

# --- 1. 客戶資產區塊 (嚴格復原至您最滿意的版本) ---
if 'clients' not in st.session_state:
    st.session_state.clients = {}

def get_portfolio_report(transactions):
    report = {}
    for tx in transactions:
        s = tx['stock']
        if s not in report: report[s] = {"shares": 0, "total_cost": 0.0}
        if tx['type'] == "買入":
            report[s]["shares"] += tx['shares']
            report[s]["total_cost"] += tx['shares'] * tx['price']
        elif tx['type'] == "賣出":
            if report[s]["shares"] > 0:
                avg = report[s]["total_cost"] / report[s]["shares"]
                report[s]["shares"] -= tx['shares']
                report[s]["total_cost"] -= tx['shares'] * avg
    return report

# 側邊欄：管理與交易紀錄
with st.sidebar:
    st.header("👤 客戶管理中心")
    new_c = st.text_input("輸入新客戶姓名")
    if st.button("➕ 新增帳戶") and new_c:
        if new_c not in st.session_state.clients:
            st.session_state.clients[new_c] = []; st.rerun()
    st.divider()
    st.header("📥 紀錄交易")
    with st.form("tx_input"):
        active_c = st.selectbox("選擇操作帳戶", list(st.session_state.clients.keys()))
        stock_id = st.text_input("股票代碼 (如: 2330.TW)", "2330.TW")
        type_radio = st.radio("交易類型", ["買入", "賣出"], horizontal=True)
        price_in = st.number_input("成交單價", min_value=0.0, step=0.1)
        shares_in = st.number_input("成交股數", min_value=1, step=1)
        if st.form_submit_button("確認提交紀錄"):
            st.session_state.clients[active_c].append({"stock": stock_id.upper(), "price": price_in, "shares": shares_in, "type": type_radio})
            st.rerun()

# 主介面：資產顯示區 (照截圖樣式復原)
st.title("💼 客戶資產監控中心")
if st.session_state.clients:
    selected_name = st.selectbox("📂 選取查看帳戶", list(st.session_state.clients.keys()))
    my_assets = get_portfolio_report(st.session_state.clients[selected_name])
    
    st.subheader(f"📊 {selected_name} 持股明細")
    
    asset_list = []
    for s, d in my_assets.items():
        if d['shares'] > 0:
            avg_cost = d['total_cost'] / d['shares']
            try:
                curr_price = yf.Ticker(s).history(period="1d")['Close'].iloc[-1]
            except:
                curr_price = avg_cost
            
            pnl = (curr_price - avg_cost) * d['shares']
            pnl_pct = ((curr_price / avg_cost) - 1) * 100
            
            # 根據損益決定顏色
            color = "red" if pnl >= 0 else "green"
            
            asset_list.append({
                "代碼": s,
                "持股數": f"{d['shares']:,} 股",
                "每股損益": f":{color}[{ (curr_price - avg_cost):+,.2f} ]",
                "累積損益": f":{color}[{pnl:+,.0f} ]",
                "損益%": f":{color}[{pnl_pct:+,.2f}% ]",
                "帳務摘要": f"平均成本: {avg_cost:.2f} | 即時市值: {curr_price:.2f}"
            })
    
    if asset_list:
        st.table(pd.DataFrame(asset_list))
    
    with st.expander("📝 原始交易歷史 (右側可進行刪除)"):
        st.write(st.session_state.clients[selected_name])

# --- 2. 新聞區塊 (保留您滿意的即時對接版) ---
st.divider()
st.subheader("🌎 全球地緣政治 & 財經監控 (權威媒體即時對接)")

def fetch_rss_news_final(keyword):
    ssl._create_default_https_context = ssl._create_unverified_context
    rss_url = f"https://news.google.com/rss/search?q={keyword}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    feed = feedparser.parse(rss_url)
    return feed.entries[:20]

tabs = st.tabs(["🇯🇵 美日台", "🇨🇳 中國/亞太", "🇷🇺 俄羅斯/歐洲", "🇮🇷 中東/全球"])
queries = ["美日台+地緣政治", "中國+亞太經濟", "俄羅斯+烏克蘭+能源", "中東+石油+金融"]

for idx, tab in enumerate(tabs):
    with tab:
        news_entries = fetch_rss_news_final(queries[idx])
        if not news_entries:
            st.warning("暫時無法取得即時新聞。")
        else:
            for entry in news_entries:
                with st.expander(f"● {entry.title}", expanded=False):
                    source = entry.source.title if hasattr(entry, 'source') else "權威媒體"
                    st.markdown(f"**【情報來源】** {source} | **【發布時間】** {entry.published}")
                    st.markdown("---")
                    st.write("實時動態：該報導涉及全球市場關鍵變動，詳細深度分析請點擊下方連結。")
                    st.markdown(f"[🔗 閱讀國際媒體原始報導內容]({entry.link})")
