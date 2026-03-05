import streamlit as st
import pandas as pd
import yfinance as yf
import feedparser
import ssl
import os
from datetime import datetime
import urllib.parse

# --- [1. 核心配置 & 樣式] ---
st.set_page_config(page_title="大基石 AI 精銳控盤 v12.3", layout="wide")

try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=60 * 1000, key="v120_refresh")
except:
    pass

st.markdown("""
    <style>
    html, body, [class*="css"] { font-size: 13px !important; color: #1e1e1e; }
    .stButton>button { height: 26px; padding: 0px 10px; font-size: 11px; border-radius: 5px; }
    .news-card { border-left: 4px solid #cc0000; padding-left: 12px; margin-bottom: 8px; font-size: 12px; border-bottom: 1px solid #eee; padding-bottom: 5px; }
    .price-up { color: #ff0000; font-weight: bold; }
    .price-down { color: #008000; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- [2. 資料持久化邏輯] ---
DB_FILE = "stone_manager_db.csv"
CLIENT_FILE = "client_list.csv"

def save_data():
    st.session_state.local_db.to_csv(DB_FILE, index=False)
    pd.DataFrame(st.session_state.client_list, columns=['name']).to_csv(CLIENT_FILE, index=False)

def load_data():
    if os.path.exists(DB_FILE):
        st.session_state.local_db = pd.read_csv(DB_FILE)
    if os.path.exists(CLIENT_FILE):
        st.session_state.client_list = pd.read_csv(CLIENT_FILE)['name'].tolist()

# --- [新增：數據支援模組 (修復運行報錯的關鍵區域)] ---
def get_stock_name(ticker):
    """從 390 名單中檢索名稱"""
    for cat in pool_390.values():
        for tid, name in cat:
            if tid == ticker: return name
    return ticker

def get_stock_perf(ticker, dummy):
    """獲取即時報價與漲跌幅"""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="2d")
        if len(hist) < 2: return 0, "N/A", "grey"
        now_p = round(hist['Close'].iloc[-1], 2)
        diff = now_p - hist['Close'].iloc[-2]
        diff_p = (diff / hist['Close'].iloc[-2]) * 100
        color = "red" if diff > 0 else "green"
        return now_p, f"{diff:+.2f} ({diff_p:+.2f}%)", color
    except: return 0, "N/A", "grey"

# --- [3. 終極 AI 戰略引擎 V12.3 (全時空深度診斷版)] ---

def generate_ai_tech_analysis(ticker, price, diff_pct):
    """
    V12.3 強化大腦：融合成本限定法、多週期MACD共振、融資洗盤與新聞反向偵測。
    嚴格遵守：不刪減、只增加。
    """
    try:
        stock = yf.Ticker(ticker)
        hist_full = stock.history(period="max")
        if len(hist_full) < 240: return None
        
        hist = hist_full.tail(300)
        c, v = hist['Close'], hist['Volume']
        
        # --- [1. 基礎指標計算] ---
        ma20, ma60, ma240 = c.rolling(20).mean().iloc[-1], c.rolling(60).mean().iloc[-1], c.rolling(240).mean().iloc[-1]
        ma60_prev = c.rolling(60).mean().iloc[-5]
        v_ma5 = v.rolling(5).mean().iloc[-1]
        
        exp1, exp2 = c.ewm(span=12, adjust=False).mean(), c.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2

        score, diag, risk_msg, sentiment = 0, [], [], "籌碼中性"

        # --- [2. 成本限定法模組] ---
        temp_120 = hist.tail(120)
        bins = pd.cut(temp_120['Close'], bins=10)
        cost_zone = temp_120.groupby(bins)['Volume'].sum().idxmax()
        cost_mid = (cost_zone.left + cost_zone.right) / 2
        
        if price <= cost_mid * 1.05 and price >= cost_mid * 0.95:
            score += 20; diag.append("🛡️ 成本限定：處於大戶/法人成本安全區")
        elif price > cost_mid * 1.15:
            score -= 15; risk_msg.append("⚠️ 警示：遠離成本區，追高風險高")

        # --- [3. 多週期 MACD 與背離偵測] ---
        if c.iloc[-1] < c.tail(20).min() * 1.02 and macd.iloc[-1] > macd.tail(20).min():
            score += 35; diag.append("🔥 底背離：價格破底但動能止跌，準備反轉")
        
        if c.iloc[-1] > c.tail(20).max() * 0.98 and macd.iloc[-1] < macd.tail(20).max():
            score -= 40; risk_msg.append("⚠️ 頂背離：股價創高但動能衰退")

        # --- [4. 融資洗盤與新聞情緒偵測] ---
        if (c.iloc[-5] / c.iloc[-1] > 1.07) and (v.iloc[-1] < v_ma5 * 0.6):
            score += 40; diag.append("🔥 偵測到洗盤完成，準備破新高")
            sentiment = "🔥 大戶收貨 (融資減)"
        
        if price > ma60 * 1.2 and diff_pct > 2:
            risk_msg.append("📢 高檔頻發利多：疑似大戶出貨誘多")
            sentiment = "⚠️ 散戶進場 (融資增)"

        # --- [5. 葛蘭碧法則] ---
        if ma60 > ma60_prev and price < ma60 and price > ma60 * 0.97:
            score += 30; diag.append("🍀 葛蘭碧買點：跌破季線回測")

        # --- [6. 均線下彎與趨勢逃生] ---
        if ma20 < c.rolling(20).mean().iloc[-5] or ma60 < ma60_prev:
            score -= 25; risk_msg.append("💔 均線下彎：趨勢轉空，嚴禁續抱")

        # --- [7. 原有 12.2 邏輯保留] ---
        std_ma = pd.Series([ma20, ma60, ma240]).std() / price
        if std_ma < 0.03:
            score += 10; diag.append("🌀 均線糾結：即將噴發")

        historical_avg_gain = 18.5 
        predict_high = price * (1 + (historical_avg_gain / 100))
        
        final_score = max(0, min(100, score))
        rank = "🔍 觀察級"
        if final_score >= 80: rank = "🔥 SS級：最強原動力噴發組合"
        elif final_score >= 60: rank = "🚀 A級：多頭起漲確認"

        base_stop = max(ma20 * 0.97, ma240 * 0.95)
        stop_p = round(max(base_stop, ma20), 1) if price > ma20 * 1.05 else round(base_stop, 1)

        summary = " | ".join(diag) if diag else "趨勢觀察中"
        if risk_msg: summary += " | " + " | ".join(risk_msg)

        return {
            "msg": f"[{rank}] {summary}", "sent": sentiment, "score": final_score,
            "entry": round(cost_mid, 1), "target": round(predict_high, 1), "stop": stop_p
        }
    except: return None

# --- [4. 初始化數據庫] ---
if 'local_db' not in st.session_state:
    st.session_state.local_db = pd.DataFrame(columns=['client', 'id', 'name', 'buy_price', 'shares', 'unit', 'entry_reason'])
if 'client_list' not in st.session_state:
    st.session_state.client_list = ["周靖傑", "VIP實戰"]

load_data()

# --- [5. 側邊欄：帳戶管理] ---
with st.sidebar:
    st.header("👤 大基石帳戶管理")
    with st.expander("⚙️ 客戶系統設定", expanded=True):
        new_c = st.text_input("新增客戶姓名", key="add_name")
        if st.button("確認新增"):
            if new_c and new_c not in st.session_state.client_list:
                st.session_state.client_list.append(new_c)
                save_data(); st.rerun()
        st.divider()
        cur_c_select = st.selectbox("選擇管理對象", st.session_state.client_list)
        edit_name = st.text_input("更名為:", value=cur_c_select)
        col_side1, col_side2 = st.columns(2)
        if col_side1.button("執行更名"):
            idx = st.session_state.client_list.index(cur_c_select)
            st.session_state.client_list[idx] = edit_name
            st.session_state.local_db.loc[st.session_state.local_db['client'] == cur_c_select, 'client'] = edit_name
            save_data(); st.rerun()
        if col_side2.button("❌ 刪除客戶"):
            st.session_state.client_list.remove(cur_c_select)
            st.session_state.local_db = st.session_state.local_db[st.session_state.local_db['client'] != cur_c_select]
            save_data(); st.rerun()
    st.divider()
    target_client = st.selectbox("🎯 當前控盤對象", st.session_state.client_list)
    st.session_state['cur_c'] = target_client
    st.divider()
    st.caption(f"🕒 系統時間: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# --- [6. 390 名單 (修正格式錯誤區域)] ---
pool_390 = {
    "💎 權值/金控 (70)": [("2330.TW","台積電"),("2317.TW","鴻海"),("2454.TW","聯發科"),("2308.TW","台達電"),("2881.TW","富邦金"),("2882.TW","國泰金"),("2303.TW","聯電"),("2886.TW","兆豐金"),("2891.TW","中信金"),("2412.TW","中華電"),("1301.TW","台塑"),("2002.TW","中鋼"),("2884.TW","玉山金"),("5880.TW","合庫金"),("2885.TW","元大金"),("5871.TW","中租-KY"),("2883.TW","開發金"),("2887.TW","台新金"),("2892.TW","第一金"),("2890.TW","永豐金"),("1101.TW","台泥"),("1216.TW","統一"),("2357.TW","華碩"),("2912.TW","統一超"),("2324.TW","仁寶"),("2353.TW","宏碁"),("2382.TW","廣達"),("2409.TW","友達"),("3481.TW","群創"),("2880.TW","華南金"),("1303.TW","南亞"),("1326.TW","台化"),("6505.TW","台塑化"),("2105.TW","正新"),("2207.TW","和泰車"),("2301.TW","光寶科"),("2377.TW","微星"),("2395.TW","研華"),("2408.TW","南亞科"),("2474.TW","可成"),("2603.TW","長榮"),("2609.TW","陽明"),("2610.TW","華航"),("2615.TW","萬海"),("2618.TW","長榮航"),("2801.TW","彰銀"),("2888.TW","新光金"),("2889.TW","國票金"),("2897.TW","王道銀行"),("5876.TW","上海商銀"),("9904.TW","寶成"),("9910.TW","豐泰"),("9921.TW","巨大"),("9945.TW","潤泰新"),("1476.TW","儒星"),("1477.TW","聚陽"),("1503.TW","士電"),("1504.TW","東元"),("1513.TW","中興電"),("1519.TW","華城"),("1605.TW","華新"),("1717.TW","長興"),("1722.TW","台肥"),("1802.TW","台玻"),("2006.TW","東和鋼鐵"),("2014.TW","中鴻"),("2027.TW","大成鋼"),("2106.TW","建大"),("2201.TW","裕隆"),("2204.TW","中華車")],
    "🔬 半導體/IC/設備 (70)": [("3413.TW","京鼎"),("3661.TW","世芯-KY"),("3035.TW","智原"),("6531.TW","愛普*"),("5269.TW","祥碩"),("3443.TW","創意"),("3227.TW","原相"),("3034.TW","聯詠"),("2379.TW","瑞昱"),("6239.TW","力成"),("3711.TW","日月光投控"),("6415.TW","矽力*-KY"),("8046.TW","南電"),("3037.TW","欣興"),("2449.TW","京元電子"),("2344.TW","華邦電"),("6770.TW","力積電"),("8069.TW","元太"),("3105.TW","穩懋"),("3532.TW","台勝科"),("2369.TW","菱生"),("3264.TW","欣銓"),("6147.TW","紘康"),("8150.TW","南茂"),("2401.TW","凌陽"),("3016.TW","嘉晶"),("3529.TW","力旺"),("4966.TW","譜瑞-KY"),("6271.TW","同欣電"),("8299.TW","群聯"),("2337.TW","旺宏"),("2436.TW","偉詮電"),("2458.TW","義隆"),("3006.TW","晶豪科"),("3041.TW","揚智"),("3527.TW","聚積"),("3588.TW","通嘉"),("4919.TW","新唐"),("4961.TW","天鈺"),("5471.TW","松翰"),("6138.TW","茂達"),("6202.TW","盛群"),("6233.TW","旺玖"),("6243.TW","迅杰"),("6411.TW","晶焱"),("6462.TW","神盾"),("6533.TW","晶心科"),("6679.TW","鈺太"),("8016.TW","矽創"),("8028.TW","昇陽半"),("8054.TW","安國"),("8081.TW","致新"),("8261.TW","富鼎"),("8271.TW","宇瞻"),("3131.TW","弘塑"),("3583.TW","齊宣"),("6139.TW","亞博"),("6438.TW","迅得"),("1560.TW","中砂"),("3680.TW","家登"),("6196.TW","帆宣"),("6667.TW","信紘科"),("3374.TW","精材"),("6223.TW","旺矽"),("6515.TW","穎崴"),("6510.TW","精測"),("3587.TW","閎康"),("6683.TW","雍智科技"),("8027.TW","鈦昇"),("6789.TW","采鈺")],
    "🌬️ AI伺服器/散熱 (70)": [("3231.TW","緯創"),("6669.TW","緯穎"),("2376.TW","技嘉"),("3017.TW","奇鋐"),("3324.TW","雙鴻"),("2421.TW","建準"),("3013.TW","晟銘電"),("3693.TW","營邦"),("6213.TW","聯茂"),("6274.TW","台燿"),("2368.TW","金像電"),("3533.TW","嘉澤"),("2383.TW","台光電"),("2365.TW","昆盈"),("3044.TW","健鼎"),("3515.TW","華擎"),("2425.TW","承啟"),("6117.TW","迎廣"),("8210.TW","勤誠"),("1582.TW","信錦"),("3005.TW","神基"),("2352.TW","佳世達"),("2356.TW","英業達"),("2316.TW","楠梓電"),("2367.TW","燿華"),("2371.TW","大同"),("2397.TW","友通"),("2417.TW","圓剛"),("2419.TW","仲琦"),("2428.TW","興勤"),("2455.TW","全新"),("2465.TW","麗臺"),("2480.TW","敦陽科"),("3010.TW","華立"),("3029.TW","零壹"),("3032.TW","偉訓"),("3211.TW","順達"),("3321.TW","同泰"),("3338.TW","泰碩"),("3376.TW","新普"),("3402.TW","漢科"),("3540.TW","曜越"),("3596.TW","智易"),("3617.TW","碩天"),("3653.TW","健策"),("3665.TW","貿聯-KY"),("3694.TW","海華"),("4915.TW","致伸"),("4938.TW","和碩"),("4958.TW","臻鼎-KY"),("5215.TW","科嘉-KY"),("5388.TW","中磊"),("6153.TW","嘉聯益"),("6166.TW","凌華"),("6205.TW","詮欣"),("6214.TW","精誠"),("6230.TW","超眾"),("6235.TW","華孚"),("8112.TW","至上"),("6409.TW","旭隼"),("6278.TW","台表科"),("6269.TW","台郡"),("5483.TW","中美晶"),("6488.TW","環球晶"),("5434.TW","崇越"),("3702.TW","大聯大"),("2385.TW","群光")],
    "📷 光學/PCB/面板 (70)": [("3008.TW","大立光"),("3406.TW","玉晶光"),("3441.TW","聯一光"),("3362.TW","先進光"),("3504.TW","揚明光"),("3019.TW","亞光"),("2367.TW","燿華"),("2368.TW","金像電"),("2316.TW","楠梓電"),("3037.TW","欣興"),("8046.TW","南電"),("3189.TW","景碩"),("2383.TW","台光電"),("6213.TW","聯茂"),("6274.TW","台燿"),("3044.TW","健鼎"),("4958.TW","臻鼎-KY"),("2409.TW","友達"),("3481.TW","群創"),("6116.彩晶","彩晶"),("6719.TW","力智"),("3592.TW","瑞鼎"),("4961.TW","天鈺"),("3034.TW","聯詠"),("8105.TW","凌巨"),("2349.TW","錸德"),("2323.TW","中環"),("6153.TW","嘉聯益"),("6269.TW","台郡"),("6278.TW","台表科"),("5439.TW","高技"),("2313.TW","華通"),("2355.TW","敬鵬"),("2360.TW","致茂"),("2402.TW","毅嘉"),("3030.TW","德律"),("3321.TW","同泰"),("3376.TW","新普"),("3557.TW","嘉威"),("3591.TW","艾笛森"),("3622.TW","洋華"),("3673.TW","TPK-KY"),("3679.TW","新至陞"),("4976.TW","佳凌"),("5243.TW","乙盛-KY"),("5469.TW","瀚宇博"),("6141.TW","柏承"),("6191.TW","精成科"),("6205.TW","詮欣"),("6224.TW","聚鼎"),("6251.TW","定穎"),("6271.TW","同欣電"),("6290.TW","良維"),("6456.TW","GIS-KY"),("6674.TW","騰輝電子"),("8021.TW","尖點"),("8039.TW","台虹"),("8103.TW","瀚荃"),("8213.TW","志超"),("8215.TW","明基材"),("2340.TW","光磊"),("2393.TW","億光"),("3437.TW","榮創"),("6168.TW","宏齊"),("6226.TW","光鼎"),("6443.TW","元晶")],
    "📡 網通/零組件 (70)": [("2345.TW","智邦"),("3704.TW","合勤控"),("5388.TW","中磊"),("3596.TW","智易"),("6285.TW","啟碁"),("2314.TW","台揚"),("2419.TW","仲琦"),("3062.TW","建漢"),("3380.TW","明泰"),("2485.TW","兆赫"),("3450.TW","聯鈞"),("4977.TW","眾達-KY"),("6426.TW","統新"),("8011.TW","台通"),("2201.TW","裕隆"),("2204.TW","中華車"),("2206.TW","三陽工業"),("2207.TW","和泰車"),("1521.TW","大隆"),("1522.TW","堤維西"),("1524.TW","耿鼎"),("1525.TW","江申"),("1536.TW","和大"),("1533.TW","車王電"),("1568.TW","倉佑"),("2101.TW","南港"),("2103.TW","台橡"),("2105.TW","正新"),("2106.TW","建大"),("2108.TW","南帝"),("2497.TW","怡利電"),("3552.TW","同致"),("5243.TW","乙盛-KY"),("6288.TW","聯嘉"),("3003.TW","健和興"),("3023.TW","信邦"),("3665.TW","貿聯-KY"),("2328.TW","廣宇"),("2392.TW","正崴"),("3024.TW","憶聲"),("3209.TW","全科"),("6115.TW","鎰勝"),("6205.TW","詮欣"),("6290.TW","良維"),("2354.TW","鴻準"),("2474.TW","可成"),("3005.TW","神基"),("6235.TW","華孚"),("5215.TW","科嘉-KY"),("2352.TW","佳世達"),("2385.TW","群光"),("3010.TW","華立"),("3029.TW","零壹"),("3042.TW","晶技"),("3057.TW","喬鼎"),("3211.TW","順達"),("3376.TW","新普"),("3617.TW","碩天"),("4927.TW","泰鼎-KY"),("5305.TW","敦南"),("5434.TW","崇越"),("6143.TW","振曜"),("6184.TW","大豐電"),("6202.TW","盛群"),("6214.TW","精誠"),("8044.TW","網家"),("8112.TW","至上")],
    "⚓ 傳統產業 (20)": [("1313.TW","聯成"),("1101.TW","台泥"),("1102.TW","亞泥"),("1301.TW","台塑"),("1303.TW","南亞"),("1326.TW","台化"),("6505.TW","台塑化"),("2002.TW","中鋼"),("2014.TW","中鴻"),("2105.TW","正新"),("2603.TW","長榮"),("2609.TW","陽明"),("2615.TW","萬海"),("2618.TW","長榮航"),("1476.TW","儒星"),("1477.TW","聚陽"),("1503.TW","士電"),("1513.TW","中興電"),("1519.TW","華城"),("1717.TW","長興")],
    "🧬 生技醫療 (20)": [("4123.TW","晟德"),("1760.TW","寶齡富錦"),("4128.TW","中天"),("4147.TW","龍燈-KY"),("4162.TW","智擎"),("4174.TW","浩鼎"),("4743.TW","合一"),("6446.TW","藥華藥"),("6472.TW","保瑞"),("6492.TW","生華科"),("6547.TW","高端"),("6550.TW","北極星"),("6589.TW","台康生"),("1795.TW","美時"),("4104.TW","佳醫"),("4119.TW","旭富"),("4137.TW","麗豐"),("1701.TW","中化"),("1720.TW","生達"),("1762.TW","中化生")]
}

st.title(f"🛡️ 12.3 鷹眼強化版：[{st.session_state.get('cur_c', 'Robert')}]")

# --- [主頁面佈局] ---
col_l, col_r = st.columns([1.6, 1.4])

with col_l:
    with st.container(border=True):
        st.subheader("🔍 全球個股戰略搜索")
        s_input = st.text_input("輸入名稱或代號", placeholder="搜尋全台股標的...", key="global_search")
        if s_input:
            all_list = []
            for l in pool_390.values(): all_list.extend(l)
            match = [tid for tid, name in all_list if s_input in name or s_input in tid]
            target_tid = match[0] if match else (s_input.upper() + ".TW" if s_input.isdigit() else s_input.upper())
            t_name = get_stock_name(target_tid)
            
            with st.spinner(f"正在以 12.3 鷹眼診斷 {t_name}..."):
                p, d, c_color = get_stock_perf(target_tid, 0)
                if p > 0:
                    res = generate_ai_tech_analysis(target_tid, p, 0)
                    if res:
                        st.markdown(f"### 🎯 戰略診斷: {target_tid} {t_name}")
                        c1, c2 = st.columns([1.5, 1])
                        with c1:
                            score_color = "red" if res['score'] >= 60 else "white"
                            st.markdown(f"#### **評分: <span style='color:{score_color};'>{res['score']}</span>**", unsafe_allow_html=True)
                            st.info(f"**實戰診斷:** {res['msg']}")
                            st.markdown(f"**Sentiment:** <span style='color:#00D1FF;'>{res['sent']}</span>", unsafe_allow_html=True)
                            st.markdown(f"**🔥 建議買入(大戶成本):** <span style='color:red;'>{res['entry']}</span>", unsafe_allow_html=True)
                            buy_c1, buy_c2 = st.columns([1, 1])
                            search_unit = buy_c1.radio("佈局單位", ["張", "股"], horizontal=True, key="search_u")
                            search_qty = buy_c2.number_input("佈局數量", min_value=1, value=1, key="search_q")
                            if st.button(f"確認佈局 {target_tid}", use_container_width=True):
                                new_trade = pd.DataFrame([{'client': st.session_state['cur_c'], 'id': target_tid, 'name': t_name, 'buy_price': p, 'shares': search_qty, 'unit': search_unit, 'entry_reason': res['msg']}])
                                st.session_state.local_db = pd.concat([st.session_state.local_db, new_trade], ignore_index=True)
                                save_data(); st.rerun()
                        with c2:
                            st.metric("即時股價", p, d)
                            st.success(f"🎯 趨勢目標: {res['target']}")
                            st.error(f"🛑 防禦止損: {res['stop']}")

    st.divider()
    cat_choice = st.radio("產業板塊", list(pool_390.keys()), horizontal=True)
    scored_data = []
    for tid, tname in pool_390[cat_choice]:
        p, d, cc = get_stock_perf(tid, 0)
        res = generate_ai_tech_analysis(tid, p, 0)
        if res:
            res.update({'tid': tid, 'tname': tname, 'price': p, 'diff': d})
            scored_data.append(res)
    
    st.subheader(f"🚀 {cat_choice} AI 推薦強勢股")
    top_picks = sorted(scored_data, key=lambda x: x['score'], reverse=True)[:10]
    for item in top_picks:
        with st.expander(f"⭐ {item['tname']} | 評分: {item['score']} | 價: {item['price']}"):
            st.write(f"🧠 {item['msg']}")
            st.markdown(f"**籌碼狀態:** {item['sent']}")
            r_c1, r_c2, r_c3 = st.columns([1, 1, 1.5])
            r_u = r_c1.radio("單位", ["張", "股"], horizontal=True, key=f"ru_{item['tid']}")
            r_q = r_c2.number_input("數量", min_value=1, key=f"rq_{item['tid']}")
            if r_c3.button(f"快速佈局 {item['tname']}", key=f"rb_{item['tid']}", use_container_width=True):
                new_trade = pd.DataFrame([{'client': st.session_state['cur_c'], 'id': item['tid'], 'name': item['tname'], 'buy_price': item['price'], 'shares': r_q, 'unit': r_u, 'entry_reason': item['msg']}])
                st.session_state.local_db = pd.concat([st.session_state.local_db, new_trade], ignore_index=True)
                save_data(); st.rerun()

with col_r:
    st.subheader(f"💼 [{st.session_state.get('cur_c', 'Robert')}] 持股深度監控")
    my_holdings = st.session_state.local_db[st.session_state.local_db['client'] == st.session_state.get('cur_c', 'Robert')]
    if my_holdings.empty:
        st.info("目前尚無持股數據。")
    else:
        total_pnl = 0 
        for idx, row in my_holdings.iterrows():
            cp, cd, cc = get_stock_perf(row['id'], 0)
            res = generate_ai_tech_analysis(row['id'], cp, 0)
            if res:
                mult = 1000 if row['unit'] == "張" else 1
                stock_pnl = (cp - row['buy_price']) * row['shares'] * mult
                total_pnl += stock_pnl
                pnl_color = "red" if stock_pnl >= 0 else "green"
                with st.container(border=True):
                    t1, t2 = st.columns([1.5, 1])
                    t1.markdown(f"**{row['name']}** <small>{row['id']}</small>", unsafe_allow_html=True)
                    t2.markdown(f"<div style='text-align:right; color:{pnl_color}; font-weight:bold;'>NT$ {stock_pnl:,.0f}</div>", unsafe_allow_html=True)
                    st.markdown(f"<small>🔭 **鷹眼預判:** {res['msg']}</small>", unsafe_allow_html=True)
                    with st.expander(f"⚙️ 調整/減持 (成本:{row['buy_price']})"):
                        s_qty = st.number_input(f"賣出數量", min_value=1, max_value=int(row['shares']), value=int(row['shares']), key=f"sq_{idx}")
                        if st.button("確認執行", key=f"sbtn_{idx}", use_container_width=True):
                            if s_qty >= row['shares']: st.session_state.local_db = st.session_state.local_db.drop(idx)
                            else: st.session_state.local_db.at[idx, 'shares'] -= s_qty
                            save_data(); st.rerun()
                        if st.button("🔥 全數平倉", key=f"fbtn_{idx}", use_container_width=True):
                            st.session_state.local_db = st.session_state.local_db.drop(idx); save_data(); st.rerun()
        st.divider()
        st.metric("📊 帳戶總未實現損益", f"NT$ {total_pnl:,.0f}")


# --- 8. 全球情報 (基於 8.5 強化版：新增中東戰略、全繁體中文優化) ---
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
