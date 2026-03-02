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

# --- [4. 側邊欄：帳戶管理 - 完整同步版] ---
with st.sidebar:
    st.header("👤 客戶帳戶管理")
    
    # 新增客戶輸入區
    new_client_input = st.text_input("📝 輸入新客戶全名", key="sidebar_new_client")
    if st.button("➕ 建立並同步帳戶"):
        if new_client_input and db:
            # 寫入初始化標記，確保雲端能即時抓到這個新客戶
            db.append_row([new_client_input, "INIT", "初始化", 0, 0])
            st.success(f"帳戶 {new_client_input} 已同步至雲端")
            st.rerun()
        elif not new_client_input:
            st.warning("請先輸入姓名")

    st.divider()
    
    # 讀取雲端最新客戶清單
    df_sync = get_cloud_data()
    if not df_sync.empty:
        # 過濾掉 INIT 標記，提取唯一客戶名稱
        real_clients = df_sync[df_sync['id'] != "INIT"]['client'].unique().tolist()
        if real_clients:
            existing_clients = real_clients
        else:
            existing_clients = ["尚未有持股客戶"]
    else:
        existing_clients = ["連線中..."]
        
    cur_c = st.selectbox("🎯 當前操作客戶", existing_clients)

# --- [5. 主畫面：完整 15 檔推薦與投資組合 - 零精簡版] ---
st.title(f"🛡️ AI 經理人 9.2：[{cur_c}] 全功能戰略版")

col_l, col_r = st.columns([1.6, 1.4])

with col_l:
    st.subheader("🔥 每日 15 檔推薦 (含預警機制)")
    # 完整 15 檔清單，絕不精簡
    scan_list = [
        {"id": "2402.TW", "name": "毅嘉", "score": 93, "detail": "站穩 42.5 元支撐。MACD 二次金叉。"},
        {"id": "6531.TW", "name": "愛普*", "score": 95, "detail": "月日 MACD 共振。起漲第一點。"},
        {"id": "3035.TW", "name": "智原", "score": 91, "detail": "法人連買，紅 K 吞噬壓力區。"},
        {"id": "5269.TW", "name": "祥碩", "score": 94, "detail": "帶量突破年線，溢價預估 20%+。"},
        {"id": "3227.TW", "name": "原相", "score": 88, "detail": "60分K回測不破，均線斜率向上。"},
        {"id": "3034.TW", "name": "聯詠", "score": 86, "detail": "低位MACD收斂，高殖利率護體。"},
        {"id": "2603.TW", "name": "長榮", "score": 89, "detail": "運價支撐，月線多頭排列。"},
        {"id": "2317.TW", "name": "鴻海", "score": 85, "detail": "GB200 指標，220元強勢防線。"},
        {"id": "6438.TW", "name": "迅得", "score": 92, "detail": "CoWoS 設備需求，主力鎖籌。"},
        {"id": "3661.TW", "name": "世芯-KY", "score": 90, "detail": "非理性下殺後底背離，回補在即。"},
        {"id": "2330.TW", "name": "台積電", "score": 96, "detail": "AI 全球核心，拉回皆買點。"},
        {"id": "2454.TW", "name": "聯發科", "score": 84, "detail": "邊緣AI 龍頭，技術面回踩支撐。"},
        {"id": "6271.TW", "name": "同欣電", "score": 83, "detail": "低軌衛星題材，打底完成突破。"},
        {"id": "3008.TW", "name": "大立光", "score": 81, "detail": "光學元件築底，外資賣壓衰竭。"},
        {"id": "2308.TW", "name": "台達電", "score": 82, "detail": "電源管理龍頭，季線支撐強。"}
    ]

    for idx, s in enumerate(scan_list):
        # 獲取即時數據 (包含預警燈)
        price, diff, color, final_score, alert_info = get_stock_perf(s['id'], s['score'])
        
        # 展開摺疊面板：標題含現價與評分
        with st.expander(f"📊 {s['id']} {s['name']} | 評分: {final_score} | 現價: {price}"):
            st.markdown(f"**狀態預警：** <span class='{alert_info[1]}'>{alert_info[0]}</span>", unsafe_allow_html=True)
            st.markdown(f"**今日表現：** <span class='{color}' style='font-size:18px;'>{diff}</span>", unsafe_allow_html=True)
            st.write(f"**戰略分析：** {s['detail']}")
            st.markdown("---")
            
            # 買入指令
            o_c1, o_c2, o_c3 = st.columns([1, 1, 1])
            unit = o_c1.radio("選擇單位", ["張 (1000股)", "股 (零股)"], key=f"unit_{idx}")
            qty = o_c2.number_input("輸入數量", min_value=1, value=1, key=f"qty_{idx}")
            actual_shares = qty * 1000 if "張" in unit else qty
            
            if o_c3.button("執行買入", key=f"buy_btn_{idx}"):
                if db and cur_c != "連線中..." and cur_c != "尚未有持股客戶":
                    # 直接寫入雲端
                    db.append_row([cur_c, s['id'], s['name'], price, actual_shares])
                    st.toast(f"✅ {s['name']} 已加入 {cur_c} 持股")
                    st.rerun()

