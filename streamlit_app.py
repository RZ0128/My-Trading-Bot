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
    """大基石 15.0 戰略情報引擎：全中文、分級、24H 即時"""
    import ssl
    import collections
    import re
    import urllib.parse

    if hasattr(ssl, '_create_unverified_context'):
        ssl._create_default_https_context = ssl._create_unverified_context

    # 完整戰略矩陣：確保台美日中與國際戰略全覆蓋
    strategic_map = {
        "🇹🇼 台美日中 (地緣)": [
            "台海局勢 when:24h", "中共軍演 when:24h", "台積電 晶片禁令 when:24h", 
            "美台關係 when:24h", "南海衝突 when:24h", "半導體戰爭 when:24h"
        ],
        "🌐 國際戰略 (全球)": [
            "中東戰爭 以色列 伊朗 when:24h", "美聯儲 利率 鮑爾 when:24h", "川普 關稅 when:24h", 
            "俄烏戰爭 戰況 when:24h", "紅海 航運 when:24h", "全球經濟 崩盤 when:24h"
        ]
    }
    
    news_list, seen_links = [], set()
    for cat_name, queries in strategic_map.items():
        for q in queries:
            u = f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
            try:
                feed = feedparser.parse(u)
                for e in feed.entries[:15]:
                    if e.link not in seen_links:
                        # 權重分級計算
                        score = 55
                        title = e.title.upper()
                        if any(w in title for w in ["戰爭", "衝突", "爆炸", "制裁", "斷鏈", "降息", "加息"]): score += 30
                        if any(w in title for w in ["台積電", "NVIDIA", "川普", "習近平"]): score += 15
                        
                        pub_tag = "24H 內"
                        if hasattr(e, 'published'): pub_tag = e.published[5:16]
                            
                        news_list.append({'data': e, 'score': min(99, score), 'cat': cat_name, 'time': pub_tag})
                        seen_links.add(e.link)
            except: continue

    # 提取熱門戰略詞
    all_titles = " ".join([item['data'].title for item in news_list])
    words = re.findall(r'[\u4e00-\u9fa5]{2,4}', all_titles)
    hot_words = [w for w, c in collections.Counter(words).most_common(12)] 
    return sorted(news_list, key=lambda x: x['score'], reverse=True), hot_words



# ==============================================================================
# 第四區：大基石核心標題池 (500 檔完整細分名單 - 2026 實戰版)
# ==============================================================================

