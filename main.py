import yfinance as yf
import pandas_ta as ta
import pandas as pd
import requests
import os
from datetime import datetime

# --- 1. 填寫你的 Webhook 與持倉 ---
DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK')
MY_PORTFOLIO = {
    "3023.TW": {"buy_price": 280.5, "shares": 1000},
    "1301.TW": {"buy_price": 45.2, "shares": 2000},
}
TICKERS = ["2330.TW", "2454.TW", "2317.TW", "1513.TW", "3023.TW"] # 示例，可補全150檔

def send_discord(msg):
    requests.post(DISCORD_WEBHOOK_URL, json={"content": msg})

def run_ceo_system():
    # A. 美股趨勢預判 (看 S&P 500, SOX)
    us_indices = {"^GSPC": "標普500", "^SOX": "費城半導體"}
    us_report = "🇺🇸 **美股連動分析**\n"
    for sym, name in us_indices.items():
        us_data = yf.Ticker(sym).history(period="2d")
        change = ((us_data['Close'].iloc[-1] / us_data['Close'].iloc[-2]) - 1) * 100
        us_report += f"● {name}: {round(change, 2)}% ({'🔥利多' if change > 0 else '❄️降溫'})\n"
    send_discord(us_report)

    # B. 台股持倉追蹤 (台幣計價)
    send_discord("🏛️ **【經理人創業基金】即時監控報告 (TWD)**")
    total_pl = 0
    for symbol, info in MY_PORTFOLIO.items():
        t = yf.Ticker(symbol)
        df = t.history(period="1y")
        price = df['Close'].iloc[-1]
        ma60 = ta.sma(df['Close'], length=60).iloc[-1]
        pl = (price - info['buy_price']) * info['shares']
        total_pl += pl
        
        status = (f"📊 **{t.info.get('shortName', symbol)}**: NT${format(int(pl), ',')} ({round(((price/info['buy_price'])-1)*100, 2)}%)\n"
                  f"💡 決策：{'續抱 (趨勢未變)' if price > ma60 else '警示 (破季線)'}\n")
        send_discord(status)

    # C. 未來一週強勢股推薦 (示例邏輯)
    send_discord(f"📈 **全帳戶總浮動損益：NT${format(int(total_pl), ',')}**")

if __name__ == "__main__":
    run_ceo_system()
