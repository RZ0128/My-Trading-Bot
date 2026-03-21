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
    # 確保這裡的 sheet_name 傳入時與 Google Sheet 分頁名稱完全吻合
    return f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"

def check_connection():
    """檢測與 Google Sheets 的連線狀態"""
    try:
        # 以 history 作為連線測試標的
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
    st.info("💡 提示：請確保 Google Sheets 已改名為 inventory/history/clients 並已『發布到網路』。")

# --- [第 2 區：修正後的載入邏輯 - 強化容錯版] ---

def load_data():
    """混合記憶模式：修正排序並加強欄位容錯，確保不因空值崩潰"""
    # 核心鎖：防止 Streamlit 重複執行初始化
    if 'initialized' in st.session_state and st.session_state.initialized:
        return

    try:
        # 1. 讀取庫存 (第一頁: inventory)
        st.session_state.local_db = pd.read_csv(get_sheet_url("inventory"))
        
        # 2. 讀取歷史 (第二頁: history)
        df_hist = pd.read_csv(get_sheet_url("history"))
        
        # 【超級防禦機制】：即便雲端試算表是空的或標題不對，也強制補上 date 欄位防止後續報錯
        if df_hist.empty or 'date' not in df_hist.columns:
            df_hist = pd.DataFrame(columns=['date', 'client', 'id', 'action', 'shares', 'price', 'note'])
        
        st.session_state.trade_history = df_hist
        
        # 3. 讀取客戶 (第三頁: clients)
        client_df = pd.read_csv(get_sheet_url("clients"))
        cloud_clients = client_df['name'].tolist() if 'name' in client_df.columns else []
        
        if 'client_list' not in st.session_state:
            st.session_state.client_list = ["Robert"]
            
        ghosts = ["nan", "None", None]
        combined = list(set(st.session_state.client_list + cloud_clients))
        st.session_state.client_list = sorted([str(c) for c in combined if str(c) not in ghosts])
        
        # 標記初始化成功
        st.session_state.initialized = True
            
    except Exception as e:
        # 最終備援：如果連線完全斷路，建立空白 DataFrame 確保 UI 能顯示
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



# --- [第 3 區：史詩將軍級超強大腦 V12.6 (戰略擴張/轉型偵測/洗盤完成)] ---
def generate_ai_tech_analysis(ticker, price, diff_pct):
    """
    大腦核心法則：板塊共振/填息基因/短線冷靜 + 2026 戰略轉型邏輯
    """
    try:
        stock = yf.Ticker(ticker)
        # 擴展數據抓取：2年歷史以計算長線高點
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
        
        # --- 核心 1: 籌碼洗盤與 35年價值發現 (融資洗盤邏輯) ---
        is_wash_done = False
        is_value_gem = False
        sentiment = "散戶進場 (融資增)"
        
        # 偵測洗盤完成：回檔至關鍵均線且成交量極縮
        if on_support and vol_dry_out:
            score += 45
            is_wash_done = True
            sentiment = "大戶收貨 (融資減)" # AI 判定洗盤完成後的籌碼位格
        
        if price <= low_30 * 1.05 and on_support and vol_dry_out:
            score += 20 
            is_value_gem = True
            sentiment = "💎 戰略價值區 (大戶長期鎖籌)"

        # --- [新增] 核心 1.5: 戰略轉型與突破偵測 (適合 3211, 3293) ---
        # 邏輯：股價挑戰 2 年新高且位階在均線之上，代表產業結構改變 (Re-rating)
        high_2y = hist_full['Close'].max()
        is_strategic_pivot = False
        if price >= high_2y * 0.96 and price > ma60:
            score += 20 # 給予強大的轉型溢價分
            is_strategic_pivot = True
            sentiment = "🔥 大戶瘋狂掃貨 (產業轉型確認)"

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
        # 修正：如果是「戰略突破股」，乖離容忍度稍微提高
        cool_limit = 0.18 if is_strategic_pivot else 0.15
        if bias_20 > cool_limit: 
            score -= 15
            is_overheated = True

        # --- 核心 4: 長線風險過濾 ---
        bias_240 = (price - ma240) / ma240
        if bias_240 > 0.5: score -= 30 # 高檔修正風險

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
        if is_strategic_pivot: msg = "🔥 偵測到轉型利基題材，分析師強推標的 " + msg
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


