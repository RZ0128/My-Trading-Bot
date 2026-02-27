import streamlit as st
import pandas as pd
import yfinance as yf
import feedparser
import ssl
from datetime import datetime
import urllib.parse
import gspread  # 新增：雲端同步庫
from google.oauth2.service_account import Credentials

# --- 核心配置 ---
st.set_page_config(page_title="AI Manager 9.0 - Cloud Sync", layout="wide")

# --- 雲端資料庫初始化 (解決手機同步問題) ---
def init_connection():
    # 請確保在 Streamlit 管理後台的 Secrets 填入憑證
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    # 打開名為 "AI_Manager_DB" 的試算表 (需手動建立)
    return client.open("AI_Manager_DB").sheet1

try:
    db = init_connection()
except Exception as e:
    st.error("⚠️ 雲端資料庫尚未連接。請先完成 Google Sheets 設定。")
    db = None

# --- 樣式設定 (與 8.5 完全相同) ---
st.markdown("""
    <style>
    html, body, [class*="css"] { font-size: 13px !important; color: #1e1e1e; }
    .stButton>button { height: 26px; padding: 0px 10px; font-size: 11px; border-radius: 5px; }
    .news-card { border-left: 4px solid #cc0000; padding-left: 12px; margin-bottom: 8px; font-size: 12px; border-bottom: 1px solid #eee; padding-bottom: 5px; }
    .price-up { color: #ff0000; font-weight: bold; }
    .price-down { color: #008000; font-weight: bold; }
    .profit-text { font-size: 14px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 數據引擎 (與 8.5 完全相同) ---
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

# --- 狀態管理與同步功能 ---
def get_cloud_data():
    if db:
        data = db.get_all_records()
        return pd.DataFrame(data)
    return pd.DataFrame()

with st.sidebar:
    st.header("👤 客戶帳戶管理")
    new_c = st.text_input("新增客戶姓名")
    if st.button("➕ 建立帳戶") and new_c:
        st.success(f"帳戶 {new_c} 已準備就緒")
    
    df_all = get_cloud_data()
    all_c = df_all['client'].unique().tolist() if not df_all.empty else []
    cur_c = st.selectbox("🎯 當前操作客戶", all_c if all_c else ["周靖傑"])

# --- 主畫面佈局 (15 檔推薦) ---
st.title(f"🛡️ AI 經理人 9.0：[{cur_c}] 雲端同步戰情室")

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
        header = f"📊 {s['id']} {s['name']} | 評分: {final_score} | 現價: {price}"
        with st.expander(header):
            st.markdown(f"**今日表現：** <span class='{color}'>{diff}</span>", unsafe_allow_html=True)
            st.write(f"**分析：** {s['detail']}")
            o_c1, o_c2, o_c3 = st.columns([1, 1, 1])
            unit = o_c1.radio("單位", ["張", "股"], key=f"u_{idx}")
            qty = o_c2.number_input("數量", min_value=1, value=1, key=f"q_{idx}")
            actual_shares = qty * 1000 if "張" in unit else qty
            if o_c3.button("雲端買入", key=f"b_{idx}"):
                if db:
                    db.append_row([cur_c, s['id'], s['name'], price, actual_shares])
                    st.rerun()

with col_r:
    st.subheader(f"💼 {cur_c} 投資組合 (雲端同步)")
    total_twd_pnl = 0
    df_client = get_cloud_data()
    if not df_client.empty:
        df_mine = df_client[df_client['client'] == cur_c]
        for i, row in df_mine.iterrows():
            cp, _, cc, _ = get_stock_perf(row['id'], 0)
            twd_pnl = (cp - row['buy_price']) * row['shares']
            total_twd_pnl += twd_pnl
            
            c1, c2, c3, c4 = st.columns([1.5, 1.5, 1.8, 0.8])
            c1.write(f"**{row['name']}**\n{row['shares']} 股")
            c2.write(f"現價: {cp}\n(成本: {row['buy_price']})")
            p_color = "red" if twd_pnl >= 0 else "green"
            c3.markdown(f"損益: <span style='color:{p_color}; font-weight:bold;'>NT$ {twd_pnl:,.0f}</span>", unsafe_allow_html=True)
            
            with c4:
                if st.button("🗑️", key=f"del_{i}"):
                    db.delete_rows(int(i) + 2) # +2 補償標題列
                    st.rerun()
            st.divider()
        st.markdown(f"### 總台幣損益: <span style='color:red;'>NT$ {total_twd_pnl:,.0f}</span>", unsafe_allow_html=True)

# --- 情報引擎 (維持 8.5 強度) ---
st.divider()
st.header("🌎 全球 24H 戰略情報")
# (fetch_massive_intel 與 8.5 版一致，此處省略以保持精簡，實際貼上時請包含 8.5 的 news 函數)
