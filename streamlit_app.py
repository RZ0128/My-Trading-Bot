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

# --- [3. 數據與 AI 引擎] ---
@st.cache_data(ttl=300)
def get_stock_perf(ticker, base_score):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="2d")
        if len(df) >= 2:
            curr_p = df['Close'].iloc[-1]
            prev_p = df['Close'].iloc[-2]
            diff = curr_p - prev_p
            pct = (diff / prev_p) * 100
            color = "price-up" if diff > 0 else "price-down"
            return round(curr_p, 1), f"{pct:+.2f}%", color
    except: pass
    return 0.0, "0.00%", "price-even"

def generate_ai_tech_analysis(ticker, price, diff_pct):
    try:
        stock = yf.Ticker(ticker)
        # 為了偵測年線洗盤，獲取更長的歷史數據
        hist = stock.history(period="300d")
        if len(hist) < 240: return None
        
        c = hist['Close']
        v = hist['Volume']
        ma20 = c.rolling(20).mean().iloc[-1]
        ma60 = c.rolling(60).mean().iloc[-1]
        ma240 = c.rolling(240).mean().iloc[-1] # 年線
        v_ma5 = v.rolling(5).mean().iloc[-1]
        
        # 強化邏輯：洗盤偵測與大戶收貨
        # 1. 股價回檔至年線(正負5%)且成交量縮(低於5日均量70%)
        is_wash_out = (price <= ma240 * 1.05 and price >= ma240 * 0.95) and (v.iloc[-1] < v_ma5 * 0.7)
        # 2. 底部穩定度
        is_stable_3m = (c.tail(60).max() - c.tail(60).min()) / c.tail(60).mean() < 0.15 
        
        score = 0
        diag = []
        sentiment = "籌碼中性"

        if is_wash_out:
            score += 50
            diag.append("🔥 偵測到洗盤完成，準備破新高")
            sentiment = "🔥 大戶收貨 (融資減)"
        
        # 針對資深經理人邏輯補強 (低位階、PB低、法人進貨)
        if price < ma240 and diff_pct > 0:
            score += 20
            diag.append("🛡️ 價值窪地：低位階反轉")
            
        if is_stable_3m: score += 15; diag.append("🛡️ 底部整理逾3個月")
        if price > ma20: score += 5

        return {
            "msg": " | ".join(diag) if diag else "趨勢觀察中",
            "sent": sentiment, "score": score,
            "entry": round(ma20 if price > ma20 else price * 0.98, 1),
            "target": round(price * 1.15, 1),
            "stop": round(min(ma20, ma240) * 0.95, 1)
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
    target_client = st.selectbox("🎯 當前控盤對象", st.session_state.client_list)
    st.session_state['cur_c'] = target_client

# --- [6. 主畫面邏輯：5大類別 + 2新增類別] ---
st.title(f"🛡️ 大基石 AI 精銳控盤：[{st.session_state['cur_c']}]")
col_l, col_r = st.columns([1.6, 1.4])

with col_l:
    pool_350 = {
        "💎 權值/金控/高EPS (70)": [("2330.TW","台積電"),("2317.TW","鴻海"),("2454.TW","聯發科"),("2308.TW","台達電"),("2881.TW","富邦金"),("2882.TW","國泰金"),("2303.TW","聯電"),("2886.TW","兆豐金"),("2891.TW","中信金"),("2412.TW","中華電"),("1301.TW","台塑"),("2002.TW","中鋼"),("2884.TW","玉山金"),("5880.TW","合庫金"),("2885.TW","元大金"),("5871.TW","中租-KY"),("2883.TW","開發金"),("2887.TW","台新金"),("2892.TW","第一金"),("2890.TW","永豐金"),("1101.TW","台泥"),("1216.TW","統一"),("2357.TW","華碩"),("2912.TW","統一超"),("2324.TW","仁寶"),("2353.TW","宏碁"),("2382.TW","廣達"),("2409.TW","友達"),("3481.TW","群創"),("2880.TW","華南金"),("1303.TW","南亞"),("1326.TW","台化"),("6505.TW","台塑化"),("2105.TW","正新"),("2207.TW","和泰車"),("2301.TW","光寶科"),("2377.TW","微星"),("2395.TW","研華"),("2408.TW","南亞科"),("2474.TW","可成"),("2603.TW","長榮"),("2609.TW","陽明"),("2610.TW","華航"),("2615.TW","萬海"),("2618.TW","長榮航"),("2801.TW","彰銀"),("2888.TW","新光金"),("2889.TW","國票金"),("2897.TW","王道銀行"),("5876.TW","上海商銀"),("9904.TW","寶成"),("9910.TW","豐泰"),("9921.TW","巨大"),("9945.TW","潤泰新"),("1476.TW","儒星"),("1477.TW","聚陽"),("1503.TW","士電"),("1504.TW","東元"),("1513.TW","中興電"),("1519.TW","華城"),("1605.TW","華新"),("1717.TW","長興"),("1722.TW","台肥"),("1802.TW","台玻"),("2006.TW","東和鋼鐵"),("2014.TW","中鴻"),("2027.TW","大成鋼"),("2106.TW","建大"),("2201.TW","裕隆"),("2204.TW","中華車")],
        "🔬 半導體/IC/設備 (70)": [("3413.TW","京鼎"),("3661.TW","世芯-KY"),("3035.TW","智原"),("6531.TW","愛普*"),("5269.TW","祥碩"),("3443.TW","創意"),("3227.TW","原相"),("3034.TW","聯詠"),("2379.TW","瑞昱"),("6239.TW","力成"),("3711.TW","日月光投控"),("6415.TW","矽力*-KY"),("8046.TW","南電"),("3037.TW","欣興"),("2449.TW","京元電子"),("2408.TW","南亞科"),("2344.TW","華邦電"),("6770.TW","力積電"),("8069.TW","元太"),("3105.TW","穩懋"),("3532.TW","台勝科"),("2369.TW","菱生"),("3264.TW","欣銓"),("6147.TW","紘康"),("8150.TW","南茂"),("2401.TW","凌陽"),("3016.TW","嘉晶"),("3529.TW","力旺"),("4966.TW","譜瑞-KY"),("6271.TW","同欣電"),("8299.TW","群聯"),("2337.TW","旺宏"),("2436.TW","偉詮電"),("2458.TW","義隆"),("3006.TW","晶豪科"),("3041.TW","揚智"),("3527.TW","聚積"),("3588.TW","通嘉"),("4919.TW","新唐"),("4961.TW","天鈺"),("5471.TW","松翰"),("6138.TW","茂達"),("6202.TW","盛群"),("6233.TW","旺玖"),("6243.TW","迅杰"),("6411.TW","晶焱"),("6462.TW","神盾"),("6533.TW","晶心科"),("6679.TW","鈺太"),("8016.TW","矽創"),("8028.TW","昇陽半"),("8054.TW","安國"),("8081.TW","致新"),("8261.TW","富鼎"),("8271.TW","宇瞻"),("3131.TW","弘塑"),("3583.TW","齊宣"),("6139.TW","亞博"),("6438.TW","迅得"),("1560.TW","中砂"),("3680.TW","家登"),("6196.TW","帆宣"),("6667.TW","信紘科"),("3374.TW","精材"),("6223.TW","旺矽"),("6515.TW","穎崴"),("6510.TW","精測"),("3587.TW","閎康"),("6683.TW","雍智科技")],
        "🌬️ AI伺服器/散熱 (70)": [("2382.TW","廣達"),("3231.TW","緯創"),("6669.TW","緯穎"),("2357.TW","華碩"),("2376.TW","技嘉"),("3017.TW","奇鋐"),("3324.TW","雙鴻"),("2421.TW","建準"),("3013.TW","晟銘電"),("3693.TW","營邦"),("2324.TW","仁寶"),("2353.TW","宏碁"),("2301.TW","光寶科"),("6213.TW","聯茂"),("6274.TW","台燿"),("2368.TW","金像電"),("3533.TW","嘉澤"),("2383.TW","台光電"),("2365.TW","昆盈"),("3044.TW","健鼎"),("3515.TW","華擎"),("2425.TW","承啟"),("6117.TW","迎廣"),("8210.TW","勤誠"),("1582.TW","信錦"),("2474.TW","可成"),("3005.TW","神基"),("2352.TW","佳世達"),("2356.TW","英業達"),("2316.TW","楠梓電"),("2367.TW","燿華"),("2371.TW","大同"),("2397.TW","友通"),("2417.TW","圓剛"),("2419.TW","仲琦"),("2428.TW","興勤"),("2455.TW","全新"),("2465.TW","麗臺"),("2480.TW","敦陽科"),("3010.TW","華立"),("3029.TW","零壹"),("3032.TW","偉訓"),("3037.TW","欣興"),("3211.TW","順達"),("3321.TW","同泰"),("3338.TW","泰碩"),("3376.TW","新普"),("3402.TW","漢科"),("3540.TW","曜越"),("3596.TW","智易"),("3617.TW","碩天"),("3653.TW","健策"),("3665.TW","貿聯-KY"),("3694.TW","海華"),("4915.TW","致伸"),("4938.TW","和碩"),("4958.TW","臻鼎-KY"),("5215.TW","科嘉-KY"),("5388.TW","中磊"),("6153.TW","嘉聯益"),("6166.TW","凌華"),("6205.TW","詮欣"),("6214.TW","精誠"),("6230.TW","超眾"),("6235.TW","華孚")],
        "⚓ 傳統產業 (20)": [("1313.TW","聯成"),("1101.TW","台泥"),("1102.TW","亞泥"),("1301.TW","台塑"),("1303.TW","南亞"),("2002.TW","中鋼"),("2014.TW","中鴻"),("2105.TW","正新"),("2603.TW","長榮"),("2609.TW","陽明"),("2615.TW","萬海"),("2618.TW","長榮航"),("1476.TW","儒星"),("1477.TW","聚陽"),("1503.TW","士電"),("1513.TW","中興電"),("1519.TW","華城"),("9921.TW","巨大"),("1717.TW","長興"),("1802.TW","台玻")],
        "🧬 生技醫療 (20)": [("4123.TW","晟德"),("1760.TW","寶齡富錦"),("4128.TW","中天"),("4147.TW","龍燈-KY"),("4162.TW","智擎"),("4174.TW","浩鼎"),("4743.TW","合一"),("6446.TW","藥華藥"),("6472.TW","保瑞"),("6492.TW","生華科"),("6547.TW","高端"),("6550.TW","北極星"),("6589.TW","台康生"),("1795.TW","美時"),("4104.TW","佳醫"),("4119.TW","旭富"),("4137.TW","麗豐"),("6620.TW","岳豐"),("6703.TW","軒郁"),("1786.TW","財團")]
    }
    
    cat = st.radio("產業板塊", list(pool_350.keys()), horizontal=True)
    
    with st.spinner(f"正在掃描庫存標的..."):
        scored_data = []
        for tid, tname in pool_350[cat]:
            p, d, c = get_stock_perf(tid, 0)
            try: d_val = float(d.replace('%','').replace('+',''))
            except: d_val = 0
            res = generate_ai_tech_analysis(tid, p, d_val)
            if res:
                res.update({'tid': tid, 'tname': tname, 'price': p, 'diff': d, 'color': c})
                scored_data.append(res)
        
        # 顯示該類別所有標的 (按 AI 分數排序)
        display_list = sorted(scored_data, key=lambda x: x['score'], reverse=True)

    st.subheader(f"🚀 {cat}：完整清單 ({len(display_list)} 檔)")
    for item in display_list:
        with st.expander(f"⭐ {item['tname']} ({item['tid']}) | 現價: {item['price']} ({item['diff']}) | 分數: {item['score']}"):
            c1, c2 = st.columns([1.5, 1])
            with c1:
                st.markdown(f"**實戰診斷:** {item['msg']}")
                st.markdown(f"**Sentiment:** <span style='color:#00D1FF;'>{item['sent']}</span>", unsafe_allow_html=True)
                st.markdown(f"**🔥 建議買入:** <span style='color:red;'>{item['entry']}</span>", unsafe_allow_html=True)
                u_col, q_col = st.columns(2)
                unit = u_col.radio("單位", ["張", "股"], key=f"unit_{item['tid']}", horizontal=True)
                qty = q_col.number_input("數量", min_value=1, value=1, key=f"qty_{item['tid']}")
                
                if st.button(f"確認佈局 {item['tname']}", key=f"btn_{item['tid']}"):
                    new_trade = pd.DataFrame([{'client': st.session_state['cur_c'], 'id': item['tid'], 'name': item['tname'], 'buy_price': item['price'], 'shares': qty, 'unit': unit, 'entry_reason': item['msg']}])
                    st.session_state.local_db = pd.concat([st.session_state.local_db, new_trade], ignore_index=True)
                    save_data()
                    st.toast(f"✅ 已存檔至本地資料庫")
                    st.rerun()
            with c2:
                st.success(f"🎯 目標: {item['target']}")
                st.error(f"🛑 止損: {item['stop']}")

# --- [7. 右側監控區：實戰持股 - V11.4] ---
with col_r:
    st.subheader(f"💼 [{st.session_state['cur_c']}] 實戰持股明細")
    my_holdings = st.session_state.local_db[st.session_state.local_db['client'] == st.session_state['cur_c']]
    
    if my_holdings.empty:
        st.info("目前尚無持股數據。")
    else:
        total_unrealized_pnl = 0 
        for idx, row in my_holdings.iterrows():
            cp, cd, cc = get_stock_perf(row['id'], 0)
            try: d_val = float(cd.replace('%','').replace('+',''))
            except: d_val = 0
            res = generate_ai_tech_analysis(row['id'], cp, d_val)
            if res:
                multiplier = 1000 if row['unit'] == "張" else 1
                stock_pnl = (cp - row['buy_price']) * row['shares'] * multiplier
                total_unrealized_pnl += stock_pnl
                pnl_color = "#e04e4e" if stock_pnl >= 0 else "#4ea04e"
                
                with st.container(border=True):
                    t_col1, t_col2 = st.columns([1.5, 1])
                    t_col1.markdown(f"**{row['name']}** <small>{row['id']}</small>", unsafe_allow_html=True)
                    t_col2.markdown(f"<div style='text-align:right; color:{pnl_color}; font-weight:bold;'>NT$ {stock_pnl:,.0f}</div>", unsafe_allow_html=True)
                    d_col1, d_col2, d_col3 = st.columns(3)
                    d_col1.caption(f"現價: {cp}")
                    d_col2.caption(f"成本: {row['buy_price']}")
                    d_col3.markdown(f"<small>持股: <b>{row['shares']}</b> {row['unit']}</small>", unsafe_allow_html=True)
                    
                    with st.expander(f"⚙️ 減持 / 平倉 ({row['unit']})"):
                        st.write(f"當前單位：{row['unit']}")
                        sell_col1, sell_col2 = st.columns([1.5, 1])
                        s_qty = sell_col1.number_input(f"減持數", min_value=1, max_value=int(row['shares']), value=1, key=f"sq_{idx}")
                        if sell_col2.button("確認", key=f"sbtn_{idx}", use_container_width=True):
                            if s_qty >= row['shares']: st.session_state.local_db = st.session_state.local_db.drop(idx)
                            else: st.session_state.local_db.at[idx, 'shares'] -= s_qty
                            save_data()
                            st.rerun()
                    if cp < res['stop']: st.markdown(f"<small style='color:#4ea04e;'>🛑 跌破止損 {res['stop']}</small>", unsafe_allow_html=True)
                    elif cp >= res['target']: st.markdown(f"<small style='color:#e04e4e;'>🎯 達標預警 {res['target']}</small>", unsafe_allow_html=True)

        st.markdown("---")
        total_color = "#e04e4e" if total_unrealized_pnl >= 0 else "#4ea04e"
        st.markdown(f"<div style='padding:12px; border:1px solid #ddd; border-radius:8px; text-align:center;'><div style='font-size:13px; color:#666;'>帳戶總未實現損益</div><div style='font-size:22px; font-weight:bold; color:{total_color};'>NT$ {total_unrealized_pnl:,.0f}</div></div>", unsafe_allow_html=True)

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