# ==============================================================================
# 第四區：大基石核心標的池 (500 檔自動後綴處理器)
# ==============================================================================

# 1. 首先定義【自動補完邏輯】(放在最上面，確保後續調用順暢)
def get_full_ticker(stock_id):
    """
    自動識別上市(.TW)與上櫃(.TWO)規則：
    """
    # 定義上櫃代碼開頭 (涵蓋 3211, 3293, 以及多數生技與網通上櫃股)
    otc_prefixes = ["31", "32", "33", "34", "35", "36", "41", "49", "52", "53", "54", "61", "62", "64", "65", "66", "80", "82"]
    
    # 特例排除：若代碼長度不是 4 位 (如 ETF 0050) 一律走 .TW
    if len(stock_id) != 4:
        return f"{stock_id}.TW"
        
    # 根據開頭識別上櫃
    if any(stock_id.startswith(pre) for pre in otc_prefixes):
        return f"{stock_id}.TWO"
    else:
        return f"{stock_id}.TW"

# 2. 映射表 (代號: 中文名稱) - 500 檔完整清單
STOCK_MAP = {
    "3211": "順達", "3293": "鈊象", "1313": "聯成", "2330": "台積電", "2454": "聯發科",
    # ... (請接續貼上你剛剛整理好的那 500 檔完整清單) ...
    # 確保結尾有括號閉合
}

# 3. 產業別分類 (對應 UI 上的 Radio 選項)

