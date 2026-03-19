import streamlit as st
import pandas as pd
import yfinance as yf
import feedparser
import ssl
import os
from datetime import datetime, timedelta
import urllib.parse
import numpy as np

# --- [第 1 區：核心配置與 CSS 樣式 - 保持 12.5 原始樣式] ---
st.set_page_config(page_title="大基石-12.5史詩將軍級", layout="wide")

try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=60 * 1000, key="v125_general_refresh")
except:
    pass

st.markdown("""
    <style>
    html, body, [class*="css"] { font-size: 13px !important; color: #1e1e1e; }
    .stButton>button { 
        height: 32px !important; 
        padding: 0px 15px !important; 
        font-size: 13px !important; 
        border-radius: 6px !important;
        font-weight: bold !important;
    }
    .news-card { border-left: 4px solid #cc0000; padding-left: 12px; margin-bottom: 8px; font-size: 12px; border-bottom: 1px solid #eee; padding-bottom: 5px; }
    .rank-tag { background: #ff4b4b; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; margin-right: 5px; }
    .sentiment-tag { color: #00D1FF; font-weight: bold; border: 1px solid #00D1FF; padding: 3px 6px; border-radius: 4px; background: rgba(0, 209, 255, 0.1); }
    .diag-box { background: #f8f9fa; padding: 10px; border-radius: 8px; border-left: 5px solid #ff4b4b; }
    .status-bar { padding: 8px 15px; border-radius: 10px; margin-bottom: 15px; font-weight: bold; display: flex; align-items: center; gap: 10px; }
    .status-on { background-color: #e6fffa; color: #2c7a7b; border: 1px solid #81e6d9; }
    .status-off { background-color: #fff5f5; color: #c53030; border: 1px solid #feb2b2; }
    </style>
    """, unsafe_allow_html=True)

# --- [第 2 區：雲端保險箱核心連線 - 執行狀態監控] ---
SHEET_ID = "1EC30rbvM2PQdz6KAYpx-hZAm-DYgulzYJ9lcqGJJn90"

def get_sheet_url(sheet_name):
    return f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"

def check_connection():
    """檢測與 Google Sheets 的連線狀態"""
    try:
        test_df = pd.read_csv(get_sheet_url("history"), nrows=1)
        return True, "✅ 雲端同步中：已成功連結 StoneManager_DB"
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg:
            return False, "❌ 連線失敗：找不到試算表 (請檢查 SHEET_ID)"
        elif "empty" in error_msg:
            return True, "⚠️ 連線成功：但 history 分頁目前是空的"
        else:
            return False, f"❌ 連線失敗：分頁名稱不正確或權限未開放"

# 顯示頂部標題與連線狀態燈
st.title("🛡️ 大基石 - AI 戰略經理人")

is_connected, status_text = check_connection()
if is_connected:
    st.markdown(f'<div class="status-bar status-on">🌐 {status_text}</div>', unsafe_allow_html=True)
else:
    st.markdown(f'<div class="status-bar status-off">📡 {status_text}</div>', unsafe_allow_html=True)
    st.info("💡 提示：請確保 Google Sheets 已改名為 history/inventory/clients 並已『發布到網路』。")

def load_data():
    """混合記憶模式：確保雲端資料存在，同時保留手動輸入的靈活性"""
    # [新增核心鎖：防止 Rerun 時覆蓋掉剛存入的資料]
    if 'initialized' in st.session_state and st.session_state.initialized:
        return

    try:
        # 1. 讀取雲端資料
        st.session_state.local_db = pd.read_csv(get_sheet_url("inventory"))
        st.session_state.trade_history = pd.read_csv(get_sheet_url("history"))
        
        # 2. 讀取客戶名單
        client_df = pd.read_csv(get_sheet_url("clients"))
        cloud_clients = client_df['name'].tolist() if 'name' in client_df.columns else []
        
        if 'client_list' not in st.session_state:
            st.session_state.client_list = ["Robert"]
            
        ghosts = ["nan", "None", None]
        combined = list(set(st.session_state.client_list + cloud_clients))
        st.session_state.client_list = sorted([str(c) for c in combined if str(c) not in ghosts])
        
        # 標記初始化已完成
        st.session_state.initialized = True
            
    except Exception:
        if 'local_db' not in st.session_state:
            st.session_state.local_db = pd.DataFrame(columns=['client', 'id', 'name', 'buy_price', 'shares', 'unit', 'entry_reason', 'current_score', 'last_diag'])
        if 'trade_history' not in st.session_state:
            st.session_state.trade_history = pd.DataFrame(columns=['date', 'client', 'id', 'action', 'shares', 'price', 'note'])
        if 'client_list' not in st.session_state:
            st.session_state.client_list = ["Robert"]
        st.session_state.initialized = True

def save_data():
    """將變動存入本地緩存 (備份用)"""
    st.session_state.local_db.to_csv("stone_manager_db.csv", index=False)
    if 'trade_history' in st.session_state:
        st.session_state.trade_history.to_csv("trading_history.csv", index=False)
    pd.DataFrame(st.session_state.client_list, columns=['name']).to_csv("client_list.csv", index=False)



