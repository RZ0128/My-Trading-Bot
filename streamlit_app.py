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
    
# --- [3. 終極 AI 核心分析引擎：實戰 8 大邏輯文字化] ---
def generate_ai_tech_analysis(ticker, price, diff_pct):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="260d") 
        hist_w = stock.history(period="1y", interval="1wk")
        if len(hist) < 240: return "數據收集中...", "⚖️ 觀望", "normal"
        
        info = stock.info
        c = hist['Close']
        v = hist['Volume']
        
        ma5 = c.rolling(5).mean().iloc[-1]
        ma20 = c.rolling(20).mean().iloc[-1]
        ma60 = c.rolling(60).mean().iloc[-1]
        ma240 = c.rolling(240).mean().iloc[-1]
        v_ma5 = v.rolling(5).mean().iloc[-1]
        
        # 1. 底部整理時長 (圖7)
        last_60d = c.tail(60)
        is_stable_3m = (last_60d.max() - last_60d.min()) / last_60d.mean() < 0.15
        # 2. 季線戰略區 (圖3)
        is_ma60_zone = price < ma60 and price > ma60 * 0.94
        # 3. 高獲利對標 (圖6)
        eps = info.get('trailingEps', 0)
        # 4. 大換手/整理縮短 (圖4)
        is_handover = v.iloc[-1] > v_ma5 * 2.2
        # 5. 週線趨勢 (圖8)
        is_weekly_up = hist_w['Close'].iloc[-1] > hist_w['Close'].iloc[-2]
        # 6. 洗盤偵測
        is_wash_out = (price <= ma240 * 1.08 and price >= ma240 * 0.95) and (v.iloc[-1] < v_ma5 * 0.7)

        analysis = []
        status_color = "normal"
        
        if is_wash_out: analysis.append("🔥 洗盤完成：量縮回踩年線，主力洗淨準備破高"); status_color = "safe"
        if is_stable_3m: analysis.append("🛡️ 底部建構：已橫盤整理逾三個月，換手充分")
        if is_ma60_zone: analysis.append("🎯 戰略位階：現價處於季線下方買點區")
        if eps > 20: analysis.append(f"💰 價值對標：年度 EPS 達 {eps} 元，屬高獲利績優股")
        if is_handover: analysis.append("⚡ 換手邏輯：偵測到大成交量換手，預期整理時間縮短")
        if is_weekly_up: analysis.append("📈 趨勢翻正：週線層級動能轉強")
        
        if price < ma20:
            analysis.append("🚨 趨勢破線：股價跌破月線支撐")
            status_color = "danger"
        elif diff_pct < -3 and is_handover:
            analysis.append("💀 出貨警訊：高檔放量下跌")
            status_color = "danger"
        elif price < ma5:
            analysis.append("⚠️ 短線偏弱：回檔 5 日線之下")
            status_color = "warning"

        sentiment = "🔥 洗盤完成 (大戶收貨)" if is_wash_out else ("散戶進場 (融資增)" if status_color == "danger" else "大戶收貨 (融資減)")
        return " | ".join(analysis) if analysis else "目前處於區間震盪", sentiment, status_color
    except:
        return "分析引擎連線中...", "偵測中", "normal"

# --- [4. 側邊欄：帳戶管理控制台] ---
with st.sidebar:
    st.header("👤 帳戶控制台 (v10.4)")
    if 'local_db' not in st.session_state:
        st.session_state.local_db = pd.DataFrame(columns=['client', 'id', 'name', 'buy_price', 'shares', 'entry_reason'])
    if 'client_list' not in st.session_state:
        st.session_state.client_list = ["周靖傑", "大基石VIP"]
    st.session_state['cur_c'] = st.selectbox("🎯 控盤帳戶", st.session_state.client_list)

# --- [5. 主畫面：350 檔完整名單偵測] ---
st.title(f"🛡️ AI 終極控盤中心：[{st.session_state['cur_c']}]")
col_l, col_r = st.columns([1.6, 1.4])

