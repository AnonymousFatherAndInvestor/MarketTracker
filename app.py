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
        data = data.swaplevel(axis=1)
        col = None
        for name in ["Close", "Adj Close"]:
            if name in data.columns.get_level_values(0):
                col = name
                break
        if col is None:
            raise KeyError("Close")
        close = data[col]
    else:
        col = "Close" if "Close" in data.columns else "Adj Close"
        close = data[[col]]
        close.columns = pd.MultiIndex.from_product([[col], TICKERS])

    close = close.ffill()
    all_days = pd.date_range(close.index.min(), close.index.max(), freq="B")
    close = close.reindex(all_days).ffill()
    return close

def compute_avg_daily_return(close: pd.DataFrame, window: int = 30) -> pd.Series:
    """Calculate the average daily percent return for each ticker."""
    returns = close.pct_change()
    return returns.tail(window).mean() * 100

def build_summary(close: pd.DataFrame, avg_returns: pd.Series | None = None):
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
            avg_ret = None
            if avg_returns is not None and ticker in avg_returns:
                avg_ret = avg_returns[ticker]
            rows.append({
                "ticker": ticker,
                "name": name,
                "last": round(float(last), 2),
                "change": round(float(change), 2),
                "avg": round(float(avg_ret), 4) if avg_ret is not None else None,
            })
            series_list.append((s / first) * 100)
        if series_list:
            summary[group] = pd.concat(series_list, axis=1).mean(axis=1)
            tables[group] = rows
    return summary, tables

def summary_chart(summary: dict) -> str:
    fig = go.Figure()
    for name, series in summary.items():
        fig.add_trace(go.Scatter(x=series.index, y=series, mode="lines", name=name))
    fig.update_layout(height=400, margin=dict(l=40,r=40,t=40,b=40))
    return fig.to_html(full_html=False, include_plotlyjs='cdn')

@app.route("/")
def index():
    period = request.args.get("period", DEFAULT_PERIOD)
    if period not in PERIODS:
        period = DEFAULT_PERIOD
    close = get_prices(period)
    close_30d = get_prices("1mo")
    avg_returns = compute_avg_daily_return(close_30d)
    summary, tables = build_summary(close, avg_returns)
    chart_html = summary_chart(summary)
    return render_template("index.html", periods=PERIODS, period=period, chart=chart_html, tables=tables)

@app.route("/api/summary")
def api_summary():
    period = request.args.get("period", DEFAULT_PERIOD)
    if period not in PERIODS:
        period = DEFAULT_PERIOD
    close = get_prices(period)
    close_30d = get_prices("1mo")
    avg_returns = compute_avg_daily_return(close_30d)
    summary, _ = build_summary(close, avg_returns)
    resp = {k: v.round(2).to_dict() for k,v in summary.items()}
    return jsonify(resp)


if __name__ == "__main__":
    app.run(debug=True)
