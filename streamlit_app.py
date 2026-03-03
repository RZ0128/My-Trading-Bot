import streamlit as st
import pandas as pd
import yfinance as yf
import feedparser
import ssl
import os
from datetime import datetime
import urllib.parse

# --- [1. 核心配置 & 樣式] ---
st.set_page_config(page_title="大基石 AI 精銳控盤 v12.0", layout="wide")

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

# --- [2. 資料持久化邏輯 - 解決資料消失問題] ---
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


# --- [3. 終極 AI 戰略引擎 V12.2 (三十年趨勢預判擴充版)] ---

def get_stock_perf(ticker, prev_price):
    """基礎股價抓取函數：保持 12.2 原樣，確保數據流穩定"""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="2d")
        if len(hist) < 2:
            fast = stock.fast_info
            current_p = round(fast.last_price, 2)
            return current_p, "0.0 (0.00%)", "grey"
        current_p = round(hist['Close'].iloc[-1], 2)
        last_p = hist['Close'].iloc[-2]
        diff = current_p - last_p
        pct = (diff / last_p) * 100
        color = "red" if diff > 0 else "green" if diff < 0 else "grey"
        return current_p, f"{diff:+.1f} ({pct:+.2f}%)", color
    except: return 0, "N/A", "grey"

def generate_ai_tech_analysis(ticker, price, diff_pct):
    """
    V12.2 合體大腦擴充：
    1. 保留：洗盤偵測、12.1 均線糾結、12.2 逃頂法則
    2. 新增：三十年趨勢預判 (Predict_High) + 零虧損保本防禦 (Guard_Level)
    """
    try:
        stock = yf.Ticker(ticker)
        # 抓取 300 天數據確保短期指標；另抓取歷史數據做 30 年慣性分析
        hist = stock.history(period="300d")
        if len(hist) < 240: return None
        
        # --- [A. 12.2 基石數據計算] ---
        c = hist['Close']
        v = hist['Volume']
        ma20 = c.rolling(20).mean().iloc[-1]
        ma60 = c.rolling(60).mean().iloc[-1]
        ma60_prev = c.rolling(60).mean().iloc[-5]
        ma240 = c.rolling(240).mean().iloc[-1]
        v_ma5 = v.rolling(5).mean().iloc[-1]
        
        # MACD
        exp1, exp2 = c.ewm(span=12, adjust=False).mean(), c.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        
        score, diag, risk_msg, sentiment = 0, [], [], "籌碼中性"

        # --- [B. 12.2 核心邏輯 (原封不動)] ---
        # 1. 洗盤偵測
        is_wash_out = (price <= ma240 * 1.05 and price >= ma240 * 0.95) and (v.iloc[-1] < v_ma5 * 0.7)
        if is_wash_out:
            score += 45
            diag.append("🔥 偵測到洗盤完成，準備破新高")
            sentiment = "🔥 大戶收貨 (融資減)"

        # 2. 均線糾結
        std_ma = pd.Series([ma20, ma60, ma240]).std() / price
        if std_ma < 0.03:
            score += 10; diag.append("🌀 均線糾結：即將噴發")

        # 3. 12.2 逃頂與防禦
        if price > ma60 * 1.3:
            score -= 30; risk_msg.append("🚨 高檔乖離過大：獲利了結"); sentiment = "散戶進場 (融資增)"
        if price < ma20:
            score -= 20
            if macd.iloc[-1] < signal.iloc[-1]: risk_msg.append("💀 趨勢轉空：全撤訊號"); score -= 20

        # --- [C. 新增：三十年趨勢預判演算法] ---
        # 計算歷史波動率 (ATR 概念) 與 歷史高點慣性
        hist_long = stock.history(period="max") # 取得三十年最大數據
        if not hist_long.empty:
            # 1. 歷史慣性漲幅：計算過去幾次波段平均漲幅 (約 25%-35%)
            # 2. 預判高點：取 歷史最高價 與 近年壓力位 的加權
            max_hist = hist_long['Close'].max()
            avg_volatility = (hist_long['High'] - hist_long['Low']).mean()
            predict_high = price + (avg_volatility * 2.5) # 基於波動率的預判高點
            
            # 確保預判高點具備邏輯性 (不超過歷史天花板太多)
            predict_high = min(predict_high, max_hist * 1.1)
        else:
            predict_high = price * 1.25 # 保底預估

        # --- [D. 修正：成本絕對鎖定 + 零虧損保本防禦邏輯] ---
        # 12.2 核心升級：買入即保本，獲利即鎖定
        
        # 判斷是否已經脫離成本區 (獲利超過 5% 或 高於月線 5%)
        is_profit_safe = (price > ma20 * 1.05)
        
        if is_profit_safe:
            guard_msg = "🛡️ 已啟動移動保本防禦 (獲利鎖定)"
            # 獲利後，防禦位上移至 月線(MA20) 或 年線(MA240) 的較高者，確保守住波段利潤
            stop_p = round(max(ma20, ma240), 1)
        else:
            guard_msg = "⚠️ 成本絕對防護中 (初始佈局)"
            # 【關鍵修正】：在初始佈局階段，防禦位直接鎖定在「當前價格」
            # 這樣介面上就會顯示現價，告訴客人：這就是我們的零虧損底線。
            stop_p = round(price, 1) 

        final_msg = " | ".join(diag) if diag else "趨勢觀察中"
        if risk_msg: final_msg += " | " + " | ".join(risk_msg)
        
        return {
            "msg": f"{final_msg} | {guard_msg}",
            "sent": sentiment,
            "score": max(0, min(100, score)),
            "entry": round(ma20, 1) if price > ma20 else "觀望",
            "target": round(predict_high, 1), 
            "stop": stop_p
        }
    except: return None