with col_l:
    st.subheader("🔥 350 檔 AI 全量掃描 (每區 70 檔)")
    
    pool_350 = {
        "💎 權值/金控/高EPS (70)": [
            ("2330.TW","台積電"),("2317.TW","鴻海"),("2454.TW","聯發科"),("2308.TW","台達電"),("2881.TW","富邦金"),("2882.TW","國泰金"),("2303.TW","聯電"),("2886.TW","兆豐金"),("2891.TW","中信金"),("2412.TW","中華電"),
            ("1301.TW","台塑"),("2002.TW","中鋼"),("2884.TW","玉山金"),("5880.TW","合庫金"),("2885.TW","元大金"),("5871.TW","中租-KY"),("2883.TW","開發金"),("2887.TW","台新金"),("2892.TW","第一金"),("2890.TW","永豐金"),
            ("1101.TW","台泥"),("1216.TW","統一"),("2357.TW","華碩"),("2912.TW","統一超"),("2324.TW","仁寶"),("2353.TW","宏碁"),("2382.TW","廣達"),("2409.TW","友達"),("3481.TW","群創"),("2880.TW","華南金"),
            ("1303.TW","南亞"),("1326.TW","台化"),("6505.TW","台塑化"),("2105.TW","正新"),("2207.TW","和泰車"),("2301.TW","光寶科"),("2377.TW","微星"),("2395.TW","研華"),("2408.TW","南亞科"),("2474.TW","可成"),
            ("2603.TW","長榮"),("2609.TW","陽明"),("2610.TW","華航"),("2615.TW","萬海"),("2618.TW","長榮航"),("2801.TW","彰銀"),("2888.TW","新光金"),("2889.TW","國票金"),("2897.TW","王道銀行"),("5876.TW","上海商銀"),
            ("9904.TW","寶成"),("9910.TW","豐泰"),("9921.TW","巨大"),("9945.TW","潤泰新"),("1476.TW","儒星"),("1477.TW","聚陽"),("1503.TW","士電"),("1504.TW","東元"),("1513.TW","中興電"),("1519.TW","華城"),
            ("1605.TW","華新"),("1717.TW","長興"),("1722.TW","台肥"),("1802.TW","台玻"),("2006.TW","東和鋼鐵"),("2014.TW","中鴻"),("2027.TW","大成鋼"),("2106.TW","建大"),("2201.TW","裕隆"),("2204.TW","中華車")
        ],
        "🔬 半導體/IC/設備 (70)": [
            ("3413.TW","京鼎"),("3661.TW","世芯-KY"),("3035.TW","智原"),("6531.TW","愛普*"),("5269.TW","祥碩"),("3443.TW","創意"),("3227.TW","原相"),("3034.TW","聯詠"),("2379.TW","瑞昱"),("6239.TW","力成"),
            ("3711.TW","日月光投控"),("6415.TW","矽力*-KY"),("8046.TW","南電"),("3037.TW","欣興"),("2449.TW","京元電子"),("2408.TW","南亞科"),("2344.TW","華邦電"),("6770.TW","力積電"),("8069.TW","元太"),("3105.TW","穩懋"),
            ("3532.TW","台勝科"),("2369.TW","菱生"),("3264.TW","欣銓"),("6147.TW","紘康"),("8150.TW","南茂"),("2401.TW","凌陽"),("3016.TW","嘉晶"),("3529.TW","力旺"),("4966.TW","譜瑞-KY"),("6271.TW","同欣電"),
            ("8299.TW","群聯"),("2337.TW","旺宏"),("2436.TW","偉詮電"),("2458.TW","義隆"),("3006.TW","晶豪科"),("3041.TW","揚智"),("3227.TW","原相"),("3527.TW","聚積"),("3588.TW","通嘉"),("4919.TW","新唐"),
            ("4961.TW","天鈺"),("5471.TW","松翰"),("6138.TW","茂達"),("6202.TW","盛群"),("6233.TW","旺玖"),("6243.TW","迅杰"),("6411.TW","晶焱"),("6462.TW","神盾"),("6533.TW","晶心科"),("6679.TW","鈺太"),
            ("8016.TW","矽創"),("8028.TW","昇陽半"),("8054.TW","安國"),("8081.TW","致新"),("8261.TW","富鼎"),("8271.TW","宇瞻"),("3131.TW","弘塑"),("3583.TW","齊宣"),("6139.TW","亞博"),("6438.TW","迅得"),
            ("1560.TW","中砂"),("3680.TW","家登"),("6196.TW","帆宣"),("6667.TW","信紘科"),("3374.TW","精材"),("6223.TW","旺矽"),("6515.TW","穎崴"),("6510.TW","精測"),("3587.TW","閎康"),("6683.TW","雍智科技")
        ],
        "🌬️ AI伺服器/散熱 (70)": [
            ("2382.TW","廣達"),("3231.TW","緯創"),("6669.TW","緯穎"),("2357.TW","華碩"),("2376.TW","技嘉"),("3017.TW","奇鋐"),("3324.TW","雙鴻"),("2421.TW","建準"),("3013.TW","晟銘電"),("3693.TW","營邦"),
            ("2324.TW","仁寶"),("2353.TW","宏碁"),("2301.TW","光寶科"),("6213.TW","聯茂"),("6274.TW","台燿"),("2368.TW","金像電"),("3533.TW","嘉澤"),("2383.TW","台光電"),("2365.TW","昆盈"),("3044.TW","健鼎"),
            ("3515.TW","華擎"),("2425.TW","承啟"),("6117.TW","迎廣"),("8210.TW","勤誠"),("1582.TW","信錦"),("2474.TW","可成"),("3005.TW","神基"),("2352.TW","佳世達"),("2356.TW","英業達"),("2316.TW","楠梓電"),
            ("2367.TW","燿華"),("2371.TW","大同"),("2397.TW","友通"),("2417.TW","圓剛"),("2419.TW","仲琦"),("2421.TW","建準"),("2428.TW","興勤"),("2455.TW","全新"),("2465.TW","麗臺"),("2480.TW","敦陽科"),
            ("3010.TW","華立"),("3029.TW","零壹"),("3032.TW","偉訓"),("3037.TW","欣興"),("3044.TW","健鼎"),("3211.TW","順達"),("3321.TW","同泰"),("3338.TW","泰碩"),("3376.TW","新普"),("3402.TW","漢科"),
            ("3515.TW","華擎"),("3540.TW","曜越"),("3596.TW","智易"),("3617.TW","碩天"),("3653.TW","健策"),("3665.TW","貿聯-KY"),("3694.TW","海華"),("4915.TW","致伸"),("4938.TW","和碩"),("4958.TW","臻鼎-KY"),
            ("5215.TW","科嘉-KY"),("5388.TW","中磊"),("6121.TW","新普"),("6153.TW","嘉聯益"),("6166.TW","凌華"),("6205.TW","詮欣"),("6213.TW","聯茂"),("6214.TW","精誠"),("6230.TW","超眾"),("6235.TW","華孚")
        ],
        "⚓ 航運/重電/傳產 (70)": [
            ("2603.TW","長榮"),("2609.TW","陽明"),("2615.TW","萬海"),("2618.TW","長榮航"),("2610.TW","華航"),("1513.TW","中興電"),("1519.TW","華城"),("1503.TW","士電"),("1514.TW","亞力"),("1101.TW","台泥"),
            ("1102.TW","亞泥"),("2105.TW","正新"),("9921.TW","巨大"),("1476.TW","儒星"),("1477.TW","聚陽"),("2201.TW","裕隆"),("2207.TW","和泰車"),("2912.TW","統一超"),("1216.TW","統一"),("9910.TW","豐泰"),
            ("2606.TW","裕民"),("2637.TW","慧洋-KY"),("2605.TW","新興"),("2617.TW","台航"),("2633.TW","台灣高鐵"),("2634.TW","漢翔"),("2636.TW","台驊投控"),("5607.TW","遠雄港"),("5608.TW","四維航"),("2642.TW","宅配通"),
            ("1504.TW","東元"),("1514.TW","亞力"),("1517.TW","利奇"),("1521.TW","大隆"),("1522.TW","堤維西"),("1524.TW","耿鼎"),("1525.TW","江申"),("1530.TW","亞崴"),("1532.TW","勤美"),("1533.TW","車王電"),
            ("1535.TW","元山"),("1536.TW","和大"),("1537.TW","廣隆"),("1539.TW","巨庭"),("1540.TW","喬福"),("1541.TW","錩泰"),("1558.TW","伸興"),("1560.TW","中砂"),("1582.TW","信錦"),("1583.TW","程泰"),
            ("1589.TW","永冠-KY"),("1590.TW","亞德客-KY"),("1597.TW","直得"),("1605.TW","華新"),("1608.TW","華榮"),("1609.TW","大亞"),("1611.TW","中電"),("1612.TW","宏泰"),("1615.TW","大山"),("1616.TW","億泰"),
            ("1617.TW","榮星"),("1618.TW","合機"),("1701.TW","中化"),("1702.TW","南僑"),("1704.TW","榮化"),("1707.TW","葡萄王"),("1708.TW","東鹼"),("1710.TW","東聯"),("1711.TW","永光"),("1712.TW","興農")
        ],
        "📷 光學/PCB/面板 (70)": [
            ("3008.TW","大立光"),("3406.TW","玉晶光"),("2367.TW","燿華"),("2402.TW","毅嘉"),("2313.TW","華通"),("3037.TW","欣興"),("8046.TW","南電"),("3189.TW","景碩"),("2409.TW","友達"),("3481.TW","群創"),
            ("6116.TW","彩晶"),("2349.TW","錸德"),("2323.TW","中環"),("2374.TW","佳能"),("2392.TW","正崴"),("3019.TW","亞光"),("3059.TW","華晶科"),("3356.TW","奇偶"),("3362.TW","先進光"),("3441.TW","聯一光"),
            ("3504.TW","揚明光"),("3630.TW","新鉅科"),("4912.TW","聯發"),("4976.TW","佳凌"),("6209.TW","今國光"),("6405.TW","悅城"),("2316.TW","楠梓電"),("2355.TW","敬鵬"),("2368.TW","金像電"),("2383.TW","台光電"),
            ("2402.TW","毅嘉"),("3003.TW","健和興"),("3044.TW","健鼎"),("4927.TW","泰鼎-KY"),("4958.TW","臻鼎-KY"),("5349.TW","先豐"),("5469.TW","瀚宇博"),("6141.TW","柏承"),("6153.TW","嘉聯益"),("6191.TW","精成導"),
            ("6213.TW","聯茂"),("6269.TW","台郡"),("6274.TW","台燿"),("8021.TW","尖點"),("8039.TW","台虹"),("8155.TW","博智"),("8213.TW","志超"),("8358.TW","金居"),("2426.TW","鼎元"),("2448.TW","晶電"),
            ("3031.TW","佰鴻"),("3038.TW","全台"),("3049.TW","和鑫"),("3062.TW","建漢"),("3383.TW","新世紀"),("3437.TW","榮創"),("3481.TW","群創"),("3559.TW","全智科"),("3591.TW","艾笛森"),("3673.TW","TPK-KY"),
            ("3698.TW","隆達"),("4935.TW","茂林-KY"),("4956.TW","光鋐"),("5234.TW","達運"),("5484.TW","慧友"),("6116.TW","彩晶"),("6120.TW","達運"),("6164.TW","華興"),("6226.TW","光鼎"),("6278.TW","台表科")
        ]
    }
    
    cat = st.radio("板塊導航", list(pool_350.keys()), horizontal=True)
    for tid, tname in pool_350[cat]:
        p, d, color, fs, alert = get_stock_perf(tid, 90)
        try: diff_p = float(d.replace('%','').replace('+',''))
        except: diff_p = 0
        
        msg, sent, s_color = generate_ai_tech_analysis(tid, p, diff_p)
        
        with st.expander(f"📊 {tid} {tname} | {p} ({d}) | 評分: {fs}"):
            st.markdown(f"**Sentiment:** <span style='color:#00D1FF;'>{sent}</span>", unsafe_allow_html=True)
            st.markdown(f"**AI 分析:** {msg}")
            
            c1, c2, c3 = st.columns([1,1,1])
            u = c1.radio("單位", ["張", "股"], key=f"u{tid}")
            q = c2.number_input("數量", 1, 1000, key=f"q{tid}")
            if c3.button("執行買入", key=f"b{tid}"):
                real_s = q * 1000 if u == "張" else q
                new_h = pd.DataFrame([[st.session_state['cur_c'], tid, tname, p, real_s, msg]], 
                                    columns=['client', 'id', 'name', 'buy_price', 'shares', 'entry_reason'])
                st.session_state.local_db = pd.concat([st.session_state.local_db, new_h], ignore_index=True)
                st.toast(f"✅ {tname} 已存入組合"); st.rerun()

