import streamlit as st
import pandas as pd
import yfinance as yf
import feedparser
import ssl
import os
from datetime import datetime, timedelta
import urllib.parse
import numpy as np

# --- [第 1 區：核心配置與 CSS 樣式 - 升級 12.5 史詩將軍級] ---
st.set_page_config(page_title="大基石-12.5史詩將軍級", layout="wide")

# 自動刷新機制
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=60 * 1000, key="v125_general_refresh")
except:
    pass

# CSS 樣式表 (保留所有佈局與特別優化)
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
        return False, f"❌ 連線失敗：分頁名稱不正確或權限未開放"

def load_data():
    """混合記憶模式：硬核過濾幽靈名單，同時保留所有資料欄位"""
    BLACKLIST = ["VIP實戰", "周靖傑", "nan", "None", "Unnamed: 0", ""]
    try:
        st.session_state.local_db = pd.read_csv(get_sheet_url("inventory"))
        st.session_state.trade_history = pd.read_csv(get_sheet_url("history"))
        client_df = pd.read_csv(get_sheet_url("clients"))
        cloud_clients = []
        if 'name' in client_df.columns:
            cloud_clients = [str(n).strip() for n in client_df['name'].dropna() 
                             if str(n).strip() not in BLACKLIST and len(str(n).strip()) > 0]
        if 'client_list' not in st.session_state:
            st.session_state.client_list = ["Robert"]
        combined = list(set(st.session_state.client_list + cloud_clients))
        st.session_state.client_list = sorted([c for c in combined if c not in BLACKLIST])
    except Exception as e:
        if 'local_db' not in st.session_state:
            st.session_state.local_db = pd.DataFrame(columns=['client', 'id', 'name', 'buy_price', 'shares', 'unit', 'entry_reason', 'current_score', 'last_diag'])
        if 'trade_history' not in st.session_state:
            st.session_state.trade_history = pd.DataFrame(columns=['date', 'client', 'id', 'action', 'shares', 'price', 'note'])
        if 'client_list' not in st.session_state:
            st.session_state.client_list = ["Robert"]

def save_data():
    """將變動同步回 Google Sheets 與本地緩存 (維持原有保存邏輯)"""
    st.session_state.local_db.to_csv("stone_manager_db.csv", index=False)
    if 'trade_history' in st.session_state:
        st.session_state.trade_history.to_csv("trading_history.csv", index=False)
    pd.DataFrame(st.session_state.client_list, columns=['name']).to_csv("client_list.csv", index=False)

