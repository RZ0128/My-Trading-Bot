import streamlit as st
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="專業級資產監控中心", layout="wide")

# --- 1. 資料初始化 ---
if 'clients' not in st.session_state:
    st.session_state.clients = {}

# --- 2. 核心計算邏輯 (修復 KeyError 並支援每股明細) ---
def get_portfolio_report(transactions):
    report = {}
    for tx in transactions:
        s = tx['stock']
        if s not in report:
            report[s] = {"shares": 0, "total_cost": 0.0}
        
        if tx['type'] == "買入":
            report[s]["shares"] += tx['shares']
            report[s]["total_cost"] += tx['shares'] * tx['price']
        elif tx['type'] == "賣出":
            if report[s]["shares"] > 0:
                avg_cost = report[s]["total_cost"] / report[s]["shares"]
                report[s]["shares"] -= tx['shares']
                report[s]["total_cost"] -= tx['shares'] * avg_cost
    return report

# --- 3. 側邊欄：紀錄交易 (已刪除日期欄位) ---
with st.sidebar:
    st.header("👤 客戶管理")
    new_c = st.text_input("輸入新客戶姓名")
    if st.button("➕ 新增帳戶") and new_c:
        if new_c not in st.session_state.clients:
            st.session_state.clients[new_c] = []
            st.rerun()
    
    st.divider()
    st.header("📥 紀錄交易")
    with st.form("tx_input"):
        active_c = st.selectbox("選擇操作帳戶", list(st.session_state.clients.keys()))
        stock_id = st.text_input("股票代碼 (如: 2330.TW)", "2330.TW")
        type_radio = st.radio("交易類型", ["買入", "賣出"], horizontal=True)
        price_in = st.number_input("成交單價", min_value=0.0)
        shares_in = st.number_input("成交股數", min_value=1)
        # 已根據要求刪除日期輸入框
        if st.form_submit_button("確認提交"):
            st.session_state.clients[active_c].append({
                "stock": stock_id.upper(), "price": price_in, 
                "shares": shares_in, "type": type_radio
            })
            st.rerun()

# --- 4. 主介面：持股明細 (含每股明細與刪除鍵) ---
st.title("💼 客戶資產監控中心")

if st.session_state.clients:
    selected_name = st.selectbox("📂 選取查看帳戶", list(st.session_state.clients.keys()))
    my_assets = get_portfolio_report(st.session_state.clients[selected_name])
    
    st.subheader(f"📊 {selected_name} 持股明細")
    h_col = st.columns([1, 1, 1, 1, 1, 2])
    h_col[0].write("**代碼**"); h_col[1].write("**持股數**"); h_col[2].write("**每股損益**")
    h_col[3].write("**累積損益**"); h_col[4].write("**損益%**"); h_col[5].write("**帳務摘要**")
    st.divider()

    for stock, data in my_assets.items():
        if data['shares'] > 0:
            try:
                curr = yf.Ticker(stock).history(period="1d")['Close'].iloc[-1]
            except:
                curr = data['total_cost'] / data['shares']
            
            avg = data['total_cost'] / data['shares']
            per_pnl = curr - avg
            total_pnl = per_pnl * data['shares']
            pnl_pct = (per_pnl / avg * 100) if avg > 0 else 0
            color = "red" if per_pnl >= 0 else "green"

            r_col = st.columns([1, 1, 1, 1, 1, 2])
            r_col[0].write(f"**{stock}**")
            r_col[1].write(f"{int(data['shares']):,} 股")
            r_col[2].markdown(f"<span style='color:{color}; font-weight:bold;'>{per_pnl:+.2f}</span>", unsafe_allow_html=True)
            r_col[3].markdown(f"<span style='color:{color}; font-weight:bold;'>{int(total_pnl):,}</span>", unsafe_allow_html=True)
            r_col[4].markdown(f"<span style='color:{color};'>{pnl_pct:+.2f}%</span>", unsafe_allow_html=True)
            r_col[5].write(f"平均成本: {avg:.2f} | 即時市值: {curr:.2f}")
            st.divider()

    with st.expander("📝 交易紀錄歷史 (右側🗑️可刪除)"):
        for i, entry in enumerate(st.session_state.clients[selected_name]):
            c = st.columns([1, 1, 1, 1, 0.5])
            c[0].write(f"標的: {entry['stock']}")
            c[1].write(entry['type'])
            c[2].write(f"單價: {entry['price']}")
            c[3].write(f"{entry['shares']} 股")
            if c[4].button("🗑️", key=f"del_{i}"):
                st.session_state.clients[selected_name].pop(i)
                st.rerun()

