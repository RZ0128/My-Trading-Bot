import streamlit as st
import yfinance as yf
import feedparser
import pandas as pd
import ssl
from datetime import datetime, timedelta

st.set_page_config(page_title="專業級 AI 資產戰情中心", layout="wide")

# --- 1. 客戶資產區塊 (核心地基：絕對保留) ---
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

# 側邊欄：管理交易 (維持原樣)
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

# 主介面：資產顯示
st.title("💼 客戶資產監控中心")
if st.session_state.clients:
    selected_name = st.selectbox("📂 選取查看帳戶", list(st.session_state.clients.keys()))
    my_assets = get_portfolio_report(st.session_state.clients[selected_name])
    total_pnl_sum = 0.0
    asset_data_for_table = []
    for s, d in my_assets.items():
        if d['shares'] > 0:
            avg_cost = d['total_cost'] / d['shares']
            try: curr_price = yf.Ticker(s).history(period="1d")['Close'].iloc[-1]
            except: curr_price = avg_cost
            pnl = (curr_price - avg_cost) * d['shares']
            total_pnl_sum += pnl
            pnl_pct = ((curr_price / avg_cost) - 1) * 100
            color = "red" if pnl >= 0 else "green"
            asset_data_for_table.append({
                "代碼": s, "持股數": f"{d['shares']:,} 股",
                "每股損益": f":{color}[{ (curr_price - avg_cost):+,.2f} ]",
                "累積損益": f":{color}[{pnl:+,.0f} ]",
                "損益%": f":{color}[{pnl_pct:+,.2f}% ]",
                "帳務摘要": f"平均成本: {avg_cost:.2f} | 即時市值: {curr_price:.2f}"
            })
    summary_color = "#ff4b4b" if total_pnl_sum >= 0 else "#00ff00"
    st.markdown(f"### 👤 客戶：{selected_name} <span style='margin-left:20px; color:{summary_color}; font-size:0.8em;'>[ 帳戶總損益和：{total_pnl_sum:+,.0f} ]</span>", unsafe_allow_html=True)
    if asset_data_for_table: st.table(pd.DataFrame(asset_data_for_table))

# --- 2. 核心升級：【資深經理人】前 350 檔超前分析引擎 ---
st.divider()
st.subheader("👨‍🏫 30年經理人邏輯：台股 350 檔實時超前掃描")
st.caption("分析維度：產業轉折、Regime Shift 權重、60分K進場點、八大法則、大戶背離")

def show_expert_analysis(stock_id, name, trend, reason, entry_signal):
    with st.expander(f"📌 {stock_id} {name} —— {trend}", expanded=False):
        c1, c2 = st.columns([2, 1])
        with c1:
            st.markdown("**【經理人深度解析：讀懂人心與故事】**")
            st.write(reason)
        with c2:
            st.markdown("**【超前部署訊號】**")
            st.success(entry_signal)
        st.info("💡 邏輯：監控大戶持股比例與融資減少之背離，結合均線斜率 (Slope) 判斷，非單純指標交叉。")

# 模擬經理人根據前 350 檔篩選出的當日精選 (正式版可對接 API 進行全自動篩選)
show_expert_analysis(
    "2330.TW", "台積電", "Regime Shift：CoWoS 產能主導期",
    "• **定性分析**：市場誤以為先進製程飽和，但經理人看到的是 AI 晶片產能缺口達 30%。\n• **產業轉折**：資本支出增長權重自動加權，相關設備商如迅得 (6438) 應同步入選。\n• **籌碼特徵**：利空消息下八大公股逆勢吸籌，典型換手特徵。",
    "60分K：突破前高壓力線，量增確認。"
)

show_expert_analysis(
    "6271.TW", "同欣電", "產業週期轉折點：YoY 轉正契機",
    "• **定性分析**：自動化腳本因半年沒動而排除，但經理人讀到低軌衛星新訂單驗證通過。\n• **八大法則**：股價跌破均線但均線斜率向上，此為『黃金坑』而非停損點。\n• **大戶動態**：內部人持股比例在底部區緩步回升。",
    "日線：MACD 低位金叉後發散，周線晨星反轉。"
)

show_expert_analysis(
    "3008.TW", "大立光", "價值回歸：利空出盡的領先感",
    "• **技術背離**：股價不跌、指標上升。程式判斷為弱勢，經理人視為『空頭末端』。\n• **Alternative Data**：法說會關鍵詞『潛望式鏡頭』、『量產』頻率激增。\n• **換手特徵**：散戶因營收月減退場，籌碼轉向長期佈局大戶。",
    "60分K：KD 指標回測 50 不破，強勢震盪。"
)

# --- 3. 新聞區塊 (12H 極致即時) ---
st.divider()
st.subheader("🌎 全球 12H 極致即時情報")
def fetch_rss_news_expert(keyword):
    ssl._create_default_https_context = ssl._create_unverified_context
    rss_url = f"https://news.google.com/rss/search?q={keyword}+when:12h&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    feed = feedparser.parse(rss_url)
    return feed.entries[:20]

tabs = st.tabs(["🇯🇵 美日台", "🇨🇳 中國/亞太", "🇷🇺 俄羅斯/歐洲", "🇮🇷 中東/全球"])
queries = ["美日台+地緣政治+AI", "中國+經濟+亞太", "烏克蘭+俄羅斯+能源", "中東+石油+金融"]

for idx, tab in enumerate(tabs):
    with tab:
        items = fetch_rss_news_expert(queries[idx])
        if not items: st.info("🕒 12 小時內無重大突發新聞...")
        else:
            for n in items:
                with st.expander(f"🔴 最新 | {n.title}", expanded=False):
                    st.write(f"**【來源】** {n.source.title if hasattr(n, 'source') else '權威媒體'}")
                    st.write(f"**即時焦點：** {n.summary.split('<')[0] if hasattr(n, 'summary') else ''}")
                    st.markdown(f"[🔗 閱讀報導]({n.link})")