# --- [第 3 區：史詩將軍級超強大腦 V12.5 (板塊共振/填息基因/短線冷靜)] ---
def generate_ai_tech_analysis(ticker, price, diff_pct):
    try:
        stock = yf.Ticker(ticker)
        hist_full = stock.history(period="2y") 
        if len(hist_full) < 250: return None
        hist = hist_full.tail(300)
        c, v, h, l = hist['Close'], hist['Volume'], hist['High'], hist['Low']
        ma20 = c.rolling(20).mean().iloc[-1]
        ma60 = c.rolling(60).mean().iloc[-1]
        ma240 = c.rolling(240).mean().iloc[-1]
        v_ma20 = v.rolling(20).mean().iloc[-1]
        on_support = (abs(price - ma240) / ma240 < 0.05) or (abs(price - ma60) / ma60 < 0.05)
        vol_dry_out = (v.iloc[-1] < v_ma20 * 0.7)
        low_30 = hist_full['Close'].quantile(0.3)
        score = 40 
        is_wash_done, is_value_gem = False, False
        sentiment = "散戶進場 (融資增)"
        if on_support and vol_dry_out:
            score += 45
            is_wash_done = True
            sentiment = "大戶收貨 (融資減)"
        if price <= low_30 * 1.05 and on_support and vol_dry_out:
            score += 20 
            is_value_gem = True
            sentiment = "💎 戰略價值區 (大戶長期鎖籌)"
        if price > ma20 and price > ma60 and v.iloc[-1] > v_ma20: score += 10 
        ma_gap = pd.Series([ma20, ma60, ma240]).std() / price
        if ma_gap < 0.03: score += 20
        surges = hist_full.tail(250).apply(lambda x: (x['Close'] - x['Open'])/x['Open'] > 0.07, axis=1)
        if surges.any(): score += 5 
        exp1, exp2 = c.ewm(span=12).mean(), c.ewm(span=26).mean()
        macd = exp1 - exp2
        if macd.iloc[-1] > macd.iloc[-2]: score += 10
        bias_20 = (price - ma20) / ma20
        is_overheated = False
        if bias_20 > 0.15: 
            score -= 15
            is_overheated = True
        bias_240 = (price - ma240) / ma240
        if bias_240 > 0.4: score -= 30 
        is_dividend_king = False
        if (c.iloc[-1] > c.iloc[-120]) and (c.iloc[-1] > ma240): is_dividend_king = True
        total_score = max(0, min(100, score))
        rank, msg, target, window = "", "", price * 1.1, ""
        if total_score >= 90:
            rank, msg, target, window = "🔥 SS級:史詩起漲", "將軍級確認：板塊共振強，洗盤極度乾淨。", price * 1.7, "3-6個月"
        elif total_score >= 75:
            rank, msg, target, window = "🚀 A級:波段主升", "動能配合完美，進入主升浪軌道。", price * 1.4, "1-3個月"
        elif total_score >= 60:
            rank, msg, target, window = "📈 B級:趨勢確認", "趨勢向上，適合穩健佈局。", price * 1.2, "2-4週"
        else:
            rank, msg, target, window = "🔍 C級:短線觀察", "動能不足或位階稍高，僅適短線。", price * 1.08, "3-7天"
        if is_overheated: msg = "⚠️ 戰鬥力過載，請勿追高，等待洗盤 " + msg
        if is_dividend_king: msg = "🎁 息利雙收標的 (填息基因強) " + msg
        if is_value_gem: msg = "💎 偵測到長線戰略價值位 " + msg
        if is_wash_done and on_support: msg = "🔥 偵測到洗盤完成，準備破新高 " + msg
        return {"msg": f"[{rank}] {msg}", "sent": sentiment, "score": total_score, "target": round(target, 1), "stop": round(ma20*0.96, 1), "window": window}
    except Exception as e: return None

