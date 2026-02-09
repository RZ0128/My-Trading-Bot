import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="全球地緣政治與資產導航", layout="wide")

# --- 1. 資料初始化 ---
if 'clients' not in st.session_state:
    st.session_state.clients = {"新客戶": []}

# --- 2. 核心計算邏輯 (新增累積損益) ---
def get_detailed_analysis(transactions):
    analysis = {}
    for tx in transactions:
        s = tx['stock']
        if s not in analysis: 
            analysis[s] = {"shares": 0, "total_cost": 0.0, "realized_pnl": 0.0}
        
        if tx['type'] == "買入":
            analysis[s]["shares"] += tx['shares']
            analysis[s]["total_cost"] += tx['shares'] * tx['price']
        elif tx['type'] == "賣出":
            if analysis[s]["shares"] > 0:
                avg_cost = analysis[s]["total_cost"] / analysis[s]["shares"]
                # 賣出時計算實現損益
                analysis[s]["realized_pnl"] += tx['shares'] * (tx['price'] - avg_cost)
                analysis[s]["shares"] -= tx['shares']
                analysis[s]["total_cost"] -= tx['shares'] * avg_cost
    return analysis

# --- 3. 沉浸式跑馬燈 (慢速/大字體) ---
def get_marquee():
    try:
        symbols = {"加權指數": "^TWII", "台積電": "2330.TW", "美股道瓊": "^DJI", "日經225": "^N225"}
        text = ""
        for name, sym in symbols.items():
            d = yf.Ticker(sym).history(period="2d")
            p = d['Close'].iloc[-1]
            c = p - d['Close'].iloc[-2]
            icon = "🔺" if c >= 0 else "🔻"
            text += f" &nbsp;&nbsp;&nbsp;&nbsp; 【{name}】 {p:,.2f} ({icon}{c:+.2f}) &nbsp;&nbsp;&nbsp;&nbsp; "
        return text
    except: return " 數據連線中... "

st.markdown(f"""
    <div style="background-color: #1e1e1e; color: #ff4b4b; padding: 15px; border-bottom: 3px solid #ff4b4b;">
        <marquee scrollamount="3" style="font-size: 24px; font-weight: 900; font-family: 'Microsoft JhengHei';">{get_marquee()}</marquee>
    </div>
""", unsafe_allow_html=True)

# --- 4. 客戶資產區 (加入詳細損益) ---
st.title("💼 客戶資產監控中心")
cur_client = st.selectbox("📁 選取帳戶", list(st.session_state.clients.keys()))

portfolio = get_detailed_analysis(st.session_state.clients[cur_client])

if st.session_state.clients[cur_client]:
    for stock, data in portfolio.items():
        if data['shares'] > 0 or data['realized_pnl'] != 0:
            try:
                curr_p = yf.Ticker(stock).history(period="1d")['Close'].iloc[-1]
            except: curr_p = 0
            
            avg = data['total_cost'] / data['shares'] if data['shares'] > 0 else 0
            unrealized_pnl = (curr_p - avg) * data['shares']
            total_pnl = unrealized_pnl + data['realized_pnl']
            per_share_pnl = (curr_p - avg) if data['shares'] > 0 else 0
            
            with st.container():
                c1, c2, c3, c4 = st.columns([1, 1, 1, 1.5])
                c1.metric(f"📈 {stock}", f"{int(data['shares'])} 股")
                c2.metric("每股損益", f"{per_share_pnl:+.2f}")
                c3.metric("累積總損益", f"{int(total_pnl):,}", f"{((curr_p/avg-1)*100 if avg>0 else 0):.2f}%")
                with c4:
                    st.write("帳務摘要")
                    st.caption(f"平均成本: {avg:.2f} | 即時市價: {curr_p:.2f}")
            st.divider()

# 交易明細 (右側刪除)
with st.expander("📝 原始交易歷史 (更正請點擊🗑️)", expanded=False):
    for idx, tx in enumerate(st.session_state.clients[cur_client]):
        cols = st.columns([2, 1, 1, 1])
        cols[0].write(f"{tx['date']} {tx['stock']}")
        cols[1].write(tx['type'])
        cols[2].write(f"${tx['price']}")
        if cols[3].button("🗑️", key=f"del_{idx}"):
            st.session_state.clients[cur_client].pop(idx); st.rerun()

# --- 5. 全球新聞動態 (去重複+外部鏈結) ---
st.divider()
st.subheader("🌎 全球重大情報彙整 (點擊標題查看詳情)")

# 關鍵字預警
with st.expander("⚙️ 預警標籤設定"):
    warn_keywords = st.text_input("輸入關鍵字 (以逗號隔開)", "川普, 關稅, 日本國會, 台海, 封鎖, 美伊, 核協議").split(",")

def news_card(title, url, source):
    display_title = title
    for kw in warn_keywords:
        kw = kw.strip()
        if kw in title:
            display_title = title.replace(kw, f"<span style='color:red; font-weight:bold;'>{kw}</span>")
    
    st.markdown(f"""
        <div style="margin-bottom: 10px; padding: 5px; border-left: 4px solid #ccc;">
            <a href="{url}" target="_blank" style="text-decoration: none; color: #333; font-size: 18px;">• {display_title}</a>
            <span style="color: #888; font-size: 12px; margin-left: 10px;">[{source}]</span>
        </div>
    """, unsafe_allow_html=True)

t1, t2, t3, t4 = st.tabs(["🇺🇸美日台", "🇨🇳亞太", "🇪🇺歐俄", "🇮🇷中東全球"])
with t1:
    news_card("日本高市早苗內閣首度施政報告：強調台日經濟安保重要性", "https://news.google.com/search?q=高市早苗", "NHK")
    news_card("川普 關稅 2.0 政策解讀：對主要貿易夥伴影響評估報告", "https://news.google.com/search?q=Trump+Tariff", "WSJ")
    news_card("台海 局勢觀察：美軍第七艦隊加強巴士海峽偵巡次數", "https://news.google.com/search?q=Taiwan+Strait", "Reuters")

with t2:
    news_card("中國 兩會 召開日期確定：市場關注是否推出新一輪房地產救市政策", "https://news.google.com/search?q=兩會", "南華早報")
    news_card("中印邊境衝突出現轉機：雙方同意建立常態化熱線", "https://news.google.com/search?q=Sino-India", "財新")

with t3:
    news_card("俄烏戰爭：普丁釋放談判意願，前提是保留現有佔領領土", "https://news.google.com/search?q=Ukraine+Russia", "BBC")

with t4:
    news_card("美伊 關係：伊朗重申若美方取消石油禁運，願重返 核協議 框架", "https://news.google.com/search?q=Iran+Nuclear", "Al Jazeera")
    news_card("華爾街 預警：科技股高點已過？防禦性價值股重新獲得法人青睞", "https://news.google.com/search?q=Wall+Street", "Bloomberg")

# --- 6. 側邊欄紀錄 ---
with st.sidebar:
    st.header("📥 紀錄交易")
    with st.form("tx"):
        s = st.text_input("代碼", "2330.TW"); t = st.radio("類型", ["買入", "賣出"], horizontal=True)
        p = st.number_input("單價", 0.0); sh = st.number_input("股數", 1); d = st.date_input("日期")
        if st.form_submit_button("確認紀錄"):
            st.session_state.clients[cur_client].append({"date":str(d),"stock":s.upper(),"price":p,"shares":sh,"type":t})
            st.rerun()