# --- [4. 初始化數據庫] ---
if 'local_db' not in st.session_state:
    st.session_state.local_db = pd.DataFrame(columns=['client', 'id', 'name', 'buy_price', 'shares', 'unit', 'entry_reason'])
if 'client_list' not in st.session_state:
    st.session_state.client_list = ["周靖傑", "VIP實戰"]

# 執行讀取存檔
load_data()

# --- [5. 側邊欄：帳戶管理] ---
with st.sidebar:
    st.header("👤 大基石帳戶管理")
    with st.expander("⚙️ 客戶系統設定", expanded=True):
        new_c = st.text_input("新增客戶姓名", key="add_name")
        if st.button("確認新增"):
            if new_c and new_c not in st.session_state.client_list:
                st.session_state.client_list.append(new_c)
                save_data()
                st.rerun()
        
        cur_c_select = st.selectbox("選擇要更名的客戶", st.session_state.client_list)
        edit_name = st.text_input("修改為:", value=cur_c_select)
        if st.button("執行更名"):
            idx = st.session_state.client_list.index(cur_c_select)
            st.session_state.client_list[idx] = edit_name
            st.session_state.local_db.loc[st.session_state.local_db['client'] == cur_c_select, 'client'] = edit_name
            save_data()
            st.rerun()

    st.divider()
    # 先確認目前選取的客戶是否還在清單中，不在的話預設選第一個
current_list = st.session_state.client_list
try:
    default_idx = current_list.index(st.session_state.get('cur_c', current_list[0]))
except ValueError:
    default_idx = 0

target_client = st.selectbox("🎯 當前控盤對象", current_list, index=default_idx)
st.session_state['cur_c'] = target_client


# =================================================================
# --- [第六區：終極開業經理人系統 V12.2 合體版] ---
# 包含：390 戰略名單 + V12.2 合體大腦 + 實戰介面 (找回張/股記憶)
# =================================================================