pool_500 = {
    "💎 權值/金控/保險 (70)": [
        ("2330.TW","台積電"),("2317.TW","鴻海"),("2454.TW","聯發科"),("2308.TW","台達電"),("2881.TW","富邦金"),("2882.TW","國泰金"),("2303.TW","聯電"),("2886.TW","兆豐金"),("2891.TW","中信金"),("2412.TW","中華電"),
        ("2884.TW","玉山金"),("5880.TW","合庫金"),("2885.TW","元大金"),("5871.TW","中租-KY"),("2883.TW","凱基金"),("2887.TW","台新金"),("2892.TW","第一金"),("2890.TW","永豐金"),("2880.TW","華南金"),("5876.TW","上海商銀"),
        ("2801.TW","彰銀"),("2888.TW","新光金"),("2889.TW","國票金"),("2834.TW","臺企銀"),("2809.TW","京城銀"),("2812.TW","台中銀"),("2851.TW","中再保"),("6005.TW","群益證"),("2845.TW","遠東銀"),("2838.TW","聯邦銀"),
        ("2816.TW","旺旺保"),("2836.TW","高雄銀"),("2850.TW","新產"),("2852.TW","第一保"),("2855.TW","統一證"),("2867.TW","三商壽"),("6016.TW","康和證"),("6024.TWO","群益期"),("6026.TWO","福邦證"),("5878.TW","台名"),
        ("2849.TW","安泰銀"),("2820.TW","華票"),("2823.TW","中壽"),("2832.TW","台產"),("2841.TW","台開"),("2856.TW","元富證"),("6021.TWO","大慶證"),("6023.TWO","元大期"),("2812.TW","台中銀"),("2845.TW","遠東銀"),
        ("2801.TW","彰銀"),("2834.TW","臺企銀"),("2897.TW","王道銀行"),("2869.TW","宏遠證"),("2855.TW","統一證"),("5876.TW","上海商銀"),("2880.TW","華南金"),("2892.TW","第一金"),("2881.TW","富邦金"),("2882.TW","國泰金"),
        ("2883.TW","凱基金"),("2884.TW","玉山金"),("2885.TW","元大金"),("2886.TW","兆豐金"),("2887.TW","台新金"),("2888.TW","新光金"),("2889.TW","國票金"),("2890.TW","永豐金"),("2891.TW","中信金"),("5880.TW","合庫金")
    ],
    "🔬 半導體/IC/設備 (80)": [
        ("3661.TW","世芯-KY"),("3443.TW","創意"),("3035.TW","智原"),("5269.TW","祥碩"),("3227.TW","原相"),("3034.TW","聯詠"),("2379.TW","瑞昱"),("6415.TW","矽力*-KY"),("6531.TW","愛普*"),("4966.TW","譜瑞-KY"),
        ("8299.TWO","群聯"),("4919.TW","新唐"),("2458.TW","義隆"),("8016.TW","矽創"),("3529.TWO","力旺"),("6643.TWO","M31"),("6732.TWO","昇佳電子"),("6138.TWO","茂達"),("3014.TW","聯陽"),("8081.TW","致新"),
        ("3131.TWO","弘塑"),("3583.TW","辛耘"),("1560.TW","中砂"),("3680.TW","家登"),("6196.TW","帆宣"),("6667.TWO","信紘科"),("3374.TWO","精材"),("6223.TWO","旺矽"),("6515.TW","穎崴"),("6510.TWO","精測"),
        ("3413.TW","京鼎"),("3587.TWO","閎康"),("6683.TWO","雍智科技"),("8027.TW","鈦昇"),("6789.TW","采鈺"),("6438.TW","迅得"),("6139.TW","亞博"),("3563.TW","牧德"),("2467.TW","志聖"),("6640.TWO","均華"),
        ("8028.TW","昇陽半"),("3532.TW","台勝科"),("6488.TWO","環球晶"),("5483.TWO","中美晶"),("3016.TW","嘉晶"),("2344.TW","華邦電"),("2337.TW","旺宏"),("2408.TW","南亞科"),("3006.TW","晶豪科"),("6239.TW","力成"),
        ("3711.TW","日月光投控"),("2449.TW","京元電子"),("6147.TWO","頎邦"),("8150.TW","南茂"),("3264.TWO","欣銓"),("6257.TW","矽格"),("6271.TW","同欣電"),("2369.TW","菱生"),("2401.TW","凌陽"),("3041.TW","揚智"),
        ("3527.TWO","聚積"),("3588.TWO","通嘉"),("5471.TW","松翰"),("6202.TW","盛群"),("6233.TWO","旺玖"),("6243.TWO","迅杰"),("6411.TWO","晶焱"),("6462.TWO","神盾"),("6533.TWO","晶心科"),("6679.TWO","鈺太"),
        ("8261.TW","富鼎"),("8271.TW","宇瞻"),("4961.TW","天鈺"),("4952.TW","凌通"),("5272.TWO","笙科"),("6568.TWO","宏觀"),("6613.TW","朋程"),("6684.TWO","安格"),("6719.TW","力智"),("3557.TW","嘉威")
    ],
    "🔋 BBU 電池/儲能特區 (50)": [
        ("3211.TWO","順達"),("6121.TWO","新普"),("1513.TW","中興電"),("1519.TW","華城"),("1514.TW","亞力"),("1503.TW","士電"),("1609.TW","大亞"),("6806.TW","森崴能源"),("1101.TW","台泥"),("2301.TW","光寶科"),
        ("3027.TW","盛達"),("6409.TW","旭隼"),("2457.TW","飛宏"),("3617.TW","碩天"),("8121.TWO","達邁"),("6101.TWO","弘凱"),("1517.TW","利奇"),("1525.TW","江申"),("5227.TW","立凱-KY"),("3323.TWO","加百裕"),
        ("1514.TW","亞力"),("1513.TW","中興電"),("1504.TW","東元"),("1605.TW","華新"),("1608.TW","華榮"),("1611.TW","中電"),("1612.TW","大亞"),("1614.TW","三洋電"),("1617.TW","榮星"),("1618.TW","合機"),
        ("1517.TW","利奇"),("1521.TW","大億"),("1522.TW","堤維西"),("1524.TW","耿鼎"),("1525.TW","江申"),("1532.TW","勤美"),("1533.TW","車王電"),("1535.TW","中宇"),("1536.TW","和大"),("1537.TW","廣隆"),
        ("1538.TW","正峰新"),("1539.TW","巨庭"),("1540.TW","喬福"),("1541.TW","錩泰"),("1558.TW","伸興"),("1560.TW","中砂"),("1582.TW","信錦"),("1589.TW","永冠-KY"),("1590.TW","亞德客-KY"),("1597.TW","直得")
    ],
    "🌬️ AI伺服器/散熱/機殼 (80)": [
        ("2382.TW","廣達"),("3231.TW","緯創"),("6669.TW","緯穎"),("2376.TW","技嘉"),("2356.TW","英業達"),("2353.TW","宏碁"),("2357.TW","華碩"),("3017.TW","奇鋐"),("3324.TWO","雙鴻"),("2421.TW","建準"),
        ("3013.TW","晟銘電"),("3693.TWO","營邦"),("8210.TW","勤誠"),("2368.TW","金像電"),("2383.TW","台光電"),("6213.TW","聯茂"),("6274.TWO","台燿"),("2465.TW","麗臺"),("3515.TW","華擎"),("2365.TW","昆盈"),
        ("1582.TW","信錦"),("3005.TW","神基"),("2352.TW","佳世達"),("2316.TW","楠梓電"),("2367.TW","燿華"),("2371.TW","大同"),("2397.TW","友通"),("2417.TW","圓剛"),("2419.TW","仲琦"),("2428.TW","興勤"),
        ("2455.TW","全新"),("2480.TW","敦陽科"),("3010.TW","華立"),("3029.TW","零壹"),("3032.TW","偉訓"),("3321.TWO","同泰"),("3338.TW","泰碩"),("3376.TW","新日興"),("3402.TW","漢科"),("3540.TWO","曜越"),
        ("3596.TW","智易"),("3617.TW","碩天"),("3653.TW","健策"),("3665.TW","貿聯-KY"),("3694.TW","海華"),("4915.TW","致伸"),("4938.TW","和碩"),("4958.TW","臻鼎-KY"),("5215.TW","科嘉-KY"),("5388.TW","中磊"),
        ("6153.TW","嘉聯益"),("6166.TW","凌華"),("6205.TW","詮欣"),("6214.TW","精誠"),("6230.TW","超眾"),("6235.TW","華孚"),("8112.TW","至上"),("6409.TW","旭隼"),("6278.TW","台表科"),("6269.TW","台郡"),
        ("2385.TW","群光"),("3044.TW","健鼎"),("2425.TW","承啟"),("6117.TW","迎廣"),("2312.TW","金寶"),("2328.TW","廣宇"),("3060.TW","銘異"),("3454.TW","晶睿"),("3515.TW","華擎"),("2425.TW","承啟"),
        ("3231.TW","緯創"),("6669.TW","緯穎"),("2376.TW","技嘉"),("3017.TW","奇鋐"),("3324.TWO","雙鴻"),("2421.TW","建準"),("3013.TW","晟銘電"),("3693.TWO","營邦"),("8210.TW","勤誠"),("2368.TW","金像電")
    ],
    "🎮 數位文創/遊戲/軟體 (40)": [
        ("3293.TWO","鈊象"),("5478.TWO","智冠"),("6111.TWO","大宇資"),("6180.TWO","橘子"),("3083.TWO","網龍"),("4946.TWO","辣椒"),("3546.TWO","宇峻"),("6214.TW","精誠"),("4953.TW","緯軟"),("3029.TW","零壹"),
        ("2480.TW","敦陽科"),("6112.TW","聚碩"),("8446.TWO","華研"),("4803.TWO","VHQ-KY"),("6441.TWO","廣錠"),("8044.TWO","網家"),("8454.TW","富邦媒"),("3086.TWO","華義"),("3221.TWO","台嘉碩"),("3687.TWO","歐買尬"),
        ("5263.TWO","智崴"),("6143.TWO","振曜"),("6169.TWO","昱泉"),("6542.TWO","隆中"),("2496.TW","卓越"),("2471.TW","資通"),("3130.TW","一零四"),("4994.TW","傳奇"),("5203.TW","訊連"),("5209.TW","新鼎"),
        ("5211.TWO","蒙恬"),("5212.TWO","凌網"),("6221.TWO","晉泰"),("6414.TW","樺漢"),("6470.TWO","宇智"),("8068.TWO","全達"),("8477.TWO","創業家"),("8906.TWO","花王"),("9949.TWO","琉園"),("9960.TW","邁達特")
    ],
    "⚓ 航運/鋼鐵/傳產標竿 (90)": [
        ("2603.TW","長榮"),("2609.TW","陽明"),("2615.TW","萬海"),("2618.TW","長榮航"),("2610.TW","華航"),("2637.TWO","慧洋-KY"),("2606.TW","裕民"),("2605.TW","新興"),("2002.TW","中鋼"),("2014.TW","中鴻"),
        ("2006.TW","東和鋼鐵"),("2027.TW","大成鋼"),("2031.TW","新光鋼"),("1301.TW","台塑"),("1303.TW","南亞"),("1326.TW","台化"),("6505.TW","台塑化"),("2105.TW","正新"),("2912.TW","統一超"),("1216.TW","統一"),
        ("1101.TW","台泥"),("1102.TW","亞泥"),("1304.TW","台聚"),("1305.TW","華夏"),("1308.TW","亞聚"),("1309.TW","台達化"),("1310.TW","台苯"),("1312.TW","國喬"),("1313.TW","聯成"),("1314.TW","中石化"),
        ("1315.TW","達新"),("1316.TW","上曜"),("1319.TW","東陽"),("1321.TW","大洋"),("1323.TW","永裕"),("1324.TW","地球"),("1325.TW","恆大"),("1337.TW","再生-KY"),("1338.TW","廣華-KY"),("1339.TW","昭輝"),
        ("1340.TW","勝悅-KY"),("1341.TW","富林-KY"),("1402.TW","遠東新"),("1409.TW","新纖"),("1410.TW","南染"),("1413.TW","宏洲"),("1414.TW","東和"),("1416.TW","廣豐"),("1417.TW","嘉裕"),("1418.TW","東華"),
        ("1419.TW","新紡"),("1423.TW","利華"),("1432.TW","大魯閣"),("1434.TW","福懋"),("1435.TW","中福"),("1436.TW","華友聯"),("1437.TW","勤益控"),("1438.TW","三地開發"),("1439.TW","中和"),("1440.TW","南紡"),
        ("1441.TW","大東"),("1442.TW","名軒"),("1443.TW","立益"),("1444.TW","力麗"),("1445.TW","大宇"),("1446.TW","宏和"),("1447.TW","力鵬"),("1449.TW","佳和"),("1451.TW","年興"),("1452.TW","宏益"),
        ("1453.TW","大將"),("1454.TW","台富"),("1455.TW","集盛"),("1456.TW","怡華"),("1457.TW","宜進"),("1459.TW","聯發"),("1460.TW","宏遠"),("1463.TW","強盛"),("1464.TW","得力"),("1465.TW","偉全"),
        ("1466.TW","聚隆"),("1467.TW","南緯"),("1468.TW","昶和"),("1470.TW","大統新創"),("1471.TW","首利"),("1472.TW","三洋紡"),("1473.TW","台南"),("1474.TW","弘裕"),("1475.TW","本盟"),("1476.TW","儒鴻")
    ],
    "📡 網通/車用/光學/PCB (90)": [
        ("2345.TW","智邦"),("3704.TW","合勤控"),("5388.TW","中磊"),("3596.TW","智易"),("6285.TW","啟碁"),("4906.TW","正文"),("3380.TW","明泰"),("2314.TW","台揚"),("2201.TW","裕隆"),("2207.TW","和泰車"),
        ("1536.TW","和大"),("2313.TW","華通"),("2367.TW","燿華"),("3044.TW","健鼎"),("3037.TW","欣興"),("8046.TW","南電"),("3189.TW","景碩"),("6269.TW","台郡"),("6278.TW","台表科"),("2328.TW","廣宇"),
        ("3008.TW","大立光"),("3406.TW","玉晶光"),("3441.TW","聯一光"),("3362.TWO","先進光"),("3504.TW","揚明光"),("3019.TW","亞光"),("2409.TW","友達"),("3481.TW","群創"),("6116.TW","彩晶"),("6719.TW","力智"),
        ("3592.TW","瑞鼎"),("8105.TW","凌巨"),("2349.TW","錸德"),("2323.TW","中環"),("5439.TW","高技"),("2355.TW","敬鵬"),("2360.TW","致茂"),("2402.TW","毅嘉"),("3030.TW","德律"),("3557.TW","嘉威"),
        ("3591.TW","艾笛森"),("3622.TW","洋華"),("3673.TW","TPK-KY"),("3679.TW","新至陞"),("4976.TW","佳凌"),("5243.TW","乙盛-KY"),("5469.TW","瀚宇博"),("6141.TW","柏承"),("6191.TW","精成科"),("6205.TW","詮欣"),
        ("6224.TW","聚鼎"),("6251.TW","定穎"),("6290.TW","良維"),("6456.TW","GIS-KY"),("6674.TW","騰輝電子"),("8021.TW","尖點"),("8039.TW","台虹"),("8103.TW","瀚荃"),("8213.TW","志超"),("8215.TW","明基材"),
        ("2340.TW","光磊"),("2393.TW","億光"),("3437.TW","榮創"),("6168.TW","宏齊"),("6226.TW","光鼎"),("6443.TW","元晶"),("2419.TW","仲琦"),("3450.TW","聯鈞"),("4977.TW","眾達-KY"),("6426.TW","統新"),
        ("8011.TW","台通"),("2204.TW","中華車"),("2206.TW","三陽工業"),("1521.TW","大億"),("1522.TW","堤維西"),("1524.TW","耿鼎"),("1525.TW","江申"),("1533.TW","車王電"),("1568.TW","倉佑"),("2101.TW","南港"),
        ("2103.TW","台橡"),("2106.TW","建大"),("2108.TW","南帝"),("2497.TW","怡利電"),("3552.TW","同致"),("6288.TW","聯嘉"),("3003.TW","健和興"),("3023.TW","信邦"),("2392.TW","正崴"),("3024.TW","憶聲")
    ],
    "🧬 生技/綠能/其他 (100)": [
        ("6472.TW","保瑞"),("1795.TW","美時"),("4743.TWO","合一"),("4128.TWO","中天"),("6446.TWO","藥華藥"),("1760.TW","寶齡富錦"),("4162.TWO","智擎"),("4123.TWO","晟德"),("1701.TW","中化"),("1720.TW","生達"),
        ("4147.TW","龍燈-KY"),("4174.TWO","浩鼎"),("6492.TWO","生華科"),("6547.TWO","高端"),("6550.TW","北極星"),("6589.TW","台康生"),("4104.TW","佳醫"),("4119.TW","旭富"),("4137.TW","麗豐"),("1762.TW","中化生"),
        ("1702.TW","南僑"),("1704.TW","榮化"),("1707.TW","葡萄王"),("1708.TW","東鹼"),("1709.TW","和益"),("1710.TW","東聯"),("1711.TW","永光"),("1712.TW","興農"),("1713.TW","國化"),("1714.TW","和桐"),
        ("1718.TW","中纖"),("1721.TW","三晃"),("1722.TW","台肥"),("1723.TW","中碳"),("1724.TW","台硝"),("1725.TW","元禎"),("1726.TW","永記"),("1727.TW","中華化"),("1730.TW","花仙子"),("1731.TW","美吾華"),
        ("1732.TW","毛寶"),("1733.TW","五鼎"),("1734.TW","杏輝"),("1735.TW","日勝化"),("1736.TW","喬山"),("1737.TW","臺鹽"),("1752.TW","南光"),("1773.TW","勝一"),("1776.TW","展宇"),("1783.TW","和康生"),
        ("1786.TW","科妍"),("1789.TW","神隆"),("4106.TW","雃博"),("4108.TW","懷特"),("4114.TW","健喬"),("4133.TW","亞諾法"),("4141.TW","龍燈-KY"),("4142.TW","國光生"),("4144.TW","康聯-KY"),("4148.TW","全宇生技"),
        ("4155.TW","訊聯"),("4164.TW","承業醫"),("4190.TW","佐登-KY"),("4720.TW","德淵"),("4722.TW","國精化"),("4725.TW","信昌化"),("4737.TW","華廣"),("4739.TW","康普"),("4746.TW","台耀"),("4763.TW","材料-KY"),
        ("4764.TW","雙鍵"),("4766.TW","南寶"),("6405.TW","悅城"),("6504.TW","南六"),("8341.TW","日友"),("8404.TW","百和興業"),("8436.TW","大江"),("9902.TW","經緯航"),("9904.TW","寶成"),("9905.TW","大華"),
        ("9906.TW","欣巴巴"),("9907.TW","統一實"),("9908.TW","大台北"),("9910.TW","豐泰"),("9911.TW","櫻花"),("9912.TW","偉聯"),("9914.TW","美利達"),("9917.TW","中保"),("9918.TW","欣天然"),("9919.TW","康那香"),
        ("9921.TW","巨大"),("9924.TW","福興"),("9925.TW","新保"),("9926.TW","新海"),("9927.TW","泰銘"),("9928.TW","中視"),("9929.TW","秋雨"),("9930.TW","中聯資源"),("9931.TW","欣高"),("9933.TW","中鼎")
    ]
}
STOCK_MAP = {}
for cat_list in pool_500.values():
    for tid, sname in cat_list:
        STOCK_MAP[tid.split(".")[0]] = sname # 支援輸入 2330
        STOCK_MAP[tid] = sname               # 支援輸入 2330.TW

