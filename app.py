from flask import Flask, render_template, request
import io
import base64
import yfinance as yf
from cachetools import TTLCache, cached
from config import TICKERS, REFRESH_INTERVAL

app = Flask(__name__)

PERIODS = ["1d", "5d", "1mo", "6mo", "1y", "ytd", "5y", "max"]

cache = TTLCache(maxsize=1, ttl=REFRESH_INTERVAL)

@cached(cache, key=lambda period: period)
def get_prices(period: str):
    results = {}
    for ticker in TICKERS:
        df = yf.download(ticker, period=period, interval="1d", progress=False)
        if not df.empty:
            results[ticker] = df["Close"]
    return results

def make_chart(series):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(4,3))
    series.plot(ax=ax)
    ax.legend().remove()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")

@app.route("/")
def index():
    period = request.args.get("period", "1mo")
    if period not in PERIODS:
        period = "1mo"
    data = get_prices(period)
    cards = []
    for ticker, series in data.items():
        if len(series) < 2:
            continue
        last_close = series.iloc[-1]
        prev_close = series.iloc[-2]
        pct_change = (last_close - prev_close) / prev_close * 100
        chart = make_chart(series)
        cards.append(
            {
                "ticker": ticker,
                "name": TICKERS[ticker],
                "close": f"{last_close:.2f}",
                "change": f"{pct_change:.2f}",
                "chart": chart,
            }
        )
    return render_template("index.html", period=period, periods=PERIODS, cards=cards)

if __name__ == "__main__":
    app.run(debug=True)
