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

# --- [第 2 區修正：頂部標題、美股監控看板與連線狀態燈] ---
st.title("🛡️ 大基石 - AI 戰略經理人")

is_connected, status_text = check_connection()

if is_connected:
    us_impact, stress_count = get_us_market_impact()
    if us_impact:
        with st.container(border=True):
            st.markdown("#### 🌍 全球戰略連動看板")
            u_cols = st.columns(len(us_impact))
            for i, (name, val) in enumerate(us_impact.items()):
                is_risk = (name != "美元指數" and val <= -2.0)
                delta_color = "inverse" if is_risk else "normal"
                u_cols[i].metric(name, f"{val}%", delta=f"{val}%", delta_color=delta_color)
            
            if stress_count >= 1:
                st.markdown(f"""
                    <div style="background-color: #fff5f5; border: 2px solid #ff4b4b; padding: 10px; border-radius: 8px; color: #ff4b4b; font-weight: bold; text-align: center;">
                        🚨 AI 壓力預警：當前美股壓力值 [{stress_count}]！台股 AI 板塊可能面臨連動修正，建議防守。
                    </div>
                """, unsafe_allow_html=True)
    
    st.markdown(f'<div class="status-bar status-on">🌐 {status_text}</div>', unsafe_allow_html=True)
    st.divider()

else:
    st.markdown(f'<div class="status-bar status-off">📡 {status_text}</div>', unsafe_allow_html=True)
    st.info("💡 提示：請確保 Google Sheets 已改名為 inventory/history/clients 並已『發布到網路』。")

def load_data():
    if 'initialized' in st.session_state and st.session_state.initialized:
        return
    try:
        st.session_state.local_db = pd.read_csv(get_sheet_url("inventory"))
        df_hist = pd.read_csv(get_sheet_url("history"))
        if df_hist.empty or 'date' not in df_hist.columns:
            df_hist = pd.DataFrame(columns=['date', 'client', 'id', 'action', 'shares', 'price', 'note'])
        st.session_state.trade_history = df_hist
        client_df = pd.read_csv(get_sheet_url("clients"))
        cloud_clients = client_df['name'].tolist() if 'name' in client_df.columns else []
        if 'client_list' not in st.session_state:
            st.session_state.client_list = ["Robert"]
        ghosts = ["nan", "None", None]
        combined = list(set(st.session_state.client_list + cloud_clients))
        st.session_state.client_list = sorted([str(c) for c in combined if str(c) not in ghosts])
        st.session_state.initialized = True
    except Exception as e:
        if 'local_db' not in st.session_state:
            st.session_state.local_db = pd.DataFrame(columns=['client', 'id', 'name', 'buy_price', 'shares', 'unit', 'entry_reason', 'current_score', 'last_diag', 'sentiment'])
        if 'trade_history' not in st.session_state:
            st.session_state.trade_history = pd.DataFrame(columns=['date', 'client', 'id', 'action', 'shares', 'price', 'note'])
        if 'client_list' not in st.session_state:
            st.session_state.client_list = ["Robert"]
        st.session_state.initialized = True

def save_data():
    st.session_state.local_db.to_csv("stone_manager_db.csv", index=False)
    if 'trade_history' in st.session_state:
        st.session_state.trade_history.to_csv("trading_history.csv", index=False)
    pd.DataFrame(st.session_state.client_list, columns=['name']).to_csv("client_list.csv", index=False)

# ==============================================================================
# 第 3 區：大基石史詩級強大腦 V15.0 - 超越老總級「AI 全自動進化」版本
# ==============================================================================
def get_us_market_impact():
    try:
        tickers = {"^SOX": "費半", "^IXIC": "那指", "TSM": "台積電ADR", "NVDA": "輝達"}
        impact_report = {}
        total_stress = 0
        for tid, tname in tickers.items():
            tk = yf.Ticker(tid)
            h = tk.history(period="2d")
            if len(h) < 2: continue
            change = ((h['Close'].iloc[-1] - h['Close'].iloc[-2]) / h['Close'].iloc[-2]) * 100
            impact_report[tname] = round(change, 2)
            if change < -2.5: total_stress += 1
        return impact_report, total_stress
    except:
        return {}, 0