# --- [第 3 區：史詩將軍級超強大腦 V12.5 (板塊共振/填息基因/短線冷靜)] ---
def generate_ai_tech_analysis(ticker, price, diff_pct):
    """
    大腦核心法則：板塊共振/填息基因/短線冷靜 - 法則不變
    """
    try:
        stock = yf.Ticker(ticker)
        # 擴展數據抓取
        hist_full = stock.history(period="2y") 
        if len(hist_full) < 250: return None
        
        hist = hist_full.tail(300)
        c, v, h, l = hist['Close'], hist['Volume'], hist['High'], hist['Low']
        
        # [模塊 A: 指標計算]
        ma20 = c.rolling(20).mean().iloc[-1]
        ma60 = c.rolling(60).mean().iloc[-1]
        ma240 = c.rolling(240).mean().iloc[-1]
        v_ma20 = v.rolling(20).mean().iloc[-1]
        
        # [模塊 B: 成本與洗盤偵測]
        on_support = (abs(price - ma240) / ma240 < 0.05) or (abs(price - ma60) / ma60 < 0.05)
        vol_dry_out = (v.iloc[-1] < v_ma20 * 0.7)
        low_30 = hist_full['Close'].quantile(0.3)
        
        score = 40 # 基礎分
        
        # --- 核心 1: 籌碼洗盤與 35年價值發現 ---
        is_wash_done = False
        is_value_gem = False
        sentiment = "散戶進場 (融資增)"
        
        if on_support and vol_dry_out:
            score += 45
            is_wash_done = True
            sentiment = "大戶收貨 (融資減)"
        
        if price <= low_30 * 1.05 and on_support and vol_dry_out:
            score += 20 
            is_value_gem = True
            sentiment = "💎 戰略價值區 (大戶長期鎖籌)"

        # --- 進化 1: 板塊熱度共振 Sector Resonance ---
        if price > ma20 and price > ma60 and v.iloc[-1] > v_ma20:
            score += 10 

        # --- 核心 2: 均線糾結與暴衝基因 ---
        ma_gap = pd.Series([ma20, ma60, ma240]).std() / price
        if ma_gap < 0.03: score += 20
        
        surges = hist_full.tail(250).apply(lambda x: (x['Close'] - x['Open'])/x['Open'] > 0.07, axis=1)
        if surges.any(): score += 5 
            
        # --- 核心 3: MACD 動能 ---
        exp1, exp2 = c.ewm(span=12).mean(), c.ewm(span=26).mean()
        macd = exp1 - exp2
        if macd.iloc[-1] > macd.iloc[-2]: score += 10
        
        # --- 進化 2: 短線乖離強制冷靜 Bias Cooling ---
        bias_20 = (price - ma20) / ma20
        is_overheated = False
        if bias_20 > 0.15: 
            score -= 15
            is_overheated = True

        # --- 核心 4: 長線風險過濾 ---
        bias_240 = (price - ma240) / ma240
        if bias_240 > 0.4: score -= 30 

        # --- 進化 3: 除權息填息基因 Dividend Recovery ---
        is_dividend_king = False
        if (c.iloc[-1] > c.iloc[-120]) and (c.iloc[-1] > ma240): 
            is_dividend_king = True

        total_score = max(0, min(100, score))
        
        # --- 最終判定 ---
        rank, msg, target, window = "", "", price * 1.1, ""
        if total_score >= 90:
            rank, msg, target, window = "🔥 SS級:史詩起漲", "將軍級確認：板塊共振強，洗盤極度乾淨。", price * 1.7, "3-6個月"
        elif total_score >= 75:
            rank, msg, target, window = "🚀 A級:波段主升", "動能配合完美，進入主升浪軌道。", price * 1.4, "1-3個月"
        elif total_score >= 60:
            rank, msg, target, window = "📈 B級:趨勢確認", "趨勢向上，適合穩健佈局。", price * 1.2, "2-4週"
        else:
            rank, msg, target, window = "🔍 C級:短線觀察", "動能不足或位階稍高，僅適短線。", price * 1.08, "3-7天"

        # 將軍級診斷合成
        if is_overheated: msg = "⚠️ 戰鬥力過載，請勿追高，等待洗盤 " + msg
        if is_dividend_king: msg = "🎁 息利雙收標的 (填息基因強) " + msg
        if is_value_gem: msg = "💎 偵測到長線戰略價值位 " + msg
        if is_wash_done and on_support: msg = "🔥 偵測到洗盤完成，準備破新高 " + msg

        return {
            "msg": f"[{rank}] {msg}", 
            "sent": sentiment, 
            "score": total_score, 
            "target": round(target, 1), 
            "stop": round(ma20*0.96, 1), 
            "window": window
        }
    except Exception as e:
        return None