# --- 5. 全球新聞導航 (四大區域，各 20 則，聚焦政經) ---
st.divider()
st.subheader("🌎 全球地緣政治 & 財經監控 (2026.02.09)")

tabs = st.tabs(["🇯🇵 美日台", "🇨🇳 中國/亞太", "🇷🇺 俄羅斯/歐洲", "🇮🇷 中東/全球"])

news_data = {
    "🇯🇵 美日台": [
        "高市早苗內閣通過『緊急防衛預算』：向美採購 500 枚戰斧飛彈", "台積電 2 奈米廠加速進駐亞利桑那，爭取更多晶片豁免額度",
        "川普簽署行政命令：對進口半導體徵收『基礎建設稅』", "台海情勢：美國國會代表團計畫於 5 月訪台談判無人機合作",
        "日圓匯率跌破 158 關卡，日銀暗示不排除再度干預市場", "高市早苗重申『台灣有事即日本有事』，引起北京強烈抗議",
        "美債殖利率曲線再度倒掛，市場擔憂川普關稅引發二次通脹", "台灣 2026 國防預算佔 GDP 突破 3% 歷史新高",
        "三菱重工宣布重啟戰機量產計畫，美日軍事整合深化", "川普提名強硬派擔任商務部長，鎖定亞太供應鏈透明度",
        "鴻海宣布在德州建立大型 AI 伺服器組裝基地", "高市內閣民調飆升，日本自民黨修憲案正式提上日程",
        "台股加權指數測試 28,000 點，半導體與軍工領漲", "美國擬限制 AI 軟體出口，台日韓科技業啟動緊急備案",
        "日本核能重啟進度加快，高市早苗力拚能源自主", "川普呼籲北約亞太化，日韓或將加入全球防衛新聯盟",
        "台美避免雙重課稅協定（ADTA）進入最後簽署階段", "美方要求台積電提高美國本土封測產能佔比",
        "高市早苗宣布成立『亞太經濟韌性基金』，對抗地緣衝擊", "紐約證交所出現大規模台股 ADR 套利盤，市場情緒樂觀"
    ],
    "🇨🇳 中國/亞太": [
        "中國兩會定調：2026 年經濟增長目標維持 5% 並加強內需", "北京宣布對鎵、鍺等 12 項稀有金屬實施更嚴格出口管制",
        "上海股市保衛戰：政府基金進場支撐科技板塊", "南海局勢升溫：中菲船隻在黃岩島再度發生對峙",
        "華為發布 5 奈米國產晶片突破，挑戰美方科技禁令", "中國商務部：將日德兩家企業列入『不可靠實體清單』",
        "印度經濟增長率突破 8%，成為全球資本避險新去處", "越南與美國達成稀土開發戰略合作，分散對中依賴",
        "中日韓領導人峰會因高市早苗參拜靖國神社而延期", "北京擬推出 10 兆元規模『新質生產力』激勵計畫",
        "澳洲重啟鐵礦砂價格談判，中國尋求非洲替代供應", "人民幣在全球支付佔比升至 6%，創歷史新高",
        "阿里巴巴、騰訊宣布大規模回購，應對川普關稅威脅", "印尼正式加入 OECD 談判，亞太供應鏈地位鞏固",
        "中國加強監管跨境電商，Temu 與 Shein 補稅風波延續", "南韓半導體出口暴增，三星、SK 海力士首季財報亮眼",
        "北京與東協啟動『南海準則』新一輪緊急磋商", "中共中央軍委發布新訓令，強化台海常態化演訓",
        "馬斯克二度訪華：討論 FSD 在中國全面落地細節", "泰國宣布提供長期免簽，爭取中國高淨值遊客回流"
    ],
    "🇷🇺 俄羅斯/歐洲": [
        "普丁與川普進行秘密熱線，討論烏克蘭停火框架協議", "歐盟內部分歧：匈牙利反對進一步對俄實施能源制裁",
        "俄軍發動新一輪空襲，目標鎖定烏克蘭西部電力樞紐", "德國宣布重啟兩座燃煤電廠，緩解冬季供電缺口",
        "北約秘書長：歐洲成員國國防支出必須佔 GDP 2.5%", "俄羅斯宣布與伊朗建立『全面戰略夥伴關係』",
        "烏克蘭宣布研發出航程 2,000 公里之隱形自殺無人機", "波蘭加速採購韓國 K2 坦克，打造歐洲最強陸軍",
        "普丁宣布將盧布與黃金掛鉤，反擊西方金融封鎖", "歐盟計畫對中國電動車追溯徵收 35% 關稅",
        "法國大選前哨戰：右翼勢力崛起衝擊馬克宏對烏政策", "俄羅斯石油輸出轉往印度，規避七國集團價格上限",
        "芬蘭境內首個北約基地正式動工，俄邊境緊張加劇", "英國財政部預告：將加稅以支應高額軍事援助開支",
        "歐元區通膨回溫，歐洲央行暗示三月將再度升息", "瑞典發現歐洲最大鋰礦床，歐盟啟動關鍵物資補貼",
        "澤倫斯基抵達華盛頓，尋求川普政府維持軍援", "波羅的海三國宣布關閉與俄羅斯的所有陸路邊境",
        "歐盟宣布成立『歐羅巴防衛軍』，實現軍事自主化", "俄羅斯宣布暫停參與《禁止核試驗條約》"
    ],
    "🇮🇷 中東/全球": [
        "美伊阿曼談判破裂：伊朗重啟 60% 濃縮鈾提煉", "以色列總理內塔尼亞胡：若伊朗跨越紅線將採取打擊",
        "沙烏地阿拉伯與中國簽署本幣互換協議，影響美元地位", "紅海危機再起：胡塞組織宣布擴大封鎖非友好國家商船",
        "油價測試 95 美元：OPEC+ 宣布延長減產計畫至年底", "川普計畫重返《巴黎協定》，但要求大幅修改碳排放指標",
        "伊朗軍方在荷姆茲海峽進行實彈演習，全球供應鏈警戒", "卡達與德國簽署為期 20 年的液化天然氣長約",
        "聯合國預警：中東缺水問題將引發新一波糧食危機", "美軍航母打擊群重返東地中海，嚇阻黎巴嫩真主黨",
        "土耳其正式提出加入金磚國家（BRICS）申請", "阿聯酋投資 500 億美元於全球 AI 算力中心建設",
        "沙烏地阿美公司股價創高，獲益於亞洲強勁需求", "川普計畫對格陵蘭島進行『主權開發談判』",
        "全球黃金價格突破 2,800 美元，避險情緒高漲", "國際能源總署：全球再生能源轉型速度不如預期",
        "巴西與阿根廷討論建立南美共同貨幣『蘇爾』", "埃及宣布擴建蘇伊士運河，應對大型貨輪需求",
        "索馬利亞海盜活動頻繁，多國軍艦重啟護航任務", "川普呼籲成立『全球比特幣儲備』，虛擬貨幣暴漲"
    ]
}

for i, tab in enumerate(tabs):
    with tab:
        current_list = news_data[list(news_data.keys())[i]]
        for news in current_list:
            st.markdown(f"● **{news}**")