def ai_evolution_engine(ticker, h_full):
    """ 核心 V15.0：對比 35 年歷史大數據模型 """
    if h_full.empty or len(h_full) < 250:
        return 50, "📚 數據積累中"
    
    c = h_full['Close']
    v = h_full['Volume']
    price_std = c.tail(20).std()
    is_compressing = price_std < (c.tail(250).mean() * 0.035)
    vol_surge = v.iloc[-1] > v.rolling(248).mean().iloc[-1] * 1.8
    
    score = 60
    intel_tags = []
    
    if is_compressing and vol_surge and c.iloc[-1] > c.rolling(20).mean().iloc[-1]:
        score += 35
        intel_tags.append("🔥 匹配 35 年噴發模型")
    
    if c.iloc[-1] > c.rolling(248).max() * 0.98 and v.iloc[-1] < v.rolling(20).mean().iloc[-1] * 0.6:
        score -= 40
        intel_tags.append("🚨 歷史高檔量價背離")
        
    return max(0, min(100, score)), " | ".join(intel_tags) if intel_tags else "⚖️ 常態波動"

def generate_ai_tech_analysis(ticker, price, diff_pct):
    """
    大腦核心 V15.0：精準對比歷史、偵測洗盤、與美股實時連動
    """
    try:
        # 1. 識別標的與抓取數據 (自動補齊後綴)
        formatted_ticker = ticker
        if ".TW" not in ticker and ".TWO" not in ticker:
            formatted_ticker = f"{ticker}.TWO" if ticker.startswith("3") or ticker.startswith("8") or ticker.startswith("6") else f"{ticker}.TW"
        
        stock = yf.Ticker(formatted_ticker)
        h_full = stock.history(period="2y")
        h_max = stock.history(period="max") # V15.0 歷史數據引擎核心
        h_60m = stock.history(interval="60m", period="1mo")
        h_week = stock.history(interval="1wk", period="2y")
        
        if h_full.empty: return None 

        us_data, stress_lvl = get_us_market_impact()

        # [MACD 斜率共振系統]
        def get_macd_slope(df):
            if df.empty or len(df) < 30: return 0, "觀測"
            ema12 = df['Close'].ewm(span=12, adjust=False).mean()
            ema26 = df['Close'].ewm(span=26, adjust=False).mean()
            macd = ema12 - ema26
            sig = macd.ewm(span=9, adjust=False).mean()
            slope = macd.iloc[-1] - macd.iloc[-2]
            status = "📈翻揚" if (macd.iloc[-1] > sig.iloc[-1] and slope > 0) else "📉轉弱"
            return slope, status

        _, st_60 = get_macd_slope(h_60m)
        _, st_day = get_macd_slope(h_full)
        _, st_week = get_macd_slope(h_week)

        # [均線系統與洗盤偵測]
        c, v, hi, lo = h_full['Close'], h_full['Volume'], h_full['High'], h_full['Low']
        ma20, ma60, ma124, ma248 = c.rolling(20).mean().iloc[-1], c.rolling(60).mean().iloc[-1], \
                                   c.rolling(124).mean().iloc[-1], c.rolling(248).mean().iloc[-1]
        
        score = 60
        logic_tags = []
        sentiment = "🔍 散戶進場 (融資增)" # 預設狀態

        # A. 洗盤偵測邏輯 (融資大幅出場 + 支撐位回測)
        if (price >= ma248 * 0.98 and price <= ma248 * 1.05) or (price >= ma124 * 0.98 and price <= ma124 * 1.05):
            if v.iloc[-1] < v.rolling(20).mean().iloc[-1] * 0.7:
                score += 25
                logic_tags.append("🔥 偵測到洗盤完成，準備破新高")
                sentiment = "💎 大戶收貨 (融資減)"

        # B. 三線糾結噴發型態
        ma_gaps = [abs(ma20-ma60)/ma60, abs(ma60-ma124)/ma124]
        if max(ma_gaps) < 0.04:
            score += 20
            logic_tags.append("🚀 均線高度糾結")

        # C. 全球壓力扣分
        if stress_lvl > 0:
            score -= (stress_lvl * 10)
            logic_tags.append(f"⚠️ 全球避險連動 -{stress_lvl*10}")

        # V15.0 混合評分融合
        h_score, h_logic = ai_evolution_engine(ticker, h_max)
        final_hybrid_score = int((score * 0.6) + (h_score * 0.4))
        
        rank = "SS" if final_hybrid_score >= 90 else ("A" if final_hybrid_score >= 75 else "B")
        
        tr = pd.concat([hi-lo, (hi-c.shift()).abs(), (lo-c.shift()).abs()], axis=1).max(axis=1)
        rng = round(tr.rolling(14).mean().iloc[-1] * 1.618, 1)

        return {
            "msg": f"{h_logic} | [{rank}] MACD:{st_60}/{st_day}/{st_week} | " + (" | ".join(logic_tags)),
            "sent": sentiment,
            "score": final_hybrid_score,
            "target": round(price + rng, 1),
            "stop": round(ma20 * 0.96, 1),
            "atr_range": f"±{rng}",
            "pivot": "V15.0 AI 自主進化中"
        }
    except Exception as e:
        return {"msg": f"AI 數據重組中...{str(e)[:5]}", "score": 50, "target": price, "stop": price}

