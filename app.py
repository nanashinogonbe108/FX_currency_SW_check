import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ページ設定
st.set_page_config(page_title="FX Professional Monitor", layout="wide")

# --- 1. 定数とユーティリティ関数 ---
PRIORITY = ["EUR", "GBP", "AUD", "NZD", "USD", "CAD", "CHF", "JPY"]
CURRENCIES = ["USD", "EUR", "JPY", "GBP", "AUD", "CAD", "CHF", "NZD"]

def get_proper_symbol(c1, c2):
    """金融業界標準の通貨ペア順に変換"""
    idx1, idx2 = PRIORITY.index(c1), PRIORITY.index(c2)
    return (f"{c1}{c2}=X", False) if idx1 < idx2 else (f"{c2}{c1}=X", True)

def calculate_atr(df, period=14):
    """ATR (Average True Range) の計算"""
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    return true_range.rolling(window=period).mean()

@st.cache_data(ttl=300)
def get_strength_data():
    """全通貨の強弱スコアを計算"""
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

# --- 2. バックテストロジック ---
def run_advanced_backtest(df, risk_reward=2.0):
    """ATRを用いた動的TP/SLバックテスト"""
    df = df.copy()
    df['MA_S'] = df['Close'].rolling(window=10).mean()
    df['MA_M'] = df['Close'].rolling(window=25).mean()
    df['MA_L'] = df['Close'].rolling(window=50).mean()
    df['ATR'] = calculate_atr(df)
    df = df.dropna()
    
    history = []
    balance = 0
    in_position = False
    entry_price = 0
    tp_price, sl_price = 0, 0

    for i in range(1, len(df)):
        curr = df.iloc[i]
        prev = df.iloc[i-1]

        if not in_position:
            # エントリー: パーフェクトオーダーの初動
            is_perfect = curr['MA_S'] > curr['MA_M'] > curr['MA_L']
            was_not_perfect = not (prev['MA_S'] > prev['MA_M'] > prev['MA_L'])
            
            if is_perfect and was_not_perfect:
                in_position = True
                entry_price = curr['Close']
                # TP/SLの計算
                tp_price = entry_price + (curr['ATR'] * risk_reward)
                sl_price = entry_price - (curr['ATR'] * 1.0)
        else:
            # 決済判定
            if curr['High'] >= tp_price:
                balance += (tp_price - entry_price)
                history.append(balance)
                in_position = False
            elif curr['Low'] <= sl_price:
                balance += (sl_price - entry_price)
                history.append(balance)
                in_position = False
    return history

# --- 3. メイン UI ---
st.title("📈 FX Advanced Expansion Monitor")

try:
    # 1. 通貨強弱の取得
    strength_series = get_strength_data()
    if strength_series.empty:
        st.warning("強弱データの取得に失敗しました。")
        st.stop()

    c_top, c_bot = strength_series.index[0], strength_series.index[-1]
    symbol, is_inverted = get_proper_symbol(c_top, c_bot)
    display_name = symbol.replace("=X", "")

    # 2. サイドバー設定
    st.sidebar.header("🔧 設定")
    period_options = {"5日間": "5d", "1ヶ月": "1mo", "60日間(最大)": "60d"}
    selected_label = st.sidebar.selectbox("検証期間", list(period_options.keys()), index=1)
    selected_period = period_options[selected_label]
    
    # 3. データ取得
    df = yf.download(symbol, period=selected_period, interval="15m", progress=False)
    if isinstance(df.columns, pd.MultiIndex): 
        df.columns = df.columns.get_level_values(0)

    if df.empty:
        st.error("チャートデータを取得できませんでした。")
    else:
        st.success(f"🔥 最強: {c_top} / 🧊 最弱: {c_bot} → 取引ペア: **{display_name}**")
        
        # タブの作成
        tab1, tab2 = st.tabs(["ライブチャート", "ATRバックテスト"])

        with tab1:
            # 移動平均の再計算（表示用）
            df['MA_S'] = df['Close'].rolling(window=10).mean()
            df['MA_M'] = df['Close'].rolling(window=25).mean()
            df['MA_L'] = df['Close'].rolling(window=50).mean()
            
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="価格"))
            colors = {'MA_S': 'yellow', 'MA_M': 'orange', 'MA_L': 'red'}
            for ma in ['MA_S', 'MA_M', 'MA_L']:
                fig.add_trace(go.Scatter(x=df.index, y=df[ma], name=ma, line=dict(width=1.5, color=colors[ma])))
            
            fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False, title=f"{display_name} 15分足")
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            st.subheader(f"{display_name} ロジック検証結果")
            rr = st.slider("リスクリワード比率 (SL 1に対し TP何倍か)", 1.0, 5.0, 2.0)
            bt_history = run_advanced_backtest(df, rr)
            
            if bt_history:
                st.line_chart(bt_history)
                st.metric("累積損益 (pips近似)", f"{bt_history[-1]:.4f}")
                st.write(f"期間内のトレード回数: {len(bt_history)} 回")
            else:
                st.info("この期間中に条件（MAの拡散）を満たすエントリーはありませんでした。")

except Exception as e:
    st.error(f"実行中にエラーが発生しました: {e}")

st.divider()
st.caption("※yfinanceから取得した15分足データを使用しています。週末はデータが更新されません。")