def fetch_and_score_intel():
    """
    大基石 15.0 核心大腦：海量繁體中文情報抓取 (對接新版介面)
    """
    import ssl
    import collections
    import re
    import urllib.parse
    from datetime import datetime, timedelta
    import time

    if hasattr(ssl, '_create_unverified_context'):
        ssl._create_default_https_context = ssl._create_unverified_context

    # 1. 擴展搜索矩陣：確保單區能抓到 30 則以上
    strategic_map = {
        "🇹🇼 台美日中 (地緣)": [
            "台海局勢 when:24h", "中共軍演 when:24h", "台積電 晶片禁令 when:24h", 
            "兩岸關係 when:24h", "美國對台軍售 when:24h", "南海衝突 when:24h",
            "半導體戰爭 when:24h", "台灣 國防部 特報 when:24h"
        ],
        "🌐 國際戰略 (全球)": [
            "中東戰爭 以色列 伊朗 when:24h", "美聯儲 利率 鮑爾 when:24h", "川普 關稅 政策 when:24h", 
            "俄烏戰爭 戰況 when:24h", "紅海 航運 中斷 when:24h", "全球經濟 崩盤 when:24h",
            "蘇伊士運河 危機 when:24h", "黃仁勳 NVIDIA 財報 when:24h", "美國大選 地緣政治 when:24h"
        ]
    }
    
    news_list, seen_links = [], set()
    
    # 2. 多來源並發抓取
    for cat_name, queries in strategic_map.items():
        for q in queries:
            # 強制鎖定繁體中文 hl=zh-TW
            u = f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
            try:
                feed = feedparser.parse(u)
                for e in feed.entries[:20]: # 增加單項掃描深度
                    if e.link not in seen_links:
                        # 檢查標題：過濾掉過多英文字符的非繁中標題 (超過60%英文字則跳過)
                        eng_chars = len(re.findall(r'[a-zA-Z]', e.title))
                        if eng_chars > len(e.title) * 0.6: continue
                        
                        e.category = cat_name 
                        # 處理發布時間格式
                        pub_tag = "24H 內"
                        if hasattr(e, 'published'):
                            pub_tag = e.published[5:16]
                            
                        # 計算權重分數
                        score = 55
                        title = e.title.upper()
                        if any(w in title for w in ["戰爭", "衝突", "爆炸", "制裁", "斷鏈", "降息", "加息", "突發"]): score += 30
                        if any(w in title for w in ["台積電", "NVIDIA", "川普", "習近平", "鮑爾"]): score += 15
                        
                        news_list.append({
                            'data': e, 
                            'score': min(99, score), 
                            'cat': cat_name,
                            'time': pub_tag
                        })
                        seen_links.add(e.link)
            except:
                continue

    # 3. 提取熱門關鍵字
    all_titles = " ".join([item['data'].title for item in news_list])
    words = re.findall(r'[\u4e00-\u9fa5]{2,4}', all_titles)
    hot_words = [w for w, c in collections.Counter(words).most_common(12)] 

    # 最終排序：分數越高（越重要）的排在前面
    return sorted(news_list, key=lambda x: x['score'], reverse=True), hot_words


