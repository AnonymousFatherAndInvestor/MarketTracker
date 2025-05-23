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
    """Download closing prices and forward fill on business days."""
    tickers_str = " ".join(TICKERS)
    data = yf.download(
        tickers_str,
        period=period,
        interval="1d",
        group_by="ticker",
        auto_adjust=False,
        threads=True,
    )

    if isinstance(data.columns, pd.MultiIndex):
        cols = data.columns.get_level_values(1)
        if "Close" in cols:
            close = data.swaplevel(axis=1).xs("Close", level=0, axis=1)
        elif "Adj Close" in cols:
            close = data.swaplevel(axis=1).xs("Adj Close", level=0, axis=1)
        else:
            raise KeyError("Close")
    else:
        if "Close" in data.columns:
            close = data[["Close"]]
        elif "Adj Close" in data.columns:
            close = data[["Adj Close"]].rename(columns={"Adj Close": "Close"})
        else:
            raise KeyError("Close")
        close.columns = pd.Index(TICKERS)

    close.index = pd.to_datetime(close.index)
    close = close.sort_index()
    # align to business days without extending beyond the last price for each
    # ticker. Missing days inside the range are forward filled but trailing
    # NaNs remain so later logic can drop or ignore them.
    idx = pd.date_range(close.index.min(), close.index.max(), freq="B")
    close = close.reindex(idx)
    for col in close.columns:
        last = close[col].last_valid_index()
        if last is not None:
            close.loc[:last, col] = close.loc[:last, col].ffill()
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
        rows = []
        frames = []
        for ticker in present:
            series = close[ticker].dropna()
            if series.empty:
                continue
            series = series.ffill()
            norm = (series / series.iloc[0]) * 100
            frames.append(norm.rename(ticker))
            change = (series.iloc[-1] - series.iloc[0]) / series.iloc[0] * 100
            rows.append({
                "ticker": ticker,
                "name": tickers[ticker],
                "last": round(float(series.iloc[-1]), 2),
                "change": round(float(change), 2),
                "spark": _mini_chart(norm),
            })
        if rows:
            data[group] = pd.concat(frames, axis=1)
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
