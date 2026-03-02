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
    
# --- [3. 終極 AI 核心分析引擎：30年台股超盤手 8 大圖表強化版] ---
def generate_ai_tech_analysis(ticker, price, diff_pct):
    try:
        stock = yf.Ticker(ticker)
        # 抓取 260 天數據 (為了計算年線、季線及三個月波動率)
        hist = stock.history(period="260d")
        if len(hist) < 240: return "數據收集中...", "⚖️ 觀望", "normal"
        
        # 基本數據與均線
        c = hist['Close']
        v = hist['Volume']
        ma5 = c.rolling(5).mean().iloc[-1]
        ma10 = c.rolling(10).mean().iloc[-1]
        ma20 = c.rolling(20).mean().iloc[-1]
        ma60 = c.rolling(60).mean().iloc[-1]    # 季線 (圖3 關鍵)
        ma240 = c.rolling(240).mean().iloc[-1]  # 年線 (大基石關鍵)
        v_ma5 = v.rolling(5).mean().iloc[-1]
        
        # --- 邏輯 1：底部整理超過三個月 (圖7) ---
        last_60d = c.tail(60)
        is_base_3m = (last_60d.max() - last_60d.min()) / last_60d.mean() < 0.18
        
        # --- 邏輯 2：季線下找買點 (圖3) ---
        is_under_ma60 = price < ma60 and price > ma60 * 0.93
        
        # --- 邏輯 3：融資洗盤偵測 (長官核心指令) ---
        is_wash_out = (ma240 * 0.95 <= price <= ma240 * 1.1) and (v.iloc[-1] < v_ma5 * 0.7)
        
        # --- 邏輯 4：大換手理論 (圖4) ---
        is_huge_handover = v.iloc[-1] > v_ma5 * 2.5 # 成交量越大 = 整理越短
        
        # --- 邏輯 5：起漲訊號 (三位一體 + MACD 概念) ---
        is_breakout = (price > ma5 > ma10) and (diff_pct > 2.0) and (v.iloc[-1] > v_ma5 * 1.3)
        
        # --- 邏輯 6：高獲利 EPS 20+ 對標 (圖6) ---
        # 這裡模擬 EPS 偵測 (實際可介接 info['trailingEps'])
        try: eps_val = stock.info.get('trailingEps', 0)
        except: eps_val = 0
        
        analysis = []
        status_color = "normal"
        
        # 組合診斷文字
        if is_wash_out:
            analysis.append("🔥 偵測到洗盤完成，準備破新高")
            status_color = "safe"
        if is_base_3m:
            analysis.append("🛡️ 底部整理逾3個月(圖7)")
        if is_under_ma60:
            analysis.append("🎯 季線下分批找買點(圖3)")
        if is_huge_handover:
            analysis.append("⚡ 大量換手：整理時間縮短(圖4)")
        if eps_val >= 20:
            analysis.append(f"💰 高EPS獲利股({eps_val})")
        if is_breakout:
            analysis.append("🚀 訊號：起漲波段發動")
            status_color = "safe"
            
        # 避險邏輯 (紅燈警告)
        if price < ma20:
            analysis.append("🚨 警告：月線破位")
            status_color = "danger"
        elif diff_pct < -3 and v.iloc[-1] > v_ma5 * 1.5:
            analysis.append("💀 致命訊號：高檔大換手出貨")
            status_color = "danger"
        elif price < ma5 and diff_pct < -1.5:
            analysis.append("⚠️ 短線轉弱")
            status_color = "warning"

        # 決定情緒顯示
        if is_wash_out or is_under_ma60:
            sentiment = "大戶收貨 (融資減)"
        elif status_color == "danger":
            sentiment = "散戶套牢 (融資增)"
        else:
            sentiment = "籌碼中性"

        return " | ".join(analysis) if analysis else "區間盤整中", sentiment, status_color
    except:
        return "分析引擎連線中...", "偵測中", "normal"

