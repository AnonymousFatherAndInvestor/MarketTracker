# MarketTracker

A minimal Flask dashboard to display selected market indices using yfinance.

## Setup

If you are running in a clean environment, install dependencies first.  A helper
script `setup.sh` is provided:

```bash
./setup.sh
```

It simply runs `python -m pip install -r requirements.txt`.  In network
restricted environments this may still fail, so ensure you have connectivity or
use a prebuilt environment.

Run the application:

```bash
python app.py
```

Then open your browser at `http://localhost:5000`.