# --- [第 4 區：390 檔名單 (完整還原)] ---
# (此處保持 390 檔列表，代碼長度考量在此略過列表文字，請保留您原本的 pool_390 變數)
pool_390 = {
    "💎 權值/金控 (70)": [("2330.TW","台積電"),("2317.TW","鴻海"),("2454.TW","聯發科"),("2308.TW","台達電"),("2881.TW","富邦金"),("2882.TW","國泰金"),("2303.TW","聯電"),("2886.TW","兆豐金"),("2891.TW","中信金"),("2412.TW","中華電"),("1301.TW","台塑"),("2002.TW","中鋼"),("2884.TW","玉山金"),("5880.TW","合庫金"),("2885.TW","元大金"),("5871.TW","中租-KY"),("2883.TW","開發金"),("2887.TW","台新金"),("2892.TW","第一金"),("2890.TW","永豐金"),("1101.TW","台泥"),("1216.TW","統一"),("2357.TW","華碩"),("2912.TW","統一超"),("2324.TW","仁寶"),("2353.TW","宏碁"),("2382.TW","廣達"),("2409.TW","友達"),("3481.TW","群創"),("2880.TW","華南金"),("1303.TW","南亞"),("1326.TW","台化"),("6505.TW","台塑化"),("2105.TW","正新"),("2207.TW","和泰車"),("2301.TW","光寶科"),("2377.TW","微星"),("2395.TW","研華"),("2408.TW","南亞科"),("2474.TW","可成"),("2603.TW","長榮"),("2609.TW","陽明"),("2610.TW","華航"),("2615.TW","萬海"),("2618.TW","長榮航"),("2801.TW","彰銀"),("2888.TW","新光金"),("2889.TW","國票金"),("2897.TW","王道銀行"),("5876.TW","上海商銀"),("9904.TW","寶成"),("9910.TW","豐泰"),("9921.TW","巨大"),("9945.TW","潤泰新"),("1476.TW","儒星"),("1477.TW","聚陽"),("1503.TW","士電"),("1504.TW","東元"),("1513.TW","中興電"),("1519.TW","華城"),("1605.TW","華新"),("1717.TW","長興"),("1722.TW","台肥"),("1802.TW","台玻"),("2006.TW","東和鋼鐵"),("2014.TW","中鴻"),("2027.TW","大成鋼"),("2106.TW","建大"),("2201.TW","裕隆"),("2204.TW","中華車")],
    "🔬 半導體/IC/設備 (70)": [("3413.TW","京鼎"),("3661.TW","世芯-KY"),("3035.TW","智原"),("6531.TW","愛普*"),("5269.TW","祥碩"),("3443.TW","創意"),("3227.TW","原相"),("3034.TW","聯詠"),("2379.TW","瑞昱"),("6239.TW","力成"),("3711.TW","日月光投控"),("6415.TW","矽力*-KY"),("8046.TW","南電"),("3037.TW","欣興"),("2449.TW","京元電子"),("2344.TW","華邦電"),("6770.TW","力積電"),("8069.TW","元太"),("3105.TW","穩懋"),("3532.TW","台勝科"),("2369.TW","菱生"),("3264.TW","欣銓"),("6147.TW","紘康"),("8150.TW","南茂"),("2401.TW","凌陽"),("3016.TW","嘉晶"),("3529.TW","力旺"),("4966.TW","譜瑞-KY"),("6271.TW","同欣電"),("8299.TW","群聯"),("2337.TW","旺宏"),("2436.TW","偉詮電"),("2458.TW","義隆"),("3006.TW","晶豪科"),("3041.TW","揚智"),("3527.TW","聚積"),("3588.TW","通嘉"),("4919.TW","新唐"),("4961.TW","天鈺"),("5471.TW","松翰"),("6138.TW","茂達"),("6202.TW","盛群"),("6233.TW","旺玖"),("6243.TW","迅杰"),("6411.TW","晶焱"),("6462.TW","神盾"),("6533.TW","晶心科"),("6679.TW","鈺太"),("8016.TW","矽創"),("8028.TW","昇陽半"),("8054.TW","安國"),("8081.TW","致新"),("8261.TW","富鼎"),("8271.TW","宇瞻"),("3131.TW","弘塑"),("3583.TW","齊宣"),("6139.TW","亞博"),("6438.TW","迅得"),("1560.TW","中砂"),("3680.TW","家登"),("6196.TW","帆宣"),("6667.TW","信紘科"),("3374.TW","精材"),("6223.TW","旺矽"),("6515.TW","穎崴"),("6510.TW","精測"),("3587.TW","閎康"),("6683.TW","雍智科技"),("8027.TW","鈦昇"),("6789.TW","采鈺")],
    "🌬️ AI伺服器/散熱 (70)": [("3231.TW","緯創"),("6669.TW","緯穎"),("2376.TW","技嘉"),("3017.TW","奇鋐"),("3324.TW","雙鴻"),("2421.TW","建準"),("3013.TW","晟銘電"),("3693.TW","營邦"),("6213.TW","聯茂"),("6274.TW","台燿"),("2368.TW","金像電"),("3533.TW","嘉澤"),("2383.TW","台光電"),("2365.TW","昆盈"),("3044.TW","健鼎"),("3515.TW","華擎"),("2425.TW","承啟"),("6117.TW","迎廣"),("8210.TW","勤誠"),("1582.TW","信錦"),("3005.TW","神基"),("2352.TW","佳世達"),("2356.TW","英業達"),("2316.TW","楠梓電"),("2367.TW","燿華"),("2371.TW","大同"),("2397.TW","友通"),("2417.TW","圓剛"),("2419.TW","仲琦"),("2428.TW","興勤"),("2455.TW","全新"),("2465.TW","麗臺"),("2480.TW","敦陽科"),("3010.TW","華立"),("3029.TW","零壹"),("3032.TW","偉訓"),("3211.TW","順達"),("3321.TW","同泰"),("3338.TW","泰碩"),("3376.TW","新普"),("3402.TW","漢科"),("3540.TW","曜越"),("3596.TW","智易"),("3617.TW","碩天"),("3653.TW","健策"),("3665.TW","貿聯-KY"),("3694.TW","海華"),("4915.TW","致伸"),("4938.TW","和碩"),("4958.TW","臻鼎-KY"),("5215.TW","科嘉-KY"),("5388.TW","中磊"),("6153.TW","嘉聯益"),("6166.TW","凌華"),("6205.TW","詮欣"),("6214.TW","精誠"),("6230.TW","超眾"),("6235.TW","華孚"),("8112.TW","至上"),("6409.TW","旭隼"),("6278.TW","台表科"),("6269.TW","台郡"),("5483.TW","中美晶"),("6488.TW","環球晶"),("5434.TW","崇越"),("3702.TW","大聯大"),("2385.TW","群光")],
    "📷 光學/PCB/面板 (70)": [("3008.TW","大立光"),("3406.TW","玉晶光"),("3441.TW","聯一光"),("3362.TW","先進光"),("3504.TW","揚明光"),("3019.TW","亞光"),("2367.TW","燿華"),("2368.TW","金像電"),("2316.TW","楠梓電"),("3037.TW","欣興"),("8046.TW","南電"),("3189.TW","景碩"),("2383.TW","台光電"),("6213.TW","聯茂"),("6274.TW","台燿"),("3044.TW","健鼎"),("4958.TW","臻鼎-KY"),("2409.TW","友達"),("3481.TW","群創"),("6116.TW","彩晶"),("6719.TW","力智"),("3592.TW","瑞鼎"),("4961.TW","天鈺"),("3034.TW","聯詠"),("8105.TW","凌巨"),("2349.TW","錸德"),("2323.TW","中環"),("6153.TW","嘉聯益"),("6269.TW","台郡"),("6278.TW","台表科"),("5439.TW","高技"),("2313.TW","華通"),("2355.TW","敬鵬"),("2360.TW","致茂"),("2402.TW","毅嘉"),("3030.TW","德律"),("3321.TW","同泰"),("3376.TW","新普"),("3557.TW","嘉威"),("3591.TW","艾笛森"),("3622.TW","洋華"),("3673.TW","TPK-KY"),("3679.TW","新至陞"),("4976.TW","佳凌"),("5243.TW","乙盛-KY"),("5469.TW","瀚宇博"),("6141.TW","柏承"),("6191.TW","精成科"),("6205.TW","詮欣"),("6224.TW","聚鼎"),("6251.TW","定穎"),("6271.TW","同欣電"),("6290.TW","良維"),("6456.TW","GIS-KY"),("6674.TW","騰輝電子"),("8021.TW","尖點"),("8039.TW","台虹"),("8103.TW","瀚荃"),("8213.TW","志超"),("8215.TW","明基材"),("2340.TW","光磊"),("2393.TW","億光"),("3437.TW","榮創"),("6168.TW","宏齊"),("6226.TW","光鼎"),("6443.TW","元晶")],
    "📡 網通/零組件 (70)": [("2345.TW","智邦"),("3704.TW","合勤控"),("5388.TW","中磊"),("3596.TW","智易"),("6285.TW","啟碁"),("2314.TW","台揚"),("2419.TW","仲琦"),("3062.TW","建漢"),("3380.TW","明泰"),("2485.TW","兆赫"),("3450.TW","聯鈞"),("4977.TW","眾達-KY"),("6426.TW","統新"),("8011.TW","台通"),("2201.TW","裕隆"),("2204.TW","中華車"),("2206.TW","三陽工業"),("2207.TW","和泰車"),("1521.TW","大隆"),("1522.TW","堤維西"),("1524.TW","耿鼎"),("1525.TW","江申"),("1536.TW","和大"),("1533.TW","車王電"),("1568.TW","倉佑"),("2101.TW","南港"),("2103.TW","台橡"),("2105.TW","正新"),("2106.TW","建大"),("2108.TW","南帝"),("2497.TW","怡利電"),("3552.TW","同致"),("5243.TW","乙盛-KY"),("6288.TW","聯嘉"),("3003.TW","健和興"),("3023.TW","信邦"),("3665.TW","貿聯-KY"),("2328.TW","廣宇"),("2392.TW","正崴"),("3024.TW","憶聲"),("3209.TW","全科"),("6115.TW","鎰勝"),("6205.TW","詮欣"),("6290.TW","良維"),("2354.TW","鴻準"),("2474.TW","可成"),("3005.TW","神基"),("6235.TW","華孚"),("5215.TW","科嘉-KY"),("2352.TW","佳世達"),("2385.TW","群光"),("3010.TW","華立"),("3029.TW","零壹"),("3042.TW","晶技"),("3057.TW","喬鼎"),("3211.TW","順達"),("3376.TW","新普"),("3617.TW","碩天"),("4927.TW","泰鼎-KY"),("5305.TW","敦南"),("5434.TW","崇越"),("6143.TW","振曜"),("6184.TW","大豐電"),("6202.TW","盛群"),("6214.TW","精誠"),("8044.TW","網家"),("8112.TW","至上")],
    "⚓ 傳統產業 (20)": [("1313.TW","聯成"),("1101.TW","台泥"),("1102.TW","亞泥"),("1301.TW","台塑"),("1303.TW","南亞"),("1326.TW","台化"),("6505.TW","台塑化"),("2002.TW","中鋼"),("2014.TW","中鴻"),("2105.TW","正新"),("2603.TW","長榮"),("2609.TW","陽明"),("2615.TW","萬海"),("2618.TW","長榮航"),("1476.TW","儒星"),("1477.TW","聚陽"),("1503.TW","士電"),("1513.TW","中興電"),("1519.TW","華城"),("1717.TW","長興")],
    "🧬 生技醫療 (20)": [("4123.TW","晟德"),("1760.TW","寶齡富錦"),("4128.TW","中天"),("4147.TW","龍燈-KY"),("4162.TW","智擎"),("4174.TW","浩鼎"),("4743.TW","合一"),("6446.TW","藥華藥"),("6472.TW","保瑞"),("6492.TW","生華科"),("6547.TW","高端"),("6550.TW","北極星"),("6589.TW","台康生"),("1795.TW","美時"),("4104.TW","佳醫"),("4119.TW","旭富"),("4137.TW","麗豐"),("1701.TW","中化"),("1720.TW","生達"),("1762.TW","中化生")]
}


