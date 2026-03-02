import streamlit as st
import pandas as pd
import yfinance as yf
import feedparser
import ssl
from datetime import datetime
import urllib.parse
import gspread 
from google.oauth2.service_account import Credentials

# --- [1. 核心配置 & 樣式] ---
st.set_page_config(page_title="AI Manager 9.1 - Unabridged", layout="wide")

# 強制自動刷新 (每 60 秒)
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=60 * 1000, key="v91_unabridged")
except:
    pass

def init_connection():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        return client.open("AI_Manager_DB").sheet1
    except:
        return None

db = init_connection()

st.markdown("""
    <style>
    html, body, [class*="css"] { font-size: 13px !important; color: #1e1e1e; }
    .stButton>button { height: 26px; padding: 0px 10px; font-size: 11px; border-radius: 5px; }
    .news-card { border-left: 4px solid #cc0000; padding-left: 12px; margin-bottom: 8px; font-size: 12px; border-bottom: 1px solid #eee; padding-bottom: 5px; }
    .price-up { color: #ff0000; font-weight: bold; }
    .price-down { color: #008000; font-weight: bold; }
    .alert-red { color: #ffffff; background-color: #ff0000; padding: 2px 8px; border-radius: 12px; font-weight: bold; font-size: 11px; }
    .alert-yellow { color: #000000; background-color: #ffcc00; padding: 2px 8px; border-radius: 12px; font-weight: bold; font-size: 11px; }
    .alert-green { color: #ffffff; background-color: #008000; padding: 2px 8px; border-radius: 12px; font-weight: bold; font-size: 11px; }
    </style>
    """, unsafe_allow_html=True)

# --- [2. 數據引擎：含預警燈邏輯] ---
def get_stock_perf(ticker, base_score):
    search_list = [ticker, ticker.replace(".TW", ".TWO")] if ".TW" in ticker else [ticker]
    for t in search_list:
        try:
            stock = yf.Ticker(t)
            df = stock.history(period="2d")
            if len(df) >= 2:
                curr_p = df['Close'].iloc[-1]
                prev_p = df['Close'].iloc[-2]
                diff = curr_p - prev_p
                pct_change = (diff / prev_p) * 100
                color = "price-up" if diff > 0 else "price-down" if diff < 0 else "price-even"
                
                # 預警參數：-3% 紅燈, -1.5% 黃燈
                if pct_change <= -3.0: 
                    alert = ("🔴 破位", "alert-red")
                elif -3.0 < pct_change <= -1.5: 
                    alert = ("🟡 警戒", "alert-yellow")
                else: 
                    alert = ("🟢 安全", "alert-green")
                
                return round(curr_p, 1), f"{diff:+.1f}", color, base_score + (1 if diff > 0 else -1), alert
        except: continue
    return 0.0, "0.0", "price-even", base_score, ("⚪ 讀取", "")

# --- [3. 雲端同步邏輯] ---
def get_cloud_data():
    if db:
        try:
            records = db.get_all_records()
            return pd.DataFrame(records)
        except: return pd.DataFrame()
    return pd.DataFrame()

# --- [4. 側邊欄：內存客戶管理系統 (iPad 專用版)] ---
with st.sidebar:
    st.header("👤 帳戶控制台 (iPad 專用)")
    
    # 初始化內存資料庫 (Session State)
    if 'local_db' not in st.session_state:
        st.session_state.local_db = pd.DataFrame(columns=['client', 'id', 'name', 'buy_price', 'shares'])
    
    if 'client_list' not in st.session_state:
        st.session_state.client_list = ["周靖傑"]

    new_c_name = st.text_input("📝 輸入新客戶全名", key="ipad_new_c")
    if st.button("➕ 建立客戶帳戶"):
        if new_c_name and new_c_name not in st.session_state.client_list:
            st.session_state.client_list.append(new_c_name)
            st.success(f"客戶 {new_c_name} 已建立")
            st.rerun()

    st.divider()
    cur_c = st.selectbox("🎯 當前操作客戶", st.session_state.client_list)
    st.info("💡 目前運作於 iPad 本地高速模式，操作將即時反應。")

