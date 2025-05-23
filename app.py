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
    """Download closing prices for all tickers and forward fill on business days."""
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
    idx = pd.date_range(close.index.min(), close.index.max(), freq="B")
    close = close.reindex(idx).ffill()
    return close

def compute_avg_daily_return(close: pd.DataFrame, window: int = 30) -> pd.Series:
    """Calculate the average daily percent return for each ticker."""
    returns = close.pct_change()
    return returns.tail(window).mean() * 100

def build_summary(close: pd.DataFrame, avg_returns: pd.Series | None = None):
    summary = {}
    tables = {}
    for group, tickers in CATEGORIES.items():
        present = [t for t in tickers if t in close.columns]
        if not present:
            continue
        subset = close[present]
        # earliest date where all tickers have data
        first_valid = subset.dropna(how="any").index.min()
        if pd.isna(first_valid):
            continue
        subset = subset.loc[first_valid:].ffill()

        series_list = []
        rows = []
        for ticker in present:
            s = subset[ticker]
            first = s.iloc[0]
            last = s.iloc[-1]
            change = (last - first) / first * 100
            avg_ret = None
            if avg_returns is not None and ticker in avg_returns:
                avg_ret = avg_returns[ticker]
            rows.append({
                "ticker": ticker,
                "name": tickers[ticker],
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
