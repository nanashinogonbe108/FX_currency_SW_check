import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import time

# ページ設定
st.set_page_config(page_title="FX Monitor 2026", layout="wide")

# --- 定数 ---
BRIGHT_COLORS = ["#FF0055", "#FF5500", "#FFCC00", "#AAEE00", "#00CCFF", "#5588FF", "#8855FF", "#444444"]
CURRENCIES = ["USD", "EUR", "JPY", "GBP", "AUD", "CAD", "CHF", "NZD"]

# --- データ取得関数 ---
def get_strength_safe(interval):
    try:
        symbols = [f"{c}USD=X" if c != "USD" else "" for c in CURRENCIES]
        symbols = [s for s in symbols if s]
        # 1分足は1日分しか取れないための制限
        period = "1d" if interval == "1m" else "5d"
        df = yf.download(symbols, period=period, interval=interval, progress=False)
        
        if df.empty or 'Close' not in df:
            return None
        
        returns = (df['Close'].iloc[-1] / df['Close'].iloc[0]) - 1
        strengths = {c: 0.0 for c in CURRENCIES}
        for col in returns.index:
            base = col[:3]
            strengths[base] += returns[col]
            strengths["USD"] -= returns[col]
        return pd.Series(strengths).sort_values(ascending=False)
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
        return None

# --- メイン UI ---
st.title("⚡ FX Real-time Matrix")

interval = st.sidebar.selectbox("時間足", ["1m", "5m", "15m", "1h"], index=0)

data = get_strength_safe(interval)

if data is not None:
    # --- 通貨ブロック ---
    sorted_curr = data.index.tolist()
    blocks_html = ""
    for i, currency in enumerate(sorted_curr):
        bg = BRIGHT_COLORS[i] if i < len(BRIGHT_COLORS) else "#333"
        sep = "<span style='color: white; font-size: 2em; margin: 0 10px;'>&gt;</span>" if i < len(sorted_curr)-1 else ""
        blocks_html += f"""
        <div style="display: inline-block; text-align: center; vertical-align: middle;">
            <div style="background-color: {bg}; color: white; font-weight: 900; font-size: 1.5em; padding: 15px 25px; border-radius: 12px; min-width: 100px; border: 2px solid rgba(255,255,255,0.3);">{currency}</div>
        </div>{sep}"""

    st.markdown(f"<div style='background-color: #000; padding: 30px; border-radius: 20px; text-align: center; overflow-x: auto; white-space: nowrap;'>{blocks_html}</div>", unsafe_allow_html=True)

    # --- チャート (最新の width='stretch' を使用) ---
    pair = f"{sorted_curr[0]}{sorted_curr[-1]}=X"
    df_c = yf.download(pair, period="1d", interval=interval, progress=False)
    if not df_c.empty:
        if isinstance(df_c.columns, pd.MultiIndex): df_c.columns = df_c.columns.get_level_values(0)
        fig = go.Figure(data=[go.Candlestick(x=df_c.index, open=df_c['Open'], high=df_c['High'], low=df_c['Low'], close=df_c['Close'])])
        fig.update_layout(template="plotly_dark", height=450, xaxis_rangeslider_visible=False)
        # 2026年仕様: use_container_width=True ではなく width='stretch'
        st.plotly_chart(fig, width='stretch')
else:
    st.warning("市場データが取得できません。週末や閉場時間の可能性があります。")

# 自動更新
time.sleep(60)
st.rerun()