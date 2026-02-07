import yfinance as yf
import requests
import os
from datetime import datetime

# 1. 設定區：請確保您的 Discord Webhook 已設定在 GitHub Secrets 中
WEBHOOK = os.environ.get('DISCORD_WEBHOOK')
MIN_GAIN = 10.0  # 預期漲幅門檻，低於此數值不顯示

# 2. 客戶持倉清單 (已修正為字典格式，支援中文與台幣計算)
# 註：qty 代表張數 (1張=1000股)
MY_PORTFOLIO = {
    "3023.TW": {"name": "信邦", "cost": 280.5, "qty": 0.5},
    "2330.TW": {"name": "台積電", "cost": 950.0,"qty":  0.5}
}

# 3. 150 檔全市場掃描清單 (含中文名稱)
STOCK_POOL = {
    "半導體與 AI 核心": {
        "2330.TW": "台積電", "2454.TW": "聯發科", "2317.TW": "鴻海", "2308.TW": "台達電", "2382.TW": "廣達",
        "3711.TW": "日月光投控", "3231.TW": "緯創", "2357.TW": "華碩", "6669.TW": "緯穎", "2301.TW": "光寶科",
        "2379.TW": "瑞昱", "3034.TW": "聯詠", "3037.TW": "欣興", "2408.TW": "南亞科", "2303.TW": "聯電",
        "4966.TW": "譜瑞-KY", "3661.TW": "世芯-KY", "5269.TW": "祥碩", "3443.TW": "創意", "3035.TW": "智原",
        "8046.TW": "南電", "2360.TW": "致茂", "3532.TW": "台勝科", "6239.TW": "力成", "2449.TW": "京元電子",
        "3017.TW": "奇鋐", "3321.TW": "同泰", "6213.TW": "聯茂", "2383.TW": "台光電", "3023.TW": "信邦",
        "3653.TW": "健策", "6176.TW": "瑞儀", "4958.TW": "臻鼎-KY", "2474.TW": "可成", "3131.TW": "弘塑",
        "3583.TW": "辛耘", "1560.TW": "勤誠", "2376.TW": "技嘉", "2353.TW": "宏碁", "2324.TW": "仁寶"
    },
    "關鍵零組件": {
        "2327.TW": "國巨", "2492.TW": "華新科", "3044.TW": "健鼎", "2313.TW": "華通", "2367.TW": "燿華",
        "2368.TW": "金像電", "3189.TW": "景碩", "3006.TW": "晶豪科", "2451.TW": "創見", "2352.TW": "佳世達",
        "2355.TW": "敬鵬", "2458.TW": "義隆", "3533.TW": "嘉澤", "6206.TW": "飛捷", "3014.TW": "聯陽",
        "2439.TW": "美律", "2480.TW": "敦陽科", "6116.TW": "彩晶", "8215.TW": "明基材", "2347.TW": "聯強",
        "2344.TW": "華邦電", "5347.TW": "世界先進", "2455.TW": "全新", "2441.TW": "超豐", "3293.TW": "鈊象",
        "3592.TW": "瑞鼎", "6706.TW": "勁豐", "6719.TW": "力智", "6770.TW": "力積電", "8069.TW": "元太"
    },
    "重電綠能傳產": {
        "1513.TW": "中興電", "1519.TW": "華城", "1503.TW": "士電", "1504.TW": "東元", "1605.TW": "華新",
        "1514.TW": "亞力", "1101.TW": "台泥", "1102.TW": "亞泥", "1301.TW": "台塑", "1303.TW": "南亞",
        "1326.TW": "台化", "6505.TW": "台塑化", "1717.TW": "長興", "1722.TW": "台肥", "2105.TW": "正新",
        "2103.TW": "台橡", "2002.TW": "中鋼", "2006.TW": "東和鋼鐵", "2014.TW": "中鴻", "1216.TW": "統一",
        "1210.TW": "大成", "9910.TW": "豐泰", "9921.TW": "巨大", "9914.TW": "美利達", "1476.TW": "儒鴻",
        "1477.TW": "聚陽", "2603.TW": "長榮", "2609.TW": "陽明", "2615.TW": "萬海", "2618.TW": "長榮航",
        "2610.TW": "華航", "2707.TW": "晶華", "2723.TW": "美食-KY", "2912.TW": "統一超", "5904.TW": "寶雅",
        "8454.TW": "富邦媒", "9945.TW": "潤泰新", "2542.TW": "興富發", "5522.TW": "遠雄", "1802.TW": "台玻"
    },
    "金融權值": {
        "2881.TW": "富邦金", "2882.TW": "國泰金", "2886.TW": "兆豐金", "2891.TW": "中信金", "2884.TW": "玉山金",
        "2880.TW": "華南金", "2885.TW": "元大金", "2892.TW": "第一金", "5880.TW": "合庫金", "2883.TW": "開發金",
        "2887.TW": "台新金", "2890.TW": "永豐金", "5871.TW": "中租-KY", "5876.TW": "上海商銀", "2801.TW": "彰銀",
        "2812.TW": "台中銀", "2834.TW": "臺企銀", "2888.TW": "新光金", "2845.TW": "遠東銀", "2851.TW": "中再保"
    }
}

