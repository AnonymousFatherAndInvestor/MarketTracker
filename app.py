from flask import Flask, render_template, request
import yfinance as yf
import pandas as pd
from cachetools import TTLCache, cached
from config import TICKER_GROUPS, ALL_TICKERS, REFRESH_INTERVAL
import plotly.graph_objects as go

app = Flask(__name__)

PERIODS = ["1d", "5d", "1mo", "6mo", "1y", "ytd", "5y", "max"]

cache = TTLCache(maxsize=32, ttl=REFRESH_INTERVAL)

@cached(cache, key=lambda period: period)
def get_prices(period: str) -> pd.DataFrame:
    data = yf.download(ALL_TICKERS, period=period, interval="1d", group_by="ticker")
    if isinstance(data.columns, pd.MultiIndex):
        close = data.loc[:, pd.IndexSlice[:, 'Close']]
        close.columns = close.columns.get_level_values(0)
    else:
        close = data[['Close']]
    close = close.ffill()
    return close

@app.route("/")
def index():
    period = request.args.get("period", "1mo")
    if period not in PERIODS:
        period = "1mo"
    close = get_prices(period)

    last_close = close.iloc[-1]
    first_close = close.iloc[0]
    pct_change = (last_close - first_close) / first_close * 100

    cards = []
    for group in TICKER_GROUPS.values():
        for ticker, name in group.items():
            if ticker not in close.columns:
                continue
            cards.append({
                'ticker': ticker,
                'name': name,
                'close': round(last_close[ticker], 2),
                'change': round(pct_change[ticker], 2),
            })

    charts = []
    for group_name, tickers in TICKER_GROUPS.items():
        fig = go.Figure()
        for ticker, name in tickers.items():
            if ticker not in close.columns:
                continue
            series = close[ticker] / close[ticker].iloc[0] * 100
            fig.add_trace(go.Scatter(x=close.index, y=series, mode='lines', name=name))
        fig.update_layout(
            title=group_name,
            template='plotly_white',
            legend=dict(orientation='h', y=-0.2, x=0.5, xanchor='center')
        )
        charts.append({'group': group_name, 'html': fig.to_html(include_plotlyjs=False, full_html=False)})

    return render_template(
        "index.html",
        period=period,
        periods=PERIODS,
        cards=cards,
        charts=charts,
    )

if __name__ == "__main__":
    app.run(debug=True)