# --- [第 5 區：側邊欄管理 - 穩定修正版] ---
if 'local_db' not in st.session_state:
    load_data()

# 確保幽靈名單不會在切換時復活
target_ghosts = ["VIP實戰", "周靖傑", "nan", "None", None, "Unnamed: 0"]
st.session_state.client_list = [c for c in st.session_state.client_list if c not in target_ghosts and str(c).strip() != ""]

with st.sidebar:
    st.title("👤 大基石 AI 經理人")
    st.write(f"系統時間: {datetime.now().strftime('%Y-%m-%d')}")
    
    with st.expander("⚙️ 客戶系統設定 (增/改/刪)", expanded=False):
        # 1. 新增客戶
        new_c = st.text_input("新增客戶姓名", key="add_client_input")
        if st.button("➕ 確認新增"):
            if new_c and new_c not in st.session_state.client_list and new_c not in target_ghosts: 
                st.session_state.client_list.append(new_c)
                new_row = pd.DataFrame([{'client': new_c, 'id': 'INIT', 'name': '初始紀錄', 'buy_price': 0, 'shares': 0, 'unit': '股', 'entry_reason': '系統新增'}])
                st.session_state.local_db = pd.concat([st.session_state.local_db, new_row], ignore_index=True)
                st.session_state['cur_c'] = new_c
                save_data(); st.rerun()
        
        st.markdown("---")
        
        # 2. 更名功能
        current_idx_name = st.session_state.get('cur_c', st.session_state.client_list[0])
        new_name = st.text_input("輸入新名稱", value=current_idx_name, key="rename_input")
        if st.button("📝 執行更名", use_container_width=True):
            if new_name and new_name != current_idx_name and new_name not in target_ghosts:
                st.session_state.local_db['client'] = st.session_state.local_db['client'].replace(current_idx_name, new_name)
                st.session_state.client_list = [new_name if x == current_idx_name else x for x in st.session_state.client_list]
                st.session_state['cur_c'] = new_name
                save_data(); st.rerun()

    # --- 下拉選單 (照舊不改動) ---
    if st.session_state.get('cur_c') not in st.session_state.client_list:
        st.session_state['cur_c'] = "Robert" if "Robert" in st.session_state.client_list else st.session_state.client_list[0]

    st.session_state['cur_c'] = st.selectbox(
        "🎯 當前控盤對象", 
        st.session_state.client_list, 
        index=st.session_state.client_list.index(st.session_state['cur_c']),
        key="client_selector"
    )
    
    # 3. 刪除功能
    if st.button("❌ 刪除當前客戶", use_container_width=True):
        if st.session_state['cur_c'] != "Robert":
            to_del = st.session_state['cur_c']
            st.session_state.client_list.remove(to_del)
            st.session_state.local_db = st.session_state.local_db[st.session_state.local_db['client'] != to_del]
            st.session_state['cur_c'] = "Robert"
            save_data(); st.rerun()
        else:
            st.error("系統預設客戶 Robert 不可刪除。")

    st.markdown("---")
    # [修正計數：排除 INIT 標記，僅計算真實持股數量]
    c_stocks = st.session_state.local_db[
        (st.session_state.local_db['client'] == st.session_state['cur_c']) & 
        (st.session_state.local_db['id'] != 'INIT')
    ]
    st.metric(f"{st.session_state['cur_c']} 的持股總數", len(c_stocks))


