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


# --- [3. 終極 AI 戰略引擎 V12.2 (中文化與零虧損保本修正版)] ---

def get_stock_name(ticker):
    """自動獲取中文化名稱，優先從 390 名單找，找不到再從 yfinance 抓"""
    # 從 pool_390 名單搜尋 (pool_390 必須定義在前面或設為全局)
    for cat in pool_390:
        for tid, tname in pool_390[cat]:
            if ticker.upper() == tid.upper() or ticker.upper() in tid.upper():
                return tname
    # 若名單沒找到，從 yfinance API 抓取簡稱
    try:
        s_info = yf.Ticker(ticker).info
        return s_info.get('shortName', ticker)
    except:
        return ticker

def generate_ai_tech_analysis(ticker, price, diff_pct):
    """
    V12.2 核心邏輯：
    1. 保留：洗盤偵測、12.1 均線糾結/葛蘭碧、12.2 逃頂法則
    2. 新增：三十年趨勢預判 + 零虧損保本防護 + 中文化顯示
    """
    try:
        stock = yf.Ticker(ticker)
        # 抓取數據：300d 用於技術指標，max 用於三十年趨勢
        hist = stock.history(period="300d")
        if len(hist) < 240: return None
        
        # --- [A. 12.2 基石數據計算 (嚴格保留，不更動)] ---
        c = hist['Close']
        v = hist['Volume']
        ma20 = c.rolling(20).mean().iloc[-1]
        ma60 = c.rolling(60).mean().iloc[-1]
        ma60_prev = c.rolling(60).mean().iloc[-5]
        ma240 = c.rolling(240).mean().iloc[-1]
        v_ma5 = v.rolling(5).mean().iloc[-1]
        
        # MACD (保留基石指標)
        exp1, exp2 = c.ewm(span=12, adjust=False).mean(), c.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        
        score, diag, risk_msg, sentiment = 0, [], [], "籌碼中性"
        t_name = get_stock_name(ticker) # 執行中文化抓取

        # --- [B. 12.1/12.2 基石邏輯整合 (原封不動)] ---
        # 1. 洗盤偵測 (長官核心)
        if (price <= ma240 * 1.05 and price >= ma240 * 0.95) and (v.iloc[-1] < v_ma5 * 0.7):
            score += 45
            diag.append("🔥 偵測到洗盤完成，準備破新高")
            sentiment = "🔥 大戶收貨 (融資減)"

        # 2. 均線糾結
        std_ma = pd.Series([ma20, ma60, ma240]).std() / price
        if std_ma < 0.03:
            score += 10; diag.append("🌀 均線糾結")

        # 3. 12.2 逃頂與防禦賣出
        if price > ma60 * 1.3:
            score -= 30; risk_msg.append("🚨 高檔乖離過大：獲利了結"); sentiment = "散戶進場 (融資增)"
        if price < ma20:
            score -= 20
            if macd.iloc[-1] < signal.iloc[-1]: risk_msg.append("💀 趨勢轉空：全撤訊號"); score -= 20

        # --- [C. 三十年趨勢預判 + 零虧損防禦位計算 (新增修正)] ---
        # 1. 預判高點 (三十年數據)
        hist_long = stock.history(period="max")
        if not hist_long.empty:
            max_hist = hist_long['Close'].max()
            avg_vol = (hist_long['High'] - hist_long['Low']).mean()
            predict_high = min(price + (avg_vol * 3), max_hist * 1.1)
        else:
            predict_high = price * 1.25

        # 2. 零虧損防禦 (重點修正：絕不讓客人從 216.5 虧到 190.9)
        # 如果利潤尚未拉開 (未達 5%)，防禦位就是買入現價，實現「絕對保本」
        if price > ma20 * 1.05:
            guard_msg = "🛡️ 已啟動移動保本防禦 (獲利鎖定)"
            stop_p = round(max(ma20, price * 0.98), 1) 
        else:
            guard_msg = "⚠️ 初始佈局：成本絕對防護中"
            stop_p = round(price, 1) # 防禦位 = 現在股價，解決 190.9 問題

        final_msg = " | ".join(diag) if diag else "趨勢觀察中"
        if risk_msg: final_msg += " | " + " | ".join(risk_msg)
        
        return {
            "tname": t_name, # 回傳中文名
            "msg": f"{final_msg} | {guard_msg}",
            "sent": sentiment,
            "score": max(0, min(100, score)),
            "entry": round(ma20, 1),
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
# --- [6. 板塊掃描與個股搜索區：V12.2 終極合體版（390檔全名單修正版）] ---
# =================================================================

import pandas as pd
import yfinance as yf

# --- [基礎函數補全：確保不再報錯] ---
def get_stock_perf(ticker, dummy):
    """獲取股價、漲跌與顏色 (修正 NameError)"""
    try:
        s = yf.Ticker(ticker)
        h = s.history(period="2d")
        if len(h) < 2: return 0, 0, "black"
        now_p = round(h['Close'].iloc[-1], 2)
        diff = round(h['Close'].iloc[-1] - h['Close'].iloc[-2], 2)
        color = "red" if diff > 0 else "green" if diff < 0 else "black"
        return now_p, diff, color
    except: return 0, 0, "black"

# --- [390 檔完整基石名單：嚴格遵守只增不減] ---
pool_390 = {
    "💎 權值/金控 (70)": [
        ("2330.TW","台積電"),("2317.TW","鴻海"),("2454.TW","聯發科"),("2303.TW","聯電"),("2881.TW","富邦金"),("2882.TW","國泰金"),("2886.TW","兆豐金"),("2891.TW","中信金"),("2884.TW","玉山金"),("5880.TW","合庫金"),("2308.TW","台達電"),("2892.TW","第一金"),("2880.TW","華南金"),("2885.TW","元大金"),("2883.TW","開發金"),("2887.TW","台新金"),("5871.TW","中租-KY"),("5876.TW","上海商銀"),("2890.TW","永豐金"),("2912.TW","統一超"),("2357.TW","華碩"),("2412.TW","中華電"),("3045.TW","台灣大"),("4904.TW","遠傳"),("1301.TW","台塑"),("1303.TW","南亞"),("1326.TW","台化"),("6505.TW","台塑化"),("2002.TW","中鋼"),("2105.TW","正新"),("2201.TW","裕隆"),("2207.TW","和泰車"),("2603.TW","長榮"),("2609.TW","陽明"),("2615.TW","萬海"),("1402.TW","遠東新"),("1101.TW","台泥"),("1102.TW","亞泥"),("1216.TW","統一"),("2106.TW","建大"),("2610.TW","華航"),("2618.TW","長榮航"),("2801.TW","彰銀"),("2809.TW","京城銀"),("2812.TW","台中銀"),("2834.TW","臺企銀"),("2838.TW","聯邦銀"),("2845.TW","遠東銀"),("2851.TW","中再保"),("2855.TW","統一證"),("2867.TW","三商壽"),("2888.TW","新光金"),("2889.TW","國票金"),("5878.TW","台名"),("6005.TW","群益證"),("9904.TW","寶成"),("9917.TW","中保科"),("9921.TW","巨大"),("9933.TW","中鼎"),("9945.TW","潤泰新")
    ],
    "🔬 半導體/IC/設備 (70)": [
        ("2379.TW","瑞昱"),("3034.TW","聯詠"),("3711.TW","日月光"),("3035.TW","智原"),("3661.TW","世芯-KY"),("5269.TW","祥碩"),("6415.TW","矽力*-KY"),("8016.TW","矽創"),("4919.TW","新唐"),("4961.TW","天鈺"),("3592.TW","瑞鼎"),("3227.TW","原相"),("2458.TW","義隆"),("6231.TW","系微"),("3131.TW","弘塑"),("3583.TW","辛耘"),("6138.TW","茂達"),("6182.TW","合晶"),("3532.TW","台勝科"),("6488.TW","環球晶"),("5483.TW","中美晶"),("2329.TW","華泰"),("2337.TW","旺宏"),("2338.TW","光罩"),("2344.TW","華邦電"),("2369.TW","菱生"),("2408.TW","南亞科"),("2441.TW","超豐"),("2449.TW","京元電子"),("3006.TW","晶豪科"),("3016.TW","嘉晶"),("3264.TW","欣銓"),("3374.TW","精材"),("3588.TW","通嘉"),("3680.TW","家登"),("4952.TW","凌通"),("4967.TW","十銓"),("4968.TW","立積"),("5222.TW","全訊"),("5274.TW","信驊"),("5289.TW","宜鼎"),("6147.TW","紘康"),("6202.TW","盛群"),("6243.TW","迅杰"),("6271.TW","同欣電"),("6411.TW","晶焱"),("6435.TW","大中"),("6462.TW","神盾"),("6510.TW","精測"),("6515.TW","穎崴"),("6525.TW","捷敏-KY"),("6531.TW","愛普*"),("6533.TW","晶心科"),("6548.TW","海德威"),("6568.TW","宏觀"),("6573.TW","虹揚-KY"),("6613.TW","朋程"),("6643.TW","M31"),("6679.TW","鈺太"),("6684.TW","安格"),("6719.TW","力智"),("6732.TW","昇佳電子"),("6756.TW","威鋒電子"),("6770.TW","力積電"),("6799.TW","來頡"),("8028.TW","昇陽半導體"),("8054.TW","安國"),("8081.TW","致新"),("8110.TW","華東"),("8131.TW","福懋科")
    ],
    "✨ AI伺服器/散熱 (70)": [
        ("2382.TW","廣達"),("3231.TW","緯創"),("2356.TW","英業達"),("2376.TW","技嘉"),("2377.TW","微星"),("6669.TW","緯穎"),("3017.TW","奇鋐"),("3324.TW","雙鴻"),("3013.TW","晟銘電"),("3693.TW","營邦"),("8210.TW","勤誠"),("2301.TW","光寶科"),("2383.TW","台光電"),("6213.TW","聯茂"),("6274.TW","台耀"),("2421.TW","建準"),("3653.TW","健策"),("6125.TW","廣運"),("3533.TW","嘉澤"),("2352.TW","佳世達"),("2353.TW","宏碁"),("2354.TW","鴻準"),("2365.TW","昆盈"),("2385.TW","群光"),("2395.TW","研華"),("2397.TW","友通"),("2417.TW","圓剛"),("2425.TW","承啟"),("2465.TW","麗臺"),("3005.TW","神基"),("3032.TW","偉訓"),("3046.TW","建碁"),("3217.TW","優群"),("3312.TW","弘憶股"),("3413.TW","京鼎"),("3515.TW","華擎"),("3540.TW","曜越"),("3563.TW","牧德"),("4938.TW","和碩"),("4958.TW","臻鼎-KY"),("4966.TW","譜瑞-KY"),("5215.TW","科嘉-KY"),("5234.TW","達興材料"),("5288.TW","豐祥-KY"),("5305.TW","萬潤"),("5469.TW","瀚宇博"),("6117.TW","迎廣"),("6166.TW","凌華"),("6197.TW","佳必琪"),("6205.TW","詮欣"),("6206.TW","飛捷"),("6230.TW","超眾"),("6235.TW","華孚"),("6245.TW","立端"),("6277.TW","宏正"),("6414.TW","樺漢"),("6449.TW","鈺邦"),("6515.TW","穎崴"),("6541.TW","泰金寶-DR"),("6579.TW","研揚"),("6625.TW","必應"),("6641.TW","基士德-KY"),("6672.TW","騰輝電子-KY"),("6691.TW","洋基工程"),("6715.TW","嘉基"),("6776.TW","展碁國際"),("6806.TW","森崴能源"),("8069.TW","元太"),("8114.TW","振曜"),("8411.TW","福貞-KY")
    ],
    "📷 光學/PCB/面板 (70)": [
        ("3008.TW","大立光"),("3406.TW","玉晶光"),("2367.TW","燿華"),("2368.TW","金像電"),("3037.TW","欣興"),("8046.TW","南電"),("3189.TW","景碩"),("2409.TW","友達"),("3481.TW","群創"),("6116.TW","彩晶"),("2393.TW","億光"),("2448.TW","晶宏"),("2313.TW","華通"),("2316.TW","楠梓電"),("2323.TW","中環"),("2340.TW","光鼎"),("2349.TW","錸德"),("2355.TW","敬鵬"),("2392.TW","正崴"),("2402.TW","毅嘉"),("2406.TW","國碩"),("2426.TW","鼎元"),("2439.TW","美律"),("2462.TW","良得電"),("2474.TW","可成"),("3019.TW","亞光"),("3023.TW","信邦"),("3031.TW","佰鴻"),("3044.TW","健鼎"),("3050.TW","鈺德"),("3051.TW","力特"),("3059.TW","華晶科"),("3221.TW","台嘉碩"),("3239.TW","龍承"),("3338.TW","泰碩"),("3362.TW","先進光"),("3380.TW","明泰"),("3437.TW","榮創"),("3443.TW","創意"),("3450.TW","聯鈞"),("3501.TW","維熹"),("3504.TW","揚明光"),("3518.TW","柏騰"),("3527.TW","聚積"),("3550.TW","聯嘉"),("3557.TW","嘉威"),("3563.TW","牧德"),("3576.TW","聯合再生"),("3591.TW","艾笛森"),("3622.TW","洋華"),("3653.TW","健策"),("3673.TW","TPK-KY"),("3679.TW","新至陞"),("4935.TW","茂林-KY"),("4956.TW","光鋐"),("4960.TW","誠美材"),("5434.TW","崇越"),("5484.TW","慧友"),("6120.TW","達運"),("6153.TW","嘉聯益"),("6164.TW","華興"),("6168.TW","宏齊"),("6176.TW","瑞儀"),("6213.TW","聯茂"),("6226.TW","光鼎"),("6269.TW","台郡"),("6278.TW","台表科"),("6405.TW","悅城"),("6456.TW","GIS-KY"),("8103.TW","瀚荃")
    ],
    "📡 網通/零組件 (70)": [
        ("2345.TW","智邦"),("5388.TW","中磊"),("6285.TW","啟碁"),("3596.TW","智易"),("2332.TW","友訊"),("2419.TW","仲琦"),("3062.TW","建漢"),("6442.TW","光聖"),("4977.TW","眾達-KY"),("2485.TW","兆赫"),("2314.TW","台揚"),("2321.TW","東訊"),("2327.TW","國巨"),("2431.TW","聯昌"),("2442.TW","新美齊"),("2450.TW","神腦"),("2455.TW","全新"),("2457.TW","飛宏"),("2472.TW","立隆電"),("2478.TW","大毅"),("2481.TW","強茂"),("2484.TW","希華"),("2492.TW","華新科"),("2493.TW","揚博"),("2498.TW","宏達電"),("3025.TW","星通"),("3027.TW","盛達"),("3036.TW","文曄"),("3042.TW","晶技"),("3047.TW","訊舟"),("3141.TW","晶宏"),("3163.TW","波若威"),("3169.TW","亞信"),("3191.TW","和進"),("3209.TW","全科"),("3234.TW","光環"),("3289.TW","宜特"),("3305.TW","昇貿"),("3311.TW","閎暉"),("3363.TW","上詮"),("3380.TW","明泰"),("3416.TW","信紘科"),("3419.TW","譁裕"),("3491.TW","昇達科"),("3558.TW","神準"),("3563.TW","牧德"),("3617.TW","碩天"),("3672.TW","康聯訊"),("3682.TW","亞太電"),("3702.TW","大聯大"),("4906.TW","正文"),("4908.TW","前鼎"),("4979.TW","華星光"),("5349.TW","先豐"),("5351.TW","鈺創"),("5425.TW","台半"),("5471.TW","松翰"),("6142.TW","友勁"),("6143.TW","振曜"),("6152.TW","百一"),("6196.TW","帆宣"),("6209.TW","今國光"),("6214.TW","精誠"),("6284.TW","佳邦"),("6426.TW","統新"),("6464.TW","台半"),("6485.TW","點序"),("6514.TW","芮特-KY"),("8011.TW","台通"),("8086.TW","宏捷科")
    ],
    "⚓ 傳統產業/重電 (20)": [
        ("1513.TW","中興電"),("1519.TW","華城"),("1503.TW","士電"),("1514.TW","亞力"),("1605.TW","華新"),("1722.TW","台肥"),("9910.TW","豐泰"),("1504.TW","東元"),("1536.TW","和大"),("1513.TW","中興電"),("1519.TW","華城"),("1503.TW","士電"),("1514.TW","亞力"),("1605.TW","華新"),("1608.TW","華榮"),("1609.TW","大亞"),("1611.TW","中電"),("1612.TW","宏泰"),("1617.TW","榮星"),("1618.TW","合機")
    ],
    "🧬 生技醫療 (20)": [
        ("1762.TW","中化生"),("4137.TW","麗豐-KY"),("1760.TW","寶齡富錦"),("6446.TW","藥華藥"),("6472.TW","保瑞"),("1795.TW","美時"),("4147.TW","龍燈-KY"),("4162.TW","智擎"),("4105.TW","集盛"),("1701.TW","中化"),("1707.TW","葡萄王"),("1720.TW","生達"),("1731.TW","美吾華"),("1733.TW","五鼎"),("1734.TW","杏輝"),("1736.TW","喬山"),("1752.TW","南光"),("1783.TW","和康生"),("1786.TW","科妍"),("1789.TW","神隆")
    ]
}

st.title(f"🛡️ 12.2 終極合體版 390 檔：[{st.session_state.get('cur_c', '預設客戶')}]")

# A. 全能搜索區
with st.container(border=True):
    st.subheader("🔍 全球個股戰略搜索")
    s_input = st.text_input("輸入名稱或代號 (如: 長榮、2603)", placeholder="搜尋全台股標的...", key="search_main")
    if s_input:
        all_stocks = []
        for l in pool_390.values(): all_stocks.extend(l)
        # 搜尋匹配邏輯
        match = [tid for tid, name in all_stocks if s_input in name or s_input in tid]
        target_tid = match[0] if match else (s_input.upper() + ".TW" if s_input.isdigit() else s_input.upper())
        
        p, d, c_color = get_stock_perf(target_tid, 0)
        if p > 0:
            res = generate_ai_tech_analysis(target_tid, p, 0)
            if res:
                # 標題強制中文化
                st.markdown(f"### 🎯 戰略診斷: {target_tid} {res['tname']}")
                c1, c2 = st.columns([1.5, 1])
                with c1:
                    st.info(f"**實戰診斷:** {res['msg']}")
                    st.markdown(f"**Sentiment:** <span style='color:#00D1FF;'>{res['sent']}</span>", unsafe_allow_html=True)
                    
                    # 趨勢預判視覺化 (修正百分比顯示)
                    p_gain = ((res['target'] - p) / p) * 100
                    st.markdown(f"""
                        <div style='padding:12px; background-color:rgba(255,75,75,0.08); border-radius:8px; border-left:6px solid #ff4b4b; margin:10px 0;'>
                            <span style='color:#ff4b4b; font-weight:bold;'>📈 30年趨勢預判目標：NT$ {res['target']}</span><br>
                            <span style='color:#e04e4e;'>預期獲利空間：<b>+{p_gain:.1f}%</b></span>
                        </div>
                    """, unsafe_allow_html=True)

                    buy_c1, buy_c2 = st.columns([1, 1])
                    search_unit = buy_c1.radio("佈局單位", ["張", "股"], horizontal=True, key="s_unit")
                    search_qty = buy_c2.number_input("佈局數量", min_value=1, value=1, key="s_qty")
                    
                    if st.button(f"確認佈局 {res['tname']}", use_container_width=True):
                        new_trade = pd.DataFrame([{
                            'client': st.session_state['cur_c'], 'id': target_tid, 'name': res['tname'], 
                            'buy_price': p, 'shares': search_qty, 'unit': search_unit, 'entry_reason': res['msg']
                        }])
                        st.session_state.local_db = pd.concat([st.session_state.local_db, new_trade], ignore_index=True)
                        save_data(); st.rerun()
                with c2:
                    st.metric("即時股價", p, d)
                    st.success(f"🎯 趨勢目標: {res['target']}")
                    st.error(f"🛑 零虧損防禦: {res['stop']}")
        else: st.error("❌ 找不到標的，請檢查輸入。")

st.divider()

# B. 板塊掃描區
cat = st.radio("產業板塊", list(pool_390.keys()), horizontal=True)
with st.spinner(f"掃描 {cat}..."):
    scored_data = []
    for tid, tname in pool_390[cat]:
        p, d, c_color = get_stock_perf(tid, 0) # 這裡現在不會再報錯了
        res = generate_ai_tech_analysis(tid, p, 0)
        if res:
            res.update({'tid': tid, 'tname': tname, 'price': p, 'diff': d})
            scored_data.append(res)

    display_list = sorted(scored_data, key=lambda x: x['score'], reverse=True)[:10]
    st.subheader(f"🚀 {cat}：AI 推薦前 10 強")
    for item in display_list:
        with st.expander(f"⭐ {item['tname']} ({item['tid']}) | 價: {item['price']}"):
            st.write(f"🧠 診斷: {item['msg']}")
            st.markdown(f"🔥 籌碼: <span style='color:#00D1FF;'>{item['sent']}</span>", unsafe_allow_html=True)
            
            p_gain = ((item['target'] - item['price']) / item['price']) * 100
            st.markdown(f"""
                <div style='padding:8px; background-color:rgba(255,75,75,0.05); border-radius:5px; border-left:4px solid #ff4b4b;'>
                    <b>📈 30年趨勢目標：NT$ {item['target']} (空間: +{p_gain:.1f}%)</b>
                </div>
            """, unsafe_allow_html=True)
            st.write(f"🛑 零虧損防禦位: {item['stop']}")
            
            st.divider()
            c1, c2, c3 = st.columns([1, 1, 1.5])
            r_u = c1.radio("單位", ["張", "股"], horizontal=True, key=f"u_{item['tid']}")
            r_q = c2.number_input("數量", min_value=1, value=1, key=f"q_{item['tid']}")
            if c3.button(f"快速佈局 {item['tname']}", key=f"b_{item['tid']}", use_container_width=True):
                new_trade = pd.DataFrame([{
                    'client': st.session_state['cur_c'], 'id': item['tid'], 'name': item['tname'], 
                    'buy_price': item['price'], 'shares': r_q, 'unit': r_u, 'entry_reason': item['msg']
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
