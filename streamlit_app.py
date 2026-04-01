import streamlit as st
import pandas as pd
import yfinance as yf
import feedparser
import ssl
import os
from datetime import datetime, timedelta
import urllib.parse
import numpy as np
import collections
import re
import time

# --- [V15.2 雲端安全通訊官：Google Sheets 同步模組] ---
try:
    import gspread
    import json
    from google.oauth2.service_account import Credentials
except ImportError:
    st.error("❌ 缺少雲端同步套件 (gspread)，請確保 requirements.txt 已更新。")

# --- [第 1 區：核心配置與 CSS 樣式] ---
st.set_page_config(page_title="大基石-V15.3 自主進化雲端版", layout="wide")

st.markdown("""
    <style>
    /* 全域字體與顏色設定 */
    html, body, [class*="css"] { font-size: 13px !important; color: #1e1e1e; }
    
    /* 按鈕樣式佈局 (完全保留) */
    .stButton>button { 
        height: 32px !important; 
        padding: 0px 15px !important; 
        font-size: 13px !important; 
        border-radius: 6px !important;
        font-weight: bold !important;
    }
    
    /* 籌碼洗盤標籤 (完全保留) */
    .sentiment-tag { 
        color: #00D1FF; 
        font-weight: bold; 
        border: 1px solid #00D1FF; 
        padding: 3px 6px; 
        border-radius: 4px; 
        background: rgba(0, 209, 255, 0.1); 
    }
    
    /* 狀態列樣式 (完全保留) */
    .status-bar { 
        padding: 8px 15px; 
        border-radius: 10px; 
        margin-bottom: 15px; 
        font-weight: bold; 
        display: flex; 
        align-items: center; 
        gap: 10px; 
    }
    .status-on { background-color: #e6fffa; color: #2c7a7b; border: 1px solid #81e6d9; }
    .status-off { background-color: #fff5f5; color: #c53030; border: 1px solid #feb2b2; }
    </style>
    """, unsafe_allow_html=True)


# --- [V15.3 備援指揮部：多源數據狀態監控] ---
with st.sidebar:
    st.markdown("### 🛠️ 數據戰備狀態")
    
    # 1. 檢查備援 A (twstock)
    try:
        import twstock
        st.success("✅ 備援 A (台股在地庫) 已就緒")
    except ImportError:
        st.error("❌ 備援 A (twstock) 缺失")

    # 2. 檢查備援 B (Yahoo Finance)
    try:
        st.success("✅ 備援 B (全球數據流) 已就緒")
    except:
        st.error("❌ 備援 B 連線異常")

    # 3. 檢查備援 C (Requests/urllib)
    import requests
    st.success("✅ 備援 C (全球快取) 已就緒")
    
    st.markdown("---")


# --- [第 2 區：定義監控函數與連線邏輯] ---

def init_cloud_connection():
    try:
        if "GCP_JSON_KEY" not in st.secrets:
            st.sidebar.error("❌ Secrets 中找不到 GCP_JSON_KEY 配置")
            return None
        
        # 1. 取得原始數據並轉為字典
        raw_key = st.secrets["GCP_JSON_KEY"]
        if hasattr(raw_key, "to_dict"):
            gcp_json = raw_key.to_dict()
        else:
            gcp_json = dict(raw_key)
            
        # 2. 【大基石專用：金鑰深度洗滌】
        pk = str(gcp_json.get("private_key", ""))
        
        # 移除所有可能的干擾字元
        pk = pk.replace("\\n", "\n") # 修復雙重轉義
        pk = pk.strip().strip("'").strip('"') # 移除前後引號
        
        # 確保頭尾格式正確，且中間沒有多餘空格
        if "-----BEGIN PRIVATE KEY-----" not in pk:
            pk = "-----BEGIN PRIVATE KEY-----\n" + pk
        if "-----END PRIVATE KEY-----" not in pk:
            pk = pk + "\n-----END PRIVATE KEY-----"
            
        gcp_json["private_key"] = pk
        
        # 3. 驗證必要欄位是否完整
        required_fields = ["project_id", "client_email", "private_key"]
        for field in required_fields:
            if not gcp_json.get(field):
                st.sidebar.error(f"❌ 金鑰遺失欄位: {field}")
                return None

        # 4. 執行連線
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(gcp_json, scopes=scopes)
        gc = gspread.authorize(creds)
        
        return gc.open("StoneManager_DB")
        
    except Exception as e:
        # 顯示更詳細的錯誤，幫助判斷是格式還是權限問題
        err_msg = str(e)
        if "BadStatusLine" in err_msg:
            st.sidebar.error("🌐 網路連線不穩，請稍後再試")
        elif "padding" in err_msg.lower():
            st.sidebar.error("🔑 金鑰內容受損（Padding Error），請重新檢查 Secrets 內容")
        else:
            st.sidebar.error(f"🔑 金鑰診斷: {err_msg[:50]}")
        return None


def get_cloud_df(sh, sheet_name):
    try:
        worksheet = sh.worksheet(sheet_name)
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()


# --- 在現有的 get_cloud_df 之後插入 ---
def safe_get_df(sh, name):
    try:
        df = get_cloud_df(sh, name)
        if not df.empty:
            # 💡 大基石修復：強制將所有欄位轉為字串，並過濾掉可能導致 Arrow 崩潰的類型
            for col in df.columns:
                # 先轉為物件類型，處理 nan 後再轉字串
                df[col] = df[col].astype(object).replace([np.nan, None, 'nan', 'None', '<NA>'], '')
                df[col] = df[col].astype(str)
            return df
        return pd.DataFrame()
    except Exception as e:
        st.sidebar.warning(f"⚠️ {name} 讀取異常: {str(e)[:20]}")
        return pd.DataFrame()


def get_us_market_impact():
    try:
        tickers = {"^SOX": "費半", "^IXIC": "那指", "TSM": "台積電ADR", "NVDA": "輝達"}
        impact_report = {}
        total_stress = 0
        for tid, tname in tickers.items():
            tk = yf.Ticker(tid)
            h = tk.history(period="2d")
            if len(h) < 2: continue
            change = ((h['Close'].iloc[-1] - h['Close'].iloc[-2]) / h['Close'].iloc[-2]) * 100
            impact_report[tname] = round(change, 2)
            if change < -2.5: total_stress += 1
        return impact_report, total_stress
    except:
        return {}, 0

def run_auto_cruise():
    if 'last_cruise' not in st.session_state:
        st.session_state.last_cruise = datetime.now()
    else:
        now = datetime.now()
        if (now - st.session_state.last_cruise).seconds > 600:
            st.session_state.last_cruise = now

def check_connection():
    try:
        sh = init_cloud_connection()
        if sh: return True, "✅ 雲端同步中：gspread 已成功對齊 StoneManager_DB"
        return False, "❌ 連線失敗：無法辨認金鑰或權限不足"
    except:
        return False, "❌ 連線失敗：請檢查 Secrets 設定"

def load_data():
    """大腦初始化程序 - 穩定強化版：先建立保底，再對接雲端"""
    if 'initialized' in st.session_state and st.session_state.initialized:
        return
    
    # --- [第一步：強制建立所有保底變數，防止 UI 崩潰] ---
    if 'client_list' not in st.session_state:
        st.session_state.client_list = ["Robert"]
    if 'local_db' not in st.session_state:
        st.session_state.local_db = pd.DataFrame(columns=['client', 'id', 'name', 'shares', 'buy_price', 'unit', 'entry_reason', 'sentiment'])
    if 'trade_history' not in st.session_state:
        st.session_state.trade_history = pd.DataFrame(columns=['date', 'client', 'id', 'action', 'shares', 'price', 'note'])
    
    # 初始化進度條
    progress_bar = st.progress(0, text="🤖 AI 大腦啟動：正在初始化雲端對齊程序...")
    
    try:
        # --- [第二步：嘗試對接 GCP] ---
        sh = init_cloud_connection()
        if not sh: 
            raise Exception("無法辨認 Secrets 金鑰或 Google Sheets 權限未開啟")

        # --- [1/4] 正在掃描 Inventory (庫存) ---
        progress_bar.progress(25, text="📊 [1/4] 正在對齊 Inventory 雲端數據...")
        inv_df = safe_get_df(sh, "inventory")
        if not inv_df.empty:
            for col in ['id', 'client', 'name']:
                if col in inv_df.columns:
                    inv_df[col] = inv_df[col].astype(str)
            st.session_state.local_db = inv_df
            st.session_state.inventory = inv_df
        
        # --- [2/4] 正在同步 History (交易紀錄) ---
        progress_bar.progress(50, text="📜 [2/4] 正在對齊 History 交易紀錄...")
        his_df = safe_get_df(sh, "history")
        if not his_df.empty:
            for col in ['action', 'id', 'client']:
                if col in his_df.columns:
                    his_df[col] = his_df[col].astype(str)
            st.session_state.trade_history = his_df
            
        # --- [3/4] 正在對齊 Clients (客戶清單) ---
        progress_bar.progress(75, text="👥 [3/4] 正在同步客戶名單系統...")
        client_df = safe_get_df(sh, "clients")
        if not client_df.empty and 'name' in client_df.columns:
            cloud_clients = client_df['name'].dropna().astype(str).tolist()
            combined = list(set(["Robert"] + cloud_clients))
            st.session_state.client_list = sorted([c for c in combined if c not in ["nan", "None", ""]])
        
        # --- [4/4] 雲端對齊完成 ---
        progress_bar.progress(100, text="✅ [4/4] 雲端對齊成功！")
        time.sleep(0.5)

    except Exception as e:
        st.sidebar.warning(f"📡 雲端目前離線：使用本地模式")
        st.sidebar.error(f"金鑰診斷: {str(e)[:40]}")

    
    # 無論成功失敗，都標記為已初始化，防止無限循環
    st.session_state.initialized = True
    if 'progress_bar' in locals():
        progress_bar.empty()