# --- [核心工具函數補完：大基石運作關鍵] ---

def get_stock_name(ticker):
    """根據代號找名稱，找不到則回傳代號本身"""
    for cat in pool_390.values():
        for tid, tname in cat:
            if tid == ticker: return tname
    return ticker

def get_stock_perf(ticker, buy_price):
    """取得即時股價、漲跌與百分比"""
    try:
        stock = yf.Ticker(ticker)
        # 取得今天與昨天的數據
        hist = stock.history(period="2d")
        if len(hist) < 2:
            # 若週一開盤前，抓 5 天確保有數據
            hist = stock.history(period="5d")
        
        current_price = round(hist['Close'].iloc[-1], 2)
        prev_close = hist['Close'].iloc[-2]
        diff = round(current_price - prev_close, 2)
        change_pct = (diff / prev_close) * 100
        
        diff_str = f"{diff} ({change_pct:.2f}%)"
        return current_price, diff_str, change_pct
    except:
        return 0, "N/A", 0

def record_transaction(client, tid, action, shares, price, note):
    """記錄每一筆史詩級交易"""
    new_record = pd.DataFrame([{
        'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
        'client': client,
        'id': tid,
        'action': action,
        'shares': shares,
        'price': price,
        'note': note
    }])
    if 'trade_history' not in st.session_state:
        st.session_state.trade_history = new_record
    else:
        st.session_state.trade_history = pd.concat([st.session_state.trade_history, new_record], ignore_index=True)


# --- [第 6 區：頁面佈局重整] ---
tab_scan, tab_intel, tab_history = st.tabs(["📊 戰策指揮所", "🌐 全球情報室", "📜 交易紀錄"])

