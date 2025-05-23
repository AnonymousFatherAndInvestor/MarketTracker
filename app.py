from flask import Flask, render_template, request, jsonify
from cachetools import TTLCache, cached
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from config import CATEGORIES, TICKERS, PERIODS, DEFAULT_PERIOD, REFRESH_INTERVAL

app = Flask(__name__)

cache = TTLCache(maxsize=8, ttl=REFRESH_INTERVAL)

@cached(cache, key=lambda period: period)
def get_prices(period: str) -> pd.DataFrame:
    """Download close prices for all tickers and forward-fill missing days."""
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
        cols = data.columns.get_level_values(0)
        label = "Close" if "Close" in cols else "Adj Close"
        close = data[label]
    else:
        close = data[["Close"]]
        close.columns = pd.MultiIndex.from_product([["Close"], TICKERS])
    close.index = pd.to_datetime(close.index)
    close = close.asfreq("B")
    return close.ffill()

def sparkline(series: pd.Series) -> str:
    """Return a small inline Plotly chart as HTML."""
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=series.index, y=series.values, mode="lines", line=dict(width=1))
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=40,
        xaxis_visible=False,
        yaxis_visible=False,
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)

def build_summary(close: pd.DataFrame):
    summary = {}
    tables = {}
    for group, tickers in CATEGORIES.items():
        series_list = []
        rows = []
        for ticker, name in tickers.items():
            if ticker not in close.columns:
                continue
            s = close[ticker].dropna()
            if s.empty:
                continue
            first = s.iloc[0]
            last = s.iloc[-1]
            change = (last - first) / first * 100
            norm = (s / first) * 100
            rows.append({
                "ticker": ticker,
                "name": name,
                "last": round(float(last), 2),
                "change": round(float(change), 2),
                "spark": sparkline(norm),
            })
            series_list.append(norm.rename(name))
        if series_list:
            summary[group] = pd.concat(series_list, axis=1)
            tables[group] = rows
    return summary, tables

def group_chart(df: pd.DataFrame) -> str:
    fig = go.Figure()
    for col in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df[col], mode="lines", name=col))
    fig.update_layout(height=300, margin=dict(l=40, r=40, t=30, b=40), legend=dict(orientation="h"))
    return fig.to_html(full_html=False, include_plotlyjs=False)

@app.route("/")
def index():
    period = request.args.get("period", DEFAULT_PERIOD)
    if period not in PERIODS:
        period = DEFAULT_PERIOD
    close = get_prices(period)
    summary, tables = build_summary(close)
    charts = {g: group_chart(df) for g, df in summary.items()}
    return render_template("index.html", periods=PERIODS, period=period, charts=charts, tables=tables)

@app.route("/api/summary")
def api_summary():
    period = request.args.get("period", DEFAULT_PERIOD)
    if period not in PERIODS:
        period = DEFAULT_PERIOD
    close = get_prices(period)
    summary, _ = build_summary(close)
    resp = {g: df.round(2).to_dict() for g, df in summary.items()}
    return jsonify(resp)


if __name__ == "__main__":
    app.run(debug=True)