with col_r:
    st.subheader(f"💼 {cur_c} 投資組合 (台幣損益)")
    total_twd_pnl = 0
    df_current = get_cloud_data()
    
    if not df_current.empty and cur_c in df_current['client'].values:
        # 過濾該客戶持股，排除 INIT 標記
        my_stocks = df_current[(df_current['client'] == cur_c) & (df_current['id'] != "INIT")]
        
        if my_stocks.empty:
            st.info("目前尚無持股部位")
        else:
            for i, row in my_stocks.iterrows():
                # 獲取即時行情 (用於損益計算)
                cp, _, cc, _, a_info = get_stock_perf(row['id'], 0)
                twd_pnl = (cp - row['buy_price']) * row['shares']
                total_twd_pnl += twd_pnl
                pnl_pct = (cp / row['buy_price'] - 1) * 100 if row['buy_price'] > 0 else 0
                
                # 顯示持股明細
                c1, c2, c3 = st.columns([2, 2, 1])
                with c1:
                    st.markdown(f"**{row['name']}** <span class='{a_info[1]}'>{a_info[0]}</span>", unsafe_allow_html=True)
                    st.write(f"{row['shares']} 股")
                
                with c2:
                    p_color = "red" if twd_pnl >= 0 else "green"
                    st.markdown(f"損益: <span style='color:{p_color}; font-weight:bold;'>NT$ {twd_pnl:,.0f}</span>", unsafe_allow_html=True)
                    st.write(f"現價: {cp} ({pnl_pct:+.2f}%)")
                
                # 個別刪除/減倉按鍵
                with c3:
                    del_pop = st.popover("⚙️")
                    d_qty = del_pop.number_input("減持股數", min_value=1, max_value=int(row['shares']), value=int(row['shares']), key=f"dq_r_{i}")
                    if del_pop.button("確認執行", key=f"db_r_{i}"):
                        # 換算回雲端表單行號 (索引 i 從 0 開始，+2 補償標題與位移)
                        # 注意：此處需根據 row 原有的資料庫 index 處理更精確
                        target_row = i + 2
                        if d_qty >= row['shares']:
                            db.delete_rows(int(target_row))
                        else:
                            new_shares = int(row['shares'] - d_qty)
                            db.update_cell(target_row, 5, new_shares)
                        st.rerun()
                st.divider()
            
            # 總損益統計
            total_color = "red" if total_twd_pnl >= 0 else "green"
            st.markdown(f"### 帳戶總損益: <span style='color:{total_color};'>NT$ {total_twd_pnl:,.0f}</span>", unsafe_allow_html=True)
            if st.button("🚨 清空該客戶所有持股"):
                # 倒序刪除避免行號跑掉
                for idx in reversed(my_stocks.index.tolist()):
                    db.delete_rows(idx + 2)
                st.rerun()
    else:
        st.info("請先在左側建立帳戶並執行買入")

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
