from flask import Flask, render_template, request, jsonify
from cachetools import TTLCache, cached
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from config import (
    CATEGORIES,
    TICKERS,
    PERIODS,
    DEFAULT_PERIOD,
    REFRESH_INTERVAL,
)

app = Flask(__name__)

cache = TTLCache(maxsize=8, ttl=REFRESH_INTERVAL)


@cached(cache, key=lambda period: period)
def get_prices(period: str) -> pd.DataFrame:
    """Download closing prices for all tickers and reindex each series to business days."""
    tickers_str = " ".join(TICKERS)
    data = yf.download(
        tickers_str,
        period=period,
        interval="1d",
        group_by="ticker",
        auto_adjust=False,
        threads=True,
    )

    close_dict: dict[str, pd.Series] = {}

    if isinstance(data.columns, pd.MultiIndex):
        # extract Close or Adj Close for each ticker individually
        frames: list[pd.Series] = []
        for ticker in TICKERS:
            if (ticker, "Close") in data.columns:
                frames.append(data[ticker]["Close"].rename(ticker))
            elif (ticker, "Adj Close") in data.columns:
                frames.append(data[ticker]["Adj Close"].rename(ticker))
        if frames:
            close = pd.concat(frames, axis=1)
        else:
            close = pd.DataFrame()
    else:
        # yf returns a single-index dataframe when only one ticker succeeds
        if "Close" in data.columns:
            close = data[["Close"]]
        elif "Adj Close" in data.columns:
            close = data[["Adj Close"]].rename(columns={"Adj Close": "Close"})
        else:
            raise KeyError("Close")
        close.columns = pd.Index(TICKERS[:1])

    close.index = pd.to_datetime(close.index)
    close = close.sort_index()
    idx = pd.date_range(close.index.min(), close.index.max(), freq="B")
    close = close.reindex(idx).ffill()
    return close


def _mini_chart(series: pd.Series) -> str:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=series.index, y=series, mode="lines"))
    fig.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        height=40,
        margin=dict(l=0, r=0, t=0, b=0),
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)

def build_summary(close: pd.DataFrame):
    """Return normalized data per group and table rows."""
    data: dict[str, pd.DataFrame] = {}
    tables: dict[str, list] = {}
    for group, tickers in CATEGORIES.items():
        present = [t for t in tickers if t in close.columns]
        if not present:
            continue

        series_dict: dict[str, pd.Series] = {}
        rows = []
        norm_parts = {}
        for ticker in present:
            series = close[ticker].dropna()
            if series.empty:
                continue
            series = series.ffill()
            norm_parts[ticker] = series / series.iloc[0] * 100

            first = series.iloc[0]
            last = series.iloc[-1]
            change = (last - first) / first * 100
            rows.append({
                "ticker": ticker,
                "name": tickers[ticker],
                "last": round(float(series.iloc[-1]), 2),
                "change": round(float(change), 2),
                "spark": _mini_chart(norm_parts[ticker]),
            })

        if not norm_parts:
            continue

        norm_df = pd.DataFrame(norm_parts).reindex(close.index).ffill()
        data[group] = norm_df
        tables[group] = rows
    return data, tables


def summary_charts(data: dict[str, pd.DataFrame]) -> dict:
    charts = {}
    for group, df in data.items():
        fig = go.Figure()
        for ticker in df.columns:
            name = CATEGORIES[group].get(ticker, ticker)
            fig.add_trace(go.Scatter(x=df.index, y=df[ticker], mode="lines", name=name))
        fig.update_layout(height=300, margin=dict(l=40, r=40, t=40, b=40))
        charts[group] = fig.to_html(full_html=False, include_plotlyjs="cdn")
    return charts

@app.route("/")
def index():
    period = request.args.get("period", DEFAULT_PERIOD)
    selected_category = request.args.get("category", "")
    
    if period not in PERIODS:
        period = DEFAULT_PERIOD
    
    close = get_prices(period)
    data, tables = build_summary(close)
    
    # Filter by selected category if specified
    if selected_category and selected_category in CATEGORIES:
        data = {selected_category: data.get(selected_category, pd.DataFrame())}
        tables = {selected_category: tables.get(selected_category, [])}
    
    charts = summary_charts(data)
    return render_template(
        "index.html",
        periods=PERIODS,
        period=period,
        selected_category=selected_category,
        charts=charts,
        tables=tables,
    )

@app.route("/api/summary")
def api_summary():
    period = request.args.get("period", DEFAULT_PERIOD)
    if period not in PERIODS:
        period = DEFAULT_PERIOD
    close = get_prices(period)
    data, _ = build_summary(close)
    resp = {grp: df.round(2).to_dict() for grp, df in data.items()}
    return jsonify(resp)


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