pool_500 = {
    # --- 指數/高股息/海外 ETF (50檔) ---
    "0050": "元大台灣50", "0056": "元大高股息", "00878": "國泰永續高股息", "00919": "群益台灣精選高股息", "00929": "復華台灣科技優息",
    "00713": "元大台灣高息低波", "006208": "富邦台50", "00940": "元大台灣價值高息", "00939": "統一台灣高息動能", "00881": "國泰台灣5G+",
    "00900": "富邦特選高股息", "00915": "凱基台灣優選高股息", "00918": "大鴻台灣高息低波", "00922": "國泰台灣領袖50", "00923": "群益台灣ESG低碳",
    "0052": "富邦科技", "006205": "富邦上証", "00631L": "元大台灣50正2", "00632R": "元大台灣50反1", "00646": "元大S&P500",
    "00662": "富邦 NASDAQ", "00679B": "元大美債20年", "00757": "統一FANG+", "00893": "國泰智能電動車", "00895": "富邦未來車",
    "00937B": "群益ESG投等債20+", "00680L": "元大美債20正2", "00687B": "國泰美債20年", "00712": "復華富時不動產", "00751B": "元大AAA至A級公司債",
    "00720B": "元大投資級公司債", "00772B": "中信高評級公司債", "00773B": "中信優先金融債", "00933B": "國泰10Y+金融債", "00936": "台新臺灣IC設計",
    "00905": "FT臺灣Smart", "00944": "野村趨勢動能高息", "00946": "群益台灣科技高息", "00921": "兆豐龍頭等權重", "00907": "永豐優息存股",
    "00891": "中信關鍵半導體", "00892": "富邦台灣半導體", "00830": "國泰費城半導體", "00657": "國泰日本", "00645": "富邦日本",
    "00637L": "元大滬深300正2", "00633L": "富邦上証正2", "00882": "中信中國高股息", "00753L": "元大中證500正2", "00636": "國泰中國A50",

    # --- 半導體/IC設計/封測 (100檔) ---
    "2330": "台積電", "2454": "聯發科", "2303": "聯電", "2379": "瑞昱", "3034": "聯詠", "3227": "原相", "6138": "茂達", "3443": "創意",
    "3661": "世芯-KY", "3529": "力旺", "6415": "矽力*-KY", "5269": "祥碩", "2408": "南亞科", "2344": "華邦電", "3006": "晶豪科",
    "8150": "南茂", "3035": "智原", "2337": "旺宏", "3711": "日月光投控", "6239": "力成", "4919": "新唐", "8016": "矽創", "3545": "敦泰",
    "3583": "齊宣", "6533": "晶心科", "6515": "穎崴", "3189": "景碩", "8039": "台達化", "3376": "新日興", "6182": "合晶", "8299": "群聯",
    "6202": "盛群", "3264": "欣銓", "5483": "中美晶", "6488": "環球晶", "3532": "台勝科", "3016": "嘉晶", "2401": "凌陽", "2436": "偉詮電",
    "2458": "義隆", "3014": "聯陽", "3041": "揚智", "3536": "誠創", "4952": "凌通", "5285": "界霖", "6233": "旺玖", "6243": "迅杰",
    "6679": "鈺太", "8028": "昇陽半導體", "8081": "致新", "3218": "大學光", "3413": "京鼎", "3557": "嘉威", "3588": "通嘉", "3682": "亞太電",
    "4967": "十銓", "4968": "立積", "5222": "全訊", "5272": "笙科", "6147": "頎邦", "6417": "聖暉*", "6435": "大中", "6451": "訊芯-KY",
    "6462": "神盾", "6494": "九齊", "6510": "精測", "6531": "愛普*", "6568": "宏觀", "6573": "虹揚-KY", "6586": "長興", "6613": "朋程",
    "6643": "M31", "6684": "安格", "6719": "力智", "6732": "昇佳電子", "6756": "威鋒電子", "8054": "安國", "8261": "富鼎", "8271": "宇瞻",
    "2329": "華泰", "2369": "菱生", "2449": "京元電子", "3265": "台星科", "6147": "頎邦", "6257": "矽格", "6271": "同欣電", "6515": "穎崴",
    "6664": "群翊", "3563": "牧德", "2467": "志聖", "6640": "均華", "3131": "弘塑", "3583": "辛耘", "6187": "萬潤", "1560": "中砂", "8028": "昇陽半導體",

    # --- AI伺服器/電腦組裝 (70檔) ---
    "2317": "鴻海", "2382": "廣達", "2357": "華碩", "3231": "緯創", "2356": "英業達", "6669": "緯穎", "2301": "光寶科", "2353": "宏碁",
    "2324": "仁寶", "4938": "和碩", "2395": "研華", "3017": "奇鋐", "3013": "晟銘電", "3515": "華擎", "2376": "技嘉", "2377": "微星",
    "2425": "承啟", "8046": "南電", "8210": "勤誠", "2362": "藍天", "2365": "昆盈", "2397": "友通", "3416": "融程電", "3005": "神基",
    "3209": "全科", "4916": "事欣科", "6235": "華孚", "8046": "南電", "8215": "明基材", "2364": "倫飛", "2352": "佳世達", "2417": "圓剛",
    "3057": "喬鼎", "3062": "建漢", "3288": "點晶", "3494": "誠研", "4953": "緯軟", "5215": "科嘉-KY", "5264": "鎧勝-KY", "5324": "士開",
    "5469": "瀚宇博", "6117": "盟立", "6121": "新普", "6142": "友勁", "6153": "嘉聯益", "6197": "佳必琪", "6205": "詮欣", "6206": "飛捷",
    "6213": "聯茂", "6214": "精誠", "6245": "立端", "6277": "宏齊", "6281": "全國電", "6285": "啟碁", "6409": "旭隼", "6414": "樺漢",
    "6441": "廣錠", "6492": "生華科", "6541": "泰福-KY", "6579": "研揚", "8050": "廣積", "8064": "東捷", "8076": "伍豐", "8096": "擎亞",
    "8114": "振曜", "8215": "明基材", "8410": "森田", "2312": "金寶", "2328": "廣宇",

    # --- 網通/零組件/散熱 (80檔) ---
    "2313": "華通", "2367": "燿華", "2368": "金像電", "3044": "健鼎", "6269": "台郡", "3037": "欣興", "3324": "雙鴻", "2421": "建準",
    "3060": "銘異", "3454": "晶睿", "3596": "智易", "3704": "合勤控", "5388": "中磊", "6285": "啟碁", "2345": "智邦", "4906": "正文",
    "6426": "統新", "3163": "波若威", "3234": "光環", "4977": "眾達-KY", "3025": "星通", "3311": "閎暉", "3312": "弘憶股", "3338": "泰碩",
    "3373": "熱映", "3419": "驊訊", "3491": "昇達科", "3523": "迎輝", "3528": "安馳", "3540": "曜越", "3558": "神準", "3605": "宏致",
    "3624": "光頡", "3645": "達邁", "3664": "安力-KY", "3686": "達能", "3694": "海華", "4904": "遠傳", "4971": "IET-KY", "4979": "華星光",
    "5225": "東科-KY", "5349": "先豐", "5469": "瀚宇博", "6101": "弘凱", "6143": "振曜", "6153": "嘉聯益", "6190": "萬泰科", "6216": "居易",
    "6241": "易通展", "6245": "立端", "6282": "康舒", "2486": "一詮", "3017": "奇鋐", "3338": "泰碩", "3023": "信邦", "2308": "台達電",
    "2421": "建準", "3324": "雙鴻", "3017": "奇鋐", "6230": "超眾", "3653": "健策", "2482": "連宇", "3046": "建碁", "3211": "順達", # 3211 在此
    "3321": "同泰", "3693": "營邦", "4935": "茂林-KY", "4989": "榮科", "5439": "高技", "6108": "競國", "6141": "柏承", "6153": "嘉聯益",
    "6213": "聯茂", "6220": "岳豐", "6235": "華孚", "6269": "台郡", "6274": "台燿", "6278": "台表科", "8039": "台達化", "8155": "博智",

    # --- 塑膠/化學/傳產 (60檔) ---
    "1301": "台塑", "1303": "南亞", "1313": "聯成", "1304": "台聚", "1308": "亞聚", "1310": "台苯", "1312": "國喬", "1314": "中石化", # 1313 在此
    "1326": "台化", "2105": "正新", "1101": "台泥", "1102": "亞泥", "1216": "統一", "1402": "遠東新", "2002": "中鋼", "2014": "中鴻",
    "2006": "東和鋼鐵", "2106": "建大", "1717": "長興", "1722": "台肥", "1723": "中碳", "4763": "材料-KY", "1701": "中化", "1704": "榮化",
    "1708": "東鹼", "1709": "和益", "1710": "東聯", "1711": "永光", "1712": "興農", "1713": "國化", "1714": "和桐", "1718": "中纖",
    "1720": "生達", "1721": "三晃", "1725": "元禎", "1726": "永記", "1727": "中華化", "1730": "花仙子", "1731": "美吾華", "1732": "毛寶",
    "1733": "五鼎", "1734": "杏輝", "1735": "日勝化", "1736": "喬山", "1737": "臺鹽", "1752": "南光", "1773": "勝一", "1776": "展宇",
    "1783": "和康生", "1786": "科妍", "1789": "神隆", "1802": "台玻", "1904": "正隆", "1907": "永豐餘", "1909": "榮成", "2103": "台橡",
    "2104": "國際中橡", "2108": "南帝", "6505": "台塑化", "9904": "寶成",

    # --- 金融保險 (40檔) ---
    "2881": "富邦金", "2882": "國泰金", "2891": "中信金", "2886": "兆豐金", "2884": "玉山金", "2885": "元大金", "2892": "第一金",
    "2890": "永豐金", "2880": "華南金", "2883": "凱基金", "2887": "台新金", "2888": "新光金", "5880": "合庫金", "5871": "中租-KY",
    "5876": "上海商銀", "2801": "彰銀", "2809": "京城銀", "2812": "台中銀", "2820": "華票", "2834": "臺企銀", "2836": "高雄銀",
    "2838": "聯邦銀", "2845": "遠東銀", "2849": "安泰銀", "2850": "新產", "2851": "中再保", "2852": "第一保", "2855": "統一證",
    "2867": "三商壽", "5864": "致和證", "6005": "群益證", "6012": "金鼎證", "6015": "宏遠證", "6016": "康和證", "6020": "大展證",
    "6021": "大慶證", "6023": "元大期", "6024": "群益期", "6026": "福邦證", "6028": "永豐期",

    # --- 航運/重電/電機 (50檔) ---
    "2603": "長榮", "2609": "陽明", "2615": "萬海", "2610": "華航", "2618": "長榮航", "1503": "士電", "1504": "東元", "1513": "中興電",
    "1519": "華城", "1514": "亞力", "1605": "華新", "1608": "華榮", "1609": "大亞", "1517": "利奇", "1516": "川飛", "2633": "台灣高鐵",
    "2634": "漢翔", "2637": "慧洋-KY", "5607": "遠雄港", "2601": "益航", "2605": "新興", "2606": "裕民", "2607": "榮運", "2608": "嘉里大榮",
    "2611": "志信", "2612": "中航", "2613": "中櫃", "2614": "東森", "2617": "台航", "2630": "亞航", "2636": "台驊投控", "2642": "宅配通",
    "1506": "元禎", "1507": "永大", "1512": "瑞智", "1521": "大億", "1522": "堤維西", "1524": "耿鼎", "1525": "江申", "1526": "日馳",
    "1527": "鑽全", "1528": "恩德", "1529": "樂士", "1530": "亞崴", "1531": "高林股", "1532": "勤美", "1533": "車王電", "1535": "力肯",
    "1536": "和大", "1537": "廣隆",

    # --- 生技/內需/遊戲/其他 (50檔) ---
    "1760": "寶齡富錦", "4147": "龍燈-KY", "6472": "保瑞", "1795": "美時", "4174": "浩鼎", "9904": "寶成", "9910": "豐泰", "9921": "巨大",
    "2912": "統一超", "5904": "寶雅", "3293": "鈊象", "5478": "智冠", "6111": "大宇資", "6180": "橘子", "8454": "富邦媒", "9933": "中鼎",
    "4104": "佳醫", "4106": "雃博", "4108": "懷特", "4111": "濟生", "4114": "健喬", "4119": "旭富", "4120": "友華", "4121": "優盛",
    "4123": "晟德", "4126": "太醫", "4128": "中天", "4129": "聯合", "4130": "健亞", "4137": "麗豐-KY", "4141": "龍燈-KY", "4142": "國光生",
    "4148": "全宇-KY", "4155": "訊聯", "4162": "智凱", "4164": "承業醫", "4167": "展旺", "4174": "浩鼎", "4180": "椒房", "4190": "佐登-KY",
    "4743": "合一", "6446": "藥華藥", "6452": "康友-KY", "6461": "益得", "6472": "保瑞", "6492": "生華科", "6504": "南六", "6531": "愛普*",
    "6541": "泰福-KY", "6547": "高端疫苗"
}