# --- [5. 主畫面：15 檔 AI 偵測與投資組合 - 極速執行版] ---
st.title(f"🛡️ AI 經理人 9.7：[{cur_c}] 戰略中心")

col_l, col_r = st.columns([1.6, 1.4])

# --- 左側：15 檔 AI 實時偵測 (秒速下單) ---
with col_l:
    st.subheader("🔥 AI 全方位技術偵測 (Top 15)")
    
    scan_list = [
        {"id": "2402.TW", "name": "毅嘉", "score": 93, "tech": "MACD 二次金叉，K線站穩42.5元支撐。"},
        {"id": "6531.TW", "name": "愛普*", "score": 95, "tech": "月日 MACD 多頭共振，起漲第一點。"},
        {"id": "3035.TW", "name": "智原", "score": 91, "tech": "法人連買，60分K呈現多頭排列。"},
        {"id": "5269.TW", "name": "祥碩", "score": 94, "tech": "技術面帶量突破年線，目標溢價20%+。"},
        {"id": "3227.TW", "name": "原相", "score": 88, "tech": "60分K回測不破，均線斜率向上。"},
        {"id": "3034.TW", "name": "聯詠", "score": 86, "tech": "低位 MACD 收斂，高殖利率護體。"},
        {"id": "2603.TW", "name": "長榮", "score": 89, "tech": "紅海局勢升溫，運價支撐力道強。"},
        {"id": "2317.TW", "name": "鴻海", "score": 85, "tech": "GB200 指標股，220元強勢防線。"},
        {"id": "6438.TW", "name": "迅得", "score": 92, "tech": "CoWoS 設備需求爆發，主力鎖籌。"},
        {"id": "3661.TW", "name": "世芯-KY", "score": 90, "tech": "非理性下殺後底背離，回補力道強。"},
        {"id": "2330.TW", "name": "台積電", "score": 96, "tech": "AI 全球核心，各級均線多頭排列。"},
        {"id": "2454.TW", "name": "聯發科", "score": 84, "tech": "邊緣 AI 龍頭，回踩年線支撐。"},
        {"id": "6271.TW", "name": "同欣電", "score": 83, "tech": "低軌衛星題材，打底完成準備突破。"},
        {"id": "3008.TW", "name": "大立光", "score": 81, "tech": "光學元件築底完成，外資賣壓衰竭。"},
        {"id": "2308.TW", "name": "台達電", "score": 82, "tech": "電源管理龍頭，季線強支撐。"}
    ]

    for idx, s in enumerate(scan_list):
        p, d, c, fs, alert_info = get_stock_perf(s['id'], s['score'])
        
        with st.expander(f"📊 {s['id']} {s['name']} | 評分: {fs} | 現價: {p}"):
            st.markdown(f"**狀態預警：** <span class='{alert_info[1]}'>{alert_info[0]}</span>", unsafe_allow_html=True)
            st.markdown(f"**今日漲跌：** <span class='{c}' style='font-size:18px;'>{d}</span>", unsafe_allow_html=True)
            st.write(f"**深度分析：** {s['tech']}")
            
            o1, o2, o3 = st.columns([1, 1, 1])
            u = o1.radio("單位", ["張", "股"], key=f"u_ipad_{idx}")
            q = o2.number_input("數量", min_value=1, value=1, key=f"q_ipad_{idx}")
            real_shares = q * 1000 if u == "張" else q
            
            if o3.button("執行買入", key=f"b_ipad_{idx}"):
                # 關鍵優化：直接寫入 iPad 本地記憶體，不透過雲端
                new_data = pd.DataFrame([[cur_c, s['id'], s['name'], p, real_shares]], 
                                       columns=['client', 'id', 'name', 'buy_price', 'shares'])
                st.session_state.local_db = pd.concat([st.session_state.local_db, new_data], ignore_index=True)
                st.toast(f"✅ {s['name']} 買入成功")
                st.rerun()

