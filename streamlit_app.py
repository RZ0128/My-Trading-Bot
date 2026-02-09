import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="全球資產與地緣政治導航", layout="wide")

# --- 1. 資料初始化 ---
if 'clients' not in st.session_state:
    st.session_state.clients = {"新客戶": []}

# --- 2. 核心計算邏輯 (刪除鍵同步) ---
def get_portfolio_analysis(transactions):
    analysis = {}
    for tx in transactions:
        s = tx['stock']
        if s not in analysis: analysis[s] = {"shares": 0, "total_cost": 0.0}
        if tx['type'] == "買入":
            analysis[s]["shares"] += tx['shares']
            analysis[s]["total_cost"] += tx['shares'] * tx['price']
        elif tx['type'] == "賣出":
            if analysis[s]["shares"] > 0:
                avg_cost = analysis[s]["total_cost"] / analysis[s]["shares"]
                analysis[s]["shares"] -= tx['shares']
                analysis[s]["total_cost"] -= tx['shares'] * avg_cost
    return analysis

# --- 3. 跑馬燈 (台股行情) ---
st.markdown("""
    <style>
    .marquee { background-color: #0e1117; color: #ff4b4b; padding: 10px; border-bottom: 2px solid #ff4b4b; font-weight: bold; }
    .critical { color: white; background-color: #ff0000; padding: 2px 5px; border-radius: 3px; font-size: 12px; animation: blinker 1.5s linear infinite; }
    @keyframes blinker { 50% { opacity: 0; } }
    </style>
""", unsafe_allow_html=True)

def get_marquee():
    try:
        symbols = {"加權指數": "^TWII", "台積電": "2330.TW", "鴻海": "2317.TW", "美股道瓊": "^DJI"}
        text = ""
        for name, sym in symbols.items():
            d = yf.Ticker(sym).history(period="2d")
            p = d['Close'].iloc[-1]
            c = p - d['Close'].iloc[-2]
            icon = "🔺" if c >= 0 else "🔻"
            text += f" | {name}: {p:.2f} ({icon}{c:+.2f}) "
        return text
    except: return " | 數據連線中..."

st.markdown(f'<div class="marquee"><marquee scrollamount="6">{get_marquee()}</marquee></div>', unsafe_allow_html=True)

# --- 4. 客戶資產與刪除功能 (iPad 優化) ---
st.title("💼 專業投資人資產管理系統")
cur_client = st.selectbox("📁 選擇管理客戶", list(st.session_state.clients.keys()))

col_p1, col_p2 = st.columns([3, 2])
portfolio = get_portfolio_analysis(st.session_state.clients[cur_client])

with col_p1:
    st.subheader("📊 現有持股與即時損益")
    if not st.session_state.clients[cur_client]:
        st.info("目前無交易紀錄。")
    else:
        for stock, data in portfolio.items():
            if data['shares'] > 0:
                avg = data['total_cost'] / data['shares']
                c1, c2, c3 = st.columns(3)
                c1.metric("標的", stock)
                c2.metric("持股", f"{int(data['shares'])} 股")
                c3.metric("均價", f"{avg:.2f}")
                st.divider()

with col_p2:
    with st.expander("📝 交易明細 (右側刪除)", expanded=True):
        for idx, tx in enumerate(st.session_state.clients[cur_client]):
            cols = st.columns([2, 1, 1, 1])
            cols[0].write(f"{tx['date']} {tx['stock']}")
            cols[1].write(f"<span style='color:{'red' if tx['type']=='買入' else 'green'}'>{tx['type']}</span>", unsafe_allow_html=True)
            cols[2].write(f"${tx['price']}")
            if cols[3].button("🗑️", key=f"del_{idx}"):
                st.session_state.clients[cur_client].pop(idx)
                st.rerun()

# --- 5. 全球新聞動態分析 (含動態標籤與關鍵字預警) ---
st.divider()
st.subheader("🌎 全球地緣政治 & 財經監控 (2026.02)")

# 可隨時編輯的動態預警關鍵字
with st.expander("⚙️ 預警字眼設定 (可自行根據國際情勢增減)"):
    warn_input = st.text_area("當新聞出現以下關鍵字時自動標紅：", "川普, 關稅, 日本國會, 台海, 兩會, 核談判, 稀土, 中美, 封鎖, 停火")
    warn_keywords = [k.strip() for k in warn_input.split(',')]