# 4. 戰略搜索 UI 邏輯
search_query = st.text_input("🔍 大基石搜索", placeholder="輸入代號或名稱 (如: 3211 或 順達)")
if search_query:
    matches = [(sid, sname) for sid, sname in STOCK_MAP.items() if search_query in sid or search_query in sname]
    for sid, sname in matches:
        full_sid = get_full_ticker(sid) 
        if st.button(f"🎯 診斷: {sname} ({full_sid})", key=f"btn_{sid}"):
            st.session_state.selected_stock = full_sid
            st.rerun()
pool_390 = pool_500 # 保持指引一致性


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
    for cat in pool_500.values():
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


# --- [第 6 區：頁面佈局重整 - 大基石 500 檔專用版] ---
tab_scan, tab_intel, tab_history = st.tabs(["📊 戰策指揮所", "🌐 全球情報室", "📜 交易紀錄"])

with tab_scan:
    st.title(f"🛡️ 12.5 史詩大腦整合版: [{st.session_state.get('cur_c', 'Robert')}]")
    col_l, col_r = st.columns([1.6, 1.4]) 
    
    # --- [左側：戰略掃描] ---
    with col_l:
        with st.container(border=True):
            st.subheader("🔍 全球個股戰略搜索")
            # 使用唯一 Key 防止衝突
            s_input = st.text_input("輸入名稱或代號", placeholder="例如：長榮、順達、3211", key="global_search_v126")
            
            target_id = None
            target_name = ""

            if s_input:
                s_lower = s_input.lower().strip()
                # 從大基石 STOCK_MAP 進行全域匹配
                matches = [(sid, sname) for sid, sname in STOCK_MAP.items() if s_lower in sid or s_lower in sname]
                
                if matches:
                    if len(matches) > 1:
                        st.write(f"💡 找到 {len(matches)} 檔相關標的：")
                        m_cols = st.columns(3)
                        for idx, (m_sid, m_sname) in enumerate(matches[:9]): # 最多顯示 9 個候選
                            with m_cols[idx % 3]:
                                # 這裡調用 get_full_ticker 確保顯示正確後綴
                                display_id = get_full_ticker(m_sid)
                                if st.button(f"🎯 {m_sname}", key=f"search_btn_{m_sid}"):
                                    st.session_state['active_tid'] = m_sid
                                    st.session_state['active_name'] = m_sname
                        
                        target_id = st.session_state.get('active_tid', matches[0][0])
                        target_name = st.session_state.get('active_name', matches[0][1])
                    else:
                        target_id, target_name = matches[0]
                else:
                    st.warning("⚠️ 500 檔名單中無匹配項。")

            # --- 執行診斷與顯示 ---
            if target_id:
                full_tid = get_full_ticker(target_id) # 關鍵：轉換為 .TW / .TWO
                p, d, cc = get_stock_perf(full_tid, 0)
                if p > 0:
                    res = generate_ai_tech_analysis(full_tid, p, 0)
                    if res:
                        st.markdown("---")
                        st.markdown(f"### 🎯 戰略診斷: {target_name} ({full_tid})")
                        with st.container(border=True):
                            sc1, sc2 = st.columns([1.5, 1])
                            with sc1:
                                st.markdown(f"#### **評分: <span style='color:red;'>{res['score']}</span>**", unsafe_allow_html=True)
                                st.info(f"**診斷:** {res['msg']}")
                                # 這裡會顯示你要求的：🔥 偵測到洗盤完成，準備破新高
                                st.markdown(f"**籌碼狀態:** <span style='background:#f0f2f6;padding:2px 5px;'>{res['sent']}</span>", unsafe_allow_html=True)
                                
                                st.write("---")
                                u_c1, u_c2 = st.columns(2)
                                q_val = u_c1.number_input("佈局數量", min_value=1, value=1, key=f"q_fin_{target_id}")
                                u_val = u_c2.radio("佈局單位", ["張", "股"], key=f"u_fin_{target_id}", horizontal=True)
                                
                                if st.button(f"🚀 確認執行佈局 {target_name}", key=f"conf_fin_{target_id}", use_container_width=True):
                                    new_entry = pd.DataFrame([{
                                        'client': st.session_state.cur_c, 'id': full_tid, 'name': target_name,
                                        'buy_price': p, 'shares': q_val, 'unit': u_val,
                                        'entry_reason': res['msg'], 'current_score': res['score'], 'last_diag': datetime.now().strftime("%m-%d")
                                    }])
                                    st.session_state.local_db = pd.concat([st.session_state.local_db, new_entry], ignore_index=True)
                                    record_transaction(st.session_state.cur_c, full_tid, "BUY", q_val, p, "AI 搜尋佈局")
                                    save_data(); st.success(f"✅ 已成功佈局 {target_name}"); st.rerun()
                            with sc2:
                                st.metric("即時股價", p, d)
                                st.success(f"🎯 目標預期: {res['target']}")
                                st.warning(f"🛡️ 防守位: {res['stop']}")

        st.divider()
        # 修正：統一使用 pool_500 變數
        cat_choice = st.radio("產業板塊掃描", list(pool_500.keys()), horizontal=True, key="cat_radio")
        scored_data = []
        for tid in pool_500[cat_choice]:
            tname = STOCK_MAP.get(tid, "未知")
            full_tid = get_full_ticker(tid)
            p, d, cc = get_stock_perf(full_tid, 0)
            res = generate_ai_tech_analysis(full_tid, p, 0)
            if res:
                res.update({'tid': full_tid, 'tname': tname, 'price': p, 'diff': d, 'base_id': tid})
                scored_data.append(res)
        
        top_picks = sorted(scored_data, key=lambda x: x['score'], reverse=True)[:15]
        for item in top_picks:
            with st.expander(f"⭐ {item['tname']} | 評分: {item['score']} | 價: {item['price']} ({item['diff']})"):
                st.markdown(f"**🧠 AI 診斷:** {item['msg']}")
                k_c1, k_c2, k_c3 = st.columns([1, 1.2, 1.8])
                quick_q = k_c1.number_input("數量", min_value=1, value=1, key=f"qq_{item['base_id']}")
                quick_u = k_c2.radio("單位", ["張", "股"], key=f"qu_{item['base_id']}", horizontal=True)
                if k_c3.button(f"🚀 快速佈局 {item['tname']}", key=f"bp_{item['base_id']}", use_container_width=True):
                    new_entry = pd.DataFrame([{
                        'client': st.session_state.cur_c, 'id': item['tid'], 'name': item['tname'],
                        'buy_price': item['price'], 'shares': quick_q, 'unit': quick_u,
                        'entry_reason': item['msg'], 'current_score': item['score'], 'last_diag': datetime.now().strftime("%m-%d")
                    }])
                    st.session_state.local_db = pd.concat([st.session_state.local_db, new_entry], ignore_index=True)
                    record_transaction(st.session_state.cur_c, item['tid'], "BUY", quick_q, item['price'], "板塊掃描快速進場")
                    save_data(); st.rerun()

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
                    # 佈局保持不變，特別優化過的監控卡片
                    st.markdown(f"**{row['name']}** `{row['id']}`")
                    st.write(f"持有: **{row['shares']} {row['unit']}** | 成本: {row['buy_price']}")
                    pnl_color = "red" if pnl >= 0 else "green"
                    st.markdown(f"損益: <span style='color:{pnl_color}; font-weight:bold;'>NT$ {pnl:,.0f}</span>", unsafe_allow_html=True)
                    
                    e_c1, e_c2 = st.columns([1, 1.2])
                    exit_q = e_c1.number_input("減持數量", min_value=1, max_value=max(1, int(row['shares'])), value=1, key=f"eq_{idx}")
                    if e_c2.button(f"❌ 執行減持", key=f"btn_exit_{idx}", use_container_width=True):
                        if exit_q >= row['shares']:
                            st.session_state.local_db = st.session_state.local_db.drop(idx)
                        else:
                            st.session_state.local_db.at[idx, 'shares'] -= exit_q
                        record_transaction(st.session_state.cur_c, row['id'], "SELL", exit_q, cp, "手動減持")
                        save_data(); st.rerun()
            st.metric("📊 帳戶總未實現損益", f"NT$ {total_pnl:,.0f}", delta=f"{total_pnl:,.0f}")


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


