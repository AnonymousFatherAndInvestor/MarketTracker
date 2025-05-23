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
        for ticker in data.columns.levels[0]:
            df = data[ticker]
            col = "Close" if "Close" in df.columns else "Adj Close" if "Adj Close" in df.columns else None
            if col is None:
                continue
            series = df[col].dropna()
            if series.empty:
                continue
            series.index = pd.to_datetime(series.index)
            idx = pd.date_range(series.index.min(), series.index.max(), freq="B")
            close_dict[ticker] = series.reindex(idx).ffill()
    else:
        col = "Close" if "Close" in data.columns else "Adj Close" if "Adj Close" in data.columns else None
        if col:
            series = data[col].dropna()
            if not series.empty:
                series.index = pd.to_datetime(series.index)
                idx = pd.date_range(series.index.min(), series.index.max(), freq="B")
                close_dict[TICKERS[0]] = series.reindex(idx).ffill()

    close = pd.DataFrame(close_dict)
    close.sort_index(inplace=True)
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
        subset = close[present]

        rows = []
        norm_series = []
        for ticker in present:
            s = subset[ticker].dropna()
            if s.empty:
                continue
            first = s.iloc[0]
            last = s.iloc[-1]
            change = (last - first) / first * 100
            rows.append({
                "ticker": ticker,
                "name": tickers[ticker],
                "last": round(float(series.iloc[-1]), 2),
                "change": round(float(change), 2),
                "spark": _mini_chart((s / first) * 100),
            })
            norm_series.append((s / first) * 100)

        if rows:
            norm_df = pd.concat(norm_series, axis=1, join="outer")
            norm_df.columns = [r["ticker"] for r in rows]
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
    if period not in PERIODS:
        period = DEFAULT_PERIOD
    close = get_prices(period)
    data, tables = build_summary(close)
    charts = summary_charts(data)
    return render_template(
        "index.html",
        periods=PERIODS,
        period=period,
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
    app.run(debug=True)