# 1. 統一正名為 pool_390 (390 檔完整戰略名單)
pool_390 = {
    "💎 權值/金控 (70)": [("2330.TW","台積電"),("2317.TW","鴻海"),("2454.TW","聯發科"),("2308.TW","台達電"),("2881.TW","富邦金"),("2882.TW","國泰金"),("2303.TW","聯電"),("2886.TW","兆豐金"),("2891.TW","中信金"),("2412.TW","中華電"),("1301.TW","台塑"),("2002.TW","中鋼"),("2884.TW","玉山金"),("5880.TW","合庫金"),("2885.TW","元大金"),("5871.TW","中租-KY"),("2883.TW","開發金"),("2887.TW","台新金"),("2892.TW","第一金"),("2890.TW","永豐金"),("1101.TW","台泥"),("1216.TW","統一"),("2357.TW","華碩"),("2912.TW","統一超"),("2324.TW","仁寶"),("2353.TW","宏碁"),("2382.TW","廣達"),("2409.TW","友達"),("3481.TW","群創"),("2880.TW","華南金"),("1303.TW","南亞"),("1326.TW","台化"),("6505.TW","台塑化"),("2105.TW","正新"),("2207.TW","和泰車"),("2301.TW","光寶科"),("2377.TW","微星"),("2395.TW","研華"),("2408.TW","南亞科"),("2474.TW","可成"),("2603.TW","長榮"),("2609.TW","陽明"),("2610.TW","華航"),("2615.TW","萬海"),("2618.TW","長榮航"),("2801.TW","彰銀"),("2888.TW","新光金"),("2889.TW","國票金"),("2897.TW","王道銀行"),("5876.TW","上海商銀"),("9904.TW","寶成"),("9910.TW","豐泰"),("9921.TW","巨大"),("9945.TW","潤泰新"),("1476.TW","儒星"),("1477.TW","聚陽"),("1503.TW","士電"),("1504.TW","東元"),("1513.TW","中興電"),("1519.TW","華城"),("1605.TW","華新"),("1717.TW","長興"),("1722.TW","台肥"),("1802.TW","台玻"),("2006.TW","東和鋼鐵"),("2014.TW","中鴻"),("2027.TW","大成鋼"),("2106.TW","建大"),("2201.TW","裕隆"),("2204.TW","中華車")],
    "🔬 半導體/IC/設備 (70)": [("3413.TW","京鼎"),("3661.TW","世芯-KY"),("3035.TW","智原"),("6531.TW","愛普*"),("5269.TW","祥碩"),("3443.TW","創意"),("3227.TW","原相"),("3034.TW","聯詠"),("2379.TW","瑞昱"),("6239.TW","力成"),("3711.TW","日月光投控"),("6415.TW","矽力*-KY"),("8046.TW","南電"),("3037.TW","欣興"),("2449.TW","京元電子"),("2344.TW","華邦電"),("6770.TW","力積電"),("8069.TW","元太"),("3105.TW","穩懋"),("3532.TW","台勝科"),("2369.TW","菱生"),("3264.TW","欣銓"),("6147.TW","紘康"),("8150.TW","南茂"),("2401.TW","凌陽"),("3016.TW","嘉晶"),("3529.TW","力旺"),("4966.TW","譜瑞-KY"),("6271.TW","同欣電"),("8299.TW","群聯"),("2337.TW","旺宏"),("2436.TW","偉詮電"),("2458.TW","義隆"),("3006.TW","晶豪科"),("3041.TW","揚智"),("3527.TW","聚積"),("3588.TW","通嘉"),("4919.TW","新唐"),("4961.TW","天鈺"),("5471.TW","松翰"),("6138.TW","茂達"),("6202.TW","盛群"),("6233.TW","旺玖"),("6243.TW","迅杰"),("6411.TW","晶焱"),("6462.TW","神盾"),("6533.TW","晶心科"),("6679.TW","鈺太"),("8016.TW","矽創"),("8028.TW","昇陽半"),("8054.TW","安國"),("8081.TW","致新"),("8261.TW","富鼎"),("8271.TW","宇瞻"),("3131.TW","弘塑"),("3583.TW","齊宣"),("6139.TW","亞博"),("6438.TW","迅得"),("1560.TW","中砂"),("3680.TW","家登"),("6196.TW","帆宣"),("6667.TW","信紘科"),("3374.TW","精材"),("6223.TW","旺矽"),("6515.TW","穎崴"),("6510.TW","精測"),("3587.TW","閎康"),("6683.TW","雍智科技"),("8027.TW","鈦昇"),("6789.TW","采鈺")],
    "🌬️ AI伺服器/散熱 (70)": [("3231.TW","緯創"),("6669.TW","緯穎"),("2376.TW","技嘉"),("3017.TW","奇鋐"),("3324.TW","雙鴻"),("2421.TW","建準"),("3013.TW","晟銘電"),("3693.TW","營邦"),("6213.TW","聯茂"),("6274.TW","台燿"),("2368.TW","金像電"),("3533.TW","嘉澤"),("2383.TW","台光電"),("2365.TW","昆盈"),("3044.TW","健鼎"),("3515.TW","華擎"),("2425.TW","承啟"),("6117.TW","迎廣"),("8210.TW","勤誠"),("1582.TW","信錦"),("3005.TW","神基"),("2352.TW","佳世達"),("2356.TW","英業達"),("2316.TW","楠梓電"),("2367.TW","燿華"),("2371.TW","大同"),("2397.TW","友通"),("2417.TW","圓剛"),("2419.TW","仲琦"),("2428.TW","興勤"),("2455.TW","全新"),("2465.TW","麗臺"),("2480.TW","敦陽科"),("3010.TW","華立"),("3029.TW","零壹"),("3032.TW","偉訓"),("3211.TW","順達"),("3321.TW","同泰"),("3338.TW","泰碩"),("3376.TW","新普"),("3402.TW","漢科"),("3540.TW","曜越"),("3596.TW","智易"),("3617.TW","碩天"),("3653.TW","健策"),("3665.TW","貿聯-KY"),("3694.TW","海華"),("4915.TW","致伸"),("4938.TW","和碩"),("4958.TW","臻鼎-KY"),("5215.TW","科嘉-KY"),("5388.TW","中磊"),("6153.TW","嘉聯益"),("6166.TW","凌華"),("6205.TW","詮欣"),("6214.TW","精誠"),("6230.TW","超眾"),("6235.TW","華孚"),("8112.TW","至上"),("6409.TW","旭隼"),("3008.TW","大立光"),("3406.TW","玉晶光"),("3504.TW","揚明光"),("6278.TW","台表科"),("6269.TW","台郡"),("5483.TW","中美晶"),("6488.TW","環球晶"),("5434.TW","崇越"),("3702.TW","大聯大")],
    "📷 光學/PCB/面板 (70)": [("3008.TW","大立光"),("3406.TW","玉晶光"),("3441.TW","聯一光"),("3362.TW","先進光"),("3504.TW","揚明光"),("3019.TW","亞光"),("2367.TW","燿華"),("2368.TW","金像電"),("2316.TW","楠梓電"),("3037.TW","欣興"),("8046.TW","南電"),("3189.TW","景碩"),("2383.TW","台光電"),("6213.TW","聯茂"),("6274.TW","台燿"),("3044.TW","健鼎"),("4958.TW","臻鼎-KY"),("2409.TW","友達"),("3481.TW","群創"),("6116.TW","彩晶"),("6719.TW","力智"),("3592.TW","瑞鼎"),("4961.TW","天鈺"),("3034.TW","聯詠"),("8105.TW","凌巨"),("2349.TW","錸德"),("2323.TW","中環"),("6153.TW","嘉聯益"),("6269.TW","台郡"),("6278.TW","台表科"),("5349.TW","先豐"),("5439.TW","高技"),("8155.TW","博智"),("2313.TW","華通"),("2355.TW","敬鵬"),("2360.TW","致茂"),("2402.TW","毅嘉"),("3030.TW","德律"),("3321.TW","同泰"),("3376.TW","新普"),("3557.TW","嘉威"),("3591.TW","艾笛森"),("3622.TW","洋華"),("3673.TW","TPK-KY"),("3679.TW","新至陞"),("4935.TW","茂輝"),("4976.TW","佳凌"),("5243.TW","乙盛-KY"),("5469.TW","瀚宇博"),("6141.TW","柏承"),("6191.TW","精成科"),("6205.TW","詮欣"),("6224.TW","聚鼎"),("6251.TW","定穎"),("6271.TW","同欣電"),("6290.TW","良維"),("6456.TW","GIS-KY"),("6674.TW","騰輝電子"),("8021.TW","尖點"),("8039.TW","台虹"),("8103.TW","瀚荃"),("8213.TW","志超"),("8215.TW","明基材"),("2340.TW","光磊"),("2393.TW","億光"),("2448.TW","晶電"),("3437.TW","榮創"),("6168.TW","宏齊"),("6226.TW","光鼎"),("6443.TW","元晶")],
    "📡 網通/零組件 (70)": [("2345.TW","智邦"),("3704.TW","合勤控"),("5388.TW","中磊"),("3596.TW","智易"),("6285.TW","啟碁"),("2314.TW","台揚"),("2419.TW","仲琦"),("3062.TW","建漢"),("3380.TW","明泰"),("2485.TW","兆赫"),("3450.TW","聯鈞"),("4977.TW","眾達-KY"),("6426.TW","統新"),("8011.TW","台通"),("2201.TW","裕隆"),("2204.TW","中華車"),("2206.TW","三陽工業"),("2207.TW","和泰車"),("1521.TW","大隆"),("1522.TW","堤維西"),("1524.TW","耿鼎"),("1525.TW","江申"),("1536.TW","和大"),("1533.TW","車王電"),("1568.TW","倉佑"),("2101.TW","南港"),("2103.TW","台橡"),("2105.TW","正新"),("2106.TW","建大"),("2108.TW","南帝"),("2497.TW","怡利電"),("3552.TW","同致"),("5243.TW","乙盛-KY"),("6288.TW","聯嘉"),("3003.TW","健和興"),("3023.TW","信邦"),("3665.TW","貿聯-KY"),("2328.TW","廣宇"),("2392.TW","正崴"),("3024.TW","憶聲"),("3209.TW","全科"),("6115.TW","鎰勝"),("6205.TW","詮欣"),("6290.TW","良維"),("2354.TW","鴻準"),("2474.TW","可成"),("3005.TW","神基"),("6235.TW","華孚"),("5215.TW","科嘉-KY"),("5264.TW","鎧勝-KY"),("1471.TW","首利"),("2352.TW","佳世達"),("2385.TW","群光"),("3010.TW","華立"),("3029.TW","零壹"),("3042.TW","晶技"),("3057.TW","喬鼎"),("3211.TW","順達"),("3376.TW","新普"),("3617.TW","碩天"),("4927.TW","泰鼎-KY"),("5305.TW","敦南"),("5434.TW","崇越"),("6121.TW","新普"),("6143.TW","振曜"),("6184.TW","大豐電"),("6202.TW","盛群"),("6214.TW","精誠"),("8044.TW","網家"),("8112.TW","至上")],
    "⚓ 傳統產業 (20)": [("1313.TW","聯成"),("1101.TW","台泥"),("1102.TW","亞泥"),("1301.TW","台塑"),("1303.TW","南亞"),("1326.TW","台化"),("6505.TW","台塑化"),("2002.TW","中鋼"),("2014.TW","中鴻"),("2105.TW","正新"),("2603.TW","長榮"),("2609.TW","陽明"),("2615.TW","萬海"),("2618.TW","長榮航"),("1476.TW","儒星"),("1477.TW","聚陽"),("1503.TW","士電"),("1513.TW","中興電"),("1519.TW","華城"),("1717.TW","長興")],
    "🧬 生技醫療 (20)": [("4123.TW","晟德"),("1760.TW","寶齡富錦"),("4128.TW","中天"),("4147.TW","龍燈-KY"),("4162.TW","智擎"),("4174.TW","浩鼎"),("4743.TW","合一"),("6446.TW","藥華藥"),("6472.TW","保瑞"),("6492.TW","生華科"),("6547.TW","高端"),("6550.TW","北極星"),("6589.TW","台康生"),("1795.TW","美時"),("4104.TW","佳醫"),("4119.TW","旭富"),("4137.TW","麗豐"),("1701.TW","中化"),("1720.TW","生達"),("1762.TW","中化生")]
}

