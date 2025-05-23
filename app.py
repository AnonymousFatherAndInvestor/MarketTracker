from flask import Flask, render_template, request
import yfinance as yf
import pandas as pd
from cachetools import TTLCache
from config import CATEGORIES, TICKERS, REFRESH_INTERVAL
from plotly.offline import plot
import plotly.graph_objects as go

app = Flask(__name__)

PERIODS = ["1d", "5d", "1mo", "6mo", "1y", "ytd", "5y", "max"]

cache = TTLCache(maxsize=128, ttl=REFRESH_INTERVAL)

def fetch_ticker(ticker: str, period: str):
    key = (ticker, period)
    if key in cache:
        return cache[key]
    df = yf.download(ticker, period=period, interval="1d")
    if df.empty:
        cache[key] = None
        return None
    close = df["Close"].fillna(method="ffill")
    cache[key] = close
    return close

@app.route("/")
def index():
    period = request.args.get("period", "1mo")
    if period not in PERIODS:
        period = "1mo"

    summary_charts = {}
    ticker_cards = {}

    for category, tickers in CATEGORIES.items():
        series_list = []
        cards = []
        for ticker, name in tickers.items():
            close = fetch_ticker(ticker, period)
            if close is None or len(close) < 2:
                continue
            close = close.ffill()
            first, last = close.iloc[0], close.iloc[-1]
            change = (last - first) / first * 100

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=close.index, y=close.values, name=name, line=dict(width=2)))
            fig.update_layout(width=350, height=200, margin=dict(l=30, r=10, t=10, b=30), showlegend=False)
            chart_html = plot(fig, include_plotlyjs=False, output_type="div")

            cards.append({
                "ticker": ticker,
                "name": name,
                "close": f"{last:.2f}",
                "change": f"{change:.2f}",
                "chart": chart_html,
            })
            series_list.append(close.rename(name))
        ticker_cards[category] = cards

        if series_list:
            combined = pd.concat(series_list, axis=1).ffill()
            norm = combined / combined.iloc[0] * 100
            fig = go.Figure()
            for col in norm.columns:
                fig.add_trace(go.Scatter(x=norm.index, y=norm[col], name=col))
            fig.update_layout(width=600, height=300, margin=dict(l=40, r=20, t=30, b=40), legend=dict(orientation="h"))
            summary_charts[category] = plot(fig, include_plotlyjs=False, output_type="div")
        else:
            summary_charts[category] = None


    return render_template(
        "index.html",
        period=period,
        periods=PERIODS,
        summary_charts=summary_charts,
        ticker_cards=ticker_cards,
    )

if __name__ == "__main__":
    app.run(debug=True)
