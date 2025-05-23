from flask import Flask, render_template, request
import yfinance as yf
from cachetools import TTLCache, cached
import pandas as pd
import plotly.graph_objects as go
from config import CATEGORIES, REFRESH_INTERVAL

app = Flask(__name__)

PERIODS = ["1d", "5d", "1mo", "6mo", "1y", "ytd", "5y", "max"]

ALL_TICKERS = [t for group in CATEGORIES.values() for t in group.keys()]

cache = TTLCache(maxsize=32, ttl=REFRESH_INTERVAL)

@cached(cache, key=lambda period: period)
def get_prices(period: str):
    data = {}
    for ticker in ALL_TICKERS:
        df = yf.download(ticker, period=period, interval="1d", progress=False)
        if df.empty:
            continue
        close = df["Close"].copy()
        full_range = pd.date_range(close.index.min(), close.index.max(), freq="D")
        close = close.reindex(full_range, method="ffill")
        data[ticker] = close
    return data


def make_line_chart(series, name):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=series.index, y=series.values, mode="lines", name=name))
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=200, legend=dict(orientation="h"))
    return fig.to_html(include_plotlyjs=False, full_html=False)


def make_relative_chart(data_dict):
    fig = go.Figure()
    for name, series in data_dict.items():
        base = series.iloc[0]
        rel = series / base * 100
        fig.add_trace(go.Scatter(x=rel.index, y=rel.values, mode="lines", name=name))
    fig.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=250, legend=dict(orientation="h"))
    return fig.to_html(include_plotlyjs=False, full_html=False)


@app.route("/")
def index():
    period = request.args.get("period", "1mo")
    if period not in PERIODS:
        period = "1mo"

    prices = get_prices(period)

    categories = []
    summaries = {}

    for cat, tickers in CATEGORIES.items():
        cat_items = []
        rel_data = {}
        for ticker, name in tickers.items():
            series = prices.get(ticker)
            if series is None or len(series) < 1:
                continue
            last_close = series.iloc[-1]
            first_close = series.iloc[0]
            pct_change = (last_close - first_close) / first_close * 100
            chart_html = make_line_chart(series, name)
            cat_items.append({
                "ticker": ticker,
                "name": name,
                "close": f"{last_close:.2f}",
                "change": f"{pct_change:.2f}%",
                "chart": chart_html,
            })
            rel_data[name] = series
        if rel_data:
            summaries[cat] = make_relative_chart(rel_data)
        categories.append({"name": cat, "items": cat_items})

    return render_template(
        "index.html",
        period=period,
        periods=PERIODS,
        summaries=summaries,
        categories=categories,
    )


if __name__ == "__main__":
    app.run(debug=True)