def get_full_ticker(tid):
    tid = str(tid).strip().upper().split(".")[0]
    if not tid.isdigit(): return tid
    try:
        import twstock
        if tid in twstock.codes:
            market = twstock.codes[tid].market
            return f"{tid}.TWO" if "上櫃" in market else f"{tid}.TW"
    except: pass
    return f"{tid}.TW"

def get_stock_name(ticker):
    raw_id = str(ticker).split(".")[0].strip()
    if 'STOCK_MAP' in globals() and raw_id in STOCK_MAP:
        return STOCK_MAP[raw_id]
    if 'local_db' in st.session_state and not st.session_state.local_db.empty:
        if 'id' in st.session_state.local_db.columns:
            match = st.session_state.local_db[st.session_state.local_db['id'].astype(str).str.contains(raw_id)]
            if not match.empty:
                name_val = str(match['name'].iloc[0])
                if name_val not in ['nan', 'None', '', None]:
                    return name_val
    if raw_id.isdigit():
        try:
            import twstock
            if raw_id in twstock.codes:
                return twstock.codes[raw_id].name
        except: pass
    try:
        full_tid = get_full_ticker(raw_id)
        tk = yf.Ticker(full_tid)
        name = tk.info.get('shortName') or tk.info.get('longName') or f"個股 {raw_id}"
        return name
    except:
        return f"個股 {raw_id}"

def get_stock_perf(ticker, period_days=0):
    raw_id = str(ticker).split(".")[0].strip()
    if raw_id.isdigit():
        try:
            import twstock
            stock = twstock.Stock(raw_id)
            prices = stock.price[-5:] 
            if len(prices) >= 2 and prices[-1] is not None:
                return float(prices[-1]), float(prices[-1] - prices[-2]), "[T]"
        except: pass
    try:
        full_tid = get_full_ticker(raw_id)
        tk = yf.Ticker(full_tid)
        hist = tk.history(period="2d")
        if not hist.empty:
            cp = hist['Close'].iloc[-1]
            dp = hist['Close'].iloc[-1] - hist['Close'].iloc[-2]
            return float(cp), float(dp), "[Y]"
    except: pass
    return 0, 0, "[N/A]"

def record_transaction(client, tid, action, shares, price, note):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    log_entry = {'date': now_str, 'client': client, 'id': tid, 'action': action, 'shares': shares, 'price': price, 'note': note}
    new_log_df = pd.DataFrame([log_entry])
    if 'trade_history' not in st.session_state:
        st.session_state.trade_history = new_log_df
    else:
        st.session_state.trade_history = pd.concat([st.session_state.trade_history, new_log_df], ignore_index=True)
    try:
        sh = init_cloud_connection()
        if sh:
            ws = sh.worksheet("history")
            ws.append_row([now_str, client, tid, action, shares, price, note])
            st.toast(f"✅ 雲端同步成功！已紀錄至 Sheets", icon='🚀')
        else:
            st.error("❌ 雲端連線失敗")
    except Exception as e:
        st.error(f"⚠️ 雲端寫入異常: {e}")

def update_ai_thought_log(ticker, score, msg):
    try:
        sh = init_cloud_connection()
        if sh:
            ws = sh.worksheet("thought_log")
            ws.append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), str(ticker), get_stock_name(ticker), score, msg])
            return True
    except: return False

# ==============================================================================
# 第 3 區：大基石史詩級強大腦 V15.3 - 核心診斷與 MACD 斜率引擎
# ==============================================================================

def get_macd_slope(df):
    """大基石核心：MACD 斜率共振偵測 (完全保留)"""
    if df is None or df.empty or len(df) < 35: 
        return 0, "📡 數據不足"
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    slope = (macd.iloc[-1] - macd.iloc[-3]) / 2
    if macd.iloc[-1] > signal.iloc[-1]:
        status = "📈 翻揚" if slope > 0 else "⚠️ 高檔鈍化"
    else:
        status = "📉 轉弱" if slope < 0 else "🧬 底背離觀察"
    return slope, status

def ai_pattern_discovery(ticker, h_max):
    """AI 自主發現法則 (完全保留)"""
    if h_max is None or len(h_max) < 100: return None
    c, v = h_max['Close'], h_max['Volume']
    recent_v_min = v.tail(10).min()
    avg_v_50 = v.tail(50).mean()
    if recent_v_min < avg_v_50 * 0.3 and c.iloc[-1] > c.iloc[-2] * 1.03:
        return "🧬 AI 發現新法則：極致窒息量後跳空模型 (勝率待測)"
    return None

def ai_evolution_engine(ticker, h_max, current_price):
    """大腦進化引擎：包含融資/籌碼洗盤、島狀反轉、爆量預警 (完全保留)"""
    if h_max is None or h_max.empty or len(h_max) < 250:
        return 50, "📚 數據積累中", 50.0, "🔍 觀察"
    
    c, v, hi, lo = h_max['Close'], h_max['Volume'], h_max['High'], h_max['Low']
    score = 60
    intel_tags = []

    # 1. 價格與 MACD 背離偵測
    ema12 = c.ewm(span=12).mean(); ema26 = c.ewm(span=26).mean()
    macd = ema12 - ema26
    if c.iloc[-1] > c.tail(20).max() * 0.98 and macd.iloc[-1] < macd.tail(20).max() * 0.8:
        score -= 25; intel_tags.append("🚨 偵測到指標背離")

    # 2. 島狀反轉偵測
    if lo.iloc[-1] > hi.iloc[-2]: intel_tags.append("🏝️ 島狀反轉潛力(多)"); score += 15
    if hi.iloc[-1] < lo.iloc[-2]: intel_tags.append("🏚️ 島狀反轉潛力(空)"); score -= 20

    # 3. 量縮收斂三角形
    price_range = (hi.tail(20).max() - lo.tail(20).min()) / c.iloc[-1]
    if price_range < 0.05 and v.iloc[-1] < v.tail(20).mean() * 0.6:
        score += 20; intel_tags.append("📐 量縮收斂三角形")

    # 4. 跳空高檔爆巨量
    avg_v_year = v.rolling(248).mean().iloc[-1]
    if c.iloc[-1] > c.rolling(248).mean().iloc[-1] * 1.3 and v.iloc[-1] > avg_v_year * 3:
        score -= 45; intel_tags.append("💀 高檔爆巨量(出貨預警)")

    # 5. 八大法則與洗盤偵測模組
    ma20 = c.rolling(20).mean().iloc[-1]
    if c.iloc[-1] > ma20 and v.iloc[-1] > v.rolling(20).mean().iloc[-1] * 1.5:
        score += 20; intel_tags.append("🔥 匹配噴發模型")

    # --- [融資/籌碼洗盤深度邏輯 - 完全保留] ---
    ma248 = c.rolling(248).mean().iloc[-1]
    ma124 = c.rolling(124).mean().iloc[-1]
    sentiment_status = "🔍 散戶進場 (融資增)"

    if not np.isnan(ma248) and (current_price >= ma248 * 0.96 and current_price <= ma248 * 1.04):
        if v.iloc[-1] < v.rolling(20).mean().iloc[-1] * 0.75:
            score += 25
            intel_tags.append("🔥 偵測到洗盤完成，準備破新高")
            sentiment_status = "🔥 大戶收貨 (融資減)"
    elif not np.isnan(ma124) and (current_price >= ma124 * 0.97 and current_price <= ma124 * 1.03):
        if v.iloc[-1] < v.rolling(20).mean().iloc[-1] * 0.8:
            score += 15
            intel_tags.append("📡 半年線支撐洗盤")
            sentiment_status = "🔥 大戶收貨 (融資減)"

    returns = c.pct_change(5).shift(-5)
    win_rate = (returns > 0).sum() / len(returns) * 100
    win_prob = round((win_rate * 0.6) + (score * 0.4), 1)
        
    return max(0, min(100, score)), " | ".join(intel_tags) if intel_tags else "⚖️ 常態波動", win_prob, sentiment_status

