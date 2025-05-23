from flask import Flask, render_template, request
import yfinance as yf
from cachetools import TTLCache, cached
from config import TICKERS, REFRESH_INTERVAL

app = Flask(__name__)

PERIODS = ["1d", "5d", "1mo", "6mo", "1y", "ytd", "5y", "max"]

cache = TTLCache(maxsize=128, ttl=REFRESH_INTERVAL)

@cached(cache, key=lambda ticker, period: (ticker, period))
def get_prices(ticker: str, period: str):
    df = yf.download(ticker, period=period, interval="1d")
    if "Close" in df:
        close = df["Close"].ffill()
    else:
        close = df.ffill()
    return close

@app.route("/")
def index():
    period = request.args.get("period", "1mo")
    if period not in PERIODS:
        period = "1mo"
    cards = []
    import io, base64
    for ticker, name in TICKERS.items():
        close = get_prices(ticker, period)
        if close.empty:
            continue
        close = close.ffill()
        if len(close) < 1:
            continue
        last_close = close.iloc[-1]
        prev_close = close.iloc[-2] if len(close) > 1 else last_close
        pct_change = ((last_close - prev_close) / prev_close * 100) if prev_close != 0 else 0
        fig = close.plot(title=name).get_figure()
        buf = io.BytesIO()
        fig.tight_layout()
        fig.savefig(buf, format="png")
        buf.seek(0)
        encoded = base64.b64encode(buf.read()).decode("utf-8")
        buf.close()
        cards.append({
            "ticker": ticker,
            "name": name,
            "close": round(float(last_close), 2),
            "change": round(float(pct_change), 2),
            "chart": encoded,
        })
    return render_template(
        "index.html",
        period=period,
        periods=PERIODS,
        cards=cards,
    )

if __name__ == "__main__":
    app.run(debug=True)
