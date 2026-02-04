import streamlit as st
import yfinance as yf
import pandas as pd
import time

# --- ページ設定 ---
st.set_page_config(page_title="FX Strength Dashboard", layout="wide")

# --- 定数 ---
# 強い順のカラー（赤→青）
BRIGHT_COLORS = ["#FF0055", "#FF5500", "#FFCC00", "#AAEE00", "#00CCFF", "#5588FF", "#8855FF", "#444444"]
CURRENCIES = ["USD", "EUR", "JPY", "GBP", "AUD", "CAD", "CHF", "NZD"]

# --- データ取得関数 ---
@st.cache_data(ttl=60) # 60秒間キャッシュ（連打対策）
def get_strength_optimized(interval, lookback):
    """
    interval: 時間足 (1m, 5m, 1h...)
    lookback: 過去何本分のローソク足を見て強弱を決めるか
    """
    symbols = [f"{c}USD=X" if c != "USD" else "" for c in CURRENCIES]
    symbols = [s for s in symbols if s]
    
    # 必要な期間だけを計算して取得（データ量を減らして高速化）
    # 1分足なら直近90分、1時間足なら直近5日分など
    if interval == "1m":
        period = "1d"
    elif interval in ["5m", "15m"]:
        period = "5d"
    else:
        period = "1mo"

    try:
        df = yf.download(symbols, period=period, interval=interval, progress=False)
        
        if df.empty or 'Close' not in df:
            return None
        
        # 【修正点】 指定した「直近N本」の変動率を見る
        # これにより「1分足を選んだら、直近数分の勢い」が反映される
        close_data = df['Close'].tail(lookback) 
        
        if len(close_data) < 2:
            return None

        # (最新価格 - N本前の価格) / N本前の価格
        returns = (close_data.iloc[-1] / close_data.iloc[0]) - 1
        
        strengths = {c: 0.0 for c in CURRENCIES}
        for col in returns.index:
            base = col[:3]
            strengths[base] += returns[col]
            strengths["USD"] -= returns[col]
            
        return pd.Series(strengths).sort_values(ascending=False)
        
    except Exception:
        return None

# --- メイン UI ---
st.title("⚡ FX Multi-Timeframe Matrix")

# 設定エリア
col_conf1, col_conf2 = st.columns(2)
with col_conf1:
    # 時間足の選択
    interval_map = {
        "1分足 (スキャルピング)": "1m",
        "5分足 (デイトレ短期)": "5m",
        "1時間足 (デイトレ・スイング)": "1h",
        "日足 (長期トレンド)": "1d"
    }
    selected_label = st.selectbox("分析する時間足", list(interval_map.keys()), index=1)
    interval = interval_map[selected_label]

with col_conf2:
    # 比較期間（キャンドル本数）
    lookback = st.slider("判定期間 (過去何本分のローソク足で比較するか)", 5, 50, 20)

st.divider()

# データ処理
data = get_strength_optimized(interval, lookback)

if data is not None:
    sorted_curr = data.index.tolist()
    
    # --- 1. パワーバランス表示 ---
    st.subheader(f"📊 通貨強弱 ({selected_label} / 直近{lookback}本)")
    
    blocks_html = ""
    for i, currency in enumerate(sorted_curr):
        bg = BRIGHT_COLORS[i] if i < len(BRIGHT_COLORS) else "#333"
        sep = "<span style='color: white; font-size: 2em; margin: 0 10px;'>&gt;</span>" if i < len(sorted_curr)-1 else ""
        blocks_html += f"""
        <div style="display: inline-block; text-align: center; vertical-align: middle;">
            <div style="background-color: {bg}; color: white; font-weight: 900; font-size: 1.5em; padding: 15px 25px; border-radius: 12px; min-width: 100px; border: 2px solid rgba(255,255,255,0.3);">{currency}</div>
        </div>{sep}"""
    
    st.markdown(f"<div style='background-color: #000; padding: 30px; border-radius: 20px; text-align: center; overflow-x: auto; white-space: nowrap; margin-bottom: 20px;'>{blocks_html}</div>", unsafe_allow_html=True)

    # --- 2. トレード推奨カード ---
    c_strong, c_weak = sorted_curr[0], sorted_curr[-1]
    
    # ペア名の特定
    PRIORITY = ["EUR", "GBP", "AUD", "NZD", "USD", "CAD", "CHF", "JPY"]
    idx1, idx2 = PRIORITY.index(c_strong), PRIORITY.index(c_weak)
    
    if idx1 < idx2:
        pair_display = f"{c_strong}/{c_weak}"
        pair_symbol = f"{c_strong}{c_weak}=X"
        action = "LONG (買い)"
        color = "red" # 強い色が左に来る場合
    else:
        pair_display = f"{c_weak}/{c_strong}"
        pair_symbol = f"{c_weak}{c_strong}=X"
        action = "SHORT (売り)" # 強い通貨が右（分母）に来るため、チャートは下がる
        color = "blue"

    # Yahoo Finance URL
    yf_url = f"https://finance.yahoo.com/quote/{pair_symbol}/chart"

    # カード表示
    st.info(f"💡 分析結果: **{c_strong}** が最強、**{c_weak}** が最弱です。")
    
    col_res1, col_res2 = st.columns([2, 1])
    
    with col_res1:
        st.markdown(f"""
        ### 🎯 Target: {pair_display}
        **戦略**: <span style='color:{color}; font-size:1.2em; font-weight:bold;'>{action}</span>
        """, unsafe_allow_html=True)
    
    with col_res2:
        st.markdown("<br>", unsafe_allow_html=True) # 余白調整
        # 外部リンクボタン
        st.link_button(f"📈 {pair_display} のチャートを見る (Yahoo Finance)", yf_url, type="primary")

else:
    st.warning("データ取得中、または市場休場中です。しばらく待ってからリロードしてください。")

# 自動更新ボタン（手動）
if st.button("データ更新"):
    st.cache_data.clear()
    st.rerun()