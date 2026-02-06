import yfinance as yf
import pandas_ta as ta
import pandas as pd
import requests
import os

# 確保從 GitHub Secrets 讀取網址
WEBHOOK = os.environ.get('DISCORD_WEBHOOK')
DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK')
def run():
    # 簡單測試：如果沒網址就報錯提醒
    if not WEBHOOK:
        print("錯誤：找不到 DISCORD_WEBHOOK 設定")
        return

    # 持倉資料 (請確保格式正確)
    portfolio = {"3023.TW": 280.5, "2330.TW": 950.0}
    
    msg = "🏛️ **創業基金即時報告**\n"
    for sym, buy_p in portfolio.items():
        try:
            df = yf.Ticker(sym).history(period="1mo")
            curr_p = df['Close'].iloc[-1]
            diff = (curr_p - buy_p) / buy_p * 100
            msg += f"● {sym}: NT${round(curr_p,1)} ({round(diff,2)}%)\n"
        except:
            msg += f"● {sym}: 讀取失敗\n"
            
    requests.post(WEBHOOK, json={"content": msg})
    print("報告已發送至 Discord")

if __name__ == "__main__":
    run()