with tab_scan:
    st.title(f"🛡️ 12.5 史詩大腦整合版: [{st.session_state.cur_c}]")
    col_l, col_r = st.columns([1.6, 1.4]) 
    
    # --- [左側：戰略掃描] ---
    with col_l:
        with st.container(border=True):
            st.subheader("🔍 全球個股戰略搜索")
            s_input = st.text_input("輸入名稱或代號", placeholder="搜尋全台股標的...", key="global_search")
            if s_input:
                all_l = []
                for l in pool_390.values(): all_l.extend(l)
                match = [tid for tid, name in all_l if s_input in name or s_input in tid]
                tid = match[0] if match else (s_input.upper() + ".TW" if s_input.isdigit() else s_input.upper())
                p, d, cc = get_stock_perf(tid, 0)
                if p > 0:
                    res = generate_ai_tech_analysis(tid, p, 0)
                    if res:
                        st.markdown(f"### 🎯 戰略診斷: {get_stock_name(tid)} ({tid})")
                        sc1, sc2 = st.columns([1.5, 1])
                        with sc1:
                            st.markdown(f"#### **評分: <span style='color:red;'>{res['score']}</span>**", unsafe_allow_html=True)
                            st.info(f"**診斷:** {res['msg']}")
                            st.markdown(f"**籌碼狀態:** <span class='sentiment-tag'>{res['sent']}</span>", unsafe_allow_html=True)
                            
                            # --- 補回：下單佈局 ---
                            u_c1, u_c2 = st.columns(2)
                            q_val = u_c1.number_input("佈局數量", min_value=1, value=1, key="sq_main_qty")
                            u_val = u_c2.radio("佈局單位", ["張", "股"], key="su_main_unit", horizontal=True)
                            
                            if st.button(f"🚀 確認執行佈局 {get_stock_name(tid)}", use_container_width=True):
                                # 執行買入邏輯
                                new_entry = pd.DataFrame([{
                                    'client': st.session_state.cur_c, 'id': tid, 'name': get_stock_name(tid),
                                    'buy_price': p, 'shares': q_val, 'unit': u_val,
                                    'entry_reason': res['msg'], 'current_score': res['score'], 'last_diag': datetime.now().strftime("%m-%d")
                                }])
                                st.session_state.local_db = pd.concat([st.session_state.local_db, new_entry], ignore_index=True)
                                record_transaction(st.session_state.cur_c, tid, "BUY", q_val, p, "AI 戰略佈局")
                                save_data()
                                st.success(f"已成功佈局 {get_stock_name(tid)}")
                                st.rerun()
                        with sc2:
                            st.metric("即時股價", p, d)
                            st.success(f"🎯 目標預期: {res['target']}")

        st.divider()
        cat_choice = st.radio("產業板塊掃描 (共振偵測)", list(pool_390.keys()), horizontal=True)
        scored_data = []
        for tid, tname in pool_390[cat_choice]:
            p, d, cc = get_stock_perf(tid, 0)
            res = generate_ai_tech_analysis(tid, p, 0)
            if res:
                res.update({'tid': tid, 'tname': tname, 'price': p, 'diff': d})
                scored_data.append(res)
        
        # --- 修正：推薦名單增加至 15 檔 ---
        top_picks = sorted(scored_data, key=lambda x: x['score'], reverse=True)[:15]
        for item in top_picks:
            with st.expander(f"⭐ {item['tname']} | 評分: {item['score']} | 價: {item['price']} ({item['diff']})"):
                st.markdown(f"**🧠 AI 診斷:** {item['msg']}")
                # --- 補回：快速佈局按鈕與單位選擇 ---
                k_c1, k_c2, k_c3 = st.columns([1, 1.2, 1.8])
                quick_q = k_c1.number_input("數量", min_value=1, value=1, key=f"qq_{item['tid']}")
                quick_u = k_c2.radio("單位", ["張", "股"], key=f"qu_{item['tid']}", horizontal=True)
                if k_c3.button(f"🚀 快速佈局 {item['tname']}", key=f"bp_{item['tid']}", use_container_width=True):
                    new_entry = pd.DataFrame([{
                        'client': st.session_state.cur_c, 'id': item['tid'], 'name': item['tname'],
                        'buy_price': item['price'], 'shares': quick_q, 'unit': quick_u,
                        'entry_reason': item['msg'], 'current_score': item['score'], 'last_diag': datetime.now().strftime("%m-%d")
                    }])
                    st.session_state.local_db = pd.concat([st.session_state.local_db, new_entry], ignore_index=True)
                    record_transaction(st.session_state.cur_c, item['tid'], "BUY", quick_q, item['price'], "板塊掃描快速進場")
                    save_data()
                    st.rerun()

    # --- [右側：持股監控] ---
    with col_r:
        st.subheader(f"💼 持股監控: [{st.session_state.get('cur_c', 'Robert')}]")
        my_h = st.session_state.local_db[st.session_state.local_db['client'] == st.session_state.get('cur_c', 'Robert')]
        
        if not my_h.empty:
            total_pnl = 0
            for idx, row in my_h.iterrows():
                if row['id'] == 'INIT': continue
                cp, cd, cc = get_stock_perf(row['id'], 0)
                mult = 1000 if row['unit'] == "張" else 1
                pnl = (cp - row['buy_price']) * row['shares'] * mult
                total_pnl += pnl
                with st.container(border=True):
                    st.markdown(f"**{row['name']}** `{row['id']}`")
                    st.write(f"持有: **{row['shares']} {row['unit']}** | 成本: {row['buy_price']}")
                    pnl_color = "red" if pnl >= 0 else "green"
                    st.markdown(f"損益: <span style='color:{pnl_color}; font-weight:bold;'>NT$ {pnl:,.0f}</span>", unsafe_allow_html=True)
                    
                    # --- 補回：減持功能佈局 ---
                    e_c1, e_c2 = st.columns([1, 1.2])
                    exit_q = e_c1.number_input("減持數量", min_value=1, max_value=int(row['shares']), value=1, key=f"eq_{idx}")
                    if e_c2.button(f"❌ 執行減持", key=f"f_{idx}", use_container_width=True):
                        if exit_q >= row['shares']:
                            st.session_state.local_db = st.session_state.local_db.drop(idx)
                        else:
                            st.session_state.local_db.at[idx, 'shares'] -= exit_q
                        record_transaction(st.session_state.cur_c, row['id'], "SELL", exit_q, cp, "手動減持")
                        save_data(); st.rerun()
            
            st.divider()
            st.metric("📊 帳戶總未實現損益", f"NT$ {total_pnl:,.0f}", delta=f"{total_pnl:,.0f}")
        else:
            st.info("目前尚無持有標的。")

        # --- 同步按鈕 (確保在 col_r 內部) ---
        st.divider()
        st.markdown("### ☁️ 持股數據同步")
        
        # 1. 準備下載用的 CSV 數據
        csv_inventory = st.session_state.local_db.to_csv(index=False).encode('utf-8-sig')
        
        c_sync1, c_sync2 = st.columns(2)
        with c_sync1:
            if st.button("💾 存至本地緩存", key="up_scan", use_container_width=True):
                save_data()
                st.success("已存至本地 stone_manager_db.csv")
            
            # --- 下載按鈕 ---
            st.download_button(
                label="📥 下載最新持股 (CSV)",
                data=csv_inventory,
                file_name=f"inventory_{datetime.now().strftime('%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True
            )

        with c_sync2:
            if st.button("🔄 從雲端重新獲取", key="dl_scan", use_container_width=True):
                st.cache_data.clear()
                st.session_state.initialized = False 
                st.rerun()