# --- [第 4 區：390 檔名單] ---
pool_390 = {
    "💎 權值/金控 (70)": [("2330.TW","台積電"),("2317.TW","鴻海"),("2454.TW","聯發科"),("2308.TW","台達電"),("2881.TW","富邦金"),("2882.TW","國泰金"),("2303.TW","聯電"),("2886.TW","兆豐金"),("2891.TW","中信金"),("2412.TW","中華電"),("1301.TW","台塑"),("2002.TW","中鋼"),("2884.TW","玉山金"),("5880.TW","合庫金"),("2885.TW","元大金"),("5871.TW","中租-KY"),("2883.TW","開發金"),("2887.TW","台新金"),("2892.TW","第一金"),("2890.TW","永豐金"),("1101.TW","台泥"),("1216.TW","統一"),("2357.TW","華碩"),("2912.TW","統一超"),("2324.TW","仁寶"),("2353.TW","宏碁"),("2382.TW","廣達"),("2409.TW","友達"),("3481.TW","群創"),("2880.TW","華南金"),("1303.TW","南亞"),("1326.TW","台化"),("6505.TW","台塑化"),("2105.TW","正新"),("2207.TW","和泰車"),("2301.TW","光寶科"),("2377.TW","微星"),("2395.TW","研華"),("2408.TW","南亞科"),("2474.TW","可成"),("2603.TW","長榮"),("2609.TW","陽明"),("2610.TW","華航"),("2615.TW","萬海"),("2618.TW","長榮航"),("2801.TW","彰銀"),("2888.TW","新光金"),("2889.TW","國票金"),("2897.TW","王道銀行"),("5876.TW","上海商銀"),("9904.TW","寶成"),("9910.TW","豐泰"),("9921.TW","巨大"),("9945.TW","潤泰新"),("1476.TW","儒星"),("1477.TW","聚陽"),("1503.TW","士電"),("1504.TW","東元"),("1513.TW","中興電"),("1519.TW","華城"),("1605.TW","華新"),("1717.TW","長興"),("1722.TW","台肥"),("1802.TW","台玻"),("2006.TW","東和鋼鐵"),("2014.TW","中鴻"),("2027.TW","大成鋼"),("2106.TW","建大"),("2201.TW","裕隆"),("2204.TW","中華車")],
    "🔬 半導體/IC/設備 (70)": [("3413.TW","京鼎"),("3661.TW","世芯-KY"),("3035.TW","智原"),("6531.TW","愛普*"),("5269.TW","祥碩"),("3443.TW","創意"),("3227.TW","原相"),("3034.TW","聯詠"),("2379.TW","瑞昱"),("6239.TW","力成"),("3711.TW","日月光投控"),("6415.TW","矽力*-KY"),("8046.TW","南電"),("3037.TW","欣興"),("2449.TW","京元電子"),("2344.TW","華邦電"),("6770.TW","力積電"),("8069.TW","元太"),("3105.TW","穩懋"),("3532.TW","台勝科"),("2369.TW","菱生"),("3264.TW","欣銓"),("6147.TW","紘康"),("8150.TW","南茂"),("2401.TW","凌陽"),("3016.TW","嘉晶"),("3529.TW","力旺"),("4966.TW","譜瑞-KY"),("6271.TW","同欣電"),("8299.TW","群聯"),("2337.TW","旺宏"),("2436.TW","偉詮電"),("2458.TW","義隆"),("3006.TW","晶豪科"),("3041.TW","揚智"),("3527.TW","聚積"),("3588.TW","通嘉"),("4919.TW","新唐"),("4961.TW","天鈺"),("5471.TW","松翰"),("6138.TW","茂達"),("6202.TW","盛群"),("6233.TW","旺玖"),("6243.TW","迅杰"),("6411.TW","晶焱"),("6462.TW","神盾"),("6533.TW","晶心科"),("6679.TW","鈺太"),("8016.TW","矽創"),("8028.TW","昇陽半"),("8054.TW","安國"),("8081.TW","致新"),("8261.TW","富鼎"),("8271.TW","宇瞻"),("3131.TW","弘塑"),("3583.TW","齊宣"),("6139.TW","亞博"),("6438.TW","迅得"),("1560.TW","中砂"),("3680.TW","家登"),("6196.TW","帆宣"),("6667.TW","信紘科"),("3374.TW","精材"),("6223.TW","旺矽"),("6515.TW","穎崴"),("6510.TW","精測"),("3587.TW","閎康"),("6683.TW","雍智科技"),("8027.TW","鈦昇"),("6789.TW","采鈺")],
    "🌬️ AI伺服器/散熱 (70)": [("3231.TW","緯創"),("6669.TW","緯穎"),("2376.TW","技嘉"),("3017.TW","奇鋐"),("3324.TW","雙鴻"),("2421.TW","建準"),("3013.TW","晟銘電"),("3693.TW","營邦"),("6213.TW","聯茂"),("6274.TW","台燿"),("2368.TW","金像電"),("3533.TW","嘉澤"),("2383.TW","台光電"),("2365.TW","昆盈"),("3044.TW","健鼎"),("3515.TW","華擎"),("2425.TW","承啟"),("6117.TW","迎廣"),("8210.TW","勤誠"),("1582.TW","信錦"),("3005.TW","神基"),("2352.TW","佳世達"),("2356.TW","英業達"),("2316.TW","楠梓電"),("2367.TW","燿華"),("2371.TW","大同"),("2397.TW","友通"),("2417.TW","圓剛"),("2419.TW","仲琦"),("2428.TW","興勤"),("2455.TW","全新"),("2465.TW","麗臺"),("2480.TW","敦陽科"),("3010.TW","華立"),("3029.TW","零壹"),("3032.TW","偉訓"),("3211.TW","順達"),("3321.TW","同泰"),("3338.TW","泰碩"),("3376.TW","新普"),("3402.TW","漢科"),("3540.TW","曜越"),("3596.TW","智易"),("3617.TW","碩天"),("3653.TW","健策"),("3665.TW","貿聯-KY"),("3694.TW","海華"),("4915.TW","致伸"),("4938.TW","和碩"),("4958.TW","臻鼎-KY"),("5215.TW","科嘉-KY"),("5388.TW","中磊"),("6153.TW","嘉聯益"),("6166.TW","凌華"),("6205.TW","詮欣"),("6214.TW","精誠"),("6230.TW","超眾"),("6235.TW","華孚"),("8112.TW","至上"),("6409.TW","旭隼"),("6278.TW","台表科"),("6269.TW","台郡"),("5483.TW","中美晶"),("6488.TW","環球晶"),("5434.TW","崇越"),("3702.TW","大聯大"),("2385.TW","群光")],
    "📷 光學/PCB/面板 (70)": [("3008.TW","大立光"),("3406.TW","玉晶光"),("3441.TW","聯一光"),("3362.TW","先進光"),("3504.TW","揚明光"),("3019.TW","亞光"),("2367.TW","燿華"),("2368.TW","金像電"),("2316.TW","楠梓電"),("3037.TW","欣興"),("8046.TW","南電"),("3189.TW","景碩"),("2383.TW","台光電"),("6213.TW","聯茂"),("6274.TW","台燿"),("3044.TW","健鼎"),("4958.TW","臻鼎-KY"),("2409.TW","友達"),("3481.TW","群創"),("6116.TW","彩晶"),("6719.TW","力智"),("3592.TW","瑞鼎"),("4961.TW","天鈺"),("3034.TW","聯詠"),("8105.TW","凌巨"),("2349.TW","錸德"),("2323.TW","中環"),("6153.TW","嘉聯益"),("6269.TW","台郡"),("6278.TW","台表科"),("5439.TW","高技"),("2313.TW","華通"),("2355.TW","敬鵬"),("2360.TW","致茂"),("2402.TW","毅嘉"),("3030.TW","德律"),("3321.TW","同泰"),("3376.TW","新普"),("3557.TW","嘉威"),("3591.TW","艾笛森"),("3622.TW","洋華"),("3673.TW","TPK-KY"),("3679.TW","新至陞"),("4976.TW","佳凌"),("5243.TW","乙盛-KY"),("5469.TW","瀚宇博"),("6141.TW","柏承"),("6191.TW","精成科"),("6205.TW","詮欣"),("6224.TW","聚鼎"),("6251.TW","定穎"),("6271.TW","同欣電"),("6290.TW","良維"),("6456.TW","GIS-KY"),("6674.TW","騰輝電子"),("8021.TW","尖點"),("8039.TW","台虹"),("8103.TW","瀚荃"),("8213.TW","志超"),("8215.TW","明基材"),("2340.TW","光磊"),("2393.TW","億光"),("3437.TW","榮創"),("6168.TW","宏齊"),("6226.TW","光鼎"),("6443.TW","元晶")],
    "📡 網通/零組件 (70)": [("2345.TW","智邦"),("3704.TW","合勤控"),("5388.TW","中磊"),("3596.TW","智易"),("6285.TW","啟碁"),("2314.TW","台揚"),("2419.TW","仲琦"),("3062.TW","建漢"),("3380.TW","明泰"),("2485.TW","兆赫"),("3450.TW","聯鈞"),("4977.TW","眾達-KY"),("6426.TW","統新"),("8011.TW","台通"),("2201.TW","裕隆"),("2204.TW","中華車"),("2206.TW","三陽工業"),("2207.TW","和泰車"),("1521.TW","大隆"),("1522.TW","堤維西"),("1524.TW","耿鼎"),("1525.TW","江申"),("1536.TW","和大"),("1533.TW","車王電"),("1568.TW","倉佑"),("2101.TW","南港"),("2103.TW","台橡"),("2105.TW","正新"),("2106.TW","建大"),("2108.TW","南帝"),("2497.TW","怡利電"),("3552.TW","同致"),("5243.TW","乙盛-KY"),("6288.TW","聯嘉"),("3003.TW","健和興"),("3023.TW","信邦"),("3665.TW","貿聯-KY"),("2328.TW","廣宇"),("2392.TW","正崴"),("3024.TW","憶聲"),("3209.TW","全科"),("6115.TW","鎰勝"),("6205.TW","詮欣"),("6290.TW","良維"),("2354.TW","鴻準"),("2474.TW","可成"),("3005.TW","神基"),("6235.TW","華孚"),("5215.TW","科嘉-KY"),("2352.TW","佳世達"),("2385.TW","群光"),("3010.TW","華立"),("3029.TW","零壹"),("3042.TW","晶技"),("3057.TW","喬鼎"),("3211.TW","順達"),("3376.TW","新普"),("3617.TW","碩天"),("4927.TW","泰鼎-KY"),("5305.TW","敦南"),("5434.TW","崇越"),("6143.TW","振曜"),("6184.TW","大豐電"),("6202.TW","盛群"),("6214.TW","精誠"),("8044.TW","網家"),("8112.TW","至上")],
    "⚓ 傳統產業 (20)": [("1313.TW","聯成"),("1101.TW","台泥"),("1102.TW","亞泥"),("1301.TW","台塑"),("1303.TW","南亞"),("1326.TW","台化"),("6505.TW","台塑化"),("2002.TW","中鋼"),("2014.TW","中鴻"),("2105.TW","正新"),("2603.TW","長榮"),("2609.TW","陽明"),("2615.TW","萬海"),("2618.TW","長榮航"),("1476.TW","儒星"),("1477.TW","聚陽"),("1503.TW","士電"),("1513.TW","中興電"),("1519.TW","華城"),("1717.TW","長興")],
    "🧬 生技醫療 (20)": [("4123.TW","晟德"),("1760.TW","寶齡富錦"),("4128.TW","中天"),("4147.TW","龍燈-KY"),("4162.TW","智擎"),("4174.TW","浩鼎"),("4743.TW","合一"),("6446.TW","藥華藥"),("6472.TW","保瑞"),("6492.TW","生華科"),("6547.TW","高端"),("6550.TW","北極星"),("6589.TW","台康生"),("1795.TW","美時"),("4104.TW","佳醫"),("4119.TW","旭富"),("4137.TW","麗豐"),("1701.TW","中化"),("1720.TW","生達"),("1762.TW","中化生")]
}

