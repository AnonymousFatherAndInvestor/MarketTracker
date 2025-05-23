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
        # Detect which level contains the price fields
        if "Close" in data.columns.get_level_values(1) or "Adj Close" in data.columns.get_level_values(1):
            lvl = 1
        else:
            data = data.swaplevel(axis=1)
            lvl = 0
        label = "Adj Close" if "Adj Close" in data.columns.get_level_values(lvl) else "Close"
        close = data.xs(label, level=lvl, axis=1)
    else:
        label = "Adj Close" if "Adj Close" in data.columns else "Close"
        close = data[[label]]
        close.columns = [TICKERS[0]]

    bdays = pd.date_range(close.index.min(), close.index.max(), freq="B")
    close = close.reindex(bdays).ffill()
    return close


def _mini_chart(series: pd.Series) -> str:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=series.index, y=series, mode="lines", line=dict(width=1)))
    fig.update_layout(
        width=150,
        height=60,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis_visible=False,
        yaxis_visible=False,
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)


def build_summary(close: pd.DataFrame):
    summary = {}
    tables = {}
    for group, tickers in CATEGORIES.items():
        series_dict = {}
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
            rows.append({
                "ticker": ticker,
                "name": name,
                "last": round(float(last), 2),
                "change": round(float(change), 2),
                "chart": _mini_chart(s),
            })
            series_dict[ticker] = (s / first) * 100
        if series_dict:
            summary[group] = pd.DataFrame(series_dict)
            tables[group] = rows
    return summary, tables

def summary_charts(data: dict) -> dict:
    charts = {}
    for group, df in data.items():
        fig = go.Figure()
        for col in df.columns:
            fig.add_trace(
                go.Scatter(x=df.index, y=df[col], mode="lines", name=col)
            )
        fig.update_layout(height=300, margin=dict(l=40, r=40, t=30, b=30))
        charts[group] = fig.to_html(full_html=False, include_plotlyjs=False)
    return charts

@app.route("/")
def index():
    period = request.args.get("period", DEFAULT_PERIOD)
    if period not in PERIODS:
        period = DEFAULT_PERIOD
    close = get_prices(period)
    summary, tables = build_summary(close)
    charts = summary_charts(summary)
    return render_template("index.html", periods=PERIODS, period=period, charts=charts, tables=tables)

@app.route("/api/summary")
def api_summary():
    period = request.args.get("period", DEFAULT_PERIOD)
    if period not in PERIODS:
        period = DEFAULT_PERIOD
    close = get_prices(period)
    summary, _ = build_summary(close)
    resp = {grp: df.round(2).to_dict() for grp, df in summary.items()}
    return jsonify(resp)


if __name__ == "__main__":
    app.run(debug=True)