# 新聞區塊
tab1, tab2, tab3, tab4 = st.tabs(["🇺🇸美日台局勢", "🇨🇳中國與亞太", "🇪🇺歐洲與俄烏", "🇮🇷中東與全球"])

def format_news(news_list):
    for n in news_list:
        # 重大新聞標記
        is_critical = "【重大】" in n
        display_text = n.replace("【重大】", '<span class="critical">重大</span> ')
        
        # 關鍵字變色
        for kw in warn_keywords:
            if kw in display_text:
                display_text = display_text.replace(kw, f"<span style='color:red; font-weight:bold;'>{kw}</span>")
        
        st.markdown(f"• {display_text}", unsafe_allow_html=True)

with tab1: # 美日台
    format_news([
        "【重大】日本眾議院大選結果揭曉：高市早苗帶領自民黨奪下 316 席，跨越修憲門檻。",
        "川普 於社群平台祝賀高市早苗，並喊話 3 月白宮會面談論新版 關稅 協議。",
        "美國商務部考慮對台半導體出口實施「靈活性」管制，觀察 2026 上半年 台海 變化。",
        "台海 局勢名列 2026 全球衝突熱點第一，智庫預警中國可能採取經濟封鎖手段。",
    ] + [f"美日財經觀測：聯準會新任主席華許擬推動積極降息政策，應對 關稅 衝擊新聞 {i}" for i in range(1, 15)])

with tab2: # 中國
    format_news([
        "【重大】習近平計畫於 2026 年底訪問美國，美中關係試圖在貿易戰陰影下重啟溝通。",
        "中國商務部擴大 稀土 管制範圍，嚴格審核輸日半導體關鍵用戶。",
        "兩會 前夕：中國高層針對張又俠遭調查引發的軍事裂痕進行內部整頓。",
        "中印關係回暖：印度擬開放支付系統對接中國供應鏈，緩解地緣壓力。",
    ] + [f"亞太觀察：中國低價產能過剩持續衝擊全球傳產市場新聞 {i}" for i in range(1, 15)])

with tab3: # 歐洲與俄羅斯
    format_news([
        "【重大】俄烏戰爭 邁入第五年，川普 擬推動「以領土換安全」停火方案，普丁尚未表態。",
        "歐洲各國 加強國防開支，德國外資投資因 美國 關稅 反而呈現翻倍流入趨勢。",
        "俄羅斯特使出現在邁阿密，與 美國 團隊閉門討論烏克蘭衝突凍結可能性。",
        "法國、波蘭領袖憂慮 美國 撤出北約，考慮成立歐洲獨立防衛聯盟。",
    ] + [f"俄烏動態：東線戰場進入精疲力竭期，雙方測試外交底線新聞 {i}" for i in range(1, 15)])

with tab4: # 中東與全球
    format_news([
        "【重大】美伊核談判 擬於近日重啟，川普 簽署行政命令封鎖委內瑞拉石油出口。",
        "中東 局勢：美軍加強紅海護航，應對伊朗支援之武裝組織對能源航道之威脅。",
        "古巴 抨擊 美國 加徵石油關稅為「殘酷侵略」，尋求 俄羅斯 能源援助。",
        "華爾街 預警：AI 基礎建設投資紅利耗盡，2026 年市場轉向防禦型資產。",
    ] + [f"全球趨勢：氣候變遷引發之關鍵礦物爭奪戰持續升溫新聞 {i}" for i in range(1, 15)])

# --- 6. 側邊欄紀錄 ---
with st.sidebar:
    st.header("📥 紀錄交易")
    with st.form("tx"):
        s = st.text_input("代碼", "2330.TW"); t = st.radio("類型", ["買入", "賣出"], horizontal=True)
        p = st.number_input("價格", 0.0); sh = st.number_input("股數", 1); d = st.date_input("日期")
        if st.form_submit_button("確認提交"):
            st.session_state.clients[cur_client].append({"date":str(d),"stock":s.upper(),"price":p,"shares":sh,"type":t})
            st.rerun()
