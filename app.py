from flask import Flask, render_template, request
import yfinance as yf
from cachetools import TTLCache, cached
from config import CATEGORIES, REFRESH_INTERVAL
import plotly.graph_objects as go

app = Flask(__name__)

PERIODS = ["1d", "5d", "1mo", "6mo", "1y", "ytd", "5y", "max"]

cache = TTLCache(maxsize=128, ttl=REFRESH_INTERVAL)

@cached(cache)
def get_prices(ticker: str, period: str):
    data = yf.download(ticker, period=period, interval="1d", progress=False)
    if not data.empty:
        data = data.ffill()
    return data

@app.route("/")
def index():
    period = request.args.get("period", "1mo")
    if period not in PERIODS:
        period = "1mo"

    categories = []
    for category, tickers in CATEGORIES.items():
        items = []
        for ticker, name in tickers.items():
            df = get_prices(ticker, period)
            if df.empty or "Close" not in df or df["Close"].dropna().size < 2:
                continue
            close = df["Close"].dropna()
            start_price = float(close.iloc[0])
            end_price = float(close.iloc[-1])
            pct_change = (end_price - start_price) / start_price * 100

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=close.index, y=close.values, mode="lines", name=name))
            fig.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=300,
                              legend=dict(orientation="h", y=-0.2))
            chart_html = fig.to_html(full_html=False, include_plotlyjs=False)

            items.append({
                "ticker": ticker,
                "name": name,
                "last_close": f"{end_price:.2f}",
                "pct_change": f"{pct_change:.2f}",
                "chart": chart_html,
            })
        if items:
            categories.append((category, items))

    return render_template(
        "index.html",
        period=period,
        periods=PERIODS,
        categories=categories,
    )

if __name__ == "__main__":
    app.run(debug=True)