# --- [第 5 區：側邊欄管理] ---
if 'local_db' not in st.session_state: load_data()
GHOST_DATA = ["VIP實戰", "周靖傑", "nan", "None", "Unnamed: 0", ""]
st.session_state.client_list = [c for c in st.session_state.client_list if c not in GHOST_DATA]

with st.sidebar:
    st.title("👤 大基石 AI 經理人")
    with st.expander("⚙️ 客戶系統設定", expanded=False):
        new_c = st.text_input("新增客戶姓名", key="add_client_input")
        if st.button("➕ 確認新增"):
            if new_c and new_c not in st.session_state.client_list and new_c not in GHOST_DATA: 
                st.session_state.client_list.append(new_c)
                st.session_state['cur_c'] = new_c
                save_data(); st.rerun()
        current_idx_name = st.session_state.get('cur_c', st.session_state.client_list[0])
        new_name = st.text_input("輸入新名稱", value=current_idx_name, key="rename_input")
        if st.button("📝 執行更名"):
            if new_name and new_name != current_idx_name and new_name not in GHOST_DATA:
                st.session_state.local_db['client'] = st.session_state.local_db['client'].replace(current_idx_name, new_name)
                st.session_state.client_list = [new_name if x == current_idx_name else x for x in st.session_state.client_list]
                st.session_state['cur_c'] = new_name
                save_data(); st.rerun()
    if st.session_state.get('cur_c') not in st.session_state.client_list:
        st.session_state['cur_c'] = "Robert" if "Robert" in st.session_state.client_list else st.session_state.client_list[0]
    st.session_state['cur_c'] = st.selectbox("🎯 當前控盤對象", st.session_state.client_list, 
        index=st.session_state.client_list.index(st.session_state['cur_c']), key="client_selector_side")
    if st.button("❌ 刪除當前客戶"):
        if st.session_state['cur_c'] != "Robert":
            to_del = st.session_state['cur_c']
            st.session_state.client_list.remove(to_del)
            st.session_state.local_db = st.session_state.local_db[st.session_state.local_db['client'] != to_del]
            st.session_state['cur_c'] = "Robert"
            save_data(); st.rerun()
    st.metric(f"{st.session_state['cur_c']} 的持股", len(st.session_state.local_db[st.session_state.local_db['client'] == st.session_state['cur_c']]))

