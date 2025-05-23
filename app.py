from flask import Flask, render_template, request
import yfinance as yf
from cachetools import TTLCache, cached
import plotly.express as px
from config import TICKERS, REFRESH_INTERVAL

app = Flask(__name__)

PERIODS = ["1d", "5d", "1mo", "6mo", "1y", "ytd", "5y", "max"]

cache = TTLCache(maxsize=32, ttl=REFRESH_INTERVAL)

@cached(cache, key=lambda period: period)
def get_prices(period: str):
    data = yf.download(TICKERS, period=period, interval="1d")
    return data

@app.route("/")
def index():
    period = request.args.get("period", "1mo")
    if period not in PERIODS:
        period = "1mo"
    data = get_prices(period)
    close = data["Close"]
    last_close = close.iloc[-1]
    prev_close = close.iloc[-2]
    pct_change = (last_close - prev_close) / prev_close * 100
    fig = px.line(close, labels={"index": "Date", "value": "Close", "variable": "Ticker"})
    encoded = fig.to_html(full_html=False, include_plotlyjs="cdn")
    return render_template(
        "index.html",
        period=period,
        last_close=last_close.round(2).to_dict(),
        pct_change=pct_change.round(2).to_dict(),
        chart_data=encoded,
        periods=PERIODS,
    )

if __name__ == "__main__":
    app.run(debug=True)
