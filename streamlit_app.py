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
st.set_page_config(page_title="AI Manager 6.6 - Ultimate", layout="wide")

# 自動刷新 (60秒)
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
    .k-red { color: #ff0000; font-weight: bold; font-size: 16px; }
    .k-green { color: #008000; font-weight: bold; font-size: 16px; }
    .price-large { font-size: 18px; font-weight: bold; color: #003366; }
    </style>
    """, unsafe_allow_html=True)

# --- 數據引擎 ---
def get_detailed_mkt(ticker):
    """抓取股價與K棒狀態，增加容錯機制"""
    try:
        stock = yf.Ticker(ticker)
        # 優先抓取今日即時數據
        df = stock.history(period="1d", interval="1m")
        if df.empty or len(df) < 1:
            df = stock.history(period="5d", interval="1d")
        
        curr_p = float(df['Close'].iloc[-1])
        open_p = float(df['Open'].iloc[-1])
        
        k_status = "🔴 紅K (多頭推升)" if curr_p >= open_p else "🟢 綠K (空頭整理)"
        k_class = "k-red" if curr_p >= open_p else "k-green"
            
        return round(curr_p, 2), k_status, k_class
    except:
        return 0.0, "數據讀取中", "k-green"

def detect_macd_divergence(ticker):
    """偵測 MACD 背離邏輯"""
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
        if curr_p > prev_p_max and curr_h < prev_h_max: return "🚨 頂背離 (預警)"
        if curr_p < close.iloc[-20:-2].min() and curr_h > hist.iloc[-20:-2].min(): return "📈 底背離 (築底)"
        return "指標正常"
    except:
        return "計算中"

# --- 狀態管理 ---
if 'client_battles' not in st.session_state:
    st.session_state.client_battles = {}

with st.sidebar:
    st.header("👤 指揮部")
    new_c = st.text_input("新增客戶姓名")
    if st.button("➕ 建立帳戶") and new_c:
        if new_c not in st.session_state.client_battles:
            st.session_state.client_battles[new_c] = []
            st.rerun()
    st.divider()
    all_c = list(st.session_state.client_battles.keys())
    cur_c = st.selectbox("🎯 選取目標", all_c if all_c else ["請先建立客戶"])

# --- 主畫面佈局 ---
st.title(f"🛡️ AI 經理人 6.6：[{cur_c}] 戰略中心")
st.caption(f"即時數據更新中... 最後同步: {datetime.now().strftime('%H:%M:%S')}")

col_l, col_r = st.columns([1.8, 1.2])

with col_l:
    st.subheader("🔥 每日 15 檔起漲深度分析")
    scan_list = [
        {"id": "2402.TW", "name": "毅嘉", "detail": "突破大量區支撐 42.5 元。均線多頭排列，外資連買，預估溢價 15%。"},
        {"id": "6531.TW", "name": "愛普*", "detail": "MACD 零軸上再度發散。強勢股拉回後攻擊，短線目標 500 元。"},
        {"id": "3035.TW", "name": "智原", "detail": "底背離完成。回測 5 日線不破，IP 授權金預期增長，法人買盤進駐。"},
        {"id": "5269.TW", "name": "祥碩", "detail": "USB4.0 領先者。帶量突破年線，中期慣性轉強，長線潛力巨大。"},
        {"id": "3227.TW", "name": "原相", "detail": "三角形突破。影像感測需求回溫，股價回踩均線後收紅，具攻擊動能。"},
        {"id": "3034.TW", "name": "聯詠", "detail": "高配息支撐。本益比歷史低位，適合穩健型佈局，MACD 即將翻紅。"},
        {"id": "2603.TW", "name": "長榮", "detail": "紅海局勢支撐運價。股價橫盤蓄勢，今日 K 棒強度決定突破方向。"},
        {"id": "2317.TW", "name": "鴻海", "detail": "GB200 量產期。200 元築底完成，AI 伺服器營收比重持續提升。"},
        {"id": "6438.TW", "name": "迅得", "detail": "CoWoS 設備需求噴發。買盤積極，KD 指標高檔發散，主升段架構。"},
        {"id": "3661.TW", "name": "世芯-KY", "detail": "非理性殺盤結束。主力低位回補，目標回補上方缺口，站穩季線。"},
        {"id": "2330.TW", "name": "台積電", "detail": "全球核心資產。多頭排列不變，洗盤整理中，具備強大抗跌性。"},
        {"id": "2454.TW", "name": "聯發科", "detail": "邊緣 AI 放量。回踩 10 日線支撐，MACD 持續翻紅，多頭動能充沛。"},
        {"id": "6271.TW", "name": "同欣電", "detail": "低軌衛星雙引擎。黃金交叉形成，量縮整理完畢，準備啟動。"},
        {"id": "3008.TW", "name": "大立光", "detail": "完成三底架構。底背離訊號明顯，外資賣壓衰竭，反轉在即。"},
        {"id": "2308.TW", "name": "台達電", "detail": "電力管理龍頭。季線強支撐，法人籌碼安定，回檔皆是買點。"}
    ]

    for idx, s in enumerate(scan_list):
        p, k_text, k_style = get_detailed_mkt(s['id'])
        with st.expander(f"📊 {s['id']} {s['name']} | 即時報價: {p}"):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"**當前態勢：** <span class='{k_style}'>{k_text}</span>", unsafe_allow_html=True)
                st.write(f"**技術分析：** {s['detail']}")
                st.write(f"**MACD監控：** {detect_macd_divergence(s['id'])}")
            with c2:
                if st.button("買入交易", key=f"btn_{s['id']}_{idx}"):
                    if cur_c != "請先建立客戶" and p > 0:
                        st.session_state.client_battles[cur_c].append({"id":s['id'], "name":s['name'], "buy_p":p})
                        st.rerun()

with col_r:
    st.subheader(f"💼 {cur_c} 實戰組合")
    if cur_c in st.session_state.client_battles and st.session_state.client_battles[cur_c]:
        p_list = []
        total_pnl = 0
        for itm in st.session_state.client_battles[cur_c]:
            cp, kb, ks = get_detailed_mkt(itm['id'])
            pct = (cp / itm['buy_p'] - 1) * 100 if itm['buy_p'] > 0 else 0
            total_pnl += (cp - itm['buy_p'])
            
            div = detect_macd_divergence(itm['id'])
            advice = "✅ 安心持有"
            if "頂背離" in div or pct > 12: advice = "🚨 建議獲利"
            elif pct < -5: advice = "🛑 止損賣出"
            
            p_list.append({
                "標的": itm['name'],
                "現價": cp,
                "K棒": kb[:3], # 僅顯示紅/綠K字樣
                "損益%": f"{pct:+.2f}%",
                "戰略": advice
            })
        st.table(pd.DataFrame(p_list))
        st.metric("總損益估值 (TWD)", f"{total_pnl:+.2f}")
        if st.button("全數結算"):
            st.session_state.client_battles[cur_c] = []
            st.rerun()
    else:
        st.info("目前無持股部位")

# --- 情報中心 ---
st.divider()
st.header("🌎 全球 20H 核心情報")
def fetch_news(q):
    ssl._create_default_https_context = ssl._create_unverified_context
    u = f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}+when:20h&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    return feedparser.parse(u).entries[:6]

t1, t2, t3, t4 = st.tabs(["🇺🇸 美國", "🇪🇺 歐洲", "🇯🇵 亞洲", "🇨🇳 中國"])
qs = ["USA+Fed+Nvidia", "Europe+Economy", "Taiwan+Semiconductor", "China+Macro+Policy"]
for tab, q in zip([t1, t2, t3, t4], qs):
    with tab:
        for n in fetch_news(q):
            st.markdown(f"<div class='news-card'>🕒 {n.published[5:16]} | <a href='{n.link}'>{n.title}</a></div>", unsafe_allow_html=True)