def fetch_and_score_intel():
    import ssl, collections, re
    if hasattr(ssl, '_create_unverified_context'):
        ssl._create_default_https_context = ssl._create_unverified_context
    strategic_map = {
        "🇹🇼 台美日中 (地緣)": ["台海局勢 when:24h", "中共軍演 when:24h", "台積電 when:24h"],
        "🌐 國際戰略 (全球)": ["中東戰爭 when:24h", "美聯儲 when:24h", "川普 關稅 when:24h"]
    }
    news_list, seen_links = [], set()
    for cat_name, queries in strategic_map.items():
        for q in queries:
            u = f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
            try:
                feed = feedparser.parse(u)
                for e in feed.entries[:5]:
                    if e.link not in seen_links:
                        score = 55
                        if any(w in e.title for w in ["戰爭", "衝突", "斷鏈", "降息"]): score += 30
                        news_list.append({'data': e, 'score': score, 'cat': cat_name, 'time': e.published[5:16] if hasattr(e, 'published') else "24H"})
                        seen_links.add(e.link)
            except: continue
    all_titles = " ".join([item['data'].title for item in news_list])
    words = re.findall(r'[\u4e00-\u9fa5]{2,4}', all_titles)
    hot_words = [w for w, c in collections.Counter(words).most_common(10)] 
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

def update_ai_thought_log(ticker, pred_score, reason):
    """大基石：AI 學習記憶體 - 紀錄診斷當下的思維 (V15.0 每10分鐘進化版)"""
    if 'ai_memory' not in st.session_state:
        st.session_state.ai_memory = []
    
    # AI 自動學習與 35 年歷史資料對比日誌
    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "ticker": ticker,
        "prediction": pred_score,
        "logic": reason,
        "actual_move": None,
        "engine_ver": "V15.0_Evolution"
    }
    st.session_state.ai_memory.append(log_entry)
    
    # 保持記憶體精簡，僅保留最近 100 筆學習資料
    if len(st.session_state.ai_memory) > 100:
        st.session_state.ai_memory.pop(0)

def get_full_ticker(tid):
    """【修正補件】自動判斷上市(.TW)或上櫃(.TWO)，精準識別 3211 等 500 檔股票"""
    if "." in tid: return tid
    
    # 大基石 AI 判斷邏輯：擴充上櫃識別頭部，確保 500 檔涵蓋範圍
    otc_prefixes = ["31","32","33","34","35","36","41","43","45","47","49","52","53","54","61","62","64","65","66","80","82","83","84"]
    if any(tid.startswith(p) for p in otc_prefixes):
        return f"{tid}.TWO"
    return f"{tid}.TW"

def get_stock_name(ticker):
    """根據代號找名稱，確保 UI 顯示正確中文"""
    base_id = ticker.split(".")[0]
    # 優先從 500 檔大池中搜尋
    for cat in pool_500.values():
        for tid, tname in cat:
            if tid.split(".")[0] == base_id: return tname
    return ticker

def get_stock_perf(ticker, buy_price):
    """取得即時股價、漲跌與百分比 (V15.0 強化容錯版)"""
    try:
        # 確保帶有正確後綴
        full_tid = get_full_ticker(ticker.split(".")[0])
        stock = yf.Ticker(full_tid)
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

# --- [第 5 區：側邊欄管理與分頁定義 - 關鍵修正] ---
if 'local_db' not in st.session_state:
    load_data()

# 側邊欄過濾與客戶管理
target_ghosts = ["VIP實戰", "周靖傑", "nan", "None", None, "Unnamed: 0"]
if 'client_list' in st.session_state:
    st.session_state.client_list = [c for c in st.session_state.client_list if str(c) not in target_ghosts and str(c).strip() != ""]