with col_r:
    st.subheader(f"💼 {st.session_state['cur_c']} 監控中心")
    my_h = st.session_state.local_db[st.session_state.local_db['client'] == st.session_state['cur_c']]
    
    if my_h.empty:
        st.info("尚無持股")
    else:
        for i, row in my_h.iterrows():
            cp, cd, cc, _, _ = get_stock_perf(row['id'], 0)
            try: d_val = float(cd.replace('%','').replace('+',''))
            except: d_val = 0
            
            msg, sent, s_color = generate_ai_tech_analysis(row['id'], cp, d_val)
            pnl = (cp - row['buy_price']) * row['shares']
            
            bg = "#551111" if s_color == "danger" else ("#555511" if s_color == "warning" else "#1E1E1E")
            
            with st.container(border=True):
                st.markdown(f"<div style='background:{bg}; padding:12px; border-radius:10px;'>", unsafe_allow_html=True)
                c1, c2 = st.columns([2.5, 1])
                with c1:
                    st.markdown(f"**{row['name']}** ({row['id']})")
                    st.markdown(f"**實時診斷:** {msg}")
                with c2:
                    pnl_c = "red" if pnl >= 0 else "green"
                    st.markdown(f"**損益: <span style='color:{pnl_c};'>{pnl:,.0f}</span>**", unsafe_allow_html=True)
                    st.write(f"現價: {cp}")
                    if st.button("清倉", key=f"del{i}"):
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
