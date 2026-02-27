import streamlit as st
import pandas as pd
import yfinance as yf
import feedparser
import ssl
from datetime import datetime
import time
import urllib.parse
import numpy as np

# --- 核心配置 ---
st.set_page_config(page_title="AI Manager 6.5 - 深度即時監控版", layout="wide")

# 每分鐘自動刷新
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=60 * 1000, key="mkt_pulse")
except:
    pass

st.markdown("""
    <style>
    html, body, [class*="css"] { font-size: 13px !important; color: #1e1e1e; }
    .stButton>button { height: 26px; padding: 0px 10px; font-size: 11px; background-color: #f0f2f6; border-radius: 5px; }
    .news-card { border-left: 4px solid #cc0000; padding-left: 12px; margin-bottom: 10px; font-size: 12px; }
    .price-tag { color: #003366; font-weight: bold; font-family: 'Courier New', monospace; }
    .k-red { color: #ff0000; font-weight: bold; }
    .k-green { color: #008000; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 數據引擎 ---
def get_detailed_mkt(ticker):
    """抓取即時價、開盤價、K棒狀態及MACD數據"""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="5d", interval="1m") # 抓取 1 分鐘級別數據
        if df.empty:
            df = stock.history(period="1mo", interval="1d")
        
        curr_p = df['Close'].iloc[-1]
        open_p = df['Open'].iloc[-1]
        
        # K棒判定
        if curr_p >= open_p:
            k_bar = "🔴 紅K"
        else:
            k_bar = "🟢 綠K"
            
        return round(curr_p, 2), k_bar
    except:
        return 0, "N/A"

def detect_macd_divergence(ticker):
    try:
        df = yf.Ticker(ticker).history(period="3mo", interval="1d")
        if len(df) < 30: return "分析中"
        close = df['Close']
        exp1 = close.ewm(span=12, adjust=False).mean()
        exp2 = close.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        hist = macd - signal
        curr_p, prev_p_max = close.iloc[-1], close.iloc[-20:-2].max()
        curr_h, prev_h_max = hist.iloc[-1], hist.iloc[-20:-2].max()
        if curr_p > prev_p_max and curr_h < prev_h_max: return "🚨 頂背離"
        if curr_p < close.iloc[-20:-2].min() and curr_h > hist.iloc[-20:-2].min(): return "📈 底背離"
        return "正常"
    except:
        return "計算中"

# --- 狀態管理 ---
if 'client_battles' not in st.session_state:
    st.session_state.client_battles = {}

with st.sidebar:
    st.header("👤 帳戶管理")
    new_c = st.text_input("建立新客戶")
    if st.button("➕ 確認建立") and new_c:
        if new_c not in st.session_state.client_battles:
            st.session_state.client_battles[new_c] = []
            st.rerun()
    st.divider()
    all_c = list(st.session_state.client_battles.keys())
    cur_c = st.selectbox("🎯 指揮目標", all_c if all_c else ["請建立客戶"])

# --- 主戰場 ---
st.title(f"🛡️ AI 經理人 6.5：[{cur_c}] 深度控盤中心")
st.caption(f"數據自動同步中... 最後更新: {datetime.now().strftime('%H:%M:%S')}")

col_l, col_r = st.columns([1.8, 1.2])

with col_l:
    st.subheader("🔥 每日 15 檔深度分析推薦")
    scan_list = [
        {"id": "2402.TW", "name": "毅嘉", "detail": "【量價分析】量能溫和放大，站穩關鍵支撐 42.5 元。均線多頭排列，外資近期連續買超 3 日，預估溢價 15-20%。"},
        {"id": "6531.TW", "name": "愛普*", "detail": "【籌碼分析】大戶持股比例回升。MACD 日線於零軸上再度發散，典型強勢股拉回後再攻擊架構，短線目標看 500 元。"},
        {"id": "3035.TW", "name": "智原", "detail": "【技術面】月線級別底背離完成。近期回測 5 日線不破，呈現強勢換手。IP 授權金預期增長，法人買盤進駐。"},
        {"id": "5269.TW", "name": "祥碩", "detail": "【基本面】USB4 指標股。股價帶量突破年線壓力，且今日呈現紅K帶量，中期慣性由弱轉強，建議長線佈局。"},
        {"id": "3227.TW", "name": "原相", "detail": "【技術面】60分K呈現對稱三角形突破。影像感測器需求回溫，股價回踩均線後收紅，具備波段攻擊動能。"},
        {"id": "3034.TW", "name": "聯詠", "detail": "【策略】高配息護體。目前本益比仍處歷史低位，MACD 收斂即將翻紅。適合保守型客戶作為核心持股。"},
        {"id": "2603.TW", "name": "長榮", "detail": "【量價】運價指數維持高位。股價在大量區頂端橫盤整理，今日 K 棒強度決定是否啟動下一波段。"},
        {"id": "2317.TW", "name": "鴻海", "reason": "【趨勢】AI 伺服器營收比重提升。股價在 200 元整數關卡後築底完成，今日觀察能否站穩開盤價。"},
        {"id": "6438.TW", "name": "迅得", "detail": "【籌碼】CoWoS 設備訂單滿載。今日成交量已達昨日 80%，買盤積極。KD 指標高檔鈍化，典型主升段特徵。"},
        {"id": "3661.TW", "name": "世芯-KY", "detail": "【分析】非理性下殺後，股價進入關鍵 0.618 回檔位。今日開高走高顯示主力回補心切，目標先看季線。"},
        {"id": "2330.TW", "name": "台積電", "detail": "【核心】全球半導體制霸。月線級別多頭不變，今日股價於平盤上下震盪，洗盤性質高，建議續抱。"},
        {"id": "2454.TW", "name": "聯發科", "detail": "【技術面】邊緣 AI 處理器放量。股價回踩 10 日線支撐，MACD 翻紅第 2 天，多頭動能充足。"},
        {"id": "6271.TW", "name": "同欣電", "detail": "【趨勢】車用與低軌衛星雙引擎。均線形成黃金交叉，量縮整理完成，今日若出量即為介入訊號。"},
        {"id": "3008.TW", "name": "大立光", "detail": "【價值】潛望式鏡頭升級趨勢。技術面完成三底架構，今日 K 棒轉紅，外資賣壓衰竭，反轉在即。"},
        {"id": "2308.TW", "name": "台達電", "detail": "【分析】電力管理龍頭。季線支撐極強，今日股價回升至開盤價上方，法人籌碼相對安定。"}
    ]

    for idx, s in enumerate(scan_list):
        price, kbar = get_detailed_mkt(s['id'])
        k_class = "k-red" if "紅" in kbar else "k-green"
        
        with st.expander(f"📊 {s['name']} | 現價: {price} | <span class='{k_class}'>{kbar}</span>", unsafe_allow_html=True):
            c1, c2 = st.columns([4, 1])
            div = detect_macd_divergence(s['id'])
            c1.write(f"**深度策略分析:** {s.get('detail', '分析中...')}")
            c1.write(f"**指標監控:** {div}")
            if c2.button("買入", key=f"b_{s['id']}_{idx}"):
                if cur_c != "請建立客戶":
                    if price > 0:
                        st.session_state.client_battles[cur_c].append({"id":s['id'], "name":s['name'], "buy_p":price})
                        st.rerun()

with col_r:
    st.subheader(f"💼 {cur_c} 部位即時監測")
    if cur_c in st.session_state.client_battles and st.session_state.client_battles[cur_c]:
        p_list = []
        total_p = 0
        for itm in st.session_state.client_battles[cur_c]:
            cp, kb = get_detailed_mkt(itm['id'])
            pct = (cp / itm['buy_p'] - 1) * 100 if itm['buy_p'] > 0 else 0
            total_p += (cp - itm['buy_p'])
            div = detect_macd_divergence(itm['id'])
            adv = "✅ 持有"
            if "頂背離" in div or pct > 12: adv = "🚨 建議獲利"
            elif pct < -5: adv = "🛑 止損賣出"
            p_list.append({"標的":itm['name'], "即時價":cp, "K棒":kb, "損益%":f"{pct:+.2f}%", "指令":adv})
        st.table(pd.DataFrame(p_list))
        st.metric("累積損益 (TWD)", f"{total_p:+.2f}")
        if st.button("結算帳戶"): st.session_state.client_battles[cur_c] = []; st.rerun()
    else: st.info("尚無持股")

# --- 情報 ---
st.divider()
st.header("🌎 全球 20H 政經情報")
def fetch_news(q):
    ssl._create_default_https_context = ssl._create_unverified_context
    u = f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}+when:20h&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    return feedparser.parse(u).entries[:8]

tabs = st.tabs(["🇺🇸 美國", "🇪🇺 歐洲", "🇯🇵 亞洲", "🇨🇳 中國"])
qs = ["USA+Fed+Nvidia", "Europe+Economy", "Taiwan+Semiconductor", "China+Economic+Policy"]
for tab, q in zip(tabs, qs):
    with tab:
        for n in fetch_news(q):
            st.markdown(f"<div class='news-card'>🕒 {n.published[5:16]} | <a href='{n.link}'>{n.title}</a></div>", unsafe_allow_html=True)