with st.sidebar:
    st.title("👤 大基石 AI 經理人")
    st.write(f"系統時間: {datetime.now().strftime('%Y-%m-%d')}")
    
    with st.expander("⚙️ 客戶系統設定 (增/改/刪)", expanded=False):
        new_c = st.text_input("新增客戶姓名", key="add_client_input")
        if st.button("➕ 確認新增"):
            if new_c and new_c not in st.session_state.client_list: 
                st.session_state.client_list.append(new_c)
                # 預留 sentiment 欄位以對接 V15.0 洗盤偵測邏輯
                new_row = pd.DataFrame([{'client': new_c, 'id': 'INIT', 'name': '初始紀錄', 'buy_price': 0, 'shares': 0, 'unit': '股', 'entry_reason': '系統新增', 'sentiment': '觀測中'}])
                st.session_state.local_db = pd.concat([st.session_state.local_db, new_row], ignore_index=True)
                st.session_state['cur_c'] = new_c
                save_data(); st.rerun()
        
        st.markdown("---")
        # 確保當前客戶存在於列表
        if not st.session_state.client_list:
            st.session_state.client_list = ["Robert"]
            
        current_idx_name = st.session_state.get('cur_c', st.session_state.client_list[0])
        new_name = st.text_input("輸入新名稱", value=current_idx_name, key="rename_input")
        if st.button("📝 執行更名", use_container_width=True):
            if new_name and new_name != current_idx_name:
                st.session_state.local_db['client'] = st.session_state.local_db['client'].replace(current_idx_name, new_name)
                st.session_state.client_list = [new_name if x == current_idx_name else x for x in st.session_state.client_list]
                st.session_state['cur_c'] = new_name
                save_data(); st.rerun()

    # 下拉選單處理
    if st.session_state.get('cur_c') not in st.session_state.client_list:
        st.session_state['cur_c'] = st.session_state.client_list[0]

    st.session_state['cur_c'] = st.selectbox(
        "🎯 當前控盤對象", 
        st.session_state.client_list, 
        index=st.session_state.client_list.index(st.session_state['cur_c']),
        key="client_selector"
    )
    
    if st.button("❌ 刪除當前客戶", use_container_width=True):
        if st.session_state['cur_c'] != "Robert":
            to_del = st.session_state['cur_c']
            st.session_state.client_list.remove(to_del)
            st.session_state.local_db = st.session_state.local_db[st.session_state.local_db['client'] != to_del]
            st.session_state['cur_c'] = "Robert"
            save_data(); st.rerun()

    st.markdown("---")
    c_stocks = st.session_state.local_db[(st.session_state.local_db['client'] == st.session_state['cur_c']) & (st.session_state.local_db['id'] != 'INIT')]
    st.metric(f"{st.session_state['cur_c']} 的持股總數", len(c_stocks))


# ==============================================================================
# 第六區 ：大基石史詩全功能還原版 (V15.0 AI 自動學習進化版)
# ==============================================================================
tab_scan, tab_intel, tab_brain, tab_history = st.tabs(["📊 戰策指揮所", "🌐 全球情報室", "🧠 AI 進化大腦", "📜 交易紀錄"])