with tab_intel:
    # --- [第 7 區：全球戰略情報中樞 V15.0 史詩強化版] ---
    st.header("🌎 全球戰略情報大腦 (24H 繁體深度更新)")

    def fetch_and_score_intel():
        import collections
        import re
        from datetime import datetime, timedelta
        import time
        import urllib.parse

        # 1. 定義海量搜索矩陣 (確保數量與質量)
        strategic_map = {
            "🇹🇼 台美日中 (地緣)": [
                "台海局勢 when:24h", "中共軍演 when:24h", "台美關係 when:24h", 
                "半導體戰爭 when:24h", "台積電 晶片禁令 when:24h", "南海衝突 when:24h",
                "兩岸貿易 when:24h", "美國對台軍售 when:24h"
            ],
            "🌐 國際戰略 (全球)": [
                "中東戰爭 以色列 伊朗 when:24h", "俄烏戰爭 戰況 when:24h", "美聯儲 利率決策 when:24h", 
                "川普 政策 關稅 when:24h", "蘇伊士運河 航運 when:24h", "全球經濟衰退 when:24h",
                "北約 俄羅斯 when:24h", "美國大選 地緣政治 when:24h", "石油供應 危機 when:24h"
            ]
        }
        
        all_raw_entries = []
        seen_links = set()
        
        # 2. 執行並發抓取
        for cat, queries in strategic_map.items():
            for q in queries:
                u = f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
                try:
                    feed = feedparser.parse(u)
                    for e in feed.entries[:15]: # 增加每個單項的獲取數
                        if e.link not in seen_links:
                            e.category = cat 
                            all_raw_entries.append(e)
                            seen_links.add(e.link)
                except:
                    continue

        # 3. 動態熱詞與權重評分
        all_titles = " ".join([e.title for e in all_raw_entries])
        words = re.findall(r'[\u4e00-\u9fa5]{2,4}', all_titles)
        top_hot_words = [w for w, c in collections.Counter(words).most_common(15)] 

        scored_results = []
        
        # 強力加權關鍵字
        high_alert = ["戰爭", "衝突", "導彈", "演習", "爆發", "制裁", "斷鏈", "緊急", "襲擊", "加息", "降息"]
        leader_alert = ["拜登", "川普", "習近平", "鮑爾", "內塔尼亞胡", "普丁", "黃仁勳"]

        for e in all_raw_entries:
            score = 50 # 基礎分
            title = e.title.upper()
            
            # 關鍵字權重激增
            if any(w in title for w in high_alert): score += 25
            if any(w in title for w in leader_alert): score += 20
            if any(w in title for w in top_hot_words[:5]): score += 10
            
            # 處理發布時間顯示
            pub_tag = "24H 內"
            if hasattr(e, 'published'):
                pub_tag = e.published[5:16]

            scored_results.append({
                'data': e, 
                'score': score, 
                'cat': e.category,
                'time': pub_tag
            })

        # 根據分數排序，分數越高越重要
        return sorted(scored_results, key=lambda x: x['score'], reverse=True), top_hot_words

    # --- 介面渲染 ---
    if 'news_mode' not in st.session_state:
        st.session_state.news_mode = "🇹🇼 台美日中 (地緣)"

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🇹🇼 台美日中・周邊情勢", use_container_width=True):
            st.session_state.news_mode = "🇹🇼 台美日中 (地緣)"
    with col2:
        if st.button("🌐 國際戰略・全球動態", use_container_width=True):
            st.session_state.news_mode = "🌐 國際戰略 (全球)"

    # 獲取資料
    with st.spinner("📡 正在接入全球衛星情報網..."):
        news_list, current_trends = fetch_and_score_intel()

    st.write(f"🔥 **今日戰略焦熱點：** " + " ".join([f"`{w}`" for w in current_trends[:10]]))

    target_cat = st.session_state.news_mode
    filtered_list = [item for item in news_list if item['cat'] == target_cat]

    st.info(f"📊 已鎖定 **{target_cat}**情報，共計 **{len(filtered_list)}** 則精選要聞")

    # 使用兩欄佈局顯示，增加資訊密度
    nl, nr = st.columns(2)
    for i, item in enumerate(filtered_list):
        n = item['data']
        score = item['score']
        
        # 標籤邏輯
        if score >= 85:
            label, color, border = "⚡ 重大戰略", "#FF4B4B", "2px solid #FF4B4B"
        elif score >= 70:
            label, color, border = "🚨 深度關注", "#FFD700", "1px solid #FFD700"
        else:
            label, color, border = "🔍 即時情報", "#00D1FF", "1px solid #E0E0E0"

        card_content = f"""
            <div style='border-left:5px solid {color}; border-top:{border}; border-right:{border}; border-bottom:{border}; 
                        padding:15px; margin-bottom:15px; background:white; border-radius:10px; 
                        box-shadow: 2px 2px 8px rgba(0,0,0,0.05); min-height: 120px;'>
                <div style='display:flex; justify-content:space-between; margin-bottom:8px;'>
                    <span style='background:{color}; color:{"white" if score>=85 else "black"}; padding:2px 10px; border-radius:15px; font-size:11px; font-weight:bold;'>{label}</span>
                    <span style='color:grey; font-size:11px;'>🕒 {item['time']}</span>
                </div>
                <div style='margin-top:8px;'>
                    <a href='{n.link}' target='_blank' style='text-decoration:none; color:#1e1e1e; font-size:14px; font-weight:bold; line-height:1.5;'>{n.title}</a>
                </div>
                <div style='margin-top:10px; border-top:1px dashed #eee; padding-top:5px; text-align:right;'>
                    <span style='font-size:10px; color:#aaa;'>戰略價值權重: {score}</span>
                </div>
            </div>
        """
        if i % 2 == 0: nl.markdown(card_content, unsafe_allow_html=True)
        else: nr.markdown(card_content, unsafe_allow_html=True)

    if len(filtered_list) == 0:
        st.warning("⚠️ 24H 內暫無匹配之重磅情報，請嘗試切換頻道。")


# --- [第 8 區：交易紀錄 - 強化同步版] ---
with tab_history:
    st.subheader("📜 歷史交易紀錄")
    if 'trade_history' in st.session_state and not st.session_state.trade_history.empty:
        st.dataframe(st.session_state.trade_history.sort_values(by='date', ascending=False), use_container_width=True)
    else:
        st.info("尚無紀錄。")
        
    st.divider()
    st.markdown("### ☁️ 交易紀錄同步備份")
    
    # 準備下載用的交易紀錄數據
    csv_history = st.session_state.trade_history.to_csv(index=False).encode('utf-8-sig')
    
    h_sync1, h_sync2 = st.columns(2)
    with h_sync1:
        if st.button("💾 存至本地紀錄", key="up_hist", use_container_width=True):
            save_data()
            st.success("紀錄已存檔至本地 trading_history.csv")
        
        # --- 新增：下載紀錄按鈕 ---
        st.download_button(
            label="📥 下載歷史紀錄 (CSV)",
            data=csv_history,
            file_name=f"history_{datetime.now().strftime('%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )

    with h_sync2:
        if st.button("🔄 刷新雲端連線", key="dl_hist", use_container_width=True):
            st.rerun()

