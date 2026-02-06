import yfinance as yf
import requests
import os

# 確保從 GitHub Secrets 讀取網址 (對準您的 Settings 設定)
WEBHOOK = os.environ.get('DISCORD_WEBHOOK')
DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK')
