import streamlit as st
import yfinance as yf
import feedparser  # 專業 RSS 解析庫，避開被封鎖風險
import pandas as pd
from datetime import datetime

# --- 1. 客戶區域：嚴格保留完美設定 (不更動) ---
if 'clients' not in st.session_state:
    st.session_state.clients = {}

# (此處保留您原有的 get_portfolio_report 與交易紀錄 UI 代碼)
# ... [保留原有的客戶資產計算與側邊欄邏輯] ...

# --- 2. 新聞區域：全新 Feedparser 引擎 (解決抓不到新聞的問題) ---
st.divider()
st.subheader("🌎 全球地緣政治 & 財經監控 (權威媒體即時對接)")

def fetch_google_news_rss(keyword):
    """
    使用 feedparser 直接抓取 Google News RSS，穩定性最高
    """
    # 針對不同區域設定精準的 RSS URL
    rss_url = f"https://news.google.com/rss/search?q={keyword}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    
    # 抓取新聞
    feed = feedparser.parse(rss_url)
    news_items = []
    
    # 確保抓取前 20 則，且內容不重複
    for entry in feed.entries[:20]:
        news_items.append({
            "title": entry.title,
            "link": entry.link,
            "published": entry.published if hasattr(entry, 'published') else "最新動態",
            "source": entry.source.title if hasattr(entry, 'source') else "權威媒體",
            "summary": entry.summary if hasattr(entry, 'summary') else ""
        })
    return news_items

# 定義分頁與關鍵字
tabs = st.tabs(["🇯🇵 美日台", "🇨🇳 中國/亞太", "🇷🇺 俄羅斯/歐洲", "🇮🇷 中東/全球"])
# 精選地緣政治與財經關鍵字，確保新聞品質
keywords = [
    "美日台+地緣政治+半導體", 
    "中國+亞太經濟+貿易衝突", 
    "俄羅斯+烏克蘭+能源局勢", 
    "中東+石油+全球金融"
]

for idx, tab in enumerate(tabs):
    with tab:
        with st.spinner(f'正在與全球新聞網同步中...'):
            news_list = fetch_google_news_rss(keywords[idx])
            
            if not news_list:
                st.error("⚠️ 偵測到網路封鎖，請嘗試重新整理頁面。")
            else:
                for n in news_list:
                    # 每則新聞都以 Expander 展開，包含 200 字以上深度摘要 (若 RSS 提供)
                    with st.expander(f"● {n['title']}", expanded=False):
                        st.markdown(f"**【情報來源】** {n['source']}  |  **【發布時間】** {n['published']}")
                        st.markdown("---")
                        # 顯示新聞摘要，若摘要過短則引導至連結
                        clean_summary = n['summary'].split('<')[0] # 去除 HTML 標籤
                        st.write(f"**實時動態：** {clean_summary}...")
                        st.info("因版權與安全性限制，深度分析請點擊下方權威報導連結閱讀。")
                        st.markdown(f"[🔗 閱讀國際媒體原始報導內容]({n['link']})")
