CATEGORIES = {
    "Global Equity": {
        "^GSPC": "S&P 500",
        "^IXIC": "NASDAQ Composite",
        "^RUT": "Russell 2000",
        "^FTSE": "FTSE 100",
        "^STOXX50E": "Euro Stoxx 50",
        "^N225": "Nikkei 225",
        "1563.T": "TSE Growth Core ETF",
        "1343.T": "TSE REIT ETF",
        "^HSI": "Hang Seng",
        "000001.SS": "Shanghai Composite",
        "^STI": "Straits Times",
    },
    "Interest Rate": {
        "^IRX": "US 3M T-Bill",
        "^TNX": "US 10Y Treasury",
    },
    "Currency": {
        "JPY=X": "USD/JPY",
        "EURJPY=X": "EUR/JPY",
        "GBPJPY=X": "GBP/JPY",
        "SGDJPY=X": "SGD/JPY",
        "CHFJPY=X": "CHF/JPY",
    },
    "Commodity": {
        "GC=F": "Gold Futures",
        "BTC-USD": "Bitcoin",
        "CL=F": "Crude Oil WTI",
        "HG=F": "Copper Futures",
    },
    "Global Sector ETFs": {
        "IXN": "Global Tech ETF",
        "IXG": "Global Financials ETF",
        "IXJ": "Global Health Care ETF",
        "IXC": "Global Energy ETF",
        "MXI": "Global Materials ETF",
        "EXI": "Global Industrials ETF",
        "RXI": "Global Cons Discretionary ETF",
        "KXI": "Global Cons Staples ETF",
        "IXP": "Global Communication Services ETF",
        "JXI": "Global Utilities ETF",
        "RWO": "Global Real Estate ETF",
    },
    "US Sector ETFs": {
        "XLK": "US Technology ETF",
        "XLF": "US Financials ETF",
        "XLV": "US Health Care ETF",
        "XLE": "US Energy ETF",
        "XLB": "US Materials ETF",
        "XLI": "US Industrials ETF",
        "XLY": "US Cons Discretionary ETF",
        "XLP": "US Cons Staples ETF",
        "XLC": "US Communication Services ETF",
        "XLU": "US Utilities ETF",
        "XLRE": "US Real Estate ETF",
    },
    "Europe Sector ETFs": {
        "EXV3.DE": "Europe Tech ETF",
        "EXV1.DE": "Europe Banks ETF",
        "EXV4.DE": "Europe Health Care ETF",
        "EXH1.DE": "Europe Oil & Gas ETF",
    },
    "Japan Sector ETFs": {
        "1625.T": "JP Electronics ETF",
        "1626.T": "JP IT & Services ETF",
        "1631.T": "JP Banks ETF",
        "1621.T": "JP Pharma ETF",
        "1618.T": "JP Energy Resources ETF",
    },
    "Global Factor ETFs": {
        "IWVL.L": "World Value Factor ETF",
        "IWFG.L": "World Growth Factor ETF",
        "IWFM.L": "World Momentum Factor ETF",
        "IWQU.L": "World Quality Factor ETF",
        "ACWV": "World Min Volatility ETF",
    },
    "US Factor ETFs": {
        "VLUE": "US Value ETF",
        "IWF": "US Growth ETF",
        "MTUM": "US Momentum ETF",
        "QUAL": "US Quality ETF",
        "USMV": "US Min Volatility ETF",
    },
    "Europe Factor ETFs": {
        "IEVL.L": "Europe Value ETF",
        "IEMO.L": "Europe Momentum ETF",
        "IEFQ.L": "Europe Quality ETF",
    },
    "Japan Factor ETFs": {
        "EWJV": "Japan Value ETF",
        "2636.T": "Japan Quality ETF",
        "1477.T": "Japan Min Volatility ETF",
    },
}

PERIODS = ["1d", "5d", "1mo", "6mo", "1y", "ytd", "5y"]
DEFAULT_PERIOD = "1mo"
REFRESH_INTERVAL = 3600

TICKERS = [t for group in CATEGORIES.values() for t in group.keys()]