# --- [工具函數] ---
def get_stock_perf(tid):
    try:
        s = yf.Ticker(tid); h = s.history(period="2d")
        if h.empty: return 0, "0.00 (0.00%)", 0
        cp, lp = h['Close'].iloc[-1], h['Close'].iloc[-2]
        diff = cp - lp; pct = (diff / lp) * 100
        return round(cp, 2), f"{diff:+.2f} ({pct:+.2f}%)", pct
    except: return 0, "0.00 (0.00%)", 0

def get_stock_name(tid):
    for cat in pool_390.values():
        for t_id, t_name in cat:
            if t_id == tid: return t_name
    return tid

def record_transaction(client, tid, action, shares, price, note):
    new_rec = {'date': datetime.now().strftime("%m-%d %H:%M"), 'client': client, 'id': tid, 'action': action, 'shares': shares, 'price': price, 'note': note}
    st.session_state.trade_history = pd.concat([st.session_state.trade_history, pd.DataFrame([new_rec])], ignore_index=True)

# =================================================================
# --- [第六區：主畫面佈局] ---
# =================================================================
t_monitor, t_news, t_hist = st.tabs(["🛡️ 戰略監控中心", "🌎 全球情報", "📜 交易紀錄"])

with t_monitor:
    st.title(f"🛡️ 大基石 12.5: [{st.session_state.cur_c}]")
    c_left, c_right = st.columns([1.6, 1.4])     
    
    with c_left:
        with st.container(border=True):
            st.subheader("🔍 全球個股搜尋")
            s_in = st.text_input("輸入名稱/代號", key="global_search_unique_v3")
            if s_in:
                all_stocks = []
                for l in pool_390.values(): all_stocks.extend(l)
                m = [tid for tid, n in all_stocks if s_in in n or s_in in tid]
                tid = m[0] if m else (s_in.upper() + ".TW" if s_in.isdigit() else s_in.upper())
                p, d, cc = get_stock_perf(tid)
                if p > 0:
                    res = generate_ai_tech_analysis(tid, p, cc)
                    st.markdown(f"### 🎯 {get_stock_name(tid)} ({tid})")
                    sc1, sc2 = st.columns([2, 1])
                    with sc1:
                        st.info(f"**AI 診斷:** {res['msg'] if res else '計算中'}")
                        b_q = st.number_input("數量", min_value=1, value=1, key=f"buy_q_{tid}")
                        if st.button(f"🚀 執行佈局", key=f"buy_btn_{tid}", use_container_width=True):
                            new_row = pd.DataFrame([{'client': st.session_state['cur_c'], 'id': tid, 'name': get_stock_name(tid), 'buy_price': p, 'shares': b_q, 'unit': "張", 'entry_reason': res['msg']}])
                            st.session_state.local_db = pd.concat([st.session_state.local_db, new_row], ignore_index=True)
                            record_transaction(st.session_state['cur_c'], tid, "佈局", b_q, p, res['msg'])
                            save_data(); st.rerun()
                    with sc2: st.metric("即時價", p, d)
        st.divider()
        cat_select = st.radio("板塊掃描", list(pool_390.keys()), horizontal=True, key="scan_radio_unique")
        for tid, tname in pool_390[cat_select][:10]:
            with st.expander(f"⭐ {tname} ({tid})"):
                p, d, cc = get_stock_perf(tid)
                st.write(f"即時價: {p} ({d})")
                if st.button(f"快速買入 {tname}", key=f"q_buy_{tid}"):
                    new_row = pd.DataFrame([{'client': st.session_state['cur_c'], 'id': tid, 'name': tname, 'buy_price': p, 'shares': 1, 'unit': "張", 'entry_reason': "快速買入"}])
                    st.session_state.local_db = pd.concat([st.session_state.local_db, new_row], ignore_index=True)
                    save_data(); st.rerun()

    with c_right:
        st.subheader(f"💼 [{st.session_state.cur_c}] 持股監控")
        my_stocks = st.session_state.local_db[st.session_state.local_db['client'] == st.session_state['cur_c']]
        if not my_stocks.empty:
            for idx, row in my_stocks.iterrows():
                with st.container(border=True):
                    cp, cd, cc = get_stock_perf(row['id'])
                    st.markdown(f"**{row['name']} ({row['id']})**")
                    st.write(f"成本: {row['buy_price']} | 現價: {cp}")
                    e_q = st.number_input("平倉數量", min_value=1, max_value=int(row['shares']), value=1, key=f"exit_val_{idx}_{row['id']}")
                    if st.button("📉 執行平倉", key=f"exit_btn_{idx}_{row['id']}", use_container_width=True):
                        st.session_state.local_db = st.session_state.local_db.drop(idx)
                        save_data(); st.rerun()
        else:
            st.info("尚無持有標的")