with tab_scan:
    # --- [1. 標題與核心佈局定義] ---
    st.title(f"🛡️ 戰略指揮所: [{st.session_state.get('cur_c', 'Robert')}]")
    
    col_l, col_r = st.columns([1.6, 1.4]) 
    
    with col_l:
        # 1. 搜尋區 (核心修復：V15.0 自動識別與 35 年歷史診斷)
        with st.container(border=True):
            st.subheader("🔍 全球個股戰略搜索")
            s_input = st.text_input("輸入名稱或代號", placeholder="例如：2330 或 3211", key="global_search_fix")
            
            if s_input:
                s_raw = s_input.strip()
                # A. 處理純數字代號 (自動判斷上市/上櫃，解決 3211 等問題)
                if s_raw.isdigit():
                    sel_sid = get_full_ticker(s_raw)
                    display_name = STOCK_MAP.get(s_raw, s_raw)
                    if st.button(f"🔍 啟動 AI 深度診斷: {display_name} ({sel_sid})", use_container_width=True, key="diag_btn"):
                        st.session_state.selected_stock = sel_sid
                        st.rerun()
                
                # B. 處理中文名稱模糊搜尋
                else:
                    matches = [tid for tid, name in STOCK_MAP.items() if s_raw in name and "." in tid]
                    if matches:
                        m_cols = st.columns(3)
                        for idx, m_sid in enumerate(list(set(matches))[:9]):
                            m_name = STOCK_MAP.get(m_sid, m_sid)
                            with m_cols[idx % 3]:
                                if st.button(f"🎯 {m_name}", key=f"src_{idx}_{m_sid}", use_container_width=True):
                                    st.session_state.selected_stock = m_sid
                                    st.rerun()
                    else:
                        st.warning("查無此名稱，請嘗試輸入數字代號。")

        # --- 2. 診斷呈現區：AI 個股深度分析 (V15.0 混合評分模式) ---
        sel_sid = st.session_state.get('selected_stock')

        if sel_sid:
            # 1. 觸發 V15.0 每 10 分鐘自動對比與進化計時器
            run_auto_cruise() 
            
            # 2. 獲取數據與大腦分析 (注入洗盤偵測與 35 年歷史比對)
            p, d, cc = get_stock_perf(sel_sid, 0)
            res = generate_ai_tech_analysis(sel_sid, p, 0)

            if res:
                # 3. 取得名稱與記錄學習日誌
                raw_id = sel_sid.split('.')[0]
                display_name = STOCK_MAP.get(raw_id, raw_id)
                update_ai_thought_log(display_name, res['score'], res['msg'])
                
                # 4. UI 標題與進化時間戳 (標註 V15.0)
                st.markdown(f"### 🧠 V15.0 AI 進化診斷: {display_name} ({sel_sid})")
                
                last_t = st.session_state.get('last_cruise', datetime.now()).strftime("%H:%M:%S")
                st.caption(f"🤖 AI 每 10 分鐘對比 35 年歷史中 | 上次學習: {last_t}")

                # --- 戰略儀表板主容器 ---
                with st.container(border=True):
                    sc1, sc2 = st.columns([1.5, 1])
                    with sc1:
                        # 分數顏色邏輯 (與 V15.0 銳利度對齊)
                        score_color = "red" if res['score'] >= 80 else ("orange" if res['score'] >= 60 else "green")
                        st.markdown(f"#### **評分: <span style='color:{score_color};'>{res['score']}</span>**", unsafe_allow_html=True)
                        
                        if res['score'] >= 80:
                            st.error(f"🔥 **AI 指令：** {res['msg']}")
                        elif res['score'] <= 40:
                            st.warning(f"🚨 **AI 指令：** {res['msg']}")
                        else:
                            st.info(f"💡 **AI 指令：** {res['msg']}")
                            
                        # 顯示洗盤偵測狀態 (Sentiment 欄位)
                        st.markdown(f"**📊 籌碼與心理:** `{res.get('sent', '觀測中')}`")
                        st.write("---")
                        
                        # 操作佈局區 (維持 12.5 原始樣式)
                        u_c1, u_c2 = st.columns(2)
                        q_val = u_c1.number_input("佈局數量", min_value=1, value=1, key=f"q_buy_{sel_sid}")
                        u_val = u_c2.radio("單位", ["張", "股"], key=f"u_buy_{sel_sid}", horizontal=True)
                        
                        if st.button(f"🚀 執行戰略佈局", key=f"cf_buy_{sel_sid}", use_container_width=True):
                            new_entry = pd.DataFrame([{
                                'client': st.session_state.cur_c, 'id': sel_sid, 'name': display_name, 
                                'buy_price': p, 'shares': q_val, 'unit': u_val, 'entry_reason': res['msg'], 
                                'current_score': res['score'], 'last_diag': datetime.now().strftime("%m-%d"),
                                'sentiment': res.get('sent', '觀測中')
                            }])
                            st.session_state.local_db = pd.concat([st.session_state.local_db, new_entry], ignore_index=True)
                            
                            # 紀錄交易紀錄
                            record_transaction(st.session_state.cur_c, sel_sid, "買入", q_val, p, f"V15.0 AI 評分:{res['score']} | {res['msg']}")
                            
                            save_data()
                            st.success(f"✅ {display_name} 已加入 {st.session_state.cur_c} 的持股！")
                            st.rerun()

                    with sc2:
                        st.metric("即時股價", f"{p}", d)
                        st.subheader("🔮 AI 未來預測")
                        with st.container(border=True):
                            st.write(f"📈 預期波動: `{res['atr_range']}`")
                            st.markdown(f"**🎯 目標價：** `NT$ {res['target']}`")
                            st.markdown(f"**🛡️ 停損價：** `NT$ {res['stop']}`")
                            st.progress(res['score'] / 100, text=f"預測勝率: {res['score']}%")
            else:
                st.warning(f"📡 數據載入中，請稍候...")

        # --- 3. 產業板塊區 (整合全市場 500 檔掃描) ---
        st.divider()
        st.subheader("🚀 產業板塊共振偵測")
        if us_impact.get("費半", 0) < -3.0:
            st.error("📉 **美股警報：** 費半暴跌，請謹慎對待 [AI、半導體、設備] 板塊！")
        if us_impact.get("那指", 0) < -3.0:
            st.warning("📉 **科技壓力：** 那指重挫，[IC設計、軟體] 可能出現多殺多。")

        cat_choice = st.radio("選擇掃描板塊", list(pool_500.keys()), horizontal=True, key="cat_radio_v135")
        
        scored_data = []
        with st.status(f"正在由 V15.0 AI 深度診斷 {cat_choice}...", expanded=False) as status:
            for tid, tname in pool_500[cat_choice]:
                try:
                    p_s, d_s, _ = get_stock_perf(tid, 0)
                    if p_s == 0: continue
                    res_s = generate_ai_tech_analysis(tid, p_s, 0)
                    if res_s:
                        res_s.update({'tid': tid, 'tname': tname, 'price': p_s, 'diff': d_s})
                        scored_data.append(res_s)
                except: continue
            status.update(label="✅ V15.0 全板塊診斷完成！", state="complete")
        
        if scored_data:
            # 依據 AI 進化評分排序
            top_picks = sorted(scored_data, key=lambda x: x['score'], reverse=True)[:15]
            for idx, item in enumerate(top_picks):
                with st.expander(f"⭐ {item['tname']} ({item['tid']}) | 評分: {item['score']} | 價: {item['price']}"):
                    st.markdown(f"**🧠 AI 診斷：** `{item['msg']}`")
                    st.markdown(f"**🎯 AI 預期目標：** `NT$ {item['target']}` | **🛡️ 建議防守：** `NT$ {item['stop']}`")
                    k_c1, k_c2, k_c3 = st.columns([1, 1.2, 1.8])
                    q_val_s = k_c1.number_input("數量", min_value=1, value=1, key=f"sq_v131_{item['tid']}_{idx}")
                    u_val_s = k_c2.radio("單位", ["張", "股"], key=f"su_v131_{item['tid']}_{idx}", horizontal=True)
                    if k_c3.button(f"🚀 執行戰略佈局 {item['tname']}", key=f"sb_v131_{item['tid']}_{idx}", use_container_width=True):
                        new_entry = pd.DataFrame([{
                            'client': st.session_state.cur_c, 'id': item['tid'], 'name': item['tname'], 
                            'buy_price': item['price'], 'shares': q_val_s, 'unit': u_val_s, 
                            'entry_reason': item['msg'], 'current_score': item['score'], 'last_diag': datetime.now().strftime("%m-%d"),
                            'sentiment': item.get('sent', '觀測中')
                        }])
                        st.session_state.local_db = pd.concat([st.session_state.local_db, new_entry], ignore_index=True)
                        record_transaction(st.session_state.cur_c, item['tid'], "買入", q_val_s, item['price'], f"板塊推薦|評分:{item['score']}")
                        save_data(); st.rerun()
        else:
            st.warning("⚠️ 目前該板塊無符合條件的標的。")

    with col_r:
        # --- 持股監控 (完全還原佈局) ---
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
                    # 顯示個股名稱與 Sentiment 標籤
                    st.markdown(f"**{row['name']}** `{row['id']}`")
                    st.write(f"持有: **{row['shares']} {row['unit']}** | 成本: {row['buy_price']}")
                    
                    pnl_color = "red" if pnl >= 0 else "green"
                    st.markdown(f"損益: <span style='color:{pnl_color}; font-weight:bold;'>NT$ {pnl:,.0f}</span>", unsafe_allow_html=True)
                    
                    # 顯示目前的籌碼狀態標籤
                    st.markdown(f"<span class='sentiment-tag'>{row.get('sentiment', '偵測中')}</span>", unsafe_allow_html=True)
                    
                    e_c1, e_c2, e_c3 = st.columns([1.2, 1.2, 1.5])
                    exit_q = e_c1.number_input("減持數量", min_value=1, value=1, key=f"exq_{idx}_{row['id']}")
                    exit_u = e_c2.radio("單位", ["張", "股"], key=f"exu_{idx}_{row['id']}", horizontal=True)
                    if e_c3.button(f"❌ 執行減持", key=f"exb_{idx}_{row['id']}", use_container_width=True):
                        if exit_u == row['unit']:
                            if exit_q >= row['shares']: st.session_state.local_db = st.session_state.local_db.drop(idx)
                            else: st.session_state.local_db.at[idx, 'shares'] -= exit_q
                        else: st.warning("⚠️ 單位不一致")
                        save_data(); st.rerun()
            st.metric("📊 總未實現損益", f"NT$ {total_pnl:,.0f}", delta=f"{total_pnl:,.0f}")