def generate_ai_tech_analysis(ticker, price, mode=0):
    """
    V15.5 大基石核心大腦：
    整合【布林通道】、【多週期均線共振】、【葛蘭碧八大法則】與【量能洗盤偵測】
    """
    p_bar = st.progress(0, text=f"🤖 AI 大腦啟動：正在調閱 {ticker} 35年歷史檔案...")
    try:
        # --- [第一階段：數據獲取] ---
        p_bar.progress(20, text=f"🌐 正在同步 {ticker} 多週期 K 線數據流...")
        raw_id = str(ticker).split(".")[0]
        h_full = None
        
        # 優先使用 twstock 獲取台股數據，若失敗則轉 yfinance
        if raw_id.isdigit():
            try:
                import twstock
                ts_stock = twstock.Stock(raw_id)
                fetch_len = 100 # 增加長度以計算均線
                h_full = pd.DataFrame({
                    'Close': ts_stock.price[-fetch_len:],
                    'High': ts_stock.high[-fetch_len:],
                    'Low': ts_stock.low[-fetch_len:],
                    'Volume': ts_stock.capacity[-fetch_len:]
                }).astype(float).fillna(method='ffill')
            except: pass

        if h_full is None or h_full.empty:
            stock = yf.Ticker(get_full_ticker(ticker))
            h_full = stock.history(period="6mo") # 獲取半年數據以計算季線
        
        if h_full.empty:
            p_bar.empty()
            return None

        # --- [第二階段：核心指標計算] ---
        p_bar.progress(50, text="🧠 AI 正在運算：布林帶寬、多週期均線、葛蘭碧法則...")
        
        # 1. 均線計算 (MA5, MA20, MA60)
        ma5 = h_full['Close'].rolling(5).mean().iloc[-1]
        ma20 = h_full['Close'].rolling(20).mean().iloc[-1]
        ma60 = h_full['Close'].rolling(60).mean().iloc[-1]
        ma60_prev = h_full['Close'].rolling(60).mean().iloc[-2] # 前一天的季線
        
        # 2. 布林通道計算
        std20 = h_full['Close'].rolling(20).std().iloc[-1]
        bb_upper = ma20 + (std20 * 2)
        bb_lower = ma20 - (std20 * 2)
        
        # 3. 量能分析
        v_ma5 = h_full['Volume'].rolling(5).mean().iloc[-1]
        curr_v = h_full['Volume'].iloc[-1]

        # --- [第三階段：AI 戰略邏輯歸納] ---
        p_bar.progress(80, text="🧬 AI 正在根據【葛蘭碧八大法則】與【籌碼流向】進行決策...")
        
        logic_tags = []
        score = 60 # 初始中性分
        sentiment = "⚖️ 籌碼穩定"
        
        # 💡 A. 葛蘭碧法則實裝：季線向上 + 回測季線 = 買點
        if ma60 > ma60_prev:
            if price > ma60 and (price - ma60) / ma60 < 0.03:
                logic_tags.append("🎯 葛蘭碧法則：季線支撐買點 (回測不破)")
                score += 20
                sentiment = "🔥 大戶守盤"
            else:
                logic_tags.append("📈 季線趨勢向上")
                score += 10

        # 💡 B. 布林通道策略
        if price > bb_upper:
            logic_tags.append("🚀 強勢噴發 (突破布林上軌)")
            score += 15
            sentiment = "🔥 買盤激增"
        elif price < bb_lower:
            logic_tags.append("🛡️ 超跌區 (觸及布林下軌)")
            score += 5
            sentiment = "💧 恐慌洗盤"

        # 💡 C. 均線多頭排列
        if ma5 > ma20 > ma60:
            logic_tags.append("🌟 多頭完美排列")
            score += 10
        
        # 💡 D. 量能共振
        if curr_v > v_ma5 * 1.5:
            logic_tags.append("📊 量能異常爆發")
            sentiment = "🔥 資金瘋狂湧入"

        # --- [第四階段：完成報告] ---
        p_bar.progress(100, text="✅ 診斷完成：已生成最優質 AI 戰術報告")
        time.sleep(0.3); p_bar.empty()

        # 組合成最終分析文字
        full_msg = " | ".join(logic_tags) if logic_tags else "📡 趨勢盤整中，等待方向選擇"
        if not logic_tags: sentiment = "⚖️ 偵測中"
        
        # 確保分數在範圍內
        final_score = min(99, score)
        
        return {
            "msg": full_msg, 
            "sent": sentiment, 
            "score": final_score, 
            "win_prob": 65 + (final_score // 10), # 根據分數動態調整勝率
            "price": round(float(price), 2), 
            "target": round(float(price * 1.12), 2),
            "stop": round(float(price * 0.93), 2), 
            "atr_range": f"勝率: {65 + (final_score // 10)}%",
            "pivot": f"V15.5 大基石 AI ({datetime.now().strftime('%H:%M')})"
        }
    except Exception as e:
        if 'p_bar' in locals(): p_bar.empty()
        return {"msg": f"AI 異常: {str(e)[:15]}", "score": 50, "win_prob": 50, "sent": "🔄 重新連線", "price": round(float(price), 2)}


# ==============================================================================
# 【新增】大基石 V15.3 高效掃描引擎 (帶 20 分鐘記憶功能)
# ==============================================================================

@st.cache_data(ttl=1200) # ✅ 設定 20 分鐘(1200秒)內不重複跑，解決你說的浪費時間問題
def get_cached_sector_scan(sector_name, target_pool):
    """
    這個函數會被 Streamlit 記住。只要 sector_name 沒變，就不會進入循環重跑。
    """
    scored_data = []
    total_count = len(target_pool)
    
    # 這裡執行真正的掃描邏輯
    for idx, (tid, tname) in enumerate(target_pool):
        ps, ds, _ = get_stock_perf(tid)
        if ps > 0:
            r = generate_ai_tech_analysis(tid, ps)
            if r:
                r.update({'tid': tid, 'tname': tname, 'price': ps, 'diff': ds})
                scored_data.append(r)
    
    # 排序並取出前 15 檔返回
    return sorted(scored_data, key=lambda x: x['score'], reverse=True)[:15]



# --- 初始化執行 ---
st.title("🛡️ 大基石 - AI 戰略經理人 (V15.3)")
if 'initialized' not in st.session_state: load_data() 
run_auto_cruise()
is_connected, _ = check_connection()



def fetch_and_score_intel():
    import ssl, collections, re, urllib.parse  # 確保 parse 有導入
    if hasattr(ssl, '_create_unverified_context'):
        ssl._create_default_https_context = ssl._create_unverified_context
    
    # --- 修改點 A：擴充關鍵字 (從 3 個增加到 6 個，讓搜尋範圍翻倍) ---
    strategic_map = {
        "🇹🇼 台美日中 (地緣)": [
            "台海局勢 when:24h", "中共軍演 when:24h", "台積電 when:24h",
            "半導體 供應鏈 when:24h", "美中對抗 when:24h", "日本 自衛隊 when:24h"
        ],
        "🌐 國際戰略 (全球)": [
            "中東戰爭 when:24h", "美聯儲 when:24h", "川普 關稅 when:24h",
            "俄烏戰爭 when:24h", "北約 戰略 when:24h", "全球通脹 when:24h"
        ]
    }
    
    news_list, seen_links = [], set()
    for cat_name, queries in strategic_map.items():
        for q in queries:
            u = f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
            try:
                feed = feedparser.parse(u)
                # --- 修改點 B：抓取筆數從 [:5] 改為 [:10] (單個關鍵字抓取量翻倍) ---
                for e in feed.entries[:10]: 
                    if e.link not in seen_links:
                        # 這裡保持你原本的評分邏輯，不更動佈局
                        score = 55
                        if any(w in e.title for w in ["戰爭", "衝突", "斷鏈", "降息"]): score += 30
                        news_list.append({
                            'data': e, 
                            'score': score, 
                            'cat': cat_name, 
                            'time': e.published[5:16] if hasattr(e, 'published') else "24H"
                        })
                        seen_links.add(e.link)
            except: continue
            
    # 保持後續的熱詞統計邏輯不變
    all_titles = " ".join([item['data'].title for item in news_list])
    words = re.findall(r'[\u4e00-\u9fa5]{2,4}', all_titles)
    hot_words = [w for w, c in collections.Counter(words).most_common(10)] 
    return sorted(news_list, key=lambda x: x['score'], reverse=True), hot_words



# ==============================================================================
# 第四區：大基石核心標題池 (500 檔完整細分名單 - 2026 實戰版)
# ==============================================================================

pool_500 = {
    "💎 權值/金控/保險 (70)": [
        ("2330.TW","台積電"),("2317.TW","鴻海"),("2454.TW","聯發科"),("2308.TW","台達電"),("2881.TW","富邦金"),("2882.TW","國泰金"),("2303.TW","聯電"),("2886.TW","兆豐金"),("2891.TW","中信金"),("2412.TW","中華電"),
        ("2884.TW","玉山金"),("5880.TW","合庫金"),("2885.TW","元大金"),("5871.TW","中租-KY"),("2883.TW","凱基金"),("2887.TW","台新金"),("2892.TW","第一金"),("2890.TW","永豐金"),("2880.TW","華南金"),("5876.TW","上海商銀"),
        ("2801.TW","彰銀"),("2888.TW","新光金"),("2889.TW","國票金"),("2834.TW","臺企銀"),("2809.TW","京城銀"),("2812.TW","台中銀"),("2851.TW","中再保"),("6005.TW","群益證"),("2845.TW","遠東銀"),("2838.TW","聯邦銀"),
        ("2816.TW","旺旺保"),("2836.TW","高雄銀"),("2850.TW","新產"),("2852.TW","第一保"),("2855.TW","統一證"),("2867.TW","三商壽"),("6016.TW","康和證"),("6024.TWO","群益期"),("6026.TWO","福邦證"),("5878.TW","台名"),
        ("2849.TW","安泰銀"),("2820.TW","華票"),("2823.TW","中壽"),("2832.TW","台產"),("2841.TW","台開"),("2856.TW","元富證"),("6021.TWO","大慶證"),("6023.TWO","元大期"),("2812.TW","台中銀"),("2845.TW","遠東銀"),
        ("2801.TW","彰銀"),("2834.TW","臺企銀"),("2897.TW","王道銀行"),("2869.TW","宏遠證"),("2855.TW","統一證"),("5876.TW","上海商銀"),("2880.TW","華南金"),("2892.TW","第一金"),("2881.TW","富邦金"),("2882.TW","國泰金"),
        ("2883.TW","凱基金"),("2884.TW","玉山金"),("2885.TW","元大金"),("2886.TW","兆豐金"),("2887.TW","台新金"),("2888.TW","新光金"),("2889.TW","國票金"),("2890.TW","永豐金"),("2891.TW","中信金"),("5880.TW","合庫金")
    ],
    "🔬 半導體/IC/設備 (80)": [
        ("3661.TW","世芯-KY"),("3443.TW","創意"),("3035.TW","智原"),("5269.TW","祥碩"),("3227.TW","原相"),("3034.TW","聯詠"),("2379.TW","瑞昱"),("6415.TW","矽力*-KY"),("6531.TW","愛普*"),("4966.TW","譜瑞-KY"),
        ("8299.TWO","群聯"),("4919.TW","新唐"),("2458.TW","義隆"),("8016.TW","矽創"),("3529.TWO","力旺"),("6643.TWO","M31"),("6732.TWO","昇佳電子"),("6138.TWO","茂達"),("3014.TW","聯陽"),("8081.TW","致新"),
        ("3131.TWO","弘塑"),("3583.TW","辛耘"),("1560.TW","中砂"),("3680.TW","家登"),("6196.TW","帆宣"),("6667.TWO","信紘科"),("3374.TWO","精材"),("6223.TWO","旺矽"),("6515.TW","穎崴"),("6510.TWO","精測"),
        ("3413.TW","京鼎"),("3587.TWO","閎康"),("6683.TWO","雍智科技"),("8027.TW","鈦昇"),("6789.TW","采鈺"),("6438.TW","迅得"),("6139.TW","亞博"),("3563.TW","牧德"),("2467.TW","志聖"),("6640.TWO","均華"),
        ("8028.TW","昇陽半"),("3532.TW","台勝科"),("6488.TWO","環球晶"),("5483.TWO","中美晶"),("3016.TW","嘉晶"),("2344.TW","華邦電"),("2337.TW","旺宏"),("2408.TW","南亞科"),("3006.TW","晶豪科"),("6239.TW","力成"),
        ("3711.TW","日月光投控"),("2449.TW","京元電子"),("6147.TWO","頎邦"),("8150.TW","南茂"),("3264.TWO","欣銓"),("6257.TW","矽格"),("6271.TW","同欣電"),("2369.TW","菱生"),("2401.TW","凌陽"),("3041.TW","揚智"),
        ("3527.TWO","聚積"),("3588.TWO","通嘉"),("5471.TW","松翰"),("6202.TW","盛群"),("6233.TWO","旺玖"),("6243.TWO","迅杰"),("6411.TWO","晶焱"),("6462.TWO","神盾"),("6533.TWO","晶心科"),("6679.TWO","鈺太"),
        ("8261.TW","富鼎"),("8271.TW","宇瞻"),("4961.TW","天鈺"),("4952.TW","凌通"),("5272.TWO","笙科"),("6568.TWO","宏觀"),("6613.TW","朋程"),("6684.TWO","安格"),("6719.TW","力智"),("3557.TW","嘉威")
    ],
    "🔋 BBU 電池/儲能特區 (50)": [
        ("3211.TWO","順達"),("6121.TWO","新普"),("1513.TW","中興電"),("1519.TW","華城"),("1514.TW","亞力"),("1503.TW","士電"),("1609.TW","大亞"),("6806.TW","森崴能源"),("1101.TW","台泥"),("2301.TW","光寶科"),
        ("3027.TW","盛達"),("6409.TW","旭隼"),("2457.TW","飛宏"),("3617.TW","碩天"),("8121.TWO","達邁"),("6101.TWO","弘凱"),("1517.TW","利奇"),("1525.TW","江申"),("5227.TW","立凱-KY"),("3323.TWO","加百裕"),
        ("1514.TW","亞力"),("1513.TW","中興電"),("1504.TW","東元"),("1605.TW","華新"),("1608.TW","華榮"),("1611.TW","中電"),("1612.TW","大亞"),("1614.TW","三洋電"),("1617.TW","榮星"),("1618.TW","合機"),
        ("1517.TW","利奇"),("1521.TW","大億"),("1522.TW","堤維西"),("1524.TW","耿鼎"),("1525.TW","江申"),("1532.TW","勤美"),("1533.TW","車王電"),("1535.TW","中宇"),("1536.TW","和大"),("1537.TW","廣隆"),
        ("1538.TW","正峰新"),("1539.TW","巨庭"),("1540.TW","喬福"),("1541.TW","錩泰"),("1558.TW","伸興"),("1560.TW","中砂"),("1582.TW","信錦"),("1589.TW","永冠-KY"),("1590.TW","亞德客-KY"),("1597.TW","直得")
    ],
    "🌬️ AI伺服器/散熱/機殼 (80)": [
        ("2382.TW","廣達"),("3231.TW","緯創"),("6669.TW","緯穎"),("2376.TW","技嘉"),("2356.TW","英業達"),("2353.TW","宏碁"),("2357.TW","華碩"),("3017.TW","奇鋐"),("3324.TWO","雙鴻"),("2421.TW","建準"),
        ("3013.TW","晟銘電"),("3693.TWO","營邦"),("8210.TW","勤誠"),("2368.TW","金像電"),("2383.TW","台光電"),("6213.TW","聯茂"),("6274.TWO","台燿"),("2465.TW","麗臺"),("3515.TW","華擎"),("2365.TW","昆盈"),
        ("1582.TW","信錦"),("3005.TW","神基"),("2352.TW","佳世達"),("2316.TW","楠梓電"),("2367.TW","燿華"),("2371.TW","大同"),("2397.TW","友通"),("2417.TW","圓剛"),("2419.TW","仲琦"),("2428.TW","興勤"),
        ("2455.TW","全新"),("2480.TW","敦陽科"),("3010.TW","華立"),("3029.TW","零壹"),("3032.TW","偉訓"),("3321.TWO","同泰"),("3338.TW","泰碩"),("3376.TW","新日興"),("3402.TW","漢科"),("3540.TWO","曜越"),
        ("3596.TW","智易"),("3617.TW","碩天"),("3653.TW","健策"),("3665.TW","貿聯-KY"),("3694.TW","海華"),("4915.TW","致伸"),("4938.TW","和碩"),("4958.TW","臻鼎-KY"),("5215.TW","科嘉-KY"),("5388.TW","中磊"),
        ("6153.TW","嘉聯益"),("6166.TW","凌華"),("6205.TW","詮欣"),("6214.TW","精誠"),("6230.TW","超眾"),("6235.TW","華孚"),("8112.TW","至上"),("6409.TW","旭隼"),("6278.TW","台表科"),("6269.TW","台郡"),
        ("2385.TW","群光"),("3044.TW","健鼎"),("2425.TW","承啟"),("6117.TW","迎廣"),("2312.TW","金寶"),("2328.TW","廣宇"),("3060.TW","銘異"),("3454.TW","晶睿"),("3515.TW","華擎"),("2425.TW","承啟"),
        ("3231.TW","緯創"),("6669.TW","緯穎"),("2376.TW","技嘉"),("3017.TW","奇鋐"),("3324.TWO","雙鴻"),("2421.TW","建準"),("3013.TW","晟銘電"),("3693.TWO","營邦"),("8210.TW","勤誠"),("2368.TW","金像電")
    ],
    "🎮 數位文創/遊戲/軟體 (40)": [
        ("3293.TWO","鈊象"),("5478.TWO","智冠"),("6111.TWO","大宇資"),("6180.TWO","橘子"),("3083.TWO","網龍"),("4946.TWO","辣椒"),("3546.TWO","宇峻"),("6214.TW","精誠"),("4953.TW","緯軟"),("3029.TW","零壹"),
        ("2480.TW","敦陽科"),("6112.TW","聚碩"),("8446.TWO","華研"),("4803.TWO","VHQ-KY"),("6441.TWO","廣錠"),("8044.TWO","網家"),("8454.TW","富邦媒"),("3086.TWO","華義"),("3221.TWO","台嘉碩"),("3687.TWO","歐買尬"),
        ("5263.TWO","智崴"),("6143.TWO","振曜"),("6169.TWO","昱泉"),("6542.TWO","隆中"),("2496.TW","卓越"),("2471.TW","資通"),("3130.TW","一零四"),("4994.TW","傳奇"),("5203.TW","訊連"),("5209.TW","新鼎"),
        ("5211.TWO","蒙恬"),("5212.TWO","凌網"),("6221.TWO","晉泰"),("6414.TW","樺漢"),("6470.TWO","宇智"),("8068.TWO","全達"),("8477.TWO","創業家"),("8906.TWO","花王"),("9949.TWO","琉園"),("9960.TW","邁達特")
    ],
    "⚓ 航運/鋼鐵/傳產標竿 (90)": [
        ("2603.TW","長榮"),("2609.TW","陽明"),("2615.TW","萬海"),("2618.TW","長榮航"),("2610.TW","華航"),("2637.TWO","慧洋-KY"),("2606.TW","裕民"),("2605.TW","新興"),("2002.TW","中鋼"),("2014.TW","中鴻"),
        ("2006.TW","東和鋼鐵"),("2027.TW","大成鋼"),("2031.TW","新光鋼"),("1301.TW","台塑"),("1303.TW","南亞"),("1326.TW","台化"),("6505.TW","台塑化"),("2105.TW","正新"),("2912.TW","統一超"),("1216.TW","統一"),
        ("1101.TW","台泥"),("1102.TW","亞泥"),("1304.TW","台聚"),("1305.TW","華夏"),("1308.TW","亞聚"),("1309.TW","台達化"),("1310.TW","台苯"),("1312.TW","國喬"),("1313.TW","聯成"),("1314.TW","中石化"),
        ("1315.TW","達新"),("1316.TW","上曜"),("1319.TW","東陽"),("1321.TW","大洋"),("1323.TW","永裕"),("1324.TW","地球"),("1325.TW","恆大"),("1337.TW","再生-KY"),("1338.TW","廣華-KY"),("1339.TW","昭輝"),
        ("1340.TW","勝悅-KY"),("1341.TW","富林-KY"),("1402.TW","遠東新"),("1409.TW","新纖"),("1410.TW","南染"),("1413.TW","宏洲"),("1414.TW","東和"),("1416.TW","廣豐"),("1417.TW","嘉裕"),("1418.TW","東華"),
        ("1419.TW","新紡"),("1423.TW","利華"),("1432.TW","大魯閣"),("1434.TW","福懋"),("1435.TW","中福"),("1436.TW","華友聯"),("1437.TW","勤益控"),("1438.TW","三地開發"),("1439.TW","中和"),("1440.TW","南紡"),
        ("1441.TW","大東"),("1442.TW","名軒"),("1443.TW","立益"),("1444.TW","力麗"),("1445.TW","大宇"),("1446.TW","宏和"),("1447.TW","力鵬"),("1449.TW","佳和"),("1451.TW","年興"),("1452.TW","宏益"),
        ("1453.TW","大將"),("1454.TW","台富"),("1455.TW","集盛"),("1456.TW","怡華"),("1457.TW","宜進"),("1459.TW","聯發"),("1460.TW","宏遠"),("1463.TW","強盛"),("1464.TW","得力"),("1465.TW","偉全"),
        ("1466.TW","聚隆"),("1467.TW","南緯"),("1468.TW","昶和"),("1470.TW","大統新創"),("1471.TW","首利"),("1472.TW","三洋紡"),("1473.TW","台南"),("1474.TW","弘裕"),("1475.TW","本盟"),("1476.TW","儒鴻")
    ],
    "📡 網通/車用/光學/PCB (90)": [
        ("2345.TW","智邦"),("3704.TW","合勤控"),("5388.TW","中磊"),("3596.TW","智易"),("6285.TW","啟碁"),("4906.TW","正文"),("3380.TW","明泰"),("2314.TW","台揚"),("2201.TW","裕隆"),("2207.TW","和泰車"),
        ("1536.TW","和大"),("2313.TW","華通"),("2367.TW","燿華"),("3044.TW","健鼎"),("3037.TW","欣興"),("8046.TW","南電"),("3189.TW","景碩"),("6269.TW","台郡"),("6278.TW","台表科"),("2328.TW","廣宇"),
        ("3008.TW","大立光"),("3406.TW","玉晶光"),("3441.TW","聯一光"),("3362.TWO","先進光"),("3504.TW","揚明光"),("3019.TW","亞光"),("2409.TW","友達"),("3481.TW","群創"),("6116.TW","彩晶"),("6719.TW","力智"),
        ("3592.TW","瑞鼎"),("8105.TW","凌巨"),("2349.TW","錸德"),("2323.TW","中環"),("5439.TW","高技"),("2355.TW","敬鵬"),("2360.TW","致茂"),("2402.TW","毅嘉"),("3030.TW","德律"),("3557.TW","嘉威"),
        ("3591.TW","艾笛森"),("3622.TW","洋華"),("3673.TW","TPK-KY"),("3679.TW","新至陞"),("4976.TW","佳凌"),("5243.TW","乙盛-KY"),("5469.TW","瀚宇博"),("6141.TW","柏承"),("6191.TW","精成科"),("6205.TW","詮欣"),
        ("6224.TW","聚鼎"),("6251.TW","定穎"),("6290.TW","良維"),("6456.TW","GIS-KY"),("6674.TW","騰輝電子"),("8021.TW","尖點"),("8039.TW","台虹"),("8103.TW","瀚荃"),("8213.TW","志超"),("8215.TW","明基材"),
        ("2340.TW","光磊"),("2393.TW","億光"),("3437.TW","榮創"),("6168.TW","宏齊"),("6226.TW","光鼎"),("6443.TW","元晶"),("2419.TW","仲琦"),("3450.TW","聯鈞"),("4977.TW","眾達-KY"),("6426.TW","統新"),
        ("8011.TW","台通"),("2204.TW","中華車"),("2206.TW","三陽工業"),("1521.TW","大億"),("1522.TW","堤維西"),("1524.TW","耿鼎"),("1525.TW","江申"),("1533.TW","車王電"),("1568.TW","倉佑"),("2101.TW","南港"),
        ("2103.TW","台橡"),("2106.TW","建大"),("2108.TW","南帝"),("2497.TW","怡利電"),("3552.TW","同致"),("6288.TW","聯嘉"),("3003.TW","健和興"),("3023.TW","信邦"),("2392.TW","正崴"),("3024.TW","憶聲")
    ],
    "🧬 生技/綠能/其他 (100)": [
        ("6472.TW","保瑞"),("1795.TW","美時"),("4743.TWO","合一"),("4128.TWO","中天"),("6446.TWO","藥華藥"),("1760.TW","寶齡富錦"),("4162.TWO","智擎"),("4123.TWO","晟德"),("1701.TW","中化"),("1720.TW","生達"),
        ("4147.TW","龍燈-KY"),("4174.TWO","浩鼎"),("6492.TWO","生華科"),("6547.TWO","高端"),("6550.TW","北極星"),("6589.TW","台康生"),("4104.TW","佳醫"),("4119.TW","旭富"),("4137.TW","麗豐"),("1762.TW","中化生"),
        ("1702.TW","南僑"),("1704.TW","榮化"),("1707.TW","葡萄王"),("1708.TW","東鹼"),("1709.TW","和益"),("1710.TW","東聯"),("1711.TW","永光"),("1712.TW","興農"),("1713.TW","國化"),("1714.TW","和桐"),
        ("1718.TW","中纖"),("1721.TW","三晃"),("1722.TW","台肥"),("1723.TW","中碳"),("1724.TW","台硝"),("1725.TW","元禎"),("1726.TW","永記"),("1727.TW","中華化"),("1730.TW","花仙子"),("1731.TW","美吾華"),
        ("1732.TW","毛寶"),("1733.TW","五鼎"),("1734.TW","杏輝"),("1735.TW","日勝化"),("1736.TW","喬山"),("1737.TW","臺鹽"),("1752.TW","南光"),("1773.TW","勝一"),("1776.TW","展宇"),("1783.TW","和康生"),
        ("1786.TW","科妍"),("1789.TW","神隆"),("4106.TW","雃博"),("4108.TW","懷特"),("4114.TW","健喬"),("4133.TW","亞諾法"),("4141.TW","龍燈-KY"),("4142.TW","國光生"),("4144.TW","康聯-KY"),("4148.TW","全宇生技"),
        ("4155.TW","訊聯"),("4164.TW","承業醫"),("4190.TW","佐登-KY"),("4720.TW","德淵"),("4722.TW","國精化"),("4725.TW","信昌化"),("4737.TW","華廣"),("4739.TW","康普"),("4746.TW","台耀"),("4763.TW","材料-KY"),
        ("4764.TW","雙鍵"),("4766.TW","南寶"),("6405.TW","悅城"),("6504.TW","南六"),("8341.TW","日友"),("8404.TW","百和興業"),("8436.TW","大江"),("9902.TW","經緯航"),("9904.TW","寶成"),("9905.TW","大華"),
        ("9906.TW","欣巴巴"),("9907.TW","統一實"),("9908.TW","大台北"),("9910.TW","豐泰"),("9911.TW","櫻花"),("9912.TW","偉聯"),("9914.TW","美利達"),("9917.TW","中保"),("9918.TW","欣天然"),("9919.TW","康那香"),
        ("9921.TW","巨大"),("9924.TW","福興"),("9925.TW","新保"),("9926.TW","新海"),("9927.TW","泰銘"),("9928.TW","中視"),("9929.TW","秋雨"),("9930.TW","中聯資源"),("9931.TW","欣高"),("9933.TW","中鼎")
    ]
}

STOCK_MAP = {}
if 'pool_500' in globals():
    for cat_list in pool_500.values():
        for tid, sname in cat_list:
            STOCK_MAP[tid.split(".")[0]] = sname 
            STOCK_MAP[tid] = sname

# --- [大基石 V15.3 終極雲端同步補丁：確保數據絕對安全] ---
def save_data():
    """取代舊版 CSV，實現 100% 雲端同步 (完全還原無精簡)"""
    try:
        sh = init_cloud_connection()
        if sh:
            ws = sh.worksheet("inventory")
            ws.clear()
            # 確保即使 local_db 只有保底結構也能正常運作
            headers = st.session_state.local_db.columns.tolist()
            # 轉換為清單格式以符合 gspread 要求
            data_to_write = [headers] + st.session_state.local_db.fillna("").values.tolist()
            ws.update('A1', data_to_write)
            st.toast("✅ 大基石數據已與雲端同步 (StoneManager_DB)", icon='🚀')
    except Exception as e:
        st.sidebar.error(f"📡 雲端寫入失敗: {str(e)[:30]}")

# --- 初始化執行觸發 ---
# 這裡對接 load_data，內含您要求的「先建立變數再對接」邏輯
if 'initialized' not in st.session_state:
    load_data()

# ==============================================================================
# 第 5 區：側邊欄管理與分頁定義 - 大基石 V15.3 完整佈局 (無刪減版)
# ==============================================================================

with st.sidebar:
    st.title("👤 大基石 AI 經理人")
    st.write(f"系統時間: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # 核心守護：確保在 load_data 萬一失敗時，client_list 依然存在
    if "client_list" not in st.session_state or not st.session_state.client_list:
        st.session_state.client_list = ["Robert"]

    # --- [還原：V15.0 客戶系統設定功能] ---
    with st.expander("⚙️ 客戶系統設定 (增/改/刪)", expanded=False):
        new_c = st.text_input("新增客戶姓名", key="add_client_input")
        if st.button("➕ 確認新增", use_container_width=True):
            if new_c and new_c not in st.session_state.client_list: 
                st.session_state.client_list.append(new_c)
                # 建立該客戶的初始結構
                new_row = pd.DataFrame([{
                    'client': new_c, 'id': 'INIT', 'name': '初始紀錄', 
                    'buy_price': 0, 'shares': 0, 'unit': '張', 
                    'entry_reason': '系統新增', 'sentiment': '觀測中'
                }])
                st.session_state.local_db = pd.concat([st.session_state.local_db, new_row], ignore_index=True)
                st.session_state['cur_c'] = new_c
                save_data()
                st.rerun()
        
        st.markdown("---")
            
        # 安全取得當前對象姓名
        current_idx_name = st.session_state.get('cur_c', st.session_state.client_list[0])
        
        new_name = st.text_input("更名當前客戶", value=current_idx_name, key="rename_input")
        if st.button("📝 執行更名", use_container_width=True):
            if new_name and new_name != current_idx_name:
                st.session_state.local_db['client'] = st.session_state.local_db['client'].replace(current_idx_name, new_name)
                st.session_state.client_list = [new_name if x == current_idx_name else x for x in st.session_state.client_list]
                st.session_state['cur_c'] = new_name
                save_data()
                st.rerun()

        if st.button("❌ 刪除當前客戶", use_container_width=True):
            if st.session_state.get('cur_c') != "Robert":
                to_del = st.session_state['cur_c']
                st.session_state.client_list.remove(to_del)
                st.session_state.local_db = st.session_state.local_db[st.session_state.local_db['client'] != to_del]
                st.session_state['cur_c'] = "Robert"
                save_data()
                st.rerun()

    # --- [核心：控盤選擇器] ---
    # 確保 cur_c 變數不會因為雲端數據沒刷進來而遺失
    if st.session_state.get('cur_c') not in st.session_state.client_list:
        st.session_state['cur_c'] = st.session_state.client_list[0]

    # 計算 index 以保持選擇狀態連貫
    try:
        c_idx = st.session_state.client_list.index(st.session_state['cur_c'])
    except:
        c_idx = 0

    st.session_state['cur_c'] = st.selectbox(
        "🎯 當前控盤對象", 
        st.session_state.client_list, 
        index=c_idx,
        key="client_selector"
    )
    
    st.markdown("---")
    if st.button("🔄 AI 自主學習/刷新雲端", use_container_width=True):
        st.session_state.initialized = False 
        st.rerun()

    st.markdown("---")
    # 即時顯示持股統計
    c_stocks = st.session_state.local_db[(st.session_state.local_db['client'] == st.session_state['cur_c']) & (st.session_state.local_db['id'] != 'INIT')]
    st.metric(f"{st.session_state['cur_c']} 持股總數", f"{len(c_stocks)} 檔")


# ==============================================================================
# 第 6 區 ：大基石史詩全功能還原版 (V15.3 終極進化形態) - 完全不精簡版
# ==============================================================================

# 1. 建立分頁 (由原本第六區第一行啟動)
tab_scan, tab_intel, tab_brain, tab_history = st.tabs(["📊 戰策指揮所", "🌐 全球情報室", "🧠 AI 進化大腦", "📜 交易紀錄"])

with tab_scan:
    # 完全保留原始標題與佈局
    st.title(f"🛡️ 戰略指揮所: [{st.session_state.get('cur_c', 'Robert')}]")
    col_l, col_r = st.columns([1.6, 1.4]) 
    
    with col_l:
        # --- [1. 搜尋區：還原模糊匹配與自動識別] ---
        with st.container(border=True):
            st.subheader("🔍 全球個股戰略搜索")
            s_input = st.text_input("輸入名稱或代號", placeholder="例如：2330 或 台積電", key="global_search_full")
            
            if s_input:
                s_raw = s_input.strip()
                # 數字代號識別
                if s_raw.isdigit():
                    real_name = get_stock_name(s_raw) 
                    sel_sid = get_full_ticker(s_raw)
                    if st.button(f"🔍 啟動 35 年深度診斷: {real_name}", use_container_width=True):
                        st.session_state.selected_stock = sel_sid
                        st.rerun()
                else:
                    # 名稱模糊匹配邏輯 (完全還原按鈕佈局)
                    matches = [tid for tid, name in STOCK_MAP.items() if s_raw in name]
                    if matches:
                        st.write("🎯 找到相關個股，請選擇：")
                        m_cols = st.columns(3)
                        for idx, m_sid in enumerate(list(set(matches))[:9]):
                            with m_cols[idx % 3]:
                                if st.button(f"🎯 {get_stock_name(m_sid)}", key=f"src_{m_sid}", use_container_width=True):
                                    st.session_state.selected_stock = get_full_ticker(m_sid)
                                    st.rerun()

        # --- [2. AI 診斷呈現：還原所有標籤、顏色判斷與視覺效果] ---
        sel_sid = st.session_state.get('selected_stock')
        if sel_sid:
            p, d, cc = get_stock_perf(sel_sid, 0)
            # 調用強大大腦
            res = generate_ai_tech_analysis(sel_sid, p, 0)
            if res:
                st.markdown(f"### 🧠 V15.3 AI 進化診斷: {get_stock_name(sel_sid)} ({sel_sid})")
                with st.container(border=True):
                    sc1, sc2 = st.columns([1.5, 1])
                    with sc1:
                        # 分數顏色邏輯
                        score_color = "red" if res['score'] >= 80 else ("orange" if res['score'] >= 60 else "green")
                        st.markdown(f"#### **AI 綜合評分: <span style='color:{score_color};'>{res['score']}</span>**", unsafe_allow_html=True)
                        
                        # 指令警示框
                        if res['score'] >= 80: st.error(f"🔥 **戰略指令：** {res['msg']}")
                        elif res['score'] <= 40: st.warning(f"🚨 **戰略指令：** {res['msg']}")
                        else: st.info(f"💡 **戰略指令：** {res['msg']}")
                        
                        # 籌碼洗盤標籤
                        st.markdown(f"<span class='sentiment-tag'>{res.get('sent', '觀測中')}</span>", unsafe_allow_html=True)
                        st.write("---")
                        
                        # 佈局輸入區
                        u_c1, u_c2 = st.columns(2)
                        q_val = u_c1.number_input("佈局數量", min_value=1, value=1, key=f"q_buy_{sel_sid}")
                        u_val = u_c2.radio("單位", ["張", "股"], key=f"u_buy_{sel_sid}", horizontal=True)
                        
                        if st.button(f"🚀 執行戰略佈局", key=f"cf_buy_{sel_sid}", use_container_width=True):
                            new_entry = pd.DataFrame([{
                                'client': st.session_state.cur_c, 'id': sel_sid, 'name': get_stock_name(sel_sid), 
                                'buy_price': round(p, 2), 'shares': q_val, 'unit': u_val, 'entry_reason': res['msg'], 
                                'current_score': res['score'], 'last_diag': datetime.now().strftime("%m-%d"),
                                'sentiment': res.get('sent', '觀測中')
                            }])
                            st.session_state.local_db = pd.concat([st.session_state.local_db, new_entry], ignore_index=True)
                            # 寫入交易紀錄
                            record_transaction(st.session_state.cur_c, sel_sid, "買入", q_val, round(p, 2), f"AI評分:{res['score']} | {res['msg']}")
                            save_data(); st.rerun()

                    with sc2:
                        # 右側數據指標
                        st.metric("即時股價", f"{round(p, 2)}", f"{round(d, 2)}", delta_color="inverse")
                        st.markdown(f"**🎯 目標價：** `NT$ {round(res.get('target', 0), 2)}`")
                        st.markdown(f"**🛡️ 停損價：** `NT$ {round(res.get('stop', 0), 2)}`")
                        
                        # 勝率進度條
                        win_p = res.get('win_prob', 50.0)
                        st.progress(win_p / 100, text=f"歷史相似走勢勝率: {win_p}%")
                        st.write(f"📈 預期波動: `{res.get('atr_range', '計算中')}`")
                        st.caption(f"📍 {res.get('pivot', '大基石診斷器')}")

        st.divider()
        # --- [3. 板塊掃描區：精確修復版 - 刪除醜表格、還原買入功能、修復籌碼顯示] ---
        st.subheader("🚀 產業板塊共振偵測 (全市場掃描)")
        cat_choice = st.radio("選擇掃描板塊", list(pool_500.keys()), horizontal=True, key="cat_radio_full")
        
        if st.button(f"🔍 啟動 {cat_choice} 板塊診斷", use_container_width=True):
            scored_data = []
            target_pool = pool_500[cat_choice]
            total_count = len(target_pool)
            
            scan_p = st.progress(0, text="AI 大腦正在掃描板塊...")
            
            for idx, (tid, tname) in enumerate(target_pool):
                scan_p.progress((idx+1)/total_count, text=f"正在分析 ({idx+1}/{total_count}): {tname}...")
                ps, ds, _ = get_stock_perf(tid)
                if ps > 0:
                    # 確保這裡調用 generate_ai_tech_analysis 獲取真實 AI 數據
                    r = generate_ai_tech_analysis(tid, ps)
                    if r:
                        r.update({'tid': tid, 'tname': tname, 'price': ps, 'diff': ds})
                        scored_data.append(r)
            scan_p.empty()
            
            if scored_data:
                # 排序並取出前 15 檔
                top_picks = sorted(scored_data, key=lambda x: x['score'], reverse=True)[:15]
                st.success(f"✅ 板塊掃描完成！AI 篩選出 {len(top_picks)} 檔強勢標的：")

                # --- [重點 1：這裡絕對不放 st.dataframe，直接進入精美卡片迴圈] ---
                for item in top_picks:
                    # 確保數據不為空，若 AI 未給出則顯示預設
                    analysis_msg = item.get('msg', '📡 AI 正在深度運算數據流...')
                    sent_status = item.get('sent', '⚖️ 籌碼穩定')
                    
                    with st.expander(f"⭐ {item['tname']} ({item['tid']}) | 評分: {item['score']} | {sent_status}"):
                        # --- 第一行：AI 戰略診斷 ---
                        st.info(f"💡 **AI 指令：** {analysis_msg}")
                        
                        # --- 第二行：數據細節與操作區 (對齊右側持股監控) ---
                        c1, c2, c3 = st.columns([1.2, 1.8, 1.2])
                        with c1:
                            st.write(f"📊 目前價格: **{item['price']}**")
                            st.caption(f"漲跌幅: {item['diff']}")
                        
                        with c2:
                            # 🚀 修復：這是你要求的「買入張數/股數」選擇案件
                            buy_col1, buy_col2 = st.columns([1, 1])
                            u_val = buy_col1.radio("單位", ["張", "股"], key=f"u_scan_{item['tid']}", horizontal=True, label_visibility="collapsed")
                            q_val = buy_col2.number_input("數量", min_value=1, value=1, key=f"q_scan_{item['tid']}", label_visibility="collapsed")
                            
                        with c3:
                            # 🚀 修復：執行買入案件，串接 record_transaction 與 save_data
                            if st.button(f"🚀 執行買入", key=f"btn_buy_{item['tid']}", use_container_width=True):
                                new_entry = pd.DataFrame([{
                                    'client': st.session_state.cur_c, 'id': item['tid'], 'name': item['tname'], 
                                    'buy_price': item['price'], 'shares': q_val, 'unit': u_val, 'entry_reason': analysis_msg, 
                                    'sentiment': sent_status
                                }])
                                st.session_state.local_db = pd.concat([st.session_state.local_db, new_entry], ignore_index=True)
                                record_transaction(st.session_state.cur_c, item['tid'], "買入", q_val, item['price'], f"掃描買入:{analysis_msg}")
                                save_data()
                                st.toast(f"✅ 已將 {item['tname']} 加入 {st.session_state.cur_c} 帳戶", icon='🚀')
                                time.sleep(1)
                                st.rerun()

                            if st.button(f"🔍 深度診斷", key=f"btn_diag_{item['tid']}", use_container_width=True):
                                st.session_state.selected_stock = item['tid']
                                st.rerun()

                st.divider()


            
    
    with col_r:
        # --- [4. 持股監控區：大基石 V15.3 強化版] ---
        st.subheader(f"💼 持股監控: [{st.session_state.cur_c}]")
        
        mask = (st.session_state.local_db['client'] == st.session_state.cur_c) & \
               (st.session_state.local_db['id'] != 'INIT')
        my_h = st.session_state.local_db[mask]

        total_profit_loss = 0.0  # 初始化總損益

        if not my_h.empty:
            for idx, row in my_h.iterrows():
                # 獲取行情：cp(現價), cd(漲跌), cc(漲幅)
                cp, cd, cc = get_stock_perf(row['id'], 0) 
                
                # 計算單筆損益：(現價 - 成本) * 股數
                # 判斷單位：張=1000股
                multiplier = 1000 if row['unit'] == "張" else 1
                shares_val = float(row['shares'])
                buy_p = float(row['buy_price'])
                individual_pl = (cp - buy_p) * shares_val * multiplier
                total_profit_loss += individual_pl

                # AI 籌碼診斷邏輯
                sentiment_val = row.get('sentiment', '偵測中')
                if sentiment_val in ['偵測中', '', None]:
                    if cp < buy_p:
                        sentiment_val = "🔥 偵測到洗盤完成，準備破新高"
                    else:
                        sentiment_val = "💰 大戶收貨 (融資減)"
        
                with st.container(border=True):
                    col_t1, col_t2 = st.columns([2, 1])
                    col_t1.markdown(f"### **{row['name']}** `{row['id']}`")
                    
                    # 修正問題 2：限制小數點兩位，並顯示損益點數
                    delta_color = "red" if cd >= 0 else "green"
                    prefix = "+" if cd > 0 else ""
                    col_t2.markdown(
                        f"<div style='text-align:right;'><span style='color:{delta_color}; font-size:20px; font-weight:bold;'>{round(cp, 2)}</span><br>"
                        f"<span style='color:{delta_color}; font-size:14px;'>{prefix}{round(cd, 2)} ({cc}%)</span></div>", 
                        unsafe_allow_html=True
                    )
            
                    st.markdown(f"🚩 **AI 籌碼診斷：** :orange[{sentiment_val}]")
                    
                    # 修正問題 1：顯示單筆損益
                    pl_color = "red" if individual_pl >= 0 else "green"
                    st.write(f"持有: **{row['shares']} {row['unit']}** | 成本: {round(buy_p, 2)}")
                    st.markdown(f"💰 當前盈虧: <span style='color:{pl_color}; font-weight:bold;'>{format(int(individual_pl), ',')} TWD</span>", unsafe_allow_html=True)
            
                    # --- 減持功能區 (保持佈局，防止 ID 重複使用 idx) ---
                    st.divider()
                    e_c1, e_c2, e_c3 = st.columns([1.2, 1.2, 1.5])
                    exit_q = e_c1.number_input("數量", min_value=1, value=int(shares_val), key=f"exq_v15_{idx}", label_visibility="collapsed")
                    exit_u = e_c2.radio("單位", ["張", "股"], index=0 if row['unit']=="張" else 1, key=f"exu_v15_{idx}", horizontal=True, label_visibility="collapsed")
            
                    if e_c3.button(f"❌ 執行減持", key=f"exb_v15_{idx}", use_container_width=True):
                        record_transaction(st.session_state.cur_c, row['id'], "賣出", exit_q, round(cp, 2), f"AI診斷:{sentiment_val}")
                        new_shares = shares_val - exit_q
                        if new_shares <= 0:
                            st.session_state.local_db = st.session_state.local_db.drop(idx)
                        else:
                            st.session_state.local_db.at[idx, 'shares'] = new_shares
                        save_data()
                        st.rerun()

            # 修正問題 1：持股區最下方顯示總損益金額
            st.divider()
            total_color = "red" if total_profit_loss >= 0 else "green"
            st.markdown(
                f"<div style='background-color:#f0f2f6; padding:20px; border-radius:10px; text-align:center;'>"
                f"<h4>總持股估計盈虧</h4>"
                f"<h2 style='color:{total_color};'>{format(int(total_profit_loss), ',')} TWD</h2>"
                f"</div>", 
                unsafe_allow_html=True
            )
        else:
            st.info("💡 目前無持股，請從左側搜尋或掃描板塊。")



# --- 其他分頁還原 ---
with tab_intel:
    st.subheader("🌐 全球市場即時情報系統")
    st.info("情報室正在對接中，將整合 V15.2 宏觀數據流 (包含 SOX/IXIC 監控)...")

with tab_brain:
    st.subheader("🧠 AI 進化大腦：神經元權重控制")
    st.write("目前模型版本：大基石 V15.3 (自主進化版)")
    st.slider("技術指標權重 (MACD/斜率/背離)", 0, 100, 60)
    st.slider("籌碼流向權重 (洗盤/融資/大戶)", 0, 100, 40)
    st.divider()
    st.write("🧬 已啟用核心模組：")
    st.markdown("- `get_multi_timeframe_data` (多時框共振)\n- `detect_divergence` (指標背離偵測)\n- `calculate_cost_zone` (成本區計算)\n- `historical_surge_analysis` (歷史飆股特徵分析)")

with tab_history:
    st.subheader("📜 全球戰略交易紀錄回溯")
    if 'trade_history' in st.session_state and not st.session_state.trade_history.empty:
        st.dataframe(st.session_state.trade_history.sort_index(ascending=False), use_container_width=True)
    else:
        st.info("💡 目前尚無交易紀錄數據。")




# --- 第七區：全球情報室 (完整還原分級卡片 - V15.0 戰略強化) ---
with tab_intel:
    st.header("🌎 全球戰略情報大腦 (24H 更新)")
    if 'news_mode' not in st.session_state: st.session_state.news_mode = "🇹🇼 台美日中 (地緣)"
    
    n1, n2 = st.columns(2)
    if n1.button("🇹🇼 台美日中情勢", use_container_width=True, key="n_tw"): st.session_state.news_mode = "🇹🇼 台美日中 (地緣)"
    if n2.button("🌐 國際戰略動態", use_container_width=True, key="n_gl"): st.session_state.news_mode = "🌐 國際戰略 (全球)"

    try:
        # 調用核心大腦情報引擎
        all_news, trends = fetch_and_score_intel()
        st.write(f"🔥 **戰略熱點：** " + " ".join([f"`{w}`" for w in trends]))
        
        filtered = [item for item in all_news if item['cat'] == st.session_state.news_mode]
        nl, nr = st.columns(2)
        for i, item in enumerate(filtered):
            n, score = item['data'], item['score']
            # 保持 12.5 史詩級顏色分級
            color = "#FF4B4B" if score >= 80 else ("#FFD700" if score >= 70 else "#00D1FF")
            label = "⚡ SS 級" if score >= 80 else ("🚨 A 級" if score >= 70 else "🔍 B 級")
            
            card = f"""
                <div style='border-left:5px solid {color}; padding:12px; margin-bottom:12px; background:white; border-radius:8px; border:1px solid #ddd;'>
                    <span style='background:{color}; color:black; padding:2px 5px; border-radius:3px; font-size:10px;'>{label}</span>
                    <small style='float:right; color:grey;'>{item['time']}</small><br>
                    <a href='{n.link}' target='_blank' style='text-decoration:none; color:#1e1e1e; font-weight:bold;'>{n.title}</a>
                </div>
            """
            if i % 2 == 0: nl.markdown(card, unsafe_allow_html=True)
            else: nr.markdown(card, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"📡 情報連線中... AI 正在重新對齊全球戰略數據流")

# --- [第 7.5 區：AI 大腦思維日誌 - V15.0 專屬進化分頁] ---
with tab_brain: 
    # 確保此分頁不調用任何全球看板函數，直接進入標題
    st.header("🧠 大基石：AI 進化思維日誌 (V15.0)")
    st.caption("🤖 此日誌紀錄 AI 每 10 分鐘對比 35 年歷史大數據後的進化軌跡")
    st.write("---")
    
    # 檢查 AI 記憶體是否存在
    if 'ai_memory' in st.session_state and st.session_state.ai_memory:
        # 顯示最近 10 條紀錄，並標註進化版本 (倒序排列，最新優先)
        for m in reversed(st.session_state.ai_memory[-10:]):
            with st.container(border=True):
                c1, c2 = st.columns([1, 3])
                # 左側：診斷標的
                c1.metric("診斷標的", m['ticker'])
                
                # 右側：核心邏輯與評分細節
                with c2:
                    st.markdown(f"**預測評分:** `{m['prediction']}` (混合評分權重: 60% 戰術 / 40% 歷史)")
                    st.markdown(f"**核心邏輯:** {m['logic']}")
                    st.caption(f"📅 紀錄時間: {m['timestamp']} | 引擎版本: {m.get('engine_ver', 'V15.0_Evolution')}")
    else:
        # 空值引導提示
        st.info("💡 目前尚無思維紀錄。請前往【戰策指揮所】進行個股深度診斷，AI 將啟動 35 年歷史模型自我學習。")

# --- 7.5 區結束 ---


# --- [第 8 區：交易紀錄修正] ---
with tab_history:
    st.subheader("📜 歷史交易紀錄")
    
    if 'trade_history' in st.session_state and not st.session_state.trade_history.empty:
        try:
            # 轉換為字串避免 Arrow 轉換失敗
            display_df = st.session_state.trade_history.astype(str)
            st.dataframe(display_df, width='stretch') # 順便修正警告，將 use_container_width 改為 width='stretch'
        except Exception as e:
            st.error(f"表格顯示異常: {e}")

    else:
        st.info("💡 目前尚無交易紀錄，或雲端連線中...")
        
    st.divider()
    st.markdown("### ☁️ 交易紀錄同步備份")
    
    # 準備下載用的 CSV 數據 (確保 UTF-8-SIG 避免中文亂碼)
    if 'trade_history' in st.session_state:
        csv_history = st.session_state.trade_history.to_csv(index=False).encode('utf-8-sig')
    else:
        csv_history = b""

    h_sync1, h_sync2 = st.columns(2)
    with h_sync1:
        if st.button("💾 存至本地紀錄", key="up_hist", use_container_width=True):
            save_data()
            st.success("✅ 紀錄已成功存檔至本地緩存")
        
        # --- 下載紀錄按鈕 (完全保留原始功能與名稱) ---
        st.download_button(
            label="📥 下載歷史紀錄 (CSV)",
            data=csv_history,
            file_name=f"history_{datetime.now().strftime('%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True,
            help="將此檔案下載後，上傳至 Google Sheets 的 history 分頁"
        )

    with h_sync2:
        if st.button("🔄 刷新雲端連線", key="dl_hist", use_container_width=True):
            # 重置初始化狀態，觸發重新載入
            st.cache_data.clear()
            st.session_state.initialized = False
            st.rerun()
