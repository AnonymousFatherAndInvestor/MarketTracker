from flask import Flask, render_template, request
import io
import base64
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
from cachetools import TTLCache, cached
from config import TICKERS, REFRESH_INTERVAL

app = Flask(__name__)

PERIODS = ["1d", "5d", "1mo", "6mo", "1y", "ytd", "5y", "max"]

cache = TTLCache(maxsize=32, ttl=REFRESH_INTERVAL)

@cached(cache, key=lambda period: period)
def get_prices(period: str):
    results = {}
    fetch_period = "2d" if period == "1d" else period
    for ticker, name in TICKERS.items():
        df = yf.download(ticker, period=fetch_period, interval="1d", progress=False)
        if df.empty or "Close" not in df:
            continue
        close = df["Close"].dropna()
        if close.empty:
            continue
        close = close.resample("D").ffill()
        if period == "1d" and len(close) > 1:
            close = close[-2:]
        results[ticker] = {
            "name": name,
            "series": close,
            "last": close.iloc[-1],
            "first": close.iloc[0],
        }
    return results

@app.route("/")
def index():
    period = request.args.get("period", "1mo")
    if period not in PERIODS:
        period = "1mo"
    data = get_prices(period)
    cards = []
    for ticker, info in data.items():
        series = info["series"]
        fig, ax = plt.subplots()
        ax.plot(series.index, series.values, label=info["name"])
        ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        buf.seek(0)
        encoded = base64.b64encode(buf.read()).decode("utf-8")
        buf.close()
        cards.append({
            "ticker": ticker,
            "name": info["name"],
            "close": round(info["last"], 2),
            "change": round((info["last"] - info["first"]) / info["first"] * 100, 2),
            "chart": encoded,
        })
        plt.close(fig)
    return render_template(
        "index.html",
        period=period,
        cards=cards,
        periods=PERIODS,
    )

if __name__ == "__main__":
    app.run(debug=True)
