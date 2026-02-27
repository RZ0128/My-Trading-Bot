import streamlit as st
import pandas as pd
import yfinance as yf
import feedparser
import ssl
from datetime import datetime
import time
import urllib.parse

# --- 核心配置 ---
st.set_page_config(page_title="AI Manager 6.8 - Command Center", layout="wide")

try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=60 * 1000, key="global_pulse")
except:
    pass

st.markdown("""
    <style>
    html, body, [class*="css"] { font-size: 13px !important; color: #1e1e1e; }
    .stButton>button { height: 26px; padding: 0px 10px; font-size: 11px; background-color: #f0f2f6; border-radius: 5px; }
    .news-card { border-left: 4px solid #cc0000; padding-left: 12px; margin-bottom: 8px; font-size: 12px; line-height: 1.4; border-bottom: 1px solid #eee; padding-bottom: 5px; }
    .k-red { color: #ff0000; font-weight: bold; font-size: 22px; line-height: 1; }
    .k-green { color: #008000; font-weight: bold; font-size: 22px; line-height: 1; }
    .k-neutral { color: #555; font-weight: bold; font-size: 22px; line-height: 1; }
    .region-banner { background-color: #001f3f; color: white; padding: 6px; border-radius: 4px; font-weight: bold; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 強化數據引擎 ---
def get_k_symbol(ticker):
    """模擬長官提供的 K 線形態圖 (圖一)"""
    tickers_to_try = [ticker, ticker.replace(".TW", ".TWO")] if ".TW" in ticker else [ticker]
    for t in tickers_to_try:
        try:
            stock = yf.Ticker(t)
            df = stock.history(period="2d", interval="1m")
            if df.empty: df = stock.history(period="5d", interval="1d")
            if not df.empty:
                curr = df['Close'].iloc[-1]
                open_p = df['Open'].iloc[-1]
                high_p = df['High'].iloc[-1]
                low_p = df['Low'].iloc[-1]
                diff = curr - open_p
                body_ratio = abs(diff) / (high_p - low_p) if (high_p - low_p) != 0 else 0
                
                # 形態判定邏輯
                if body_ratio < 0.1: # 十字星形態
                    return round(curr, 2), "╁", "k-neutral", "十字線 (多空拉鋸)"
                elif diff > 0: # 紅K系列
                    if body_ratio > 0.7: return round(curr, 2), "█", "k-red", "長紅K (大陽線)"
                    return round(curr, 2), "▲", "k-red", "紅K棒"
                else: # 綠K系列
                    if body_ratio > 0.7: return round(curr, 2), "█", "k-green", "長黑K (大陰線)"
                    return round(curr, 2), "▼", "k-green", "黑K棒"
        except: continue
    return 0.0, "？", "k-neutral", "數據擷取中"

def detect_macd_divergence(ticker):
    try:
        df = yf.Ticker(ticker).history(period="3mo", interval="1d")
        if len(df) < 30: return "分析中..."
        close = df['Close']
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        sig = macd.ewm(span=9, adjust=False).mean()
        hist = macd - sig
        if close.iloc[-1] > close.iloc[-20:-2].max() and hist.iloc[-1] < hist.iloc[-20:-2].max():
            return "🚨 頂背離 (警告)"
        if close.iloc[-1] < close.iloc[-20:-2].min() and hist.iloc[-1] > hist.iloc[-20:-2].min():
            return "📈 底背離 (築底)"
        return "動能正常"
    except: return "計算中"

# --- 帳戶管理 ---
if 'client_battles' not in st.session_state:
    st.session_state.client_battles = {}

with st.sidebar:
    st.header("👤 帳戶控制台")
    new_c = st.text_input("新增客戶姓名")
    if st.button("➕ 建立") and new_c:
        st.session_state.client_battles[new_c] = []
        st.rerun()
    st.divider()
    all_c = list(st.session_state.client_battles.keys())
    cur_c = st.selectbox("🎯 監控對象", all_c if all_c else ["尚未建立客戶"])

# --- 主畫面 ---
st.title(f"🛡️ AI 經理人 6.8：[{cur_c}] 專業監控版")
st.caption(f"視覺形態校準：參考長官 K 線圖 | 全球 24H 情報全開 | {datetime.now().strftime('%H:%M:%S')}")

col_l, col_r = st.columns([1.8, 1.2])

with col_l:
    st.subheader("🔥 深度技術分析：15 檔起漲戰略")
    scan_list = [
        {"id": "2402.TW", "name": "毅嘉", "detail": "站穩 42.5 元支撐。MACD 二次金叉，外資籌碼高度安定。"},
        {"id": "6531.TW", "name": "愛普*", "detail": "月日 MACD 共振。3D 封裝題材進入主升段，目標 550 元。"},
        {"id": "3035.TW", "name": "智原", "detail": "法人連買 5 日。紅 K 吞噬壓力區，IP 權利金增長明確。"},
        {"id": "5269.TW", "name": "祥碩", "detail": "USB4 指標。帶量突破年線，今日 K 棒強度為關鍵追價點。"},
        {"id": "3227.TW", "name": "原相", "detail": "CIS 需求爆發。三角形突破，均線多頭排列，具翻倍潛力。"},
        {"id": "3034.TW", "name": "聯詠", "detail": "高配息護體。本益比僅 12 倍，技術面綠柱萎縮，安全性極高。"},
        {"id": "2603.TW", "name": "長榮", "detail": "運價漲價紅利。股價橫盤蓄勢，今日 K 棒決定突破方向。"},
        {"id": "2317.TW", "name": "鴻海", "detail": "GB200 唯一領航。220 元構築防線，AI 伺服器貢獻度大幅提升。"},
        {"id": "6438.TW", "name": "迅得", "detail": "CoWoS 產能擴張。股價高檔鈍化，主力鎖籌意願強烈。"},
        {"id": "3661.TW", "name": "世芯-KY", "detail": "底背離訊號。外資回補力道加劇，目標回補上方跳空缺口。"},
        {"id": "2330.TW", "name": "台積電", "detail": "全球 AI 核心。高檔震盪洗盤，長線多頭結構未損，績優首選。"},
        {"id": "2454.TW", "name": "聯發科", "detail": "邊緣 AI 放量。回踩均線支撐，MACD 持續翻紅，動能充沛。"},
        {"id": "6271.TW", "name": "同欣電", "detail": "低軌衛星雙引擎。完成三個月大底，放量突破頸線。"},
        {"id": "3008.TW", "name": "大立光", "detail": "三底架構完成。底背離明顯，外資賣壓衰竭，反轉在即。"},
        {"id": "2308.TW", "name": "台達電", "detail": "電力管理龍頭。季線強支撐，法人籌碼安定，逢回皆買點。"}
    ]

    for idx, s in enumerate(scan_list):
        p, k_s, k_c, k_n = get_k_symbol(s['id'])
        with st.expander(f"📊 {s['name']} | 現價: {p} | 形態: {k_s}"):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"**實戰形態：** <span class='{k_c}'>{k_s}</span> <b>{k_n}</b>", unsafe_allow_html=True)
                st.write(f"**深度戰略：** {s['detail']}")
                st.write(f"**MACD 監控：** {detect_macd_divergence(s['id'])}")
            with c2:
                if st.button("執行買入", key=f"btn_{s['id']}_{idx}"):
                    if cur_c != "尚未建立客戶" and p > 0:
                        st.session_state.client_battles[cur_c].append({"id":s['id'], "name":s['name'], "buy_p":p})
                        st.rerun()

with col_r:
    st.subheader(f"💼 {cur_c} 實戰組合")
    if cur_c in st.session_state.client_battles and st.session_state.client_battles[cur_c]:
        items = []
        total_pnl = 0
        for itm in st.session_state.client_battles[cur_c]:
            cp, ks, kc, kn = get_k_symbol(itm['id'])
            pct = (cp / itm['buy_p'] - 1) * 100 if itm['buy_p'] > 0 else 0
            total_pnl += (cp - itm['buy_p'])
            items.append({"標的":itm['name'], "價":cp, "K":ks, "損益%":f"{pct:+.2f}%"})
        st.table(pd.DataFrame(items))
        st.metric("累積損益 (TWD)", f"{total_pnl:+.2f}")
        if st.button("清空帳戶"): st.session_state.client_battles[cur_c] = []; st.rerun()
    else: st.info("目前無持股")

# --- 終極情報中樞：優化 RSS 抓取 ---
st.divider()
st.header("🌎 全球 24H 戰略情報中樞 (深度優化版)")

def fetch_safe_intel(query):
    ssl._create_default_https_context = ssl._create_unverified_context
    # 移除 restrict 以防 0 結果
    u = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    feed = feedparser.parse(u)
    return feed.entries[:15]

# 新聞區域定義
intel_map = {
    "🇺🇸 美國 (川普/馬斯克/華爾街)": "Trump+Elon+Musk+Wall+Street+Federal+Reserve",
    "🇪🇺 歐洲 (政經/衝突)": "Europe+Economy+Ukraine+NATO",
    "🇯🇵 亞洲 (半導體/地緣)": "Taiwan+Semiconductor+TSMC+Japan+Tech",
    "🇨🇳 中國 (台媒視角)": "中國+經濟+財經+政策 -新華網 -人民網"
}

tabs = st.tabs(list(intel_map.keys()))
for tab, (region, query) in zip(tabs, intel_map.items()):
    with tab:
        st.markdown(f"<div class='region-banner'>{region} 最新 15 則情報</div>", unsafe_allow_html=True)
        news_items = fetch_safe_intel(query)
        if not news_items:
            st.warning("情報源暫時無回應，請手動刷新。")
        else:
            for n in news_items:
                st.markdown(f"<div class='news-card'>🕒 {n.published[5:16]} | <a href='{n.link}' target='_blank'>{n.title}</a></div>", unsafe_allow_html=True)

# 視覺輔助