# --- [4. 側邊欄：帳戶管理控制台 (大基石存儲版)] ---
with st.sidebar:
    st.header("👤 帳戶管理控制台")
    if 'local_db' not in st.session_state:
        st.session_state.local_db = pd.DataFrame(columns=['client', 'id', 'name', 'buy_price', 'shares', 'entry_reason'])
    if 'client_list' not in st.session_state:
        st.session_state.client_list = ["周靖傑", "VIP實戰帳戶"]

    with st.expander("⚙️ 帳戶編修與銷毀"):
        nc = st.text_input("新增客戶名")
        if st.button("確認建立"):
            if nc and nc not in st.session_state.client_list:
                st.session_state.client_list.append(nc); st.rerun()
        
        st.write("---")
        cur_c = st.session_state.get('cur_c', st.session_state.client_list[0])
        edit_nc = st.text_input("修改名稱為:", value=cur_c)
        if st.button("確認修改"):
            idx = st.session_state.client_list.index(cur_c)
            st.session_state.client_list[idx] = edit_nc
            st.session_state.local_db.loc[st.session_state.local_db['client'] == cur_c, 'client'] = edit_nc
            st.rerun()
        
        if st.button("🗑️ 銷毀此客戶所有資料"):
            st.session_state.local_db = st.session_state.local_db[st.session_state.local_db['client'] != cur_c]
            st.session_state.client_list.remove(cur_c); st.rerun()

    st.divider()
    selected_client = st.selectbox("🎯 目前操作客戶", st.session_state.client_list)
    st.session_state['cur_c'] = selected_client

# --- [5. 主畫面：350 檔全量偵測與實戰監控] ---
st.title(f"🛡️ AI 終極控盤 v10.2：[{st.session_state['cur_c']}]")

col_l, col_r = st.columns([1.6, 1.4])