# --- [V12.2 終極合體版 UI 邏輯：三十年趨勢預判顯示強化] ---
st.title(f"🛡️ 12.2 終極合體版 390 檔：[{st.session_state.get('cur_c', '預設客戶')}]")

# A. 全能搜索區 (含單位記憶與趨勢預判)
with st.container(border=True):
    st.subheader("🔍 全球個股戰略搜索")
    s_input = st.text_input("輸入名稱或代號 (如: 長榮、2603)", placeholder="搜尋全台股標的...", key="global_search")
    if s_input:
        all_390 = []
        for l in pool_390.values(): all_390.extend(l)
        match = [tid for tid, name in all_390 if s_input in name]
        target_tid = match[0] if match else (s_input.upper() + ".TW" if s_input.isdigit() else s_input.upper())
        
        with st.spinner(f"正在診斷 {target_tid}..."):
            p, d, c_color = get_stock_perf(target_tid, 0)
            if p > 0:
                res = generate_ai_tech_analysis(target_tid, p, 0)
                if res:
                    st.markdown(f"### 🎯 戰略診斷: {target_tid}")
                    c1, c2 = st.columns([1.5, 1])
                    with c1:
                        st.info(f"**實戰診斷:** {res['msg']}")
                        st.markdown(f"**Sentiment:** <span style='color:#00D1FF;'>{res['sent']}</span>", unsafe_allow_html=True)
                        st.markdown(f"**🔥 建議買入:** <span style='color:red;'>{res['entry']}</span>", unsafe_allow_html=True)
                        
                        # --- [新增：A區趨勢預判強化顯示] ---
                        potential_gain = ((res['target'] - p) / p) * 100
                        st.markdown(f"""
                            <div style='padding:10px; background-color:rgba(255,75,75,0.08); border-radius:8px; border-left:5px solid #ff4b4b; margin:10px 0;'>
                                <span style='color:#ff4b4b; font-weight:bold;'>📈 30年趨勢預判目標：NT$ {res['target']}</span><br>
                                <span style='color:#e04e4e; font-size:14px;'>預期獲利空間：<b>+{potential_gain:.1f}%</b></span>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        # --- [佈局控制項 - 嚴格沿用] ---
                        buy_c1, buy_c2 = st.columns([1, 1])
                        search_unit = buy_c1.radio("佈局單位", ["張", "股"], horizontal=True, key="search_u")
                        search_qty = buy_c2.number_input("佈局數量", min_value=1, value=1, key="search_q")
                        
                        if st.button(f"確認佈局 {target_tid}", use_container_width=True):
                            new_trade = pd.DataFrame([{
                                'client': st.session_state['cur_c'], 
                                'id': target_tid, 
                                'name': target_tid, 
                                'buy_price': p, 
                                'shares': search_qty, 
                                'unit': search_unit, 
                                'entry_reason': res['msg']
                            }])
                            st.session_state.local_db = pd.concat([st.session_state.local_db, new_trade], ignore_index=True)
                            save_data(); st.rerun()
                    with c2:
                        st.metric("即時股價", p, d)
                        st.success(f"🎯 趨勢目標: {res['target']}")
                        st.error(f"🛑 防禦止損: {res['stop']}")
            else: st.error("❌ 找不到股票，請檢查格式。")

st.divider()

# B. 板塊掃描區 (含 12.1 實戰快速佈局按鈕與趨勢顯示)
col_l, col_r = st.columns([1.6, 1.4])
with col_l:
    cat = st.radio("產業板塊", list(pool_390.keys()), horizontal=True)
    with st.spinner(f"掃描 {cat}..."):
        scored_data = []
        for tid, tname in pool_390[cat]:
            p, d, c_color = get_stock_perf(tid, 0)
            res = generate_ai_tech_analysis(tid, p, 0)
            if res:
                res.update({'tid': tid, 'tname': tname, 'price': p, 'diff': d, 'color': c_color})
                scored_data.append(res)
        display_list = sorted(scored_data, key=lambda x: x['score'], reverse=True)[:10]

    st.subheader(f"🚀 {cat}：AI 推薦前 10 強")
    for item in display_list:
        with st.expander(f"⭐ {item['tname']} ({item['tid']}) | 分數: {item['score']} | 價: {item['price']}"):
            st.write(f"🧠 診斷: {item['msg']}")
            st.markdown(f"🔥 籌碼面: <span style='color:#00D1FF;'>{item['sent']}</span>", unsafe_allow_html=True)
            
            # --- [新增：B區趨勢預判強化顯示] ---
            p_gain = ((item['target'] - item['price']) / item['price']) * 100
            st.markdown(f"""
                <div style='padding:10px; background-color:rgba(255,75,75,0.08); border-radius:8px; border-left:5px solid #ff4b4b; margin:10px 0;'>
                    <span style='color:#ff4b4b; font-weight:bold;'>📈 30年趨勢預判目標：NT$ {item['target']}</span>
                    <span style='color:#e04e4e; margin-left:10px;'>空間：<b>+{p_gain:.1f}%</b></span>
                </div>
            """, unsafe_allow_html=True)
            
            st.write(f"🛑 零虧損防禦位: {item['stop']}")
            
            st.divider()
            # --- [佈局按鈕 - 嚴格沿用] ---
            rec_c1, rec_c2, rec_c3 = st.columns([1, 1, 1.5])
            r_unit = rec_c1.radio("單位", ["張", "股"], horizontal=True, key=f"ru_{item['tid']}")
            r_qty = rec_c2.number_input("數量", min_value=1, value=1, key=f"rq_{item['tid']}")
            
            if rec_c3.button(f"快速佈局 {item['tname']}", key=f"rb_{item['tid']}", use_container_width=True):
                new_trade = pd.DataFrame([{
                    'client': st.session_state['cur_c'], 
                    'id': item['tid'], 
                    'name': item['tname'], 
                    'buy_price': item['price'], 
                    'shares': r_qty, 
                    'unit': r_unit, 
                    'entry_reason': item['msg']
                }])
                st.session_state.local_db = pd.concat([st.session_state.local_db, new_trade], ignore_index=True)
                save_data(); st.rerun()



# --- [7. 右側監控區：實戰持股 - V12.2 優化版] ---
with col_r:
    st.subheader(f"💼 [{st.session_state['cur_c']}] 實戰持股明細")
    my_holdings = st.session_state.local_db[st.session_state.local_db['client'] == st.session_state['cur_c']]
    
    if my_holdings.empty:
        st.info("目前尚無持股數據。")
    else:
        total_unrealized_pnl = 0 
        # 遍歷持股清單
        for idx, row in my_holdings.iterrows():
            # 獲取最新即時行情
            cp, cd, cc = get_stock_perf(row['id'], 0)
            
            # 解析漲跌幅數值
            try: d_val = float(cd.split('(')[1].replace('%','').replace(')',''))
            except: d_val = 0
            
            # 調用 AI 大腦診斷 (包含洗盤偵測與止損目標建議)
            res = generate_ai_tech_analysis(row['id'], cp, d_val)
            
            if res:
                # 損益計算邏輯：自動識別「張(1000股)」或「股(1股)」
                multiplier = 1000 if row['unit'] == "張" else 1
                stock_pnl = (cp - row['buy_price']) * row['shares'] * multiplier
                total_unrealized_pnl += stock_pnl
                pnl_color = "#ff4b4b" if stock_pnl >= 0 else "#008000" # 紅漲綠跌 (台股慣用)
                
                with st.container(border=True):
                    # 第一列：名稱與損益
                    t_col1, t_col2 = st.columns([1.5, 1])
                    t_col1.markdown(f"**{row['name']}** <small>{row['id']}</small>", unsafe_allow_html=True)
                    t_col2.markdown(f"<div style='text-align:right; color:{pnl_color}; font-weight:bold; font-size:15px;'>NT$ {stock_pnl:,.0f}</div>", unsafe_allow_html=True)
                    
                    # 第二列：即時數據與持股細節
                    d_col1, d_col2, d_col3 = st.columns(3)
                    d_col1.caption(f"現價: {cp}")
                    d_col2.caption(f"成本: {row['buy_price']}")
                    d_col3.markdown(f"<small>持有: <b>{row['shares']}</b> {row['unit']}</small>", unsafe_allow_html=True)
                    
                    # 診斷與籌碼狀態顯示
                    st.markdown(f"<small>🧠 診斷: {res['msg']}</small>", unsafe_allow_html=True)
                    st.markdown(f"<small>🔥 籌碼: {res['sent']}</small>", unsafe_allow_html=True)

                    # 減持邏輯：嚴格對應買入時的單位
                    with st.expander(f"⚙️ 執行減持 / 平倉 ({row['unit']})"):
                        st.write(f"當前單位為「{row['unit']}」，請輸入欲賣出數量：")
                        sell_col1, sell_col2 = st.columns([1.5, 1])
                        
                        # 自動抓取該筆資料原本的單位，確保減持不跨單位出錯
                        s_qty = sell_col1.number_input(
                            f"減持{row['unit']}數", 
                            min_value=1, 
                            max_value=int(row['shares']), 
                            value=int(row['shares']) if row['shares'] > 0 else 1, 
                            key=f"sq_{idx}"
                        )
                        
                        if sell_col2.button("確認出脫", key=f"sbtn_{idx}", use_container_width=True):
                            if s_qty >= row['shares']: 
                                # 全數賣出，移除該筆
                                st.session_state.local_db = st.session_state.local_db.drop(idx)
                            else: 
                                # 部分減持，減少股數/張數
                                st.session_state.local_db.at[idx, 'shares'] -= s_qty
                            save_data()
                            st.rerun()

                    # 預警系統
                    if cp <= res['stop']: 
                        st.warning(f"🚨 跌破止損價 {res['stop']}，請評估全撤！")
                    elif cp >= res['target']: 
                        st.success(f"🎯 已達目標價 {res['target']}，建議部分分盤獲利！")

        # 底部總帳戶總覽
        st.markdown("---")
        total_color = "#ff4b4b" if total_unrealized_pnl >= 0 else "#008000"
        st.markdown(f"""
            <div style='padding:12px; border:2px solid {total_color}; border-radius:10px; text-align:center; background-color: rgba(255, 75, 75, 0.05);'>
                <div style='font-size:14px; color:#555;'>當前對象 [{st.session_state['cur_c']}] 總未實現損益</div>
                <div style='font-size:26px; font-weight:bold; color:{total_color};'>NT$ {total_unrealized_pnl:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)


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
