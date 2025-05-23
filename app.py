from flask import Flask, render_template, request
import io
import base64
import pandas as pd
import yfinance as yf
from cachetools import TTLCache, cached
from config import TICKERS, REFRESH_INTERVAL

app = Flask(__name__)

PERIODS = ["1d", "5d", "1mo", "6mo", "1y", "ytd", "5y", "max"]

cache = TTLCache(maxsize=32, ttl=REFRESH_INTERVAL)

@cached(cache, key=lambda period: period)
def get_prices(period: str) -> pd.DataFrame:
    """Download prices for all tickers, skipping ones with no data."""
    frames = []
    for ticker in TICKERS:
        try:
            df = yf.download(ticker, period=period, interval="1d", progress=False)
        except Exception:
            continue
        if not df.empty:
            df = df[["Close"]].rename(columns={"Close": ticker})
            frames.append(df)
    if frames:
        return pd.concat(frames, axis=1, join="outer")
    return pd.DataFrame()

@app.route("/")
def index():
    period = request.args.get("period", "1mo")
    if period not in PERIODS:
        period = "1mo"
    data = get_prices(period)
    close = data.dropna()

    last_close = {}
    pct_change = {}
    chart_data = ""

    if len(close) >= 2:
        last = close.iloc[-1]
        prev = close.iloc[-2]
        last_close = last.round(2).to_dict()
        pct_change = ((last - prev) / prev * 100).round(2).to_dict()
        fig = close.plot().get_figure()
        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        buf.seek(0)
        chart_data = base64.b64encode(buf.read()).decode("utf-8")
        buf.close()

    return render_template(
        "index.html",
        period=period,
        last_close=last_close,
        pct_change=pct_change,
        chart_data=chart_data,
        periods=PERIODS,
    )

if __name__ == "__main__":
    app.run(debug=True)