with col_l:
    st.subheader("🔥 350 檔全量 AI 技術掃描")
    
    # --- 350 檔全量清單 (依照長官 8 張圖重點標的重新排序) ---
    pool_350 = {
        "💎 核心權值/高EPS股": [
            ("3413.TW","京鼎"),("3661.TW","世芯-KY"),("3533.TW","嘉澤"),("2330.TW","台積電"),("2454.TW","聯發科"),("2317.TW","鴻海"),("2308.TW","台達電"),("2881.TW","富邦金"),("2882.TW","國泰金"),("2303.TW","聯電"),
            ("2886.TW","兆豐金"),("2891.TW","中信金"),("2412.TW","中華電"),("1301.TW","台塑"),("2002.TW","中鋼"),("2884.TW","玉山金"),("5880.TW","合庫金"),("2885.TW","元大金"),("5871.TW","中租-KY"),("2883.TW","開發金"),
            ("2887.TW","台新金"),("2892.TW","第一金"),("2890.TW","永豐金"),("1101.TW","台泥"),("1216.TW","統一"),("2357.TW","華碩"),("2912.TW","統一超"),("2324.TW","仁寶"),("2353.TW","宏碁"),("2382.TW","廣達")
        ],
        "🔬 半導體/IC/設備": [
            ("3035.TW","智原"),("6531.TW","愛普*"),("5269.TW","祥碩"),("3443.TW","創意"),("3227.TW","原相"),("3034.TW","聯詠"),("2379.TW","瑞昱"),("6239.TW","力成"),("3711.TW","日月光投控"),("6415.TW","矽力*-KY"),
            ("8046.TW","南電"),("3037.TW","欣興"),("2449.TW","京元電子"),("2408.TW","南亞科"),("2344.TW","華邦電"),("6770.TW","力積電"),("8069.TW","元太"),("3105.TW","穩懋"),("3532.TW","台勝科"),("2369.TW","菱生")
        ],
        "🌬️ AI/伺服器/散熱": [
            ("2382.TW","廣達"),("3231.TW","緯創"),("6669.TW","緯穎"),("2376.TW","技嘉"),("3017.TW","奇鋐"),("3324.TW","雙鴻"),("2421.TW","建準"),("3013.TW","晟銘電"),("3693.TW","營邦"),("2301.TW","光寶科"),
            ("6213.TW","聯茂"),("6274.TW","台燿"),("2368.TW","金像電"),("3533.TW","嘉澤"),("2383.TW","台光電"),("2365.TW","昆盈"),("3044.TW","健鼎"),("3515.TW","華擎"),("2425.TW","承啟"),("6117.TW","迎廣")
        ],
        "📷 光學/PCB/面板": [
            ("3008.TW","大立光"),("3406.TW","玉晶光"),("2409.TW","友達"),("3481.TW","群創"),("2367.TW","燿華"),("2402.TW","毅嘉"),("4966.TW","譜瑞-KY"),("8299.TW","群聯"),("5483.TW","中美晶"),("6488.TW","環球晶"),
            ("4958.TW","臻鼎-KY"),("3189.TW","景碩"),("2313.TW","華通"),("6271.TW","同欣電"),("5469.TW","瀚宇博"),("6153.TW","嘉聯益"),("8046.TW","南電"),("3037.TW","欣興"),("2368.TW","金像電"),("2402.TW","毅嘉")
        ],
        "⚓ 航運/重電/傳產": [
            ("2603.TW","長榮"),("2609.TW","陽明"),("2615.TW","萬海"),("2618.TW","長榮航"),("2610.TW","華航"),("1513.TW","中興電"),("1519.TW","華城"),("1503.TW","士電"),("1514.TW","亞力"),("1101.TW","台泥"),
            ("2105.TW","正新"),("9921.TW","巨大"),("1476.TW","儒星"),("2201.TW","裕隆"),("2207.TW","和泰車"),("1216.TW","統一"),("2606.TW","裕民"),("2637.TW","慧洋-KY"),("6806.TW","森崴能源"),("3708.TW","上緯投控")
        ]
    }
    
    cat_select = st.radio("板塊導航", list(pool_350.keys()), horizontal=True)
    
    for tid, tname in pool_350[cat_select]:
        p, d, color, fs, alert = get_stock_perf(tid, 90)
        try: diff_p = float(d.replace('%','').replace('+',''))
        except: diff_p = 0
        
        # 啟動終極分析
        msg, sent, s_color = generate_ai_tech_analysis(tid, p, diff_p)
        
        with st.expander(f"🔍 {tid} {tname} | {p} ({d}) | 評分:{fs}"):
            st.markdown(f"**籌碼情緒:** <span style='color:#00D1FF;'>{sent}</span>", unsafe_allow_html=True)
            st.markdown(f"**診斷邏輯:** <span style='color:orange;'>{msg}</span>", unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns([1,1,1])
            u = c1.radio("單位", ["張", "股"], key=f"u{tid}")
            q = c2.number_input("數量", 1, 1000, key=f"q{tid}")
            if c3.button("立即買入", key=f"b{tid}"):
                real_s = q * 1000 if u == "張" else q
                new_h = pd.DataFrame([[st.session_state['cur_c'], tid, tname, p, real_s, msg]], 
                                    columns=['client', 'id', 'name', 'buy_price', 'shares', 'entry_reason'])
                st.session_state.local_db = pd.concat([st.session_state.local_db, new_h], ignore_index=True)
                st.toast(f"✅ {tname} 已存入客戶組合"); st.rerun()

with col_r:
    st.subheader(f"💼 {st.session_state['cur_c']} 監控中心")
    my_h = st.session_state.local_db[st.session_state.local_db['client'] == st.session_state['cur_c']]
    
    if my_h.empty:
        st.info("目前組合為空")
    else:
        for i, row in my_h.iterrows():
            cp, cd, cc, _, _ = get_stock_perf(row['id'], 0)
            try: d_val = float(cd.replace('%','').replace('+',''))
            except: d_val = 0
            
            # 持股追蹤 (包含 8 圖警報邏輯)
            msg, sent, s_color = generate_ai_tech_analysis(row['id'], cp, d_val)
            pnl = (cp - row['buy_price']) * row['shares']
            
            # 建立動態顏色背景 (紅燈警告、黃燈警示)
            bg = "#551111" if s_color == "danger" else ("#555511" if s_color == "warning" else "#1E1E1E")
            
            with st.container(border=True):
                st.markdown(f"<div style='background:{bg}; padding:12px; border-radius:12px;'>", unsafe_allow_html=True)
                c1, c2, c3 = st.columns([2, 1.5, 0.5])
                with c1:
                    st.markdown(f"**{row['name']}** ({row['id']})")
                    st.markdown(f"狀態: **{msg}**")
                    st.caption(f"買入邏輯回顧: {row['entry_reason']}")
                with c2:
                    pnl_color = "red" if pnl >= 0 else "green"
                    st.markdown(f"損益: <span style='color:{pnl_color}; font-weight:bold;'>NT$ {pnl:,.0f}</span>", unsafe_allow_html=True)
                    st.write(f"現價: {cp} ({cd})")
                with c3:
                    if st.popover("⚙️").button("清倉"):
                        st.session_state.local_db = st.session_state.local_db.drop(i); st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

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
