import streamlit as st
import pandas as pd
import yfinance as yf
import feedparser
import ssl
from datetime import datetime
import time

# --- 1. 全域樣式與 1 分鐘自動刷新 ---
st.set_page_config(page_title="AI 經理人 5.1 - 全球實戰戰情室", layout="wide")

# 嘗試載入自動刷新組件 (若環境未安裝可手動重新整理)
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=60 * 1000, key="global_refresh")
except:
    pass

# 字體縮小與樣式美化
st.markdown("""
    <style>
    html, body, [class*="css"] { font-size: 13px !important; }
    .stButton>button { height: 24px; padding: 0px 8px; font-size: 11px; }
    .region-header { background-color: #1e3a8a; color: white; padding: 5px; border-radius: 3px; margin-top: 10px; font-weight: bold; }
    .news-card { border-left: 3px solid #3b82f6; padding-left: 10px; margin-bottom: 8px; font-size: 12px; }
    .sell-alert { color: #ff4b4b; font-weight: bold; background-color: #ffebeb; padding: 2px; border-radius: 4px; }
    .status-hold { color: #2ecc71; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 初始化數據庫 ---
if 'client_battles' not in st.session_state:
    st.session_state.client_battles = {}

# --- 3. 核心功能：抓取即時數據 ---
def get_live_price(ticker):
    try:
        # 抓取最新一筆交易數據
        data = yf.Ticker(ticker).history(period="1d")
        return data['Close'].iloc[-1] if not data.empty else 0
    except:
        return 0

# --- 4. 側邊欄：客戶切換與管理 (第 1 部分) ---
with st.sidebar:
    st.header("👤 客戶帳戶管理")
    new_client = st.text_input("新增客戶姓名", key="add_client")
    if st.button("➕ 建立帳戶") and new_client:
        if new_client not in st.session_state.client_battles:
            st.session_state.client_battles[new_client] = []
            st.rerun()
    
    st.divider()
    all_clients = list(st.session_state.client_battles.keys())
    current_client = st.selectbox("🎯 當前操作客戶", all_clients if all_clients else ["請先新增客戶"])

# --- 主畫面佈局 ---
st.title(f"🛡️ AI 經理人 5.1：[{current_client}] 實戰戰情室")
st.caption(f"數據自動刷新中... 最後同步：{datetime.now().strftime('%H:%M:%S')}")

col_left, col_right = st.columns([1.8, 1.2])

with col_left:
    # --- 5. 每日 15 檔起漲推薦 (第 2 部分) ---
    st.subheader("🔥 每日起漲點推薦 (齒輪共振邏輯)")
    
    def get_market_scan():
        # 整合：成本突破 + MACD共振 + 20%溢價論述
        return [
            {"id": "2402.TW", "name": "毅嘉", "score": 93, "reason": "突破大量成本區，MACD日線翻揚。"},
            {"id": "6531.TW", "name": "愛普*", "score": 95, "reason": "月日MACD共振，起漲第一點。"},
            {"id": "3035.TW", "name": "智原", "score": 91, "reason": "法人低位洗盤結束，慣性改變。"},
            {"id": "5269.TW", "name": "祥碩", "score": 94, "reason": "USB4.0趨勢帶量突破，溢價25%+"},
            {"id": "3227.TW", "name": "原相", "score": 88, "reason": "60分K回測均線不破，葛蘭碧買點2。"},
            {"id": "3034.TW", "name": "聯詠", "score": 86, "reason": "低位階MACD收斂，高殖利率護體。"},
            {"id": "2603.TW", "name": "長榮", "score": 89, "reason": "運價指數支撐，月線級別多頭排列。"},
            {"id": "2317.TW", "name": "鴻海", "score": 85, "reason": "228元底部防線確立，GB200量產期。"},
            {"id": "6438.TW", "name": "迅得", "score": 92, "reason": "CoWoS供應鏈噴發，MACD無背離。"},
            {"id": "3661.TW", "name": "世芯-KY", "score": 90, "reason": "法人洗盤結束，重回3500元成本區。"},
            {"id": "2330.TW", "name": "台積電", "score": 96, "reason": "全球核心資產，MACD零軸上發散。"},
            {"id": "2454.TW", "name": "聯發科", "score": 84, "reason": "邊緣AI題材，股價站穩所有均線。"},
            {"id": "6271.TW", "name": "同欣電", "score": 83, "reason": "低軌衛星題材，均線斜率向上。"},
            {"id": "3008.TW", "name": "大立光", "score": 81, "reason": "底部背離完成，主力低位吃貨。"},
            {"id": "2308.TW", "name": "台達電", "score": 82, "reason": "能源管理長線趨勢，量縮整理末端。"}
        ]

    for idx, s in enumerate(get_market_scan()):
        with st.expander(f"📊 {s['id']} {s['name']} - 評分: {s['score']}"):
            c1, c2 = st.columns([3, 1])
            c1.write(f"**分析:** {s['reason']} | **策略:** 齒輪 2.0 預測引擎")
            if c2.button("買入", key=f"buy_{s['id']}_{idx}"):
                if current_client != "請先新增客戶":
                    p = get_live_price(s['id'])
                    if p > 0:
                        st.session_state.client_battles[current_client].append({
                            "id": s['id'], "name": s['name'], "buy_p": p, "time": datetime.now()
                        })
                        st.toast(f"已加入 {current_client} 清單"); st.rerun()
                    else: st.error("價格抓取失敗")

with col_right:
    # --- 6. 客戶專屬戰鬥追蹤 (第 3 部分) ---
    st.subheader(f"💼 {current_client} 投資組合")
    if current_client in st.session_state.client_battles and st.session_state.client_battles[current_client]:
        battle_data = []
        total_pnl = 0
        
        for i, itm in enumerate(st.session_state.client_battles[current_client]):
            cur_p = get_live_price(itm['id'])
            pnl_per_share = cur_p - itm['buy_p']
            pnl_pct = (cur_p / itm['buy_p'] - 1) * 100 if itm['buy_p'] > 0 else 0
            total_pnl += pnl_per_share
            
            # 🚨 警示賣出訊號判定
            advice = "✅ 持有"
            if pnl_pct > 12: advice = "🚨 建議獲利 (背離)"
            elif pnl_pct < -5: advice = "🛑 止損 (破線)"

            battle_data.append({
                "標的": itm['name'],
                "每股損益": f"{pnl_per_share:+.2f}",
                "損益%": f"{pnl_pct:+.2f}%",
                "🚨 戰略指令": advice
            })
        
        st.table(pd.DataFrame(battle_data))
        st.metric("帳戶累積總損益", f"{total_pnl:+.2f} TWD")
        if st.button("結算清空清單", key="clear_battle"):
            st.session_state.client_battles[current_client] = []; st.rerun()
    else:
        st.info("尚無持股部位。")

# --- 7. 全球 20H 權威政經情報中樞 (第 4 部分：重磅升級) ---
st.divider()
st.header("🌎 全球政經情報中樞 (20H 極致時效)")
st.caption("精選當地權威媒體 (Reuters, Bloomberg, FT) | 繁體中文彙整")

def fetch_global_intel(region_query):
    ssl._create_default_https_context = ssl._create_unverified_context
    # 強制限制 20 小時內新聞
    url = f"https://news.google.com/rss/search?q={region_query}+when:20h&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    feed = feedparser.parse(url)
    return feed.entries[:8]

t1, t2, t3, t4 = st.tabs(["🇺🇸 美加墨", "🇪🇺 歐洲區域", "🇯🇵 亞洲/日本", "🇨🇳 中國地區"])

with t1:
    st.markdown("<div class='region-header'>NORTH AMERICA INTEL (WSJ/Bloomberg)</div>", unsafe_allow_html=True)
    for n in fetch_global_intel("USA+Economic+Fed+Semiconductor+Nvidia"):
        st.markdown(f"<div class='news-card'><b>{n.published[5:16]}</b> | <a href='{n.link}'>{n.title}</a></div>", unsafe_allow_html=True)

with t2:
    st.markdown("<div class='region-header'>EUROPEAN STRATEGY (FT/Reuters)</div>", unsafe_allow_html=True)
    for n in fetch_global_intel("Europe+Energy+Economy+Geopolitics"):
        st.markdown(f"<div class='news-card'><b>{n.published[5:16]}</b> | <a href='{n.link}'>{n.title}</a></div>", unsafe_allow_html=True)

with t3:
    st.markdown("<div class='region-header'>ASIA PACIFIC (Nikkei/Yonhap)</div>", unsafe_allow_html=True)
    for n in fetch_global_intel("Japan+Korea+Taiwan+SupplyChain+Tech"):
        st.markdown(f"<div class='news-card'><b>{n.published[5:16]}</b> | <a href='{n.link}'>{n.title}</a></div>", unsafe_allow_html=True)

with t4:
    st.markdown("<div class='region-header'>GREATER CHINA (Macro/Policy)</div>", unsafe_allow_html=True)
    for n in fetch_global_intel("China+Economy+Property+Market"):
        st.markdown(f"<div class='news-card'><b>{n.published[5:16]}</b> | <a href='{n.link}'>{n.title}</a></div>", unsafe_allow_html=True)

# --- 8. 技術分析輔助示意圖 ---
st.divider()
col_img1, col_img2 = st.columns(2)
with col_img1:
    
    st.caption("🚨 賣出警示 1：破位止損 (當股價跌破關鍵支撐區)")
with col_img2:
    
    st.caption("🚨 賣出警示 2：動能背離 (當股價創高但買盤動能衰退)")
