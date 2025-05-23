from flask import Flask, render_template, request
import pandas as pd
import yfinance as yf
from cachetools import TTLCache, cached
from config import TICKERS, REFRESH_INTERVAL

app = Flask(__name__)

PERIODS = ["1d", "5d", "1mo", "6mo", "1y", "ytd", "5y", "max"]

cache = TTLCache(maxsize=32, ttl=REFRESH_INTERVAL)

@cached(cache, key=lambda period: period)
def get_prices(period: str) -> pd.DataFrame:
    """Download prices for all tickers, skipping ones that return no data."""
    frames = {}
    for ticker in TICKERS:
        try:
            df = yf.download(ticker, period=period, interval="1d", progress=False)
        except Exception:
            continue
        if not df.empty:
            frames[ticker] = df["Close"]
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, axis=1)

@app.route("/")
def index():
    period = request.args.get("period", "1mo")
    if period not in PERIODS:
        period = "1mo"
    data = get_prices(period)
    if data.empty:
        last_close = {}
        pct_change = {}
        chart_img = ""
    else:
        close = data.dropna()
        last_close = close.iloc[-1].round(2).to_dict()
        prev_close = close.iloc[-2]
        pct_change = ((close.iloc[-1] - prev_close) / prev_close * 100).round(2).to_dict()
        chart = close.plot().get_figure()
        import io, base64
        buf = io.BytesIO()
        chart.savefig(buf, format="png")
        buf.seek(0)
        chart_img = base64.b64encode(buf.read()).decode("utf-8")
        buf.close()
    return render_template(
        "index.html",
        period=period,
        last_close=last_close,
        pct_change=pct_change,
        chart_data=chart_img,
        periods=PERIODS,
    )

if __name__ == "__main__":
    app.run(debug=True)
