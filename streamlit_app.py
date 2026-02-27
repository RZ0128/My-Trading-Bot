import streamlit as st
import pandas as pd
import yfinance as yf
import feedparser
import ssl
from datetime import datetime
import urllib.parse

# --- 核心配置 ---
st.set_page_config(page_title="AI Manager 8.5 - Consolidation", layout="wide")

try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=60 * 1000, key="v85_pulse")
except:
    pass

st.markdown("""
    <style>
    html, body, [class*="css"] { font-size: 13px !important; color: #1e1e1e; }
    .stButton>button { height: 26px; padding: 0px 10px; font-size: 11px; border-radius: 5px; }
    .news-card { border-left: 4px solid #cc0000; padding-left: 12px; margin-bottom: 8px; font-size: 12px; border-bottom: 1px solid #eee; padding-bottom: 5px; }
    .price-up { color: #ff0000; font-weight: bold; }
    .price-down { color: #008000; font-weight: bold; }
    .profit-text { font-size: 14px; font-weight: bold; }
    .region-banner { background-color: #001f3f; color: white; padding: 8px; border-radius: 4px; font-weight: bold; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 數據引擎 ---
def get_stock_perf(ticker, base_score):
    search_list = [ticker, ticker.replace(".TW", ".TWO")] if ".TW" in ticker else [ticker]
    for t in search_list:
        try:
            stock = yf.Ticker(t)
            df = stock.history(period="2d")
            if len(df) >= 2:
                curr_p = df['Close'].iloc[-1]
                diff = curr_p - df['Close'].iloc[-2]
                color = "price-up" if diff > 0 else "price-down" if diff < 0 else "price-even"
                dynamic_score = base_score + (1 if diff > 0 else -1)
                return round(curr_p, 1), f"{diff:+.1f}", color, dynamic_score
        except: continue
    return 0.0, "0.0", "price-even", base_score

# --- 狀態管理 ---
if 'client_battles' not in st.session_state:
    st.session_state.client_battles = {}

with st.sidebar:
    st.header("👤 客戶帳戶管理")
    new_c = st.text_input("新增客戶姓名")
    if st.button("➕ 建立帳戶") and new_c:
        if new_c not in st.session_state.client_battles:
            st.session_state.client_battles[new_c] = []
            st.rerun()
    st.divider()
    all_c = list(st.session_state.client_battles.keys())
    cur_c = st.selectbox("🎯 當前操作客戶", all_c if all_c else ["請先新增客戶"])

# --- 主畫面佈局 ---
st.title(f"🛡️ AI 經理人 8.5：[{cur_c}] 戰略作戰室")
st.caption(f"鞏固版：含每股/總台幣損益、AI評分、精確下單與減倉功能")

col_l, col_r = st.columns([1.6, 1.4])

with col_l:
    st.subheader("🔥 每日 15 檔推薦 (含 AI 評分)")
    scan_list = [
        {"id": "2402.TW", "name": "毅嘉", "score": 93, "detail": "站穩 42.5 元支撐。MACD 二次金叉。"},
        {"id": "6531.TW", "name": "愛普*", "score": 95, "detail": "月日 MACD 共振。起漲第一點。"},
        {"id": "3035.TW", "name": "智原", "score": 91, "detail": "法人連買，紅 K 吞噬壓力區。"},
        {"id": "5269.TW", "name": "祥碩", "score": 94, "detail": "帶量突破年線，溢價預估 20%+。"},
        {"id": "3227.TW", "name": "原相", "score": 88, "detail": "60分K回測不破，均線斜率向上。"},
        {"id": "3034.TW", "name": "聯詠", "score": 86, "detail": "低位MACD收斂，高殖利率護體。"},
        {"id": "2603.TW", "name": "長榮", "score": 89, "detail": "運價支撐，月線多頭排列。"},
        {"id": "2317.TW", "name": "鴻海", "score": 85, "detail": "GB200 指標，220元強勢防線。"},
        {"id": "6438.TW", "name": "迅得", "score": 92, "detail": "CoWoS 設備需求，主力鎖籌。"},
        {"id": "3661.TW", "name": "世芯-KY", "score": 90, "detail": "非理性下殺後底背離，回補在即。"},
        {"id": "2330.TW", "name": "台積電", "score": 96, "detail": "AI 全球核心，拉回皆買點。"},
        {"id": "2454.TW", "name": "聯發科", "score": 84, "detail": "邊緣AI 龍頭，技術面回踩支撐。"},
        {"id": "6271.TW", "name": "同欣電", "score": 83, "detail": "低軌衛星題材，打底完成突破。"},
        {"id": "3008.TW", "name": "大立光", "score": 81, "detail": "光學元件築底，外資賣壓衰竭。"},
        {"id": "2308.TW", "name": "台達電", "score": 82, "detail": "電源管理龍頭，季線支撐強。"}
    ]

    for idx, s in enumerate(scan_list):
        price, diff, color, final_score = get_stock_perf(s['id'], s['score'])
        header = f"📊 {s['id']} {s['name']} | 評分: {final_score} | 現價: {price} | 漲跌: {diff}"
        with st.expander(header):
            st.markdown(f"**今日表現：** <span class='{color}' style='font-size:18px;'>{diff}</span>", unsafe_allow_html=True)
            st.write(f"**戰略分析：** {s['detail']}")
            st.markdown("---")
            st.write("🛒 **買入指令**")
            o_c1, o_c2, o_c3 = st.columns([1, 1, 1])
            unit = o_c1.radio("選擇單位", ["張 (1000股)", "股 (零股)"], key=f"u_{idx}")
            qty = o_c2.number_input("輸入數量", min_value=1, value=1, key=f"q_{idx}")
            actual_shares = qty * 1000 if "張" in unit else qty
            if o_c3.button("執行買入", key=f"b_{idx}"):
                if cur_c != "請先新增客戶":
                    st.session_state.client_battles[cur_c].append({
                        "id": s['id'], "name": s['name'], "buy_p": price, 
                        "shares": actual_shares
                    })
                    st.rerun()

with col_r:
    st.subheader(f"💼 {cur_c} 投資組合 (台幣損益監控)")
    total_twd_pnl = 0
    if cur_c in st.session_state.client_battles and st.session_state.client_battles[cur_c]:
        for i, itm in enumerate(st.session_state.client_battles[cur_c]):
            cp, ds, cc, _ = get_stock_perf(itm['id'], 0)
            # 計算每股台幣損益
            pnl_per_share = cp - itm['buy_p']
            twd_pnl = pnl_per_share * itm['shares']
            total_twd_pnl += twd_pnl
            pnl_pct = (cp / itm['buy_p'] - 1) * 100 if itm['buy_p'] > 0 else 0
            
            c1, c2, c3, c4 = st.columns([1.5, 1.5, 1.8, 0.8])
            c1.write(f"**{itm['name']}**\n{itm['shares']} 股")
            c2.write(f"現價: {cp}\n(成本: {itm['buy_p']})")
            
            # 呈現每股台幣損益
            pnl_color = "red" if twd_pnl >= 0 else "green"
            c3.markdown(f"損益: <span style='color:{pnl_color}; font-weight:bold;'>NT$ {twd_pnl:,.0f}</span><br><span class='{cc}'>({pnl_pct:+.2f}%)</span>", unsafe_allow_html=True)
            
            with c4:
                del_mode = st.popover("⚙️")
                del_qty = del_mode.number_input("減持股數", min_value=1, max_value=int(itm['shares']), value=int(itm['shares']), key=f"dq_{i}")
                if del_mode.button("執行", key=f"dbtn_{i}"):
                    if del_qty >= itm['shares']: st.session_state.client_battles[cur_c].pop(i)
                    else: st.session_state.client_battles[cur_c][i]['shares'] -= del_qty
                    st.rerun()
            st.divider()
        
        # 呈現帳戶總台幣損益
        total_color = "red" if total_twd_pnl >= 0 else "green"
        st.markdown(f"### 帳戶總損益估值: <span style='color:{total_color};'>NT$ {total_twd_pnl:,.0f}</span>", unsafe_allow_html=True)
        if st.button("🚨 清空帳戶"): 
            st.session_state.client_battles[cur_c] = []
            st.rerun()
    else:
        st.info("尚無持股部位")

# --- 情報引擎 (美國、歐洲、亞洲、中國深度強化) ---
st.divider()
st.header("🌎 全球 24H 戰略情報中樞")
def fetch_massive_intel(query_list):
    ssl._create_default_https_context = ssl._create_unverified_context
    all_entries = []
    for q in query_list:
        u = f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        all_entries.extend(feedparser.parse(u).entries)
    unique_news = {n.link: n for n in all_entries}.values()
    return sorted(list(unique_news), key=lambda x: x.published, reverse=True)[:18]

intel_map = {
    "🇺🇸 美國戰略": ["Trump+Elon+Musk+Wall+Street", "Nvidia+US+Market"],
    "🇪🇺 歐洲動態": ["Europe+Economy+Ukraine+ECB"],
    "🇯🇵 亞洲科技": ["Taiwan+Semiconductor+TSMC", "Japan+Nikkei"],
    "🇨🇳 中國觀點": ["中國+經濟+財經+政策 -新華網 -人民網"]
}

tabs = st.tabs(list(intel_map.keys()))
for tab, (region, q_list) in zip(tabs, intel_map.items()):
    with tab:
        items = fetch_massive_intel(q_list)
        for n in items:
            st.markdown(f"<div class='news-card'>🕒 {n.published[5:16]} | <a href='{n.link}' target='_blank'>{n.title}</a></div>", unsafe_allow_html=True)
