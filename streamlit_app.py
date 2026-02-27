import streamlit as st
import pandas as pd
import yfinance as yf
import feedparser
import ssl
from datetime import datetime, timedelta
import time
import urllib.parse
import numpy as np

# --- 核心配置 ---
st.set_page_config(page_title="AI Manager 6.7 - Command Center", layout="wide")

# 強制 60 秒刷新
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=60 * 1000, key="global_pulse")
except:
    pass

st.markdown("""
    <style>
    html, body, [class*="css"] { font-size: 13px !important; color: #1e1e1e; }
    .stButton>button { height: 26px; padding: 0px 10px; font-size: 11px; background-color: #f0f2f6; border-radius: 5px; }
    .news-card { border-left: 4px solid #cc0000; padding-left: 12px; margin-bottom: 8px; font-size: 12px; line-height: 1.3; }
    .k-up { color: #ff0000; font-weight: bold; font-size: 18px; }
    .k-down { color: #008000; font-weight: bold; font-size: 18px; }
    .k-cross { color: #666666; font-weight: bold; font-size: 18px; }
    .region-banner { background-color: #001f3f; color: white; padding: 5px; border-radius: 3px; font-weight: bold; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 強化版數據引擎 ---
def get_stock_data(ticker):
    """針對 3227 等櫃買標的優化抓取邏輯"""
    tickers_to_try = [ticker, ticker.replace(".TW", ".TWO")] if ".TW" in ticker else [ticker]
    for t in tickers_to_try:
        try:
            stock = yf.Ticker(t)
            df = stock.history(period="2d", interval="1m")
            if df.empty:
                df = stock.history(period="5d", interval="1d")
            if not df.empty:
                curr = df['Close'].iloc[-1]
                open_p = df['Open'].iloc[-1]
                diff = curr - open_p
                # K棒字形邏輯
                if abs(diff) < (open_p * 0.001): k_shape, k_class = "╋", "k-cross"
                elif diff > 0: k_shape, k_class = "⬆", "k-up"
                else: k_shape, k_class = "⬇", "k-down"
                return round(curr, 2), k_shape, k_class
        except:
            continue
    return 0.0, "?", "k-cross"

def detect_macd_divergence(ticker):
    """深度 MACD 技術判斷"""
    try:
        df = yf.Ticker(ticker).history(period="3mo", interval="1d")
        if len(df) < 30: return "分析中..."
        close = df['Close']
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        sig = macd.ewm(span=9, adjust=False).mean()
        hist = macd - sig
        # 邏輯判定
        c_p, p_p = close.iloc[-1], close.iloc[-20:-2].max()
        c_h, p_h = hist.iloc[-1], hist.iloc[-20:-2].max()
        if c_p > p_p and c_h < p_h: return "🚨 頂背離 (建議減碼)"
        if c_p < close.iloc[-20:-2].min() and c_h > hist.iloc[-20:-2].min(): return "📈 底背離 (築底買進)"
        return "多空力道平衡"
    except:
        return "計算中"

# --- 狀態管理 ---
if 'client_battles' not in st.session_state:
    st.session_state.client_battles = {}

with st.sidebar:
    st.header("👤 帳戶控制台")
    new_c = st.text_input("新增客戶姓名")
    if st.button("➕ 建立") and new_c:
        if new_c not in st.session_state.client_battles:
            st.session_state.client_battles[new_c] = []
            st.rerun()
    st.divider()
    all_c = list(st.session_state.client_battles.keys())
    cur_c = st.selectbox("🎯 監控對象", all_c if all_c else ["尚未建立客戶"])

# --- 主戰場佈局 ---
st.title(f"🛡️ AI 經理人 6.7：[{cur_c}] 旗艦作戰室")
st.caption(f"系統核心：每分鐘同步 / 台灣視角中國情報 / K棒字形模擬器 | {datetime.now().strftime('%H:%M:%S')}")

col_l, col_r = st.columns([1.8, 1.2])

with col_l:
    st.subheader("🔥 深度技術分析：15 檔起漲點戰略")
    scan_list = [
        {"id": "2402.TW", "name": "毅嘉", "detail": "【技術分析】股價放量站穩 42.5 元成本區，MACD 零軸上方二次金叉。外資籌碼高度安定，適合波段持有。"},
        {"id": "6531.TW", "name": "愛普*", "detail": "【量價分析】月線、日線 MACD 同步發散。3D 堆疊封裝題材發酵，目前處於起漲第一點，目標看向 550 元。"},
        {"id": "3035.TW", "name": "智原", "detail": "【籌碼深度】法人連續買超 5 日。股價回踩 5 日線後呈紅 K 吞噬，慣性由空轉多，IP 權利金增長明確。"},
        {"id": "5269.TW", "name": "祥碩", "detail": "【趨勢研判】USB4 指標。帶量突破年線並完成回測，中期趨勢向上，今日 K 棒強度為關鍵追價點。"},
        {"id": "3227.TW", "name": "原相", "detail": "【波段監控】CIS 需求爆發。60 分 K 呈現對稱三角形突破，均線多頭排列，股價具備翻倍潛力。"},
        {"id": "3034.TW", "name": "聯詠", "detail": "【價值分析】超高配息護體。目前本益比僅 12 倍，技術面 MACD 綠柱萎縮即將翻紅，安全性高。"},
        {"id": "2603.TW", "name": "長榮", "detail": "【國際局勢】運價漲價紅利。股價在大量區頂端橫盤，今日若能站穩開盤價，將啟動第二波段攻擊。"},
        {"id": "2317.TW", "name": "鴻海", "detail": "【核心佈局】GB200 唯一領航者。220 元構築強大防線，AI 伺服器貢獻度超標，法人重新定價中。"},
        {"id": "6438.TW", "name": "迅得", "detail": "【半導體設備】CoWoS 產能擴張。股價高檔鈍化，KD 指標持續 80 以上，主力鎖籌意願強烈。"},
        {"id": "3661.TW", "name": "世芯-KY", "detail": "【轉機分析】非理性下殺後出現底背離。外資回補力道加劇，目標先看季線回補缺口。"},
        {"id": "2330.TW", "name": "台積電", "detail": "【國家戰略】全球 AI 核心。目前處於高檔震盪洗盤，MACD 雖然微幅收斂，但長線多頭結構未損。"},
        {"id": "2454.TW", "name": "聯發科", "detail": "【邊緣AI】處理器出貨超預期。回踩均線後獲支撐，MACD 持續翻紅第 3 天，動能依然充沛。"},
        {"id": "6271.TW", "name": "同欣電", "detail": "【低軌衛星】車用元件回溫。股價完成三個月的大底，今日放量突破頸線，正式啟動主升段。"},
        {"id": "3008.TW", "name": "大立光", "detail": "【光學龍頭】技術面三底架構。底背離訊號極其明顯，今日 K 棒轉強，是低位階佈局首選。"},
        {"id": "2308.TW", "name": "台達電", "detail": "【電力革命】能源管理訂單滿載。季線支撐力道極強，法人籌碼相對安定，逢拉回皆買點。"}
    ]

    for idx, s in enumerate(scan_list):
        p, k_s, k_c = get_stock_data(s['id'])
        with st.expander(f"📊 {s['name']} ({s['id']}) | 現價: {p} | 態勢: {k_s}"):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"**即時 K 棒：** <span class='{k_c}' style='font-size:24px;'>{k_s}</span>", unsafe_allow_html=True)
                st.write(f"**深度戰略：** {s['detail']}")
                st.write(f"**指標預警：** {detect_macd_divergence(s['id'])}")
            with c2:
                if st.button("執行買入", key=f"btn_{s['id']}_{idx}"):
                    if cur_c != "尚未建立客戶" and p > 0:
                        st.session_state.client_battles[cur_c].append({"id":s['id'], "name":s['name'], "buy_p":p})
                        st.rerun()

with col_r:
    st.subheader(f"💼 {cur_c} 持股戰況")
    if cur_c in st.session_state.client_battles and st.session_state.client_battles[cur_c]:
        p_list = []
        total_pnl = 0
        for itm in st.session_state.client_battles[cur_c]:
            cp, ks, kc = get_stock_data(itm['id'])
            pct = (cp / itm['buy_p'] - 1) * 100 if itm['buy_p'] > 0 else 0
            total_pnl += (cp - itm['buy_p'])
            div = detect_macd_divergence(itm['id'])
            advice = "✅ 安心持有"
            if "頂背離" in div or pct > 12: advice = "🚨 建議獲利"
            elif pct < -5: advice = "🛑 止損賣出"
            p_list.append({"標的":itm['name'], "價":cp, "K":ks, "損益%":f"{pct:+.2f}%", "戰略":advice})
        st.table(pd.DataFrame(p_list))
        st.metric("累積淨損益 (TWD)", f"{total_pnl:+.2f}")
        if st.button("全數結算"): st.session_state.client_battles[cur_c] = []; st.rerun()
    else: st.info("尚無部位")

# --- 情報中心：24H 高密度/可靠來源 ---
st.divider()
st.header("🌎 全球 24H 戰略情報中樞 (高可靠來源)")

def fetch_intel(query, region_name):
    ssl._create_default_https_context = ssl._create_unverified_context
    # 中國新聞特別過濾，排除官方媒體
    if region_name == "🇨🇳 中國 (台媒視角)":
        query += " -新華網 -人民網 -環球時報"
    u = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}+when:24h&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    return feedparser.parse(u).entries[:15]

regions = [
    ("🇺🇸 美國財經", "USA+Federal+Reserve+Economy+Nasdaq+Nvidia"),
    ("🇪🇺 歐洲局勢", "Europe+Economy+Ukraine+Energy+Policy"),
    ("🇯🇵 亞洲科技", "Japan+Taiwan+Semiconductor+TSMC+Tech"),
    ("🇨🇳 中國 (台媒視角)", "中國+經濟+財經+兩岸+政策")
]

tabs = st.tabs([r[0] for r in regions])
for tab, (name, q) in zip(tabs, regions):
    with tab:
        st.markdown(f"<div class='region-banner'>{name} 24H 重大情報 (共 15 則)</div>", unsafe_allow_html=True)
        items = fetch_intel(q, name)
        if not items: st.warning("暫無重大突發新聞")
        for n in items:
            st.markdown(f"<div class='news-card'>🕒 {n.published[5:16]} | <a href='{n.link}'>{n.title}</a></div>", unsafe_allow_html=True)

# --- 視覺輔助 ---
st.divider()
c1, c2 = st.columns(2)
with c1:
    st.caption("🛑 指令：破位止損（價格跌破關鍵支撐）")
    
with c2:
    st.caption("🚨 指令：頂背離偵測（價格新高但動能衰退）")
    