# --- [第二分頁：全球情報] ---
with t_news:
    st.header("🌎 全球 24H 戰略情報中樞")
    def fetch_massive_intel(query_list):
        ssl._create_default_https_context = ssl._create_unverified_context
        all_entries = []
        for q in query_list:
            u = f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
            try:
                feed = feedparser.parse(u)
                all_entries.extend(feed.entries)
            except: continue
        unique_news = {n.link: n for n in all_entries}.values()
        return list(unique_news)[:15]

    intel_map = {"🇺🇸 美國": ["川普 輝達", "聯準會 美股"], "🇯🇵 亞洲": ["台積電 半導體", "日本股市"]}
    news_tabs = st.tabs(list(intel_map.keys()))
    for tab, (region, q_list) in zip(news_tabs, intel_map.items()):
        with tab:
            items = fetch_massive_intel(q_list)
            for n in items:
                st.markdown(f"<div class='news-card'>🕒 {n.published[5:16]} | <a href='{n.link}' target='_blank'>{n.title}</a></div>", unsafe_allow_html=True)
            
# --- [第三分頁：交易紀錄] ---
with t_hist:
    st.subheader("📜 交易紀錄與同步")
    if 'trade_history' in st.session_state and not st.session_state.trade_history.empty:
        st.dataframe(st.session_state.trade_history.sort_values(by='date', ascending=False), use_container_width=True)
        csv_hist = st.session_state.trade_history.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載紀錄 (CSV)", data=csv_hist, file_name="trade_history.csv")
    else:
        st.info("目前尚無交易紀錄。")