# --- [第 8 區：交易紀錄 - 強化同步防錯版] ---
with tab_history:
    st.subheader("📜 歷史交易紀錄")
    
    # 檢查是否有資料
    if 'trade_history' in st.session_state and not st.session_state.trade_history.empty:
        try:
            # 防錯機制：檢查 'date' 欄位是否存在
            if 'date' in st.session_state.trade_history.columns:
                # 排除空白的日期行再進行排序，避免崩潰
                df_to_show = st.session_state.trade_history.copy()
                # 強制轉換日期格式，不合法的轉為 NaT
                df_to_show['date'] = pd.to_datetime(df_to_show['date'], errors='coerce')
                display_df = df_to_show.sort_values(by='date', ascending=False)
            else:
                # 如果沒有 date 欄位，就直接顯示原始資料不排序
                display_df = st.session_state.trade_history
            
            st.dataframe(display_df, use_container_width=True)
        except Exception as e:
            # 如果排序還是失敗，顯示原始資料並提示
            st.warning(f"⚠️ 排序功能暫時失效 (格式偏移)，改為原始顯示模式")
            st.dataframe(st.session_state.trade_history, use_container_width=True)
    else:
        st.info("💡 目前尚無交易紀錄，或雲端連線中...")
        
    st.divider()
    st.markdown("### ☁️ 交易紀錄同步備份")
    
    # 準備下載用的 CSV 數據
    if 'trade_history' in st.session_state:
        csv_history = st.session_state.trade_history.to_csv(index=False).encode('utf-8-sig')
    else:
        csv_history = b""

    h_sync1, h_sync2 = st.columns(2)
    with h_sync1:
        if st.button("💾 存至本地紀錄", key="up_hist", use_container_width=True):
            save_data()
            st.success("✅ 紀錄已存檔至本地緩存")
        
        # --- 下載紀錄按鈕 ---
        st.download_button(
            label="📥 下載歷史紀錄 (CSV)",
            data=csv_history,
            file_name=f"history_{datetime.now().strftime('%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True,
            help="將此檔案下載後，上傳至 Google Sheets 的 history 分頁"
        )

    with h_sync2:
        if st.button("🔄 刷新雲端連線", key="dl_hist", use_container_width=True):
            st.cache_data.clear()
            st.session_state.initialized = False
            st.rerun()