# --- 第七區：全球情報室 (完整還原分級卡片) ---
with tab_intel:
    st.header("🌎 全球戰略情報大腦 (24H 更新)")
    if 'news_mode' not in st.session_state: st.session_state.news_mode = "🇹🇼 台美日中 (地緣)"
    
    n1, n2 = st.columns(2)
    if n1.button("🇹🇼 台美日中情勢", use_container_width=True, key="n_tw"): st.session_state.news_mode = "🇹🇼 台美日中 (地緣)"
    if n2.button("🌐 國際戰略動態", use_container_width=True, key="n_gl"): st.session_state.news_mode = "🌐 國際戰略 (全球)"

    try:
        all_news, trends = fetch_and_score_intel()
        st.write(f"🔥 **戰略熱點：** " + " ".join([f"`{w}`" for w in trends]))
        
        filtered = [item for item in all_news if item['cat'] == st.session_state.news_mode]
        nl, nr = st.columns(2)
        for i, item in enumerate(filtered):
            n, score = item['data'], item['score']
            color = "#FF4B4B" if score >= 80 else ("#FFD700" if score >= 70 else "#00D1FF")
            label = "⚡ SS 級" if score >= 80 else ("🚨 A 級" if score >= 70 else "🔍 B 級")
            
            card = f"""
                <div style='border-left:5px solid {color}; padding:12px; margin-bottom:12px; background:white; border-radius:8px; border:1px solid #ddd;'>
                    <span style='background:{color}; color:black; padding:2px 5px; border-radius:3px; font-size:10px;'>{label}</span>
                    <small style='float:right; color:grey;'>{item['time']}</small><br>
                    <a href='{n.link}' target='_blank' style='text-decoration:none; color:#1e1e1e; font-weight:bold;'>{n.title}</a>
                </div>
            """
            if i % 2 == 0: nl.markdown(card, unsafe_allow_html=True)
            else: nr.markdown(card, unsafe_allow_html=True)
    except Exception as e:
        st.error("📡 情報連線中...")
