from flask import Flask, render_template, request
import yfinance as yf
from cachetools import TTLCache, cached
from config import TICKERS, REFRESH_INTERVAL
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)

PERIODS = ["1d", "5d", "1mo", "6mo", "1y", "ytd", "5y", "max"]

cache = TTLCache(maxsize=32, ttl=REFRESH_INTERVAL)

def _fetch_series(ticker: str, period: str) -> pd.Series:
    df = yf.download(ticker, period=period, interval="1d")
    if df.empty:
        return pd.Series(dtype=float)
    close = df["Close"].ffill()
    close.index = pd.to_datetime(close.index)
    return close

@cached(cache, key=lambda period: period)
def get_prices(period: str):
    result = {}
    for category, tickers in TICKERS.items():
        cat_data = {}
        for tic in tickers:
            series = _fetch_series(tic, period)
            if len(series) >= 2:
                cat_data[tic] = series
        result[category] = cat_data
    return result

@app.route("/")
def index():
    period = request.args.get("period", "1mo")
    if period not in PERIODS:
        period = "1mo"
    data = get_prices(period)
    categories = []
    for cat_name, tickers in TICKERS.items():
        series_map = data.get(cat_name, {})
        ticker_cards = []
        for tic, display in tickers.items():
            series = series_map.get(tic)
            if series is None or series.empty:
                continue
            last = series.iloc[-1]
            first = series.iloc[0]
            change = (last - first) / first * 100
            fig, ax = plt.subplots()
            ax.plot(series.index, series.values, label=display)
            ax.legend(loc="best")
            ax.set_title(display)
            fig.tight_layout()
            buf = io.BytesIO()
            fig.savefig(buf, format="png")
            buf.seek(0)
            img = base64.b64encode(buf.read()).decode("utf-8")
            buf.close()
            plt.close(fig)
            ticker_cards.append({
                "ticker": tic,
                "name": display,
                "close": round(float(last), 2),
                "change": round(float(change), 2),
                "chart": img,
            })

        rel_img = None
        if series_map:
            fig, ax = plt.subplots()
            for tic, series in series_map.items():
                disp = TICKERS[cat_name][tic]
                norm = series / series.iloc[0] * 100
                ax.plot(norm.index, norm.values, label=disp)
            ax.legend(loc="best")
            ax.set_title(f"{cat_name} Relative")
            fig.tight_layout()
            buf = io.BytesIO()
            fig.savefig(buf, format="png")
            buf.seek(0)
            rel_img = base64.b64encode(buf.read()).decode("utf-8")
            buf.close()
            plt.close(fig)

        categories.append({"name": cat_name, "tickers": ticker_cards, "relative_chart": rel_img})

    return render_template(
        "index.html",
        period=period,
        periods=PERIODS,
        categories=categories,
    )

if __name__ == "__main__":
    app.run(debug=True)
