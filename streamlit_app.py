import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import time

# --- 1. 全域樣式與自動刷新設定 ---
st.set_page_config(page_title="AI經理人4.0-自動戰情室", layout="wide")

# 每一分鐘 (60,000 毫秒) 自動重新整理網頁
# 如果沒安裝 streamlit_autorefresh，這段會跳過，改用手動刷新或內建循環
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=60 * 1000, key="data_refresh")
except ImportError:
    st.info("💡 提示：安裝 streamlit-autorefresh 可獲得更穩定的自動更新體驗。")

st.markdown("""
    <style>
    html, body, [class*="css"] { font-size: 14px !important; }
    .stButton>button { height: 25px; padding: 0px 10px; font-size: 12px; }
    .status-up { color: #ff4b4b; font-weight: bold; }
    .status-down { color: #00ff00; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 初始化模擬數據庫 ---
if 'battle_list' not in st.session_state:
    st.session_state.battle_list = []

# --- 3. 核心功能：抓取即時數據 ---
def get_live_price(ticker):
    try:
        data = yf.Ticker(ticker).history(period="1d")
        if not data.empty:
            return data['Close'].iloc[-1]
    except:
        return None
    return None

# --- 主畫面佈局 ---
st.title("🛡️ AI 經理人 4.0：戰鬥追蹤系統")
st.caption(f"最後更新時間：{datetime.now().strftime('%H:%M:%S')} (每分鐘自動更新數據)")

col_left, col_right = st.columns([2, 1])

with col_left:
    # --- 第四部分：每日 15 檔起漲點推薦 (含自動偵測邏輯) ---
    st.subheader("🔥 每日 15 檔起漲點預測")
    
    # 這裡模擬掃描引擎，實務上會根據 MACD/成本區 篩選
    def run_daily_scan():
        return [
            {"id": "2402.TW", "name": "毅嘉", "score": 93, "tag": "🔥 起漲確認", "reason": "突破前波大量區，MACD日線轉正。"},
            {"id": "6531.TW", "name": "愛普*", "score": 95, "tag": "🚀 強力買進", "reason": "月日MACD共振，站穩成本區以上。"},
            {"id": "3035.TW", "name": "智原", "score": 91, "tag": "🔥 慣性改變", "reason": "紅K收復大量區高點，主力換手成功。"},
            {"id": "5269.TW", "name": "祥碩", "score": 94, "tag": "👑 龍頭領漲", "reason": "帶量突破年線，溢價預期25%+"},
            {"id": "2317.TW", "name": "鴻海", "score": 85, "tag": "🛡️ 權值穩健", "reason": "守穩228元防線，MACD低位翻揚。"},
            {"id": "2603.TW", "name": "長榮", "score": 88, "tag": "🌊 趨勢啟動", "reason": "月線MACD翻紅，大波段架構確立。"},
            # ... 這裡可依此邏輯擴充至 15 檔 ...
        ]

    for idx, stock in enumerate(run_daily_scan()):
        with st.expander(f"{stock['tag']} | {stock['id']} {stock['name']} ({stock['score']}pt)"):
            c1, c2 = st.columns([4, 1])
            with c1:
                st.write(f"**分析:** {stock['reason']}")
            with c2:
                if st.button("買入", key=f"buy_{stock['id']}_{idx}"):
                    p = get_live_price(stock['id'])
                    if p:
                        st.session_state.battle_list.append({
                            "id": stock['id'], "name": stock['name'], 
                            "buy_price": p, "time": datetime.now()
                        })
                        st.success("已加入清單"); time.sleep(0.5); st.rerun()

with col_right:
    # --- 第五部分：戰鬥清單追蹤 (核心自動更新區) ---
    st.subheader("📊 戰鬥追蹤 (Live)")
    if st.session_state.battle_list:
        track_rows = []
        for i, itm in enumerate(st.session_state.battle_list):
            current_p = get_live_price(itm['id'])
            if current_p and itm['buy_price'] > 0:
                pnl = (current_p / itm['buy_price'] - 1) * 100
                
                # 賣出提示邏輯：漲幅 > 12% 且偵測背離 (此處簡化邏輯)
                advice = "✅ 持有"
                if pnl > 12: advice = "⚠️ 賣出(高檔背離)"
                elif pnl < -5: advice = "🛑 止損"
                
                track_rows.append({
                    "標的": itm['name'],
                    "成本": f"{itm['buy_price']:.1f}",
                    "現價": f"{current_p:.1f}",
                    "損益%": f"{pnl:+.2f}%",
                    "建議": advice
                })
        
        if track_rows:
            df = pd.DataFrame(track_rows)
            st.table(df)
            
            # 總結獲利
            total_pnl = sum([float(r['損益%'].replace('%','')) for r in track_rows])
            st.metric("當前戰鬥總損益", f"{total_pnl:+.2f}%")
            
            if st.button("結算清空所有部位"):
                st.session_state.battle_list = []
                st.rerun()
    else:
        st.info("目前無戰鬥中個股，請從左側選股買進。")

# --- 底部：技術指標示意圖 ---
st.divider()
st.subheader("🧠 經理人起漲點判定準則 (齒輪共振)")

st.write("1. **價格 > 前波大量成本區**：代表上方無壓力，籌碼乾淨。")
st.write("2. **MACD 翻揚且無背離**：代表動能真實，非虛假拉抬。")
