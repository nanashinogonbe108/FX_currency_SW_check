import yfinance as yf
import pandas as pd

# 8通貨の定義
currencies = ["USD", "EUR", "JPY", "GBP", "AUD", "CAD", "CHF", "NZD"]

def get_currency_strength():
    data = {}
    # 主要28ペアの直近24時間の変化率を取得（簡易版）
    # 本来は全組み合わせをループして計算します
    # 例: EURUSD=X, USDJPY=X ...
    
    strengths = {c: 0.0 for c in currencies}
    
    for base in currencies:
        for quote in currencies:
            if base == quote: continue
            symbol = f"{base}{quote}=X"
            try:
                # 1日分のデータを取得して変化率を計算
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="1d", interval="1m")
                if not hist.empty:
                    change = (hist['Close'].iloc[-1] - hist['Open'].iloc[0]) / hist['Open'].iloc[0]
                    strengths[base] += change
                    strengths[quote] -= change
            except:
                continue

    return pd.Series(strengths).sort_values(ascending=False)

# 実行
print("--- 現在の通貨強弱ランキング ---")
print(get_currency_strength())