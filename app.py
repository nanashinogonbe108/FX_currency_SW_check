import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="FX Backtest & Monitor", layout="wide")

# 1. 通貨の優先順位定義（金融業界標準の並び順）
PRIORITY = ["EUR", "GBP", "AUD", "NZD", "USD", "CAD", "CHF", "JPY"]
CURRENCIES = ["USD", "EUR", "JPY", "GBP", "AUD", "CAD", "CHF", "NZD"]

def get_proper_symbol(c1, c2):
    """金融商品の標準的な並び（例：AUDUSD）に変換する"""
    idx1 = PRIORITY.index(c1)
    idx2 = PRIORITY.index(c2)
    if idx1 < idx2:
        return f"{c1}{c2}=X", False # 正順（反転なし）
    else:
        return f"{c2}{c1}=X", True  # 逆順（反転が必要）

def get_strength_data():
    """通貨強弱を計算"""
    symbols = [f"{c}USD=X" if c != "USD" else "" for c in CURRENCIES]
    symbols = [s for s in symbols if s]
    raw_data = yf.download(symbols, period="2d", interval="15m", progress=False)
    if raw_data.empty: return pd.Series()
    close_data = raw_data['Close']
    returns = (close_data.iloc[-1] / close_data.iloc[0]) - 1
    strengths = {c: 0.0 for c in CURRENCIES}
    for col in returns.index:
        base = col[:3]
        strengths[base] += returns[col]
        strengths["USD"] -= returns[col]
    return pd.Series(strengths).sort_values(ascending=False)

def run_backtest(df, rr_ratio):
    """簡易バックテスト: 過去データに対してロジックを適用"""
    df = df.copy()
    df['MA_S'] = df['Close'].rolling(window=10).mean()
    df['MA_M'] = df['Close'].rolling(window=25).mean()
    df['MA_L'] = df['Close'].rolling(window=50).mean()
    df = df.dropna()
    
    balance = 0
    history = []
    
    for i in range(1, len(df)):
        prev = df.iloc[i-1]
        curr = df.iloc[i]
        
        # パーフェクトオーダー成立（買い）
        if curr['MA_S'] > curr['MA_M'] > curr['MA_L'] and not (prev['MA_S'] > prev['MA_M'] > prev['MA_L']):
            # 簡易的に次の足の終値で損益計算（実際はTP/SLまで待つが、ここでは20本後の結果を見る）
            if i + 20 < len(df):
                profit = df['Close'].iloc[i+20] - curr['Close']
                balance += 1 if profit > 0 else -rr_ratio
                history.append(balance)
                
    return history

# --- メイン処理 ---
st.title("📊 FX バックテスト & リアルタイム監視")

try:
    strength_series = get_strength_data()
    if not strength_series.empty:
        c1, c2 = strength_series.index[0], strength_series.index[-1]
        
        # 表示順の固定化
        symbol, is_inverted = get_proper_symbol(c1, c2)
        display_name = symbol.replace("=X", "")
        
        st.info(f"現在の最強: {c1} / 最弱: {c2} → 取引対象: **{display_name}**")

        # データ取得 (バックテスト用に期間を長めに取得)
        chart_df = yf.download(symbol, period="5d", interval="15m", progress=False)
        if isinstance(chart_df.columns, pd.MultiIndex): chart_df.columns = chart_df.columns.get_level_values(0)

        # MA計算
        chart_df['MA_S'] = chart_df['Close'].rolling(window=10).mean()
        chart_df['MA_M'] = chart_df['Close'].rolling(window=25).mean()
        chart_df['MA_L'] = chart_df['Close'].rolling(window=50).mean()

        # レイアウト
        tab1, tab2 = st.tabs(["リアルタイム監視", "簡易バックテスト"])

        with tab1:
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=chart_df.index, open=chart_df['Open'], high=chart_df['High'], low=chart_df['Low'], close=chart_df['Close'], name="Price"))
            fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['MA_S'], name="Short", line=dict(color='yellow')))
            fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['MA_L'], name="Long", line=dict(color='red')))
            fig.update_layout(xaxis_rangeslider_visible=False, height=500, template="plotly_dark", title=f"{display_name} チャート")
            st.plotly_chart(fig, use_container_width=True)
            st.bar_chart(strength_series)

        with tab2:
            st.subheader(f"{display_name} 過去5日間のロジック検証")
            bt_history = run_backtest(chart_df, 0.5)
            if bt_history:
                st.line_chart(bt_history)
                st.write(f"試行回数: {len(bt_history)} 回")
                st.write("※20本後の価格で簡易決済した際の累積損益推移")
            else:
                st.write("期間内にシグナルは発生しませんでした。")

    time.sleep(60)
    st.rerun()
except Exception as e:
    st.error(f"Error: {e}")
    time.sleep(10)
    st.rerun()