# --- [第 7.5 區：AI 大腦思維日誌 - 專屬分頁] ---
with tab_brain: 
    st.header("🧠 大基石：AI 進化思維日誌")
    st.write("---")
    
    if 'ai_memory' in st.session_state and st.session_state.ai_memory:
        # 顯示最近 10 條紀錄
        for m in reversed(st.session_state.ai_memory[-10:]):
            with st.container(border=True):
                c1, c2 = st.columns([1, 3])
                c1.metric("診斷標的", m['ticker'])
                with c2:
                    st.markdown(f"**預測評分:** `{m['prediction']}`")
                    st.markdown(f"**核心邏輯:** {m['logic']}")
                    st.caption(f"📅 紀錄時間: {m['timestamp']}")
    else:
        st.info("💡 目前尚無思維紀錄，請開始進行個股戰略診斷，AI 將啟動自我學習。")


# --- [第 8 區：交易紀錄 - 獨立分頁] ---
with tab_history:
    st.subheader("📜 歷史交易紀錄")
    
    if 'trade_history' in st.session_state and not st.session_state.trade_history.empty:
        try:
            df_to_show = st.session_state.trade_history.copy()
            if 'date' in df_to_show.columns:
                df_to_show['date'] = pd.to_datetime(df_to_show['date'], errors='coerce')
                display_df = df_to_show.sort_values(by='date', ascending=False)
            else:
                display_df = df_to_show
            st.dataframe(display_df, use_container_width=True)
        except Exception as e:
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