# --- 右側：投資組合 (本地秒速反饋) ---
with col_r:
    st.subheader(f"💼 {cur_c} 投資組合 (iPad 本地)")
    total_pnl = 0
    
    # 從 iPad 內存讀取
    my_h = st.session_state.local_db[st.session_state.local_db['client'] == cur_c]
    
    if my_h.empty:
        st.info("目前尚無持股部位。")
    else:
        for i, row in my_h.iterrows():
            curr_p, _, _, _, a_info = get_stock_perf(row['id'], 0)
            item_pnl = (curr_p - row['buy_price']) * row['shares']
            total_pnl += item_pnl
            
            with st.container():
                c1, c2, c3 = st.columns([1.8, 1.8, 0.8])
                with c1:
                    st.markdown(f"**{row['name']}** <span class='{a_info[1]}'>{a_info[0]}</span>", unsafe_allow_html=True)
                    st.write(f"{row['shares']} 股")
                with c2:
                    p_color = "red" if item_pnl >= 0 else "green"
                    st.markdown(f"損益: <span style='color:{p_color}; font-weight:bold;'>NT$ {item_pnl:,.0f}</span>", unsafe_allow_html=True)
                    st.caption(f"現價: {curr_p}")
                
                # 精密減倉齒輪
                with c3:
                    gear = st.popover("⚙️")
                    dq = gear.number_input("減持", 1, int(row['shares']), int(row['shares']), key=f"dq_ipad_{i}")
                    if gear.button("確認", key=f"dbtn_ipad_{i}"):
                        if dq >= row['shares']:
                            st.session_state.local_db = st.session_state.local_db.drop(i)
                        else:
                            st.session_state.local_db.at[i, 'shares'] -= dq
                        st.rerun()
            st.divider()
            
        t_color = "red" if total_pnl >= 0 else "green"
        st.markdown(f"### 帳戶總損益: <span style='color:{t_color};'>NT$ {total_pnl:,.0f}</span>", unsafe_allow_html=True)

# --- 6. 全球情報 (基於 8.5 強化版：新增中東戰略、全繁體中文優化) ---
st.divider()
st.header("🌎 全球 24H 戰略情報中樞")

def fetch_massive_intel(query_list):
    # 確保連線安全繞過，這是在 8.5 版本中表現最穩定的方式
    ssl._create_default_https_context = ssl._create_unverified_context
    all_entries = []
    
    for q in query_list:
        # 強制指定 hl=zh-TW (繁體中文) 與 gl=TW (台灣區域)，確保直觀觀看
        u = f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        try:
            feed = feedparser.parse(u)
            all_entries.extend(feed.entries)
        except:
            continue
            
    # 去重處理：避免不同關鍵字抓到重複新聞
    unique_news = {n.link: n for n in all_entries}.values()
    
    # 排序並取前 18 則 (維持 8.5 版的高密度)
    return sorted(list(unique_news), key=lambda x: x.published, reverse=True)[:18]

# --- 精準戰略關鍵字地圖 (全繁體中文優化) ---
intel_map = {
    "🇺🇸 美國戰略": ["川普+馬斯克+華爾街", "輝達+聯準會+降息"],
    "🇪🇺 歐洲動態": ["歐洲+經濟+烏克蘭局勢", "歐元區+歐洲央行+能源"],
    "🇮🇱 中東衝突": ["中東戰爭+以色列+伊朗", "紅海+航運+石油價格"],
    "🇯🇵 亞洲科技": ["台積電+半導體+CoWoS", "日本+日經+科技股"],
    "🇨🇳 中國觀點": ["中國+經濟+政策+財經 -新華網 -人民網"]
}

tabs = st.tabs(list(intel_map.keys()))

for tab, (region, q_list) in zip(tabs, intel_map.items()):
    with tab:
        items = fetch_massive_intel(q_list)
        if not items:
            st.warning(f"目前 {region} 暫無最新中文情報，系統持續監控中...")
        else:
            for n in items:
                # 樣式採用 8.5 版本的 news-card 結構
                st.markdown(f"""
                    <div class='news-card'>
                        🕒 {n.published[5:16]} | 
                        <a href='{n.link}' target='_blank' style='text-decoration:none; color:#1e1e1e;'>
                            {n.title}
                        </a>
                    </div>
                """, unsafe_allow_html=True)