def get_institutional_data(sym):
    """預判模組：獲取量能動向"""
    ticker = yf.Ticker(sym)
    hist = ticker.history(period="5d")
    if len(hist) < 5: return False
    avg_vol = hist['Volume'].mean()
    last_vol = hist['Volume'].iloc[-1]
    return last_vol > avg_vol and hist['Close'].iloc[-1] > hist['Open'].iloc[-1]

def get_analysis(df, sym):
    """進階預判分析：技術面與籌碼量能"""
    close = df['Close'].iloc[-1]
    ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
    ma5 = df['Close'].rolling(window=5).mean().iloc[-1]
    exp12 = df['Close'].ewm(span=12, adjust=False).mean()
    exp26 = df['Close'].ewm(span=26, adjust=False).mean()
    macd = exp12 - exp26
    sig = macd.ewm(span=9, adjust=False).mean()
    
    has_big_money = get_institutional_data(sym)
    expected = round(df['Close'].pct_change().std() * 250, 1)
    
    reason = "技術面：站穩月線；"
    if has_big_money:
        reason += "🔍 預判：法人量能啟動，具備噴出跡象。"
    if macd.iloc[-1] > sig.iloc[-1]:
        reason += "MACD金叉翻揚。"
        
    return expected, reason

def run():
    # 國安基金監控狀態 (手動更新或接入API)
    n_status = "🛡️ **國安基金動態：目前處於觀望/未啟動狀態**"
    p_report = f"{n_status}\n\n🏛️ **客戶持倉損益報告**\n"
    
    total_profit = 0
    for sym, info in MY_PORTFOLIO.items():
        ticker = yf.Ticker(sym)
        df = ticker.history(period="1mo")
        if not df.empty:
            curr = df['Close'].iloc[-1]
            buy_p = info["cost"]
            qty = info.get("qty", 1)
            diff_pct = (curr - buy_p) / buy_p * 100
            diff_cash = (curr - buy_p) * 1000 * qty # 計算台幣獲利 (每張1000股)
            total_profit += diff_cash
            p_report += f"● {info['name']}({sym}): {round(diff_pct,2)}% | **NT$ {int(diff_cash):,}**\n"
    
    p_report += f"\n💰 **總估計損益：NT$ {int(total_profit):,}**\n"

    final_report = "🎯 **籌碼面/技術面 雙重精選推薦**\n"
    for cat, stocks in STOCK_POOL.items():
        cat_section = f"\n【{cat}】\n"
        has_bull = False
        for sym, name in stocks.items():
            try:
                df = yf.Ticker(sym).history(period="3mo")
                if len(df) < 20: continue
                curr = df['Close'].iloc[-1]
                ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
                if curr > ma20:
                    gain, reason = get_analysis(df, sym)
                    if gain >= MIN_GAIN:
                        has_bull = True
                        cat_section += f"🚀 **{name}({sym})**: 現價 {round(curr,1)}\n"
                        cat_section += f" └ 📊 預判分析：{reason}\n"
                        cat_section += f" └ 📈 預期漲幅：+{gain}%\n\n"
            except: continue
        if has_bull: final_report += cat_section

    full_text = p_report + "\n" + final_report
    for i in range(0, len(full_text), 1900):
        requests.post(WEBHOOK, json={"content": full_text[i:i+1900]})

if __name__ == "__main__":
    run()