# --- [工具函數區：確保搜尋與轉換不報錯] ---

def get_full_ticker(tid):
    """【修正補件】自動判斷上市(.TW)或上櫃(.TWO)，解決 3211 等代號搜尋失敗問題"""
    if "." in tid: return tid
    # 根據大基石慣例：判斷開頭代號
    otc_list = ["31","32","33","34","35","36","41","49","52","53","54","61","62","64","65","66","80","82"]
    return f"{tid}.TWO" if any(tid.startswith(p) for p in otc_list) else f"{tid}.TW"

def get_stock_name(ticker):
    """根據代號找名稱，確保 UI 顯示正確中文"""
    # 移除點後綴進行比對
    base_id = ticker.split(".")[0]
    for cat in pool_500.values():
        for tid, tname in cat:
            if tid.split(".")[0] == base_id: return tname
    return ticker

def get_stock_perf(ticker, buy_price):
    """取得即時股價、漲跌與百分比 (補強容錯版)"""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="5d")
        if len(hist) < 2: return 0, "N/A", 0
        
        current_price = round(hist['Close'].iloc[-1], 2)
        prev_close = hist['Close'].iloc[-2]
        diff = round(current_price - prev_close, 2)
        change_pct = (diff / prev_close) * 100
        
        diff_str = f"{diff} ({change_pct:.2f}%)"
        return current_price, diff_str, change_pct
    except:
        return 0, "N/A", 0

