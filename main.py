import yfinance as yf
import requests
import os

# 1. 對準保險箱名字
WEBHOOK = os.environ.get('DISCORD_WEBHOOK')

def run():
    if not WEBHOOK:
        print("錯誤：找不到保險箱網址")
        return

    # 2. 設定您的股票資料
    portfolio = {"3023.TW": 280.5, "2330.TW": 950.0}
    
    msg = "🏛️ **創業基金即時報告 (TWD)**\n"
    for sym, buy_p in portfolio.items():
        try:
            # 獲取最新股價
            ticker = yf.Ticker(sym)
            df = ticker.history(period="1d")
            if df.empty:
                msg += f"● {sym}: 暫無成交資料\n"
                continue
                
            curr_p = df['Close'].iloc[-1]
            diff = (curr_p - buy_p) / buy_p * 100
            msg += f"● {sym}: NT${round(curr_p,1)} ({round(diff,2)}%)\n"
        except Exception as e:
            msg += f"● {sym}: 讀取失敗\n"
            
    # 3. 發送至 Discord
    requests.post(WEBHOOK, json={"content": msg})
    
    print("發送成功")

if __name__ == "__main__":
    run()
