import streamlit as st
import pandas as pd
import yfinance as yf
import feedparser
import ssl
from datetime import datetime, timedelta
import urllib.parse

# --- 核心配置 ---
st.set_page_config(page_title="AI Manager 7.0 - Command Center", layout="wide")

# 每一分鐘強制刷新畫面
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=60 * 1000, key="v7_pulse")
except:
    pass

st.markdown("""
    <style>
    html, body, [class*="css"] { font-size: 13px !important; color: #1e1e1e; }
    .stButton>button { height: 26px; padding: 0px 10px; font-size: 11px; background-color: #f0f2f6; border-radius: 5px; }
    .news-card { border-left: 4px solid #cc0000; padding-left: 12px; margin-bottom: 8px; font-size: 12px; border-bottom: 1px solid #eee; padding-bottom: 5px; }
    .price-up { color: #ff0000; font-weight: bold; }
    .price-down { color: #008000; font-weight: bold; }
    .price-even { color: #666; font-weight: bold; }
    .region-banner { background-color: #001f3f; color: white; padding: 8px; border-radius: 4px; font-weight: bold; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 漲跌點數引擎 ---
def get_stock_perf(ticker):
    """獲取現價與今日漲跌點數"""
    # 針對原相(3227)等櫃買標的自動校正
    search_list = [ticker, ticker.replace(".TW", ".TWO")] if ".TW" in ticker else [ticker]
    for t in search_list:
        try:
            stock = yf.Ticker(t)
            df = stock.history(period="2d")
            if len(df) >= 2:
                curr_p = df['Close'].iloc[-1]
                prev_p = df['Close'].iloc[-2]
                diff = curr_p - prev_p
                
                if diff > 0:
                    return round(curr_p, 1), f"+{round(diff, 1)}", "price-up"
                elif diff < 0:
                    return round(curr_p, 1), f"{round(diff, 1)}", "price-down"
                else:
                    return round(curr_p, 1), "0.0", "price-even"
        except:
            continue
    return 0.0, "---", "price-even"

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
st.title(f"🛡️ AI 經理人 7.0：[{cur_c}] 即時戰報")
st.caption(f"數據更新：漲跌點數即時同步 (紅漲綠跌) | 美歐情報深度擴張 | {datetime.now().strftime('%H:%M:%S')}")

col_l, col_r = st.columns([1.8, 1.2])

with col_l:
    st.subheader("🔥 每日 15 檔技術分析 (深度策略版)")
    scan_list = [
        {"id": "2402.TW", "name": "毅嘉", "detail": "站穩 42.5 元支撐。MACD 二次金叉，外資籌碼高度安定。"},
        {"id": "6531.TW", "name": "愛普*", "detail": "月日 MACD 共振。3D 封裝題材進入主升段，目標 550 元。"},
        {"id": "3035.TW", "name": "智原", "detail": "法人連買 5 日。紅 K 吞噬壓力區，IP 權利金增長明確。"},
        {"id": "5269.TW", "name": "祥碩", "detail": "USB4 指標。帶量突破年線，中期趨勢向上，追價力道強。"},
        {"id": "3227.TW", "name": "原相", "detail": "CIS 需求爆發。三角形突破，均線多頭排列，具翻倍潛力。"},
        {"id": "3034.TW", "name": "聯詠", "detail": "高配息護體。本益比僅 12 倍，技術面綠柱萎縮，安全性高。"},
        {"id": "2603.TW", "name": "長榮", "detail": "運價漲價紅利。股價橫盤蓄勢，回調皆是買點。"},
        {"id": "2317.TW", "name": "鴻海", "detail": "GB200 唯一領航。220 元構築防線，AI 伺服器貢獻度提升。"},
        {"id": "6438.TW", "name": "迅得", "detail": "CoWoS 產能擴張。股價高檔鈍化，主力鎖籌意願強烈。"},
        {"id": "3661.TW", "name": "世芯-KY", "detail": "底背離訊號。外資回補力道加劇，目標回補上方缺口。"},
        {"id": "2330.TW", "name": "台積電", "detail": "全球 AI 核心。高檔震盪洗盤，長線多頭結構未損。"},
        {"id": "2454.TW", "name": "聯發科", "detail": "邊緣 AI 放量。回踩均線支撐，MACD 持續翻紅。"},
        {"id": "6271.TW", "name": "同欣電", "detail": "低軌衛星雙引擎。完成大底，放量突破頸線啟動主升段。"},
        {"id": "3008.TW", "name": "大立光", "detail": "三底架構。底背離明顯，外資賣壓衰竭，反轉在即。"},
        {"id": "2308.TW", "name": "台達電", "detail": "電力管理龍頭。季線強支撐，法人籌碼相對安定。"}
    ]

    for idx, s in enumerate(scan_list):
        price, diff_str, color_class = get_stock_perf(s['id'])
        # 標題直接顯示漲跌點數
        header_text = f"📊 {s['name']} | 現價: {price} | 漲跌: {diff_str}"
        with st.expander(header_text):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"**今日表現：** <span class='{color_class}' style='font-size:20px;'>{diff_str}</span>", unsafe_allow_html=True)
                st.write(f"**戰略分析：** {s['detail']}")
            with c2:
                if st.button("執行買入", key=f"btn_{s['id']}_{idx}"):
                    if cur_c != "尚未建立客戶" and price > 0:
                        st.session_state.client_battles[cur_c].append({"id":s['id'], "name":s['name'], "buy_p":price})
                        st.rerun()

with col_r:
    st.subheader(f"💼 {cur_c} 實戰持股")
    if cur_c in st.session_state.client_battles and st.session_state.client_battles[cur_c]:
        items = []
        for itm in st.session_state.client_battles[cur_c]:
            cp, ds, cc = get_stock_perf(itm['id'])
            pct = (cp / itm['buy_p'] - 1) * 100 if itm['buy_p'] > 0 else 0
            items.append({"標的":itm['name'], "現價":cp, "今日漲跌":ds, "損益%":f"{pct:+.2f}%"})
        st.table(pd.DataFrame(items))
        if st.button("全數清空"): st.session_state.client_battles[cur_c] = []; st.rerun()
    else: st.info("尚無持股")

# --- 終極情報引擎：針對美國/歐洲深度優化 ---
st.divider()
st.header("🌎 全球 24H 戰略情報中樞 (美國/歐洲深度強化版)")

def fetch_massive_intel(query_list):
    ssl._create_default_https_context = ssl._create_unverified_context
    all_entries = []
    for q in query_list:
        u = f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        feed = feedparser.parse(u)
        all_entries.extend(feed.entries)
    # 去重並取前 18 則確保量足
    unique_news = {n.link: n for n in all_entries}.values()
    return sorted(list(unique_news), key=lambda x: x.published, reverse=True)[:18]

# 新聞區域定義 - 增加關鍵字聯集
intel_map = {
    "🇺🇸 美國戰略 (川普/馬斯克/華爾街)": [
        "Trump+policy+breaking+news", 
        "Elon+Musk+Tesla+SpaceX", 
        "Wall+Street+Federal+Reserve+Interest",
        "Nvidia+AI+US+Stock"
    ],
    "🇪🇺 歐洲動態 (經濟/地緣/能源)": [
        "Europe+Economy+ECB", 
        "Ukraine+Russia+war+update", 
        "Germany+France+politics",
        "Europe+Energy+Gas"
    ],
    "🇯🇵 亞洲科技 (台積電/半導體)": ["Taiwan+Semiconductor+TSMC", "Japan+Tech+Nikkei"],
    "🇨🇳 中國觀點 (台灣媒體視角)": ["中國+經濟+財經+政策 -新華網 -人民網"]
}

tabs = st.tabs(list(intel_map.keys()))
for tab, (region, q_list) in zip(tabs, intel_map.items()):
    with tab:
        st.markdown(f"<div class='region-banner'>{region} (24H 深度搜羅)</div>", unsafe_allow_html=True)
        news_items = fetch_massive_intel(q_list)
        if not news_items:
            st.warning("搜尋結果受限，請點擊上方標籤重試。")
        else:
            for n in news_items:
                st.markdown(f"<div class='news-card'>🕒 {n.published[5:16]} | <a href='{n.link}' target='_blank'>{n.title}</a></div>", unsafe_allow_html=True)