def record_transaction(client, tid, action, shares, price, note):
    """記錄每一筆史詩級交易 (確保 trade_history 存在)"""
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

# --- [工具函數區結束] ---

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


# ==============================================================================
# 第六區：頁面佈局重整 (大腦佈局 + 500檔對接 + 完整按鍵還原)
# ==============================================================================
tab_scan, tab_intel, tab_history = st.tabs(["📊 戰策指揮所", "🌐 全球情報室", "📜 交易紀錄"])

with tab_scan:
    # 這裡維持你最愛的史詩大腦標題與 client 顯示
    st.title(f"🛡️ 12.8 大基石整合版: [{st.session_state.get('cur_c', 'Robert')}]")
    col_l, col_r = st.columns([1.6, 1.4]) 
    
    with col_l:
        # 1. 搜尋區 (完美對接 STOCK_MAP)
        with st.container(border=True):
            st.subheader("🔍 全球個股戰略搜索")
            s_input = st.text_input("輸入名稱或代號", placeholder="例如：3211", key="global_search_fix")
            if s_input:
                s_lower = s_input.lower().strip()
                # 從 STOCK_MAP 中搜尋匹配項
                matches = [(sid, sname) for sid, sname in STOCK_MAP.items() if s_lower in sid or s_lower in sname]
                if matches:
                    m_cols = st.columns(3)
                    for idx, (m_sid, m_sname) in enumerate(matches[:9]):
                        with m_cols[idx % 3]:
                            if st.button(f"🎯 {m_sname}", key=f"src_{idx}_{m_sid}"):
                                # 確保存入帶有 .TW 或 .TWO 的完整代號
                                st.session_state.selected_stock = get_full_ticker(m_sid) if 'get_full_ticker' in globals() else m_sid
                                st.rerun()

            # 2. 診斷呈現 (保留所有細節：評分顏色、籌碼狀態、佈局單位)
            sel_sid = st.session_state.get('selected_stock')
            if sel_sid:
                # 呼叫你要求的關鍵模組：get_stock_perf 與 generate_ai_tech_analysis
                p, d, cc = get_stock_perf(sel_sid, 0)
                res = generate_ai_tech_analysis(sel_sid, p, 0)
                if res:
                    # 顯示名稱時，從 STOCK_MAP 抓取，若無則顯示代號
                    display_name = STOCK_MAP.get(sel_sid.split('.')[0], '標的')
                    st.markdown(f"### 🎯 戰略診斷: {display_name} ({sel_sid})")
                    with st.container(border=True):
                        sc1, sc2 = st.columns([1.5, 1])
                        with sc1:
                            st.markdown(f"#### **評分: <span style='color:red;'>{res['score']}</span>**", unsafe_allow_html=True)
                            st.info(f"**診斷:** {res['msg']}")
                            # 顯示你要求的 Sentiment 籌碼欄位
                            st.markdown(f"**籌碼狀態:** {res.get('sent', '分析中')}")
                            st.write("---")
                            # 佈局按鍵區：完全還原張/股選擇與數量輸入
                            u_c1, u_c2 = st.columns(2)
                            q_val = u_c1.number_input("佈局數量", min_value=1, value=1, key=f"q_buy_{sel_sid}")
                            u_val = u_c2.radio("佈局單位", ["張", "股"], key=f"u_buy_{sel_sid}", horizontal=True)
                            if st.button(f"🚀 確認執行佈局", key=f"cf_buy_{sel_sid}", use_container_width=True):
                                # 存入本地數據庫 (local_db)
                                new_entry = pd.DataFrame([{
                                    'client': st.session_state.cur_c, 
                                    'id': sel_sid, 
                                    'name': display_name, 
                                    'buy_price': p, 
                                    'shares': q_val, 
                                    'unit': u_val, 
                                    'entry_reason': res['msg'], 
                                    'current_score': res['score'], 
                                    'last_diag': datetime.now().strftime("%m-%d")
                                }])
                                st.session_state.local_db = pd.concat([st.session_state.local_db, new_entry], ignore_index=True)
                                # 交易紀錄紀錄
                                if 'record_transaction' in globals():
                                    record_transaction(st.session_state.cur_c, sel_sid, "BUY", q_val, p, "AI 搜尋佈局")
                                save_data(); st.success(f"✅ {display_name} 已加入持股"); st.rerun()
                        with sc2:
                            st.metric("即時股價", p, d)
                            st.success(f"🎯 目標: {res['target']}")
                            st.warning(f"🛡️ 防守: {res['stop']}")

        # 3. 產業板塊區 (分類標籤修復 + 15檔高分股顯示)
        st.divider()
        st.subheader("🚀 產業板塊共振偵測")
        # 直接使用 pool_500 的 key 作為 radio 選項
        cat_choice = st.radio("選擇掃描板塊", list(pool_500.keys()), horizontal=True, key="cat_radio_v128")
        
        scored_data = []
        for tid, tname in pool_500[cat_choice]:
            p, d, cc = get_stock_perf(tid, 0)
            res = generate_ai_tech_analysis(tid, p, 0)
            if res:
                res.update({'tid': tid, 'tname': tname, 'price': p, 'diff': d, 'base_id': tid.split('.')[0]})
                scored_data.append(res)
        
        # 依評分排序，顯示前 15 檔
        top_picks = sorted(scored_data, key=lambda x: x['score'], reverse=True)[:15]
        for item in top_picks:
            with st.expander(f"⭐ {item['tname']} | 評分: {item['score']} | 價: {item['price']}"):
                st.write(f"🧠 AI: {item['msg']}")
                k_c1, k_c2, k_c3 = st.columns([1, 1.2, 1.8])
                quick_q = k_c1.number_input("數量", min_value=1, value=1, key=f"scan_qty_{item['tid']}_{i}"
                quick_u = k_c2.radio("單位", ["張", "股"], key=f"qu_{item['tid']}", horizontal=True)
                if k_c3.button(f"🚀 快速佈局 {item['tname']}", key=f"bp_{item['tid']}", use_container_width=True):
                    new_entry = pd.DataFrame([{
                        'client': st.session_state.cur_c, 
                        'id': item['tid'], 
                        'name': item['tname'], 
                        'buy_price': item['price'], 
                        'shares': quick_q, 
                        'unit': quick_u, 
                        'entry_reason': item['msg'], 
                        'current_score': item['score'], 
                        'last_diag': datetime.now().strftime("%m-%d")
                    }])
                    st.session_state.local_db = pd.concat([st.session_state.local_db, new_entry], ignore_index=True)
                    if 'record_transaction' in globals():
                        record_transaction(st.session_state.cur_c, item['tid'], "BUY", quick_q, item['price'], "板塊掃描進場")
                    save_data(); st.rerun()

    with col_r:
        # 右側持股監控：完全保留總損益計算與「減持按鈕」
        st.subheader(f"💼 持股監控: [{st.session_state.cur_c}]")
        my_h = st.session_state.local_db[st.session_state.local_db['client'] == st.session_state.cur_c]
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
                    
                    # --- 減持按鈕完整還原 ---
                    e_c1, e_c2 = st.columns([1, 1.2])
                    exit_q = e_c1.number_input("減持數量", min_value=1, max_value=max(1, int(row['shares'])), value=1, key=f"exq_{idx}")
                    if e_c2.button(f"❌ 執行減持", key=f"exb_{idx}", use_container_width=True):
                        if exit_q >= row['shares']: 
                            st.session_state.local_db = st.session_state.local_db.drop(idx)
                        else: 
                            st.session_state.local_db.at[idx, 'shares'] -= exit_q
                        if 'record_transaction' in globals():
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
    with tab_intel:
    st.header("🌎 全球戰略情報大腦 (24H 繁體深度更新)")

    # 1. 頻道切換按鈕
    if 'news_mode' not in st.session_state:
        st.session_state.news_mode = "🇹🇼 台美日中 (地緣)"

    c1, c2 = st.columns(2)
    if c1.button("🇹🇼 台美日中・周邊情勢", use_container_width=True):
        st.session_state.news_mode = "🇹🇼 台美日中 (地緣)"
    if c2.button("🌐 國際戰略・全球動態", use_container_width=True):
        st.session_state.news_mode = "🌐 國際戰略 (全球)"

    # 2. 呼叫上方定義好的大腦
    with st.spinner("📡 正在接入全球衛星情報網..."):
        all_news, trends = fetch_and_score_intel()
        st.write(f"🔥 **今日戰略焦熱點：** " + " ".join([f"`{w}`" for w in trends[:10]]))

        target_cat = st.session_state.news_mode
        filtered = [item for item in all_news if item['cat'] == target_cat]

        # 3. 兩欄式精緻排版 (保留分級標籤)
        nl, nr = st.columns(2)
        for i, item in enumerate(filtered):
            n = item['data']
            score = item['score']
            color = "#FF4B4B" if score >= 80 else ("#FFD700" if score >= 70 else "#00D1FF")
            label = "⚡ 重大戰略" if score >= 80 else ("🚨 深度關注" if score >= 70 else "🔍 即時情報")

            card = f"""
                <div style='border-left:5px solid {color}; padding:15px; margin-bottom:15px; background:white; border-radius:10px; border:1px solid #eee; box-shadow: 2px 2px 5px rgba(0,0,0,0.05);'>
                    <div style='display:flex; justify-content:space-between; margin-bottom:5px;'>
                        <span style='background:{color}; color:{"white" if score>=80 else "black"}; padding:2px 8px; border-radius:5px; font-size:10px; font-weight:bold;'>{label}</span>
                        <span style='color:grey; font-size:10px;'>🕒 {item['time']}</span>
                    </div>
                    <a href='{n.link}' target='_blank' style='text-decoration:none; color:#1e1e1e; font-size:14px; font-weight:bold;'>{n.title}</a>
                </div>
            """
            if i % 2 == 0: nl.markdown(card, unsafe_allow_html=True)
            else: nr.markdown(card, unsafe_allow_html=True)



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
